"""Reviewed cell extraction; never independently resize or mirror views."""
import json
import math
from pathlib import Path
from PIL import Image


def default_crops(width,height,count,columns):
    rows=math.ceil(count/columns)
    return [[round(i%columns*width/columns),round(i//columns*height/rows),
             round((i%columns+1)*width/columns),round((i//columns+1)*height/rows)] for i in range(count)]


def validate_crops(rectangles,width,height,count):
    if not isinstance(rectangles,list) or len(rectangles)!=count: raise ValueError('Review one crop for each requested view.')
    clean=[]
    for rect in rectangles:
        if not isinstance(rect,list) or len(rect)!=4 or any(type(v) is not int for v in rect): raise ValueError('Crop bounds must be four whole pixel coordinates.')
        x1,y1,x2,y2=rect
        if not (0<=x1<x2<=width and 0<=y1<y2<=height): raise ValueError('Keep each crop inside the master image.')
        clean.append(rect[:])
    return clean


def export_images(source,destination,rectangles,views,camera):
    destination=Path(destination)
    with Image.open(source) as master:
        rectangles=validate_crops(rectangles,*master.size,len(views))
        target_size=(max(r[2]-r[0] for r in rectangles),max(r[3]-r[1] for r in rectangles))
        destination.mkdir(parents=True,exist_ok=False)
        manifest={'schema':1,'master_size':list(master.size),'camera':camera,'camera_provenance':'requested, not measured',
                  'independently_rescaled':False,'mirrored':False,'export_size':list(target_size),'views':[]}
        for view,rect in zip(views,rectangles):
            crop=master.crop(rect).convert('RGB')
            padded=Image.new('RGB',target_size,(200,200,200))
            offset=((target_size[0]-crop.width)//2,(target_size[1]-crop.height)//2)
            padded.paste(crop,offset)
            filename=view['label']+'.png'
            padded.save(destination/filename)
            manifest['views'].append({**view,'file':filename,'crop':rect,'padding_offset':list(offset)})
        (destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        return manifest
