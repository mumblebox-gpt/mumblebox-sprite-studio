import {el,button,help,assetUrl} from '../../shell/controls.mjs';
import {request} from '../../shell/client.mjs';

export function libraryPicker(shell,add) {
  const section=el('section',{class:'library-picker'},el('h3',{},'Choose reference pictures'));
  const items=el('div',{class:'reference-choices'}),status=el('span',{}),selected=new Map();let offset=0,hasMore=false;
  const report=e=>shell.message(e.message,true);
  const load=async()=>{
    try{const result=await request('refmods',undefined,{offset:String(offset)});hasMore=result.has_more;items.replaceChildren();
      for(const item of result.items){
        const cards=el('div',{class:'reference-choices'});
        item.references.forEach((card,index)=>{const key=`${item.id}:${index}`,check=el('input',{type:'checkbox',checked:selected.has(key),onchange:e=>{e.target.checked?selected.set(key,{id:item.id,index}):selected.delete(key);status.textContent=`${selected.size} pictures selected`;}});
          cards.append(el('label',{class:'reference-choice'},check,el('img',{src:assetUrl(card.asset_id),alt:`${item.name} picture ${index+1}`}),`${index+1} · ${card.role}`));});
        items.append(el('article',{},el('strong',{},item.name),help(item.kind==='refmod'?'Encoded RefMod · original/decoded pictures used for P-H3':'Reference collection'),cards,
          item.references.length?null:help('Open RefMods and decode this latent-only entry first.')));
      }
      previous.disabled=offset===0;next.disabled=!hasMore;
    }catch(e){report(e);}
  };
  const previous=button('Previous entries',()=>{offset=Math.max(0,offset-50);load();}),next=button('Next entries',()=>{offset+=50;load();});
  section.append(items,el('div',{class:'actions'},previous,next,status,button('Add selected pictures',async()=>{
    try{if(!selected.size||selected.size>8)throw Error('Choose one to eight pictures.');const grouped=new Map();for(const value of selected.values()){if(!grouped.has(value.id))grouped.set(value.id,[]);grouped.get(value.id).push(value.index);}
      const cards=[];for(const [id,indices] of grouped)cards.push(...(await request('refmod-select',{id,indices})).references);await add(cards);section.remove();
    }catch(e){report(e);}
  },'primary'),button('Close picker',()=>section.remove())));
  load();return section;
}
