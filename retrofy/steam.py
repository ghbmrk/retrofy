"""Loopback Steam OpenID linking and visible-library sync. No game download/execution.
Only Valve HTTPS endpoints receive requests. Credentials are never persisted.
"""
import datetime as dt
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import time
from urllib import error, parse, request

OPENID='https://steamcommunity.com/openid/login'
API='https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/'
NS='http://specs.openid.net/auth/2.0'
MAX_RESPONSE=8*1024*1024

class SteamError(ValueError): pass

class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SteamError('Unexpected redirect from Valve; retry later')

def valve(url, body=None):
    if url not in (OPENID, API) and not url.startswith(API+'?'):
        raise SteamError('Refused non-Valve endpoint')
    req=request.Request(url, data=body, headers={'User-Agent':'Retrofy/0.1 local-library-sync'})
    if body is not None: req.add_header('Content-Type','application/x-www-form-urlencoded')
    try:
        with request.build_opener(NoRedirect).open(req,timeout=20) as response:
            data=response.read(MAX_RESPONSE+1)
        if len(data)>MAX_RESPONSE: raise SteamError('Valve response exceeds local size limit')
        return data.decode('utf-8')
    except (error.URLError, OSError, UnicodeError) as exc:
        # Never include request URLs or exception text: the API key may be in a URL.
        raise SteamError('Valve request failed; check connectivity, key and library visibility') from None

def identity_fields(params, return_to, now=None):
    """Validate assertion shape before asking Valve to verify its signature."""
    now=now or dt.datetime.now(dt.timezone.utc)
    required=['ns','mode','op_endpoint','claimed_id','identity','return_to','response_nonce','assoc_handle','signed','sig']
    if any('openid.'+k not in params for k in required): raise SteamError('Incomplete Steam assertion')
    if params['openid.ns']!=NS or params['openid.mode']!='id_res': raise SteamError('Steam sign-in was cancelled or invalid')
    if params['openid.op_endpoint']!=OPENID or params['openid.return_to']!=return_to:
        raise SteamError('Steam endpoint or callback mismatch')
    claimed=params['openid.claimed_id']
    match=re.fullmatch(r'https://steamcommunity\.com/openid/id/([0-9]{17})',claimed)
    if not match or not 76561197960265728 < int(match.group(1)) <= 76561202255233023 or claimed!=params['openid.identity']: raise SteamError('Invalid Steam identity')
    signed=set(params['openid.signed'].split(','))
    if not {'op_endpoint','claimed_id','identity','return_to','response_nonce','assoc_handle'}<=signed:
        raise SteamError('Steam assertion omits signed identity fields')
    nonce=params['openid.response_nonce']
    if len(nonce)>256: raise SteamError('Invalid Steam nonce')
    try: stamp=dt.datetime.strptime(nonce[:20],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)
    except ValueError: raise SteamError('Invalid Steam nonce') from None
    if abs((now-stamp).total_seconds())>300: raise SteamError('Steam assertion expired; start again')
    return match.group(1)

def verify_identity(params,return_to):
    steamid=identity_fields(params,return_to)
    payload={k:v for k,v in params.items() if k.startswith('openid.')}
    payload['openid.mode']='check_authentication'
    response=valve(OPENID,parse.urlencode(payload).encode())
    fields=dict(line.split(':',1) for line in response.splitlines() if ':' in line)
    if fields.get('is_valid')!='true' or fields.get('ns')!=NS:
        raise SteamError('Steam could not verify this sign-in')
    return steamid

