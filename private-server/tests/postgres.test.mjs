import test from 'node:test';
import assert from 'node:assert/strict';
import {randomUUID,randomBytes} from 'node:crypto';
import {Store,openDatabase} from '../store.mjs';
const url=process.env.SHIMIX_TEST_DATABASE_URL;
test('PostgreSQL: durable encrypted revisions, conflicting writes and first-owner registration',{skip:!url},async()=>{
 const parsed=new URL(url);assert.equal(parsed.pathname,'/shimix_private_test','Tests require the dedicated disposable database');assert.ok(['127.0.0.1','localhost'].includes(parsed.hostname));
 const db=await openDatabase({url});const store=new Store(db);await store.init();
 try{
  const envelope={ciphertext:randomBytes(20).toString('base64')};
  const results=await Promise.allSettled([store.saveVault(envelope,0,randomUUID(),Date.now()),store.saveVault(envelope,0,randomUUID(),Date.now())]);
  assert.equal(results.filter(x=>x.status==='fulfilled').length,1);
  assert.equal(results.find(x=>x.status==='rejected').reason.status,409);
  assert.equal((await store.vault()).revision,1);
  const registration=n=>store.register({credential:{id:n,publicKey:randomBytes(32),counter:0,transports:[]}},{bootstrap:true,now:Date.now()});
  const enrolled=await Promise.allSettled([registration('one'),registration('two')]);assert.equal(enrolled.filter(x=>x.status==='fulfilled').length,1);
 }finally{await db.close();}
 const reopened=await openDatabase({url});const recovered=new Store(reopened);await recovered.init();
 try{assert.equal((await recovered.vault()).revision,1);assert.equal((await recovered.owner()).registered,1);}finally{await reopened.close();}
});
