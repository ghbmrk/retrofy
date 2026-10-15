const OPENID = 'https://steamcommunity.com/openid/login';
const NS = 'http://specs.openid.net/auth/2.0';
const API = 'https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/';
const LIMIT = 8 * 1024 * 1024;
const encoder = new TextEncoder();
const security = {'cache-control':'no-store','referrer-policy':'no-referrer','x-content-type-options':'nosniff',
  'content-security-policy':"default-src 'self'; style-src 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"};
function response(body, status=200, headers={}) { return new Response(body,{status,headers:{...security,...headers}}); }
function redirect(url, cookie) { return response('',303,{location:url,...(cookie?{'set-cookie':cookie}:{})}); }
function escape(value) { return String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function b64(bytes) { return btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_'); }
function unb64(value) { return Uint8Array.from(atob(value.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0)); }
function random() { return b64(crypto.getRandomValues(new Uint8Array(32))); }
async function hash(value) { return b64(await crypto.subtle.digest('SHA-256',encoder.encode(value))); }
async function mac(value,secret) {
  const key=await crypto.subtle.importKey('raw',encoder.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  return b64(await crypto.subtle.sign('HMAC',key,encoder.encode(value)));
}
function equal(a,b) { if(a.length!==b.length)return false;let n=0;for(let i=0;i<a.length;i++)n|=a.charCodeAt(i)^b.charCodeAt(i);return n===0; }
async function sign(payload,secret) { const text=b64(encoder.encode(JSON.stringify(payload)));return text+'.'+await mac(text,secret); }
async function unsign(text,secret) {
  try { const [body,sig,...extra]=text.split('.');if(extra.length||!sig||!equal(sig,await mac(body,secret)))return null;
    const p=JSON.parse(new TextDecoder().decode(unb64(body)));return p.exp>Date.now()?p:null;
  } catch { return null; }
}
function cookie(request,name) { return (request.headers.get('cookie')||'').split(';').map(s=>s.trim()).find(s=>s.startsWith(name+'='))?.slice(name.length+1)||''; }
const stateCookie=value=>`__Host-retrofy-steam=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=600`;
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
async function bounded(remote,url,options={}) {
  const r=await remote(url,{...options,redirect:'error',signal:AbortSignal.timeout(20000)});
  if(!r.ok)throw Error('Steam request failed. Check the API key and library visibility, then try again.');
  const reader=r.body.getReader();let size=0,chunks=[];
  while(true){const {value,done}=await reader.read();if(done)break;size+=value.length;if(size>LIMIT){await reader.cancel();throw Error('Steam response exceeds the size limit.');}chunks.push(value);}
  const bytes=new Uint8Array(size);let at=0;for(const c of chunks){bytes.set(c,at);at+=c.length;}return new TextDecoder().decode(bytes);
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
async function read(bucket,key) { const item=await bucket.get(key);return item?item.json():null; }
function page({account,library,csrf,error,hasKey}) {
 const linked=!!account;const synced=!!library;const games=library?.games||[];
 const state=synced?'Library synced':linked?'Steam linked':'Connect Steam';
 const rows=games.map(g=>`<li><div><a target="_blank" rel="noreferrer" href="https://store.steampowered.com/app/${g.appid}/">${escape(g.name)}</a><small>${Math.round(g.playtime_minutes/60)} hours played</small></div><span>Unassessed</span></li>`).join('');
 return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Retrofy · Steam library</title>
<style>*{box-sizing:border-box}body{margin:0;background:#101a1a;color:#edf2e8;font:16px/1.6 system-ui,-apple-system,sans-serif}main{max-width:920px;margin:auto;padding:24px 20px 72px}header{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #354343;padding-bottom:20px;margin-bottom:42px}.brand{font-weight:800;font-size:24px;letter-spacing:-1px}.badge{font-size:12px;border:1px solid #45574a;padding:4px 10px;border-radius:30px;color:#bccebc}h1{font-size:clamp(34px,6vw,52px);line-height:1.1;letter-spacing:-2px;margin:14px 0 20px}h2{font-size:21px;margin:0 0 12px}.eyebrow{color:#b0c778;text-transform:uppercase;font-size:12px;letter-spacing:2px}.intro{max-width:600px;color:#bbc8be;font-size:18px}.panel{background:#1b2826;border:1px solid #394b43;border-radius:16px;padding:26px;margin-top:30px}.steps{display:flex;gap:16px;font-size:13px;color:#9cab9f;padding:0;list-style:none;margin:0 0 24px}.active{color:#cce694}a{color:#cce694}.button,button{display:inline-block;background:#d6ec9c;color:#132015;border:0;border-radius:8px;padding:14px 20px;font-size:16px;font-weight:700;text-decoration:none;cursor:pointer;text-align:center}button:focus-visible,a:focus-visible,input:focus-visible{outline:3px solid #fff;outline-offset:4px}input{width:100%;background:#101a1a;color:#edf2e8;border:1px solid #72826f;border-radius:6px;padding:13px;font:inherit;margin:8px 0 16px}label{display:block;font-size:14px}small,.muted{display:block;color:#adbaaf;font-size:13px}.error{border-left:3px solid #e8aa79;background:#33291f;padding:16px;margin:20px 0;color:#ffe2c1}ul.library{list-style:none;padding:0;margin:0}ul.library li{display:flex;justify-content:space-between;gap:12px;padding:18px 0;border-bottom:1px solid #35463f}li span{color:#adbaaf;font-size:12px;white-space:nowrap}.meta{display:flex;justify-content:space-between;gap:20px;align-items:center;margin-bottom:16px}footer{border-top:1px solid #354343;margin-top:36px;padding-top:20px;color:#9aab9f;font-size:13px}@media(max-width:520px){main{padding:18px 16px 44px}.panel{padding:20px}.button,button{width:100%}.meta{display:block}header{margin-bottom:30px}.steps{gap:10px;font-size:12px}}</style></head><body><main>
<header><div class="brand">retrofy<span style="color:#b0c778">.</span></div><span class="badge">Private connection</span></header>
<div class="eyebrow">Your games. A new frontier.</div><h1>Your Steam library,<br>ready for discovery.</h1><p class="intro">Connect from your phone. Bring your library into Retrofy to find candidates for native Chromatic adaptation.</p>
${error?`<div role="alert" class="error">${escape(error)}</div>`:''}
<section class="panel"><ol class="steps"><li class="active">01 · Sign in</li><li class="${linked?'active':''}">02 · Sync library</li><li class="${synced?'active':''}">03 · Assess games</li></ol>
<h2>${state}</h2>
${linked?`<p>Steam verified account <strong>${escape(account.steamid)}</strong>.</p><form action="/api/sync" method="post"><input type="hidden" name="csrf" value="${csrf}">
${hasKey?'':`<label>Steam Web API key<input type="password" name="key" autocomplete="off" required pattern="[0-9a-fA-F]{32}" maxlength="32" placeholder="Enter securely for this sync"></label><p class="muted">Steam sign-in does not grant library API access. <a href="https://steamcommunity.com/dev/apikey" target="_blank" rel="noreferrer">Get a key directly from Valve</a>, then enter it here. It is used for this request and is not saved.</p>`}
<button type="submit">${synced?'Refresh library':'Sync library'}</button></form>`:`<p>Continue to Valve to identify your account. Your Steam password and Steam Guard code stay with Steam.</p><a class="button" href="/steam/start" target="_top">Sign in on Steam →</a><p class="muted">No Mac, local server, or Steam installation required.</p>`}
</section>
${synced?`<section class="panel"><div class="meta"><h2>${games.length} games imported</h2><a href="/api/library" download="retrofy-library.json">Download snapshot</a></div><label>Find a game<input id="filter" type="search" placeholder="Search your library" autocomplete="off"></label><ul class="library" id="games">${rows}</ul><p id="empty" hidden>No matching games.</p><small>Updated ${escape(library.synced_at)}. Library metadata only; nothing has been converted.</small></section><script>document.querySelector('#filter').addEventListener('input',e=>{let n=0;for(const row of document.querySelectorAll('#games li')){row.hidden=!row.textContent.toLowerCase().includes(e.target.value.toLowerCase());if(!row.hidden)n++}document.querySelector('#empty').hidden=n>0});</script>`:''}
<footer>Your account and snapshot are stored privately in hosted storage. API keys are not stored. Steam visibility rules still apply.<br>Imported games remain unassessed. Ownership does not establish adaptation rights or GBC compatibility.</footer>
</main></body></html>`;
}
async function handle(request,env,remote=fetch) {
 const url=new URL(request.url);const user=request.headers.get('oai-authenticated-user-id');
 if(url.pathname==='/health')return response(JSON.stringify({service:'retrofy-steam',ready:!!env.SESSION_SECRET&&!!env.BUCKET,mac_required:false}),200,{'content-type':'application/json'});
 if(!user)return response('<a href="/signin-with-chatgpt?return_to=%2F" target="_top">Sign in to your private Retrofy connection</a>',401,{'content-type':'text/html;charset=utf-8'});
 if(!env.SESSION_SECRET||!env.BUCKET)return response('Hosted connection is not configured yet.',503);
 const owner=await hash(user),prefix='users/'+owner+'/';const secret=env.SESSION_SECRET;
 const csrf=await mac('sync:'+owner,secret);
 if(url.pathname==='/steam/start'&&request.method==='GET'){
   const state=random();const data=await sign({owner,state,exp:Date.now()+600000},secret);
   const callback=url.origin+'/steam/return?state='+state;
   const params=new URLSearchParams({'openid.ns':NS,'openid.mode':'checkid_setup','openid.return_to':callback,'openid.realm':url.origin+'/',
     'openid.identity':NS+'/identifier_select','openid.claimed_id':NS+'/identifier_select'});
   return redirect(OPENID+'?'+params,stateCookie(data));
 }
 if(url.pathname==='/steam/return'&&request.method==='GET'){
   const state=await unsign(cookie(request,'__Host-retrofy-steam'),secret);
   if(!state||state.owner!==owner||url.searchParams.getAll('state').length!==1||url.searchParams.get('state')!==state.state)throw Error('This sign-in expired or belongs to another session. Start again.');
   const expected=url.origin+'/steam/return?state='+state.state;
   const steamid=assertion(url.searchParams,expected);
   const payload=new URLSearchParams([...url.searchParams].filter(([k])=>k.startsWith('openid.')));payload.set('openid.mode','check_authentication');
   const result=await bounded(remote,OPENID,{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:payload.toString()});
   const verified=Object.fromEntries(result.trim().split('\n').map(line=>{const i=line.indexOf(':');return [line.slice(0,i),line.slice(i+1).trim()];}));
   if(verified.is_valid!=='true'||verified.ns!==NS)throw Error('Valve could not verify this sign-in.');
   const existing=await read(env.BUCKET,prefix+'account.json');
   if(existing&&existing.steamid!==steamid)throw Error('A different Steam account is already linked. Account switching is not supported yet.');
   await env.BUCKET.put(prefix+'account.json',JSON.stringify({steamid,linked_at:new Date().toISOString(),verified_by:'Steam OpenID'}));
   return redirect('/',stateCookie(''));
 }
 if(url.pathname==='/api/sync'&&request.method==='POST'){
   if(request.headers.get('origin')!==url.origin)throw Error('Cross-origin sync was refused.');
   if(!request.headers.get('content-type')?.startsWith('application/x-www-form-urlencoded'))throw Error('Invalid form.');
   const raw=await request.text();if(raw.length>2048)throw Error('Form is too large.');const form=new URLSearchParams(raw);
   if(form.getAll('csrf').length!==1||!equal(form.get('csrf')||'',csrf))throw Error('Invalid sync token. Reload the page.');
   const account=await read(env.BUCKET,prefix+'account.json');if(!account)throw Error('Link Steam before syncing your library.');
   const key=env.STEAM_WEB_API_KEY||form.get('key')||'';if(!/^[a-fA-F0-9]{32}$/.test(key))throw Error('A valid Steam Web API key is required for library access.');
   const query=new URLSearchParams({key,steamid:account.steamid,include_appinfo:'1',include_played_free_games:'1',format:'json'});
   const text=await bounded(remote,API+'?'+query);let document;try{document=JSON.parse(text);}catch{throw Error('Steam returned an invalid library response.');}
   const library=normalize(document,account.steamid);await env.BUCKET.put(prefix+'library.json',JSON.stringify(library));return redirect('/');
 }
 if(url.pathname==='/api/library'&&request.method==='GET'){
   const library=await read(env.BUCKET,prefix+'library.json');if(!library)return response('No snapshot yet.',404);
   return response(JSON.stringify(library,null,2),200,{'content-type':'application/json','content-disposition':'attachment; filename="retrofy-library.json"'});
 }
 if(url.pathname==='/'&&request.method==='GET'){
   const account=await read(env.BUCKET,prefix+'account.json'),library=await read(env.BUCKET,prefix+'library.json');
   return response(page({account,library,csrf,hasKey:!!env.STEAM_WEB_API_KEY}),200,{'content-type':'text/html;charset=utf-8'});
 }
 return response('Not found',404);
}
export default {async fetch(request,env){try{return await handle(request,env);}catch(error){
  // Deliberately do not log exception objects or request URLs: keys/assertions may be present.
  const message=error instanceof TypeError||error?.name==='TimeoutError'?'Steam could not be reached. Try again shortly.':String(error.message||'Connection failed.');
  let account=null,library=null,csrf='';
  try { const user=request.headers.get('oai-authenticated-user-id');if(user&&env.BUCKET&&env.SESSION_SECRET){const owner=await hash(user);account=await read(env.BUCKET,'users/'+owner+'/account.json');library=await read(env.BUCKET,'users/'+owner+'/library.json');csrf=await mac('sync:'+owner,env.SESSION_SECRET);} } catch {}
  return response(page({error:message,account,library,csrf,hasKey:!!env.STEAM_WEB_API_KEY}),400,{'content-type':'text/html;charset=utf-8'});
}}};
export {handle,assertion,normalize,sign,unsign,hash,mac};
