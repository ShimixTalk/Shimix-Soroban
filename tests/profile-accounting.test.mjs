import test from 'node:test';
import assert from 'node:assert/strict';
import {migrateCashFlows,netCashFlow,tradingProfit} from '../scripts/profile-accounting.mjs';
for(const [id,initial,withdrawal,loss] of [['prudent',640,80,0],['equilibre',560,80,1.13],['dynamique',400,40,2.88]]) {
 test(id+': transfer excluded, genuine loss retained; migration idempotent',()=>{
 const p={id,initial,value:initial-withdrawal-loss,cash:123,holdings:{BTC:1},history:[{at:'2026-11-08T12:00:00Z',value:initial-withdrawal}],updatedAt:'2026-11-11T12:00:00Z',peak:initial-withdrawal,stop:.08,trades:[{fee:.1}]};
 const before=structuredClone(p);assert.equal(migrateCashFlows(p),-withdrawal);
 assert.equal(tradingProfit(p),loss===0?0:-loss);const migrated=structuredClone(p);migrateCashFlows(p);assert.deepEqual(p,migrated);
 const {cashFlows,...rest}=p;assert.deepEqual(rest,before);
 });
}
test('fresh profile and deposits do not erase trading losses',()=>{
 const p={value:650,initial:640,cashFlows:[]};assert.equal(tradingProfit(p),10);
 p.cashFlows=[{id:'deposit',amount:20,at:'2026-11-11T12:00:00Z'}];assert.equal(tradingProfit(p),-10);
});
test('unknown legacy histories fail closed',()=>{
 for(const p of [{id:'unknown'},{id:'prudent',initial:640,history:[{value:640}],updatedAt:'2026-11-11T12:00:00Z'}])assert.throws(()=>migrateCashFlows(p));
});
test('duplicate or invalid flows fail closed',()=>{
 const f={id:'a',amount:-80,at:'2026-11-11T12:00:00Z'};
 for(const cashFlows of [[f,f],[{...f,amount:NaN}],[{...f,amount:true}],[{...f,at:'bad'}],null])assert.throws(()=>netCashFlow({cashFlows}));
});
