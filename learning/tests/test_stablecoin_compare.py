import copy,datetime as dt,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stablecoin_compare import compare,eligible,step,VARIANTS
from shadow_compare import RISK,fresh,buy
from journal import observe
PLAN=json.loads((Path(__file__).resolve().parents[1]/'stablecoin-plan-v1.json').read_text())
START=dt.datetime.fromisoformat(PLAN['frozenAt'])

class StablecoinEntryTests(unittest.TestCase):
 def signal(self,asset='USD1',rsi=44.78):return dict(asset=asset,action='Achat',indicators=dict(rsi=rsi,sma7=101,sma21=100))
 def event(self,hour,signals=None,delay=0):
  at=START+dt.timedelta(hours=hour)
  state=dict(realTradingEnabled=False,exchangeApiConnected=False,readiness=dict(simulationOnly=True,liveOrdersEnabled=False),capital=1600,cash=1600,holdings={},prices=dict(USD1=1,BTC=100,ASTER=100),value=1600,updatedAt=at.isoformat(),marketCacheAt=at.timestamp(),signals={},trades=[],**RISK)
  e=observe(state,str(hour),(at+dt.timedelta(hours=delay)).isoformat());e['signals']=[self.signal()] if signals is None else signals;return e
 def test_usd1_excluded_but_original_recorded_signal_eligible(self):
  signals=[self.signal()];self.assertEqual(eligible(signals)[0][0][1],'USD1')
  candidates,reasons=eligible(signals,exclude=True);self.assertEqual(candidates,[]);self.assertEqual(reasons[0]['asset'],'USD1')
 def test_nonstable_unaffected_except_strict_filter(self):
  for asset in ['BTC','ETH','ASTER']:
   signal=[self.signal(asset,40)]
   self.assertEqual(eligible(signal)[0],eligible(signal,exclude=True)[0])
   self.assertEqual(eligible(signal,exclude=True,strict=True)[0],[])
 def test_strict_requires_both_rsi_and_trend(self):
  s=self.signal('BTC',30);self.assertTrue(eligible([s],exclude=True,strict=True)[0])
  s['indicators']['sma7']=99;self.assertEqual(eligible([s],exclude=True,strict=True)[0],[])
 def test_unknown_or_invalid_rsi_not_invented(self):
  for rsi in [None,float('nan'),True,-1,101]:self.assertEqual(eligible([self.signal('BTC',rsi)])[0],[])
 def test_waiting_signals_not_treated_as_buy(self):
  s=self.signal();s['action']='Attente';self.assertEqual(eligible([s],exclude=True),([],[]))
 def test_future_only_and_read_only(self):
  events=[self.event(-1),self.event(0),self.event(1),self.event(2)];before=copy.deepcopy(events)
  r=compare(events,PLAN);self.assertEqual(events,before);self.assertEqual(r['acceptedObservations'],2)
  self.assertEqual(r['variants']['recorded_buy_signals']['observedBuys'],1)
  self.assertEqual(r['variants']['recorded_buy_signals_no_stablecoins']['observedBuys'],0)
  self.assertFalse(r['automaticPromotion']);self.assertEqual(r['evidence'],'insufficient')
 def test_filtered_variant_can_select_next_eligible_asset(self):
  r=compare([self.event(1,[self.signal('USD1',20),self.signal('BTC',30)]),self.event(2)],PLAN)
  self.assertEqual(r['variants']['recorded_buy_signals']['ledger'][0]['asset'],'USD1')
  self.assertEqual(r['variants']['recorded_buy_signals_no_stablecoins']['ledger'][0]['asset'],'BTC')
 def test_current_signal_cannot_change_current_fill(self):
  a,b=self.event(1),self.event(2);c=copy.deepcopy(b);c['signals']=[]
  self.assertEqual(compare([a,b],PLAN)['variants'],compare([a,c],PLAN)['variants'])
 def test_late_collection_cannot_create_retroactive_fill(self):
  r=compare([self.event(1,delay=2),self.event(2)],PLAN)
  self.assertTrue(all(v['observedBuys']==0 for v in r['variants'].values()))
 def test_exclusion_does_not_force_sale_of_existing_position(self):
  account=dict(fresh(),excludedEntries=[]);buy(account,'USD1',120,1,self.event(1)['at'],'signal')
  step(account,self.event(2),self.event(1),'recorded_buy_signals_no_stablecoins')
  self.assertIn('USD1',account['holdings']);self.assertEqual(len(account['ledger']),1)
 def test_existing_stablecoin_still_exits_on_sell_signal(self):
  account=dict(fresh(),excludedEntries=[]);buy(account,'USD1',120,1,self.event(1)['at'],'signal')
  prior=self.event(1);prior['signals'][0]['action']='Vente'
  step(account,self.event(2),prior,'recorded_buy_signals_no_stablecoins')
  self.assertNotIn('USD1',account['holdings']);self.assertEqual(account['ledger'][-1]['action'],'Vente')
 def test_same_order_costs_and_cooldown(self):
  events=[self.event(i,[self.signal('BTC',30)]) for i in range(1,4)]
  r=compare(events,PLAN)
  for v in r['variants'].values():
   self.assertEqual(v['observedBuys'],1);self.assertEqual(v['ledger'][0]['gross'] if 'gross' in v['ledger'][0] else v['ledger'][0]['amount'],120)
   self.assertAlmostEqual(v['estimatedLiquidationEquity'],1480+120*.999/1.002*.998*.999,places=5)
 def test_gap_and_duplicate_do_not_add_orders(self):
  a,b=self.event(1),self.event(5);r=compare([a,b,b],PLAN)
  self.assertEqual(r['acceptedObservations'],2);self.assertTrue(all(v['observedBuys']==0 for v in r['variants'].values()))
 def test_missing_held_quote_blocks_all_results(self):
  a,b,c=[self.event(i) for i in range(1,4)];c['prices'].pop('USD1')
  r=compare([a,b,c],PLAN);self.assertEqual(r['status'],'blocked_partial_data');self.assertEqual(r['acceptedObservations'],2)
 def test_risk_and_plan_changes_are_rejected(self):
  a=self.event(1);a['riskSnapshot']['maxOrder']=240;self.assertEqual(compare([a],PLAN)['status'],'blocked_partial_data')
  p=copy.deepcopy(PLAN);p['blockedSymbols']=[]
  with self.assertRaises(ValueError):compare([],p)
 def test_no_data_means_no_performance(self):
  r=compare([],PLAN);self.assertEqual(r['status'],'waiting_for_new_observations')
  self.assertTrue(all(v is None for v in r['variants'].values()))
 def test_results_reproducible(self):
  events=[self.event(i) for i in range(1,4)];self.assertEqual(compare(events,PLAN),compare(events,PLAN))
