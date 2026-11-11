// Small original SVG symbols. One shared style and semantic lookup for Studio actions.
const paths={
  spark:'m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5Z',
  image:'M3 3h18v18H3ZM3 17l6-6 4 4 3-3 5 5M16 7h.01',
  turn:'M4 8a8 8 0 0 1 14-2l3 3M21 3v6h-6M20 16a8 8 0 0 1-14 2l-3-3M3 21v-6h6',
  library:'M4 3h5v18H4ZM11 3h4v18h-4ZM17 4l3-1 3 17-3 1Z',
  gallery:'M4 3h17v15H4ZM1 7v15h16M5 15l5-6 4 4 3-3 3 5',
  map:'M3 5l6-2 6 2 6-2v16l-6 2-6-2-6 2ZM9 3v16M15 5v16',
  info:'M12 8h.01M12 11v6M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20',
  settings:'M4 6h16M4 12h16M4 18h16M8 3v6M16 9v6M10 15v6',
  sun:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 1v3M12 20v3M1 12h3M20 12h3M4 4l2 2M18 18l2 2M20 4l-2 2M6 18l-2 2',
  moon:'M20 15A9 9 0 0 1 9 4a9 9 0 1 0 11 11Z',
  help:'M9 8a3 3 0 1 1 5 2c-2 1-2 2-2 3M12 17h.01M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20',
  refresh:'M20 9a8 8 0 1 0 0 6M20 3v6h-6',
  graph:'M2 3h6v6H2ZM16 3h6v6h-6ZM9 15h6v6H9ZM5 9v3h14V9M12 12v3',
  unload:'M4 4h16v6H4ZM4 14h4v6H4M20 14h-4v6h4M12 12v10m-3-3 3 3 3-3',
  play:'m7 3 14 9-14 9Z',
  stop:'M5 5h14v14H5Z',
  check:'m4 12 5 5L20 6',
  close:'m5 5 14 14M19 5 5 19',
  upload:'M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5',
  download:'M12 3v13m-5-5 5 5 5-5M4 16v5h16v-5',
  plus:'M12 4v16M4 12h16',
  trash:'M4 6h16M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7M14 10v7',
  undo:'M8 4 3 9l5 5M3 9h10a7 7 0 0 1 0 14',
  left:'m14 5-7 7 7 7',
  right:'m10 5 7 7-7 7',
  up:'m5 14 7-7 7 7',
  down:'m5 10 7 7 7-7',
  eye:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12ZM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6',
  compare:'M3 4h7v16H3ZM14 4h7v16h-7M12 2v20',
  star:'m12 2 3 6 7 1-5 5 1 8-6-4-6 4 1-8-5-5 7-1Z',
  save:'M3 3h15l3 3v15H3ZM7 3v6h10V3M7 21v-8h10v8',
  edit:'m4 16 12-12 4 4L8 20l-5 1ZM13 7l4 4',
  crop:'M7 2v15h15M2 7h15v15',
  seed:'M12 21v-9M12 14C3 14 3 5 3 5s9 0 9 9ZM12 11c0-8 9-9 9-9s0 9-9 9',
};

export function iconName(label){
  const text=String(label).toLowerCase();
  const rules=[[/favorite/,'star'],[/light theme/,'sun'],[/dark theme/,'moon'],[/trash|purge|remove/,'trash'],
    [/restore|undo|discard/,'undo'],[/cancel/,'stop'],[/close/,'close'],[/accept/,'check'],
    [/^earlier/,'up'],[/^later/,'down'],[/^previous/,'left'],[/^next/,'right'],
    [/enhance|try again/,'spark'],[/reset|updates|refresh|replace/,'refresh'],[/unload/,'unload'],
    [/show graph/,'graph'],[/settings/,'settings'],[/support/,'help'],[/about/,'info'],[/roadmap/,'map'],
    [/compare/,'compare'],[/preview|review/,'eye'],[/export|download/,'download'],[/import|upload/,'upload'],
    [/save/,'save'],[/edit/,'edit'],[/seed/,'seed'],[/add/,'plus'],[/gallery/,'gallery'],
    [/turnaround/,'turn'],[/refmod|collection/,'library'],[/create image|image reference|decode/,'image'],
    [/generate/,'play'],[/open sprite studio/,'spark']];
  return rules.find(([pattern])=>pattern.test(text))?.[1]||'right';
}

export function icon(name){
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg'),path=document.createElementNS(ns,'path');
  for(const [key,value] of Object.entries({viewBox:'0 0 24 24',width:18,height:18,fill:'none',stroke:'currentColor','stroke-width':1.7,'stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true',focusable:'false',class:'button-icon'}))svg.setAttribute(key,String(value));
  path.setAttribute('d',paths[name]||paths.right);svg.append(path);return svg;
}
