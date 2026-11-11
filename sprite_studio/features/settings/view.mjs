import {el,button,help} from '../../shell/controls.mjs';
import {request} from '../../shell/client.mjs';

export function settingsView(shell) {
  const inventory=el('div',{}),status=el('p',{role:'status'},'Checking temporary files…');
  let disposed=false;
  const refresh=async()=>{try{const info=await request('cache');if(!disposed)status.textContent=`${info.files} temporary files · ${(info.bytes/1024/1024).toFixed(1)} MB can be cleared · ${info.active_folders} active folders protected`;}catch(e){status.textContent=e.message;}};
  const purge=button('Purge cache',async()=>{purge.disabled=true;try{const result=await request('purge-cache',{});status.textContent=`Cleared ${result.files} files (${(result.bytes/1024/1024).toFixed(1)} MB). Saved assets and models were preserved.`;}catch(e){shell.message(e.message,true);}finally{purge.disabled=false;}},'primary');
  request('bootstrap').then(boot=>{if(disposed)return;for(const model of boot.models)inventory.append(el('div',{class:'model-row'},el('strong',{},model.path.split('/').at(-1)),help(`${(model.size/1e9).toFixed(2)} GB · ${model.installed?'Installed':'Downloads on first use'} · ${model.sources.join(' → ')}`)));}).catch(e=>shell.message(e.message,true));
  refresh();
  return {element:el('section',{class:'reading'},el('h1',{},'Settings'),el('h2',{},'Temporary files'),help('Clears only abandoned Sprite Studio scratch files. Active work, original references, Gallery, RefMods, model downloads, model weights and settings are protected.'),status,purge,
    el('h2',{},'Models download when needed'),el('p',{},'Generate downloads only the missing files for the selected precision. Publisher checksums verify every file; matching secondary sources are used if the primary download fails.'),inventory,
    el('h2',{},'Creative helper'),help(`${shell.boot.enhancer?.model||'Local helper'} · native ComfyUI · GPU first, CPU fallback only. Comfy manages model memory. The official P-H3 prompt upsampler uses its own model and separate toggle.`),
    el('h2',{},'Updates'),help('Local development build. There is no published Sprite Studio release channel yet. Installed version: '+shell.boot.version),
    el('h2',{},'Language'),help('English is available now. The header reserves four language choices; translation is on the roadmap.')),
    dispose:()=>{disposed=true;}};
}
