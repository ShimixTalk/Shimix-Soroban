import copy,datetime as dt,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from journal import observe,observe_portfolios,net_cash_flow
from test_learning import state,NOW,ROOT

class TimingTests(unittest.TestCase):
 def observation(self,age,delay):
  s=state();s['marketCacheAt']=NOW.timestamp()-age
  return observe(s,'fixture',(NOW+dt.timedelta(seconds=delay)).isoformat())
 def test_delayed_collection_does_not_age_execution_quotes(self):
  e=self.observation(30,86400*10)
  self.assertEqual(e['quoteAgeAtExecutionSeconds'],30)
  self.assertEqual(e['collectionDelaySeconds'],864000)
  self.assertNotIn('stale_or_unknown_quotes',[x['code'] for x in e['errors']])
 def test_old_unknown_and_future_quotes_still_alert(self):
  for age in [3601,-1]:
   self.assertIn('stale_or_unknown_quotes',[x['code'] for x in self.observation(age,86400)['errors']])
  for value in [None,True,float('nan'),'invalid']:
   s=state();s['marketCacheAt']=value
   self.assertIn('stale_or_unknown_quotes',[x['code'] for x in observe(s,'fixture',NOW.isoformat())['errors']])
 def test_threshold_and_timezone(self):
  self.assertFalse(self.observation(3600,86400)['errors'])
  s=state();s['updatedAt']=NOW.astimezone(dt.timezone(dt.timedelta(hours=2))).isoformat()
  self.assertEqual(observe(s,'fixture',NOW.isoformat())['quoteAgeAtExecutionSeconds'],0)

class AccountingTests(unittest.TestCase):
 def test_audited_transfer_only_changes_metadata_and_derived_profit(self):
  before=json.loads(subprocess.check_output(['git','show','e39c2a0:hub/trading/three-portfolios.json'],cwd=ROOT))
  after=json.loads((ROOT/'hub/trading/three-portfolios.json').read_text())
  expected=[0,-1.13,-2.88]
  for a,b,w,pnl in zip(before['portfolios'],after['portfolios'],[80,80,40],expected):
   self.assertEqual(net_cash_flow(b),-w);self.assertEqual(b['netProfit'],pnl)
   self.assertEqual({k:v for k,v in b.items() if k not in ['cashFlows','netProfit']},{k:v for k,v in a.items() if k!='netProfit'})
  self.assertEqual(after['totalInitial'],1600);self.assertEqual(after['totalProfit'],-4.01)
  self.assertEqual({k:v for k,v in after.items() if k not in ['portfolios','totalProfit']},{k:v for k,v in before.items() if k not in ['portfolios','totalProfit']})
 def test_observation_recalculates_without_mutation(self):
  s=json.loads((ROOT/'hub/trading/three-portfolios.json').read_text());s['portfolios'][1]['netProfit']=-81.13;before=copy.deepcopy(s)
  e=observe_portfolios(s,'fixture','2026-11-12T12:00:00Z')
  self.assertEqual(s,before);self.assertEqual(e['profiles'][1]['netProfit'],-1.13);self.assertEqual(e['profiles'][1]['publishedNetProfit'],-81.13)
 def test_no_ledger_does_not_hide_trading_loss(self):
  self.assertEqual(net_cash_flow({}),0)
 def test_invalid_or_duplicate_flow_rejected(self):
  f=dict(id='a',amount=-80,at=NOW.isoformat())
  for flows in [[f,f],[dict(f,amount=float('nan'))],[dict(f,amount=True)],[dict(f,at='unknown')],{}]:
   with self.assertRaises(ValueError):net_cash_flow(dict(cashFlows=flows))

class IntegrationGuardTests(unittest.TestCase):
 def test_only_audited_metadata_and_profit_changes_allowed(self):
  from integration_check import audited_portfolio_change
  before=subprocess.check_output(['git','show','e39c2a0:hub/trading/three-portfolios.json'],cwd=ROOT)
  after=json.loads((ROOT/'hub/trading/three-portfolios.json').read_text())
  self.assertTrue(audited_portfolio_change(before,json.dumps(after)))
  for key,value in [('cash',9999),('initial',9999),('stop',1),('history',[]),('trades',[]),('peak',9999)]:
   changed=copy.deepcopy(after);changed['portfolios'][1][key]=value
   self.assertFalse(audited_portfolio_change(before,json.dumps(changed)),key)
