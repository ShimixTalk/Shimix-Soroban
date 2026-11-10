import copy,datetime as dt,json,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import *
from journal import observe,append,summarize
from collect import build,PREFIX,RESEARCH_HASH
from ai_review import prepare
ROOT=Path(__file__).resolve().parents[2]
NOW=dt.datetime(2026,11,10,12,tzinfo=dt.timezone.utc)
POLICY=json.loads((ROOT/'learning/policy.json').read_text())
def histories(n=180):
 first=NOW.date()-dt.timedelta(days=n)
 rows=[dict(date=(first+dt.timedelta(days=i)).isoformat(),price=100+math.sin(i/7)*8+i*.15) for i in range(n)]
 return {a:copy.deepcopy(rows) for a in set(a for p in PROFILES.values() for a in p['assets'])}
def state():
 return dict(realTradingEnabled=False,exchangeApiConnected=False,readiness=dict(simulationOnly=True,liveOrdersEnabled=False),capital=1600,cash=1500,holdings={'BTC':1},prices={'BTC':100},value=1600,updatedAt=NOW.isoformat(),marketCacheAt=NOW.timestamp(),signals={'BTC':{'action':'Attente','reason':'Fixture'}},trades=[])
class Memory:
 def __init__(self):self.files={};self.states={'a':state()};self.pending=['a'];self.files['hub/trading/three-portfolios.json']=json.dumps(dict(simulationOnly=True,realOrdersEnabled=False,updatedAt=NOW.isoformat(),portfolios=[dict(id=k,name=k,initial=n,cash=n,holdings={},signals={},trades=[],lastPrices={},value=n,netProfit=0,feesPaid=0,updatedAt=NOW.isoformat()) for k,n in [('prudent',640),('equilibre',560),('dynamique',400)]])).encode()
 def file(self,path,ref=None,optional=False):
  if path=='hub/trading/robot-state.json':return json.dumps(self.states[ref]).encode()
  if optional:return self.files.get(path)
  return self.files[path]
 def json(self,path,optional=False):
  b=self.file(path,optional=optional);return json.loads(b) if b else None
 def commits(self,cursor,path='hub/trading/robot-state.json'):
  if path=='hub/trading/three-portfolios.json':return [] if cursor else ['portfolio-a']
  return [] if cursor==self.pending[-1] else self.pending
 def apply(self,files):self.files.update(files)
