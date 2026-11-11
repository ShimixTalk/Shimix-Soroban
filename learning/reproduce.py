"""Recompute frozen experiments from archived EUR observations, offline and without state writes."""
import json
from pathlib import Path
from engine import policy_check,study
from collect import PREFIX,RESEARCH_HASH
root=Path(__file__).resolve().parents[1];policy=policy_check(json.loads((root/'learning/policy.json').read_text()))
experiment=json.loads((root/PREFIX/'experiments'/(policy['experimentId']+'.json')).read_text())
if experiment['researchHash']!=RESEARCH_HASH:raise ValueError('Revenir au code de l’expérience gelée avant reproduction.')
for profile,frozen in experiment['studies'].items():
 histories={p.stem:[row for row in json.loads(p.read_text())['prices'] if row['date']<=frozen['cutoff']] for p in (root/PREFIX/'history').glob('*.json')}
 result=study(histories,profile,policy['minimumDailyPoints'])
 if result!=frozen:raise ValueError('Résultat non reproductible pour '+profile)
 print(profile,'reproduction exacte : OK ; résultat test candidat',result['folds']['test']['candidate']['netReturnPercent'],'%, référence',result['folds']['test']['baseline']['netReturnPercent'],'%')
