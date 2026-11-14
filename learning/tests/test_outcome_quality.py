import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from outcome_quality import outcome_quality
from journal import observe,summarize
from test_learning import state,NOW
class OutcomeQualityTests(unittest.TestCase):
 def result(self,values,unknown=0,fees=True):return outcome_quality([dict(netRealizedPnl=p) for p in values],unknown,fees)
 def test_no_sales_does_not_invent_success_rate(self):
  r=self.result([]);self.assertIsNone(r['knownSalesWinRatePercent']);self.assertIsNone(r['indicativeWilson95Percent'])
 def test_wins_losses_and_breakeven_are_distinct(self):
  r=self.result([10,-30,0]);self.assertEqual(r['knownWinningSales'],1);self.assertEqual(r['knownLosingSales'],1)
  self.assertEqual(r['knownBreakevenSales'],1);self.assertAlmostEqual(r['meanKnownPnlPerSale'],-20/3,places=5)
  self.assertAlmostEqual(r['knownProfitFactor'],1/3,places=5)
 def test_all_wins_are_not_proof_or_infinite_profit_factor(self):
  r=self.result([1,1]);self.assertEqual(r['knownSalesWinRatePercent'],100)
  self.assertLess(r['indicativeWilson95Percent'][0],50);self.assertIsNone(r['knownProfitFactor'])
  self.assertFalse(r['automaticPromotion'])
 def test_one_loss_has_wide_uncertainty(self):
  r=self.result([-10]);self.assertEqual(r['knownSalesWinRatePercent'],0)
  self.assertGreater(r['indicativeWilson95Percent'][1],70)
 def test_high_win_rate_can_still_lose_money(self):
  r=self.result([1,1,1,1,-10]);self.assertEqual(r['knownSalesWinRatePercent'],80)
  self.assertLess(r['meanKnownPnlPerSale'],0);self.assertLess(r['knownProfitFactor'],1)
 def test_unknown_costs_stay_explicit(self):
  r=self.result([1],unknown=3,fees=False);self.assertEqual(r['unattributableTrades'],3)
  self.assertFalse(r['feeCoverageComplete']);self.assertEqual(r['evidence'],'insufficient_for_automatic_promotion')
 def test_outcomes_use_entire_journal_not_last_fifty_rows(self):
  self.assertEqual(self.result([1]*60)['knownSaleOutcomes'],60)
 def test_duplicate_trade_events_do_not_duplicate_sale_outcomes(self):
  s=state();s['trades']=[dict(date='2026-11-09T12:00:00Z',asset='BTC',action='Achat',price=90,quantity=1,fee=1),dict(date='2026-11-10T12:00:00Z',asset='BTC',action='Vente',price=100,quantity=1,fee=1)]
  e=observe(s,'a',NOW.isoformat());before=copy.deepcopy(e);r=summarize([e,copy.deepcopy(e)])
  self.assertEqual(r['outcomeQuality']['knownSaleOutcomes'],1)
  self.assertEqual(r['outcomeQuality']['meanKnownPnlPerSale'],8);self.assertEqual(e,before)
 def test_missing_basis_not_counted_as_a_winning_sale(self):
  s=state();s['trades']=[dict(date=NOW.isoformat(),asset='BTC',action='Vente',price=100,quantity=1,fee=1)]
  r=summarize([observe(s,'a',NOW.isoformat())])['outcomeQuality']
  self.assertEqual(r['knownSaleOutcomes'],0);self.assertEqual(r['unattributableTrades'],1)
