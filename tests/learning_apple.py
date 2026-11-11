"""WebKit compatibility at iPhone/Mac screen profiles, not physical Apple hardware certification."""
import functools,http.server,json,os,threading,unittest,mimetypes,urllib.parse
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class AppleLearningTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.http=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'hub')));threading.Thread(target=cls.http.serve_forever,daemon=True).start();cls.pw=sync_playwright().start()
  cls.engine=os.environ.get('SHIMIX_BROWSER','webkit');opts={'headless':True}
  if cls.engine=='chromium' and os.environ.get('SHIMIX_CHROMIUM'):opts['executable_path']=os.environ['SHIMIX_CHROMIUM']
  cls.browser=getattr(cls.pw,cls.engine).launch(**opts)
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.pw.stop();cls.http.shutdown();cls.http.server_close()
 def device(self,mobile):
  options=dict(locale='fr-FR',timezone_id='Europe/Paris',accept_downloads=True,service_workers='block')
  if mobile:options.update(self.pw.devices['iPhone 13']);options.pop('default_browser_type',None)
  else:options.update(viewport={'width':1440,'height':900},device_scale_factor=1)
  ctx=self.browser.new_context(**options);self.addCleanup(ctx.close);page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  report=json.loads((ROOT/'hub/trading/learning-data/report.json').read_text())
  def external(r):
   if '/learning-data/report.json' in r.request.url:r.fulfill(json=report)
   elif '/learning-data/openai-review-input.json' in r.request.url:r.fulfill(json={'status':'disabled','spentUsd':0})
   else:r.fulfill(status=503,json={})
  page.route('https://**/*',external)
  def local_https(route):
   path=(ROOT/'hub'/urllib.parse.urlsplit(route.request.url).path.lstrip('/')).resolve()
   if not path.is_relative_to((ROOT/'hub').resolve()) or not path.is_file():return route.fulfill(status=404,body='Not found')
   headers=json.loads((ROOT/'ops/render-security-headers.json').read_text())['headers']
   route.fulfill(body=path.read_bytes(),headers=headers,content_type=mimetypes.guess_type(path)[0] or 'application/octet-stream')
  page.route('https://shimix.test/**',local_https);response=page.goto('https://shimix.test/trading/index.html');self.assertEqual(response.headers.get('x-frame-options'),'DENY');self.assertEqual(response.headers.get('referrer-policy'),'strict-origin-when-cross-origin');page.locator('[data-view=learning]').click();page.wait_for_function("()=>document.querySelector('[data-learning-status]').textContent.startsWith('Dernière collecte')")
  return page,errors
 def readable(self,mobile):
  page,errors=self.device(mobile);panel=page.locator('#robotLearningPanel');self.assertTrue(panel.is_visible());self.assertIn('1 600',panel.text_content());self.assertIn('OpenAI',panel.text_content());self.assertEqual(errors,[])
  self.assertTrue(panel.evaluate('(e)=>e.getBoundingClientRect().width<=innerWidth+1'))
  self.assertTrue(panel.evaluate('(e)=>e.scrollWidth<=e.clientWidth+2'))
  for view in ['bot','safety','learning']:
   page.locator('[data-view='+view+']').click();self.assertEqual(page.locator('[data-view='+view+']').get_attribute('aria-pressed'),'true')
  self.assertTrue(panel.is_visible());self.assertEqual(errors,[])
  before=page.evaluate('()=>JSON.stringify({...localStorage})')
  for kind in ['chatgpt','codex']:
   page.locator('[data-assistant-prepare='+kind+']').click();self.assertIn('Simulation uniquement',page.locator('[data-assistant-message]').input_value());self.assertTrue(panel.evaluate('(e)=>e.scrollWidth<=e.clientWidth+2'))
  with page.expect_download() as download:page.locator('[data-assistant-download]').click()
  self.assertIn('branche séparée',Path(download.value.path()).read_text());self.assertEqual(before,page.evaluate('()=>JSON.stringify({...localStorage})'));self.assertEqual(errors,[])
 def refresh_export(self,mobile):
  page,errors=self.device(mobile);before=page.evaluate('()=>JSON.stringify({...localStorage})');page.locator('[data-learning-refresh]').click();page.wait_for_function("()=>document.querySelector('[data-learning-status]').textContent.startsWith('Dernière collecte')")
  with page.expect_download() as download:page.get_by_role('button',name='Préparer le dossier d’analyse IA (sans appel API)').click()
  self.assertEqual(json.loads(Path(download.value.path()).read_text())['spentUsd'],0);self.assertEqual(page.evaluate('()=>JSON.stringify({...localStorage})'),before);self.assertEqual(errors,[])
 def test_iphone_layout(self):self.readable(True)
 def test_mac_layout(self):self.readable(False)
 def test_iphone_refresh_and_export(self):self.refresh_export(True)
 def test_mac_refresh_and_export(self):self.refresh_export(False)
if __name__=='__main__':unittest.main(verbosity=2)
