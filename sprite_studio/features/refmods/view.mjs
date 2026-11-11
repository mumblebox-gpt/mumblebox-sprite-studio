import {el,button,field,help,assetUrl} from '../../shell/controls.mjs';
import {request} from '../../shell/client.mjs';
import {referenceCards} from '../references/cards.mjs';

export function refmodsView(shell) {
  const draft=shell.boot.drafts.refmod;let disposed=false,offset=0,sequence=0,seenRun=null;
  const report=e=>shell.message(e.message,true);
  let saveTimer;
  const changed=()=>{clearTimeout(saveTimer);saveTimer=setTimeout(()=>request('draft',draft).catch(report),300);};
  const name=el('input',{value:draft.prompt,maxLength:160,'aria-label':'Reference name',oninput:e=>{draft.prompt=e.target.value;changed();}});
  const tags=el('input',{value:draft.tags||'',maxLength:500,'aria-label':'Reference tags',oninput:e=>{draft.tags=e.target.value;changed();}});
  const notes=el('textarea',{value:draft.notes||'',rows:3,maxLength:3000,'aria-label':'Reference notes',oninput:e=>{draft.notes=e.target.value;changed();}});
  const settings=el('div',{class:'settings-grid'}),advanced=el('div',{class:'settings-grid'});
  draft.refmod??={};
  for(const [key,definition] of Object.entries(shell.boot.refmod_fields)){
    draft.refmod[key]??=definition.default;
    (definition.advanced?advanced:settings).append(field('refmod-'+key,definition,draft.refmod[key],value=>{draft.refmod[key]=value;changed();}));
  }
  const save=async fresh=>{try{
    const saved=await request('refmod-save',{id:fresh?undefined:draft.library_id,name:draft.prompt,references:draft.references,notes:draft.notes,tags:draft.tags,category:draft.refmod.concept_type});
    draft.library_id=saved.id;changed();shell.message('Reference collection saved. Original pictures are preserved.');await load();
  }catch(e){report(e);}};
  const editor=el('section',{class:'controls-pane'},el('h1',{},'RefMods'),help('Keep reusable characters, objects and styles. Collections preserve original pictures; Create encoded RefMod also builds a real H3 safetensors bundle. P-H3 uses the originals whenever available.'),
    el('label',{class:'field-label'},'Name',name),el('label',{class:'field-label'},'Tags',tags),help('Short labels to help identify this reference set.'),el('label',{class:'field-label'},'Notes',notes),help('Describe the neutral appearance and the details future images should preserve.'),
    referenceCards(shell,draft,changed),settings,el('details',{},el('summary',{},'Advanced extraction'),advanced),
    el('div',{class:'actions'},button('Save collection',()=>save(false)),button('Save as new collection',()=>save(true)),
      button('Create encoded RefMod',async()=>{try{await request('draft',draft);await shell.jobs.generate({...draft,operation:'create'});}catch(e){report(e);}},'primary'),
      button('Cancel job',()=>shell.jobs.cancel().catch(report))));
  const list=el('div',{class:'gallery-grid'}),trash=el('input',{type:'checkbox',onchange:()=>{offset=0;load();}}),status=el('p',{role:'status'});
  const chooseFile=el('input',{type:'file',accept:'.safetensors,.zip',hidden:true,onchange:async e=>{
    const file=e.target.files[0];if(!file)return;const body=new FormData();body.append('file',file);
    try{await request('refmod-import',body);shell.message('Reference file imported.');await load();}catch(error){report(error);}finally{e.target.value='';}
  }});
  const edit=item=>{Object.assign(draft,{library_id:item.id,prompt:item.name,tags:item.tags,notes:item.notes,references:structuredClone(item.references),refmod:{...draft.refmod,...item.settings,concept_type:item.category}});shell.open('refmods');};
  const packageExport=async(item,card)=>{
    try{const result=await request('refmod-package',{id:item.id});card.append(el('a',{href:result.download,download:`${item.name}.sprite-refmod.zip`},'Download package with originals'));}catch(e){report(e);}
  };
  const load=async()=>{
    const requestSequence=++sequence;
    try{const result=await request('refmods',undefined,{offset:String(offset),trashed:String(trash.checked)});if(disposed||requestSequence!==sequence)return;list.replaceChildren();
      for(const item of result.items){
        const card=el('article',{class:'gallery-card'},el('h3',{},item.name),help(item.kind==='refmod'?`Encoded H3 RefMod · ${item.member_count} still reference(s)`:'Original picture collection'),
          item.references[0]?el('img',{src:assetUrl(item.references[0].asset_id),alt:item.name,loading:'lazy'}):el('div',{class:'empty-thumbnail'},'Latent-only · decode for preview'),
          help(`${item.category} · ${item.tags||'No tags'}`),el('p',{},item.notes),button('Edit details / use as base',()=>edit(item)));
        if(item.references.length)for(const kind of ['create_image','turnaround'])card.append(button(kind==='turnaround'?'Use in Turnaround':'Use in Create Image',async()=>{
          try{const references=(await request('refmod-select',{id:item.id,indices:item.references.map((_,i)=>i)})).references;const target=shell.boot.drafts[kind];
            if(target.references.filter(c=>c.enabled!==false).length+references.length>8)throw Error('The combined selection exceeds eight references. Use Add from RefMods to choose individual pictures.');
            target.references.push(...references);await request('draft',target);shell.open(kind);
          }catch(e){report(e);}
        }));
        if(item.kind==='refmod'){
          card.append(el('a',{href:`/sprite-studio/v1/refmod-file?id=${item.id}`,download:`${item.name}.safetensors`},'Download encoded RefMod'));
          if(!item.references.length)card.append(button('Decode reference pictures',async()=>{try{await shell.jobs.generate({kind:'refmod',operation:'decode',library_id:item.id,prompt:item.name,refmod:{},references:[]});}catch(e){report(e);}}));
        }
        card.append(button('Export package + originals',()=>packageExport(item,card)),button(trash.checked?'Restore entry':'Move entry to Trash',async()=>{try{await request('refmod-trash',{id:item.id,trashed:!trash.checked});load();}catch(e){report(e);}}));list.append(card);
      }
      if(!result.items.length)list.append(help('Save your first neutral character, object or style collection.'));
      previous.disabled=offset===0;next.disabled=!result.has_more;
    }catch(e){report(e);}
  };
  const previous=button('Previous',()=>{offset=Math.max(0,offset-50);load();}),next=button('Next',()=>{offset+=50;load();});
  const listener=e=>{const run=e.detail;if(run.recipe.kind!=='refmod')return;status.textContent=run.detail.message||run.status;if(run.status==='completed'&&seenRun!==run.id){seenRun=run.id;load();}};
  shell.jobs.addEventListener('status',listener);load();
  return {element:el('div',{class:'generation-layout'},editor,el('section',{class:'result-pane'},el('h2',{},'Reference library'),
    el('div',{class:'actions'},button('Import RefMod / package',()=>chooseFile.click()),chooseFile,el('label',{},trash,' Show Trash')),help('Supports image RefMod v4 and image bundles v5. Audio/video files remain for the future H3 workflow.'),status,list,el('div',{class:'actions'},previous,next))),
    dispose:()=>{disposed=true;clearTimeout(saveTimer);request('draft',draft).catch(()=>{});shell.jobs.removeEventListener('status',listener);}};
}
