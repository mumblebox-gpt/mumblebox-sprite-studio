"""Still-reference extraction controls; no video or diffusion controls."""
import math
from ..references.model import validate_cards, active_cards

VAE='minimax_h3_video_vae_int8_convrot.safetensors'
FIELDS={
    'mode':{'label':'Reference detail','type':'select','default':'Full Reference','choices':[['Full Reference','Full Reference · identity default'],['Compressed Reference','Compressed Reference · smaller, softer detail']], 'help':'Full keeps the encoded picture. Compressed pools it into a smaller grid and can lose facial or construction details.'},
    'concept_type':{'label':'Reference category','type':'select','default':'identity','choices':[[s,s.replace('_',' ').title()] for s in ('identity','generic','clothing','background','style')], 'help':'Describes what you are saving. This is metadata, not a training mode or a strength control.'},
    'ref_resolution':{'label':'Reference resolution','type':'number','default':1024,'min':256,'max':2048,'step':64,'help':'Short-edge ceiling before encoding. Larger preserves more detail and costs more memory; small pictures are not enlarged.'},
    'pool_h':{'label':'Compressed grid height','type':'number','default':32,'min':2,'max':64,'step':2,'advanced':True,'help':'Compressed mode only. A larger grid preserves more structure; 32 is a useful detail starting point.'},
    'pool_w':{'label':'Compressed grid width','type':'number','default':32,'min':2,'max':64,'step':2,'advanced':True,'help':'Compressed mode only. The upstream extractor fits the grid to each picture’s shape.'},
    'identity':{'label':'Refinement steps','type':'number','default':0,'min':0,'max':2000,'step':50,'advanced':True,'help':'Compressed mode only. More steps reduce reconstruction error but take longer. This does not train the image model.'},
    'max_tokens':{'label':'Token budget per picture','type':'number','default':5120,'min':0,'max':32768,'step':512,'advanced':True,'help':'Stops extraction if a picture exceeds this budget. Zero removes the cap. Pictures are never silently discarded.'},
}


def validate(data):
    if not isinstance(data,dict): raise ValueError('Provide RefMod settings.')
    name=str(data.get('prompt','')).strip()
    if not 1<=len(name)<=160: raise ValueError('Give the reference a name of up to 160 characters.')
    settings=data.get('refmod',{})
    if not isinstance(settings,dict): raise ValueError('Provide RefMod extraction settings.')
    clean={}
    for key,field in FIELDS.items():
        value=settings.get(key,field['default'])
        if field['type']=='select':
            if value not in [x[0] for x in field['choices']]:raise ValueError(f'Choose a supported {field["label"]}.')
        else:
            if type(value) not in (int,float) or not math.isfinite(value) or value!=int(value) or not field['min']<=value<=field['max'] or value%field['step']:
                raise ValueError(f'{field["label"]} is outside its supported range or increment.')
            value=int(value)
        clean[key]=value
    recipe={'schema':1,'kind':'refmod','prompt':name,'profile':'int8','width':settings.get('ref_resolution',1024),'height':settings.get('ref_resolution',1024),
            'seed':'0','references':validate_cards(data.get('references',[])),'refmod':clean,
            'notes':str(data.get('notes',''))[:3000],'tags':str(data.get('tags',''))[:500],
            'operation':data.get('operation','create')}
    if recipe['operation'] not in ('create','decode'):raise ValueError('Choose Create or Decode.')
    if recipe['operation']=='create' and not active_cards(recipe):raise ValueError('Add at least one reference picture.')
    return recipe
