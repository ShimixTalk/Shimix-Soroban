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
 return hashlib.sha256(previous).hexdigest()=='c459629e19a1554ea96b0bde65e73f59d18f910d0b1329f6e5d9ae7d26460968' and hashlib.sha256(current).hexdigest()=='329e01f41af93967e49be0629f4f81f376f42a42126ad8a3cd3f8a1e90f6f044'

def approved_owner_policy_change(previous,current):
 # Owner confirmation 2026-11-15; exact engine only, no journal or risk reset.
 return hashlib.sha256(previous).hexdigest()=='329e01f41af93967e49be0629f4f81f376f42a42126ad8a3cd3f8a1e90f6f044' and hashlib.sha256(current).hexdigest()=='12f2d97e8b6a390544f447ea27b799335b73beb6861544615980816ebd6912ca'

def approved_history_priority_change(previous,current):
 # Explicit history-budget correction, 2026-11-16; exact engine pair only.
 return hashlib.sha256(previous).hexdigest()=='12f2d97e8b6a390544f447ea27b799335b73beb6861544615980816ebd6912ca' and hashlib.sha256(current).hexdigest()=='983b27d7f29c079d554ecc61324c063e348fc9eeb82c8caf742e2609762bacae'

def verify(root,base):
 root=Path(root).resolve()
 if hashlib.sha256((root/'hub/trading/entry_review.py').read_bytes()).hexdigest()!='82b6f4d0c6256f420108a4d5aab5c28f240be03439f9586a162b9e5587c35834':raise ValueError('Module d’analyse non conforme à la révision testée')
 if not re.fullmatch(r'[0-9a-f]{40}',base):raise ValueError('Référence de base exacte requise')
 checks={}
 for name in PROTECTED:
  previous=subprocess.check_output(['git','-C',str(root),'show',base+':'+name]);current=(root/name).read_bytes()
  if current!=previous and not (name=='hub/trading/autonomous_simulation.py' and (approved_protection_change(previous,current) or approved_owner_policy_change(previous,current) or approved_history_priority_change(previous,current))):raise ValueError('Fichier existant différent de la base : '+name)
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
