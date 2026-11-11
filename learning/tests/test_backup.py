import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backup import CORE,create,restore,verify
class BackupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name);self.root=self.base/'repo';self.root.mkdir()
  for name in CORE:
   p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{"simulationOnly":true}\n')
  p=self.root/'hub/trading/learning-data/events/fixture.jsonl';p.parent.mkdir(parents=True);p.write_text('{"event":"simulation"}\n')
 def test_round_trip_preserves_sources_and_learning_journal(self):
  original={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()};check=create(self.root,self.base/'archive','a'*40);m=restore(self.base/'archive',self.base/'restored',check)
  self.assertEqual(len(m['files']),5);self.assertEqual(original,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()});self.assertEqual((self.base/'restored/hub/trading/learning-data/events/fixture.jsonl').read_text(),'{"event":"simulation"}\n')
 def test_tampered_file_is_rejected_before_restore(self):
  create(self.root,self.base/'archive');(self.base/'archive'/CORE[0]).write_text('tampered')
  with self.assertRaises(ValueError):restore(self.base/'archive',self.base/'restored')
  self.assertFalse((self.base/'restored').exists())
 def test_manifest_traversal_is_rejected(self):
  create(self.root,self.base/'archive');p=self.base/'archive/manifest.json';m=json.loads(p.read_text());m['files'][0]['path']='../outside';p.write_text(json.dumps(m))
  with self.assertRaises(ValueError):verify(self.base/'archive')
 def test_source_symlinks_cannot_capture_secrets(self):
  p=self.root/'hub/trading/learning-data/link';p.symlink_to(self.base/'outside');(self.base/'outside').write_text('not part of simulation')
  with self.assertRaises(ValueError):create(self.root,self.base/'archive')
 def test_existing_destination_cannot_be_replaced(self):
  create(self.root,self.base/'archive');target=self.base/'existing';target.mkdir();(target/'keep').write_text('preserve')
  with self.assertRaises(ValueError):restore(self.base/'archive',target)
  self.assertEqual((target/'keep').read_text(),'preserve')
 def test_extra_file_and_wrong_manifest_checksum_are_rejected(self):
  create(self.root,self.base/'archive')
  with self.assertRaises(ValueError):verify(self.base/'archive','0'*64)
  (self.base/'archive/unexpected').write_text('unexpected')
  with self.assertRaises(ValueError):verify(self.base/'archive')
if __name__=='__main__':unittest.main()
