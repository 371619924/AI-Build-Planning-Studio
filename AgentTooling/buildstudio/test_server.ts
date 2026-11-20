import test from 'node:test';import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';import {mkdtempSync,rmSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';import {join,dirname} from 'node:path';import {fileURLToPath} from 'node:url';
import {createApp} from './server.ts';
import {request as sendHttpRequest} from 'node:http';
const root=dirname(fileURLToPath(import.meta.url));
test('actual HTTP and persistent workflow',async()=>{
 const temporary=mkdtempSync(join(tmpdir(),'buildstudio-'));const transcript:any[]=[];const checks:string[]=[];
 const python=process.env.CODEX_PRIMARY_RUNTIME_PYTHON||process.env.BUILD_PYTHON||'python3';
 const fixture=spawn(python,['-m','buildstudio.model_fixture','--port','0'],{cwd:join(root,'..'),stdio:['ignore','pipe','pipe']});
 const endpoint=await new Promise<string>((resolve,reject)=>{let raw='';fixture.stdout.on('data',chunk=>{raw+=chunk;if(raw.includes('\n')){try{resolve('http://127.0.0.1:'+JSON.parse(raw.split('\n')[0]).port+'/chat/completions');}catch(e){reject(e);}}});fixture.on('error',reject);fixture.on('exit',code=>{if(code)reject(Error('Fixture failed'));});});
 const db=join(temporary,'studio.db');let app=createApp({dbPath:db,endpoint,python});
 const listen=()=>new Promise<void>(resolve=>app.server.listen(0,'127.0.0.1',resolve));await listen();
 async function request(path:string,method='GET',body?:unknown,key?:string,auth=true){
  const port=(app.server.address() as any).port;
  const res=await fetch('http://127.0.0.1:'+port+path,{method,headers:{...(auth?{Authorization:'Bearer demo-local'}:{}),...(key?{'Idempotency-Key':key}:{}),'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
  const value=res.headers.get('content-type')==='application/json'?await res.json():await res.text();transcript.push({path,method,status:res.status,body,response:value});return {status:res.status,body:value as any};
 }
 const check=(name:string,condition:unknown)=>{assert.ok(condition,name);checks.push(name);};
 const close=async()=>{app.server.closeAllConnections();await new Promise<void>(resolve=>app.server.close(()=>resolve()));app.close();};
 try{
  check('native UI served',(await request('/', 'GET',undefined,undefined,false)).status===200);
  check('auth required',(await request('/api/catalog','GET',undefined,undefined,false)).status===401);
  check('fixture catalog served',(await request('/api/catalog')).body.modules.length===5);
  check('missing key rejected',(await request('/api/plans','POST',{prompt:'plant'})).status===400);
  const [a,b]=await Promise.all([request('/api/plans','POST',{prompt:'Plant moisture monitor'},'same-key'),request('/api/plans','POST',{prompt:'Plant moisture monitor'},'same-key')]);
  check('concurrent retry same identity',a.body.id===b.body.id&&[a.status,b.status].sort().join(',')==='200,201');const id=a.body.id;
  check('structured tool plan',a.body.result.status==='supported'&&a.body.result.transcript.length===3);
  check('key payload conflict',(await request('/api/plans','POST',{prompt:'climate'},'same-key')).status===409);
  const plan=structuredClone(a.body.result.build.plan);plan.enclosure.width_mm+=10;
  const edits=await Promise.all([request('/api/plans/'+id,'PATCH',{expected_version:1,plan}),request('/api/plans/'+id,'PATCH',{expected_version:1,plan})]);
  check('one concurrent edit succeeds',edits.map(x=>x.status).sort().join(',')==='200,409');
  check('revision persisted',(await request('/api/plans/'+id)).body.version===2);
  check('audit gap free',(await request('/api/plans/'+id+'/history')).body.map((x:any)=>x.version).join(',')==='1,2');
  const invalid=structuredClone(plan);invalid.wires=[];
  check('invalid wiring blocked',(await request('/api/plans/'+id,'PATCH',{expected_version:2,plan:invalid})).status===422);
  check('rejected edit no history change',(await request('/api/plans/'+id+'/history')).body.length===2);
  const source=await request('/api/plans/'+id+'/enclosure.scad');check('geometry source export',source.status===200&&source.body.includes('difference()')&&source.body.includes('validation'));
  const unsupported=await request('/api/plans','POST',{prompt:'Battery motor robot'},'unsupported-key');check('unsupported explicit',unsupported.body.result.status==='unsupported');
  check('unsupported no geometry',(await request('/api/plans/'+unsupported.body.id+'/enclosure.scad')).status===409);
  check('provider error',(await request('/api/plans','POST',{prompt:'timeout plant'},'provider-error')).status===502);
  check('tool loop bound',(await request('/api/plans','POST',{prompt:'loop plant'},'loop-error')).status===502);
  await close();app=createApp({dbPath:db,endpoint,python});await listen();
  check('database survives restart',(await request('/api/plans/'+id)).body.version===2);
  check('receipt survives restart',(await request('/api/plans','POST',{prompt:'Plant moisture monitor'},'same-key')).body.id===id);
  const prompt='Plant moisture monitor 🌱';
  const payload=Buffer.from(JSON.stringify({prompt}));
  const split=payload.indexOf(Buffer.from('🌱'))+1;
  const splitResponse=await new Promise<{status:number|undefined,body:{prompt:string}}>((resolve,reject)=>{
   const sent=sendHttpRequest({hostname:'127.0.0.1',port:(app.server.address() as any).port,path:'/api/plans',method:'POST',
    headers:{'Authorization':'Bearer demo-local','Idempotency-Key':'split-utf8-test','Content-Type':'application/json'}},response=>{
    let json='';response.setEncoding('utf8');
    response.on('data',chunk=>{json+=chunk;});
    response.on('error',reject);
    response.on('end',()=>{
     try{resolve({status:response.statusCode,body:JSON.parse(json)});}catch(error){reject(error);}
    });
   });
   sent.on('error',reject);
   sent.write(payload.subarray(0,split));
   setTimeout(()=>sent.end(payload.subarray(split)),20);
  });
  transcript.push({path:'/api/plans',method:'POST',status:splitResponse.status,body:{prompt},response:splitResponse.body});
  check('split UTF-8 prompt preserved',splitResponse.status===201&&splitResponse.body.prompt===prompt);
  writeFileSync(join(root,'evidence','HTTP_Results.json'),JSON.stringify({passed:true,checks:checks.length,http_requests:transcript.length,results:checks,browser_executed:false,external_llm_calls:0},null,2));
  writeFileSync(join(root,'evidence','HTTP_Transcripts.json'),JSON.stringify(transcript,null,2));
 }finally{await close();fixture.kill();await new Promise<void>(resolve=>fixture.once('exit',()=>resolve()));rmSync(temporary,{recursive:true,force:true});}
});
