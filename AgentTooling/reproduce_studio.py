"""Clean-source recheck with stable software results, same installed runtime."""
import json,shutil,subprocess,sys,tempfile
from pathlib import Path
from reproduce_actionbench import stable
ROOT=Path(__file__).resolve().parent

def read(base,name):return json.loads((base/name).read_text())
def main():
 names=['buildstudio/evidence/Verification.json','buildstudio/evidence/Evaluation.json','buildstudio/evidence/HTTP_Results.json']
 before={n:read(ROOT,n) for n in names};old=stable(read(ROOT,'actionbench/artifacts/evaluation.json'))
 with tempfile.TemporaryDirectory() as td:
  dest=Path(td)/'AgentTooling';shutil.copytree(ROOT,dest,ignore=shutil.ignore_patterns('evidence','artifacts','__pycache__','*.db','*.sqlite','*.db-wal','*.db-shm','node_modules'))
  result=subprocess.run([sys.executable,'verify_studio.py'],cwd=dest,capture_output=True,text=True,timeout=240)
  assert result.returncode==0,result.stdout+result.stderr
  after={n:read(dest,n) for n in names};assert before==after
  assert old==stable(read(dest,'actionbench/artifacts/evaluation.json'))
 record=dict(passed=True,clean_source_copy=True,stable_new_and_retained_results_match=True,same_installed_runtime=True,dependency_installation_tested=False,browser_executed=False,react_renderer_executed=False,cad_renderer_executed=False,external_llm_calls=0)
 (ROOT/'buildstudio/evidence/Reproduction.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
if __name__=='__main__':main()
