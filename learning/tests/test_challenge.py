import copy,datetime as dt,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from challenge import advance,update,RULES
T=dt.datetime(2026,11,14,10,tzinfo=dt.timezone.utc)
def event(minutes=0,price=100,action='Achat'):
 at=T+dt.timedelta(minutes=minutes)
 return dict(source='robot-state.json',simulationOnly=True,at=at.isoformat(),quotesFetchedAt=at.timestamp(),prices={'BTC':price},signals=[dict(asset='BTC',action=action)])
def run(s,e):return advance(s,e,e['at'])
class ChallengeTests(unittest.TestCase):
 def test_prospective_bootstrap_never_replays_history(self):
  events=[event(),event(10),event(20)];s=update(None,events,events[-1]['at'])
  self.assertEqual(s['cash'],1600);self.assertEqual(s['trades'],[]);self.assertEqual(s['startedAt'],events[-1]['at'])
 def test_signal_executes_later_with_own_costs(self):
  first=event();before=copy.deepcopy(first);s=run(None,first);prior=copy.deepcopy(s);s=run(s,event(10))
  self.assertEqual(first,before);self.assertEqual(prior['cash'],1600)
  self.assertEqual(s['cash'],1480);self.assertEqual(len(s['trades']),1)
  self.assertLess(s['trades'][0]['signalAt'],s['trades'][0]['at']);self.assertLess(s['netEquity'],1600)
 def test_duplicate_or_old_observation_is_idempotent(self):
  s=run(run(None,event()),event(10));self.assertEqual(run(s,event(10)),s);self.assertEqual(run(s,event()),s)
 def test_missing_quote_never_valued_zero(self):
  s=run(run(None,event()),event(10));e=event(20);e['prices']={};r=run(s,e)
  self.assertIsNone(r['netEquity']);self.assertEqual(r['holdings'],s['holdings']);self.assertEqual(r['trades'],s['trades'])
 def test_stale_source_blocks_trading(self):
  s=run(None,event());e=event(10);e['quotesFetchedAt']-=3601;r=run(s,e)
  self.assertTrue(r['issues']);self.assertEqual(r['trades'],[])
 def test_daily_loss_latches_and_liquidates(self):
  s=run(run(None,event()),event(10));r=run(s,event(20,price=50))
  self.assertEqual(r['status'],'failed_daily_loss');self.assertEqual(r['holdings'],{});self.assertLess(r['cash'],1552)
  self.assertEqual(run(r,event(30))['trades'],r['trades'])
 def test_total_loss_has_priority(self):
  s=run(run(None,event()),event(10));r=run(s,event(20,price=1))
  self.assertEqual(r['status'],'failed_total_loss');self.assertLess(r['cash'],1504)
 def test_stop_does_not_rebuy_same_pass(self):
  s=run(run(None,event()),event(10));r=run(s,event(20,price=95))
  self.assertEqual(r['holdings'],{});self.assertEqual([x['action'] for x in r['trades']],['Achat','Vente'])
 def test_old_signal_is_not_traded_after_gap(self):
  self.assertEqual(run(run(None,event()),event(70))['trades'],[])
 def test_frozen_rules_cannot_silently_change(self):
  s=run(None,event());s['rules']['dailyLossPercent']=50
  with self.assertRaises(ValueError):run(s,event(10))
 def test_future_or_real_source_refused(self):
  e=event();e['simulationOnly']=False
  with self.assertRaises(ValueError):run(None,e)
  with self.assertRaises(ValueError):advance(None,event(10),event()['at'])
 def test_day_change_uses_previous_observed_net(self):
  s=run(None,event());s['day']='2026-11-13';s['netEquity']=1590
  r=run(s,event(10));self.assertEqual(r['dayStartNet'],1590)
 def test_target_requires_minimum_days_and_closes(self):
  s=run(run(None,event()),event(10));r=run(s,event(20,price=300))
  self.assertEqual(r['status'],'running')
  s['tradingDays']=['2026-11-09','2026-11-10','2026-11-11','2026-11-12','2026-11-13']
  r=run(s,event(20,price=300));self.assertEqual(r['status'],'educational_target_reached');self.assertEqual(r['holdings'],{})
 def test_missing_prior_close_requires_review_on_new_day(self):
  s=run(None,event());s['day']='2026-11-13';s['netEquity']=None
  self.assertEqual(run(s,event(10))['status'],'review_required')

class SignalAvailabilityTests(unittest.TestCase):
 def test_delayed_collection_cannot_execute_before_actual_availability(self):
  s=advance(None,event(),event(20)['at'])
  self.assertEqual(s['startedAt'],event(20)['at'])
  s=advance(s,event(10),event(30)['at']);self.assertEqual(s['trades'],[])
  s=advance(s,event(40),event(50)['at'])
  self.assertEqual(len(s['trades']),1)
  self.assertLess(s['trades'][0]['signalAvailableAt'],s['trades'][0]['at'])
 def test_legacy_pending_intent_migration_preserves_money_and_history(self):
  s=run(None,event());s.pop('pendingAvailableAt');before=copy.deepcopy(s)
  r=update(s,[event()],event(20)['at'])
  for k in ('cash','holdings','trades','netEquity','startedAt'):self.assertEqual(r[k],before[k])
  self.assertEqual(r['pending'],[]);self.assertIsNone(r['lastSignalAt'])

class ChallengeIntegrationTests(unittest.TestCase):
 def test_collector_persists_independent_account_without_touching_sources(self):
  from test_learning import Memory,POLICY,NOW
  from collect import build,PREFIX
  repo=Memory();before=copy.deepcopy(repo.states)
  files,report=build(repo,{**POLICY,'historyRequestsPerRun':0},NOW)
  c=report['parallelChallenge'];self.assertEqual(c['cash'],1600);self.assertEqual(c['holdings'],{})
  self.assertEqual(repo.states,before);self.assertIn(PREFIX+'parallel-challenge.json',files)
  repo.apply(files);again,r=build(repo,{**POLICY,'historyRequestsPerRun':0},NOW)
  self.assertEqual(c,r['parallelChallenge']);self.assertEqual(repo.states,before)
 def test_corrupt_account_never_trades(self):
  for patch in ({'cash':float('nan')},{'holdings':{'BTC':-1}},{'status':'unlocked'}):
   s=run(None,event());s.update(patch)
   with self.assertRaises(ValueError):run(s,event(10))
