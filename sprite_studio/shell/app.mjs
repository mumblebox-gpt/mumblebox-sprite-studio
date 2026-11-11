import {el,button,help,setButtonLabel} from './controls.mjs';
import {request} from './client.mjs';
import {StudioJobs} from '../runtime/jobs.mjs';
import {createImageView} from '../features/create_image/view.mjs';
import {galleryView} from '../features/gallery/view.mjs';
import {showGraph} from '../runtime/graph.mjs';
import {settingsView} from '../features/settings/view.mjs';
import {refmodsView} from '../features/refmods/view.mjs';

const tabs=[['create_image','Create Image'],['turnaround','Turnaround'],['refmods','RefMods'],['gallery','Gallery'],['roadmap','Roadmap'],['about','About'],['settings','Settings']];
export class StudioShell {
  constructor(host,node) {
    this.host=host;this.node=node;this.jobs=new StudioJobs();this.disposed=false;
    this.shadow=host.attachShadow({mode:'open'});
    this.shadow.append(el('link',{rel:'stylesheet',href:'/sprite-studio/ui/shell/theme.css'}));
    this.root=el('div',{class:'studio','data-theme':'dark'});this.shadow.append(this.root);
    for(const name of ['pointerdown','click','dblclick','wheel','keydown','contextmenu'])this.root.addEventListener(name,e=>e.stopPropagation());
    this.root.append(el('p',{},'Opening Sprite Studio…'));
    this.jobs.addEventListener('status',e=>this.status(e.detail));
    this.jobs.addEventListener('error',e=>this.message(e.detail.message,true));
    this.init().catch(e=>this.root.replaceChildren(el('p',{role:'alert'},e.message)));
  }
  async init() {
    this.boot=await request('bootstrap');if(this.disposed)return;
    this.preferences=this.boot.settings;
    this.build();this.applyPreferences();this.open(this.preferences.last_tab||'create_image');this.pollTelemetry();
    if(this.boot.active_id)this.jobs.resume(this.boot.active_id);
  }
  build() {
    const logo=el('img',{class:'brand-logo',src:'/extensions/mumblebox_sprite_studio/logo.png',alt:'mumblebox Sprite Studio'});
    const language=el('select',{'aria-label':'Language'},el('option',{value:'en'},'English'),el('option',{disabled:true},'简体中文 · planned'),el('option',{disabled:true},'Español · planned'),el('option',{disabled:true},'Fourth language · planned'));
    this.font=el('select',{'aria-label':'Text size'},[100,112,125,150,175,200].map(size=>el('option',{value:String(size)},`${size}% text`)));
    this.font.value=String(this.preferences.font);
    this.font.onchange=()=>this.setPreferences({font:Number(this.font.value)});
    this.themeButton=button('Light theme',()=>this.setPreferences({theme:this.preferences.theme==='dark'?'light':'dark'}));
    const header=el('header',{class:'brand-bar'},el('div',{class:'brand'},logo,el('small',{},this.boot.version)),
      el('div',{class:'header-controls'},language,this.font,this.themeButton,button('Support',()=>this.open('about')),button('Updates · local build',()=>this.open('settings')),button('Settings',()=>this.open('settings')),button('Show graph',()=>showGraph(this.node))));
    this.star=el('img',{class:'activity-star',src:'/extensions/mumblebox_sprite_studio/activity.svg',alt:''});
    this.activity=el('span',{role:'status','aria-live':'polite'},'Ready');
    this.meters=el('div',{class:'meters'},'Checking resources…');
    this.loaded=el('span',{class:'loaded-state'},'Models: checking…');
    this.progress=el('progress',{max:100,value:0,hidden:true,'aria-label':'Job progress'});
    const status=el('div',{class:'resource-bar'},this.star,this.activity,this.progress,this.meters,this.loaded,button('Unload models',()=>request('unload',{}).then(()=>this.message('Model unload requested; the resource bar reports the remaining loaded models.')).catch(e=>this.message(e.message,true))));
    const nav=el('nav',{class:'tabs','aria-label':'Studio tabs'});
    this.tabButtons=new Map();
    for(const [key,label] of tabs){const tab=button(label,()=>this.open(key),key==='roadmap'?'right-tabs':'');this.tabButtons.set(key,tab);nav.append(tab);}
    this.notice=el('div',{class:'notice',role:'status',hidden:true});
    this.content=el('main',{class:'content'});
    this.root.replaceChildren(header,status,nav,this.notice,this.content);
  }
  applyPreferences() {
    this.root.dataset.theme=this.preferences.theme;
    this.root.style.setProperty('--text-scale',this.preferences.font/100);
    setButtonLabel(this.themeButton,this.preferences.theme==='dark'?'Light theme':'Dark theme');
  }
  async setPreferences(patch) {
    this.preferences={...this.preferences,...patch};this.applyPreferences();
    this.preferenceWrite=(this.preferenceWrite||Promise.resolve()).then(()=>request('settings',patch)).catch(e=>this.message(e.message,true));
    await this.preferenceWrite;
  }
  open(key) {
    if(this.preferences.last_tab!==key)this.setPreferences({last_tab:key});
    this.view?.dispose?.();
    for(const [id,tab] of this.tabButtons)tab.setAttribute('aria-current',id===key?'page':'false');
    if(key==='create_image'||key==='turnaround')this.view=createImageView(this,key);
    else if(key==='gallery')this.view=galleryView(this);
    else if(key==='settings')this.view=settingsView(this);
    else if(key==='refmods')this.view=refmodsView(this);
    else this.view={element:this.information(key)};
    this.content.replaceChildren(this.view.element);this.content.scrollTop=0;
  }
  information(key) {
    if(key==='about')return el('section',{class:'reading'},el('h1',{},'mumblebox Sprite Studio'),el('p',{},`Version ${this.boot.version} · local development build`),
      el('p',{},'A local workspace for image creation, consistent turnarounds and reusable reference assets. ComfyUI owns model execution; this studio owns its drafts, recipes and Gallery.'),
      el('h2',{},'A useful starting workflow'),el('ol',{},el('li',{},'Create a neutral full-body character or upload an approved reference. Add plain-language notes beside each picture.'),el('li',{},'Use Turnaround to request the views you need. Keep the official upsampler off when you need exact camera wording.'),el('li',{},'Review identity, proportions and left/right details. Export the master and separate PNG views, or save the reviewed views in RefMods.'),el('li',{},'Reuse Gallery settings for a repeatable recipe. Fixed seeds help comparison; they do not guarantee consistency after changing other settings.')),
      el('h2',{},'Help and recovery'),el('p',{},'A first Generate downloads only missing files. If interrupted, reuse the recipe; partial downloads resume. If memory is tight, try 4-bit, a smaller canvas or tiled decoding. Unload models when the shared ComfyUI queue is idle.'),
      el('p',{},'Gallery and RefMods deletions go to recoverable Trash. Purge Cache clears only owned temporary files. Saved images, original references, models and settings are kept.'),
      el('h2',{},'Sources and support'),el('p',{},el('a',{href:'https://huggingface.co/PrunaAI/P-H3-Image-Comfy',target:'_blank',rel:'noopener'},'Pruna P-H3 model and license'),' · ',el('a',{href:'https://github.com/Luisacaotica/ComfyUI-MiniMaxH3Mod',target:'_blank',rel:'noopener'},'RefMod nodes (MIT)'),' · ',el('a',{href:'https://docs.comfy.org',target:'_blank',rel:'noopener'},'ComfyUI documentation')),
      help('RefMod extraction uses the original H3 video VAE for still images; it does not train model weights. Latent-only imports are decoded before P-H3 uses them. Camera angles remain requests, not measured calibration. Generic H3 LoRAs are not qualified for this distilled image model.'),
      help('For a local support report, keep the Gallery recipe, error text and the version shown above. Sprite Studio has no public update channel yet.'));
    if(key==='roadmap')return el('section',{class:'reading'},el('h1',{},'Roadmap'),el('h2',{},'Available in this development build'),el('p',{},'4-bit and 8-bit image generation; annotated references; reviewed creative enhancement and official upsampling; turnaround review and exports; reference collections and encoded still RefMods; Gallery and safe maintenance.'),el('h2',{},'Local validation'),el('p',{},'Both image precisions and both official helper precisions have produced real images. Character and aircraft sheets, four-picture references, RefMod encode/decode, cancellation, download resume, Gallery and cache controls were exercised in this Desktop. Review every sheet: requested angles and small construction details can still differ. Mesh quality has not been tested.'),el('h2',{},'Future work'),el('p',{},'Additional languages, H3 animation and game sprite production, then qualified Foundry integration. These are roadmap items, not active features.'));
    return el('section',{class:'reading'},el('h1',{},tabs.find(t=>t[0]===key)[1]),el('p',{},'This workflow is being connected in the current implementation phase.'));
  }
  message(text,error=false) {this.notice.hidden=false;this.notice.textContent=text;this.notice.classList.toggle('error',error);}
  status(run) {
    if(!this.activity)return;
    const busy=!['completed','failed','canceled','interrupted'].includes(run.status);
    this.star.classList.toggle('busy',busy);
    const d=run.detail;
    this.activity.textContent=d.file?`${d.stage}: ${(d.bytes/1e9).toFixed(1)} / ${(d.total/1e9).toFixed(1)} GB · ${d.file}`:d.message||run.status;
    this.activity.title=this.activity.textContent;
    if(run.status==='preparing')this.notice.hidden=true;
    this.progress.hidden=!busy;
    if(d.total)this.progress.value=d.bytes/d.total*100;else this.progress.removeAttribute('value');
    if(run.status==='failed')this.message(d.message,true);
  }
  async pollTelemetry() {
    if(this.disposed)return;
    try{const status=await request('telemetry');const gpu=status.devices[0];this.meters.textContent=`CPU ${Math.round(status.cpu)}% · RAM ${(status.ram.used/2**30).toFixed(1)} / ${(status.ram.total/2**30).toFixed(0)} GB${gpu?` · VRAM ${((gpu.vram_total-gpu.vram_free)/2**30).toFixed(1)} / ${(gpu.vram_total/2**30).toFixed(0)} GB`:''}`;this.loaded.textContent=`${status.loaded_models} model${status.loaded_models===1?'':'s'} loaded`;}catch{this.meters.textContent='Resources unavailable';}
    if(!this.disposed)this.telemetryTimer=setTimeout(()=>this.pollTelemetry(),3000);
  }
  setExpanded(value) {this.host.hidden=!value;this.host.classList.toggle('sprite-studio-expanded',value);}
  dispose() {this.disposed=true;this.view?.dispose?.();this.jobs.dispose();clearTimeout(this.telemetryTimer);this.host.remove();}
}
