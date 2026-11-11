import {el,button,help,imageUrl,setButtonLabel} from '../../shell/controls.mjs';
import {request} from '../../shell/client.mjs';
import {cropReview} from '../turnaround/review.mjs';

export function galleryView(shell) {
  const grid=el('div',{class:'gallery-grid'});
  const sort=el('select',{'aria-label':'Gallery order'},el('option',{value:'newest'},'Newest first'),el('option',{value:'oldest'},'Oldest first'));
  const kind=el('select',{'aria-label':'Workflow filter'},el('option',{value:''},'All workflows'),el('option',{value:'create_image'},'Create Image'),el('option',{value:'turnaround'},'Turnaround'));
  const favorite=el('input',{type:'checkbox'}),trash=el('input',{type:'checkbox'});
  const selected=new Set(),comparison=el('div',{class:'compare-grid',hidden:true}),page=el('span',{}),selection=el('span',{},'0 selected');
  let disposed=false,offset=0,current=[],lastTrashed=[],sequence=0;
  const report=e=>shell.message(e.message,true);
  const updateSelection=()=>{selection.textContent=`${selected.size} selected`;};
  const move=async(ids,toTrash)=>{
    try{await request('gallery-trash',{ids,trashed:toTrash});if(toTrash)lastTrashed=[...ids];await load();}catch(e){report(e);}
  };
  const compare=()=>{
    const runs=current.filter(r=>selected.has(r.id));
    if(runs.length!==2||runs.some(r=>!r.detail.outputs?.length)){shell.message('Select two completed images to compare.',true);return;}
    comparison.hidden=false;comparison.replaceChildren(...runs.map(r=>el('article',{},el('h2',{},r.name||r.recipe.profile.toUpperCase()),el('img',{src:imageUrl(r.detail.outputs[0]),alt:r.name||r.recipe.prompt}),help(`Seed ${r.recipe.seed} · ${r.recipe.width} × ${r.recipe.height}`))),button('Close comparison',()=>{comparison.hidden=true;}));
  };
  const load=async()=>{
    const requestSequence=++sequence;
    try{
      const {runs,has_more}=await request('gallery',undefined,{sort:sort.value,kind:kind.value,offset:String(offset),favorite:String(favorite.checked),trashed:String(trash.checked)});
      if(disposed||requestSequence!==sequence)return;
      current=runs;selected.clear();updateSelection();page.textContent=`Page ${offset/50+1}`;previous.disabled=offset===0;next.disabled=!has_more;
      grid.replaceChildren();
      if(!runs.length)grid.append(el('p',{class:'empty-note'},'Your generated images and their settings will appear here.'));
      for(const run of runs) {
        const image=run.detail.outputs?.[0];
        const check=el('input',{type:'checkbox',onchange:e=>{e.target.checked?selected.add(run.id):selected.delete(run.id);updateSelection();}});
        const name=el('input',{type:'text',value:run.name,placeholder:run.recipe.prompt.slice(0,60),maxLength:160,'aria-label':'Result name',onchange:async e=>{try{const value=e.target.value;await request('gallery-update',{id:run.id,patch:{name:value}});run.name=value;}catch(error){report(error);}}});
        const star=button(run.favorite?'★ Favorite':'☆ Favorite',async()=>{star.disabled=true;try{const value=!run.favorite;await request('gallery-update',{id:run.id,patch:{favorite:value}});run.favorite=value;setButtonLabel(star,run.favorite?'★ Favorite':'☆ Favorite');}catch(e){report(e);}finally{star.disabled=false;}});
        const card=el('article',{class:'gallery-card'},el('label',{},check,' Select result'),image?el('a',{href:imageUrl(image),target:'_blank',rel:'noopener'},el('img',{src:imageUrl(image),alt:run.name||run.recipe.prompt,loading:'lazy'})):el('div',{class:'empty-thumbnail'},run.status),
          name,help(new Date(run.created*1000).toLocaleString()),star,
          help(`${run.recipe.profile.toUpperCase()} · ${run.recipe.width} × ${run.recipe.height} · ${run.status}`),
          button('Reuse settings',()=>{const copy=structuredClone(run.recipe);copy.seed_mode='fixed';shell.boot.drafts[copy.kind]=copy;request('draft',copy).then(()=>shell.open(copy.kind==='refmod'?'refmods':copy.kind)).catch(e=>shell.message(e.message,true));}));
        if(image)for(const kind of ['create_image','turnaround'])card.append(button(kind==='turnaround'?'Use for turnaround':'Use as image reference',async()=>{try{const asset=await request('reference-output',{id:run.id});const draft=shell.boot.drafts[kind];if(draft.references.filter(c=>c.enabled!==false).length>=8)throw Error('Disable a reference before adding another.');draft.references.push({asset_id:asset.id,role:'identity',note:'Preserve this subject and its identifying details.',enabled:true});await request('draft',draft);shell.open(kind);}catch(e){shell.message(e.message,true);}}));
        if(image&&run.recipe.kind==='turnaround')card.append(button('Review / export views',async()=>{try{const review=await cropReview(shell,run.id);shell.content.replaceChildren(review);}catch(e){shell.message(e.message,true);}}));
        card.append(button(trash.checked?'Restore':'Move to Trash',()=>move([run.id],!trash.checked)));
        const prompt=el('pre',{class:'prompt-preview'},run.detail.actual_prompt||run.detail.compiled_prompt||run.recipe.prompt);
        card.append(el('details',{},el('summary',{},'Actual prompt and settings'),prompt,help(`Saved seed: ${run.recipe.seed}`)));
        grid.append(card);
      }
    }catch(error){shell.message(error.message,true);}
  };
  const previous=button('Previous',()=>{offset=Math.max(0,offset-50);load();}),next=button('Next',()=>{offset+=50;load();});
  for(const input of [sort,kind,favorite,trash])input.onchange=()=>{offset=0;load();};load();
  const toolbar=el('div',{class:'actions'},sort,kind,el('label',{},favorite,' Favorites only'),el('label',{},trash,' Show Trash'),selection,
    button('Compare selected',compare),button('Trash selected',()=>move([...selected],true)),button('Restore selected',()=>move([...selected],false)),button('Undo last deletion',()=>{if(lastTrashed.length)move(lastTrashed,false);}));
  return {element:el('section',{},el('h1',{},'Gallery'),help('Rename, compare, reuse or move results to recoverable Trash. Saved recipes and references remain available.'),toolbar,comparison,grid,el('div',{class:'actions'},previous,page,next)),dispose:()=>{disposed=true;}};
}
