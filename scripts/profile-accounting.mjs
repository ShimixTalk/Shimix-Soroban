// Audited migration: f1f3221 withdrew paper capital and restated historical values.
export const transferCommit='f1f3221108db602c23a8c489cd25efea4e142dce';
export function migrateCashFlows(p) {
 if (p.cashFlows !== undefined) return netCashFlow(p);
 const allocations={prudent:[640,80],equilibre:[560,80],dynamique:[400,40]};
 const [initial,withdrawal]=allocations[p.id]||[];
 if(p.initial!==initial || !p.history?.length || p.history[0].value!==initial-withdrawal || !Number.isFinite(Date.parse(p.updatedAt)) || Date.parse(p.updatedAt)<Date.parse('2026-11-09T19:10:24Z')) throw Error('Unknown allocation history: human audit required');
 p.cashFlows=[{id:transferCommit+':'+p.id,sourceCommit:transferCommit,at:'2026-11-09T18:39:53+00:00',amount:-withdrawal,type:'paper_capital_transfer',note:'Transfert fictif hors du profil, distinct du trading ; aucune réinjection.'}];
 return netCashFlow(p);
}
export function netCashFlow(p) {
 if(!Array.isArray(p.cashFlows)) throw Error('Invalid cash flows');
 const ids=new Set();let sum=0;
 for(const f of p.cashFlows){
  if(!f || typeof f.id!=='string' || !f.id || ids.has(f.id) || typeof f.amount!=='number' || !Number.isFinite(f.amount) || !Number.isFinite(Date.parse(f.at))) throw Error('Invalid or duplicate cash flow');
  ids.add(f.id);sum+=f.amount;
 }
 return sum;
}
export function tradingProfit(p){return Math.round((p.value-p.initial-netCashFlow(p))*100)/100;}
