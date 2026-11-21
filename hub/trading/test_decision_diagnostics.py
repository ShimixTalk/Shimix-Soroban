import datetime as dt, unittest
from decision_diagnostics import diagnose

class DiagnosticsTests(unittest.TestCase):
 def state(self):
  stamp='2026-11-16T03:00:00+00:00';now=dt.datetime.fromisoformat(stamp)
  return {'updatedAt':stamp,'scanner':{'updatedAt':stamp,'shortlist':[{'symbol':'BTC'},{'symbol':'USD1'}]},'assetIds':{'BTC':'bitcoin','USD1':'usd1-wlfi'},'ownerAssetPolicy':{'version':1,'allowedAssetIds':['bitcoin']},'dailyHistory':{'bitcoin':list(range(100,131))},'historyUpdated':{'bitcoin':now.timestamp()},'signals':{'BTC':{'action':'Attente','reason':'RSI et moyennes mobiles','rsi':23,'sma7':90,'sma21':100}},'holdingQuoteCoverage':{'checkedAt':stamp,'missingAssets':[]},'globalProtection':{'valuationComplete':True}}
 def test_excluded_is_not_reported_as_trade_or_profit(self):
  r=diagnose(self.state(),{},dt.datetime(2026,11,16,4,tzinfo=dt.timezone.utc))
  self.assertEqual(r['excludedShortlistCount'],1);self.assertEqual(r['snapshotAgeSeconds'],3600)
  self.assertFalse(r['decisions'][0]['buyPredicates']['shortAverageAboveLong'])
  self.assertIsNone(r['attributableSalesOnly'])
 def test_stale_history_not_replayed(self):
  s=self.state();s['historyUpdated']['bitcoin']-=86401
  self.assertIsNone(diagnose(s,{},dt.datetime.now(dt.timezone.utc))['decisions'][0]['buyPredicates'])
 def test_misaligned_scanner_and_coverage_stay_visible(self):
  s=self.state();s['scanner']['updatedAt']='old';s['holdingQuoteCoverage']['checkedAt']='old'
  r=diagnose(s,{},dt.datetime.now(dt.timezone.utc))
  self.assertFalse(r['quoteEvidence']['coverageAligned']);self.assertIsNone(r['decisions'][0]['buyPredicates'])
 def test_unknown_policy_is_not_assumed_allowed(self):
  s=self.state();s.pop('ownerAssetPolicy')
  self.assertEqual(diagnose(s,{},dt.datetime.now(dt.timezone.utc))['unknownUniverseCount'],2)
 def test_does_not_mutate_inputs(self):
  import copy
  s=self.state();original=copy.deepcopy(s);diagnose(s,{},dt.datetime.now(dt.timezone.utc));self.assertEqual(s,original)

 def test_old_success_does_not_mean_robot_is_running(self):
  from decision_diagnostics import runtime_health
  now=dt.datetime(2026,11,16,15,tzinfo=dt.timezone.utc)
  run={'id':1,'path':'.github/workflows/shimix-trading-simulation.yml','created_at':'2026-11-16T12:08:01Z','status':'completed','conclusion':'success'}
  r=runtime_health(self.state(),now,{'workflow_runs':[run]})
  self.assertEqual(r['schedulerEvidence'],'no_recent_run_visible')
  self.assertEqual(r['snapshotFreshness'],'stale');self.assertEqual(r['cause'],'unconfirmed')
 def test_other_profile_run_is_not_main_robot_heartbeat(self):
  from decision_diagnostics import runtime_health
  run={'path':'.github/workflows/shimix-trading-paper.yml','created_at':'2026-11-16T14:59:00Z','status':'in_progress'}
  r=runtime_health(self.state(),dt.datetime(2026,11,16,15,tzinfo=dt.timezone.utc),{'workflow_runs':[run]})
  self.assertEqual(r['schedulerEvidence'],'no_matching_run_in_supplied_page')
 def test_unknown_or_future_timestamp_is_not_recent(self):
  from decision_diagnostics import runtime_health
  for stamp in [None,'invalid','2027-01-01T00:00:00Z']:
   self.assertEqual(runtime_health({'updatedAt':stamp},dt.datetime(2026,11,16,tzinfo=dt.timezone.utc))['snapshotFreshness'],'unknown')
 def test_recent_run_can_coexist_with_stale_snapshot(self):
  from decision_diagnostics import runtime_health
  run={'path':'.github/workflows/shimix-trading-simulation.yml','created_at':'2026-11-16T14:59:00Z','status':'in_progress'}
  r=runtime_health(self.state(),dt.datetime(2026,11,16,15,tzinfo=dt.timezone.utc),{'workflow_runs':[run]})
  self.assertEqual(r['schedulerEvidence'],'nonterminal_run_visible');self.assertEqual(r['snapshotFreshness'],'stale')

 def test_failed_trend_is_explained_without_claiming_bad_refusal(self):
  r=diagnose(self.state(),{},dt.datetime.now(dt.timezone.utc))
  e=r['decisions'][0]['buyExplanation']
  self.assertEqual(e['signalAssessment'],'signal_predicates_fail')
  self.assertIn('shortAverageAboveLong',e['strictConditionsFailed'])
  self.assertEqual(e['economicQualityOfRefusal'],'undetermined')
  self.assertEqual(r['allowedSignalSummary']['signal_predicates_fail'],1)
 def test_rebound_route_can_pass_when_strict_route_fails(self):
  s=self.state();s['experimentMode']='aggressive_simulation'
  s['signals']['BTC'].update(rsi=40,sma7=99,sma21=100)
  e=diagnose(s,{},dt.datetime.now(dt.timezone.utc))['decisions'][0]['buyExplanation']
  self.assertEqual(e['signalAssessment'],'signal_predicates_pass')
  self.assertTrue(e['strictConditionsFailed']);self.assertEqual(e['reboundConditionsFailed'],[])
  self.assertEqual(e['orderEligibility'],'not_reconstructed')
 def test_stale_data_is_not_called_a_failed_signal(self):
  s=self.state();s['historyUpdated']['bitcoin']-=86400
  e=diagnose(s,{},dt.datetime.now(dt.timezone.utc))['decisions'][0]['buyExplanation']
  self.assertEqual(e['signalAssessment'],'not_assessable')
  self.assertIn('history_stale',e['dataAndUniverseBlockers'])
  self.assertIsNone(e['strictConditionsFailed'])
