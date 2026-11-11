import copy,datetime as dt,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_learning import state,NOW,Memory,POLICY
from journal import observe
from rigour import review
from collect import build

class RigourTests(unittest.TestCase):
 def event(self):
  s=state();s.update(feeRate=.001,spreadRate=.001,slippageRate=.001)
  return observe(s,'fixture',NOW.isoformat())
 def test_liquidation_deducts_only_exit_costs(self):
  e=self.event();before=copy.deepcopy(e);r=review([e],NOW.isoformat())
  self.assertAlmostEqual(r['estimatedLiquidationEquity'],1500+100*.998*.999)
  self.assertAlmostEqual(r['estimatedExitCosts'],.2998)
  self.assertEqual(e,before);self.assertEqual(r['evidence'],'insufficient')
 def test_missing_or_invalid_rates_never_default_to_free_exit(self):
  for v in [None,True,-.1,1,float('nan')]:
   e=self.event();e['riskSnapshot']['feeRate']=v;r=review([e],NOW.isoformat())
   self.assertIsNone(r['estimatedLiquidationEquity']);self.assertIn('unknown_or_invalid_exit_costs',r['issues'])
 def test_combined_spread_slippage_rejected(self):
  e=self.event();e['riskSnapshot'].update(spreadRate=.6,slippageRate=.6)
  self.assertIsNone(review([e],NOW.isoformat())['estimatedLiquidationEquity'])
 def test_missing_quotes_do_not_value_position_at_zero(self):
  e=self.event();e['prices']={};r=review([e],NOW.isoformat())
  self.assertIsNone(r['markedEquity']);self.assertIsNone(r['estimatedLiquidationEquity'])
 def test_stale_or_future_execution_quote_blocks_estimate(self):
  for seconds in [-1,3601]:
   e=self.event();e['quotesFetchedAt']=NOW.timestamp()-seconds
   self.assertIsNone(review([e],NOW.isoformat())['estimatedLiquidationEquity'])
 def test_collection_delay_is_separate_and_old_estimate_labelled(self):
  r=review([self.event()],(NOW+dt.timedelta(days=1)).isoformat())
  self.assertEqual(r['quoteAgeAtExecutionSeconds'],0);self.assertEqual(r['sourceAgeAtReportSeconds'],86400)
  self.assertIn('old_or_future_source',r['issues']);self.assertIsNotNone(r['estimatedLiquidationEquity'])
 def test_trade_counts_and_fees_are_deduplicated(self):
  e=self.event();e['trades']=[dict(id='a',action='Achat',fee=.12,reason='Non enregistrée')]
  r=review([e,copy.deepcopy(e)],NOW.isoformat());self.assertEqual(r['observedBuys'],1)
  self.assertEqual(r['knownPaidFees'],.12);self.assertEqual(r['observedSales'],0)
  self.assertIn('undocumented_trade_reasons',r['issues'])
 def test_missing_fees_remain_unknown(self):
  e=self.event();e['trades']=[dict(id='a',action='Vente',fee=None)]
  r=review([e],NOW.isoformat());self.assertEqual(r['missingHistoricalFees'],1)
  self.assertIn('incomplete_historical_fees',r['issues'])
 def test_observed_drawdown_and_short_evidence(self):
  a=self.event();b=copy.deepcopy(a);b.update(at=(NOW+dt.timedelta(hours=1)).isoformat(),cash=1340,equity=1440)
  r=review([b,a],b['at']);self.assertEqual(r['observedMaxDrawdownPercent'],10)
  self.assertEqual(r['evidence'],'insufficient');self.assertAlmostEqual(r['observationDays'],1/24,places=5)
 def test_one_point_does_not_invent_drawdown(self):
  self.assertIsNone(review([self.event()],NOW.isoformat())['observedMaxDrawdownPercent'])
 def test_empty_journal(self):self.assertEqual(review([],NOW.isoformat())['status'],'no_observations')
 def test_cash_only_needs_no_exit_fee(self):
  e=self.event();e.update(holdings={},cash=1600,equity=1600,riskSnapshot={})
  self.assertEqual(review([e],NOW.isoformat())['estimatedLiquidationEquity'],1600)
 def test_equity_mismatch_blocks_estimate(self):
  e=self.event();e['equity']=1700
  self.assertIsNone(review([e],NOW.isoformat())['estimatedLiquidationEquity'])
 def test_report_is_read_only_and_includes_review(self):
  repo=Memory();before=copy.deepcopy(repo.files);files,r=build(repo,{**POLICY,'historyRequestsPerRun':0},NOW)
  self.assertIn('rigour',r);self.assertEqual(repo.files,before)
  self.assertTrue(all(p.startswith('hub/trading/learning-data/') for p in files))
