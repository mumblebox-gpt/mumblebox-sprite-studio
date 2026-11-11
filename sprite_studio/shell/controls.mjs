export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key.startsWith('on') && typeof value === 'function') node.addEventListener(key.slice(2), value);
    else if (key === 'class') node.className = value;
    else if (key in node && !key.startsWith('aria-')) node[key] = value;
    else node.setAttribute(key, value);
  }
  for (const child of children.flat(Infinity)) if (child != null) node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  return node;
}
export function setButtonLabel(node,label,name=iconName(label)){
  const symbol=icon(name),text=String(label).replace(/^[★☆]\s*/, '');
  if(/^[★☆]/.test(label)){node.setAttribute('aria-pressed',String(label.startsWith('★')));if(label.startsWith('★'))symbol.setAttribute('fill','currentColor');}
  node.replaceChildren(symbol,el('span',{class:'button-label'},text));
  return node;
}
export const button = (label, action, className = '', name) => setButtonLabel(el('button', {type:'button', class:className, onclick:action}),label,name);
export const help = text => el('small', {class:'help'}, text);
export function field(key, definition, value, change) {
  const id = `studio-${key}`;
  let input;
  if (definition.type === 'select') {
    input = el('select', {id}, definition.choices.map(([id, title]) => el('option', {value:id}, title)));
    input.value = value;
  } else {
    input = el('input', {id, type:definition.type === 'boolean' ? 'checkbox' : definition.type,
      ...(definition.type === 'boolean' ? {checked:value} : {value}),
      ...(definition.min != null ? {min:definition.min,max:definition.max,step:definition.step} : {})});
  }
  input.setAttribute('aria-describedby', `${id}-help`);
  let slider;
  if(definition.slider){
    slider=el('input',{type:'range',min:definition.min,max:definition.max,step:definition.step,value,'aria-label':definition.label+' slider'});
    slider.addEventListener('input',()=>{input.value=slider.value;change(Number(slider.value));});
  }
  input.addEventListener('change', () => {if(slider)slider.value=input.value;change(definition.type === 'boolean' ? input.checked : definition.type === 'number' ? Number(input.value) : input.value);});
  return el('div', {class:`field ${definition.type === 'boolean' ? 'toggle' : ''}`},
    el('label', {htmlFor:id}, definition.label), input, slider, el('small', {id:`${id}-help`,class:'help'}, definition.help));
}
export function imageUrl(image) {
  return `/view?${new URLSearchParams({filename:image.filename,subfolder:image.subfolder || '',type:image.type || 'output'})}`;
}
export const assetUrl = id => `/sprite-studio/v1/asset?id=${encodeURIComponent(id)}`;
import {icon,iconName} from './icons.mjs';
