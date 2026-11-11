import copy,datetime as dt,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from journal import observe
from engine import digest
from shadow_compare import compare,load_events,RISK
PLAN=json.loads((Path(__file__).resolve().parents[1]/'shadow-plan-v1.json').read_text())
START=dt.datetime.fromisoformat(PLAN['frozenAt'])

class ShadowComparisonTests(unittest.TestCase):
 def event(self,hour,signal='Achat',rsi=30,price=100,delay=0):
  at=START+dt.timedelta(hours=hour)
  state=dict(realTradingEnabled=False,exchangeApiConnected=False,readiness=dict(simulationOnly=True,liveOrdersEnabled=False),capital=1600,cash=1600,holdings={},prices=dict(BTC=price,ETH=100),value=1600,updatedAt=at.isoformat(),marketCacheAt=at.timestamp(),signals=dict(BTC=dict(action=signal,rsi=rsi,sma7=101,sma21=100,reason='fixture')),trades=[],**RISK)
  return observe(state,str(hour),(at+dt.timedelta(hours=delay)).isoformat())
 def test_no_retroactive_results(self):
  r=compare([self.event(-1),self.event(0)],PLAN)
  self.assertEqual(r['acceptedObservations'],0);self.assertIsNone(r['candidate'])
 def test_next_quote_execution_and_costs(self):
  events=[self.event(1),self.event(2,price=110)];before=copy.deepcopy(events)
  r=compare(events,PLAN);t=r['candidate']['ledger'][0]
  self.assertEqual(t['at'],events[1]['at']);self.assertEqual(t['signalAt'],events[0]['at'])
  self.assertAlmostEqual(t['quantity'],120*.999/(110*1.002))
  self.assertAlmostEqual(r['candidate']['estimatedLiquidationEquity'],1480+120*.999/1.002*.998*.999,places=5)
  self.assertEqual(events,before);self.assertFalse(r['automaticPromotion'])
 def test_current_signal_cannot_change_its_own_fill(self):
  a=self.event(1);b=self.event(2,price=110);c=copy.deepcopy(b);c['signals']=[]
  self.assertEqual(compare([a,b],PLAN)['candidate'],compare([a,c],PLAN)['candidate'])
 def test_stricter_filter_does_not_buy_aggressive_rsi(self):
  r=compare([self.event(1,rsi=40),self.event(2)],PLAN)
  self.assertEqual(r['candidate']['observedBuys'],0);self.assertEqual(r['buyHold']['observedBuys'],1)
 def test_delayed_collect_cannot_trade_with_unavailable_signal(self):
  r=compare([self.event(1,delay=2),self.event(2)],PLAN)
  self.assertEqual(r['candidate']['observedBuys'],0)
 def test_duplicate_source_time_does_not_create_fill(self):
  a=self.event(1);b=copy.deepcopy(a);b['id']='anothercommit'
  self.assertEqual(compare([a,b],PLAN)['acceptedObservations'],1)
 def test_replay_is_deterministic(self):
  events=[self.event(i) for i in range(1,4)]
  self.assertEqual(compare(events,PLAN),compare(events,PLAN))
 def test_gap_does_not_fill_stale_signal(self):
  r=compare([self.event(1),self.event(5)],PLAN)
  self.assertEqual(r['candidate']['observedBuys'],0);self.assertIn('signal_gap_over_two_hours_no_fill',[x['reason'] for x in r['issues']])
 def test_risk_change_stops_evaluation(self):
  e=self.event(2);e['riskSnapshot']['maxLossPercent']=60
  r=compare([self.event(1),e],PLAN)
  self.assertEqual(r['acceptedObservations'],1);self.assertEqual(r['issues'][0]['reason'],'source_configuration_changed')
 def test_plan_cannot_be_retuned_silently(self):
  for key,value in [('capital',2000),('automaticPromotion',True),('automaticPromotion',0),('candidate','other'),('version',True)]:
   p=copy.deepcopy(PLAN);p[key]=value
   with self.assertRaises(ValueError):compare([],p)
 def test_missing_shadow_quote_stops_without_false_loss(self):
  a,b,c=[self.event(i) for i in range(1,4)];c['prices'].pop('BTC')
  r=compare([a,b,c],PLAN)
  self.assertEqual(r['acceptedObservations'],2);self.assertEqual(r['issues'][-1]['reason'],'missing_shadow_holding_quote')
 def test_stale_quote_stops(self):
  a=self.event(1);a['quotesFetchedAt']-=3601
  r=compare([a],PLAN);self.assertEqual(r['acceptedObservations'],0)
 def test_cooldown_and_exposure_caps(self):
  r=compare([self.event(i) for i in range(1,30)],PLAN)
  ledger=r['candidate']['ledger'];buys=[x for x in ledger if x['action']=='Achat']
  self.assertEqual(len(buys),2);self.assertTrue(all(t['amount']<=120 for t in buys))
  self.assertTrue(all(point['exposurePercent']<=20 for point in r['candidate']['curve']))
  self.assertEqual(r['buyHold']['observedBuys'],2)
 def test_trade_exit_cost_and_net_result(self):
  r=compare([self.event(1),self.event(2),self.event(3,price=110)],PLAN)
  self.assertEqual(r['candidate']['observedSales'],1);self.assertEqual(r['candidate']['observedBuys'],1)
  self.assertGreater(r['candidate']['netChange'],0)
 def test_global_halt_does_not_liquidate_or_buy(self):
  from shadow_compare import fresh,step
  account=fresh();account.update(cash=0,holdings={'BTC':16},entries={'BTC':100})
  event=self.event(2,price=40);step(account,event,self.event(1))
  self.assertTrue(account['paused']);self.assertEqual(account['holdings'],{'BTC':16});self.assertEqual(account['ledger'],[])
 def test_blocked_results_are_explicitly_partial(self):
  e=self.event(2);e['riskSnapshot']['maxOrder']=240
  self.assertEqual(compare([self.event(1),e],PLAN)['status'],'blocked_partial_data')
 def test_hash_chain_loader_rejects_tampering_and_paths(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp)/'hub/trading/learning-data';(base/'events').mkdir(parents=True)
   name='events/2026-11-11-0001.jsonl';index=base/'index.json';index.write_text(json.dumps(dict(segments=[name])))
   e=self.event(1);e['previousHash']=None;e['recordHash']=digest(e)
   (base/name).write_text(json.dumps(e)+'\n');self.assertEqual(len(load_events(tmp)),1)
   e['cash']=0;(base/name).write_text(json.dumps(e)+'\n')
   with self.assertRaises(ValueError):load_events(tmp)
   index.write_text(json.dumps(dict(segments=['../../escape'])))
   with self.assertRaises(ValueError):load_events(tmp)
