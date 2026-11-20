/** Local TypeScript/Node host. Node strips types; this does not run tsc. */
import http from 'node:http';
import type {IncomingMessage,ServerResponse} from 'node:http';
import {DatabaseSync} from 'node:sqlite';
import {createHash,randomUUID} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,join,resolve} from 'node:path';
import {spawn} from 'node:child_process';

type PlannerResult={status:'supported'|'unsupported',build?:Record<string,unknown>,reason?:string,enclosure_scad?:string,transcript?:unknown[]};
type Options={dbPath:string,endpoint:string,python:string};
class Problem extends Error {status:number;constructor(status:number,message:string){super(message);this.status=status;}}
const ROOT=dirname(fileURLToPath(import.meta.url));
const digest=(s:string)=>createHash('sha256').update(s).digest('hex');
const isObject=(x:unknown):x is Record<string,unknown>=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const fields=(x:unknown,keys:string[]):x is Record<string,unknown>=>isObject(x)&&JSON.stringify(Object.keys(x).sort())===JSON.stringify([...keys].sort());
const validId=(id:string)=>/^[0-9a-f-]{36}$/.test(id);

export function createApp(options:Options){
 const database=new DatabaseSync(options.dbPath);
 database.exec(`PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL;
 CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY,prompt TEXT NOT NULL,version INTEGER NOT NULL,result TEXT NOT NULL) STRICT;
 CREATE TABLE IF NOT EXISTS history(plan_id TEXT NOT NULL REFERENCES plans(id),version INTEGER NOT NULL,result TEXT NOT NULL,PRIMARY KEY(plan_id,version)) STRICT;
 CREATE TABLE IF NOT EXISTS receipts(key TEXT PRIMARY KEY,payload_hash TEXT NOT NULL,plan_id TEXT NOT NULL REFERENCES plans(id)) STRICT;`);
 const pending=new Map<string,{hash:string,promise:Promise<unknown>}>();
 const value=(row:any)=>({id:row.id,prompt:row.prompt,version:row.version,result:JSON.parse(row.result)});
 const get=(id:string)=>{const row=database.prepare('SELECT * FROM plans WHERE id=?').get(id);if(!row)throw new Problem(404,'Plan not found');return value(row);};
 const transaction=<T>(fn:()=>T):T=>{database.exec('BEGIN IMMEDIATE');try{const result=fn();database.exec('COMMIT');return result;}catch(e){database.exec('ROLLBACK');throw e;}};
 function planner(input:Record<string,unknown>):Promise<PlannerResult>{
  return new Promise((accept,reject)=>{
   const child=spawn(options.python,['-m','buildstudio.planner',options.endpoint],{cwd:join(ROOT,'..'),stdio:['pipe','pipe','pipe']});
   let output='',errors='',settled=false;
   const timer=setTimeout(()=>{child.kill();done(new Problem(502,'Planning timed out; retry the request.'));},12000);
   function done(error?:Error,result?:PlannerResult){if(settled)return;settled=true;clearTimeout(timer);error?reject(error):accept(result!);}
   child.stdout.on('data',chunk=>{output+=chunk;if(output.length>200000){child.kill();done(new Problem(502,'Planner response too large'));}});
   child.stderr.on('data',chunk=>{if(errors.length<5000)errors+=chunk;});
   child.on('error',()=>done(new Problem(502,'Planner process could not start')));
   child.on('close',code=>{try{const result=JSON.parse(output);if(code!==0||result.error)throw new Problem(input.mode==='validate'?422:502,result.error||'Planning failed');done(undefined,result);}catch(e){done(e instanceof Problem?e:new Problem(502,'Planner returned invalid JSON'));}});
   child.stdin.on('error',()=>{});child.stdin.end(JSON.stringify(input));
  });
 }
 async function body(req:IncomingMessage):Promise<unknown>{
  const chunks:Buffer[]=[];
  let size=0;
  for await(const chunk of req){
   size+=chunk.length;
   if(size>32768)throw new Problem(413,'Request too large');
   chunks.push(chunk);
  }
  try{return JSON.parse(Buffer.concat(chunks,size).toString('utf8'));}catch{throw new Problem(400,'Invalid JSON');}
 }
 const server=http.createServer(async(req:IncomingMessage,res:ServerResponse)=>{
  const requestId=randomUUID();
  const send=(status:number,data:unknown,type='application/json')=>{res.writeHead(status,{'Content-Type':type,'X-Request-ID':requestId,'Cache-Control':'no-store'});res.end(type==='application/json'?JSON.stringify(data):String(data));};
  try{
   const path=new URL(req.url||'/','http://127.0.0.1').pathname;
   const staticPaths:Record<string,[string,string]>={'/':['index.html','text/html'],'/app.mjs':['app.mjs','text/javascript'],'/ui_model.mjs':['ui_model.mjs','text/javascript']};
   if(req.method==='GET'&&staticPaths[path]){const [file,type]=staticPaths[path];send(200,readFileSync(join(ROOT,'web',file),'utf8'),type);return;}
   if(req.headers.authorization!=='Bearer demo-local')throw new Problem(401,'Local fixture token required');
   if(req.method==='GET'&&path==='/api/catalog'){send(200,JSON.parse(readFileSync(join(ROOT,'catalog.json'),'utf8')));return;}
   if(req.method==='POST'&&path==='/api/plans'){
    const input=await body(req);if(!fields(input,['prompt'])||typeof input.prompt!=='string'||!input.prompt.trim()||input.prompt.length>1000)throw new Problem(400,'Provide a prompt of 1-1000 characters');
    const key=req.headers['idempotency-key'];if(typeof key!=='string'||!/^[a-zA-Z0-9_-]{8,64}$/.test(key))throw new Problem(400,'A valid Idempotency-Key is required');
    const hash=digest(input.prompt);const receipt=database.prepare('SELECT payload_hash,plan_id FROM receipts WHERE key=?').get(key) as any;
    if(receipt){if(receipt.payload_hash!==hash)throw new Problem(409,'Request key used for different content');send(200,{...get(receipt.plan_id),replayed:true});return;}
    const existing=pending.get(key);if(existing){if(existing.hash!==hash)throw new Problem(409,'Request key pending for different content');send(200,{...(await existing.promise as any),replayed:true});return;}
    const promise=(async()=>{
     const result=await planner({prompt:input.prompt});const id=randomUUID();
     return transaction(()=>{const raw=JSON.stringify(result);database.prepare('INSERT INTO plans VALUES (?,?,1,?)').run(id,input.prompt as string,raw);database.prepare('INSERT INTO history VALUES (?,1,?)').run(id,raw);database.prepare('INSERT INTO receipts VALUES (?,?,?)').run(key,hash,id);return get(id);});
    })();pending.set(key,{hash,promise});
    try{send(201,{...(await promise as any),replayed:false});}finally{pending.delete(key);}return;
   }
   const match=path.match(/^\/api\/plans\/([^/]+)(\/history|\/enclosure.scad)?$/);
   if(match){const [,id,suffix]=match;if(!validId(id))throw new Problem(404,'Plan not found');
    if(req.method==='GET'){
     const plan=get(id);
     if(suffix==='/history'){send(200,database.prepare('SELECT version,result FROM history WHERE plan_id=? ORDER BY version').all(id).map((r:any)=>({version:r.version,result:JSON.parse(r.result)})));return;}
     if(suffix==='/enclosure.scad'){if(plan.result.status!=='supported')throw new Problem(409,'Unsupported build has no geometry source');send(200,plan.result.enclosure_scad,'text/plain');return;}
     send(200,plan);return;
    }
    if(req.method==='PATCH'&&!suffix){
     const input=await body(req);if(!fields(input,['expected_version','plan'])||!Number.isSafeInteger(input.expected_version)||Number(input.expected_version)<1)throw new Problem(400,'Expected version and complete plan required');
     const before=get(id);if(before.version!==input.expected_version)throw new Problem(409,'Plan changed; reload before editing');
     const result=await planner({mode:'validate',plan:input.plan});
     const current=transaction(()=>{
      const raw=JSON.stringify(result);const changed=database.prepare('UPDATE plans SET result=?,version=version+1 WHERE id=? AND version=?').run(raw,id,input.expected_version as number);
      if(changed.changes!==1)throw new Problem(409,'Plan changed; reload before editing');
      database.prepare('INSERT INTO history VALUES (?,?,?)').run(id,Number(input.expected_version)+1,raw);return get(id);
     });send(200,current);return;
    }
   }
   throw new Problem(404,'Route not found');
  }catch(e){const error=e instanceof Problem?e:new Problem(500,'Internal server error');send(error.status,{error:error.message});}
 });
 return {server,close:()=>database.close()};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const app=createApp({dbPath:process.env.BUILD_DB||join(ROOT,'Studio.db'),endpoint:process.env.MODEL_ENDPOINT||'http://127.0.0.1:8091/chat/completions',python:process.env.BUILD_PYTHON||'python3'});
 const port=Number(process.env.PORT||8080);app.server.listen(port,'127.0.0.1',()=>console.log(JSON.stringify({port:(app.server.address() as any).port})));
}
