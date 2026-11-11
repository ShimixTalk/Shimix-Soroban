"""Local snapshot and restore drill. No upload, deletion, service creation or production restore."""
import argparse,datetime as dt,hashlib,json,re,shutil,subprocess,tempfile
from pathlib import Path,PurePosixPath
CORE=['hub/trading/robot-state.json','hub/trading/three-portfolios.json','hub/trading/scanner-state.json','hub/trading/meme-history.json']
PREFIX='hub/trading/learning-data/'
def allowed(path):
 if not isinstance(path,str):return False
 p=PurePosixPath(path)
 return True and not p.is_absolute() and '..' not in p.parts and str(p)==path and (path in CORE or path.startswith(PREFIX))
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(65536),b''):h.update(chunk)
 return h.hexdigest()
def create(root,destination,source_ref=None,source_tree=None):
 root=Path(root).resolve();destination=Path(destination)
 if destination.is_symlink():raise ValueError('Lien symbolique refusé')
 destination=destination.resolve()
 if destination==root or root in destination.parents:raise ValueError('Copie hors du dépôt obligatoire')
 if destination.exists():raise ValueError('Destination existante : aucun remplacement autorisé')
 if any(value is not None and not re.fullmatch(r'[0-9a-f]{40}',value) for value in [source_ref,source_tree]):raise ValueError('Référence Git invalide')
 sources=[root/p for p in CORE]
 directory=root/PREFIX
 if directory.exists():sources.extend(p for p in directory.rglob('*') if p.is_file() or p.is_symlink())
 if any(not p.is_file() or any(parent.is_symlink() for parent in [p,*p.parents] if parent!=root.parent) for p in sources):raise ValueError('Source manquante ou lien symbolique refusé')
 destination.mkdir(parents=True);files=[]
 for source in sorted(sources):
  relative=source.relative_to(root).as_posix()
  if not allowed(relative):raise ValueError('Fichier non autorisé')
  target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
  files.append(dict(path=relative,sha256=sha(target),size=target.stat().st_size))
 manifest=dict(format='shimix-simulation-snapshot',version=1,createdAt=dt.datetime.now(dt.timezone.utc).isoformat(),sourceRef=source_ref,sourceTree=source_tree,simulationOnly=True,files=files)
 (destination/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
 return sha(destination/'manifest.json')
def verify(archive,expected_manifest=None):
 archive=Path(archive).absolute();manifest_path=archive/'manifest.json'
 if archive.is_symlink() or manifest_path.is_symlink():raise ValueError('Lien symbolique refusé')
 if expected_manifest and sha(manifest_path)!=expected_manifest:raise ValueError('Empreinte du manifeste incorrecte')
 m=json.loads(manifest_path.read_text())
 if m.get('format')!='shimix-simulation-snapshot' or m.get('version')!=1 or m.get('simulationOnly') is not True:raise ValueError('Format incorrect')
 names=[]
 for entry in m['files']:
  name=entry['path']
  if not allowed(name) or name in names:raise ValueError('Chemin non autorisé ou répété')
  names.append(name);p=archive/name
  if any(parent.is_symlink() for parent in [p,*p.parents] if parent!=archive.parent):raise ValueError('Lien symbolique refusé')
  if p.stat().st_size!=entry['size'] or sha(p)!=entry['sha256']:raise ValueError('Fichier absent ou corrompu : '+name)
 actual={p.relative_to(archive).as_posix() for p in archive.rglob('*') if p.is_file()}
 if actual!=set(names)|{'manifest.json'} or not set(CORE)<=set(names):raise ValueError('Contenu de sauvegarde incomplet ou inattendu')
 return m

def restore(archive,destination,expected_manifest=None):
 manifest=verify(archive,expected_manifest);destination=Path(destination).absolute()
 if destination.exists():raise ValueError('Restauration seulement vers un nouveau dossier vide')
 destination.mkdir(parents=True)
 for entry in manifest['files']:
  target=destination/entry['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(Path(archive)/entry['path'],target)
  if sha(target)!=entry['sha256']:raise ValueError('Restauration différente de la sauvegarde')
 return manifest

def drill(root,work_dir):
 root=Path(root).resolve();folder=Path(tempfile.mkdtemp(prefix='shimix-restore-drill-',dir=work_dir));source_ref=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
 source_tree=subprocess.check_output(['git','-C',str(root),'write-tree'],text=True).strip()
 checksum=create(root,folder/'snapshot',source_ref,source_tree);m=restore(folder/'snapshot',folder/'restored',checksum)
 result=dict(status='verified',files=len(m['files']),bytes=sum(x['size'] for x in m['files']),manifestSha256=checksum,sourceRef=source_ref,sourceTree=source_tree,productionModified=False,cloudUpload=False)
 print(json.dumps(result,sort_keys=True));return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));parser.add_argument('--work-dir',required=True);a=parser.parse_args();drill(a.root,a.work_dir)
