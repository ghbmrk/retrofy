const OPENID='https://steamcommunity.com/openid/login';
const NS='http://specs.openid.net/auth/2.0';
const API='https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/';
const LIMIT=8*1024*1024, LINK_TTL=3600000;
const encoder=new TextEncoder();
class Fault extends Error { constructor(message,status=400){super(message);this.status=status;} }
const security={'cache-control':'no-store','referrer-policy':'same-origin','x-content-type-options':'nosniff',
 'content-security-policy':"default-src 'none'; style-src 'self'; script-src 'none'; connect-src 'none'; img-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'",
 'permissions-policy':'camera=(), microphone=(), geolocation=(), payment=()',
 'strict-transport-security':'max-age=31536000'};
function response(body,status=200,headers={}) {return new Response(body,{status,headers:{...security,...headers}});}
function redirect(url,cookies=[]) {const r=response('',303,{location:url});for(const c of cookies)r.headers.append('set-cookie',c);return r;}
function escape(value){return String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function b64(value){return btoa(String.fromCharCode(...new Uint8Array(value))).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');}
function unb64(value){return Uint8Array.from(atob(value.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));}
function random(){return b64(crypto.getRandomValues(new Uint8Array(32)));}
async function hash(value){return b64(await crypto.subtle.digest('SHA-256',encoder.encode(value)));}
async function hmacKey(secret){return crypto.subtle.importKey('raw',encoder.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign','verify']);}
async function mac(value,secret){return b64(await crypto.subtle.sign('HMAC',await hmacKey(secret),encoder.encode(value)));}
async function sign(payload,secret){const body=b64(encoder.encode(JSON.stringify(payload)));return body+'.'+await mac(body,secret);}
async function unsign(text,secret){try{const [body,sig,...extra]=text.split('.');if(extra.length||!sig||!await crypto.subtle.verify('HMAC',await hmacKey(secret),unb64(sig),encoder.encode(body)))return null;const p=JSON.parse(new TextDecoder().decode(unb64(body)));return p.exp>Date.now()?p:null;}catch{return null;}}
function cookie(request,name){return (request.headers.get('cookie')||'').split(';').map(v=>v.trim()).find(v=>v.startsWith(name+'='))?.slice(name.length+1)||'';}
function setCookie(name,value,seconds){return `__Host-retrofy-${name}=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${seconds}`;}
async function aesKey(secret){const raw=await crypto.subtle.digest('SHA-256',encoder.encode('retrofy-link-v2:'+secret));return crypto.subtle.importKey('raw',raw,'AES-GCM',false,['encrypt','decrypt']);}
async function seal(payload,secret,scope){const iv=crypto.getRandomValues(new Uint8Array(12));const encrypted=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:encoder.encode(scope)},await aesKey(secret),encoder.encode(JSON.stringify(payload)));return b64(iv)+'.'+b64(encrypted);}
async function unseal(value,secret,scope){try{const [iv,data,...extra]=value.split('.');if(extra.length)return null;const text=await crypto.subtle.decrypt({name:'AES-GCM',iv:unb64(iv),additionalData:encoder.encode(scope)},await aesKey(secret),unb64(data));const p=JSON.parse(new TextDecoder().decode(text));return p.exp>Date.now()?p:null;}catch{return null;}}
async function token(owner,purpose,secret){return sign({owner,purpose,exp:Date.now()+600000},secret);}
async function form(request,origin,owner,purpose,secret){
 if(request.headers.get('origin')!==origin||request.headers.get('sec-fetch-site')==='cross-site')throw new Fault('Cross-origin request refused.',403);
 if(!request.headers.get('content-type')?.startsWith('application/x-www-form-urlencoded'))throw new Fault('Invalid form type.',415);
 const text=await requestBody(request,2048);const f=new URLSearchParams(text);
 if([...f.keys()].some(k=>k!=='csrf')||f.getAll('csrf').length!==1)throw new Fault('This endpoint accepts no credentials or extra fields.',400);
 const p=await unsign(f.get('csrf')||'',secret);if(!p||p.owner!==owner||p.purpose!==purpose)throw new Fault('Form expired. Reload and try again.',403);return f;
}
async function requestBody(request,limit){if(Number(request.headers.get('content-length')||0)>limit)throw new Fault('Request too large.',413);if(!request.body)return '';return streamText(request.body,limit);}
async function streamText(body,limit){const reader=body.getReader();let total=0,parts=[];while(true){const {value,done}=await reader.read();if(done)break;total+=value.length;if(total>limit){await reader.cancel();throw new Fault('Response or request too large.',413);}parts.push(value);}const b=new Uint8Array(total);let i=0;for(const p of parts){b.set(p,i);i+=p.length;}return new TextDecoder().decode(b);}
async function valve(remote,url,options={}){
 const u=new URL(url);if(!((u.origin==='https://steamcommunity.com'&&u.pathname==='/openid/login'&&!u.search)||(u.origin==='https://api.steampowered.com'&&u.pathname==='/IPlayerService/GetOwnedGames/v1/')))throw new Fault('Refused external destination.',502);
 let r;try{r=await remote(url,{...options,redirect:'error',signal:AbortSignal.timeout(15000)});}catch{throw new Fault('Valve could not be reached. Try again later.',502);}
 if(!r.ok)throw new Fault('Valve rejected the request. Check service configuration or library visibility.',502);return streamText(r.body,LIMIT);
}
async function read(bucket,key){const obj=await bucket.get(key);return obj?obj.json():null;}
async function generation(bucket,prefix){for(let n=0;n<5;n++){const existing=await read(bucket,prefix+'generation.json');if(existing)return existing.id;const id=random();const result=await bucket.put(prefix+'generation.json',JSON.stringify({id}),{onlyIf:{etagDoesNotMatch:'*'}});if(result)return id;}throw new Fault('Connection busy. Try again.',503);}
async function rate(bucket,prefix,name,max,window){
 const key=prefix+'rate-'+name+'.json';for(let n=0;n<8;n++){const obj=await bucket.get(key);let row=obj?await obj.json():null;const now=Date.now();if(!row||row.until<=now)row={count:0,until:now+window};if(row.count>=max)throw new Fault('Too many attempts. Please wait and try again.',429);
 const result=await bucket.put(key,JSON.stringify({count:row.count+1,until:row.until}),{onlyIf:obj?{etagMatches:obj.etag}:{etagDoesNotMatch:'*'}});if(result)return;}throw new Fault('Connection busy. Try again.',503);
}
async function consume(bucket,prefix,state){const key=prefix+'pending.json';const obj=await bucket.get(key);if(!obj)throw new Fault('Login already used or expired.',403);const row=await obj.json();if(row.used||row.state!==state||row.exp<=Date.now())throw new Fault('Login already used or expired.',403);const result=await bucket.put(key,JSON.stringify({used:true,exp:row.exp}),{onlyIf:{etagMatches:obj.etag}});if(!result)throw new Fault('Login already used or expired.',403);return row;}
async function linked(request,env,owner,prefix,origin){const p=await unseal(cookie(request,'__Host-retrofy-link'),env.SESSION_SECRET,origin+':'+owner);if(!p)return null;const g=await read(env.BUCKET,prefix+'generation.json');return g&&p.generation===g.id?{steamid:p.steamid}:null;}
function assertion(params,expected,now=Date.now()) {
  for(const k of ['ns','mode','op_endpoint','claimed_id','identity','return_to','response_nonce','assoc_handle','signed','sig'])
    if(!params.get('openid.'+k)||params.getAll('openid.'+k).length!==1)throw Error('Incomplete Steam assertion. Start sign-in again.');
  if(params.get('openid.ns')!==NS||params.get('openid.mode')!=='id_res'||params.get('openid.op_endpoint')!==OPENID||params.get('openid.return_to')!==expected)
    throw Error('Steam sign-in was cancelled or the callback did not match.');
  const claimed=params.get('openid.claimed_id');const id=claimed.match(/^https:\/\/steamcommunity\.com\/openid\/id\/(\d{17})$/)?.[1];
  if(!id||BigInt(id)<=76561197960265728n||BigInt(id)>76561202255233023n||claimed!==params.get('openid.identity'))throw Error('Invalid Steam identity.');
  const signed=new Set(params.get('openid.signed').split(','));
  if(!['op_endpoint','claimed_id','identity','return_to','response_nonce','assoc_handle'].every(k=>signed.has(k)))throw Error('Unsigned Steam identity fields.');
  const nonce=params.get('openid.response_nonce');const stamp=/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ/.test(nonce)?Date.parse(nonce.slice(0,20)):NaN;
  if(nonce.length>256||!Number.isFinite(stamp)||Math.abs(now-stamp)>300000)throw Error('Steam sign-in expired. Start again.');
  return id;
}
function normalize(document,steamid) {
  const r=document?.response;
  if(!r||!Number.isInteger(r.game_count)||r.game_count<0||(!Array.isArray(r.games)&&r.game_count!==0))throw Error('Steam did not expose this library. Check Game details visibility; sign-in alone cannot bypass it.');
  const games=r.games||[];if(games.length!==r.game_count)throw Error('Incomplete library response. No partial snapshot was saved.');
  const seen=new Set();const clean=games.map(g=>{
    if(!Number.isInteger(g.appid)||g.appid<=0||seen.has(g.appid)||typeof g.name!=='string'||g.name.length>1024||!Number.isInteger(g.playtime_forever??0)||(g.playtime_forever??0)<0)throw Error('Invalid game metadata.');
    seen.add(g.appid);return {appid:g.appid,name:g.name,playtime_minutes:g.playtime_forever??0,compatibility:'unassessed'};
  }).sort((a,b)=>a.name.localeCompare(b.name));
  return {schema:1,steamid,synced_at:new Date().toISOString(),games:clean,source:'Valve GetOwnedGames',adaptation_rights_verified:false,files_accessed:false};
}

const CSS='*{box-sizing:border-box}body{margin:0;background:#101a1a;color:#edf2e8;font:16px/1.6 system-ui,-apple-system,sans-serif}main{max-width:920px;margin:auto;padding:24px 20px 72px}header{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #354343;padding-bottom:20px;margin-bottom:42px}.brand{font-weight:800;font-size:24px;letter-spacing:-1px}.badge{font-size:12px;border:1px solid #45574a;padding:4px 10px;border-radius:30px;color:#bccebc}h1{font-size:clamp(34px,6vw,52px);line-height:1.1;letter-spacing:-2px;margin:14px 0 20px}h2{font-size:21px;margin:0 0 12px}.eyebrow{color:#b0c778;text-transform:uppercase;font-size:12px;letter-spacing:2px}.intro{max-width:600px;color:#bbc8be;font-size:18px}.panel{background:#1b2826;border:1px solid #394b43;border-radius:16px;padding:26px;margin-top:30px}.steps{display:flex;gap:16px;font-size:13px;color:#9cab9f;padding:0;list-style:none;margin:0 0 24px}.active{color:#cce694}a{color:#cce694}.button,button{display:inline-block;background:#d6ec9c;color:#132015;border:0;border-radius:8px;padding:14px 20px;font-size:16px;font-weight:700;text-decoration:none;cursor:pointer;text-align:center}button:disabled{opacity:.45;cursor:not-allowed}.secondary{background:transparent;color:#cce694;border:1px solid #72826f;margin-top:20px;font-size:13px}button:focus-visible,a:focus-visible,input:focus-visible{outline:3px solid #fff;outline-offset:4px}input{width:100%;background:#101a1a;color:#edf2e8;border:1px solid #72826f;border-radius:6px;padding:13px;font:inherit;margin:8px 0 16px}label{display:block;font-size:14px}small,.muted{display:block;color:#adbaaf;font-size:13px}.error{border-left:3px solid #e8aa79;background:#33291f;padding:16px;margin:20px 0;color:#ffe2c1}ul.library{list-style:none;padding:0;margin:0}ul.library li{display:flex;justify-content:space-between;gap:12px;padding:18px 0;border-bottom:1px solid #35463f}li span{color:#adbaaf;font-size:12px;white-space:nowrap}.meta{display:flex;justify-content:space-between;gap:20px;align-items:center;margin-bottom:16px}footer{border-top:1px solid #354343;margin-top:36px;padding-top:20px;color:#9aab9f;font-size:13px}@media(max-width:520px){main{padding:18px 16px 44px}.panel{padding:20px}.button,button{width:100%}.meta{display:block}header{margin-bottom:30px}.steps{gap:10px;font-size:12px}} .accent{color:#b0c778}';
function page({account,library,csrf,error,hasKey,linkCsrf,forgetCsrf}) {
 const linked=!!account;const synced=!!library;const games=library?.games||[];
 const state=synced?'Library synced':linked?'Steam linked':'Connect Steam';
 const rows=games.map(g=>`<li><div><a target="_blank" rel="noreferrer" href="https://store.steampowered.com/app/${g.appid}/">${escape(g.name)}</a><small>${Math.round(g.playtime_minutes/60)} hours played</small></div><span>Unassessed</span></li>`).join('');
 return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Retrofy · Steam library</title>
<link rel="stylesheet" href="/assets/style.css"></head><body><main>
<header><div class="brand">retrofy<span class="accent">.</span></div><span class="badge">Private connection</span></header>
<div class="eyebrow">Your games. A new frontier.</div><h1>Your Steam library,<br>ready for discovery.</h1><p class="intro">Connect from your phone. Review your Steam library without giving Retrofy your password or personal API key.</p>
${error?`<div role="alert" class="error">${escape(error)}</div>`:''}
<section class="panel"><ol class="steps"><li class="active">01 · Sign in</li><li class="${linked?'active':''}">02 · Sync library</li><li class="${synced?'active':''}">03 · Assess games</li></ol>
<h2>${state}</h2>
${linked?`<p>Steam verified account <strong>${escape(account.steamid)}</strong>. The link expires automatically after one hour.</p><form action="/api/sync" method="post"><input type="hidden" name="csrf" value="${csrf}">
${hasKey?'':`<p class="muted">Library sync is unavailable until the service operator configures Steam API access. Retrofy will never ask for your personal API key.</p>`}
<button type="submit" ${hasKey?'':'disabled'}>${synced?'Refresh library':'Sync library'}</button></form>`:`<p>Continue to Valve to identify your account. Your Steam password and Steam Guard code stay with Steam.</p><form action="/steam/start" method="post"><input type="hidden" name="csrf" value="${linkCsrf}"><button type="submit">Sign in on Steam →</button></form><p class="muted">No Mac, local server, or Steam installation required.</p>`}
<form action="/api/forget" method="post"><input type="hidden" name="csrf" value="${forgetCsrf}"><button class="secondary" type="submit">Unlink Steam and clear saved game data</button></form></section>
${synced?`<section class="panel"><div class="meta"><h2>${games.length} games imported</h2><span class="muted">Fetched for this response only</span></div><ul class="library" id="games">${rows}</ul><small>Updated ${escape(library.synced_at)}. Library metadata only; nothing has been converted.</small></section>`:''}
<footer>This version does not save Steam library data. Pseudonymous rate counters and revocation metadata remain on the server. The encrypted, HTTP-only account link expires after one hour. Steam visibility rules still apply.<br>Imported games remain unassessed. Ownership does not establish adaptation rights or GBC compatibility.</footer>
</main></body></html>`;
}
async function view(request,env,owner,prefix,error,library,status=200){
 const account=await linked(request,env,owner,prefix,env.SITE_ORIGIN);
 return response(page({account,library,error,hasKey:!!env.STEAM_WEB_API_KEY,
 csrf:await token(owner,'sync',env.SESSION_SECRET),linkCsrf:await token(owner,'link',env.SESSION_SECRET),forgetCsrf:await token(owner,'forget',env.SESSION_SECRET)}),status,{'content-type':'text/html;charset=utf-8'});
}
async function handle(request,env,remote=fetch){
 const url=new URL(request.url);
 if(url.origin!==env.SITE_ORIGIN||url.protocol!=='https:')return response('Unexpected origin.',421);
 if(url.pathname==='/health')return response(JSON.stringify({service:'retrofy-steam',security_revision:2,ready:!!env.SESSION_SECRET&&!!env.BUCKET,library_sync_configured:!!env.STEAM_WEB_API_KEY,personal_keys_accepted:false,library_storage:false,mac_required:false}),200,{'content-type':'application/json'});
 const user=request.headers.get('oai-authenticated-user-id');if(!user)return response('<a href="/signin-with-chatgpt?return_to=%2F" target="_top">Sign in to your private Retrofy connection</a>',401,{'content-type':'text/html;charset=utf-8'});
 if(!env.SESSION_SECRET||!env.BUCKET)return response('Hosted connection not configured.',503);
 const owner=await hash(user),prefix='users/'+owner+'/';
 if(url.pathname==='/assets/style.css'&&request.method==='GET')return response(CSS,200,{'content-type':'text/css;charset=utf-8'});
 if(request.method==='POST'&&url.pathname==='/steam/start'){
  await form(request,url.origin,owner,'link',env.SESSION_SECRET);await rate(env.BUCKET,prefix,'login',5,600000);
  const state=random(),exp=Date.now()+600000,g=await generation(env.BUCKET,prefix);
  await env.BUCKET.put(prefix+'pending.json',JSON.stringify({state,exp,generation:g}));
  const value=await sign({owner,state,exp},env.SESSION_SECRET);const callback=url.origin+'/steam/return?state='+state;
  const p=new URLSearchParams({'openid.ns':NS,'openid.mode':'checkid_setup','openid.return_to':callback,'openid.realm':url.origin+'/',
    'openid.identity':NS+'/identifier_select','openid.claimed_id':NS+'/identifier_select'});
  return redirect(OPENID+'?'+p,[setCookie('steam',value,600)]);
 }
 if(request.method==='GET'&&url.pathname==='/steam/return'){
  if(url.search.length>16384)throw new Fault('Oversized callback.',413);
  await rate(env.BUCKET,prefix,'callback',10,600000);
  const state=await unsign(cookie(request,'__Host-retrofy-steam'),env.SESSION_SECRET);
  if(!state||state.owner!==owner||url.searchParams.getAll('state').length!==1||url.searchParams.get('state')!==state.state)throw new Fault('Login expired or belongs to another session.',403);
  const steamid=assertion(url.searchParams,url.origin+'/steam/return?state='+state.state);
  // Atomic conditional write: exactly one callback can consume a pending flow.
  const pending=await consume(env.BUCKET,prefix,state.state);
  const g=await read(env.BUCKET,prefix+'generation.json');if(!g||pending.generation!==g.id)throw new Fault('Connection was revoked.',403);
  const payload=new URLSearchParams([...url.searchParams].filter(([k])=>k.startsWith('openid.')));payload.set('openid.mode','check_authentication');
  const text=await valve(remote,OPENID,{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:payload.toString()});
  const verified=Object.fromEntries(text.trim().split('\n').map(line=>{const i=line.indexOf(':');return [line.slice(0,i),line.slice(i+1).trim()];}));
  if(verified.is_valid!=='true'||verified.ns!==NS)throw new Fault('Valve could not verify this sign-in.',403);
  const finalGeneration=await read(env.BUCKET,prefix+'generation.json');if(finalGeneration?.id!==g.id)throw new Fault('Connection was revoked.',403);
  const value=await seal({steamid,generation:g.id,exp:Date.now()+LINK_TTL},env.SESSION_SECRET,url.origin+':'+owner);
  return redirect('/',[setCookie('steam','',0),setCookie('link',value,3600)]);
 }
 if(request.method==='POST'&&url.pathname==='/api/sync'){
  await form(request,url.origin,owner,'sync',env.SESSION_SECRET);await rate(env.BUCKET,prefix,'sync',6,3600000);
  const account=await linked(request,env,owner,prefix,url.origin);if(!account)throw new Fault('Sign in on Steam before syncing.',403);
  const key=env.STEAM_WEB_API_KEY;if(!key||!/^[a-fA-F0-9]{32}$/.test(key))throw new Fault('Library sync is unavailable: the service operator must configure Steam API access. Never submit a personal key.',503);
  const p=new URLSearchParams({key,steamid:account.steamid,include_appinfo:'1',include_played_free_games:'1',format:'json'});
  const text=await valve(remote,API+'?'+p);let parsed;try{parsed=JSON.parse(text);}catch{throw new Fault('Invalid library response.',502);}
  const library=normalize(parsed,account.steamid);
  // No library, playtime, SteamID or API key is persisted server-side.
  return view(request,env,owner,prefix,null,library);
 }
 if(request.method==='POST'&&url.pathname==='/api/forget'){
  await form(request,url.origin,owner,'forget',env.SESSION_SECRET);
  // Revoke all outstanding cookies before deleting pending and legacy personal records.
  await env.BUCKET.put(prefix+'generation.json',JSON.stringify({id:random()}));
  await env.BUCKET.delete([prefix+'pending.json',prefix+'account.json',prefix+'library.json']);
  return redirect('/',[setCookie('steam','',0),setCookie('link','',0)]);
 }
 if(url.pathname==='/'&&request.method==='GET')return view(request,env,owner,prefix);
 return response('Not found',404);
}
export default {async fetch(request,env){try{return await handle(request,env);}catch(error){
 // Never log URLs, callback assertions, exception objects, keys or library responses.
 const status=error instanceof Fault?error.status:400;
 const safe=error instanceof Fault?error.message:'Connection could not be completed. Start again.';
 try{const user=request.headers.get('oai-authenticated-user-id');if(user&&env.BUCKET&&env.SESSION_SECRET&&new URL(request.url).origin===env.SITE_ORIGIN){const owner=await hash(user);return await view(request,env,owner,'users/'+owner+'/',safe,null,status);}}catch{}
 return response('Connection unavailable.',503);
}}};
export {handle,assertion,normalize,sign,unsign,hash,mac,seal,unseal,token,consume,rate};
