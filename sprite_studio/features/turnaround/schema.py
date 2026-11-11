"""Camera requests and sheet layout, separate from inference settings."""
import math
import re

PRESETS={
    'cardinal':[('front',0),('left',90),('back',180),('right',270)],
    'presentation':[('front',0),('front-left-three-quarter',45),('left',90),('back',180)],
}
FIELDS={
    'preset':{'label':'Views','type':'select','default':'cardinal','choices':[['cardinal','Foundry cardinal · front, left, back, right'],['presentation','Presentation · front, ¾, side, back'],['custom','Custom angles']], 'help':'Cardinal views match the Foundry multiview order. Presentation adds a three-quarter angle. These are camera requests; inspect the result before export.'},
    'subject':{'label':'Subject type','type':'select','default':'character','choices':[['character','Character'],['vehicle','Vehicle / aircraft'],['object','Object / prop']], 'help':'Characters keep anatomy and clothing. Vehicles and objects keep rigid construction, proportions and asymmetry.'},
    'pose':{'label':'Pose','type':'select','default':'neutral','choices':[['neutral','Neutral stance'],['a-pose','A pose'],['t-pose','T pose'],['rigid','Rigid object']], 'help':'The same pose is requested in every view. Use a rigid pose for objects and aircraft.'},
    'columns':{'label':'Columns','type':'number','default':4,'min':1,'max':8,'step':1,'help':'Four columns makes one strip; two columns makes a 2 × 2 sheet. Allocate enough canvas pixels to each view.'},
    'projection':{'label':'Camera projection','type':'select','default':'perspective','choices':[['perspective','Long lens / weak perspective'],['orthographic','Orthographic']], 'help':'Long lens reduces perspective distortion. Orthographic asks for parallel projection; generated images may still deviate.'},
    'fov':{'label':'Requested field of view','type':'number','default':20,'min':5,'max':120,'step':1,'help':'Used for perspective only. A smaller angle resembles a longer lens and keeps proportions more even. Foundry uses 20°.'},
    'elevation':{'label':'Camera elevation','type':'number','default':0,'min':-80,'max':80,'step':1,'help':'0° is level with the subject. Positive looks down; negative looks up. All panels share this elevation.'},
    'locks':{'label':'Details to preserve','type':'text','default':'','help':'Name identifying details that must remain unchanged, including which side carries an accessory or marking.'},
}


def validate_turnaround(data):
    if not isinstance(data,dict): raise ValueError('Turnaround settings must be an object.')
    result={}
    for key,field in FIELDS.items():
        value=data.get(key,field['default'])
        if field['type']=='select':
            if value not in [c[0] for c in field['choices']]: raise ValueError(f"Choose a supported {field['label'].lower()}.")
        elif field['type']=='number':
            try: value=float(value)
            except (TypeError,ValueError): raise ValueError(f"{field['label']} needs a number.") from None
            if not math.isfinite(value) or value!=int(value) or not field['min']<=value<=field['max']:
                raise ValueError(f"{field['label']} is outside its supported range.")
            value=int(value)
        elif not isinstance(value,str) or len(value)>3000: raise ValueError('Keep detail locks under 3,000 characters.')
        result[key]=value
    if result['preset'] in PRESETS:
        views=[{'label':label,'azimuth':angle} for label,angle in PRESETS[result['preset']]]
    else:
        views=data.get('views',[])
        if not isinstance(views,list) or not 2<=len(views)<=8: raise ValueError('Choose between two and eight custom views.')
        clean=[]
        for view in views:
            if not isinstance(view,dict): raise ValueError('Each view needs a name and angle.')
            label=str(view.get('label',''))
            try: angle=float(view.get('azimuth'))
            except (TypeError,ValueError): raise ValueError('Each view needs a numeric angle.') from None
            if not re.fullmatch('[a-z0-9][a-z0-9-]{0,48}',label) or not math.isfinite(angle) or not 0<=angle<360:
                raise ValueError('Use short view names and angles from 0 to less than 360 degrees.')
            clean.append({'label':label,'azimuth':angle})
        views=clean
    if len({v['label'] for v in views})!=len(views): raise ValueError('View names must be unique.')
    if result['columns']>len(views): raise ValueError('Columns cannot exceed the number of views.')
    result['views']=views
    return result
