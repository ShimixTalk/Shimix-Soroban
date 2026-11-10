import {randomBytes,createHash} from 'node:crypto';
export const digest=s=>createHash('sha256').update(s).digest('hex');
export class Fault extends Error { constructor(status,message){super(message);this.status=status;} }

// SQL is identical in the two adapters; SQLite is restricted to local development/tests.
export async function openDatabase({url,localFile,production=false}) {
 if(url){
  if(production&&new URL(url).searchParams.get('sslmode')!=='verify-full')throw Error('PostgreSQL TLS verify-full requis.');
  const {Pool}=await import('pg');
  const pool=new Pool({connectionString:url,max:5,connectionTimeoutMillis:5000,statement_timeout:5000});
  const wrap=c=>({query:async(s,p=[])=> (await c.query(s,p)).rows});
  return {dialect:'postgres',...wrap(pool),async transaction(fn){const c=await pool.connect();try{await c.query('BEGIN');const result=await fn(wrap(c));await c.query('COMMIT');return result;}catch(e){await c.query('ROLLBACK');throw e;}finally{c.release();}},close:()=>pool.end()};
 }
 if(production)throw Error('PostgreSQL durable obligatoire en production.');
 if(!localFile)throw Error('Configurer DATABASE_URL ou un fichier SQLite local.');
 const {DatabaseSync}=await import('node:sqlite');const sqlite=new DatabaseSync(localFile);
 sqlite.exec('PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;');
 // Serialize asynchronous transactions so they cannot interleave on one connection.
 let tail=Promise.resolve();
 const execute=async(s,p=[])=>{const statement=sqlite.prepare(s);return p.length?statement.all(Object.fromEntries(p.map((v,i)=>['$'+(i+1),v]))):statement.all();};
 const schedule=fn=>{const next=tail.then(fn);tail=next.catch(()=>{});return next;};
 return {dialect:'sqlite',query:(s,p)=>schedule(()=>execute(s,p)),transaction(fn){return schedule(async()=>{sqlite.exec('BEGIN IMMEDIATE');try{const r=await fn({query:execute});sqlite.exec('COMMIT');return r;}catch(e){sqlite.exec('ROLLBACK');throw e;}});},close:async()=>sqlite.close()};
}
export class Store {
 constructor(db){this.db=db;}
 async init(){
  for(const sql of [
   `CREATE TABLE IF NOT EXISTS owner(id TEXT PRIMARY KEY CHECK(id='owner'), user_handle TEXT NOT NULL, registered INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 0)`,
   `CREATE TABLE IF NOT EXISTS credentials(id TEXT PRIMARY KEY, public_key TEXT NOT NULL, counter BIGINT NOT NULL, transports TEXT NOT NULL, created_at BIGINT NOT NULL)`,
   `CREATE TABLE IF NOT EXISTS challenges(id TEXT PRIMARY KEY, kind TEXT NOT NULL, challenge TEXT NOT NULL, binding TEXT NOT NULL, expires_at BIGINT NOT NULL)`,
   `CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, csrf TEXT NOT NULL, created_at BIGINT NOT NULL, seen_at BIGINT NOT NULL, expires_at BIGINT NOT NULL)`,
   `CREATE TABLE IF NOT EXISTS vault(revision INTEGER PRIMARY KEY, request_key TEXT UNIQUE NOT NULL, checksum TEXT NOT NULL, envelope TEXT NOT NULL, bytes INTEGER NOT NULL, created_at BIGINT NOT NULL)`,
   `CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY, event TEXT NOT NULL, created_at BIGINT NOT NULL)`
  ])await this.db.query(sql);
  await this.db.query("INSERT INTO owner(id,user_handle) VALUES('owner',$1) ON CONFLICT(id) DO NOTHING",[randomBytes(32).toString('base64url')]);
 }
 async owner(){return(await this.db.query("SELECT * FROM owner WHERE id='owner'"))[0];}
 async credentials(){return this.db.query('SELECT * FROM credentials ORDER BY created_at');}
 async credential(id){return(await this.db.query('SELECT * FROM credentials WHERE id=$1',[id]))[0];}
 async challenge(id,kind,challenge,binding,now){
  await this.db.query('DELETE FROM challenges WHERE expires_at<$1',[now]);
  await this.db.query('INSERT INTO challenges VALUES($1,$2,$3,$4,$5)',[digest(id),kind,challenge,binding,now+120000]);
 }
 async consumeChallenge(id,kind,now){
  const row=(await this.db.query('DELETE FROM challenges WHERE id=$1 RETURNING *',[digest(id)]))[0];
  if(!row||row.kind!==kind||Number(row.expires_at)<now)throw new Fault(401,'Vérification expirée. Recommence la connexion.');
  return row;
 }
 async register(info,{bootstrap,sessionHash,now}){
  const c=info.credential;
  await this.db.transaction(async db=>{
   if(bootstrap){const rows=await db.query("UPDATE owner SET registered=1 WHERE id='owner' AND registered=0 RETURNING id");if(!rows.length)throw new Fault(409,'Le compte existe déjà. Connecte-toi.');}
   else {const rows=await db.query('SELECT id FROM sessions WHERE id=$1 AND expires_at>$2 AND created_at>$3',[sessionHash,now,now-300000]);if(!rows.length)throw new Fault(401,'Reconnecte-toi avant d’ajouter une clé.');}
   await db.query('INSERT INTO credentials VALUES($1,$2,$3,$4,$5)',[c.id,Buffer.from(c.publicKey).toString('base64url'),c.counter,JSON.stringify(c.transports||[]),now]);
  });await this.audit('passkey.registered',now);
 }
 async removeCredential(id,sessionId,now){
  await this.db.transaction(async db=>{
   await db.query("UPDATE owner SET registered=registered WHERE id='owner' RETURNING id");
   const keys=await db.query('SELECT id FROM credentials');
   if(!keys.some(c=>c.id===id))throw new Fault(404,'Passkey introuvable.');
   if(keys.length<=1)throw new Fault(409,'Ajoute une clé de secours avant de retirer la dernière passkey.');
   await db.query('DELETE FROM credentials WHERE id=$1',[id]);
   await db.query('DELETE FROM sessions WHERE id<>$1',[sessionId]);
  });await this.audit('passkey.revoked',now);
 }
 async counter(id,old,newCounter){
  const rows=await this.db.query('UPDATE credentials SET counter=$1 WHERE id=$2 AND counter=$3 RETURNING id',[newCounter,id,old]);
  if(!rows.length)throw new Fault(401,'Connexion concurrente : recommence.');
 }
 async newSession(now){
  const token=randomBytes(32).toString('base64url'),csrf=randomBytes(32).toString('base64url');
  await this.db.query('INSERT INTO sessions VALUES($1,$2,$3,$4,$5)',[digest(token),digest(csrf),now,now,now+43200000]);
  return {token,csrf};
 }
 async session(token,now){
  if(!token)return null;
  const rows=await this.db.query('UPDATE sessions SET seen_at=$1 WHERE id=$2 AND expires_at>$1 AND seen_at>$3 RETURNING *',[now,digest(token),now-1800000]);
  return rows[0]||null;
 }
 async removeSession(token){await this.db.query('DELETE FROM sessions WHERE id=$1',[digest(token)]);}
 async revokeOthers(sessionId){await this.db.query('DELETE FROM sessions WHERE id<>$1',[sessionId]);}
 async vault(){return (await this.db.query('SELECT revision,envelope,created_at FROM vault ORDER BY revision DESC LIMIT 1'))[0]||{revision:0,envelope:null};}
 async saveVault(envelope,expected,key,now){
  const raw=JSON.stringify(envelope),checksum=digest(raw),bytes=Buffer.byteLength(raw);
  return this.db.transaction(async db=>{
   const prior=(await db.query('SELECT revision,checksum FROM vault WHERE request_key=$1',[key]))[0];
   if(prior){if(prior.checksum!==checksum)throw new Fault(409,'Identifiant de synchronisation déjà utilisé.');return {revision:prior.revision,replayed:true};}
   const result=await db.query("UPDATE owner SET revision=revision+1 WHERE id='owner' AND revision=$1 RETURNING revision",[expected]);
   if(!result.length)throw new Fault(409,'Une autre version existe. Compare les copies avant de continuer.');
   const size=(await db.query('SELECT COALESCE(SUM(bytes),0) AS total FROM vault'))[0];
   if(Number(size.total)+bytes>50*1024*1024)throw new Fault(507,'Coffre plein. Aucune sauvegarde supprimée.');
   const revision=result[0].revision;
   await db.query('INSERT INTO vault VALUES($1,$2,$3,$4,$5,$6)',[revision,key,checksum,raw,bytes,now]);
   return {revision,replayed:false};
  });
 }
 async audit(event,now){await this.db.query('INSERT INTO audit VALUES($1,$2,$3)',[randomBytes(16).toString('hex'),event,now]);}
}
