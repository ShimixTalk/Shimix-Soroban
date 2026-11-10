#!/usr/bin/env python3
"""Offline regression tests for simulation-only market input validation."""
import math
import os
import runpy
import unittest
from pathlib import Path

os.environ.setdefault("GITHUB_TOKEN", "test-token-not-used")
module = runpy.run_path(str(Path(__file__).with_name("autonomous_simulation.py")), run_name="shimix_validation_tests")
valid_market_row = module["valid_market_row"]
validate_simulation_state = module["validate_simulation_state"]

GOOD = {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "current_price": 65000.0,
        "total_volume": 100000000.0, "market_cap": 1000000000000.0,
        "price_change_percentage_24h": -1.2}

class MarketValidationTests(unittest.TestCase):
    def test_valid_quote(self):
        self.assertTrue(valid_market_row(GOOD))

    def test_invalid_quotes(self):
        for field, value in [
            ("current_price", 0), ("current_price", -1),
            ("current_price", math.nan), ("current_price", math.inf),
            ("current_price", "65000"), ("total_volume", 0),
            ("total_volume", math.inf), ("market_cap", -10),
            ("price_change_percentage_24h", math.nan),
        ]:
            with self.subTest(field=field, value=value):
                self.assertFalse(valid_market_row({**GOOD, field: value}))

    def test_missing_identity(self):
        self.assertFalse(valid_market_row({**GOOD, "id": None}))
        self.assertFalse(valid_market_row({**GOOD, "symbol": None}))
        self.assertFalse(valid_market_row({**GOOD, "symbol": ""}))
        self.assertFalse(valid_market_row({**GOOD, "name": None}))
        self.assertFalse(valid_market_row({**GOOD, "id": ""}))


class SimulationStateTests(unittest.TestCase):
    def setUp(self):
        self.good = {
            "realTradingEnabled": False, "exchangeApiConnected": False,
            "readiness": {"simulationOnly": True, "liveOrdersEnabled": False},
            "capital": 1600, "cash": 1360, "maxOrder": 120,
            "maxLossPercent": 5, "maxPositionPercent": 20, "maxPositions": 8,
            "feeRate": 0.001, "spreadRate": 0.001, "slippageRate": 0.001,
            "holdings": {"BTC": 0.001, "ETH": 0.02},
        }
    def test_valid_simulation(self):
        self.assertTrue(validate_simulation_state(self.good))
    def test_fail_closed(self):
        changes = [
            {"realTradingEnabled": True},
            {"exchangeApiConnected": True},
            {"cash": float("nan")},
            {"maxOrder": -1},
            {"maxLossPercent": 200},
            {"feeRate": -0.01},
            {"holdings": {"BTC": -2}},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_simulation_state({**self.good, **change})
    def test_missing_readiness(self):
        with self.assertRaises(ValueError):
            validate_simulation_state({**self.good, "readiness": None})

if __name__ == "__main__":
    unittest.main()
