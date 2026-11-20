"""Twelve authored protocol scenarios; software evaluation, never model quality."""
import json,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from .model_fixture import Handler
from .planner import run

def main():
 scenarios=[('plant','Plant moisture monitor','supported'),('climate','Climate monitor with display','supported'),('light','Indicator light','supported'),
  ('repair','Repair plant plan','supported'),('motor','Motor controller','unsupported'),('battery','Battery plant monitor','unsupported'),('unknown','Camera enclosure','unsupported'),
  ('invented','Invented plant part','error'),('loop','Loop plant planner','error'),('provider','Timeout plant planner','error'),('premature','Premature plant finish','error'),('voltage','Bad-voltage plant sensor','error')]
 Handler.requests=[];server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();results=[]
 try:
  for name,prompt,expected in scenarios:
   start=len(Handler.requests)
   try:result=run(prompt,f'http://127.0.0.1:{server.server_port}/chat/completions');actual=result['status']
   except Exception as e:result=dict(error=str(e));actual='error'
   passed=actual==expected
   if name=='repair':passed=passed and any('error' in obs['response'] for obs in result.get('transcript',[])) and len(result.get('transcript',[]))==4
   results.append(dict(name=name,prompt=prompt,expected=expected,actual=actual,passed=passed,provider_requests=len(Handler.requests)-start,result=result))
 finally:server.shutdown();server.server_close();thread.join()
 record=dict(passed=all(r['passed'] for r in results),scenarios=len(results),supported=sum(r['actual']=='supported' for r in results),unsupported=sum(r['actual']=='unsupported' for r in results),errors=sum(r['actual']=='error' for r in results),provider_http_requests=len(Handler.requests),external_llm_calls=0,model_quality_evaluated=False,results=results)
 out=Path(__file__).parent/'evidence';out.mkdir(exist_ok=True);(out/'Evaluation.json').write_text(json.dumps(record,indent=2));(out/'Provider_Transcripts.json').write_text(json.dumps(Handler.requests,indent=2))
 assert record['passed'],record
 print(json.dumps({k:v for k,v in record.items() if k!='results'}))
if __name__=='__main__':main()
