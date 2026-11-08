// SHIMIX 3 independent simulated portfolios; no brokerage API, no real orders.
const token=process.env.GITHUB_TOKEN,repo='ShimixTalk/Shimix-Soroban',branch='shimix-hub',path='hub/trading/three-portfolios.json';
const headers={Authorization:'Bearer '+token,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'};
const definitions=[
{id:'prudent',name:'Prudent',initial:640,fee:0.002,spread:0.001,slippage:0.001,maxAllocation:0.12,maxTrade:35,stop:0.08,allowed:['BTC','ETH'],description:'Réserve en euros fictifs et exposition limitée aux grandes cryptos; aucun ETF simulé sans cotation fiable'},
{id:'equilibre',name:'Équilibré',initial:560,fee:0.002,spread:0.0015,slippage:0.0015,maxAllocation:0.22,maxTrade:45,stop:0.15,allowed:['BTC','ETH','SOL','LINK'],description:'Diversification crypto; ETF surveillés mais non tradés sans données exploitables'},
{id:'dynamique',name:'Dynamique',initial:400,fee:0.002,spread:0.003,slippage:0.003,maxAllocation:0.35,maxTrade:50,stop:0.25,allowed:['BTC','ETH','SOL','LINK','AVAX','DOGE'],description:'Cryptomonnaies plus volatiles, risque élevé de pertes'}
];
const ids={BTC:'bitcoin',ETH:'ethereum',SOL:'solana',LINK:'chainlink',AVAX:'avalanche-2',DOGE:'dogecoin'};
const round=n=>Math.round(n*100)/100;
const fresh=d=>({...d,cash:d.initial,holdings:{},costBasis:{},trades:[],signals:{},history:[],peak:d.initial,paused:false,value:d.initial,netProfit:0,feesPaid:0,updatedAt:null});
async function api(url,opts){const r=await fetch(url,{...opts,signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error(r.status+' '+await r.text());return r.json()}
async function main(){
if(!token)throw Error('GITHUB_TOKEN absent');
const url='https://api.github.com/repos/'+repo+'/contents/'+path;let sha,old;
try{const file=await api(url+'?ref='+branch,{headers});sha=file.sha;old=JSON.parse(Buffer.from(file.content.replace(/\\s/g,''),'base64').toString())}catch(e){if(!String(e).startsWith('Error: 404')&&!String(e).includes('404'))throw e}
const quotes=await api('https://api.coingecko.com/api/v3/coins/markets?vs_currency=eur&ids='+Object.values(ids).join(',')+'&order=market_cap_desc&per_page=20&page=1&sparkline=false&price_change_percentage=24h');
if(!Array.isArray(quotes)||quotes.length<3)throw Error('Cotations insuffisantes');
const q={};for(const a of quotes){const symbol=Object.keys(ids).find(k=>ids[k]===a.id);if(symbol&&Number(a.current_price)>0)q[symbol]={price:Number(a.current_price),change:Number(a.price_change_percentage_24h),volume:Number(a.total_volume)}}
const now=new Date().toISOString(),portfolios=[];
for(const d of definitions){
const p=old?.portfolios?.find(x=>x.id===d.id)||fresh(d);
Object.assign(p,{name:d.name,initial:d.initial,fee:d.fee,spread:d.spread,slippage:d.slippage,maxAllocation:d.maxAllocation,maxTrade:d.maxTrade,stop:d.stop,allowed:d.allowed,description:d.description});
const value=()=>p.cash+Object.entries(p.holdings).reduce((sum,[symbol,qty])=>sum+qty*(q[symbol]?.price||p.lastPrices?.[symbol]||0),0);
p.lastPrices={...p.lastPrices,...Object.fromEntries(Object.entries(q).map(([k,v])=>[k,v.price]))};
p.peak=Math.max(p.peak||p.initial,value());if(value()<=p.initial*(1-p.stop))p.paused=true;
for(const symbol of p.allowed){
const a=q[symbol];if(!a||!Number.isFinite(a.change))continue;
let action='Attente',reason='Pas de signal suffisamment robuste';
if(!p.paused&&a.volume>=10000000){
if(a.change>=1.5&&a.change<=5&&p.cash>=10)action='Achat';
if(a.change<=-2&&p.holdings[symbol]>0)action='Vente';
}
const position=(p.holdings[symbol]||0)*a.price;
const amount=action==='Achat'?Math.min(p.maxTrade,p.cash,p.initial*p.maxAllocation-position):Math.min(p.maxTrade,position);
const estimatedCosts=amount*(p.fee+p.spread/2+p.slippage);
if(amount<10){action='Attente';reason='Montant insuffisant'}
else if(action==='Vente'){
const basis=p.costBasis[symbol];const qty=amount/(a.price*(1-p.spread/2-p.slippage));
const allocatedCost=basis&&basis.quantity>0?basis.totalCost*Math.min(1,qty/basis.quantity):Infinity;
const expectedNet=amount-estimatedCosts-allocatedCost;
if(expectedNet<0.01){action='Attente';reason='Gain net estimé inférieur à 0,01 € (avant fiscalité)'}
}
p.signals[symbol]={action,change24h:round(a.change),reason,estimatedCosts:round(estimatedCosts)};
if(action==='Attente'||p.lastTradeAt?.[symbol]&&Date.now()-Date.parse(p.lastTradeAt[symbol])<86400000)continue;
const executionPrice=a.price*(action==='Achat'?1+p.spread/2+p.slippage:1-p.spread/2-p.slippage);
const fee=amount*p.fee;const quantity=action==='Achat'?(amount-fee)/executionPrice:amount/executionPrice;
if(action==='Achat'){
p.cash-=amount;p.holdings[symbol]=(p.holdings[symbol]||0)+quantity;
const basis=p.costBasis[symbol]||{quantity:0,totalCost:0};basis.quantity+=quantity;basis.totalCost+=amount;p.costBasis[symbol]=basis;
}else{
const basis=p.costBasis[symbol],ratio=Math.min(1,quantity/basis.quantity);basis.totalCost*=1-ratio;basis.quantity=Math.max(0,basis.quantity-quantity);
p.holdings[symbol]=Math.max(0,p.holdings[symbol]-quantity);p.cash+=amount-fee;
}
p.feesPaid+=fee;p.lastTradeAt??={};p.lastTradeAt[symbol]=now;
p.trades.unshift({at:now,symbol,action,amount:round(amount),quantity,executionPrice,fee:round(fee),estimatedSpreadSlippage:round(amount*(p.spread/2+p.slippage)),tax:'Non calculée'});
}
p.value=round(value());p.netProfit=round(p.value-p.initial);p.history.push({at:now,value:p.value});p.history=p.history.slice(-365);p.trades=p.trades.slice(0,250);p.updatedAt=now;portfolios.push(p);
}
const result={version:1,updatedAt:now,simulationOnly:true,realOrdersEnabled:false,totalInitial:1600,totalValue:round(portfolios.reduce((s,p)=>s+p.value,0)),totalProfit:round(portfolios.reduce((s,p)=>s+p.netProfit,0)),taxStatus:'Non calculée : fiscalité personnelle et courtier non vérifiés',costStatus:'Hypothèses de simulation, pas tarifs Crypto.com réels',dataStatus:'Cotations CoinGecko indicatives; ETF et actions non tradés',strategyStatus:'Règles expérimentales non backtestées; aucune garantie de rentabilité',portfolios};
await api(url,{method:'PUT',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify({branch,message:'Update three independent paper portfolios',content:Buffer.from(JSON.stringify(result,null,2)+'\\n').toString('base64'),...(sha?{sha}:{})})});
console.log('Three paper portfolios updated',result.totalValue,result.totalProfit);
}
main().catch(e=>{console.error(e);process.exitCode=1});
