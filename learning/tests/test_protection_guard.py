import hashlib,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integration_check import approved_protection_change
ROOT=Path(__file__).resolve().parents[2]
class ProtectionGuardTests(unittest.TestCase):
 def test_exact_engine_transition_only(self):
  old=(ROOT/'learning/tests/fixtures/autonomous_simulation_before_fast_risk.txt').read_bytes()
  self.assertEqual(hashlib.sha256(old).hexdigest(),'e3479e3fa7b7718276b04d50cb3694120627631df8fb03ef7894a9daab21bd0a')
  current=(ROOT/'hub/trading/autonomous_simulation.py').read_bytes()
  self.assertTrue(approved_protection_change(old,current))
  self.assertFalse(approved_protection_change(old,current.replace(b'*.95',b'*.50',1)))
  self.assertFalse(approved_protection_change(old+b'\n',current))
