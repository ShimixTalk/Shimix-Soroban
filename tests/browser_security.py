"""Run against localhost only; synthetic fixtures and network interception protect user data."""
import json
import os
from pathlib import Path
import threading
import http.server
import functools
import unittest
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
KEY='shimix-trading-demo-v1'
PASSWORD='Test-Only-Password-2026!'
DEMO={'cash':10000,'positions':{},'journal':[],'watch':['BTC'],'prices':{},'hidden':False}

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class BrowserSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT/'hub')))
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()
        cls.pw=sync_playwright().start()
        opts={'headless':True}
        if os.environ.get('SHIMIX_CHROMIUM'):opts['executable_path']=os.environ['SHIMIX_CHROMIUM']
        cls.browser=cls.pw.chromium.launch(**opts)
    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.pw.stop();cls.server.shutdown();cls.server.server_close()
    def setUp(self):
        self.context=self.browser.new_context(accept_downloads=True,service_workers='block')
        self.page=self.context.new_page();self.errors=[]
        self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.page.route('https://**/*',lambda r:r.fulfill(status=503,body='{}',content_type='application/json'))
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/trading/index.html')
        self.page.wait_for_function("()=>document.querySelector('#shimixEncryptedExport') !== null")
        self.page.evaluate('(arg)=>localStorage.setItem(arg.key,JSON.stringify(arg.data))',{'key':KEY,'data':DEMO})
        self.page.on('dialog',lambda d:d.accept())
    def tearDown(self):
        self.context.close()
    def export(self):
        self.page.locator('#shimixBackupPass').fill(PASSWORD)
        with self.page.expect_download() as d:self.page.locator('#shimixEncryptedExport').click(force=True)
        return Path(d.value.path()).read_text()
    def restore(self,text,password=PASSWORD):
        self.page.locator('#shimixBackupPass').fill(password)
        self.page.locator('#shimixEncryptedImport').set_input_files({'name':'fixture.json','mimeType':'application/json','buffer':text.encode()})
        self.page.wait_for_function("()=>document.querySelector('#shimixEncryptedStatus').textContent.startsWith('Restauration')")
        return self.page.locator('#shimixEncryptedStatus').text_content()
    def stored(self):return json.loads(self.page.evaluate('(k)=>localStorage.getItem(k)',KEY))
    def test_page_loads_without_javascript_errors(self):
        self.assertEqual(self.errors,[])
        self.assertTrue(self.page.locator('#shimixExportAll').is_disabled())
    def test_encrypted_roundtrip_restores_local_data(self):
        envelope=self.export();self.assertNotIn('10000',json.loads(envelope)['ciphertext'])
        self.page.evaluate('(k)=>localStorage.setItem(k,JSON.stringify({cash:1}))',KEY)
        self.assertIn('terminée',self.restore(envelope));self.assertEqual(self.stored(),DEMO)
        self.page.reload();self.assertEqual(self.errors,[])
    def test_wrong_password_preserves_data(self):
        envelope=self.export();self.assertIn('impossible',self.restore(envelope,'Wrong-Password-2026!'));self.assertEqual(self.stored(),DEMO)
    def test_modified_ciphertext_preserves_data(self):
        envelope=json.loads(self.export());c=envelope['ciphertext'];envelope['ciphertext']=('B' if c[0]=='A' else 'A')+c[1:]
        self.assertIn('impossible',self.restore(json.dumps(envelope)));self.assertEqual(self.stored(),DEMO)
    def test_unknown_kdf_preserves_data(self):
        envelope=json.loads(self.export());envelope['kdf']='unknown'
        self.assertIn('impossible',self.restore(json.dumps(envelope)));self.assertEqual(self.stored(),DEMO)
    def test_large_encrypted_backup_roundtrip(self):
        data={**DEMO,'journal':[{'date':'2026-11-10','id':'BTC','side':'Achat','n':.001,'p':50000} for _ in range(4000)]}
        self.page.evaluate('(arg)=>localStorage.setItem(arg.key,JSON.stringify(arg.data))',{'key':KEY,'data':data})
        envelope=self.export();self.assertGreater(len(envelope),300000)
        self.assertIn('terminée',self.restore(envelope));self.assertEqual(self.stored(),data)
    def test_import_validation_rejects_prototype_and_live_mode(self):
        for data in ({KEY:{**DEMO,'positions':{'BTC':-1}}},{KEY:{**DEMO,'watch':['<img onerror=alert(1)>']}},{KEY:{**DEMO,'realTradingEnabled':True}}):
            self.assertTrue(self.page.evaluate('(data)=>{try{ShimixSecurity.entries(data);return false}catch(e){return true}}',data))
        self.assertTrue(self.page.evaluate("()=>{try{ShimixSecurity.entries(JSON.parse('{\"shimix-trading-prefs\":{\"__proto__\":{\"polluted\":true}}}'));return false}catch(e){return true}}"))
    def test_journal_html_is_escaped(self):
        self.page.evaluate("()=>{state.journal=[{date:'<img src=x onerror=alert(1)>',side:'Achat',id:'BTC',n:1,p:10}];render()}")
        self.assertEqual(self.page.locator('#portfolio img').count(),0)
        self.assertIn('<img',self.page.locator('#portfolio').text_content())
    def test_quote_failure_does_not_reuse_previous_quotes(self):
        self.page.evaluate("()=>{botQuotes={BTC:100,ETH:100,SOL:100};bot.holdings={BTC:1}}")
        self.page.route('https://api.coingecko.com/api/v3/simple/price?**',lambda r:r.fulfill(json={'ethereum':{'eur':200},'solana':{'eur':100},'cardano':{'eur':1}}))
        self.page.evaluate('()=>botRefresh()')
        self.assertFalse(self.page.evaluate("()=>Object.hasOwn(botQuotes,'BTC')"))
    def test_indicator_and_finite_order_checks(self):
        self.assertEqual(self.page.evaluate('()=>botRSI(Array(30).fill(10))'),50)
        self.page.evaluate("()=>{state.prices.BTC=1e308;document.querySelector('#tradeqty').value='1e308';trade('Achat')}")
        self.assertTrue(self.page.evaluate('()=>Number.isFinite(state.cash)'))
    def test_synthetic_crypto_selftest(self):
        self.page.locator('#shimixCryptoTest').click(force=True)
        self.page.wait_for_function("()=>document.querySelector('#shimixCryptoTestResult').textContent.includes('Test réussi')")
        self.assertEqual(self.stored(),DEMO)

    def remote_fixture(self):
        self.fixture={'capital':1600,'value':1604.11,'cash':1360,'updatedAt':'2026-11-11T15:51:06Z','enabled':True,'holdings':{'BTC':0.001},'logs':[]}
        self.page.route('https://raw.githubusercontent.com/**/robot-state.json?**',lambda r:r.fulfill(json=self.fixture))
        self.page.evaluate('()=>botRemoteRefresh()')
        self.page.wait_for_function("()=>document.querySelector('#robotEvolutionRefreshStatus').textContent.startsWith('Résultats mis à jour.')")
        return self.page.locator('#robotEvolutionRefreshStatus')
    def test_remote_refresh_unchanged_has_visible_feedback_and_preserves_local_data(self):
        status=self.remote_fixture();before=self.page.evaluate('()=>JSON.stringify({...localStorage})')
        self.page.get_by_role('button',name='Actualiser mon évolution',exact=True).click()
        self.page.wait_for_function("()=>document.querySelector('#robotEvolutionRefreshStatus').textContent.startsWith('Données à jour, résultat inchangé.')")
        self.assertTrue(status.is_visible());self.assertIn('Vérifié le',status.text_content());self.assertIn('Dernier calcul du robot',status.text_content());self.assertEqual(status.get_attribute('role'),'status')
        self.assertEqual(before,self.page.evaluate('()=>JSON.stringify({...localStorage})'));self.assertEqual(self.errors,[])
    def test_remote_refresh_new_data_updates_visible_summary(self):
        status=self.remote_fixture();self.fixture.update(value=1605.25,updatedAt='2026-11-11T16:00:00Z')
        self.page.get_by_role('button',name='Actualiser mon évolution',exact=True).click();self.page.wait_for_function("()=>document.querySelector('#robotExclusiveStatus').textContent.includes('1605.25')")
        self.assertTrue(status.text_content().startswith('Résultats mis à jour.'));self.assertIn('+5.25',self.page.locator('#robotExclusiveStatus').text_content());self.assertEqual(self.errors,[])
    def test_remote_refresh_busy_blocks_duplicate_calls(self):
        status=self.remote_fixture()
        self.page.evaluate("""()=>{window.remoteCalls=0;const original=window.fetch;window.fetch=(u,o)=>{if(String(u).includes('/robot-state.json')){window.remoteCalls++;return new Promise(resolve=>{window.finishRemote=()=>resolve(new Response(JSON.stringify({capital:1600,value:1604.11,cash:1360,updatedAt:'2026-11-11T15:51:06Z',enabled:true,holdings:{BTC:.001},logs:[]})))})}return original(u,o)};botRemoteRefresh();botRemoteRefresh()}""")
        self.assertEqual(status.text_content(),'Actualisation…');self.assertEqual(self.page.locator('[data-remote-refresh]:disabled').count(),2);self.assertEqual(self.page.evaluate('()=>window.remoteCalls'),1)
        self.page.evaluate('()=>window.finishRemote()');self.page.wait_for_function("()=>!document.querySelector('[data-remote-refresh]').disabled")
        self.assertEqual(self.page.locator('[data-remote-refresh]:disabled').count(),0);self.assertEqual(self.errors,[])
    def test_remote_refresh_network_error_keeps_both_last_results_and_recovers(self):
        status=self.remote_fixture();summary=self.page.locator('#robotExclusiveStatus').text_content();detail=self.page.locator('#botRemoteState').text_content()
        self.page.route('https://raw.githubusercontent.com/**/robot-state.json?**',lambda r:r.abort())
        self.page.evaluate('()=>botRemoteRefresh()');self.assertIn('Dernier résultat conservé',status.text_content());self.assertTrue(status.is_visible());self.assertEqual(self.page.locator('#robotExclusiveStatus').text_content(),summary);self.assertEqual(self.page.locator('#botRemoteState').text_content(),detail);self.assertEqual(self.page.locator('[data-remote-refresh]:disabled').count(),0)
        self.page.route('https://raw.githubusercontent.com/**/robot-state.json?**',lambda r:r.fulfill(json=self.fixture));self.page.evaluate('()=>botRemoteRefresh()');self.assertIn('Données à jour',status.text_content());self.assertEqual(self.errors,[])
    def test_remote_refresh_invalid_and_http_errors_do_not_replace_results(self):
        status=self.remote_fixture();summary=self.page.locator('#robotExclusiveStatus').text_content()
        for body,http_status in [({'capital':1600,'value':None,'cash':1360},200),({},503)]:
            self.page.route('https://raw.githubusercontent.com/**/robot-state.json?**',lambda r,request,body=body,http_status=http_status:r.fulfill(status=http_status,json=body))
            self.page.evaluate('()=>botRemoteRefresh()');self.assertIn('Actualisation impossible',status.text_content());self.assertEqual(self.page.locator('#robotExclusiveStatus').text_content(),summary);self.assertEqual(self.page.locator('[data-remote-refresh]:disabled').count(),0)
        self.assertEqual(self.errors,[])
    def test_remote_refresh_timeout_clears_busy_and_keeps_last_result(self):
        status=self.remote_fixture();summary=self.page.locator('#robotExclusiveStatus').text_content()
        self.page.evaluate("""()=>{const original=window.fetch,timer=window.setTimeout;window.setTimeout=(f,ms,...args)=>timer(f,ms===15000?0:ms,...args);window.fetch=(u,o)=>String(u).includes('/robot-state.json')?new Promise((resolve,reject)=>o.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')))):original(u,o)}""")
        self.page.evaluate('()=>botRemoteRefresh()');self.assertIn('15 secondes',status.text_content());self.assertEqual(self.page.locator('#robotExclusiveStatus').text_content(),summary);self.assertEqual(self.page.locator('[data-remote-refresh]:disabled').count(),0);self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main(verbosity=2)
