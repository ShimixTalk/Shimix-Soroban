"""Scheduling fairness without extra HTTP requests or fabricated history freshness."""
import unittest
import autonomous_simulation as robot
import test_robot_regressions as fixtures
from test_robot_regressions import good_state, market
class HistoryRotationTests(unittest.TestCase):
 def test_failures_release_next_two_slots(self):
  rows=market()[:6];attempted={}
  batches=[]
  for now in (100000,100001,100002):
   batch=robot.history_refresh_queue(rows,{}, {},attempted,now)[:2]
   batches.append([x['id'] for x in batch])
   attempted.update({x['id']:now for x in batch})
  self.assertEqual(batches,[['coin-0','coin-1'],['coin-2','coin-3'],['coin-4','coin-5']])
 def test_valid_history_needs_no_request(self):
  self.assertEqual(robot.history_refresh_queue(market()[:1],{'coin-0':[1]*22},{'coin-0':99999},{},100000),[])
 def test_future_and_boundary_history_need_refresh(self):
  for stamp in (100001,13600):
   self.assertEqual(len(robot.history_refresh_queue(market()[:1],{'coin-0':[1]*22},{'coin-0':stamp},{},100000)),1)
 def test_attempt_is_not_success(self):
  s=good_state();s['historyAttempted']={'coin-0':99999}
  self.assertEqual(len(robot.history_refresh_queue(market()[:1],{}, {},s['historyAttempted'],100000)),1)
  self.assertEqual(s['historyUpdated'],{})
 def test_invalid_attempt_timestamp_rejected(self):
  for v in (float('nan'),-1,'yesterday'):
   with self.assertRaises(ValueError):robot.validate_simulation_state({**good_state(),'historyAttempted':{'coin-0':v}})
 def test_engine_persists_attempts_with_two_request_limit(self):
  runner=fixtures.RobotRegressionTests();result=runner.run_robot(good_state(),market())
  self.assertEqual(len(result['historyAttempted']),2)
  self.assertEqual(len(result['historyUpdated']),2)

class RelevantHistoryTests(unittest.TestCase):
 def test_exclusions_cannot_take_allowed_slots(self):
  rows=[{'id':'tether','symbol':'usdt'},{'id':'unknown','symbol':'btc'},
        {'id':'bitcoin','symbol':'btc'},{'id':'solana','symbol':'sol'}]
  selected=robot.history_refresh_candidates(rows,good_state())
  self.assertEqual([x['id'] for x in robot.history_refresh_queue(rows,{}, {},{},100000,{x["id"] for x in selected})[:2]],['bitcoin','solana'])
 def test_held_excluded_identity_retained_only_with_matching_symbol(self):
  state=good_state();state['holdings']={'XYZ':2};state['assetIds']={'XYZ':'legacy'}
  rows=[{'id':'legacy','symbol':'xyz'},{'id':'legacy','symbol':'other'},{'id':'unknown','symbol':'xyz'}]
  self.assertEqual(robot.history_refresh_candidates(rows,state),rows[:1])
 def test_no_position_does_not_reserve_history(self):
  state=good_state();state['holdings']={'XYZ':0};state['assetIds']={'XYZ':'legacy'}
  self.assertEqual(robot.history_refresh_candidates([{'id':'legacy','symbol':'xyz'}],state),[])
 def test_relevant_failures_rotate_without_extra_requests(self):
  rows=[{'id':k,'symbol':v} for k,v in list(robot.ENTRY_ASSET_IDS.items())[:4]]
  selected=robot.history_refresh_candidates(rows,good_state());attempts={};batches=[]
  for now in (100000,100001):
   batch=robot.history_refresh_queue(selected,{}, {},attempts,now)[:2]
   batches.extend(x['id'] for x in batch);attempts.update({x['id']:now for x in batch})
  self.assertEqual(batches,[x['id'] for x in rows])
 def test_existing_freshness_still_applies(self):
  row={'id':'bitcoin','symbol':'btc'}
  selected=robot.history_refresh_candidates([row],good_state())
  self.assertEqual(robot.history_refresh_queue(selected,{'bitcoin':[1]*22},{'bitcoin':99999},{},100000),[])
