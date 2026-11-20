"""Deterministic chat-completions fixture. Not a language model."""
import argparse,json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from buildstudio.domain import recipe

class Handler(BaseHTTPRequestHandler):
    requests=[]
    def log_message(self,*args):pass
    def do_POST(self):
        try:
            size=int(self.headers.get('Content-Length',0))
            if not 0<size<=100000:raise ValueError('body size')
            body=json.loads(self.rfile.read(size));self.requests.append(body);messages=body['messages'];goal=json.loads(messages[1]['content'])['goal'].lower()
            observations=[json.loads(m['content']) for m in messages if m['role']=='tool'];n=len(observations)
            if 'timeout' in goal:raise ValueError('fixture provider failure')
            if 'loop' in goal:name,args='search_components',dict(query='')
            elif 'invented' in goal:
                name,args=('search_components',dict(query='')) if n==0 else ('validate_build',dict(plan=dict(recipe(['demo-led']),modules=['invented-part'])))
            elif 'motor' in goal or 'battery' in goal or not any(w in goal for w in ['plant','climate','light']):name,args='report_unsupported',dict(reason='This requirement is outside the authored fixture component library.')
            elif n==0:name,args='search_components',dict(query='')
            elif 'premature' in goal:name,args='finish_build',dict(validation_hash='fabricated')
            elif 'repair' in goal and n==2:name,args='validate_build',dict(plan=recipe(['demo-moisture']))
            elif 'bad-voltage' in goal and n>0:name,args='validate_build',dict(plan=recipe(['demo-legacy']))
            elif n==1:
                modules=['demo-moisture'] if 'plant' in goal else ['demo-climate','demo-display'] if 'climate' in goal else ['demo-led']
                plan=recipe(modules)
                if 'repair' in goal:plan['wires']=plan['wires'][:-1]
                name,args='validate_build',dict(plan=plan)
            else:name,args='finish_build',dict(validation_hash=observations[-1]['validation_hash'])
            result=dict(choices=[dict(message=dict(role='assistant',content=None,tool_calls=[dict(id=str(n),type='function',function=dict(name=name,arguments=json.dumps(args)))]))])
            raw=json.dumps(result).encode();status=200
        except Exception as e:raw=json.dumps(dict(error=str(e))).encode();status=503
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8091);a=p.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler);print(json.dumps(dict(port=server.server_port)),flush=True);server.serve_forever()
