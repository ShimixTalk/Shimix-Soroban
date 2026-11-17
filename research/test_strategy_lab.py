import copy, datetime as dt, unittest
from strategy_lab import ASSETS, EXIT, replay, signal
from unittest.mock import patch

def rows(n=160):
 return [dict(date=(dt.date(2026,1,1)+dt.timedelta(days=i)).isoformat(),prices={a:100+i*.1 for a in ASSETS}) for i in range(n)]

class StrategyLabTests(unittest.TestCase):
 def test_cash_benchmark_preserves_capital(self):
  r=replay(rows(),'cash',22,120);self.assertEqual(r['netPnl'],0);self.assertEqual(r['tradeCount'],0)
 def test_terminal_costs_not_double_charged(self):
  x=rows()
  for r in x:r['prices']={a:100 for a in ASSETS}
  r=replay(x,'buy_hold',22,120)
  expected=1600*(1-.001)/(1+.001+.001)*EXIT
  self.assertAlmostEqual(r['terminalLiquidation'],expected)
  self.assertAlmostEqual(r['feesPaid'],1.6)
 def test_future_cannot_change_prior_orders(self):
  x=rows();y=copy.deepcopy(x)
  for r in y[100:]:r['prices']={a:1 for a in ASSETS}
  with patch('strategy_lab.signal',return_value=True):
   a=replay(x,'trend_following',22,100);b=replay(y,'trend_following',22,100)
  self.assertGreater(a['tradeCount'],0)
  self.assertEqual(a,b)
  self.assertTrue(all(t.get('signalThrough','')<t['date'] for t in a['ledger'] if t['action']=='buy'))
 def test_no_input_mutation(self):
  x=rows();old=copy.deepcopy(x);replay(x,'trend_following',22,120);self.assertEqual(x,old)
 def test_global_liquidation_latches_on_gap(self):
  x=rows()
  for r in x[30:]:r['prices']={a:1 for a in ASSETS}
  # Several capped entries before a market-wide gap.
  with patch('strategy_lab.signal',return_value=True):r=replay(x,'trend_following',22,120)
  self.assertTrue(r['liquidationLatched'])
  self.assertTrue(any(t.get('reason')=='global_10_percent' for t in r['ledger']))
  self.assertFalse(any(t['action']=='buy' and t['date']>=x[30]['date'] for t in r['ledger']))
 def test_proxy_flat_data_has_no_signal(self):
  self.assertFalse(signal([100]*30,'current_daily_proxy'))
 def test_one_entry_per_session_and_budget(self):
  with patch('strategy_lab.signal',return_value=True):r=replay(rows(),'trend_following',22,120)
  buys=[t for t in r['ledger'] if t['action']=='buy']
  self.assertTrue(buys);self.assertEqual(len(buys),len(set(t['date'] for t in buys)))
  self.assertTrue(all(t['budget']<=120 for t in buys))

 def test_data_admission_rejects_invalid_price_or_missing_provenance(self):
  import json, tempfile
  from pathlib import Path
  from strategy_lab import load_rows
  for defect in ('price','firstSeen'):
   with tempfile.TemporaryDirectory() as directory:
    for asset in ASSETS:
     source=rows();data={'currency':'EUR','prices':[{'date':r['date'],'price':r['prices'][asset]} for r in source],
       'firstSeen':{r['date']:r['date']+'T23:59:00+00:00' for r in source}}
     if defect=='price':data['prices'][0]['price']=0
     else:data['firstSeen'].pop(source[0]['date'])
     (Path(directory)/(asset+'.json')).write_text(json.dumps(data))
    with self.assertRaises(ValueError):load_rows(Path(directory),dt.datetime(2026,11,17,tzinfo=dt.timezone.utc))