class LearningTests(unittest.TestCase):
 def test_capital_profiles_unchanged(self):self.assertEqual(sum(p['initial'] for p in PROFILES.values()),1600)
 def test_policy_denies_sensitive_automation(self):
  for key in ['automaticMerge','automaticRiskChanges','automaticLiveTrading']:
   with self.assertRaises(ValueError):policy_check({**POLICY,key:True})
 def test_negative_or_nonfinite_budgets_rejected(self):
  for value in [-1,float('nan'),float('inf'),True]:
   with self.assertRaises(ValueError):policy_check({**POLICY,'openai':dict(enabled=False,monthlyBudgetUsd=value,maxRequestUsd=0)})
 def test_ai_never_calls_even_if_enabled(self):
  for enabled,budget in [(False,0),(True,0),(True,10)]:
   p={**POLICY,'openai':dict(enabled=enabled,monthlyBudgetUsd=budget,maxRequestUsd=0)};r=prepare({},p);self.assertEqual(r['networkCalls'],0);self.assertEqual(r['spentUsd'],0);self.assertFalse(r['apiCallsImplemented'])
 def test_history_rejects_gaps_duplicates_nan(self):
  for rows in [[dict(date='2026-01-01',price=1),dict(date='2026-01-03',price=2)],[dict(date='2026-01-01',price=float('nan'))],[dict(date='2026-01-01',price=1)]*2]:
   with self.assertRaises(ValueError):check_series(rows)
 def test_chart_excludes_today(self):
  rows=[[int((NOW-dt.timedelta(days=i)).replace(hour=0,minute=0,second=0).timestamp()*1000),100] for i in range(30,-1,-1)]
  result=history_from_chart({'prices':rows},NOW);self.assertEqual(len(result),30);self.assertLess(result[-1]['date'],NOW.date().isoformat())
 def test_no_current_point_in_signal(self):
  self.assertEqual(action([100]*30,BASELINE),'Attente')
  rows=align(histories(),'bitcoin ethereum'.split());changed=copy.deepcopy(rows);changed[-1]['prices']['bitcoin']=100000
  self.assertEqual(backtest(rows,'prudent',BASELINE,0,len(rows)-1),backtest(changed,'prudent',BASELINE,0,len(rows)-1))
 def test_test_future_cannot_change_selected_parameters(self):
  h=histories();base=study(h,'prudent',120);start=splits(180)['test'][0]
  changed=copy.deepcopy(h)
  for rows in changed.values():
   for r in rows[start:]:r['price']*=100
  self.assertEqual(base['candidate'],study(changed,'prudent',120)['candidate']);self.assertFalse(base['testUsedForSelection'])
 def test_splits_disjoint_with_embargo(self):
  s=splits(180);a,b,c=[set(range(*s[k])) for k in ['train','validation','test']];self.assertFalse(a&b or b&c or a&c);self.assertEqual(min(b)-max(a),2);self.assertEqual(min(c)-max(b),2)
 def test_short_history_does_not_invent_evidence(self):self.assertEqual(study(histories(31),'dynamique',120)['status'],'insufficient_data')
 def test_terminal_costs_reduce_no_cost_result(self):
  h=histories();rows=align(h,PROFILES['dynamique']['assets']);r=backtest(rows,'dynamique',dict(lookback=7,threshold=0));self.assertGreater(r['fees'],0);self.assertTrue(r['terminalExitIncluded']);self.assertTrue(all(t['signalThrough']<t['date'] for t in r['ledger']))
 def test_observer_never_mutates_source(self):
  s=state();before=copy.deepcopy(s);observe(s,'a',NOW.isoformat());self.assertEqual(s,before)
 def test_real_mode_and_capital_change_rejected(self):
  for patch in [dict(realTradingEnabled=True),dict(capital=1500),dict(exchangeApiConnected=True)]:
   with self.assertRaises(ValueError):observe({**state(),**patch},'a',NOW.isoformat())
 def test_missing_quote_never_values_holding_at_zero(self):
  s=state();s['prices']={};o=observe(s,'a',NOW.isoformat());self.assertIsNone(o['equity']);self.assertTrue(o['errors'])
 def test_duplicate_event_is_idempotent(self):
  o=observe(state(),'a',NOW.isoformat());self.assertEqual(len(append([o],o)),1)
 def test_price_attribution(self):
  a=observe(state(),'a',NOW.isoformat());s=state();s['prices']['BTC']=110;s['value']=1610;b=observe(s,'b',NOW.isoformat());r=summarize([a,b]);self.assertEqual(r['equityAttribution'][0]['priceEffect'],10);self.assertEqual(r['equityAttribution'][0]['executionAndCashEffect'],0)
 def test_unknown_basis_not_reported_as_profit(self):
  s=state();s['trades']=[dict(date=NOW.isoformat(),asset='BTC',action='Vente',price=100,quantity=1,fee=1,amount=100)];r=summarize([observe(s,'a',NOW.isoformat())]);self.assertEqual(r['knownRealizedPnl'],0);self.assertEqual(r['unattributableTrades'],1)
 def test_known_fifo_profit_includes_both_fees(self):
  s=state();s['trades']=[dict(date=(NOW-dt.timedelta(days=1)).isoformat(),asset='BTC',action='Achat',price=90,quantity=1,fee=1),dict(date=NOW.isoformat(),asset='BTC',action='Vente',price=100,quantity=1,fee=1)];r=summarize([observe(s,'a',NOW.isoformat())]);self.assertEqual(r['knownRealizedPnl'],8);self.assertEqual(r['knownFees'],2)
 def test_collector_only_writes_learning_paths(self):
  repo=Memory();before=copy.deepcopy(repo.files);files,report=build(repo,{**POLICY,'historyRequestsPerRun':0},NOW);self.assertTrue(all(p.startswith(PREFIX) for p in files));self.assertEqual(repo.files,before);self.assertEqual(report['referenceCapitalEUR'],1600)
 def test_collector_replay_keeps_one_event_and_frozen_model(self):
  repo=Memory();h=histories();fetch=lambda a,now:h[a];p={**POLICY,'historyRequestsPerRun':2}
  for i in range(3):
   files,report=build(repo,p,NOW+dt.timedelta(minutes=i),fetch);repo.apply(files)
  self.assertIsNotNone(report['experiment']);manifest=repo.files[PREFIX+'experiments/'+p['experimentId']+'.json']
  files,report=build(repo,p,NOW+dt.timedelta(minutes=4),fetch);self.assertNotIn(PREFIX+'experiments/'+p['experimentId']+'.json',files);self.assertEqual(repo.files[PREFIX+'experiments/'+p['experimentId']+'.json'],manifest);self.assertEqual(report['observed']['observations'],1)
 def test_journal_tampering_blocks_collection(self):
  repo=Memory();p={**POLICY,'historyRequestsPerRun':0};files,_=build(repo,p,NOW);repo.apply(files);path=next(k for k in files if k.endswith('.jsonl'));repo.files[path]=repo.files[path].replace(b'1500',b'1499')
  with self.assertRaises(ValueError):build(repo,p,NOW)
 def test_historical_outage_keeps_archived_data(self):
  repo=Memory();p={**POLICY,'historyRequestsPerRun':2};files,_=build(repo,p,NOW,lambda a,n:histories()[a]);repo.apply(files);saved={k:v for k,v in repo.files.items() if '/history/' in k}
  def fail(a,n):raise OSError('unavailable')
  files,r=build(repo,p,NOW+dt.timedelta(minutes=1),fail);self.assertTrue(r['errors']);self.assertTrue(all(k not in files for k in saved))
 def test_forward_waits_for_real_new_dates(self):
  h=histories();f=study(h,'prudent',120);self.assertEqual(future(h,'prudent',f,20)['status'],'waiting_for_new_data')
 def test_large_journal_rolls_segments_without_removing_events(self):
  repo=Memory();p={**POLICY,'historyRequestsPerRun':0};repo.states['a']['signals']={str(i):dict(action='Attente',reason='x'*250) for i in range(900)}
  files,_=build(repo,p,NOW);repo.apply(files);first=next(k for k in files if k.endswith('.jsonl'));saved=repo.files[first]
  repo.states['b']=copy.deepcopy(repo.states['a']);repo.states['b']['updatedAt']=(NOW+dt.timedelta(minutes=1)).isoformat();repo.pending=['a','b']
  files,report=build(repo,p,NOW+dt.timedelta(minutes=2));repo.apply(files)
  self.assertEqual(report['observed']['observations'],2);self.assertEqual(repo.files[first],saved);self.assertEqual(len(repo.json(PREFIX+'index.json')['segments']),2)
 def test_forward_evaluation_requires_twenty_new_days(self):
  h=histories();f=study(h,'prudent',120)
  for rows in h.values():
   end=dt.date.fromisoformat(rows[-1]['date'])
   rows.extend(dict(date=(end+dt.timedelta(days=i)).isoformat(),price=130+i) for i in range(1,21))
  result=future(h,'prudent',f,20);self.assertEqual(result['status'],'forward_observation');self.assertFalse(result['appliedToRobot']);self.assertEqual(result['points'],20)
 def test_github_writer_rejects_protected_paths_before_network(self):
  from collect import GitHub
  repo=GitHub('ShimixTalk/Shimix-Soroban','shimix-hub','test-not-used')
  for path in ['hub/trading/robot-state.json','learning/policy.json','.github/workflows/evil.yml',PREFIX+'../robot-state.json']:
   with self.assertRaises(ValueError):repo.commit({path:b'{}'})
 def test_changed_model_cannot_reuse_frozen_test(self):
  repo=Memory();h=histories()
  for a,rows in h.items():repo.files[PREFIX+'history/'+a+'.json']=json.dumps(dict(currency='EUR',prices=rows,firstSeen={})).encode()
  repo.files[PREFIX+'experiments/'+POLICY['experimentId']+'.json']=json.dumps(dict(researchHash='changed',studies={})).encode()
  with self.assertRaises(ValueError):build(repo,{**POLICY,'historyRequestsPerRun':0},NOW)
 def test_archived_future_prices_are_rejected(self):
  repo=Memory();rows=histories()['bitcoin']
  for r in rows:r['date']=(dt.date.fromisoformat(r['date'])+dt.timedelta(days=2)).isoformat()
  repo.files[PREFIX+'history/bitcoin.json']=json.dumps(dict(currency='EUR',prices=rows,firstSeen={})).encode()
  with self.assertRaises(ValueError):build(repo,{**POLICY,'historyRequestsPerRun':0},NOW)
 def test_shadow_selection_requires_new_evidence_and_never_changes_risk(self):
  study_result=dict(validationSupportsCandidate=True,testSupportsCandidate=True,candidate=dict(lookback=7,threshold=.02),baseline=BASELINE)
  forward_result=dict(status='forward_observation',candidate=dict(trades=5,netReturnPercent=2,maxDrawdownPercent=3),baseline=dict(netReturnPercent=1,maxDrawdownPercent=4))
  suggestion=advisory_selection(study_result,forward_result);self.assertEqual(suggestion['selection'],'candidate');self.assertFalse(suggestion['appliedToRobot']);self.assertFalse(suggestion['riskChanges'])
  self.assertEqual(advisory_selection(study_result,{'status':'waiting_for_new_data'})['selection'],'baseline')
 def test_each_profile_decisions_are_preserved(self):
  repo=Memory();source=repo.json('hub/trading/three-portfolios.json');source['portfolios'][0]['signals']={'BTC':dict(action='Achat',reason='Fixture',estimatedCosts=.1)};repo.files['hub/trading/three-portfolios.json']=json.dumps(source).encode()
  files,report=build(repo,{**POLICY,'historyRequestsPerRun':0},NOW)
  self.assertEqual(report['profileJournal'][0]['decisions'],1);self.assertTrue(any(b'three-portfolios.json' in v for k,v in files.items() if k.endswith('.jsonl')))
 def test_forward_excludes_points_already_available_on_freeze_day(self):
  h=histories();f=study(h,'prudent',120);f['frozenAt']=NOW.isoformat()
  for rows in h.values():
   end=dt.date.fromisoformat(rows[-1]['date']);rows.extend(dict(date=(end+dt.timedelta(days=i)).isoformat(),price=130+i) for i in range(1,21))
  result=future(h,'prudent',f,20);self.assertEqual(result['points'],19);self.assertEqual(result['status'],'waiting_for_new_data')
if __name__=='__main__':unittest.main()
