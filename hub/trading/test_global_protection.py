"""No live calls: test protection boundaries, fees, missing quotes and durable halt."""
import copy,unittest
import autonomous_simulation as robot
from test_robot_regressions import good_state,market
import test_robot_regressions as fixtures
AT='2026-11-13T04:00:00Z'

class GlobalProtectionTests(unittest.TestCase):
 def run_engine(self,state,quotes=None):return fixtures.RobotRegressionTests.run_robot(self,state,market() if quotes is None else quotes)
 def test_exact_pause_boundary_and_above(self):
  for cash,allowed in [(1520,False),(1520.00001,True)]:
   s={**good_state(),'cash':cash};a,panic=robot.global_protection(s,{},AT)
   self.assertEqual(a,allowed);self.assertFalse(panic);self.assertTrue(s['enabled'])
 def test_exact_liquidation_boundary_and_above(self):
  for cash,latched in [(1440,True),(1440.00001,False)]:
   s={**good_state(),'cash':cash};a,panic=robot.global_protection(s,{},AT)
   self.assertEqual(panic,latched);self.assertFalse(a)
   self.assertEqual(s['globalProtection']['requiresApprovalToResume'],latched)
 def test_exit_costs_can_trigger_before_marked_value_threshold(self):
  s={**good_state(),'cash':1300,'holdings':{'C0':1.41},'entryPrices':{'C0':100}}
  # Marked equity 1441, but liquidation 1440.577... remains above 1440.
  self.assertGreater(robot.net_liquidation_value(s,{'C0':100}),1440)
  s['cash']=1299.4
  self.assertGreater(s['cash']+141,1440)
  self.assertTrue(robot.global_protection(s,{'C0':100},AT)[1])
 def test_entry_pause_keeps_position_stop_active(self):
  s={**good_state(),'cash':1400,'holdings':{'C0':1},'entryPrices':{'C0':120}}
  result=self.run_engine(s)
  self.assertEqual([t['action'] for t in result['trades']],['Vente'])
  self.assertTrue(result['enabled']);self.assertTrue(result['globalProtection']['buyPaused'])
  self.assertAlmostEqual(result['cash'],1499.7002)
 def test_liquidation_sells_all_and_counts_costs_once(self):
  s={**good_state(),'cash':1300,'holdings':{'C0':1,'C1':.2},'entryPrices':{'C0':100,'C1':100}}
  old=copy.deepcopy(s);result=self.run_engine(s)
  self.assertEqual(s,old);self.assertEqual(result['holdings'],{})
  self.assertAlmostEqual(result['cash'],1300+120*.998*.999,places=6)
  self.assertEqual(len(result['trades']),2);self.assertTrue(all(t['reason']=='global-loss-liquidation' for t in result['trades']))
  self.assertFalse(result['enabled']);self.assertTrue(result['globalProtection']['requiresApprovalToResume'])
 def test_no_automatic_restart_after_rebound_or_enabled_flag(self):
  s={**good_state(),'cash':1600,'globalProtection':{'liquidationLatched':True,'requiresApprovalToResume':True}}
  result=self.run_engine(s)
  self.assertFalse(result['enabled']);self.assertEqual(result['trades'],[])
 def test_partial_liquidation_is_retryable_without_duplicate_sales(self):
  s={**good_state(),'enabled':False,'cash':1300,'holdings':{'C0':1,'C1':.2},'entryPrices':{'C0':100,'C1':100},'globalProtection':{'liquidationLatched':True,'requiresApprovalToResume':True}}
  quotes=[r for r in market() if r['symbol']!='C1'];extra=copy.deepcopy(quotes[-1]);extra.update(id='coin-extra',symbol='EXTRA');quotes.append(extra)
  first=self.run_engine(s,quotes)
  self.assertEqual(first['holdings'],{'C1':.2});self.assertEqual(first['globalProtection']['pendingAssets'],['C1'])
  self.assertIsNone(first['value']);self.assertFalse(first['globalProtection']['valuationComplete'])
  second=self.run_engine(first)
  self.assertEqual(second['holdings'],{});self.assertEqual(len(second['trades']),2)
  self.assertEqual({t['asset'] for t in second['trades']},{'C0','C1'})
  self.assertAlmostEqual(second['cash'],1300+120*.998*.999,places=6)
 def test_unknown_quote_does_not_invent_a_zero_price_or_trigger(self):
  s={**good_state(),'cash':1300,'holdings':{'UNKNOWN':2}}
  result=self.run_engine(s)
  self.assertEqual(result['holdings'],s['holdings']);self.assertEqual(result['trades'],[])
  self.assertIsNone(result['value']);self.assertFalse(result['globalProtection'].get('liquidationLatched',False))
  self.assertTrue(result['globalProtection']['buyPaused'])
 def test_market_outage_preserves_pending_protection(self):
  s={**good_state(),'enabled':False,'holdings':{'C0':1},'globalProtection':{'liquidationLatched':True,'requiresApprovalToResume':True}}
  result=self.run_engine(s,[{}])
  self.assertEqual(result['holdings'],s['holdings']);self.assertTrue(result['globalProtection']['liquidationLatched'])
 def test_costs_of_new_buy_cannot_cross_pause_boundary(self):
  s={**good_state(),'cash':1420.4998,'holdings':{'C0':1},'entryPrices':{'C0':100}}
  self.assertGreater(robot.net_liquidation_value(s,{'C0':100}),1520)
  result=self.run_engine(s)
  self.assertEqual(result['trades'],[]);self.assertTrue(result['globalProtection']['buyPaused'])
 def test_pause_can_lift_on_recovery_but_emergency_cannot(self):
  s={**good_state(),'cash':1420,'holdings':{'C0':1}}
  self.assertFalse(robot.global_protection(s,{'C0':100},AT)[0])
  self.assertTrue(robot.global_protection(s,{'C0':106},AT)[0])
 def test_preserves_reference_risk_limits_and_history(self):
  old_trade=dict(date='2026-11-01T00:00:00Z',asset='OLD',action='Achat',amount=1)
  s={**good_state(),'cash':1400,'holdings':{'C0':.1},'trades':[old_trade],
     'equityHistory':[{'at':'2026-11-01T00:00:00Z','equity':1600,'cash':1600}]}
  result=self.run_engine(s)
  self.assertEqual(result['capital'],1600);self.assertEqual(result['maxOrder'],120)
  self.assertEqual(result['maxPositionPercent'],20);self.assertEqual(result['maxPositions'],8)
  self.assertIn(old_trade,result['trades']);self.assertEqual(result['equityHistory'][0],s['equityHistory'][0])
  self.assertEqual(result['maxLossPercent'],10);self.assertEqual(result['buyPauseLossPercent'],5)
 def test_invalid_latch_and_live_mode_rejected(self):
  for patch in [{'globalProtection':{'liquidationLatched':'false'}},{'realTradingEnabled':True}]:
   with self.assertRaises(ValueError):self.run_engine({**good_state(),**patch})

 def test_invalid_quotes_never_liquidated_at_zero(self):
  for price in [0,-1,float('nan'),float('inf'),True]:
   s={**good_state(),'cash':1300,'holdings':{'C0':1},'globalProtection':{'liquidationLatched':True,'requiresApprovalToResume':True}}
   robot.global_protection(s,{'C0':price},AT)
   self.assertEqual(s['holdings'],{'C0':1});self.assertEqual(s['trades'],[])
 def test_inconsistent_approval_flag_rejected(self):
  with self.assertRaises(ValueError):self.run_engine({**good_state(),'globalProtection':{'requiresApprovalToResume':True,'liquidationLatched':False}})
