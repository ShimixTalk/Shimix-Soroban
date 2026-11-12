"""Execute the pinned PR9 writer against copied current data, then test PR8/10 consumers.
No business network access or runtime-state writes. All browser requests intercepted.
"""
import argparse,copy,datetime as dt,json,mimetypes,os,re,shutil,subprocess,sys,tempfile,urllib.parse
from pathlib import Path
from playwright.sync_api import sync_playwright
import playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'learning'))
from collect import build
from preview import Files
from journal import observe_portfolios,net_cash_flow

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--automation-ref',required=True);parser.add_argument('--require-refresh-feedback',action='store_true');args=parser.parse_args()
 if not re.fullmatch('[0-9a-f]{40}',args.automation_ref):raise ValueError('Exact automation commit required')
 source=ROOT/'hub/trading/three-portfolios.json';raw=source.read_bytes();original=json.loads(raw)
 with tempfile.TemporaryDirectory(prefix='shimix-joint-') as folder:
  temp=Path(folder)
  for name in ['profile-accounting.mjs','simulation-safety.mjs','shimix-three-portfolios.mjs']:
   (temp/name).write_bytes(subprocess.check_output(['git','show',args.automation_ref+':scripts/'+name],cwd=ROOT))
  node=shutil.which('node') or str(Path(playwright.__file__).parent/'driver/node')
  runner=r'''
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const original=JSON.parse(readFileSync(0,'utf8'));
const ids={BTC:'bitcoin',ETH:'ethereum',SOL:'solana',LINK:'chainlink',AVAX:'avalanche-2',DOGE:'dogecoin'};
const prices=Object.assign({},...original.portfolios.map(p=>p.lastPrices));
let saved,puts=0;process.env.GITHUB_TOKEN='synthetic-test-only';
globalThis.fetch=async(url,opts={})=>{
 let data;
 if(String(url).startsWith('https://api.github.com/repos/ShimixTalk/Shimix-Soroban/contents/hub/trading/three-portfolios.json')){
  if(opts.method==='PUT'){puts++;saved=JSON.parse(Buffer.from(JSON.parse(opts.body).content,'base64').toString());return {ok:true,json:async()=>({})};}
  data={sha:'synthetic-sha',content:Buffer.from(JSON.stringify(original)).toString('base64')};
 }else if(String(url).startsWith('https://api.coingecko.com/api/v3/coins/markets?')){
  data=Object.entries(ids).map(([s,id])=>({id,current_price:prices[s],total_volume:1e8,price_change_percentage_24h:0}));
 }else throw Error('Unexpected business network call');
 return {ok:true,json:async()=>data};
};
await import('./shimix-three-portfolios.mjs');
process.on('beforeExit',()=>{assert.equal(puts,1);assert.ok(saved);console.log('JOINT_RESULT:'+JSON.stringify(saved));});
'''
  (temp/'run.mjs').write_text(runner)
  run=subprocess.run([node,str(temp/'run.mjs')],input=json.dumps(original),text=True,capture_output=True,timeout=30)
  if run.returncode:raise RuntimeError(run.stderr)
  result=json.loads(next(line.removeprefix('JOINT_RESULT:') for line in run.stdout.splitlines() if line.startswith('JOINT_RESULT:')))
  for before,after in zip(original['portfolios'],result['portfolios']):
   for key in ['id','initial','cash','holdings','costBasis','trades','feesPaid','peak','paused','stop','maxTrade','maxAllocation','fee','spread','slippage']:
    assert before.get(key)==after.get(key),(before['id'],key)
   assert after['history'][:-1]==before['history']
   assert after['netProfit']==round(after['value']-after['initial']-net_cash_flow(after),2)
  # Repeat the real writer: migration must not duplicate flows or alter balances.
  repeat=subprocess.run([node,str(temp/'run.mjs')],input=json.dumps(result),text=True,capture_output=True,timeout=30)
  if repeat.returncode:raise RuntimeError(repeat.stderr)
  repeated=json.loads(next(line.removeprefix('JOINT_RESULT:') for line in repeat.stdout.splitlines() if line.startswith('JOINT_RESULT:')))
  for a,b in zip(result['portfolios'],repeated['portfolios']):
   for k in ['cashFlows','netProfit','cash','holdings','trades']:assert a[k]==b[k],k
  observation=observe_portfolios(result,'joint-fixture',result['updatedAt'])
  assert [p['netProfit'] for p in observation['profiles']]==[p['netProfit'] for p in result['portfolios']]
  class CopiedState(Files):
   def file(self,path,ref=None,optional=False):
    return json.dumps(result).encode() if path=='hub/trading/three-portfolios.json' else super().file(path,ref,optional)
  policy=json.loads((ROOT/'learning/policy.json').read_text());policy['historyRequestsPerRun']=0
  _,report=build(CopiedState(ROOT),policy,dt.datetime.now(dt.timezone.utc))
  assert [p['netProfit'] for p in report['observedPortfolios']]==[p['netProfit'] for p in result['portfolios']]
  with sync_playwright() as pw:
   opts={'headless':True}
   if os.environ.get('SHIMIX_CHROMIUM'):opts['executable_path']=os.environ['SHIMIX_CHROMIUM']
   browser=pw.chromium.launch(**opts);ctx=browser.new_context(service_workers='block');page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   def route(r):
    url=r.request.url
    if url.startswith('https://shimix.test/'):
     path=(ROOT/'hub'/urllib.parse.urlsplit(url).path.lstrip('/')).resolve()
     if not path.is_relative_to((ROOT/'hub').resolve()) or not path.is_file():return r.fulfill(status=404,body='missing')
     return r.fulfill(body=path.read_bytes(),content_type=mimetypes.guess_type(path)[0] or 'application/octet-stream')
    if '/learning-data/report.json' in url:return r.fulfill(json=report)
    if '/robot-state.json' in url:return r.fulfill(body=(ROOT/'hub/trading/robot-state.json').read_bytes(),content_type='application/json')
    if '/three-portfolios.json' in url:return r.fulfill(json=result)
    r.fulfill(status=503,json={})
   page.route('https://**/*',route);page.goto('https://shimix.test/trading/index.html');page.locator('[data-view=learning]').click();page.wait_for_function("()=>document.querySelector('[data-learning-status]').textContent.startsWith('Dernière collecte')")
   rows=page.locator('#robotLearningPanel table').first.locator('tr')
   for i,p in enumerate(result['portfolios'],start=1):
    expected=page.evaluate('(n)=>n.toLocaleString("fr-FR",{maximumFractionDigits:3})',p['netProfit'])
    assert rows.nth(i).locator('td').nth(3).text_content()==expected+' €'
   if args.require_refresh_feedback:
    page.locator('[data-view=bot]').click();page.get_by_role('button',name='Actualiser mon évolution',exact=True).click();page.wait_for_function("()=>document.querySelector('#robotEvolutionRefreshStatus').textContent.includes('Vérifié le')")
    page.get_by_role('button',name='Actualiser mon évolution',exact=True).click();page.wait_for_function("()=>document.querySelector('#robotEvolutionRefreshStatus').textContent.startsWith('Données à jour, résultat inchangé.')")
    assert page.locator('#robotEvolutionRefreshStatus').is_visible()
   assert not errors,errors;ctx.close();browser.close()
 assert source.read_bytes()==raw
 print(json.dumps({'automationRef':args.automation_ref,'realWriterMockedNetwork':'passed','migrationRepeated':'passed','balancesRiskTradesPreserved':True,'existingHistoryPreserved':True,'learningAndDashboard':'passed','refreshFeedback':args.require_refresh_feedback,'productionWrites':0,'profileNetProfits':[p['netProfit'] for p in result['portfolios']]}))
if __name__=='__main__':main()