def normalize_library(document, steamid):
    if not isinstance(document,dict): raise SteamError('Invalid library response')
    response=document.get('response')
    if not isinstance(response,dict) or 'game_count' not in response or 'games' not in response and response.get('game_count')!=0:
        raise SteamError('Library not visible or response incomplete. Open Steam profile > Edit Profile > Privacy Settings > Game details, or use a key allowed to see it.')
    games=response.get('games',[]); count=response['game_count']
    if type(count) is not int or count<0 or not isinstance(games,list) or len(games)!=count:
        raise SteamError('Inconsistent library response; no partial sync saved')
    cleaned=[]; seen=set()
    for game in games:
        if not isinstance(game,dict): raise SteamError('Invalid game entry')
        appid=game.get('appid'); name=game.get('name',''); minutes=game.get('playtime_forever',0)
        if type(appid) is not int or appid<=0 or appid in seen or not isinstance(name,str) or len(name)>1024 or type(minutes) is not int or minutes<0:
            raise SteamError('Invalid game metadata')
        seen.add(appid); cleaned.append(dict(appid=appid,name=name,playtime_minutes=minutes,
            store_url='https://store.steampowered.com/app/'+str(appid)+'/',compatibility='unassessed'))
    return dict(schema=1,steamid=steamid,source='Valve GetOwnedGames',
        synced_at=dt.datetime.now(dt.timezone.utc).isoformat(),games=sorted(cleaned,key=lambda g:g['appid']),
        ownership='visible library metadata, not authenticated ownership entitlement',
        files_accessed=False,adaptation_rights_verified=False)

def fetch_library(steamid,key):
    if not re.fullmatch(r'[0-9a-fA-F]{32}',key): raise SteamError('A 32-character Steam Web API key is required')
    # Valve documents this endpoint as GET. Never log the URL or store the key.
    query=parse.urlencode(dict(key=key,steamid=steamid,include_appinfo=1,include_played_free_games=1,format='json'))
    try: document=json.loads(valve(API+'?'+query))
    except json.JSONDecodeError: raise SteamError('Valve returned invalid JSON') from None
    return normalize_library(document,steamid)

