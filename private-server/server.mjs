import http from 'node:http';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {join,resolve,extname} from 'node:path';
import {randomBytes,timingSafeEqual} from 'node:crypto';
import {generateRegistrationOptions,verifyRegistrationResponse,generateAuthenticationOptions,verifyAuthenticationResponse} from '@simplewebauthn/server';
import {openDatabase,Store,Fault,digest} from './store.mjs';

export function configuration(env=process.env){
 const origin=env.SHIMIX_ORIGIN;const production=env.NODE_ENV==='production';
 if(!origin)throw Error('SHIMIX_ORIGIN requis.');
 const u=new URL(origin);if(u.origin!==origin||u.username||u.password)throw Error('Origine exacte requise, sans chemin.');
 const local=['localhost','127.0.0.1'].includes(u.hostname);
 if(u.protocol!=='https:'&&!(local&&!production&&u.protocol==='http:'))throw Error('HTTPS obligatoire.');
 if(!env.SHIMIX_BOOTSTRAP_TOKEN||env.SHIMIX_BOOTSTRAP_TOKEN.length<32)throw Error('Secret initial aléatoire de 32 caractères minimum requis.');
 return {origin,rpID:u.hostname,production,secure:u.protocol==='https:',bootstrap:env.SHIMIX_BOOTSTRAP_TOKEN,port:Number(env.PORT||3000),localFile:env.SHIMIX_SQLITE_FILE,url:env.DATABASE_URL};
}
const equal=(a,b)=>typeof a==='string'&&typeof b==='string'&&timingSafeEqual(Buffer.from(digest(a)),Buffer.from(digest(b)));
function cookie(req,name){return req.headers.cookie?.split(';').map(x=>x.trim()).find(x=>x.startsWith(name+'='))?.slice(name.length+1)||'';}
export function validateEnvelope(o){
 const base64=(s,n)=>typeof s==='string'&&s.length>0&&/^[A-Za-z0-9+/]*={0,2}$/.test(s)&&Buffer.from(s,'base64').toString('base64')===s&&(!n||Buffer.from(s,'base64').length===n);
 if(!o||Object.keys(o).sort().join(',')!=='cipher,ciphertext,format,iterations,iv,kdf,salt,version'||o.format!=='shimix-encrypted-backup'||o.version!==1||o.kdf!=='PBKDF2-SHA256'||![250000,600000].includes(o.iterations)||o.cipher!=='AES-256-GCM'||!base64(o.salt,16)||!base64(o.iv,12)||!base64(o.ciphertext)||o.ciphertext.length>2900000||Buffer.from(o.ciphertext,'base64').length<17)throw new Fault(400,'Sauvegarde chiffrée non reconnue.');
 return o;
}
async function body(req){
 if(!/^application\/json(?:;|$)/i.test(req.headers['content-type']||''))throw new Fault(415,'JSON requis.');
 let n=0;const parts=[];
 for await(const part of req){n+=part.length;if(n>3000000)throw new Fault(413,'Fichier trop volumineux.');parts.push(part);}
 try{return JSON.parse(Buffer.concat(parts).toString('utf8'));}catch{throw new Fault(400,'JSON invalide.');}
}
export async function createApplication(config,{db,clock=()=>Date.now()}={}){
 db??=await openDatabase({url:config.url,localFile:config.localFile,production:config.production});
 const store=new Store(db);await store.init();
 const sessionName=config.secure?'__Host-shimix-session':'shimix-dev-session';
 const flowName=config.secure?'__Host-shimix-flow':'shimix-dev-flow';
 const root=resolve(fileURLToPath(new URL('../hub',import.meta.url)));
 const limits=new Map();
 function limited(req,now){
  const ip=req.socket.remoteAddress;let bucket=limits.get(ip);
  if(!bucket||bucket.until<now){for(const [key,value] of limits)if(value.until<now)limits.delete(key);if(limits.size>10000)throw new Fault(429,'Réessaie plus tard.');bucket={count:0,until:now+900000};limits.set(ip,bucket);}
  if(++bucket.count>60)throw new Fault(429,'Trop de tentatives. Attends 15 minutes.');
 }
 const setCookie=(name,value,maxAge)=>`${name}=${value}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${maxAge}${config.secure?'; Secure':''}`;
 const server=http.createServer(async(req,res)=>{
  res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('X-Frame-Options','DENY');res.setHeader('Referrer-Policy','no-referrer');
  res.setHeader('Permissions-Policy','camera=(), geolocation=(), payment=(), usb=()');
  const json=(status,data,headers={})=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8',...headers});res.end(JSON.stringify(data));};
  try{
   const url=new URL(req.url,config.origin),path=url.pathname,now=clock();
   if(['POST','PUT','DELETE','PATCH'].includes(req.method)&&req.headers.origin!==config.origin)throw new Fault(403,'Origine refusée.');
   if(path==='/healthz'&&req.method==='GET')return json(200,{ok:true,simulationOnly:true});
   if(path.startsWith('/api/')){
    if(req.method!=='GET')limited(req,now);
    const input=req.method==='GET'?undefined:await body(req);
    const token=cookie(req,sessionName),session=await store.session(token,now);
    const needSession=()=>{if(!session)throw new Fault(401,'Connecte-toi avec ta passkey.');};
    const recent=()=>{needSession();if(Number(session.created_at)<now-300000)throw new Fault(403,'Reconnecte-toi pour cette action.');};
    const csrf=()=>{needSession();if(!equal(digest(req.headers['x-csrf-token']||''),session.csrf))throw new Fault(403,'Vérification de session refusée.');};
    if(path==='/api/auth/status'&&req.method==='GET')return json(200,{enrolled:!!(await store.owner()).registered,authenticated:!!session});
    if(path==='/api/me'&&req.method==='GET'){needSession();return json(200,{account:'owner',simulationOnly:true,passkeys:(await store.credentials()).length});}
    if(path==='/api/auth/register/options'&&req.method==='POST'){
     const owner=await store.owner(),bootstrap=owner.registered===0;
     if(bootstrap){if(!equal(req.headers['x-bootstrap-token'],config.bootstrap))throw new Fault(401,'Initialisation refusée.');}
     else {csrf();recent();}
     const options=await generateRegistrationOptions({rpName:'SHIMIX TRADING PRESTIGE',rpID:config.rpID,userName:'Propriétaire SHIMIX',userID:Buffer.from(owner.user_handle,'base64url'),attestationType:'none',authenticatorSelection:{residentKey:'required',userVerification:'required'},supportedAlgorithmIDs:[-7,-257],excludeCredentials:(await store.credentials()).map(c=>({id:c.id,transports:JSON.parse(c.transports)}))});
     const flow=randomBytes(32).toString('base64url');await store.challenge(flow,'register',options.challenge,bootstrap?'bootstrap':session.id,now);
     return json(200,options,{'Set-Cookie':setCookie(flowName,flow,120)});
    }
    if(path==='/api/auth/register/verify'&&req.method==='POST'){
     const flow=await store.consumeChallenge(cookie(req,flowName),'register',now),data=input;
     const bootstrap=flow.binding==='bootstrap';if(bootstrap){if(!equal(req.headers['x-bootstrap-token'],config.bootstrap))throw new Fault(401,'Initialisation refusée.');}else{csrf();recent();if(flow.binding!==session.id)throw new Fault(401,'Session différente.');}
     let verified;try{verified=await verifyRegistrationResponse({response:data,expectedChallenge:flow.challenge,expectedOrigin:config.origin,expectedRPID:config.rpID,requireUserVerification:true,supportedAlgorithmIDs:[-7,-257]});}catch{throw new Fault(401,'Passkey non vérifiée.');}
     if(!verified.verified)throw new Fault(401,'Passkey non vérifiée.');
     await store.register(verified.registrationInfo,{bootstrap,sessionHash:session?.id,now});
     if(token)await store.removeSession(token);const created=await store.newSession(now);
     return json(200,{ok:true,csrf:created.csrf},{'Set-Cookie':[setCookie(sessionName,created.token,43200),setCookie(flowName,'',0)]});
    }
    if(path==='/api/auth/login/options'&&req.method==='POST'){
     const options=await generateAuthenticationOptions({rpID:config.rpID,userVerification:'required'});
     const flow=randomBytes(32).toString('base64url');await store.challenge(flow,'login',options.challenge,'login',now);
     return json(200,options,{'Set-Cookie':setCookie(flowName,flow,120)});
    }
    if(path==='/api/auth/login/verify'&&req.method==='POST'){
     const flow=await store.consumeChallenge(cookie(req,flowName),'login',now),data=input,credential=await store.credential(typeof data?.id==='string'?data.id:'');
     if(!credential)throw new Fault(401,'Connexion refusée.');
     const owner=await store.owner();if(data.response?.userHandle&&data.response.userHandle!==owner.user_handle)throw new Fault(401,'Connexion refusée.');
     let verified;try{verified=await verifyAuthenticationResponse({response:data,expectedChallenge:flow.challenge,expectedOrigin:config.origin,expectedRPID:config.rpID,requireUserVerification:true,credential:{id:credential.id,publicKey:Buffer.from(credential.public_key,'base64url'),counter:Number(credential.counter),transports:JSON.parse(credential.transports)}});}catch{throw new Fault(401,'Connexion refusée.');}
     if(!verified.verified)throw new Fault(401,'Connexion refusée.');
     await store.counter(credential.id,credential.counter,verified.authenticationInfo.newCounter);if(token)await store.removeSession(token);
     const created=await store.newSession(now);await store.audit('session.created',now);
     return json(200,{ok:true,csrf:created.csrf},{'Set-Cookie':[setCookie(sessionName,created.token,43200),setCookie(flowName,'',0)]});
    }
    if(path==='/api/auth/logout'&&req.method==='POST'){csrf();await store.removeSession(token);return json(200,{ok:true},{'Set-Cookie':setCookie(sessionName,'',0)});}
    if(path==='/api/sessions/revoke-others'&&req.method==='POST'){csrf();recent();await store.revokeOthers(session.id);await store.audit('sessions.revoked',now);return json(200,{ok:true});}
    if(path==='/api/passkeys'&&req.method==='GET'){needSession();return json(200,{passkeys:(await store.credentials()).map(c=>({id:c.id,createdAt:Number(c.created_at)}))});}
    const keyPath=path.match(/^\/api\/passkeys\/([A-Za-z0-9_-]{1,2048})$/);
    if(keyPath&&req.method==='DELETE'){csrf();recent();await store.removeCredential(keyPath[1],session.id,now);return json(200,{ok:true});}
    if(path==='/api/vault'&&req.method==='GET'){needSession();const data=await store.vault();return json(200,{revision:data.revision,envelope:data.envelope?JSON.parse(data.envelope):null,updatedAt:data.created_at||null},{ETag:`"${data.revision}"`});}
    if(path==='/api/vault'&&req.method==='PUT'){
     csrf();const match=req.headers['if-match'],key=req.headers['idempotency-key'];
     if(!/^"(?:0|[1-9][0-9]{0,8})"$/.test(match||''))throw new Fault(428,'Révision exacte requise.');
     if(typeof key!=='string'||!/^[a-f0-9-]{36}$/.test(key))throw new Fault(400,'Identifiant de synchronisation requis.');
     const envelope=validateEnvelope(input);const result=await store.saveVault(envelope,Number(match.slice(1,-1)),key,now);
     return json(200,result,{ETag:`"${result.revision}"`});
    }
    throw new Fault(404,'Route introuvable.');
   }
   if(req.method!=='GET'&&req.method!=='HEAD')throw new Fault(405,'Méthode refusée.');
   // Never expose backend source, secrets, database files or arbitrary directories.
   const trading=path.startsWith('/trading/');
   if(trading&&path!=='/trading/security.js'){const session=await store.session(cookie(req,sessionName),now);if(!session){res.writeHead(302,{Location:'/private/index.html'});return res.end();}}
   const allowed=path.startsWith('/private/')||trading;
   if(!allowed)throw new Fault(404,'Route introuvable.');
   const relative=decodeURIComponent(path),file=resolve(join(root,relative));
   if(!file.startsWith(root+'/')||relative.includes('..')||!['.html','.js','.css','.svg','.webmanifest'].includes(extname(file))||path.endsWith('/sw.js'))throw new Fault(404,'Route introuvable.');
   res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'");
   if(trading)res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self' https://api.coingecko.com https://raw.githubusercontent.com; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'");
   const data=await readFile(file);res.writeHead(200,{'Content-Type':({'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.webmanifest':'application/manifest+json'})[extname(file)]+'; charset=utf-8'});res.end(req.method==='HEAD'?undefined:data);
  }catch(e){json(e.status||500,{error:e.status?e.message:'Service indisponible. Aucune donnée remplacée.'});}
 });
 server.requestTimeout=15000;server.headersTimeout=10000;
 return {server,store,db,close:async()=>{await new Promise(r=>server.close(r));await db.close();}};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const cfg=configuration();const app=await createApplication(cfg);
 app.server.listen(cfg.port,cfg.production?'0.0.0.0':'127.0.0.1',()=>console.log('SHIMIX privé : serveur démarré, simulation uniquement.'));
 let stopping=false;const stop=async()=>{if(stopping)return;stopping=true;await app.close();};process.on('SIGTERM',stop);process.on('SIGINT',stop);
}
