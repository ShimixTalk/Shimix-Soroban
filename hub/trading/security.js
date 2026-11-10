/* Input boundary shared by legacy and encrypted imports. No storage writes here. */
(function (root) {
'use strict';
const object = x => !!x && typeof x === 'object' && !Array.isArray(x);
const number = x => typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 1e15;
const symbol = x => typeof x === 'string' && /^[A-Z0-9][A-Z0-9._-]{0,19}$/.test(x);
const allowed = k => ['shimix-trading-demo-v1','shimix-trading-bot-v4','shimix-academy-v1'].includes(k) || /^shimix-trading-(?:prefs|preferences|settings|academy|coach)(?:-[a-z0-9]+)*$/.test(k);
function assert(ok) { if (!ok) throw Error('Données de sauvegarde invalides.'); }
function tree(x, depth=0) {
  assert(depth < 20);
  if (typeof x === 'number') assert(Number.isFinite(x));
  if (typeof x === 'string') assert(x.length <= 10000);
  if (x && typeof x === 'object') {
    assert(Object.keys(x).length <= 100000);
    for (const [k,v] of Object.entries(x)) {
      assert(!['__proto__','prototype','constructor'].includes(k));
      assert(!(['realTradingEnabled','exchangeApiConnected','liveOrdersEnabled'].includes(k) && v !== false));
      tree(v,depth+1);
    }
  }
}
function quantities(x) { return object(x) && Object.entries(x).every(([k,v]) => symbol(k) && number(v)); }
function validateEntry(k,v) {
  assert(allowed(k) && object(v)); tree(v);
  if (k === 'shimix-trading-demo-v1') {
    assert(number(v.cash) && quantities(v.positions) && Array.isArray(v.journal) && v.journal.length <= 100000);
    assert(v.journal.every(t => object(t) && symbol(t.id) && ['Achat','Vente'].includes(t.side) && number(t.n) && t.n>0 && number(t.p) && t.p>0 && typeof t.date==='string'));
    assert(v.watch === undefined || (Array.isArray(v.watch) && v.watch.every(symbol)));
    assert(v.prices === undefined || (quantities(v.prices) && Object.values(v.prices).every(n=>n>0)));
  }
  if (k === 'shimix-trading-bot-v4') {
    assert(number(v.cash) && number(v.capital) && v.capital>0 && quantities(v.holdings));
    assert(v.mode === undefined || v.mode === 'simulation');
    for (const f of ['max','loss','peak']) if (v[f]!==undefined) assert(number(v[f]));
    assert(v.loss===undefined || v.loss<=100);
    for (const f of ['reference','lastTrade','updatedAt']) if(v[f]!==undefined) assert(quantities(v[f]));
    if(v.history!==undefined) assert(object(v.history) && Object.entries(v.history).every(([s,a])=>symbol(s)&&Array.isArray(a)&&a.length<=10000&&a.every(n=>number(n)&&n>0)));
    if(v.logs!==undefined) assert(Array.isArray(v.logs)&&v.logs.every(x=>typeof x==='string'));
    if(v.trades!==undefined) assert(Array.isArray(v.trades)&&v.trades.every(object));
    v.mode='simulation'; v.running=false;
  }
  return v;
}
function entries(data) {
  assert(object(data)); const list=Object.entries(data);
  assert(list.length>0 && list.length<=30);
  for(const [k,v] of list) validateEntry(k,v);
  return list;
}
const escape = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
root.ShimixSecurity={entries,validateEntry,escape,number,symbol};
})(globalThis);
