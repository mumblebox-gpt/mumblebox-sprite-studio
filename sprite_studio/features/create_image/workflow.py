"""Native publisher recipe; this owner keeps branch IDs and wiring together."""
from .prompt import build_prompt
from ..references.model import active_cards


def model_names(profile):
    suffix = 'w4a8' if profile=='w4a8' else 'int8_convrot'
    return {'diffusion_models': f'p-h3-image_{suffix}.safetensors', 'text_encoders': f'p-h3-image_text_encoder_{suffix}.safetensors', 'vae': 'p-h3-image_vae_int8_convrot.safetensors'}


def build_prompt_graph(recipe, reference_files, run_id):
    if len(reference_files) != len(active_cards(recipe)):
        raise ValueError('Reference pictures and instructions are out of sync.')
    base = 100 if recipe['kind']=='create_image' else 300
    def ident(offset): return str(base+offset)
    def link(offset, output=0): return [ident(offset), output]
    graph = {}
    def node(offset, kind, title, **inputs):
        graph[ident(offset)] = {'class_type':kind,'inputs':inputs,'_meta':{'title':title}}
    names = model_names(recipe['profile'])
    node(1,'UNETLoader','P-H3 diffusion · '+recipe['profile'],unet_name=names['diffusion_models'],weight_dtype='default')
    node(2,'CLIPLoader','P-H3 text and vision encoder',clip_name=names['text_encoders'],type='minimax',device='default')
    node(3,'VAELoader','P-H3 image VAE',vae_name=names['vae'])
    node(4,'MiniMaxH3SigmaShift','Sampling shifts',model=link(1),shift_video=recipe['shift_video'],shift_audio=recipe['shift_audio'])
    inputs = {'clip':link(2),'vae':link(3),'prompt':build_prompt(recipe),'width':recipe['width'],'height':recipe['height']}
    if not recipe['anchor_references']:inputs.pop('vae')
    for i, filename in enumerate(reference_files):
        node(20+i,'LoadImage',f'Reference {i+1}',image=filename)
        inputs[f'images.image_{i+1}'] = link(20+i)
    if recipe['upsample']:
        suffix='w4a8' if recipe['upsampler_precision']=='w4a8' else 'int8_convrot'
        node(40,'CLIPLoader','Official P-H3 prompt upsampler',clip_name=f'p-h3-image_prompt_upsampler_{suffix}.safetensors',type='minimax',device='default')
        helper={'clip':link(40),'prompt':build_prompt(recipe),'max_length':recipe['upsampler_tokens'],
                'sampling_mode':'on' if recipe['upsampler_sampling'] else 'off','thinking':recipe['upsampler_thinking'],
                'use_default_template':recipe['upsampler_default_template'],'mtp':recipe['upsampler_mtp']}
        if recipe['upsampler_sampling']:
            for key in ('temperature','top_k','top_p','min_p','repetition_penalty','presence_penalty','seed'):
                helper[f'sampling_mode.{key}']=int(recipe['upsampler_seed']) if key=='seed' else recipe[f'upsampler_{key}']
        if recipe['upsampler_system_prompt'].strip():
            node(43,'PrimitiveStringMultiline','Helper instruction override',value=recipe['upsampler_system_prompt'])
            helper['system_prompt']=link(43)
        for i in range(len(reference_files)): helper[f'images.image{i+1}']=link(20+i)
        node(41,'TextGenerateV2','Expand prompt using the official helper',**helper)
        node(42,'PreviewAny','Actual generation prompt',source=link(41))
        inputs['prompt']=link(41)
    node(5,'PH3ImageConditioning','Prompt and reference anchors',**inputs)
    node(6,'RandomNoise','Saved seed',noise_seed=int(recipe['seed']))
    node(7,'BasicGuider','P-H3 guidance',model=link(4),conditioning=link(5))
    node(8,'KSamplerSelect','Sampler',sampler_name=recipe['sampler'])
    node(9,'ManualSigmas','Distilled noise schedule',sigmas=recipe['sigmas'])
    node(10,'SamplerCustomAdvanced','Generate image',noise=link(6),guider=link(7),sampler=link(8),sigmas=link(9),latent_image=link(5,1))
    if recipe['decode_mode']=='tiled':
        node(11,'VAEDecodeTiled','Decode image in tiles',samples=link(10),vae=link(3),tile_size=recipe['tile_size'],overlap=recipe['tile_overlap'],temporal_size=64,temporal_overlap=8)
    else:node(11,'VAEDecode','Decode image',samples=link(10),vae=link(3))
    node(12,'SaveImage','Save master',images=link(11),filename_prefix=f'sprite_studio/{run_id}/master')
    return graph
