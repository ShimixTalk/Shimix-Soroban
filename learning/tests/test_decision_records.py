import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_learning import state,NOW
from journal import observe,decision_record

class DecisionRecordTests(unittest.TestCase):
 def raw(self):return dict(at=NOW.isoformat(),trigger='strict_rsi_trend',marketPrice=100,cashBefore=1600,signal=dict(at=NOW.isoformat(),rsi=30,sma7=101,sma21=100),costs=dict(feeRate=.001),risk=dict(maxOrder=120))
 def test_context_retained_without_changing_trade_identity(self):
  s=state();s['trades']=[dict(date=NOW.isoformat(),asset='BTC',action='Achat',amount=120,price=100,quantity=1,fee=.12)]
  original=observe(s,'a',NOW.isoformat())['trades'][0]
  s['trades'][0]['decision']=self.raw();before=copy.deepcopy(s)
  enriched=observe(s,'b',NOW.isoformat())['trades'][0]
  self.assertEqual(original['id'],enriched['id']);self.assertEqual(enriched['decision']['signal']['rsi'],30)
  self.assertEqual(s,before)
 def test_unknown_fields_and_nonfinite_values_not_retained(self):
  raw=self.raw();raw.update(secret='not copied');raw['signal'].update(extra='not copied',rsi=float('nan'))
  safe=decision_record(raw);self.assertNotIn('secret',safe);self.assertNotIn('extra',safe['signal']);self.assertNotIn('rsi',safe['signal'])
 def test_malformed_context_does_not_drop_the_trade(self):
  s=state();s['trades']=[dict(date=NOW.isoformat(),asset='BTC',action='Achat',amount=120,price=100,quantity=1,fee=.12,decision=dict(at='invalid'))]
  e=observe(s,'a',NOW.isoformat());self.assertEqual(len(e['trades']),1)
  self.assertNotIn('decision',e['trades'][0]);self.assertIn('decision_context_invalid',[x['code'] for x in e['errors']])
 def test_signal_outcome_and_context_retained(self):
  s=state();s['signals']['BTC'].update(executionOutcome='asset_cooldown',decisionContext=self.raw()['signal'])
  e=observe(s,'a',NOW.isoformat());self.assertEqual(e['signals'][0]['executionOutcome'],'asset_cooldown')
  self.assertEqual(e['signals'][0]['decisionContext']['rsi'],30)
