import hashlib,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integration_check import approved_protection_change
ROOT=Path(__file__).resolve().parents[2]
class ProtectionGuardTests(unittest.TestCase):
 def test_exact_engine_transition_only(self):
  old=subprocess.check_output(['git','show','4194236:hub/trading/autonomous_simulation.py'],cwd=ROOT)
  current=(ROOT/'hub/trading/autonomous_simulation.py').read_bytes()
  self.assertTrue(approved_protection_change(old,current))
  self.assertFalse(approved_protection_change(old,current.replace(b'*.95',b'*.50',1)))
  self.assertFalse(approved_protection_change(old+b'\n',current))
