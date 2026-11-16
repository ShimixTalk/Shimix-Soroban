import hashlib,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integration_check import approved_protection_change, approved_owner_policy_change
ROOT=Path(__file__).resolve().parents[2]
class ProtectionGuardTests(unittest.TestCase):
 def test_exact_engine_transition_only(self):
  old=(ROOT/'learning/tests/fixtures/autonomous_simulation_before_entry_review.txt').read_bytes()
  self.assertEqual(hashlib.sha256(old).hexdigest(),'c459629e19a1554ea96b0bde65e73f59d18f910d0b1329f6e5d9ae7d26460968')
  current=(ROOT/'learning/tests/fixtures/autonomous_simulation_before_owner_policy.txt').read_bytes()
  self.assertTrue(approved_protection_change(old,current))
  self.assertFalse(approved_protection_change(old,current.replace(b'*.95',b'*.50',1)))
  self.assertFalse(approved_protection_change(old+b'\n',current))

 def test_owner_policy_requires_new_regime_review(self):
  old=(ROOT/'learning/tests/fixtures/autonomous_simulation_before_owner_policy.txt').read_bytes()
  current=(ROOT/'hub/trading/autonomous_simulation.py').read_bytes()
  self.assertFalse(approved_protection_change(old,current))

 def test_owner_transition_is_exact_and_cannot_relax_risk(self):
  old=(ROOT/'learning/tests/fixtures/autonomous_simulation_before_owner_policy.txt').read_bytes()
  current=(ROOT/'learning/tests/fixtures/autonomous_simulation_before_history_priority.txt').read_bytes()
  self.assertTrue(approved_owner_policy_change(old,current))
  self.assertFalse(approved_owner_policy_change(old,current.replace(b'*.95',b'*.50',1)))
  self.assertFalse(approved_owner_policy_change(old+b'\n',current))

 def test_history_priority_is_not_silently_approved_as_owner_transition(self):
  old=(ROOT/'learning/tests/fixtures/autonomous_simulation_before_owner_policy.txt').read_bytes()
  current=(ROOT/'hub/trading/autonomous_simulation.py').read_bytes()
  self.assertFalse(approved_owner_policy_change(old,current))
