'use strict';
const $=id=>document.getElementById(id);
let csrf=null,password=null,revision=0,remote=null,synced=null,busy=false,logged=false,timer=null;
const enc=new TextEncoder(),dec=new TextDecoder('utf-8',{fatal:true});
const keys=['shimix-trading-demo-v1','shimix-trading-bot-v4','shimix-academy-v1'];
const allowed=k=>keys.includes(k)||/^shimix-trading-(?:prefs|preferences|settings|academy|coach)(?:-[a-z0-9]+)*$/.test(k);
const to64=bytes=>{let s='';for(let i=0;i<bytes.length;i+=8192)s+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(s);};
const from64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
const unurl=s=>from64(s.replace(/-/g,'+').replace(/_/g,'/'));
const url64=x=>to64(new Uint8Array(x)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
function status(s){$('status').textContent=s;}
function lock(){password=null;csrf=null;remote=null;synced=null;logged=false;$('keys').replaceChildren();$('auto').checked=false;$('password').value='';if(timer)clearInterval(timer);timer=null;buttons();}
function buttons(){for(const id of ['logout','unlock','addKey','revoke'])$(id).disabled=!logged;for(const id of ['import','push','pull','download','auto'])$(id).disabled=!(logged&&password);$('openApp').hidden=!logged;}
async function api(path,method='GET',data,headers={}){
 const r=await fetch('/api'+path,{method,credentials:'same-origin',cache:'no-store',headers:{...(data===undefined?{}:{'Content-Type':'application/json'}),...(csrf?{'X-CSRF-Token':csrf}:{}),...headers},body:data===undefined?undefined:JSON.stringify(data)});
 const result=await r.json();if(!r.ok){if(r.status===401)lock();const error=Error(result.error||'Service indisponible.');error.status=r.status;throw error;}return result;
}
async function guard(fn){if(busy)return;busy=true;try{await fn();}catch(e){$('auto').checked=false;status(e.message);}finally{busy=false;buttons();}}
function serialize(c){const r=c.response;return{id:c.id,rawId:url64(c.rawId),type:c.type,clientExtensionResults:c.getClientExtensionResults(),authenticatorAttachment:c.authenticatorAttachment,response:r.attestationObject?{clientDataJSON:url64(r.clientDataJSON),attestationObject:url64(r.attestationObject),transports:r.getTransports?.()||[]}:{clientDataJSON:url64(r.clientDataJSON),authenticatorData:url64(r.authenticatorData),signature:url64(r.signature),userHandle:r.userHandle?url64(r.userHandle):undefined}};}
async function passkey(register){
 if(!navigator.credentials||!window.PublicKeyCredential)throw Error('Passkeys indisponibles sur ce navigateur.');
 const token=$('bootstrap').value,headers=token?{'X-Bootstrap-Token':token}:{};
 const options=await api('/auth/'+(register?'register':'login')+'/options','POST',{},headers);
 options.challenge=unurl(options.challenge);
 if(register){options.user.id=unurl(options.user.id);options.excludeCredentials=(options.excludeCredentials||[]).map(x=>({...x,id:unurl(x.id)}));}
 else if(options.allowCredentials)options.allowCredentials=options.allowCredentials.map(x=>({...x,id:unurl(x.id)}));
 const c=register?await navigator.credentials.create({publicKey:options}):await navigator.credentials.get({publicKey:options});
 const result=await api('/auth/'+(register?'register':'login')+'/verify','POST',serialize(c),headers);csrf=result.csrf;logged=true;$('bootstrap').value='';$('setup').hidden=true;
 const me=await api('/me');$('account').textContent=me.passkeys+' passkey(s) enregistrée(s). Ajoute une clé de secours avant de confier tes données au coffre.';
 await listKeys();status('Connexion réussie. Déverrouille maintenant tes sauvegardes.');buttons();
}
async function listKeys(){
 const {passkeys}=await api('/passkeys');$('keys').replaceChildren();
 for(const key of passkeys){const row=document.createElement('p'),label=document.createElement('span'),button=document.createElement('button');label.textContent='Passkey '+key.id.slice(0,10)+'… · '+new Date(key.createdAt).toLocaleDateString('fr-FR')+' ';button.textContent='Retirer cette passkey';button.disabled=passkeys.length<=1;button.onclick=()=>guard(async()=>{if(!confirm('Retirer cette passkey et déconnecter les autres sessions ? Vérifie que tu possèdes encore une autre passkey.'))return;await api('/passkeys/'+encodeURIComponent(key.id),'DELETE',{});await listKeys();status('Passkey retirée et autres sessions déconnectées.');});row.append(label,button);$('keys').append(row);}
}
function localData(){const data={};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(allowed(k))data[k]=JSON.parse(localStorage.getItem(k));}if(Object.keys(data).length)ShimixSecurity.entries(structuredClone(data));return data;}
const fingerprint=data=>JSON.stringify(Object.fromEntries(Object.entries(data).sort(([a],[b])=>a.localeCompare(b))));
async function derive(salt,iterations){const material=await crypto.subtle.importKey('raw',enc.encode(password),'PBKDF2',false,['deriveKey']);return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);}
async function encrypt(data){ShimixSecurity.entries(structuredClone(data));const salt=crypto.getRandomValues(new Uint8Array(16)),iv=crypto.getRandomValues(new Uint8Array(12)),iterations=600000;
 const clear=enc.encode(JSON.stringify({format:'shimix-local',version:1,exportedAt:new Date().toISOString(),data}));if(clear.length>2*1024*1024)throw Error('Sauvegarde trop volumineuse.');
 const cipher=await crypto.subtle.encrypt({name:'AES-GCM',iv},await derive(salt,iterations),clear);
 return{format:'shimix-encrypted-backup',version:1,kdf:'PBKDF2-SHA256',iterations,cipher:'AES-256-GCM',salt:to64(salt),iv:to64(iv),ciphertext:to64(new Uint8Array(cipher))};}
