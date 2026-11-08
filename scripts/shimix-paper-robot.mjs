// SHIMIX TRADING — scheduled paper trading only. No exchange keys, no real orders.
const owner='ShimixTalk',repo='Shimix-Soroban',branch='shimix-hub',path='hub/trading/robot-state.json';
const token=process.env.GITHUB_TOKEN;
const headers={Authorization:'Bearer '+token,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'};
const assets=[['BTC','bitcoin'],['ETH','ethereum'],['SOL','solana'],['ADA','cardano'],['XRP','ripple'],['DOGE','dogecoin'],['LINK','chainlink'],['AVAX','avalanche-2'],['DOT','polkadot'],['LTC','litecoin']];
const etfWatchlist=['VWCE','CSPX','EQQQ','IWDA']; // Surveillance prévue : aucun prix ETF fiable branché, donc aucun signal ETF.
const fresh=()=>({version:1,capital:200,cash:200,holdings:{},peak:200,maxOrder:20,maxLossPercent:5,enabled:true,lastTrade:{},prices:{},signals:{},trades:[],logs:[],updatedAt:null});
const avg=(a,n)=>a.slice(-n).reduce((s,x)=>s+x,0)/n;
function rsi(a){let g=0,l=0;for(let i=a.length-14;i<a.length;i++){let d=a[i]-a[i-1];g+=Math.max(0,d);l+=Math.max(0,-d)}return l===0?100:100-100/(1+g/l)}
async function json(url,options){const r=await fetch(url,options);if(!r.ok)throw Error(r.status+' '+url);return r.json()}
async function main(){
if(!token)throw Error('GITHUB_TOKEN missing');
const api='https://api.github.com/repos/'+owner+'/'+repo+'/contents/'+path;
let state,sha;
try{const item=await json(api+'?ref='+branch,{headers});sha=item.sha;const bytes=Buffer.from(item.content.replace(/\s/g,''),'base64').toString('utf8');state=JSON.parse(bytes)}catch(e){if(!String(e).includes('404'))throw e;state=fresh()}
if(state.enabled===false){console.log('Paper bot disabled');return}
const priceData=await json('https://api.coingecko.com/api/v3/simple/price?ids='+assets.map(x=>x[1]).join(',')+'&vs_currencies=eur&include_24hr_vol=true');
const history={};const prices={};const eligible={};const errors=[];
for(const [symbol,id] of assets){
try{const price=Number(priceData[id]?.eur);if(!Number.isFinite(price)||price<=0)throw Error('Invalid price '+symbol);prices[symbol]=price;eligible[symbol]=Number(priceData[id]?.eur_24h_vol)>=10000000;
const chart=await json('https://api.coingecko.com/api/v3/coins/'+id+'/market_chart?vs_currency=eur&days=30&interval=daily');
const p=(chart.prices||[]).map(x=>Number(x[1])).filter(x=>Number.isFinite(x)&&x>0);if(p.length<22)throw Error('Insufficient history '+symbol);history[symbol]=p.slice(-31)}catch(e){errors.push(symbol+': '+e.message)}}
if(!Object.keys(prices).length)throw Error('No valid market data; refusing to trade');state.dataErrors=errors;state.prices={...state.prices,...prices};state.etfWatchlist=etfWatchlist;state.etfStatus='Surveillance ETF non active : fournisseur de données non connecté';state.liquidityEligible=eligible;
const value=()=>state.cash+Object.entries(state.holdings).reduce((sum,[id,qty])=>sum+(Number(qty)||0)*(prices[id]||state.prices[id]||0),0);
state.peak=Math.max(Number(state.peak)||state.capital,value());
if(value()<=state.capital*(1-state.maxLossPercent/100)){state.enabled=false;state.logs.unshift('STOP : limite de perte atteinte. Aucune liquidation automatique.')}
else for(const [symbol] of assets){
const p=history[symbol];if(!p)continue;const short=avg(p,7),long=avg(p,21),prev=avg(p.slice(0,-1),21),strength=rsi(p),price=prices[symbol];
let action='Attente';if(eligible[symbol]&&strength<35&&short>long&&price>prev)action='Achat';else if(strength>65&&short<long)action='Vente';
state.signals[symbol]={action,rsi:Number(strength.toFixed(2)),sma7:short,sma21:long};
if(action==='Attente'||Date.now()-Date.parse(state.lastTrade[symbol]||0)<86400000)continue;
const position=(Number(state.holdings[symbol])||0)*price;
const amount=action==='Achat'?Math.min(state.maxOrder,state.cash,state.capital*0.15-position):Math.min(state.maxOrder,position);
if(amount<5)continue; // Avoid tiny transactions whose costs dominate.
const fee=amount*0.001,quantity=action==='Achat'?(amount-fee)/price:amount/price;
if(action==='Achat'){state.cash-=amount;state.holdings[symbol]=(Number(state.holdings[symbol])||0)+quantity}else{state.cash+=amount-fee;state.holdings[symbol]=Math.max(0,(Number(state.holdings[symbol])||0)-quantity)}
const date=new Date().toISOString();state.lastTrade[symbol]=date;state.trades.unshift({date,symbol,action,amount,price,fee});state.logs.unshift(date+' '+action+' '+symbol+' '+amount.toFixed(2)+' EUR fictifs');
}
state.trades=state.trades.slice(0,200);state.logs=state.logs.slice(0,50);state.updatedAt=new Date().toISOString();state.value=Number(value().toFixed(2));
const body={message:'Update SHIMIX paper bot state',content:Buffer.from(JSON.stringify(state,null,2)+'\n').toString('base64'),branch,...(sha?{sha}:{})};
await json(api,{method:'PUT',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify(body)});
console.log('Paper simulation updated',state.updatedAt,state.value);
}
main().catch(e=>{console.error(e);process.exitCode=1});
