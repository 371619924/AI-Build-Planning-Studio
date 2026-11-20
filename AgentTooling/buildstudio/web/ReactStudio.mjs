/** Optional React adapter; shared controller is executed independently in Node. */
import React,{useState,useEffect} from 'react';
import {createStudio} from './ui_model.mjs';
const h=React.createElement;
export function ReactStudio({api}){
 const [view,setView]=useState(null),[text,setText]=useState(''),[error,setError]=useState('');
 const [model]=useState(()=>createStudio(api,setView));const v=view||model.state;
 useEffect(()=>{setText(v.draft?JSON.stringify(v.draft,null,2):'');},[v.draft]);
 return h('main',null,h('h1',null,'Build Planning Studio'),
  h('p',null,'Scripted provider and synthetic parts; no physical build validation.'),
  h('form',{onSubmit:e=>{e.preventDefault();model.generate();}},
   h('label',{htmlFor:'build-prompt'},'Build request'),
   h('input',{id:'build-prompt',value:v.prompt,onChange:e=>model.prompt(e.target.value)}),
   h('button',{disabled:v.busy},'Generate plan')),
  h('p',{role:'status','aria-live':'polite'},v.busy?'Working...':error||v.error),
  h('pre',null,JSON.stringify(v.plan?.result||{},null,2)),
  h('label',{htmlFor:'build-draft'},'Plan JSON'),
  h('textarea',{id:'build-draft',value:text,disabled:v.busy,onChange:e=>setText(e.target.value)}),
  h('button',{disabled:v.busy||!v.draft||v.conflict,onClick:()=>{try{const p=JSON.parse(text);setError('');model.edit(p);model.save();}catch{setError('Enter valid JSON.');}}},'Validate and save'),
  h('button',{disabled:v.busy||!v.plan,onClick:()=>model.reload()},'Reload latest'));
}
