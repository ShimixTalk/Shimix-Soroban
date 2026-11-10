"""Deterministic integration tests. GitHub and market calls are replaced in memory."""
import base64
import copy
import datetime
import json
import unittest
from unittest.mock import patch
import autonomous_simulation as robot


def good_state():
    return dict(enabled=True,realTradingEnabled=False,exchangeApiConnected=False,
                readiness=dict(simulationOnly=True,liveOrdersEnabled=False),
                capital=1600,cash=1600,maxOrder=120,maxLossPercent=5,
                maxPositionPercent=20,maxPositions=8,holdings={},entryPrices={},
                trades=[],logs=[],dailyHistory={},historyUpdated={})


def market():
    return [dict(id=f'coin-{i}',symbol=f'C{i}',name=f'Coin {i}',current_price=100,
                 total_volume=100000000,market_cap=1000000000,price_change_percentage_24h=1)
            for i in range(30)]


class RobotRegressionTests(unittest.TestCase):
    def run_robot(self,state,quotes=None,buy=True):
        saved=[]
        def gh(method,body=None):
            self.assertEqual(method,'GET')
            return {'sha':'fixture','content':base64.b64encode(json.dumps(state).encode()).decode()}
        now=datetime.datetime.now(datetime.timezone.utc)
        start=int(now.timestamp())//86400-31
        chart={'prices':[[(start+i)*86400000,100+i] for i in range(31)]}
        def request(url,*args):return quotes if '/coins/markets?' in url else chart
        with patch.object(robot,'gh',side_effect=gh),patch.object(robot,'request',side_effect=request),patch.object(robot,'save',side_effect=lambda s,sha:saved.append(copy.deepcopy(s))),patch.object(robot.time,'sleep'),patch.object(robot,'rsi',return_value=30 if buy else 70):
            robot.main()
        return saved[0] if saved else None

    def test_buy_accounting_and_limits(self):
        result=self.run_robot(good_state(),market())
        self.assertEqual(len(result['trades']),1)
        trade=result['trades'][0];self.assertEqual(trade['action'],'Achat')
        self.assertEqual(result['cash'],1480)
        self.assertAlmostEqual(trade['quantity'],(120-0.12)/100.2)
        self.assertLessEqual(trade['amount'],120)
        self.assertFalse(result['realTradingEnabled'])
        self.assertTrue(result['readiness']['simulationOnly'])

    def test_missing_holding_price_no_trade(self):
        state=good_state();state.update(cash=1500,holdings={'MISSING':1})
        result=self.run_robot(state,market())
        self.assertEqual(result['cash'],1500);self.assertEqual(result['holdings'],state['holdings'])
        self.assertEqual(result['trades'],[]);self.assertIn('Prix indisponible',result['dataErrors'][0])

    def test_loss_stop_preserves_holdings(self):
        state=good_state();state.update(cash=1400,holdings={'C0':1})
        result=self.run_robot(state,market())
        self.assertFalse(result['enabled']);self.assertEqual(result['holdings'],state['holdings']);self.assertEqual(result['trades'],[])

    def test_sale_accounts_for_spread_slippage_fee(self):
        state=good_state();state.update(cash=1500,holdings={'C0':1},entryPrices={'C0':120})
        result=self.run_robot(state,market(),buy=False)
        self.assertNotIn('C0',result['holdings'])
        self.assertAlmostEqual(result['cash'],1599.7002)
        self.assertEqual(result['trades'][0]['action'],'Vente')

    def test_invalid_market_preserves_portfolio(self):
        state=good_state();result=self.run_robot(state,[{}])
        self.assertEqual(result['cash'],state['cash']);self.assertEqual(result['trades'],[])
        self.assertTrue(result['dataErrors'])

    def test_live_flag_rejected_before_market(self):
        state=good_state();state['realTradingEnabled']=True
        with self.assertRaises(ValueError):self.run_robot(state,market())

    def test_no_new_trade_with_stale_history(self):
        state=good_state()
        for i in range(20):state['dailyHistory'][f'coin-{i}']=list(range(100,131));state['historyUpdated'][f'coin-{i}']=1
        # Only two histories can be refreshed; other stale assets cannot signal a buy.
        result=self.run_robot(state,market())
        self.assertTrue(all(x['action']=='Attente' for k,x in result['signals'].items() if k not in ['C0','C1']))

    def test_symbol_collision_is_ambiguous(self):
        rows=market();rows[1]['symbol']='C0'
        self.assertNotIn('C0',robot.market_prices(rows,{}))
        self.assertNotIn('C0',robot.market_prices(market(),{'C0':'different-coin'}))

    def test_flat_rsi_is_neutral(self):self.assertEqual(robot.rsi([100]*30),50)

    def test_malformed_financial_state(self):
        for change in ({'maxPositions':2.5},{'peak':float('nan')},{'dailyHistory':{'x':[float('inf')]}},{'lastTrade':{'C0':'yesterday'}}):
            with self.subTest(change=change),self.assertRaises(ValueError):robot.validate_simulation_state({**good_state(),**change})

    def test_closed_daily_history_rejects_invalid_and_stale(self):
        now=datetime.datetime.now(datetime.timezone.utc);today=int(now.timestamp())//86400
        rows=[[(today-i)*86400000,100] for i in range(31,-1,-1)]
        self.assertEqual(len(robot.closed_daily_prices({'prices':rows},now)),31)
        for bad in ({'prices':rows[:-3]},{'prices':[[1,float('inf')]]},{'prices':rows[:-3]+rows[-1:]}):
            with self.assertRaises(ValueError):robot.closed_daily_prices(bad,now)

if __name__=='__main__':unittest.main()
