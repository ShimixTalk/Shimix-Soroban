// Multi-market opportunity scanner. Public quotes only; no trading, no paid APIs.
const repo='ShimixTalk/Shimix-Soroban',branch='shimix-hub',path='hub/trading/scanner-state.json';
const token=process.env.GITHUB_TOKEN;
const headers={Authorization:'Bearer '+token,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'};
const watch=[
['ETF','spy.us'],['ETF','qqq.us'],['ETF','vti.us'],['ETF','iwm.us'],['ETF','gld.us'],['ETF','tlt.us'],['ETF','eem.us'],['ETF','vea.us'],
['Action','aapl.us'],['Action','msft.us'],['Action','nvda.us'],['Action','amzn.us'],['Action','googl.us'],['Action','meta.us'],['Action','tsla.us'],['Action','amd.us'],['Action','ko.us'],['Action','jpm.us'],['Action','xom.us'],['Action','unh.us'],
['Indice','^spx'],['Indice','^ndq'],['Devise','eurusd'],['Devise','usdjpy'],['Matière première','xauusd'],['Matière première','xagusd']
];
async function get(url,opts={}){const r=await fetch(url,{...opts,signal:AbortSignal.timeout(12000)});if(!r.ok)throw Error('HTTP '+r.status);return r}
function pct(v){return Number(v.toFixed(2))}
async function main(){
if(!token)throw Error('Missing token');
const found=[],unavailable=[];let cryptoCount=0;
try{
const r=await get('https://api.coingecko.com/api/v3/coins/markets?vs_currency=eur&order=market_cap_desc&per_page=100&page=1&sparkline=false&price_change_percentage=24h');
const items=await r.json();if(!Array.isArray(items))throw Error('Bad data');
for(const a of items){const change=Number(a.price_change_percentage_24h),volume=Number(a.total_volume),price=Number(a.current_price);if(!Number.isFinite(price)||price<=0||!Number.isFinite(change)||!Number.isFinite(volume)||volume<1000000)continue;cryptoCount++;found.push({category:'Crypto',symbol:String(a.symbol).toUpperCase(),name:a.name,price,currency:'EUR',change24h:pct(change),volume,source:'CoinGecko',signal:Math.abs(change)>=1?'Mouvement à examiner':'Surveillance',risk:'Volatilité crypto, spread et frais non garantis'})}
}catch(e){unavailable.push('Cryptos : '+e.message)}
// Stooq daily public CSV: sampled subset each run, without pretending full-market coverage.
const rotation=Math.floor(Date.now()/7200000)%Math.ceil(watch.length/12),sample=watch.slice(rotation*12,rotation*12+12);
for(const [category,symbol] of sample){try{
const r=await get('https://stooq.com/q/d/l/?s='+encodeURIComponent(symbol)+'&i=d&d1=20260901');
const csv=(await r.text()).trim().split(/\r?\n/);if(csv.length<3||!csv[0].includes('Close'))throw Error('No usable daily quotes');
const p=csv.slice(-3).map(x=>Number(x.split(',')[4]));if(!p.every(x=>Number.isFinite(x)&&x>0))throw Error('Invalid close');
const change=pct((p.at(-1)/p.at(-2)-1)*100);
found.push({category,symbol,name:symbol.toUpperCase(),price:p.at(-1),currency:'Source quote currency',change24h:change,source:'Stooq daily close',signal:Math.abs(change)>=1?'Mouvement à examiner':'Surveillance',risk:'Cours différé; spread et frais non inclus'});
}catch(e){unavailable.push(symbol+' : '+e.message)}}
if(found.length===0)throw Error('Aucune cotation exploitable : scanner non actualisé, conservation des résultats précédents');
found.sort((a,b)=>Math.abs(b.change24h)-Math.abs(a.change24h));
const result={updatedAt:new Date().toISOString(),assetsAnalyzed:found.length,cryptoCount,otherCount:found.length-cryptoCount,unavailable,notes:'Scanner indicatif, sans recommandation ni ordre réel. Les données peuvent être retardées. Les frais, spreads, fiscalité et liquidité réelle ne sont pas estimés.',estimatedRoundTripFeePct:0.2,minimumGrossMovePct:0.5,assets:found.slice(0,150)};
const api='https://api.github.com/repos/'+repo+'/contents/'+path;let sha;
const old=await fetch(api+'?ref='+branch,{headers});if(old.ok)sha=(await old.json()).sha;else if(old.status!==404)throw Error('GitHub read '+old.status);
const body={message:'Update multi-market scan',branch,content:Buffer.from(JSON.stringify(result,null,2)+'\n').toString('base64'),...(sha?{sha}:{})};
const saved=await fetch(api,{method:'PUT',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify(body)});if(!saved.ok)throw Error('GitHub write '+saved.status+' '+await saved.text());
console.log('Scanner saved',result.assetsAnalyzed,'assets;',unavailable.length,'unavailable');
}
main().catch(e=>{console.error(e);process.exitCode=1});
