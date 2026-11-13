"""Synthetic protection display tests. No market or GitHub requests are performed."""
import functools,http.server,os,threading,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
class ProtectionBrowserTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'hub')))
  threading.Thread(target=cls.server.serve_forever,daemon=True).start();cls.pw=sync_playwright().start()
  cls.browser=cls.pw.chromium.launch(headless=True,executable_path=os.environ.get('SHIMIX_CHROMIUM'))
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.pw.stop();cls.server.shutdown();cls.server.server_close()
 def setUp(self):
  self.context=self.browser.new_context(service_workers='block');self.page=self.context.new_page();self.errors=[]
  self.page.on('pageerror',lambda e:self.errors.append(str(e)))
  self.page.route('https://**/*',lambda r:r.fulfill(status=503,json={}))
  self.page.goto(f'http://127.0.0.1:{self.server.server_port}/trading/index.html')
 def tearDown(self):self.context.close()
 def test_pause_and_manual_resume_are_visible(self):
  self.page.evaluate('()=>renderGlobalProtection({globalProtection:{version:1,valuationComplete:true,buyPaused:true}})')
  self.assertIn('sorties toujours actives',self.page.locator('#globalProtectionStatus').text_content())
  self.page.evaluate('()=>renderGlobalProtection({globalProtection:{version:1,valuationComplete:true,requiresApprovalToResume:true,pendingAssets:[]}})')
  self.assertIn('accord explicite',self.page.locator('#globalProtectionStatus').text_content());self.assertEqual(self.errors,[])
 def test_incomplete_valuation_keeps_last_overview(self):
  self.page.evaluate("()=>{document.querySelector('#robotExclusiveStatus').textContent='Dernier relevé connu : 1 450 €';}")
  self.page.route('**/robot-state.json?*',lambda r:r.fulfill(json=dict(capital=1600,value=None,globalProtection=dict(version=1,valuationComplete=False,requiresApprovalToResume=True,pendingAssets=['BTC']))))
  self.page.evaluate('()=>botRemoteRefresh()')
  self.assertIn('Cours manquants',self.page.locator('#globalProtectionStatus').text_content())
  self.assertIn('1 450',self.page.locator('#robotExclusiveStatus').text_content())
  self.assertIn('Valorisation incomplète',self.page.locator('#robotEvolutionRefreshStatus').text_content());self.assertEqual(self.errors,[])
 def test_no_claim_of_activation_for_legacy_state(self):
  self.page.evaluate('()=>renderGlobalProtection({globalProtection:{version:1,buyPaused:true}})')
  self.page.evaluate('()=>renderGlobalProtection({capital:1600,maxLossPercent:50})')
  self.assertEqual(self.page.locator('#globalProtectionStatus').count(),0)
if __name__=='__main__':unittest.main(verbosity=2)
