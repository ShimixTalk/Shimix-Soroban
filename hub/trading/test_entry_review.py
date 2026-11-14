import datetime,unittest
import entry_review as policy
import test_robot_regressions as fixtures
from test_robot_regressions import good_state,market
NOW=datetime.datetime.now(datetime.timezone.utc)
def review(**kwargs):
 args=dict(coin_id='bitcoin',closes=list(range(70,101)),current=100,short=97,long=90,fee=.001,spread=.001,slippage=.001,quote_at=NOW.isoformat(),now=NOW)
 args.update(kwargs);return policy.review(**args)
class EntryReviewTests(unittest.TestCase):
 def test_confirmed_uptrend_with_realistic_costs_allowed(self):
  r=review();self.assertTrue(r['allowed']);self.assertFalse(r['prediction']);self.assertGreater(r['theoreticalRewardRisk'],1.5)
 def test_low_rsi_does_not_override_falling_trend(self):
  self.assertFalse(review(short=89,long=90)['allowed'])
 def test_current_price_must_confirm_daily_rebound(self):self.assertFalse(review(current=99)['allowed'])
 def test_flat_last_close_is_not_a_rebound(self):self.assertFalse(review(closes=[100]*31)['allowed'])
 def test_stablecoin_exact_id_rejected_not_similar_name(self):
  self.assertFalse(review(coin_id='usd1-wlfi')['allowed']);self.assertTrue(review(coin_id='usd1-unrelated')['allowed'])
 def test_unknown_stale_or_future_quote_refused(self):
  for stamp in (None,'invalid',NOW.replace(tzinfo=None).isoformat(),(NOW-datetime.timedelta(seconds=901)).isoformat(),(NOW+datetime.timedelta(seconds=61)).isoformat()):
   self.assertFalse(review(quote_at=stamp)['allowed'])
 def test_invalid_history_cannot_signal(self):
  self.assertFalse(review(closes=[100]*20)['allowed']);self.assertFalse(review(current=float('nan'))['allowed'])
 def test_costs_can_invalidate_apparent_reward(self):self.assertFalse(review(fee=.1,spread=.1,slippage=.1)['allowed'])
 def test_sell_review_uses_net_proceeds_and_known_basis_only(self):
  self.assertEqual(policy.exit_review(120,1,114,115)['netPnl'],-6)
  self.assertIsNone(policy.exit_review(None,1,114,115)['netPnl'])
 def test_engine_rejects_stablecoin_but_still_allows_its_stop(self):
  rows=market();rows[0].update(id='usd1-wlfi',symbol='USD1')
  s=good_state();s['assetIds']={'USD1':'usd1-wlfi'}
  r=fixtures.RobotRegressionTests().run_robot(s,rows);self.assertNotIn('USD1',r['holdings'])
  self.assertEqual(r['signals']['USD1']['originalAction'],'Achat')
  self.assertIn('Stablecoin',r['signals']['USD1']['reason'])
  s.update(cash=1500,holdings={'USD1':1},entryPrices={'USD1':120})
  r=fixtures.RobotRegressionTests().run_robot(s,rows,buy=False);self.assertNotIn('USD1',r['holdings'])
  self.assertLess(r['trades'][0]['exitReview']['netPnl'],0)
 def test_trade_retains_entry_reason_without_altering_accounting(self):
  r=fixtures.RobotRegressionTests().run_robot(good_state(),market())
  self.assertEqual(r['cash'],1480);self.assertTrue(r['trades'][0]['entryReview']['allowed'])

 def test_aggressive_rebound_in_falling_trend_is_rejected_by_engine(self):
  s=good_state();s['experimentMode']='aggressive_simulation'
  for i in range(20):
   s['dailyHistory'][f'coin-{i}']=[100]*24+[99,98,97,96,97,98,99]
   s['historyUpdated'][f'coin-{i}']=NOW.timestamp()
  r=fixtures.RobotRegressionTests().run_robot(s,market())
  self.assertEqual(r['trades'],[]);self.assertEqual(r['signals']['C0']['originalAction'],'Achat')
  self.assertIn('Tendance haussière non confirmée',r['signals']['C0']['reason'])
 def test_global_liquidation_trace_does_not_invent_missing_basis(self):
  import autonomous_simulation as robot
  s=good_state();s.update(cash=1000,holdings={'C0':1})
  robot.global_protection(s,{'C0':100},NOW.isoformat())
  self.assertIsNone(s['trades'][0]['exitReview']['netPnl']);self.assertFalse(s['trades'][0]['exitReview']['basisKnown'])
