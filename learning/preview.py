"""Offline preview against copied repository files; never writes the robot or calls an AI API."""
import argparse,datetime as dt,json
from pathlib import Path
from collect import build,PREFIX
from engine import digest
from ai_review import prepare
from collect import encoded
class Files:
 def __init__(self,root):self.root=Path(root)
 def file(self,path,ref=None,optional=False):
  p=self.root/path
  if optional and not p.exists():return None
  return p.read_bytes()
 def json(self,path,optional=False):
  raw=self.file(path,optional=optional);return json.loads(raw) if raw is not None else None
 def commits(self,cursor,path='hub/trading/robot-state.json'):return [] if cursor else ['preview-'+digest(self.json(path))]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
 root=Path(__file__).resolve().parents[1];policy=json.loads((root/'learning/policy.json').read_text());policy['historyRequestsPerRun']=0
 files,report=build(Files(root),policy,dt.datetime.now(dt.timezone.utc))
 report['preview']=True;report['limitations'].insert(0,'Prévisualisation locale ; collecte planifiée pas encore activée.')
 files[PREFIX+'report.json']=encoded(report);files[PREFIX+'openai-review-input.json']=encoded(prepare(report,policy))
 out=Path(args.output).resolve()
 if out==root or root in out.parents:raise ValueError('Utiliser un dossier de travail hors du dépôt pour la prévisualisation')
 for path,data in files.items():
  p=out/Path(path).relative_to(PREFIX);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 print('Prévisualisation hors ligne écrite ; capital et portefeuilles inchangés ; aucun appel OpenAI.')
if __name__=='__main__':main()
