"""Compare instrumented engine to original logic, with every external call intercepted."""
import base64,copy,datetime,json,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
import autonomous_simulation as audited
from test_robot_regressions import good_state,market
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'learning'))
from integration_check import strip_decision_audit,audit_only_engine_change

class Clock(datetime.datetime):
 @classmethod
 def now(cls,tz=None):return cls(2026,11,12,4,tzinfo=datetime.timezone.utc)

class DecisionAuditTests(unittest.TestCase):
 def run_engine(self,module,state,quotes=None,aggressive=False):
  saved=[];now=Clock.now();start=int(now.timestamp())//86400-31
  chart={'prices':[[(start+i)*86400000,100+i] for i in range(31)]}
  def get(method,body=None):
   self.assertEqual(method,'GET');return dict(sha='fixture',content=base64.b64encode(json.dumps(state).encode()).decode())
  clock=types.SimpleNamespace(datetime=Clock,timezone=datetime.timezone)
  with patch.object(module,'gh',side_effect=get),patch.object(module,'request',side_effect=lambda url,*a: (market() if quotes is None else quotes) if '/coins/markets?' in url else chart),patch.object(module,'save',side_effect=lambda s,sha:saved.append(copy.deepcopy(s))),patch.object(module.time,'sleep'),patch.object(module,'rsi',return_value=40 if aggressive else 30),patch.object(module,'datetime',clock):
   if aggressive:
    with patch.object(module,'sma',side_effect=lambda p,n:98 if n==7 else 100):module.main()
   else:module.main()
  return saved[0]
 def baseline(self):
  module=types.ModuleType('baseline');code=strip_decision_audit(Path(audited.__file__).read_bytes())
  exec(compile(code,'baseline_engine','exec'),module.__dict__);return module
 def clean(self,state):
  s=copy.deepcopy(state)
  for signal in s.get('signals',{}).values():
   signal.pop('decisionContext',None);signal.pop('executionOutcome',None)
  for trade in s.get('trades',[]):
   if 'decision' in trade:
    trade.pop('decision')
    if trade['action']=='Achat':trade.pop('reason',None)
  return s
 def test_financial_behavior_identical_in_ten_scenarios(self):
  cases=[({},None,False),({'experimentMode':'aggressive_simulation'},None,True),
   ({'cash':1500,'holdings':{'C0':1},'entryPrices':{'C0':120}},None,False),
   ({'cash':1500,'holdings':{'C0':1},'entryPrices':{'C0':80}},None,False),
   ({'cash':1400,'holdings':{'C0':1}},None,False),
   ({'cash':1500,'holdings':{'MISSING':1}},None,False),({},[{}],False),
   ({'lastTrade':{'C0':Clock.now().timestamp(),'C1':Clock.now().timestamp()}},None,False),
   ({'maxPositions':1,'cash':1500,'holdings':{'C0':1},'entryPrices':{'C0':100}},None,False),
   ({'maxPositionPercent':0},None,False)]
  for changes,quotes,aggressive in cases:
   with self.subTest(changes=changes):
    state={**good_state(),**changes}
    old=self.run_engine(self.baseline(),state,quotes,aggressive)
    new=self.run_engine(audited,state,quotes,aggressive)
    self.assertEqual(self.clean(new),old)
 def test_buy_records_full_precision_before_trade(self):
  s=self.run_engine(audited,good_state());trade=s['trades'][0];d=trade['decision']
  self.assertEqual(trade['reason'],'strict_rsi_trend');self.assertEqual(d['trigger'],'strict_rsi_trend')
  self.assertEqual(d['cashBefore'],1600);self.assertEqual(d['quantityBefore'],0)
  self.assertEqual(d['marketPrice'],100);self.assertEqual(d['signal']['rsi'],30)
  self.assertEqual(d['costs']['feeRate'],.001);self.assertEqual(d['risk']['maxOrder'],120)
  self.assertEqual(s['signals'][trade['asset']]['executionOutcome'],'executed_buy')
 def test_aggressive_reason_is_distinct(self):
  s=self.run_engine(audited,{**good_state(),'experimentMode':'aggressive_simulation'},aggressive=True)
  self.assertEqual(s['trades'][0]['reason'],'aggressive_rebound')
 def test_sale_and_global_stop_are_explained(self):
  s=self.run_engine(audited,{**good_state(),'cash':1500,'holdings':{'C0':1},'entryPrices':{'C0':120}})
  sale=next(t for t in s['trades'] if t['action']=='Vente')
  self.assertEqual(sale['decision']['trigger'],'stop-loss');self.assertEqual(sale['decision']['entryReference'],120)
  stopped=self.run_engine(audited,{**good_state(),'cash':1400,'holdings':{'C0':1}})
  self.assertTrue(all(s['executionOutcome']=='global_safety_stop' for s in stopped['signals'].values()))
 def test_old_trades_are_not_rewritten(self):
  old=dict(date='2026-11-01T00:00:00Z',asset='OLD',action='Achat',amount=1,quantity=.1,fee=.001)
  s=self.run_engine(audited,{**good_state(),'trades':[old]})
  self.assertEqual(s['trades'][-1],old)
 def test_guard_accepts_only_exact_audited_instrumentation(self):
  new=Path(audited.__file__).read_bytes();old=strip_decision_audit(new)
  self.assertTrue(audit_only_engine_change(old,new))
  changed=new.replace(b'"strategyMode":state.get',b'"otherMode":state.get')
  self.assertFalse(audit_only_engine_change(old,changed))