async function decrypt(o){
 if(o?.format!=='shimix-encrypted-backup'||o.version!==1||o.kdf!=='PBKDF2-SHA256'||o.cipher!=='AES-256-GCM'||![250000,600000].includes(o.iterations)||typeof o.ciphertext!=='string'||o.ciphertext.length>2900000)throw Error('Format de sauvegarde non reconnu.');
 try{const salt=from64(o.salt),iv=from64(o.iv);if(salt.length!==16||iv.length!==12)throw Error();const clear=await crypto.subtle.decrypt({name:'AES-GCM',iv},await derive(salt,o.iterations),from64(o.ciphertext));const payload=JSON.parse(dec.decode(clear));if(payload.format!=='shimix-local'||payload.version!==1)throw Error();ShimixSecurity.entries(payload.data);return payload.data;}catch{throw Error('Mot de passe incorrect ou sauvegarde invalide. Aucune donnée remplacée.');}
}
function apply(data){const entries=ShimixSecurity.entries(structuredClone(data)),before=new Map(entries.map(([k])=>[k,localStorage.getItem(k)]));try{for(const [k,v] of entries)localStorage.setItem(k,JSON.stringify(v));}catch(e){for(const [k,v] of before){if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v);}throw e;}}
async function refresh(){remote=await api('/vault');revision=remote.revision;$('comparison').textContent='Cet appareil : '+Object.keys(localData()).length+' rubrique(s). Coffre : '+(remote.envelope?'version '+revision:'aucune sauvegarde')+'. Choisis la copie à utiliser.';}
async function push(){const data=localData();if(!Object.keys(data).length)throw Error('Aucune donnée locale. Importe ta sauvegarde chiffrée.');const envelope=await encrypt(data);const result=await api('/vault','PUT',envelope,{'If-Match':'"'+revision+'"','Idempotency-Key':crypto.randomUUID()});revision=result.revision;synced=fingerprint(data);remote={revision,envelope};status('Copie chiffrée synchronisée, version '+revision+'.');}
async function pull({confirmFirst=true}={}){await refresh();if(!remote.envelope)throw Error('Le coffre est vide.');const data=await decrypt(remote.envelope);if(confirmFirst&&!confirm('Utiliser la copie du coffre sur cet appareil ? Exporte d’abord une sauvegarde chiffrée si tu veux garder ta copie locale.'))return;apply(data);synced=fingerprint(localData());status('Copie du coffre restaurée sur cet appareil.');}
async function tick(){if(!$('auto').checked||!password||!logged||busy||!synced)return;await guard(async()=>{const local=fingerprint(localData()),latest=await api('/vault');if(latest.revision!==revision){if(local!==synced)throw Error('Conflit entre appareils : tes deux copies sont conservées. Choisis la copie à utiliser.');const data=await decrypt(latest.envelope);apply(data);revision=latest.revision;remote=latest;synced=fingerprint(localData());status('Copie reçue de l’autre appareil, version '+revision+'.');}else if(local!==synced)await push();});}
$('login').onclick=()=>guard(()=>passkey(false));$('register').onclick=()=>guard(()=>passkey(true));$('addKey').onclick=()=>guard(()=>passkey(true));
$('logout').onclick=()=>guard(async()=>{try{await api('/auth/logout','POST',{});}finally{lock();status('Déconnecté. Les données locales restent sur cet appareil.');}});
$('revoke').onclick=()=>guard(async()=>{await api('/sessions/revoke-others','POST',{});status('Les autres sessions ont été déconnectées.');});
$('unlock').onclick=()=>guard(async()=>{const candidate=$('password').value;$('password').value='';if(candidate.length<12)throw Error('Utilise au moins 12 caractères.');password=candidate;try{await refresh();if(remote.envelope)await decrypt(remote.envelope);}catch(e){password=null;throw e;}status('Coffre déverrouillé. Choisis la copie à utiliser.');if(timer)clearInterval(timer);timer=setInterval(tick,15000);});
$('push').onclick=()=>guard(async()=>{if(!confirm('Envoyer la copie de cet appareil au coffre ? Les anciennes versions du coffre seront conservées.'))return;await push();});
$('pull').onclick=()=>guard(()=>pull());
$('import').onchange=()=>guard(async()=>{const f=$('import').files[0];try{if(!f)return;if(f.size>3000000)throw Error('Fichier trop volumineux.');const data=await decrypt(JSON.parse(await f.text()));if(!confirm('Importer cette sauvegarde sur cet appareil ? La copie du coffre reste inchangée.'))return;apply(data);synced=null;await refresh();status('Sauvegarde importée localement. Choisis ensuite de l’envoyer au coffre.');}finally{$('import').value='';}});
$('download').onclick=()=>guard(async()=>{await refresh();if(!remote.envelope)throw Error('Le coffre est vide.');await decrypt(remote.envelope);const url=URL.createObjectURL(new Blob([JSON.stringify(remote.envelope)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='SHIMIX-CHIFFRE-coffre-v'+revision+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);status('Fichier chiffré préparé. Vérifie son téléchargement.');});
$('auto').onchange=()=>{if($('auto').checked&&!synced){$('auto').checked=false;status('Choisis d’abord la copie locale ou celle du coffre.');}};
window.addEventListener('storage',tick);window.addEventListener('pagehide',lock);
api('/auth/status').then(s=>{$('register').hidden=s.enrolled;$('setup').hidden=s.enrolled;status(s.enrolled?'Connecte-toi avec ta passkey.':'Première utilisation : configure la passkey du propriétaire.');}).catch(e=>status(e.message));buttons();
