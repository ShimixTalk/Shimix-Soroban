import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collect import GitHub,PREFIX
class GitTransactionTests(unittest.TestCase):
 def fake(self,changed=False):
  repo=GitHub('ShimixTalk/Shimix-Soroban','shimix-hub','test-not-used');path=PREFIX+'report.json';repo.original[path]='old';calls=[]
  def api(endpoint,method='GET',body=None):
   calls.append((endpoint,method,body))
   if endpoint.startswith('/contents/'):return {'sha':'old'}
   if endpoint=='/git/blobs':return {'sha':'new-report'}
   if endpoint.startswith('/git/ref/heads/'):return {'object':{'sha':'head-with-latest-data'}}
   if endpoint=='/git/commits/head-with-latest-data':return {'tree':{'sha':'tree-with-latest-data'}}
   if endpoint=='/git/trees/tree-with-latest-data?recursive=1':return {'truncated':False,'tree':[{'path':path,'type':'blob','sha':'other-observer' if changed else 'old'},{'path':'hub/trading/robot-state.json','type':'blob','sha':'latest-state'}]}
   if endpoint=='/git/trees':return {'sha':'new-tree'}
   if endpoint=='/git/commits':return {'sha':'new-commit'}
   if endpoint.startswith('/git/refs/heads/'):return {'ok':True}
   raise AssertionError(endpoint)
  repo.api=api;return repo,path,calls
 def test_learning_write_between_precheck_and_head_cannot_be_lost(self):
  repo,path,calls=self.fake(changed=True)
  with self.assertRaises(ValueError):repo.commit({path:b'{}'})
  self.assertFalse(any(method=='PATCH' for _,method,_ in calls));self.assertFalse(any(endpoint=='/git/trees' and method=='POST' for endpoint,method,_ in calls))
 def test_other_robot_updates_remain_in_bound_base_tree(self):
  repo,path,calls=self.fake();self.assertEqual(repo.commit({path:b'{}'}),'new-commit')
  tree=next(body for endpoint,method,body in calls if endpoint=='/git/trees' and method=='POST')
  self.assertEqual(tree['base_tree'],'tree-with-latest-data');self.assertEqual([e['path'] for e in tree['tree']],[path])
  patch=next(body for _,method,body in calls if method=='PATCH');self.assertFalse(patch['force'])
if __name__=='__main__':unittest.main()
