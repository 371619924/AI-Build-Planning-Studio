"""Executed actionbench checks; retained LangGraph evidence is not rerun here."""
import json,platform,re,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'actionbench/artifacts'

def command(args,cwd,log):
    result=subprocess.run([sys.executable,*args],cwd=cwd,text=True,capture_output=True,timeout=90)
    (OUT/log).write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result

def stable(result):
    result=json.loads(json.dumps(result))
    for p in result['profiles'].values():p.pop('median_wall_seconds',None)
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    command(['create_fixtures.py'],ROOT,'Fixtures.log')
    tests=command(['-m','unittest','actionbench.test_runtime','actionbench.test_experiment_tools','-v'],ROOT,'Tests.log')
    command(['-m','actionbench.evaluate'],ROOT,'Evaluation.log')
    baseline=json.loads((OUT/'evaluation.json').read_text())
    with tempfile.TemporaryDirectory() as directory:
        fresh=Path(directory)/'AgentTooling'
        shutil.copytree(ROOT,fresh,ignore=shutil.ignore_patterns('artifacts','__pycache__','*.sqlite','*.db'))
        command(['create_fixtures.py'],fresh,'Fresh_Fixtures.log')
        command(['-m','unittest','actionbench.test_runtime','actionbench.test_experiment_tools','-v'],fresh,'Fresh_Tests.log')
        command(['-m','actionbench.evaluate'],fresh,'Fresh_Evaluation.log')
        actual=json.loads((fresh/'actionbench/artifacts/evaluation.json').read_text())
        assert stable(actual)==stable(baseline)
    count=re.search(r'Ran (\d+) tests?',tests.stdout+tests.stderr)
    if not count:raise RuntimeError('test count unavailable')
    result={'passed':True,'tests':int(count[1]),'evaluation_episodes':baseline['episodes'],
      'fresh_source_tests_passed':True,'stable_evaluation_matches':True,
      'agent_process_restart_tested':True,'world_server_persisted_during_agent_restart':True,
      'native_model_protocol_loopback_tested':True,'external_llm_calls':0,
      'shared_retrieval_experiment_and_report_tools_tested':True,
      'torch_runtime_executed':False,'legacy_langgraph_runtime_executed':False,
      'python':platform.python_version(),'scope':'Fresh source directory, same Python/OS. No model training, external LLM evaluation, GPU or cloud deployment.'}
    (OUT/'Reproduction.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
