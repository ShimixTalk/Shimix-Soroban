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
