import {el,button,field,help,imageUrl} from '../../shell/controls.mjs';
import {request} from '../../shell/client.mjs';
import {referenceCards} from '../references/cards.mjs';
import {turnaroundSettings} from '../turnaround/view.mjs';
import {cropReview} from '../turnaround/review.mjs';
import {creativeEnhancer} from '../enhance/view.mjs';

export function createImageView(shell,kind='create_image') {
  const draft=shell.boot.drafts[kind];
  let saveTimer;
  const changed=()=>{clearTimeout(saveTimer);saveTimer=setTimeout(()=>request('draft',draft).catch(e=>shell.message(e.message,true)),300);};
  const prompt=el('textarea',{rows:7,value:draft.prompt,placeholder:'Describe the image you want to create…',oninput:e=>{draft.prompt=e.target.value;changed();},'aria-label':'Image prompt'});
  const settings=el('div',{class:'settings-grid'}),advanced=el('div',{class:'settings-grid'});
  for(const [key,definition] of Object.entries(shell.boot.fields)) {
    const control=field(key,definition,draft[key] ?? definition.default,value=>{draft[key]=value;changed();});
    (definition.advanced?advanced:settings).append(control);
  }
  const previewText=el('pre',{class:'prompt-preview',hidden:true});
  const presets=el('select',{'aria-label':'Canvas preset'},el('option',{value:''},'Choose a canvas preset…'),
    ...[['1024,1024','Square · 1024 × 1024'],['768,1344','Portrait · 768 × 1344'],['1344,768','Landscape · 1344 × 768'],['4096,1024','Four-view strip · 4096 × 1024'],['2048,2048','Square sheet · 2048 × 2048']].map(([value,label])=>el('option',{value},label)));
  presets.onchange=()=>{if(!presets.value)return;[draft.width,draft.height]=presets.value.split(',').map(Number);changed();shell.open(kind);};
  const reset=()=>{for(const [key,definition] of Object.entries(shell.boot.fields))draft[key]=definition.default;if(kind==='turnaround'){draft.width=4096;draft.height=1024;}changed();shell.open(kind);};
  const preview=async()=>{try{previewText.textContent=(await request('preview',draft)).prompt;previewText.hidden=false;}catch(e){shell.message(e.message,true);}};
  const enhancer=creativeEnhancer(shell,draft,value=>{draft.prompt=value;prompt.value=value;changed();});
  const controls=el('section',{class:'controls-pane'},
    el('div',{class:'section-heading'},el('h1',{},kind==='create_image'?'Create an image':'Create a turnaround'),help('Build from an idea, a reference, or both.')),
    el('label',{class:'field-label'},'Your prompt',prompt),
    enhancer,
    el('div',{class:'actions'},button('Preview final prompt',preview)),previewText,
    referenceCards(shell,draft,changed),kind==='turnaround'?turnaroundSettings(shell,draft,changed):null,
    el('label',{class:'field-label'},'Canvas preset',presets),help('Sets width and height together. You can fine-tune either dimension below; references are unchanged.'),settings,
    el('details',{},el('summary',{},'Advanced'),advanced,button('Reset generation settings',reset),help('Restores model, canvas, sampling and helper defaults. Keeps your prompt, pictures and view choices.')),
    el('div',{class:'actions primary-actions'},button('Generate',async()=>{try{await request('draft',draft);await shell.jobs.generate({...draft});}catch(e){shell.message(e.message,true);}},'primary'),
      button('Cancel job',()=>shell.jobs.cancel().catch(e=>shell.message(e.message,true)))));
  const result=el('section',{class:'result-pane'});
  shell.boot.latest??={};
  const render=run=>{
    if(!run || run.recipe.kind!==kind) return;
    const images=run.detail.outputs || [];
    if(!images.length&&shell.boot.latest[kind]?.detail.outputs?.length)return;
    result.replaceChildren(el('h2',{},'Result'));
    if(images.length) {
      shell.boot.latest[kind]=run;
      result.append(el('div',{class:'preview-canvas'},el('img',{src:imageUrl(images[0]),alt:'Generated image'})),
        el('div',{class:'actions'},button('Open Gallery',()=>shell.open('gallery')),button('Reuse this seed',()=>{draft.seed=run.recipe.seed;draft.seed_mode='fixed';changed();shell.open(kind);})),
        help(`Saved seed ${run.recipe.seed} · ${run.recipe.profile.toUpperCase()} · ${run.recipe.width} × ${run.recipe.height}`));
      if(kind==='turnaround')result.append(button('Review crops and export',async()=>{try{const review=await cropReview(shell,run.id);result.querySelector('.crop-review')?.remove();result.append(review);}catch(e){shell.message(e.message,true);}}));
    } else result.append(el('div',{class:'preview-canvas empty'},el('p',{},run.detail.message || 'Your image will appear here.')));
  };
  result.append(el('h2',{},'Your canvas'),el('div',{class:'preview-canvas empty'},el('div',{},el('strong',{},'A place for your next idea'),help('Generated images are saved with their settings and references.'))));
  const listener=e=>render(e.detail);shell.jobs.addEventListener('status',listener);render(shell.boot.latest[kind]);render(shell.jobs.run);
  return {element:el('div',{class:'generation-layout'},controls,result),dispose:()=>{enhancer.dispose();clearTimeout(saveTimer);request('draft',draft).catch(()=>{});shell.jobs.removeEventListener('status',listener);}};
}