def private_json(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    # Refuse replacement/symlink attacks. Each attempt gets a fresh file.
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f: json.dump(value,f,indent=2); f.write('\n')

class LinkSession:
    def __init__(self, output):
        self.output=Path(output).resolve()
        self.token=secrets.token_urlsafe(32)
        self.csrf=secrets.token_urlsafe(32)
        self.account=None; self.message=''; self.synced=False; self.used_nonce=set()
        self.created=time.monotonic(); self.base=None
    @property
    def root(self): return '/'+self.token
    @property
    def return_to(self): return self.base+self.root+'/callback'
    def login_url(self):
        return OPENID+'?'+parse.urlencode({'openid.ns':NS,'openid.mode':'checkid_setup',
            'openid.return_to':self.return_to,'openid.realm':self.base+'/',
            'openid.identity':NS+'/identifier_select','openid.claimed_id':NS+'/identifier_select'})

def handler_for(session):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass  # Callback assertions, secrets and personal library stay out of logs.
        def permitted(self):
            return self.headers.get('Host')==parse.urlsplit(session.base).netloc and time.monotonic()-session.created<1800
        def send(self,status,body='',location=None):
            self.send_response(status)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Cache-Control','no-store')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            if location: self.send_header('Location',location)
            encoded=body.encode(); self.send_header('Content-Length',str(len(encoded))); self.end_headers(); self.wfile.write(encoded)
        def page(self):
            account=html.escape(session.account or 'Not linked')
            message=html.escape(session.message)
            form=''
            if session.account and not session.synced:
                form=f'''<form method="post" action="{session.root}/sync"><input type="hidden" name="csrf" value="{session.csrf}">
<label>Steam Web API key <input name="key" type="password" required autocomplete="off" maxlength="32" pattern="[0-9a-fA-F]{{32}}"></label>
<button>Sync visible library</button></form>
<p><a href="https://steamcommunity.com/dev/apikey" target="_blank" rel="noreferrer">Get a key directly from Valve</a>. Enter it only here. The key stays in memory for this request and is never saved.
Steam sign-in identifies the account; it does not grant library API access. Private game details may remain unavailable.</p>'''
            return f'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Retrofy · Steam</title>
<style>body{{background:#111820;color:#e9eee7;font:18px system-ui;max-width:720px;margin:8vh auto;padding:24px;line-height:1.6}}a{{color:#91e2be}}input,button{{font:inherit;padding:10px;margin:8px 0}}label{{display:block}}input{{display:block}}button{{cursor:pointer}}.status{{border-left:4px solid #91e2be;padding:16px}}</style>
<h1>Connect your Steam library</h1><p>Link an account, then import visible game names and IDs to this computer. Game files, passwords and purchases are not accessed.</p>
<p class="status">Account: {account}<br>{message}</p>
<p><a href="{session.root}/login">Sign in on Steam</a></p>{form}
<p>Synced: {'yes' if session.synced else 'no'}. Local records: {html.escape(str(session.output))}</p>
<p>Imported games remain unassessed. Library visibility does not establish adaptation rights or native ROM compatibility.</p>'''
        def do_GET(self):
            if not self.permitted(): return self.send(403,'Session expired or invalid host')
            url=parse.urlsplit(self.path)
            if url.path==session.root: return self.send(200,self.page())
            if url.path==session.root+'/login':
                if session.account: return self.send(409,'Account already linked. Restart the command to switch accounts.')
                return self.send(303,location=session.login_url())
            if url.path==session.root+'/callback':
                try:
                    if session.account: raise SteamError('Already linked; callback cannot be replayed')
                    if len(url.query)>16384: raise SteamError('Oversized callback')
                    fields=parse.parse_qs(url.query,keep_blank_values=True,max_num_fields=30)
                    if any(len(v)!=1 for v in fields.values()): raise SteamError('Duplicate assertion fields')
                    params={k:v[0] for k,v in fields.items()}
                    nonce=params.get('openid.response_nonce','')
                    if nonce in session.used_nonce: raise SteamError('Replayed Steam callback')
                    steamid=verify_identity(params,session.return_to)
                    private_json(session.output/'account.json',dict(schema=1,steamid=steamid,verified_by='Steam OpenID check_authentication'))
                    session.account=steamid; session.used_nonce.add(nonce)
                    session.message='Steam verified the account. Library retrieval still requires an API key.'
                except (SteamError,ValueError,OSError):
                    session.message='Account link failed or could not be saved. Start sign-in again; existing files are never replaced.'
                return self.send(303,location=session.root)
            return self.send(404,'Not found')
        def do_POST(self):
            if not self.permitted() or self.path!=session.root+'/sync': return self.send(403,'Invalid request')
            if self.headers.get('Origin')!=session.base: return self.send(403,'Invalid origin')
            if self.headers.get('Content-Type')!='application/x-www-form-urlencoded': return self.send(415,'Invalid form type')
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=2048: raise SteamError('Invalid form size')
                fields=parse.parse_qs(self.rfile.read(size).decode(),max_num_fields=2,keep_blank_values=True)
                if any(len(v)!=1 for v in fields.values()): raise SteamError('Duplicate form fields')
                if not secrets.compare_digest(fields.get('csrf',[''])[0],session.csrf): raise SteamError('Invalid form token')
                if not session.account or session.synced: raise SteamError('Sign in first or start a fresh sync session')
                library=fetch_library(session.account,fields.get('key',[''])[0])
                private_json(session.output/'library.json',library)
                session.synced=True; session.message=f"Saved {len(library['games'])} visible games locally. No compatibility is implied."
            except (SteamError,ValueError,OSError) as exc:
                session.message=str(exc) if isinstance(exc,SteamError) else 'Sync failed; existing files are never overwritten.'
            return self.send(303,location=session.root)
    return Handler

def serve(output,port=0):
    session=LinkSession(output)
    if session.output.exists(): raise SteamError('Use a new output directory per sync attempt')
    server=HTTPServer(('127.0.0.1',port),handler_for(session)); server.timeout=1
    session.base='http://127.0.0.1:'+str(server.server_port)
    print(json.dumps(dict(url=session.base+session.root,expires_in_seconds=1800,output=str(session.output))),flush=True)
    try:
        while time.monotonic()-session.created<1800: server.handle_request()
    except KeyboardInterrupt: pass
    finally: server.server_close()
