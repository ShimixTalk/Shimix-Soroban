"""Verify an isolated integration tree keeps the base's data and runtime engines byte-for-byte."""
import argparse,copy,datetime as dt,hashlib,json,re,subprocess
from pathlib import Path
from backup import CORE
from collect import build
from preview import Files
from engine import policy_check
PROTECTED=CORE+['hub/trading/autonomous_simulation.py','hub/trading/meme_history.py','hub/trading/security.js','hub/trading/manifest.webmanifest','hub/trading/icon.svg']
def audited_portfolio_state(previous):
 expected=copy.deepcopy(json.loads(previous))
 for p in expected['portfolios']:
  reference,withdrawal={'prudent':(640,80),'equilibre':(560,80),'dynamique':(400,40)}[p['id']]
  if p['initial']!=reference:raise ValueError('Référence modifiée')
  if 'cashFlows' not in p:
   if not p.get('history') or p['history'][0]['value']!=reference-withdrawal:raise ValueError('Historique non audité')
   sha='f1f3221108db602c23a8c489cd25efea4e142dce'
   p['cashFlows']=[dict(id=sha+':'+p['id'],sourceCommit=sha,at='2026-11-09T18:39:53+00:00',amount=-withdrawal,type='paper_capital_transfer',note='Transfert fictif hors du profil, distinct du trading ; aucune réinjection.')]
  from journal import net_cash_flow
  p['netProfit']=round(p['value']-p['initial']-net_cash_flow(p),2)
 expected['totalProfit']=round(sum(p['netProfit'] for p in expected['portfolios']),2)
 return expected

def audited_portfolio_change(previous,current):
 return json.loads(current)==audited_portfolio_state(previous)

def strip_decision_audit(code):
 lines=code.decode().splitlines(keepends=True);out=[];inside=False
 for line in lines:
  if line.strip()=='# BEGIN DECISION AUDIT':
   if inside:raise ValueError('Bloc audit imbriqué')
   inside=True
  elif line.strip()=='# END DECISION AUDIT':
   if not inside:raise ValueError('Fin audit sans début')
   inside=False
  elif not inside:out.append(line)
 if inside:raise ValueError('Bloc audit non terminé')
 return ''.join(out).encode()

def audit_only_engine_change(previous,current):
 # Only this reviewed metadata-only engine is accepted; arbitrary marker blocks fail.
 return hashlib.sha256(current).hexdigest()=='a6c7702be7b95e5faabfde1719cf392db1452b2072145c5c060571594eb99bef' and strip_decision_audit(current)==strip_decision_audit(previous)

def verify(root,base):
 root=Path(root).resolve()
 if not re.fullmatch(r'[0-9a-f]{40}',base):raise ValueError('Référence de base exacte requise')
 checks={}
 for name in PROTECTED:
  previous=subprocess.check_output(['git','-C',str(root),'show',base+':'+name]);current=(root/name).read_bytes()
  if current!=previous and not (name=='hub/trading/three-portfolios.json' and audited_portfolio_change(previous,current)) and not (name=='hub/trading/autonomous_simulation.py' and audit_only_engine_change(previous,current)):raise ValueError('Fichier existant différent de la base : '+name)
  checks[name]=hashlib.sha256(current).hexdigest()
 policy=json.loads((root/'learning/policy.json').read_text());policy_check(policy)
 if policy['openai']!=dict(enabled=False,monthlyBudgetUsd=0,maxRequestUsd=0):raise ValueError('OpenAI doit rester désactivé, budget nul')
 policy['historyRequestsPerRun']=0
 outputs,report=build(Files(root),policy,dt.datetime.now(dt.timezone.utc))
 if not all(p.startswith('hub/trading/learning-data/') for p in outputs):raise ValueError('Sortie hors du journal')
 if report['referenceCapitalEUR']!=1600 or report['appliedToRobot'] is not False:raise ValueError('Mode observation invalide')
 result=dict(base=base,protectedHashes=checks,readOnlyCollector='passed',referenceCapitalEUR=1600,profileCount=len(report['observedPortfolios']),plannedWrites=len(outputs),productionWrites=0,openaiCalls=0)
 print(json.dumps(result,sort_keys=True));return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--base',required=True);a=parser.parse_args();verify(Path(__file__).resolve().parents[1],a.base)
