"""Task-level oracles, retrieval baseline and injected failure evaluation.

Every policy used here is scripted. No live LLM or industrial deployment metric.
"""
import hashlib,json,platform,threading,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from importlib.metadata import version
from agent_lab import BM25,ScriptedPolicy,CompatibleHTTPPolicy,run_episode
ROOT=Path(__file__).parent
OUT=ROOT/'artifacts';OUT.mkdir(exist_ok=True)
corpus=json.loads((ROOT/'data/corpus.json').read_text())
tasks=json.loads((ROOT/'data/tasks.json').read_text())
database=ROOT/'data/experiments.sqlite'
traces=[];failures=[]
start=time.perf_counter()
for task in tasks:
 state=run_episode(task,corpus,database)
 passed=(state['status']=='complete' and abs(state['report']['improvement_pct']-task['expected_improvement_pct'])<1e-8
         and task['expected_source'] in state['report']['citations'] and len(state['observations'])==4
         and state['checkpoint_resumes']==4)
 traces.append({'id':task['id'],'passed':passed,'state':state})
 if not passed:failures.append(task['id'])
fault_results=[]
for fault in ['unknown_tool','missing_argument','missing_run','invalid_citation','wrong_metric','malformed_report','budget_loop','transient_retry']:
 state=run_episode(tasks[0],corpus,database,ScriptedPolicy(fault),transient_failures=1 if fault=='transient_retry' else 0)
 expected='complete' if fault=='transient_retry' else 'failed'
 passed=state['status']==expected
 if fault=='transient_retry':
  passed=passed and any(o['attempts']==2 for o in state['observations'])
 fault_results.append({'fault':fault,'passed':passed,'expected_status':expected,'state':state})
 if not passed:failures.append(fault)

# A real loopback HTTP exchange exercises provider-format parsing and tool histories.
requests_seen=[]
class FixtureHandler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  requests_seen.append(request)
  tool_messages=[m for m in request['messages'] if m['role']=='tool']
  observations=[]
  for index,message in enumerate(tool_messages):
   call=[m for m in request['messages'] if m['role']=='assistant'][index]['tool_calls'][0]['function']
   observations.append({'name':call['name'],'arguments':json.loads(call['arguments']),'result':json.loads(message['content'])})
  state={'task':tasks[0],'observations':observations}
  if observations and observations[-1]['name']=='compare_runs':state['comparison']=observations[-1]['result']
  action=ScriptedPolicy().next(state)
  if action['kind']=='tool':
   message={'role':'assistant','content':None,'tool_calls':[{'id':'fixture','type':'function','function':{'name':action['name'],'arguments':json.dumps(action['arguments'])}}]}
  else:message={'role':'assistant','content':json.dumps(action['report'])}
  payload=json.dumps({'choices':[{'message':message}]}).encode()
  self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(payload)
server=ThreadingHTTPServer(('127.0.0.1',0),FixtureHandler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
 adapter_state=run_episode(tasks[0],corpus,database,CompatibleHTTPPolicy(f'http://127.0.0.1:{server.server_port}/v1/chat/completions','local-scripted-fixture'))
 adapter_pass=(adapter_state['status']=='complete' and len(requests_seen)==5
               and len([m for m in requests_seen[-1]['messages'] if m['role']=='tool'])==4)
finally:
 server.shutdown();server.server_close();thread.join()
if not adapter_pass:failures.append('http_adapter_contract')

index=BM25(corpus)
retrieval=[]
for query in json.loads((ROOT/'data/retrieval_queries.json').read_text()):
 row=dict(query)
 for method in ['overlap','bm25']:
  docs=index.search(query['query'],3,method)
  rank=next((i+1 for i,d in enumerate(docs) if d['id']==query['relevant_id']),None)
  row[method]={'rank':rank,'top3':[d['id'] for d in docs]}
 retrieval.append(row)
ablation={}
for method in ['overlap','bm25']:
 ranks=[r[method]['rank'] for r in retrieval]
 ablation[method]={'recall_at_3':sum(r is not None for r in ranks)/len(ranks),
                   'mrr_at_3':sum(1/r if r else 0 for r in ranks)/len(ranks)}
summary={'provenance':'Agent tooling prototype; all evaluation policies scripted; all domain data synthetic.',
 'python':platform.python_version(),'langgraph':version('langgraph'),'pydantic':version('pydantic'),
 'nominal_episodes':len(traces),'nominal_passed':sum(t['passed'] for t in traces),
 'checkpoint_resumes':sum(t['state']['checkpoint_resumes'] for t in traces),
 'fault_scenarios':len(fault_results),'fault_expected_outcomes':sum(t['passed'] for t in fault_results),
 'http_adapter_fixture_passed':adapter_pass,'external_llm_calls':0,
 'corpus_documents':len(corpus),'synthetic_observation_rows':1536,'retrieval_queries':len(retrieval),
 'retrieval_ablation':ablation,'wall_seconds':time.perf_counter()-start,
 'limitations':['No live LLM reasoning benchmark','No reinforcement learning or model post-training',
                'In-memory checkpoint resume only; not restart durability','Small hand-authored synthetic retrieval set; not a held-out benchmark',
                'Citation membership is not entailment verification','No real Bosch data, equipment, customers or production deployment'],
 'failures':failures}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
(OUT/'nominal_traces.json').write_text(json.dumps(traces,indent=2))
(OUT/'fault_traces.json').write_text(json.dumps(fault_results,indent=2))
(OUT/'retrieval_ablation.json').write_text(json.dumps(retrieval,indent=2))
(OUT/'http_adapter_trace.json').write_text(json.dumps({'state':adapter_state,'requests':requests_seen},indent=2))
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
          for folder in ['data'] for p in (ROOT/folder).glob('*') if p.is_file()}
(OUT/'input_hashes.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(summary,indent=2))
assert not failures,failures
