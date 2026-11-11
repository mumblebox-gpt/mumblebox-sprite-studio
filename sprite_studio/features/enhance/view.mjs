import {el,button,help} from '../../shell/controls.mjs';

export function creativeEnhancer(shell,draft,accept) {
  const panel=el('section',{class:'enhancer'}),review=el('div',{hidden:true}),status=el('small',{class:'help',role:'status'});
  const candidate=el('textarea',{rows:5,'aria-label':'Suggested enhanced prompt'});
  let shownId=null,discardedId=null;
  const enhance=async()=>{
    run.disabled=true;review.hidden=true;status.textContent='Preparing native enhancement on the GPU…';
    try{await shell.jobs.generate({kind:'enhance',draft:structuredClone(draft)});}
    catch(e){status.textContent=e.message;run.disabled=false;}
  };
  const run=button('Enhance prompt',enhance),cancel=button('Cancel enhancement',()=>shell.jobs.cancel().catch(e=>shell.message(e.message,true)));cancel.hidden=true;
  const render=job=>{
    const busy=job&&!['completed','failed','canceled','interrupted'].includes(job.status);
    run.disabled=!!busy;
    if(job?.recipe.kind!=='enhance'||job.recipe.source_kind!==draft.kind){cancel.hidden=true;return;}
    cancel.hidden=!busy;
    status.textContent=job.detail.message||job.status;
    if(job.detail.fallback_reason)status.textContent+=' CPU fallback: '+job.detail.fallback_reason;
    if(job.status==='completed'){
      status.textContent=`Suggestion ready on ${job.detail.device} in ${job.detail.seconds}s. Review before accepting.`+(job.detail.fallback_reason?' CPU fallback: '+job.detail.fallback_reason:'');
      if(shownId!==job.id&&discardedId!==job.id){candidate.value=job.detail.candidate;review.hidden=false;shownId=job.id;}
    }
  };
  const listener=e=>render(e.detail);shell.jobs.addEventListener('status',listener);render(shell.jobs.run);
  panel.dispose=()=>shell.jobs.removeEventListener('status',listener);
  review.append(candidate,el('div',{class:'actions'},button('Accept suggestion',()=>{draft.original_prompt=draft.prompt;draft.accepted_enhancement=candidate.value;accept(candidate.value);review.hidden=true;discardedId=shownId;status.textContent='Suggestion accepted. Reference and camera settings are unchanged.';}),button('Try again',enhance),button('Discard',()=>{review.hidden=true;discardedId=shownId;status.textContent='Original prompt retained.';})));
  panel.append(el('div',{class:'actions'},run,cancel),help('Adds a few creative details for review using native ComfyUI text generation. GPU first; one CPU fallback if GPU resources fail. CPU fallback can take much longer. The 4-bit model downloads on first use. Comfy manages its memory. This is separate from the official P-H3 upsampler.'),status,review);
  return panel;
}
