// Shared, pure guards for simulated accounting. No network and no credentials.
export const nonnegative = x => typeof x==='number' && Number.isFinite(x) && x>=0 && x<=1e15;
export function validatePortfolio(p) {
  if (!p || !nonnegative(p.cash) || !p.holdings || Array.isArray(p.holdings) || typeof p.holdings!=='object' || Object.values(p.holdings).some(q=>!nonnegative(q))) throw Error('Invalid simulated portfolio');
  for(const field of ['costBasis','entryCosts']) if(p[field]!==undefined){if(!p[field]||Array.isArray(p[field])||typeof p[field]!=='object'||Object.values(p[field]).some(x=>!x||!nonnegative(x.quantity)||!nonnegative(x.totalCost)))throw Error('Invalid cost basis');}
  for(const field of ['fee','spread','slippage']) if(p[field]!==undefined && (!nonnegative(p[field])||p[field]>.1))throw Error('Invalid execution costs');
  for (const key of ['capital','initial','maxOrder','maxLossPercent','peak']) if (p[key]!==undefined && !nonnegative(p[key])) throw Error('Invalid simulated risk limit '+key);
}
export function validateSimulation(p) {
  if (p?.realTradingEnabled!==false || p?.exchangeApiConnected!==false || p?.readiness?.simulationOnly!==true || p?.readiness?.liveOrdersEnabled!==false) throw Error('Simulation-only flags required');
  validatePortfolio(p);
  if (!(p.capital>0) || p.maxLossPercent>100 || !(p.maxOrder>=0)) throw Error('Invalid risk configuration');
}
export function requireHoldingQuotes(p,quotes) {
  for(const [symbol,qty] of Object.entries(p.holdings)) if(qty>0 && !(nonnegative(quotes[symbol])&&quotes[symbol]>0)) throw Error('Missing fresh holding quote '+symbol);
}
export function saleQuantity(budget,executionPrice,holding) {
  if(!nonnegative(budget)||!nonnegative(executionPrice)||executionPrice===0||!nonnegative(holding)) throw Error('Invalid sale');
  return Math.min(holding,budget/executionPrice);
}
export function closedDailyPrices(chart,now=Date.now()) {
  if(!Array.isArray(chart?.prices)) throw Error('Missing historical prices');
  const today=Math.floor(now/86400000),days=new Map();
  for(const row of chart.prices){
    if(!Array.isArray(row)||!Number.isFinite(row[0])||!nonnegative(row[1])||row[1]===0)throw Error('Invalid historical quote');
    const day=Math.floor(row[0]/86400000);if(day<today)days.set(day,row[1]);
  }
  const sorted=[...days.keys()].sort((a,b)=>a-b);
  if(sorted.length<22||sorted.at(-1)!==today-1||sorted.some((d,i)=>i&&d-sorted[i-1]!==1))throw Error('Stale or incomplete history');
  return sorted.slice(-31).map(d=>days.get(d));
}
