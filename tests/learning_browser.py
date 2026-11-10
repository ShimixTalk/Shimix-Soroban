"""Local, synthetic read-only dashboard regression tests; all external requests intercepted."""
import functools,http.server,json,os,threading,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class LearningBrowserTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'hub')));threading.Thread(target=cls.server.serve_forever,daemon=True).start()
  cls.pw=sync_playwright().start();opts={'headless':True}
  if os.environ.get('SHIMIX_CHROMIUM'):opts['executable_path']=os.environ['SHIMIX_CHROMIUM']
  cls.browser=cls.pw.chromium.launch(**opts)
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.pw.stop();cls.server.shutdown();cls.server.server_close()
 def setUp(self):
  self.context=self.browser.new_context(accept_downloads=True,service_workers='block');self.page=self.context.new_page();self.errors=[];self.requests=[]
  self.page.on('pageerror',lambda e:self.errors.append(str(e)));self.page.on('request',lambda r:self.requests.append(r.url))
  self.report=json.loads((ROOT/'hub/trading/learning-data/report.json').read_text())
  def external(r):
   if '/learning-data/report.json' in r.request.url:r.fulfill(json=self.report)
   elif '/learning-data/openai-review-input.json' in r.request.url:r.fulfill(json={'status':'disabled','networkCalls':0,'spentUsd':0})
   else:r.fulfill(status=503,json={})
  self.page.route('https://**/*',external)
  self.page.goto(f'http://127.0.0.1:{self.server.server_port}/trading/index.html')
  self.page.locator('[data-view=learning]').click()
  self.page.wait_for_function("()=>document.querySelector('[data-learning-status]').textContent.startsWith('Dernière collecte')")
 def tearDown(self):self.context.close()
 def test_dashboard_shows_capital_zero_budget_and_rejected_hypotheses(self):
  text=self.page.locator('#robotLearningPanel').text_content();self.assertIn('1 600',text);self.assertIn('Amélioration non confirmée',text);self.assertIn('budget mensuel 0 USD',text);self.assertEqual(self.errors,[])
 def test_dashboard_refresh_does_not_change_local_simulations(self):
  before=self.page.evaluate('()=>JSON.stringify({...localStorage})');self.page.locator('[data-learning-refresh]').click();self.page.wait_for_function("()=>document.querySelector('[data-learning-status]').textContent.startsWith('Dernière collecte')");self.assertEqual(before,self.page.evaluate('()=>JSON.stringify({...localStorage})'))
 def test_untrusted_error_is_rendered_as_text(self):
  self.report['errors']=[{'code':'fixture','message':'<img src=x onerror=alert(1)>'}];self.page.locator('[data-learning-refresh]').click();self.page.wait_for_function("()=>document.querySelector('[data-learning-content]').textContent.includes('onerror')");self.assertEqual(self.page.locator('#robotLearningPanel img').count(),0)
 def test_prepare_ai_download_makes_no_openai_request(self):
  with self.page.expect_download() as d:self.page.get_by_role('button',name='Préparer le dossier d’analyse IA (sans appel API)').click()
  content=json.loads(Path(d.value.path()).read_text());self.assertEqual(content['spentUsd'],0);self.assertFalse(any('api.openai.com' in u for u in self.requests));self.assertEqual(self.errors,[])
 def test_missing_history_is_not_a_performance(self):
  self.report['hypotheses']={'prudent':{'status':'insufficient_data','points':12,'required':120}};self.page.locator('[data-learning-refresh]').click();self.page.wait_for_function("()=>document.querySelector('[data-learning-content]').textContent.includes('Données insuffisantes')");self.assertIn('12 / 120',self.page.locator('#robotLearningPanel').text_content())
if __name__=='__main__':unittest.main(verbosity=2)
