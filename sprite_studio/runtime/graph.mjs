import {app} from '/scripts/app.js';
export const INTERFACE = 'MumbleboxSpriteStudio/Interface';

export function layoutStudioBranches() {
  const branches=[['Create Image',100],['Turnaround',300],['RefMods',500],['Enhance',700]];
  branches.forEach(([label,start],lane)=>{
    const nodes=app.graph._nodes.filter(n=>Number(n.id)>=start&&Number(n.id)<start+200).sort((a,b)=>Number(a.id)-Number(b.id));
    if(!nodes.length)return;
    const x=1500+lane*1820;let y=150;
    for(let i=0;i<nodes.length;i+=4){
      const row=nodes.slice(i,i+4);let height=0;
      row.forEach((node,column)=>{const computed=node.computeSize?.()||node.size;node.size=[Math.max(360,computed[0]),Math.max(220,node.size[1],computed[1]+20)];node.pos=[x+column*420,y];height=Math.max(height,node.size[1]);});
      y+=height+90;
    }
    const title=`Sprite Studio · ${label}`;
    let group=app.graph._groups.find(g=>g.title===title);
    if(!group){group=new LiteGraph.LGraphGroup(title);app.graph.add(group);}
    group.configure({...group.serialize(),title,bounding:[x-40,65,1700,y-65],color:'#805a40',font_size:24});
  });
  app.graph.setDirtyCanvas(true,true);
}

export async function persistStudioGraph() {
  const store=app.extensionManager.workflow;
  const workflow=store.activeWorkflow;
  if(!app.graph.extra?.sprite_studio || !workflow) throw Error('Open the Sprite Studio graph first.');
  workflow.changeTracker.activeState=JSON.parse(JSON.stringify(app.graph.serialize()));
  workflow.isModified=true;
  await store.saveWorkflow(workflow);
}

export async function syncBranch(prompt, kind, recipe) {
  if (!app.graph.extra?.sprite_studio) throw Error('Open the Sprite Studio workflow before generating.');
  for(const spec of Object.values(prompt))if(!LiteGraph.registered_node_types[spec.class_type])throw Error(`ComfyUI is missing ${spec.class_type}.`);
  const start = {create_image:100,turnaround:300,refmod:500,enhance:700}[kind];
  if(!start)throw Error('Unknown Studio workflow.');
  for (const node of [...app.graph._nodes]) if (node.id >= start && node.id < start+200) app.graph.remove(node);
  const created = new Map();
  let i = 0;
  for (const [id, spec] of Object.entries(prompt)) {
    const node = LiteGraph.createNode(spec.class_type);
    if (!node) throw Error(`ComfyUI is missing ${spec.class_type}.`);
    node.id = Number(id);
    node.mode=LiteGraph.NEVER;
    node.title = spec._meta?.title || spec.class_type;
    node.pos = [1500 + (i%4)*400, 100 + Math.floor(i/4)*300];
    node.size = [360,220];
    app.graph.add(node);
    for (const [name,value] of Object.entries(spec.inputs)) {
      if (Array.isArray(value)) continue;
      const widget = node.widgets?.find(w => w.name === name);
      if (widget) {
        widget.value = spec.class_type==='RandomNoise'&&name==='noise_seed'?recipe.seed:spec.class_type==='TextGenerateV2'&&name==='sampling_mode.seed'?(kind==='enhance'?recipe.seed:recipe.upsampler_seed):value;
        if(spec.class_type==='TextGenerateV2'&&name==='sampling_mode')await widget.callback?.(value);
      }
    }
    created.set(id,node); i++;
  }
  for (const [id,spec] of Object.entries(prompt)) for (const [name,value] of Object.entries(spec.inputs)) {
    if (!Array.isArray(value)) continue;
    const target = created.get(id), source = created.get(String(value[0]));
    let index = target.inputs?.findIndex(input => input.name === name) ?? -1;
    if (index < 0) { target.addInput(name,source.outputs[value[1]].type); index=target.inputs.length-1; }
    source.connect(value[1],target,index);
  }
  app.graph.extra.sprite_studio.active_kind = kind;
  app.graph.extra.sprite_studio.recipes??={};
  app.graph.extra.sprite_studio.recipes[kind]=structuredClone(recipe);
  layoutStudioBranches();
  await persistStudioGraph();
  return app.graph.serialize();
}

export function showGraph(node) {
  node.studio?.setExpanded(false);
  app.canvas.centerOnNode(node);
}
