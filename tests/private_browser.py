"""Real WebAuthn ceremonies via Chromium's virtual authenticator; synthetic data only."""
import base64
import json
import os
from pathlib import Path
import subprocess
import unittest
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
PASSWORD='Test-Only-Encryption-2026!'
BOOTSTRAP='test-only-bootstrap-token-at-least-32-characters'
KEY='shimix-trading-demo-v1'
DATA={'cash':1600,'positions':{},'journal':[],'watch':['BTC'],'prices':{},'hidden':False}

class PrivateBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        opts={'headless':True}
        if os.environ.get('SHIMIX_CHROMIUM'):opts['executable_path']=os.environ['SHIMIX_CHROMIUM']
        cls.browser=cls.pw.chromium.launch(**opts)
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.pw.stop()
    def setUp(self):
        self.proc=subprocess.Popen(['node','private-server/tests/browser-fixture.mjs'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        line=self.proc.stdout.readline();assert line,self.proc.stderr.read()
        self.origin=json.loads(line)['origin'];self.contexts=[];self.errors=[];self.addCleanup(self.cleanup_fixture)
        self.a,self.cdp,self.auth=self.device()
        self.a.goto(self.origin+'/private/index.html')
        self.a.locator('#bootstrap').fill(BOOTSTRAP)
        self.a.locator('#register').click()
        self.a.wait_for_function("()=>document.querySelector('#status').textContent.includes('Connexion réussie')")
    def cleanup_fixture(self):
        for c in self.contexts:c.close()
        self.proc.terminate();self.proc.wait(timeout=10);self.proc.stdout.close();self.proc.stderr.close()
    def device(self,credentials=None):
        context=self.browser.new_context(accept_downloads=True,service_workers='block');self.contexts.append(context)
        page=context.new_page();page.on('pageerror',lambda e:self.errors.append(str(e)))
        page.on('dialog',lambda d:d.accept())
        page.route('https://**/*',lambda r:r.fulfill(status=503,json={}))
        cdp=context.new_cdp_session(page);cdp.send('WebAuthn.enable')
        auth=cdp.send('WebAuthn.addVirtualAuthenticator',{'options':{'protocol':'ctap2','transport':'internal','hasResidentKey':True,'hasUserVerification':True,'isUserVerified':True,'automaticPresenceSimulation':True}})['authenticatorId']
        for credential in credentials or []:cdp.send('WebAuthn.addCredential',{'authenticatorId':auth,'credential':credential})
        return page,cdp,auth
    def seed(self,page,data=DATA):page.evaluate('(a)=>localStorage.setItem(a.key,JSON.stringify(a.data))',{'key':KEY,'data':data})
    def unlock(self,page):
        page.locator('#password').fill(PASSWORD);page.locator('#unlock').click()
        page.wait_for_function("()=>document.querySelector('#status').textContent.includes('Coffre déverrouillé')")
    def upload(self,page):
        page.locator('#push').click()
        page.wait_for_function("()=>document.querySelector('#status').textContent.includes('Copie chiffrée synchronisée')")
    def second(self):
        credentials=self.cdp.send('WebAuthn.getCredentials',{'authenticatorId':self.auth})['credentials']
        page,cdp,auth=self.device(credentials);page.goto(self.origin+'/private/index.html');page.locator('#login').click()
        page.wait_for_function("()=>document.querySelector('#status').textContent.includes('Connexion réussie')")
        return page,cdp,auth
    def test_enroll_login_and_two_device_encrypted_restore(self):
        self.seed(self.a);self.unlock(self.a);self.upload(self.a)
        second,_,_=self.second();self.unlock(second);second.locator('#pull').click()
        second.wait_for_function("()=>document.querySelector('#status').textContent.includes('restaurée')")
        self.assertEqual(second.evaluate('(k)=>JSON.parse(localStorage.getItem(k))',KEY),DATA)
        vault=second.evaluate("async()=>await(await fetch('/api/vault')).json()")
        self.assertNotIn('cash',json.dumps(vault['envelope']))
        self.assertEqual(self.errors,[])
    def test_conflicting_device_keeps_local_copy(self):
        self.seed(self.a);self.unlock(self.a);self.upload(self.a)
        second,_,_=self.second();self.seed(second,{**DATA,'cash':1400});self.unlock(second)
        self.seed(self.a,{**DATA,'cash':1500});self.upload(self.a)
        second.locator('#push').click();second.wait_for_function("()=>document.querySelector('#status').textContent.includes('autre version')")
        self.assertEqual(second.evaluate('(k)=>JSON.parse(localStorage.getItem(k)).cash',KEY),1400)
        vault=second.evaluate("async()=>await(await fetch('/api/vault')).json()")
        self.assertEqual(vault['revision'],2)
    def test_wrong_password_preserves_local_data(self):
        self.seed(self.a);self.unlock(self.a);self.upload(self.a)
        second,_,_=self.second();self.seed(second,{**DATA,'cash':900})
        second.locator('#password').fill('Wrong-Password-2026!');second.locator('#unlock').click()
        second.wait_for_function("()=>document.querySelector('#status').textContent.includes('incorrect')")
        self.assertEqual(second.evaluate('(k)=>JSON.parse(localStorage.getItem(k)).cash',KEY),900)
        self.assertTrue(second.locator('#pull').is_disabled())
    def test_revoke_other_sessions_and_logout(self):
        second,_,_=self.second();self.a.locator('#revoke').click()
        self.a.wait_for_function("()=>document.querySelector('#status').textContent.includes('déconnectées')")
        self.assertEqual(second.evaluate("async()=> (await fetch('/api/vault')).status"),401)
        self.a.locator('#logout').click();self.a.wait_for_function("()=>document.querySelector('#status').textContent.startsWith('Déconnecté')")
        self.assertEqual(self.a.evaluate("async()=> (await fetch('/api/vault')).status"),401)
    def test_new_format_download_restores_in_existing_application(self):
        self.seed(self.a);self.unlock(self.a);self.upload(self.a)
        with self.a.expect_download() as download:self.a.locator('#download').click()
        data=Path(download.value.path()).read_bytes()
        self.assertEqual(json.loads(data)['iterations'],600000)
        self.a.goto(self.origin+'/trading/index.html')
        self.a.evaluate('(k)=>localStorage.setItem(k,JSON.stringify({cash:1}))',KEY)
        self.a.locator('#shimixBackupPass').fill(PASSWORD)
        self.a.locator('#shimixEncryptedImport').set_input_files({'name':'backup.json','mimeType':'application/json','buffer':data})
        self.a.wait_for_function("()=>document.querySelector('#shimixEncryptedStatus').textContent.includes('terminée')")
        self.assertEqual(self.a.evaluate('(k)=>JSON.parse(localStorage.getItem(k))',KEY),DATA)
    def test_opt_in_automatic_sync_follows_local_and_remote_changes(self):
        self.seed(self.a);self.unlock(self.a);self.upload(self.a)
        second,_,_=self.second();self.unlock(second);second.locator('#pull').click()
        second.wait_for_function("()=>document.querySelector('#status').textContent.includes('restaurée')")
        self.a.locator('#auto').check();second.locator('#auto').check()
        self.seed(self.a,{**DATA,'cash':1450});self.a.evaluate('()=>tick()')
        self.a.wait_for_function("()=>document.querySelector('#status').textContent.includes('version 2')")
        second.evaluate('()=>tick()')
        self.assertEqual(second.evaluate('(k)=>JSON.parse(localStorage.getItem(k)).cash',KEY),1450)
    def test_server_rejects_tampered_signature_and_replay(self):
        self.a.locator('#logout').click();self.a.wait_for_function("()=>document.querySelector('#status').textContent.startsWith('Déconnecté')")
        result=self.a.evaluate("""async()=>{const o=await api('/auth/login/options','POST',{});o.challenge=unurl(o.challenge);const c=await navigator.credentials.get({publicKey:o});const response=serialize(c);response.response.signature=(response.response.signature[0]==='A'?'B':'A')+response.response.signature.slice(1);const send=()=>fetch('/api/auth/login/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(response)});return [(await send()).status,(await send()).status]}""")
        self.assertEqual(result,[401,401])
    def test_unverified_authenticator_is_rejected(self):
        self.a.locator('#logout').click();self.a.wait_for_function("()=>document.querySelector('#status').textContent.startsWith('Déconnecté')")
        self.cdp.send('WebAuthn.setUserVerified',{'authenticatorId':self.auth,'isUserVerified':False})
        # Browser must not produce an accepted assertion without user verification.
        self.assertEqual(self.a.evaluate("async()=> (await fetch('/api/vault')).status"),401)
        status=self.a.evaluate("""async()=>{const o=await(await fetch('/api/auth/login/options',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();o.challenge=Uint8Array.from(atob(o.challenge.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));o.timeout=1000;try{await navigator.credentials.get({publicKey:o});return 'unexpected'}catch{return 'rejected'}}""")
        self.assertEqual(status,'rejected')

if __name__=='__main__':unittest.main(verbosity=2)
