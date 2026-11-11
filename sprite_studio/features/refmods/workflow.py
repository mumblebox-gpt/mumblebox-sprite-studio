"""Independent 500-series native/upstream branch for still RefMods."""
from .schema import VAE


def build_graph(recipe,files,run_id):
    def node(kind,**inputs):return {'class_type':kind,'inputs':inputs}
    graph={'501':node('VAELoader',vae_name=VAE)}
    if recipe['operation']=='decode':
        inputs={'show_info':False,'max_total_tokens':32768}
        for i in range(1,9):inputs.update({f'mod_{i}':recipe['mod_name'] if i==1 else '(none)',f'strength_{i}':1.0,f'copies_{i}':1})
        graph['502']=node('MiniMaxH3RefModsLoader',**inputs)
        for i in range(recipe['member_count']):
            graph[str(520+i)]=node('MiniMaxH3RefModInspect',mods=['502',0],index=i,preview='stored',strength=1.0,vae=['501',0],visual_preview='first_frame')
            graph[str(580+i)]=node('SaveImage',images=[str(520+i),1],filename_prefix=f'sprite_studio/{run_id}/ref_{i+1}')
        return graph
    extracted=[]
    for i,filename in enumerate(files):
        load=str(540+i);extract='502' if i==0 else str(520+i)
        graph[load]=node('LoadImage',image=filename)
        graph[extract]=node('MiniMaxH3RefModExtract',**recipe['refmod'],name=f'{recipe["prompt"]} {i+1}',vae=['501',0],
            **{'refs_image.ref_image_1':[load,0]},latent_frames=1,merge=False,motion_only=False,multiplier=1,
            background_retention=0,extraction_preset='manual',subfolder='sprite_studio',description=recipe['notes'],save=False,budget_policy='error')
        extracted.append([extract,0])
    graph['504']=node('SpriteStudioRefModJoin',**{f'mods_{i+1}':value for i,value in enumerate(extracted)})
    graph['503']=node('MiniMaxH3RefModBundleSave',mods=['504',0],name=run_id,subfolder='sprite_studio')
    graph['590']=node('SaveImage',images=['540',0],filename_prefix=f'sprite_studio/{run_id}/reference')
    return graph
