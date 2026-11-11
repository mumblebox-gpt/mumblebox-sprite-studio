import {el,field,help} from '../../shell/controls.mjs';

export function turnaroundSettings(shell,draft,changed) {
  const config=draft.turnaround??={};
  const fields=shell.boot.turnaround_fields;
  const section=el('section',{},el('h2',{},'Views and consistency'),help('Camera values describe what we ask for. Review the actual angles, proportions and left/right details before using the sheet for 3D.'));
  const grid=el('div',{class:'settings-grid'});
  for(const [key,definition] of Object.entries(fields)) {
    if(config[key]===undefined)config[key]=definition.default;
    grid.append(field('turnaround-'+key,definition,config[key],value=>{config[key]=value;changed();}));
  }
  const custom=el('textarea',{rows:4,'aria-label':'Custom view angles',placeholder:'front, 0\nleft, 90\nback, 180\nright, 270',
    value:(config.views||[]).map(v=>`${v.label}, ${v.azimuth}`).join('\n'),onchange:e=>{
      config.views=e.target.value.trim().split('\n').filter(Boolean).map(line=>{const [label,angle]=line.split(',');return {label:label.trim().toLowerCase().replaceAll(' ','-'),azimuth:Number(angle)};});changed();}});
  section.append(grid,el('details',{},el('summary',{},'Custom view angles'),help('When Views is set to Custom, enter one view per line: its name, a comma, then its angle in degrees. Use 2–8 views and short unique names.'),custom));
  return section;
}
