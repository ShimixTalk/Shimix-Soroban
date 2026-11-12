import copy,datetime as dt,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reserve_compare import D,fresh,buy,sell,transfer_profit,trading_value,snapshot,metrics,compare,step
from shadow_compare import RISK
from journal import observe
PLAN=json.loads((Path(__file__).resolve().parents[1]/'reserve-plan-v1.json').read_text())
START=dt.datetime.fromisoformat(PLAN['frozenAt'])

class ReserveTests(unittest.TestCase):
 def event(self,hour,price=100,action='Achat',delay=0):
  at=START+dt.timedelta(hours=hour)
  s=dict(realTradingEnabled=False,exchangeApiConnected=False,readiness=dict(simulationOnly=True,liveOrdersEnabled=False),capital=1600,cash=1600,holdings={},prices={'BTC':price,'ETH':100},value=1600,updatedAt=at.isoformat(),marketCacheAt=at.timestamp(),signals={'BTC':dict(action=action,reason='fixture',rsi=30,sma7=101,sma21=100)},trades=[],**RISK)
  return observe(s,str(hour),(at+dt.timedelta(hours=delay)).isoformat())
 def realized_account(self,realized,transferred=0):
  a=fresh(800,800);p=a['pockets']['harvest'];p['realized']=D(realized);p['transferred']=D(transferred)
  p['cash']=D(800)+D(realized)-D(transferred);a['reserve']=D(transferred)
  return a
 def test_exact_five_transferred_without_creating_money(self):
  a=self.realized_account(5);before=trading_value(a,{})+a['reserve']
  self.assertEqual(transfer_profit(a,{},'now'),D(5))
  self.assertEqual(trading_value(a,{}),D(1600));self.assertEqual(trading_value(a,{})+a['reserve'],before)
 def test_transfer_has_balanced_signed_entries(self):
  a=self.realized_account(5);transfer_profit(a,{},'now');entry=a['transfers'][0]
  self.assertEqual(entry['harvestCashDelta']+entry['reserveCashDelta'],0)
  self.assertEqual(entry['harvestCashDelta'],-5);self.assertTrue(entry['id'])
 def test_invalid_fill_does_not_mutate_account(self):
  for price in [0,-1,'NaN','Infinity']:
   a=fresh(800,800);before=copy.deepcopy(a)
   with self.assertRaises(ValueError):buy(a,'harvest','BTC',120,price,'now','signal')
   self.assertEqual(a,before)
 def test_fraction_below_threshold_not_rounded_up(self):
  a=self.realized_account('4.999999999');self.assertEqual(transfer_profit(a,{},'now'),0)
 def test_tranches_and_replay_do_not_duplicate(self):
  a=self.realized_account('16.12');self.assertEqual(transfer_profit(a,{},'now'),15)
  self.assertEqual(transfer_profit(a,{},'now'),0);self.assertEqual(len(a['transfers']),1)
 def test_losses_must_be_recovered_after_previous_transfer(self):
  for realized in [-5,0,3,5,9.99]:
   a=self.realized_account(realized,5);self.assertEqual(transfer_profit(a,{},'now'),0)
  a=self.realized_account(10,5);self.assertEqual(transfer_profit(a,{},'now'),5)
 def test_unrealized_gain_alone_is_not_withdrawn(self):
  a=fresh(800,800);buy(a,'harvest','BTC',120,100,'before','signal')
  self.assertEqual(transfer_profit(a,{'BTC':120},'now'),0)
 def test_growth_losses_block_harvest_transfer(self):
  a=self.realized_account(6);buy(a,'growth','BTC',120,100,'before','signal')
  self.assertLess(trading_value(a,{'BTC':90}),1600)
  self.assertEqual(transfer_profit(a,{'BTC':90},'now'),0)
 def test_cash_shortfall_defers_tranche(self):
  a=self.realized_account(10);buy(a,'harvest','BTC',120,100,'before','signal')
  a['pockets']['harvest']['cash']=D(4)
  self.assertEqual(transfer_profit(a,{'BTC':1000},'now'),0)
 def test_net_profit_includes_buy_fee_and_exit_costs(self):
  a=fresh(800,800);buy(a,'harvest','BTC',120,100,'before','signal')
  qty=D(120)*D('.999')/(D(100)*D('1.002'))
  profit=sell(a,'harvest','BTC',106,'now','signal','harvest')
  self.assertEqual(profit,qty*D(106)*D('.998')*D('.999')-120)
  before=trading_value(a,{})+a['reserve'];self.assertEqual(transfer_profit(a,{},'now'),5)
  self.assertEqual(trading_value(a,{})+a['reserve'],before)
 def test_reserve_not_reinvested_or_used_to_restore_capital(self):
  a=self.realized_account(5);transfer_profit(a,{},'before')
  buy(a,'growth','BTC',120,100,'before','signal')
  step(a,self.event(3,price=10,action='Attente'),self.event(2,action='Attente'))
  self.assertEqual(a['reserve'],5);self.assertLess(trading_value(a,{'BTC':10}),1600)
 def test_harvest_exit_at_net_threshold_and_no_instant_rebuy(self):
  a=fresh(800,800);buy(a,'harvest','BTC',120,100,self.event(1)['at'],'signal')
  current=self.event(26,price=106);previous=self.event(25)
  step(a,current,previous)
  self.assertEqual(a['trades'][-1]['reason'],'harvest_five_eur_net')
  self.assertEqual(a['reserve'],5);self.assertEqual(len(a['trades']),2)
 def test_growth_holds_below_normal_take_profit(self):
  a=fresh(0,1600);buy(a,'growth','BTC',120,100,self.event(1)['at'],'signal')
  step(a,self.event(3,price=106,action='Attente'),self.event(2,action='Attente'))
  self.assertIn('BTC',a['pockets']['growth']['holdings']);self.assertEqual(a['reserve'],0)
 def test_one_buy_total_and_small_pocket_exposure_limit(self):
  a=fresh(400,1200);step(a,self.event(2),self.event(1))
  self.assertEqual(len(a['trades']),1);self.assertEqual(a['trades'][0]['amount'],80)
  self.assertEqual(a['trades'][0]['pocket'],'harvest')
 def test_cooldown_across_both_pockets(self):
  a=fresh(800,800);step(a,self.event(2),self.event(1));step(a,self.event(3),self.event(2))
  self.assertEqual(len(a['trades']),1)
 def test_global_stop_excludes_reserve(self):
  a=fresh(800,800);a['pockets']['harvest']['cash']=D(100);a['pockets']['growth']['cash']=D(100);a['reserve']=D(1000)
  step(a,self.event(2),self.event(1));self.assertTrue(a['paused']);self.assertEqual(a['trades'],[])
 def test_balance_conservation_through_wins_losses_and_transfers(self):
  a=fresh(800,800)
  for i,price in enumerate([106,90,120,80,130]):
   buy(a,'harvest','BTC',120,100,str(i),'signal');sell(a,'harvest','BTC',price,str(i),'signal','fixture')
   transfer_profit(a,{},str(i))
   realized=sum((p['realized'] for p in a['pockets'].values()),D(0))
   self.assertAlmostEqual(trading_value(a,{})+a['reserve'],D(1600)+realized,places=20)
 def test_report_total_includes_reserve_and_not_double_counted(self):
  a=self.realized_account(15);transfer_profit(a,{},'now');snapshot(a,self.event(1));m=metrics(a)
  self.assertEqual(m['reserve'],15);self.assertEqual(m['combinedLiquidation'],1615)
  self.assertEqual(m['netChange'],15);self.assertEqual(m['latentAfterExitCosts'],0)
 def test_before_freeze_never_used(self):
  r=compare([self.event(-1),self.event(0)],PLAN)
  self.assertEqual(r['acceptedObservations'],0);self.assertTrue(all(v is None for v in r['variants'].values()))
 def test_comparison_preserves_inputs_and_is_reproducible(self):
  events=[self.event(1),self.event(2),self.event(3,price=106)];before=copy.deepcopy(events)
  r=compare(events,PLAN);self.assertEqual(events,before);self.assertEqual(r,compare(events,PLAN))
  self.assertEqual(set(r['variants']),{'0/1600','800/800','400/1200'})
  self.assertEqual(r['evidence'],'insufficient');self.assertFalse(r['automaticPromotion'])
 def test_current_signal_cannot_change_its_own_buy(self):
  a,b=self.event(1),self.event(2);c=copy.deepcopy(b);c['signals']=[]
  self.assertEqual(compare([a,b],PLAN)['variants'],compare([a,c],PLAN)['variants'])
 def test_collected_too_late_signal_is_unavailable(self):
  r=compare([self.event(1,delay=2),self.event(2)],PLAN)
  self.assertTrue(all(not v['trades'] for v in r['variants'].values()))
 def test_gap_no_fill_and_duplicate_no_extra_trade(self):
  a=self.event(1);b=self.event(5);r=compare([a,b,b],PLAN)
  self.assertEqual(r['acceptedObservations'],2);self.assertTrue(all(not v['trades'] for v in r['variants'].values()))
 def test_missing_held_quote_blocks_all_variants(self):
  a,b,c=self.event(1),self.event(2),self.event(3);c['prices'].pop('BTC')
  r=compare([a,b,c],PLAN);self.assertEqual(r['status'],'blocked_partial_data');self.assertEqual(r['acceptedObservations'],2)
 def test_risk_or_plan_cannot_change_silently(self):
  a=self.event(1);a['riskSnapshot']['maxOrder']=240
  self.assertEqual(compare([a],PLAN)['status'],'blocked_partial_data')
  for key,value in [('capital',2000),('transferStepEUR',1),('automaticPromotion',True)]:
   plan=copy.deepcopy(PLAN);plan[key]=value
   with self.assertRaises(ValueError):compare([],plan)
 def test_cash_only_fees_not_charged_or_capital_injected(self):
  r=compare([self.event(1,action='Attente'),self.event(2,action='Attente')],PLAN)
  for variant in r['variants'].values():
   self.assertEqual(variant['combinedLiquidation'],1600);self.assertEqual(variant['paidFees'],0);self.assertEqual(variant['reserve'],0)
