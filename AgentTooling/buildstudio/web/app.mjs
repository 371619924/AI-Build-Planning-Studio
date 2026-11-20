import {createStudio} from '/ui_model.mjs';
const find=id=>document.getElementById(id),status=find('status'),draft=find('draft');
async function api(path,options={}){
 const response=await fetch(path,{...options,headers:{'Content-Type':'application/json',Authorization:'Bearer demo-local',...options.headers}});
 if(path.endsWith('.scad')){if(!response.ok)throw new Error('Download failed');return response.text();}
 const body=await response.json();if(!response.ok){const e=new Error(body.error);e.status=response.status;throw e;}return body;
}
const studio=createStudio(api,v=>{
 status.textContent=v.busy?'Working...':v.error||((v.plan?'Plan '+v.plan.id+' / revision '+v.plan.version:'Ready'));
 find('generate').disabled=v.busy;find('save').disabled=v.busy||!v.draft||v.conflict;find('reload').disabled=v.busy||!v.plan;find('download').disabled=v.busy||v.plan?.result.status!=='supported';
 draft.disabled=v.busy;draft.value=v.draft?JSON.stringify(v.draft,null,2):'';
 if(v.plan)find('summary').textContent=JSON.stringify(v.plan.result.build||{status:'unsupported',reason:v.plan.result.reason},null,2);
 else find('summary').textContent='No current plan.';
});
find('prompt').addEventListener('input',e=>studio.prompt(e.target.value));
find('generate-form').addEventListener('submit',e=>{e.preventDefault();studio.generate();});
find('save').addEventListener('click',()=>{try{studio.edit(JSON.parse(draft.value));studio.save();}catch{status.textContent='Enter valid plan JSON.';}});
find('reload').addEventListener('click',()=>studio.reload());
find('download').addEventListener('click',async()=>{try{const text=await api('/api/plans/'+studio.state.plan.id+'/enclosure.scad');const url=URL.createObjectURL(new Blob([text],{type:'text/plain'}));const a=document.createElement('a');a.href=url;a.download='Enclosure.scad';a.click();URL.revokeObjectURL(url);}catch(e){status.textContent=e.message;}});
