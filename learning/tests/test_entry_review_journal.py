import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_learning import state,NOW
from journal import observe,summarize
class EntryReviewJournalTests(unittest.TestCase):
 def test_reason_is_retained_without_mutating_source(self):
  s=state();s['entryReviewVersion']='confirmed-entry-v1'
  s['signals']['BTC']['entryReview']=dict(version='confirmed-entry-v1',allowed=False,reasons=['Rebond invalidé'],prediction=False,theoreticalRewardRisk=1.7,arbitrary='not exported')
  before=copy.deepcopy(s);e=observe(s,'fixture',NOW.isoformat());summary=summarize([e])
  self.assertEqual(s,before);r=summary['entryReview']['decisions'][0]
  self.assertFalse(r['allowed']);self.assertEqual(r['reasons'],['Rebond invalidé']);self.assertNotIn('arbitrary',r)
 def test_legacy_observation_does_not_invent_review(self):
  r=summarize([observe(state(),'fixture',NOW.isoformat())])['entryReview']
  self.assertIsNone(r['version']);self.assertEqual(r['decisions'],[])

 def test_delayed_collection_is_not_a_stale_execution_quote(self):
  import datetime as dt
  s=state();at=NOW-dt.timedelta(hours=2);s['updatedAt']=at.isoformat();s['marketCacheAt']=at.timestamp()-300
  e=observe(s,'delayed',NOW.isoformat())
  self.assertEqual(e['quoteCacheAgeAtExecutionSeconds'],300);self.assertEqual(e['collectionDelaySeconds'],7200)
  self.assertFalse(any(x['code']=='stale_or_unknown_quotes' for x in e['errors']))
 def test_genuinely_stale_execution_quote_remains_flagged(self):
  s=state();s['marketCacheAt']=NOW.timestamp()-3601
  e=observe(s,'stale',NOW.isoformat())
  self.assertTrue(any(x['code']=='stale_or_unknown_quotes' for x in e['errors']))
