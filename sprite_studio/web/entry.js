import {app} from '/scripts/app.js';
import {StudioShell} from '/sprite-studio/ui/shell/app.mjs';
import {INTERFACE} from '/sprite-studio/ui/runtime/graph.mjs';
import {button} from '/sprite-studio/ui/shell/controls.mjs';

function registerNode() {
  if(LiteGraph.registered_node_types[INTERFACE])return;
  class SpriteStudioNode extends LiteGraph.LGraphNode {
    constructor() {
      super('mumblebox Sprite Studio');this.isVirtualNode=true;this.serialize_widgets=false;
      const host=document.createElement('div');document.body.append(host);
      const launcher=button('Open Sprite Studio',()=>this.studio.setExpanded(true));
      launcher.style.cssText='display:flex;align-items:center;justify-content:center;gap:10px;width:100%;padding:20px;background:#92502d;color:white;border:0;border-radius:8px;font-size:18px;cursor:pointer';
      this.addDOMWidget('sprite_studio','SPRITE_STUDIO',launcher,{serialize:false,hideOnZoom:false,getMinHeight:()=>70,getHeight:()=>70});
      this.studio=new StudioShell(host,this);this.studio.setExpanded(true);this.size=[450,160];this.color='#92502d';this.bgcolor='#2d2723';
      this.onRemoved=()=>this.studio.dispose();
    }
  }
  LiteGraph.registerNodeType(INTERFACE,SpriteStudioNode);
}

app.registerExtension({name:'MumbleboxSpriteStudio.Interface',registerCustomNodes:registerNode,setup(){
  registerNode();
  if(!document.getElementById('sprite-studio-presentation-style')){
    const style=document.createElement('style');style.id='sprite-studio-presentation-style';
    style.textContent='.sprite-studio-expanded{position:fixed!important;inset:52px 16px 16px 16px!important;transform:none!important;width:auto!important;height:auto!important;z-index:1000!important;pointer-events:auto!important;min-height:0!important}';document.head.append(style);
  }
},afterLoadGraph(){
  if(app.graph.extra?.sprite_studio && !app.graph._nodes.some(n=>n.type===INTERFACE))addStudioInterface();
}});

export function addStudioInterface() {
  registerNode();
  let node=app.graph._nodes.find(n=>n.type===INTERFACE);
  if(!node){node=LiteGraph.createNode(INTERFACE);node.pos=[0,80];app.graph.add(node);}
  app.graph.extra??={};app.graph.extra.sprite_studio={schema:1,interface_id:node.id};
  node.studio.setExpanded(true);app.graph.setDirtyCanvas(true,true);return node.id;
}
