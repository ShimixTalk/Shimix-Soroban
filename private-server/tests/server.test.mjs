import test from 'node:test';
import assert from 'node:assert/strict';
import {randomBytes,randomUUID} from 'node:crypto';
import {createApplication,configuration,validateEnvelope} from '../server.mjs';
import {openDatabase,digest} from '../store.mjs';
const bootstrap='test-only-bootstrap-token-at-least-32-characters';
const envelope=()=>({format:'shimix-encrypted-backup',version:1,kdf:'PBKDF2-SHA256',iterations:600000,cipher:'AES-256-GCM',salt:randomBytes(16).toString('base64'),iv:randomBytes(12).toString('base64'),ciphertext:randomBytes(100).toString('base64')});
async function fixture(fn){
 let now=Date.now();const config=configuration({SHIMIX_ORIGIN:'http://localhost',SHIMIX_BOOTSTRAP_TOKEN:bootstrap});
 const db=await openDatabase({localFile:':memory:'});const app=await createApplication(config,{db,clock:()=>now});
 await new Promise(r=>app.server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${app.server.address().port}`;config.origin=base;
 const session=await app.store.newSession(now);
 const request=(path,{method='GET',data,auth=true,origin=base,headers={}}={})=>fetch(base+path,{method,redirect:'manual',headers:{...(auth?{cookie:'shimix-dev-session='+session.token,'X-CSRF-Token':session.csrf}:{}),Origin:origin,...(data===undefined?{}:{'Content-Type':'application/json'}),...headers},body:data===undefined?undefined:JSON.stringify(data)});
 try{await fn({app,request,session,advance:ms=>now+=ms});}finally{await app.close();}
}
test('production rejects HTTP, missing configuration, and volatile DB',async()=>{
 assert.throws(()=>configuration({}));assert.throws(()=>configuration({NODE_ENV:'production',SHIMIX_ORIGIN:'http://localhost',SHIMIX_BOOTSTRAP_TOKEN:bootstrap}));
 await assert.rejects(()=>openDatabase({production:true,localFile:':memory:'}));
 await assert.rejects(()=>openDatabase({production:true,url:'postgres://localhost/shimix?sslmode=disable'}));
});
test('private routes and original trading app require a session',async()=>fixture(async({request})=>{
 assert.equal((await request('/api/vault',{auth:false})).status,401);
 assert.equal((await request('/trading/index.html',{auth:false})).status,302);
 assert.equal((await request('/trading/index.html')).status,200);
 assert.equal((await request('/private/index.html',{auth:false})).status,200);
 assert.equal((await request('/private/../../private-server/.env')).status,404);
}));
test('CSRF and foreign origin block writes',async()=>fixture(async({request})=>{
 assert.equal((await request('/api/vault',{method:'PUT',data:envelope(),origin:'https://attacker.example'})).status,403);
 assert.equal((await request('/api/vault',{method:'PUT',data:envelope(),headers:{'X-CSRF-Token':'wrong'}})).status,403);
}));
test('JSON content type and malformed envelopes rejected',async()=>fixture(async({request})=>{
 assert.equal((await request('/api/auth/login/options',{method:'POST'})).status,415);
 assert.throws(()=>validateEnvelope({...envelope(),cipher:'none'}));assert.throws(()=>validateEnvelope({...envelope(),iterations:1}));assert.throws(()=>validateEnvelope({...envelope(),extra:'secret'}));
}));
test('vault revision compare-and-swap and idempotency preserve both versions',async()=>fixture(async({request})=>{
 const first=envelope(),second=envelope(),key=randomUUID();
 const write=(data,revision,key)=>request('/api/vault',{method:'PUT',data,headers:{'If-Match':`"${revision}"`,'Idempotency-Key':key}});
 assert.equal((await write(first,0,key)).status,200);
 const replay=await write(first,0,key);assert.equal((await replay.json()).replayed,true);
 assert.equal((await write(second,0,randomUUID())).status,409);
 assert.equal((await write(second,1,key)).status,409);
 assert.equal((await write(second,1,randomUUID())).status,200);
 const latest=await(await request('/api/vault')).json();assert.equal(latest.revision,2);assert.deepEqual(latest.envelope,second);
}));
test('parallel writes cannot overwrite a revision',async()=>fixture(async({request})=>{
 const results=await Promise.all([1,2].map(()=>request('/api/vault',{method:'PUT',data:envelope(),headers:{'If-Match':'"0"','Idempotency-Key':randomUUID()}})));
 assert.deepEqual(results.map(r=>r.status).sort(),[200,409]);
}));
test('session cookies stored only as hashes and logout revokes',async()=>fixture(async({app,request,session})=>{
 const rows=await app.db.query('SELECT * FROM sessions');assert.equal(rows[0].id,digest(session.token));assert.equal(rows[0].csrf,digest(session.csrf));
 assert.equal((await request('/api/auth/logout',{method:'POST',data:{}})).status,200);
 assert.equal((await request('/api/vault')).status,401);
}));
test('idle sessions expire and sensitive actions require recent login',async()=>fixture(async({request,advance})=>{
 advance(301000);assert.equal((await request('/api/sessions/revoke-others',{method:'POST',data:{}})).status,403);
 advance(1801000);assert.equal((await request('/api/vault')).status,401);
}));
test('challenge expires and can be consumed only once',async()=>fixture(async({app,advance})=>{
 const now=Date.now();await app.store.challenge('flow','login','challenge','login',now);
 await app.store.consumeChallenge('flow','login',now);await assert.rejects(()=>app.store.consumeChallenge('flow','login',now));
 await app.store.challenge('expired','login','challenge','login',now);await assert.rejects(()=>app.store.consumeChallenge('expired','login',now+120001));
}));
test('bootstrap enrollment closes atomically after first key',async()=>fixture(async({app,request})=>{
 assert.equal((await request('/api/auth/register/options',{method:'POST',data:{},auth:false})).status,401);
 const c=n=>({credential:{id:n,publicKey:randomBytes(32),counter:0,transports:[]}});
 const results=await Promise.allSettled([app.store.register(c('first'),{bootstrap:true,now:Date.now()}),app.store.register(c('second'),{bootstrap:true,now:Date.now()})]);
 assert.equal(results.filter(x=>x.status==='fulfilled').length,1);
 assert.equal((await request('/api/auth/register/options',{method:'POST',data:{},auth:false,headers:{'X-Bootstrap-Token':bootstrap}})).status,401);
}));
test('rate limiter stops repeated login attempts',async()=>fixture(async({request})=>{
 let response;for(let i=0;i<61;i++)response=await request('/api/auth/login/options',{method:'POST',data:{},auth:false});assert.equal(response.status,429);
}));
test('API responses cannot be cached or framed; passkey options require verification',async()=>fixture(async({request})=>{
 const r=await request('/api/auth/login/options',{method:'POST',data:{},auth:false});const data=await r.json();assert.equal(data.userVerification,'required');assert.equal(r.headers.get('cache-control'),'no-store');assert.equal(r.headers.get('x-frame-options'),'DENY');assert.match(r.headers.get('set-cookie'),/HttpOnly/);assert.match(r.headers.get('set-cookie'),/SameSite=Strict/);
}));
test('credential revocation keeps last key and revokes other sessions',async()=>fixture(async({app,request})=>{
 const info=id=>({credential:{id,publicKey:randomBytes(32),counter:0,transports:[]}});
 await app.store.register(info('first'),{bootstrap:true,now:Date.now()});
 assert.equal((await request('/api/passkeys/first',{method:'DELETE',data:{}})).status,409);
 await app.db.query('INSERT INTO credentials VALUES($1,$2,$3,$4,$5)',['second',randomBytes(32).toString('base64url'),0,'[]',Date.now()]);
 const other=await app.store.newSession(Date.now());
 assert.equal((await request('/api/passkeys/first',{method:'DELETE',data:{}})).status,200);
 assert.equal(await app.store.credential('first'),undefined);
 assert.equal(await app.store.session(other.token,Date.now()),null);
 assert.equal((await request('/api/vault')).status,200);
}));
