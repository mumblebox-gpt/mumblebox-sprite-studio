import {el,button,help,assetUrl} from '../../shell/controls.mjs';
import {request} from '../../shell/client.mjs';
import {libraryPicker} from '../refmods/picker.mjs';

export function referenceCards(shell,draft,changed) {
  const list=el('div',{class:'references'});
  const redraw=()=>{
    list.replaceChildren();
    draft.references.forEach((card,index)=>{
      const role=el('select',{'aria-label':`Reference ${index+1} role`}, Object.entries(shell.boot.roles).map(([id,[title]])=>el('option',{value:id},title)));
      role.value=card.role || 'identity';
      role.onchange=()=>{card.role=role.value;changed();};
      const note=el('textarea',{value:card.note || '',rows:2,placeholder:'What should this picture contribute?', 'aria-label':`Reference ${index+1} instruction`,oninput:e=>{card.note=e.target.value;changed();}});
      const enabled=el('input',{type:'checkbox',checked:card.enabled !== false,onchange:e=>{card.enabled=e.target.checked;changed();}});
      const move=direction=>{const target=index+direction;if(target<0||target>=draft.references.length)return;[draft.references[index],draft.references[target]]=[draft.references[target],draft.references[index]];changed();redraw();};
      const replacement=el('input',{type:'file',accept:'image/png,image/jpeg,image/webp,image/bmp,image/tiff',hidden:true,onchange:async e=>{
        const file=e.target.files[0];if(!file)return;
        try{const data=new FormData();data.append('image',file);const asset=await request('upload',data);card.asset_id=asset.id;changed();redraw();}catch(error){shell.message(error.message,true);}
      }});
      list.append(el('article',{class:`reference ${card.enabled === false ? 'disabled' : ''}`},
        el('img',{src:assetUrl(card.asset_id),alt:`Reference ${index+1}`}),
        el('div',{},el('label',{},enabled,`Use reference ${index+1}`),role,note,
          el('div',{class:'actions'},button('Replace picture',()=>replacement.click()),replacement,button('Earlier',()=>move(-1)),button('Later',()=>move(1)),button('Remove',()=>{draft.references.splice(index,1);changed();redraw();})))));
    });
  };
  const input=el('input',{type:'file',accept:'image/png,image/jpeg,image/webp,image/bmp,image/tiff',multiple:true,hidden:true});
  const upload=async files=>{
    try {
      for(const file of files) {
        if(draft.references.length>=32||draft.references.filter(c=>c.enabled!==false).length>=8)throw Error('Use up to eight enabled references. Disable or remove a card before adding another.');
        const data=new FormData();data.append('image',file);
        const asset=await request('upload',data);
        draft.references.push({asset_id:asset.id,role:'identity',note:'',enabled:true});
        changed();redraw();
      }
      changed();redraw();
    } catch(error) { shell.message(error.message,true); }
  };
  input.onchange=async()=>{await upload(input.files);input.value='';};
  const zone=el('div',{class:'drop-zone',ondragover:e=>{e.preventDefault();zone.classList.add('drag');},ondragleave:()=>zone.classList.remove('drag'),ondrop:e=>{e.preventDefault();zone.classList.remove('drag');upload(e.dataTransfer.files);}},
    el('strong',{},'References'),help('Drop pictures here or choose files. Instructions beside each picture become part of the prompt.'),
    button('Upload references',()=>input.click()),button('Add from RefMods',()=>{zone.querySelector('.library-picker')?.remove();zone.append(libraryPicker(shell,async cards=>{
      if(draft.references.length+cards.length>32||draft.references.filter(c=>c.enabled!==false).length+cards.length>8)throw Error('This would exceed eight enabled references. Disable or remove a card first.');
      draft.references.push(...cards);changed();redraw();
    }));}),input,list);
  redraw(); return zone;
}
