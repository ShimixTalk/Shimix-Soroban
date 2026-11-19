import datetime as dt
import unittest
import base64
import json
from unittest.mock import patch
from simulation_recovery import decide
import simulation_recovery as recovery

NOW = dt.datetime(2026, 11, 19, 12, tzinfo=dt.timezone.utc)


class RecoveryTests(unittest.TestCase):
    def state(self, at='2026-11-19T10:00:00Z'):
        return dict(updatedAt=at, realTradingEnabled=False, exchangeApiConnected=False)

    def sample_run(self, status='completed', at='2026-11-19T10:00:00Z'):
        return dict(path='.github/workflows/shimix-trading-simulation.yml',
                    status=status, created_at=at)

    def test_old_idle_simulation_recovers(self):
        self.assertEqual(decide(self.state(), [self.sample_run()], NOW), 'dispatch')

    def test_fresh_and_boundary_snapshot_do_not_dispatch(self):
        for at in ['2026-11-19T11:59:00Z', '2026-11-19T11:15:00Z']:
            self.assertEqual(decide(self.state(at), [], NOW), 'fresh_snapshot')

    def test_active_workflow_blocks_duplicate(self):
        for status in ['queued', 'in_progress', 'waiting', 'pending', 'requested']:
            self.assertEqual(decide(self.state(), [self.sample_run(status)], NOW), 'already_active')

    def test_recent_attempt_even_failure_is_throttled(self):
        run = self.sample_run(at='2026-11-19T11:30:00Z')
        run['conclusion'] = 'failure'
        self.assertEqual(decide(self.state(), [run], NOW), 'recent_attempt')

    def test_unknown_or_real_mode_never_dispatches(self):
        for field in ['realTradingEnabled', 'exchangeApiConnected']:
            for value in [True, None, 'false', 0]:
                state = self.state()
                state[field] = value
                self.assertEqual(decide(state, [], NOW), 'unsafe_or_unknown_mode')

    def test_future_snapshot_is_not_stale(self):
        self.assertEqual(decide(self.state('2026-11-20T10:00:00Z'), [], NOW), 'future_snapshot')

    def test_missing_or_invalid_time_fails_closed(self):
        for at in ['', '2026-11-19T10:00:00']:
            with self.assertRaises(ValueError):
                decide(self.state(at), [], NOW)

    def test_wrong_workflow_rejected(self):
        run = self.sample_run()
        run['path'] = '.github/workflows/other.yml'
        with self.assertRaises(ValueError):
            decide(self.state(), [run], NOW)

    def test_dispatch_uses_only_existing_main_simulation(self):
        file = {'content': base64.b64encode(json.dumps(self.state()).encode()).decode()}
        with patch.object(recovery, 'api', side_effect=[file, {'workflow_runs': []}, None]) as api:
            recovery.main()
        self.assertEqual(api.call_args.args,
                         ('actions/workflows/shimix-trading-simulation.yml/dispatches',
                          'POST', {'ref': 'main'}))

    def test_read_error_cannot_dispatch(self):
        with patch.object(recovery, 'api', side_effect=ValueError('unavailable')) as api:
            with self.assertRaises(ValueError):
                recovery.main()
        self.assertEqual(api.call_count, 1)


if __name__ == '__main__':
    unittest.main()
