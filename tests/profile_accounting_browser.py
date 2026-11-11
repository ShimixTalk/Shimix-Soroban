import functools,http.server,json,shutil,threading,subprocess,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'learning'))
from integration_check import audited_portfolio_state
# Explicit historical fixture; never replace the living state file.
fixture=audited_portfolio_state(subprocess.check_output(['git','show','e39c2a0:hub/trading/three-portfolios.json'],cwd=root))
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox'])
 page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 def route(r):
  if 'raw.githubusercontent.com' in r.request.url and 'three-portfolios.json' in r.request.url:r.fulfill(status=200,content_type='application/json',body=json.dumps(fixture))
  elif r.request.url.startswith('http://127.0.0.1:'):r.continue_()
  else:r.abort()
 page.route('**/*',route)
 page.goto(f'http://127.0.0.1:{server.server_port}/hub/trading/index.html')
 page.evaluate("() => { const root=document.createElement('div');root.id='threePortfoliosResults';document.body.append(root);return loadThreePortfolios(); }")
 page.locator("#threePortfoliosResults").filter(has_text="Transferts nets").wait_for(state="attached")
 text=page.locator('#threePortfoliosResults').text_content()
 assert '-4,01' in text,text
 assert text.count('Transferts nets')==3,text
 assert not errors,errors
 fixture=audited_portfolio_state((root/'hub/trading/three-portfolios.json').read_bytes())
 page.evaluate('()=>loadThreePortfolios()')
 text=page.locator('#threePortfoliosResults').text_content()
 expected=sum(p['netProfit'] for p in fixture['portfolios'])
 expected_text=page.evaluate('(n)=>Number(n).toLocaleString("fr-FR",{style:"currency",currency:"EUR"})',expected)
 assert expected_text in text,text
 assert not errors,errors
 print('Browser check passed: total -4.01 EUR, three transfer disclosures, no JavaScript errors.')
 browser.close()
server.shutdown()
