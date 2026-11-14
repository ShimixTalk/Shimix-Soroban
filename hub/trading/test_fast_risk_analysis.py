"""Prove save-before-download ordering without real HTTP requests or wall-clock sleeps."""
import base64,copy,datetime,json,unittest
from unittest.mock import patch
import autonomous_simulation as robot
from test_robot_regressions import good_state,market

class FastRiskTests(unittest.TestCase):
 def run_engine(self,state,fail_history=False,checkpoint_confirmed=True,rebuy_signal=False):
  self.events=[];self.saved=[];now=datetime.datetime.now(datetime.timezone.utc);start=int(now.timestamp())//86400-31
  def get(method,body=None):
   self.assertEqual(method,'GET');return dict(sha='original',content=base64.b64encode(json.dumps(state).encode()).decode())
  def request(url,*args):
   if '/coins/markets?' in url:self.events.append('market');return market()
   self.events.append('history')
   if fail_history:raise TimeoutError('synthetic historical timeout')
   offset=200 if rebuy_signal and '/coin-0/' in url else 100
   return {'prices':[[(start+i)*86400000,offset+i] for i in range(31)]}
  def save(value,sha):
   self.events.append('save');self.saved.append((copy.deepcopy(value),sha))
   return 'saved-'+str(len(self.saved)) if checkpoint_confirmed else None
  def rsi(p):return 30 if rebuy_signal and p[-1]>200 else 70
  with patch.object(robot,'gh',side_effect=get),patch.object(robot,'request',side_effect=request),patch.object(robot,'save',side_effect=save),patch.object(robot.time,'sleep'),patch.object(robot,'rsi',side_effect=rsi):robot.main()
  return self.saved[-1][0]
 def exiting_state(self):return {**good_state(),'cash':1500,'holdings':{'C0':1},'entryPrices':{'C0':120}}
 def test_exit_is_saved_before_first_history_request(self):
  result=self.run_engine(self.exiting_state())
  self.assertLess(self.events.index('save'),self.events.index('history'))
  first,first_sha=self.saved[0];self.assertEqual(first_sha,'original')
  self.assertEqual(first['holdings'],{});self.assertEqual(first['signals'],{})
  self.assertEqual(first['trades'][0]['reason'],'stop-loss')
  self.assertAlmostEqual(first['cash'],1599.7002)
  self.assertEqual(len(result['trades']),1)
 def test_second_save_uses_new_content_sha(self):
  self.run_engine(self.exiting_state());self.assertEqual([sha for _,sha in self.saved],['original','saved-1'])
 def test_history_outage_does_not_delay_or_undo_exit(self):
  result=self.run_engine(self.exiting_state(),fail_history=True)
  self.assertLess(self.events.index('save'),self.events.index('history'))
  self.assertEqual(result['holdings'],{});self.assertEqual(len(result['trades']),1);self.assertTrue(result['dataErrors'])
 def test_no_analysis_after_unconfirmed_checkpoint(self):
  with self.assertRaises(ValueError):self.run_engine(self.exiting_state(),checkpoint_confirmed=False)
  self.assertNotIn('history',self.events);self.assertEqual(len(self.saved),1)
 def test_fresh_quote_cache_is_reused(self):
  s={**good_state(),'marketCache':market(),'marketCacheAt':datetime.datetime.now(datetime.timezone.utc).timestamp()-899}
  self.run_engine(s);self.assertNotIn('market',self.events)
 def test_fifteen_minute_cache_is_refreshed(self):
  s={**good_state(),'marketCache':market(),'marketCacheAt':datetime.datetime.now(datetime.timezone.utc).timestamp()-901}
  self.run_engine(s);self.assertEqual(self.events.count('market'),1)
 def test_no_extra_checkpoint_without_price_exit(self):
  self.run_engine(good_state());self.assertEqual(len(self.saved),1)
  self.assertLessEqual(self.events.count('history'),2);self.assertEqual(self.events.count('market'),1)
 def test_no_immediate_rebuy_after_early_exit(self):
  result=self.run_engine(self.exiting_state(),rebuy_signal=True)
  self.assertEqual([t['action'] for t in result['trades']],['Vente'])
  self.assertNotIn('C0',result['holdings'])
 def test_save_requires_github_content_sha(self):
  with patch.object(robot,'gh',return_value={'content':{'sha':'new-sha'}}) as call:
   self.assertEqual(robot.save(good_state(),'old-sha'),'new-sha')
   self.assertEqual(call.call_args.args[1]['sha'],'old-sha')
  with patch.object(robot,'gh',return_value={}):
   with self.assertRaises(ValueError):robot.save(good_state(),'old-sha')
