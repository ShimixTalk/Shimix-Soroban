"""Verify an isolated integration tree keeps the base's data and runtime engines byte-for-byte."""
import argparse,datetime as dt,hashlib,json,re,subprocess
from pathlib import Path
from backup import CORE
from collect import build
from preview import Files
from engine import policy_check
PROTECTED=CORE+['hub/trading/autonomous_simulation.py','hub/trading/meme_history.py','hub/trading/security.js','hub/trading/manifest.webmanifest','hub/trading/icon.svg']
def approved_protection_change(previous,current):
 # Only the explicit reviewed transition is allowed; all data remain protected.
 return hashlib.sha256(previous).hexdigest()=='e3479e3fa7b7718276b04d50cb3694120627631df8fb03ef7894a9daab21bd0a' and hashlib.sha256(current).hexdigest()=='c459629e19a1554ea96b0bde65e73f59d18f910d0b1329f6e5d9ae7d26460968'

def verify(root,base):
 root=Path(root).resolve()
 if not re.fullmatch(r'[0-9a-f]{40}',base):raise ValueError('Référence de base exacte requise')
 checks={}
 for name in PROTECTED:
  previous=subprocess.check_output(['git','-C',str(root),'show',base+':'+name]);current=(root/name).read_bytes()
  if current!=previous and not (name=='hub/trading/autonomous_simulation.py' and approved_protection_change(previous,current)):raise ValueError('Fichier existant différent de la base : '+name)
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
