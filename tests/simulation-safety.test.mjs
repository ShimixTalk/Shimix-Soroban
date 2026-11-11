import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {validateSimulation,requireHoldingQuotes,saleQuantity,closedDailyPrices} from '../scripts/simulation-safety.mjs';
const safe={cash:1600,capital:1600,maxOrder:120,maxLossPercent:5,holdings:{},realTradingEnabled:false,exchangeApiConnected:false,readiness:{simulationOnly:true,liveOrdersEnabled:false}};
test('live flags fail closed',()=>{assert.doesNotThrow(()=>validateSimulation(safe));for(const v of [true,undefined,'false'])assert.throws(()=>validateSimulation({...safe,realTradingEnabled:v}));});
test('non finite balances and negative holdings rejected',()=>{for(const cash of [NaN,Infinity,-1,'100'])assert.throws(()=>validateSimulation({...safe,cash}));assert.throws(()=>validateSimulation({...safe,holdings:{BTC:-1}}));});
test('missing quote suspends whole portfolio',()=>{assert.throws(()=>requireHoldingQuotes({holdings:{BTC:1}},{}));assert.doesNotThrow(()=>requireHoldingQuotes({holdings:{BTC:1}},{BTC:100}));});
test('full sale cannot exceed holdings after spread',()=>{const units=saleQuantity(100,99.8,1);assert.equal(units,1);assert.equal(units*99.8*(1-.001),99.7002);});
test('closed candles exclude intraday and reject stale history',()=>{const today=Math.floor(Date.now()/86400000),rows=Array.from({length:32},(_,i)=>[(today-31+i)*86400000,100]);assert.equal(closedDailyPrices({prices:rows}).length,31);assert.throws(()=>closedDailyPrices({prices:rows.slice(0,-3)}));});
function runPaper(changes={}){
 const state={...safe,enabled:true,peak:1600,holdings:{BTC:1},cash:1500,lastTrade:{},entryCosts:{BTC:{quantity:1,totalCost:50}},trades:[],logs:[],signals:{},...changes};
 const code=`
 process.env.GITHUB_TOKEN='test-only';
 const state=${JSON.stringify(state)};
 const today=Math.floor(Date.now()/86400000);
 globalThis.fetch=async(url,opts={})=>{
  let data;
  if(String(url).includes('api.github.com')){
   if(opts.method==='PUT'){const body=JSON.parse(opts.body);console.log('SAVED:'+JSON.stringify(JSON.parse(Buffer.from(body.content,'base64').toString())));return {ok:true,json:async()=>({})};}
   data={sha:'fixture',content:Buffer.from(JSON.stringify(state)).toString('base64')};
  }else if(String(url).includes('/simple/price')){data={bitcoin:{eur:100,eur_24h_vol:1e8}};}
  else{data={prices:Array.from({length:31},(_,i)=>[(today-31+i)*86400000,i<16?1000:50+i-16])};}
  return {ok:true,json:async()=>data};
 };
 await import('./scripts/shimix-paper-robot.mjs');`;
 return spawnSync(process.execPath,['--input-type=module','-e',code],{cwd:new URL('..',import.meta.url),encoding:'utf8'});
}
test('actual legacy robot sale conserves proceeds and quantity',()=>{
 const result=runPaper();assert.equal(result.status,0,result.stderr);
 const saved=JSON.parse(result.stdout.split('SAVED:')[1].split('\n')[0]);
 assert.equal(saved.trades.length,1);assert.equal(saved.trades[0].action,'Vente');
 assert.ok(saved.cash<=1600);assert.ok(saved.holdings.BTC>=0);
 assert.ok(Math.abs(saved.cash-(1500+saved.trades[0].amount-saved.trades[0].fee))<1e-9);
});
test('actual legacy robot rejects live state without write',()=>{const result=runPaper({realTradingEnabled:true});assert.equal(result.status,1);assert.ok(!result.stdout.includes('SAVED:'));});
test('actual legacy robot rejects missing holding quote without write',()=>{const result=runPaper({holdings:{UNKNOWN:1}});assert.equal(result.status,1);assert.ok(!result.stdout.includes('SAVED:'));});
function runPortfolios(overrides={}){
 const p={cashFlows:[],id:'prudent',cash:630,initial:640,holdings:{BTC:.1},costBasis:{BTC:{quantity:.1,totalCost:1}},trades:[],signals:{},history:[],peak:640,paused:false,value:640,netProfit:0,feesPaid:0};
 const state={simulationOnly:true,realOrdersEnabled:false,portfolios:[p],...overrides};
 const code=`process.env.GITHUB_TOKEN='test-only';const state=${JSON.stringify(state)};
 globalThis.fetch=async(url,opts={})=>{let data;
 if(String(url).includes('api.github.com')){
  if(opts.method==='PUT'){console.log('SAVED:'+JSON.stringify(JSON.parse(Buffer.from(JSON.parse(opts.body).content,'base64').toString())));return {ok:true,json:async()=>({})};}
  data={sha:'fixture',content:Buffer.from(JSON.stringify(state)).toString('base64')};
 }else{data=['bitcoin','ethereum','solana'].map(id=>({id,current_price:100,price_change_percentage_24h:-3,total_volume:1e8}));}
 return {ok:true,json:async()=>data};};await import('./scripts/shimix-three-portfolios.mjs');`;
 return spawnSync(process.execPath,['--input-type=module','-e',code],{cwd:new URL('..',import.meta.url),encoding:'utf8'});
}
test('three portfolios full liquidation accounts for actual units',()=>{
 const result=runPortfolios();assert.equal(result.status,0,result.stderr);
 const saved=JSON.parse(result.stdout.split('SAVED:')[1].split('\n')[0]);const p=saved.portfolios[0];
 assert.equal(p.trades.length,1);assert.equal(p.trades[0].quantity,.1);assert.equal(p.holdings.BTC,0);
 assert.ok(Math.abs(p.cash-(630+.1*99.85*.998))<1e-9);
});
test('three portfolios reject live flags without writing',()=>{const r=runPortfolios({realOrdersEnabled:true});assert.equal(r.status,1);assert.ok(!r.stdout.includes('SAVED:'));});

test('actual automation preserves audited transfer and all history entries',()=>{
 const history=Array.from({length:1001},()=>({at:'2026-11-10T12:00:00Z',value:560}));
 const p={id:'prudent',initial:640,cash:560,holdings:{},costBasis:{},trades:[],signals:{},history,peak:560,paused:false,value:560,feesPaid:0,updatedAt:'2026-11-11T12:00:00Z'};
 const result=runPortfolios({portfolios:[p]});assert.equal(result.status,0,result.stderr);
 const saved=JSON.parse(result.stdout.split('SAVED:')[1].split('\n')[0]).portfolios[0];
 assert.equal(saved.netProfit,0);assert.equal(saved.cash,560);assert.equal(saved.initial,640);
 assert.equal(saved.cashFlows[0].amount,-80);assert.deepEqual(saved.history.slice(0,-1),history);
 assert.equal(saved.peak,560);assert.equal(saved.stop,.08);assert.equal(saved.paused,false);
});
test('invalid transfer metadata prevents any automation write',()=>{
 const p={id:'prudent',initial:640,cash:560,holdings:{},costBasis:{},trades:[],signals:{},history:[],peak:560,paused:false,value:560,feesPaid:0,cashFlows:[{id:'bad',amount:'80',at:'bad'}]};
 const result=runPortfolios({portfolios:[p]});assert.equal(result.status,1);assert.ok(!result.stdout.includes('SAVED:'));
});
