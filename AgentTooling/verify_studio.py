"""Run only executable project layers and retain their raw output."""
import json,os,platform,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
 node=shutil.which('node')
 if node is None:
  print('Node.js was not found on PATH.',file=sys.stderr)
  return 1
 env=os.environ.copy()
 env.setdefault('BUILD_PYTHON',sys.executable)
 out=ROOT/'buildstudio/evidence';out.mkdir(exist_ok=True);runs=[]
 stages=[('Create_Retained_Fixtures',[sys.executable,'create_fixtures.py']),('Domain',[sys.executable,'-m','unittest','buildstudio.test_domain','-v']),('Node',[node,'--test','buildstudio/test_server.ts','buildstudio/test_ui.mjs']),('Evaluation',[sys.executable,'-m','buildstudio.evaluate']),('Native_UI_Syntax',[node,'--check','buildstudio/web/app.mjs']),('React_Source_Syntax',[node,'--check','buildstudio/web/ReactStudio.mjs']),('Retained_Agent_Tests',[sys.executable,'-m','unittest','actionbench.test_runtime','actionbench.test_experiment_tools','-v']),('Retained_Evaluation',[sys.executable,'-m','actionbench.evaluate'])]
 for name,command in stages:
  result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=120);(out/(name+'_Log.txt')).write_text(result.stdout+result.stderr);runs.append(dict(name=name,returncode=result.returncode))
  if result.returncode:break
 passed=len(runs)==len(stages) and all(r['returncode']==0 for r in runs)
 record=dict(passed=passed,stages=runs,python=platform.python_version(),node=subprocess.check_output([node,'--version'],text=True).strip(),typescript_native_execution=True,typescript_tsc_typecheck=False,react_renderer_executed=False,nextjs_executed=False,browser_executed=False,cad_renderer_executed=False,physical_hardware_tested=False,external_llm_calls=0,cloud_deployed=False)
 (out/'Verification.json').write_text(json.dumps(record,indent=2));print(json.dumps(record));return 0 if passed else 1
if __name__=='__main__':sys.exit(main())
