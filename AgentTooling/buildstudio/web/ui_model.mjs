export function createStudio(api,changed=()=>{}){
 let generation=0,key=null;let view={prompt:'Plant moisture monitor',busy:false,error:'',plan:null,draft:null,conflict:false};
 const emit=()=>changed(structuredClone(view));
 return {
  get state(){return structuredClone(view);},
  prompt(value){generation++;key=null;view={...view,prompt:value,busy:false,error:'',plan:null,draft:null,conflict:false};emit();},
  edit(plan){view.draft=structuredClone(plan);emit();},
  async generate(){
   if(view.busy)return false;const seq=++generation;key??=crypto.randomUUID();view.busy=true;view.error='';emit();
   try{const plan=await api('/api/plans',{method:'POST',headers:{'Idempotency-Key':key},body:JSON.stringify({prompt:view.prompt})});
    if(seq!==generation)return false;view.plan=plan;view.draft=structuredClone(plan.result.build?.plan||null);view.conflict=false;return true;
   }catch(e){if(seq===generation)view.error=e.message;return false;}finally{if(seq===generation){view.busy=false;emit();}}
  },
  async save(){
   if(view.busy||!view.plan||!view.draft||view.conflict)return false;const seq=++generation;view.busy=true;view.error='';emit();
   try{const plan=await api('/api/plans/'+view.plan.id,{method:'PATCH',body:JSON.stringify({expected_version:view.plan.version,plan:view.draft})});
    if(seq!==generation)return false;view.plan=plan;view.draft=structuredClone(plan.result.build.plan);return true;
   }catch(e){if(seq===generation){view.error=e.message;view.conflict=e.status===409;}return false;}finally{if(seq===generation){view.busy=false;emit();}}
  },
  async reload(){
   if(view.busy||!view.plan)return false;const seq=++generation;view.busy=true;view.error='';emit();
   try{const current=await api('/api/plans/'+view.plan.id);if(seq!==generation)return false;view.plan=current;view.draft=structuredClone(current.result.build?.plan||null);view.conflict=false;return true;}
   catch(e){if(seq===generation)view.error=e.message;return false;}finally{if(seq===generation){view.busy=false;emit();}}
  }
 };
}
