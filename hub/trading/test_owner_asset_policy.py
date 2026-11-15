"""Owner-requested paper exit: no HTTP or published state writes."""
import copy, datetime, unittest
import autonomous_simulation as robot
from test_robot_regressions import good_state

class OwnerAssetPolicyTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime.datetime.now(datetime.timezone.utc)
  self.state=good_state();self.state.update(cash=1457.888487,holdings={'USD1':132.8059002617187},entryPrices={'USD1':120/132.8059002617187},assetIds={'USD1':'usd1-wlfi'})
  self.row={'id':'usd1-wlfi','symbol':'usd1','last_updated':self.now.isoformat()}
 def test_net_exit_is_once_and_not_conditioned_on_profit(self):
  q=self.state['holdings']['USD1'];before=self.state['cash']
  self.assertEqual(robot.owner_requested_exits(self.state,{'USD1':.89},[self.row],self.now),{'USD1'})
  self.assertAlmostEqual(self.state['cash'],before+q*.89*.998*.999)
  self.assertLess(self.state['trades'][0]['exitReview']['netPnl'],0)
  self.assertEqual(self.state['trades'][0]['reason'],'owner-stablecoin-exit')
  robot.owner_requested_exits(self.state,{'USD1':.89},[self.row],self.now)
  self.assertEqual(len(self.state['trades']),1)
 def test_unusable_quotes_leave_cash_and_quantity_untouched(self):
  for price,rows in [(None,[self.row]),(float('nan'),[self.row]),(.9,[]),(.9,[{**self.row,'symbol':'OTHER'}]),(.9,[{**self.row,'last_updated':(self.now-datetime.timedelta(seconds=901)).isoformat()}]),(.9,[self.row,self.row])]:
   s=copy.deepcopy(self.state);robot.owner_requested_exits(s,{'USD1':price},rows,self.now)
   self.assertEqual(s['cash'],self.state['cash']);self.assertEqual(s['holdings'],self.state['holdings'])
   self.assertEqual(s['ownerAssetPolicy']['pendingExits'],['USD1'])
 def test_missing_cost_never_assumed_zero(self):
  del self.state['feeRate'];robot.owner_requested_exits(self.state,{'USD1':.9},[self.row],self.now)
  self.assertEqual(self.state['trades'],[])
 def test_id_not_ticker_controls_exit(self):
  self.state['assetIds']['USD1']='different-asset'
  robot.owner_requested_exits(self.state,{'USD1':.9},[self.row],self.now)
  self.assertEqual(self.state['trades'],[])
 def test_entry_universe_fails_closed_for_unknown_and_collisions(self):
  for row in [{'id':'usd1-wlfi','symbol':'USD1'},{'id':'unknown-stable','symbol':'BTC'},{'id':'bitcoin','symbol':'USD1'}]:self.assertFalse(robot.entry_asset_allowed(row))
  self.assertTrue(robot.entry_asset_allowed({'id':'bitcoin','symbol':'btc'}))
 def test_supplemental_quote_can_complete_exit(self):
  self.state['holdingQuoteCoverage']={'supplementalQuotes':{'USD1':{'coinId':'usd1-wlfi','providerUpdatedAt':self.now.isoformat()}}}
  self.assertEqual(robot.owner_requested_exits(self.state,{'USD1':.9},[],self.now),{'USD1'})
 def test_engine_checkpoints_exit_before_history_and_keeps_cash(self):
  from unittest.mock import patch
  from test_robot_regressions import market
  from test_fast_risk_analysis import FastRiskTests
  rows=market();rows[0].update(self.row,current_price=.9)
  runner=FastRiskTests()
  with patch('test_fast_risk_analysis.market',return_value=rows):
   result=runner.run_engine(self.state,rebuy_signal=True)
  self.assertLess(runner.events.index('save'),runner.events.index('history'))
  self.assertEqual([t['action'] for t in result['trades']],['Vente'])
  self.assertEqual(result['holdings'],{})
  self.assertAlmostEqual(result['cash'],1457.888487+132.8059002617187*.9*.998*.999,places=5)
 def test_latched_portfolio_does_not_resume_for_owner_exit(self):
  from test_fast_risk_analysis import FastRiskTests
  self.state['globalProtection']={'liquidationLatched':True,'requiresApprovalToResume':True}
  self.state['enabled']=False
  result=FastRiskTests().run_engine(self.state)
  self.assertTrue(result['globalProtection']['requiresApprovalToResume'])
  self.assertFalse(result['enabled'])
