import {el,button,help,imageUrl} from '../../shell/controls.mjs';
import {request} from '../../shell/client.mjs';

export async function cropReview(shell,runId) {
  const review=await request('crop-review',undefined,{id:runId});
  const image=new Image();image.src=imageUrl(review.image);await image.decode();
  const section=el('section',{class:'crop-review'},el('h2',{},'Review and split the sheet'),help('Check identity, the requested view, left/right markings and a matching subject scale. Adjust cell edges below. Exports pad smaller crops; they never stretch, mirror or independently resize a view.'));
  const grid=el('div',{class:'crop-grid'});
  review.views.forEach((view,index)=>{
    const rectangle=review.rectangles[index];const canvas=el('canvas',{width:360,height:260,'aria-label':`${view.label} crop preview`});
    const draw=()=>{const [x1,y1,x2,y2]=rectangle;const ctx=canvas.getContext('2d');ctx.fillStyle='#777';ctx.fillRect(0,0,360,260);if(x2<=x1||y2<=y1)return;const scale=Math.min(360/(x2-x1),260/(y2-y1));ctx.drawImage(image,x1,y1,x2-x1,y2-y1,(360-(x2-x1)*scale)/2,(260-(y2-y1)*scale)/2,(x2-x1)*scale,(y2-y1)*scale);};
    const controls=el('div',{class:'crop-bounds'});
    ['Left','Top','Right','Bottom'].forEach((name,i)=>controls.append(el('label',{},name,el('input',{type:'number',min:0,max:review.size[i%2],value:rectangle[i],step:1,onchange:e=>{rectangle[i]=Number(e.target.value);draw();}}))));
    grid.append(el('article',{},el('h3',{},`${view.label} · ${view.azimuth}°`),canvas,controls));draw();
  });
  const checked=el('input',{type:'checkbox'}),result=el('div',{role:'status'});
  if(review.download)result.append(el('a',{href:review.download,download:`turnaround-${runId.slice(0,8)}.zip`},'Download the last exported views'));
  const exportButton=button('Export PNG views + manifest',async()=>{
    try{exportButton.disabled=true;const exported=await request('crop-export',{id:runId,rectangles:review.rectangles,reviewed:checked.checked});result.replaceChildren(el('a',{href:exported.download,download:`turnaround-${runId.slice(0,8)}.zip`},'Download the exported views'),help('The master image and your settings remain in Gallery. Camera angles in the manifest are requested, not measured.'));}catch(e){shell.message(e.message,true);}finally{exportButton.disabled=false;}
  },'primary');
  const name=el('input',{value:`Turnaround ${runId.slice(0,8)}`,maxLength:160,'aria-label':'Turnaround collection name'});
  const save=button('Save views to RefMods',async()=>{try{save.disabled=true;const item=await request('crop-library',{id:runId,rectangles:review.rectangles,reviewed:checked.checked,name:name.value});shell.message(`Saved ${item.references.length} views in “${item.name}”.`);}catch(e){shell.message(e.message,true);}finally{save.disabled=false;}});
  section.append(grid,el('label',{},checked,' I reviewed all views, identity, orientation and scale.'),el('div',{class:'actions'},exportButton),result,
    el('label',{class:'field-label'},'Reusable view collection',name),help('Saves these reviewed crops as separate reference pictures. The master remains in Gallery.'),save);
  return section;
}
