"""Authoritative settings, defaults and plain-language descriptions."""
import math
import secrets
from ..references.model import validate_cards

SIGMAS = '1.0, 0.984753, 0.967905, 0.951688, 0.925372, 0.881923, 0.810083, 0.528718, 0.0'
FIELDS = {
    'profile': {'label': 'Model precision', 'type': 'select', 'default': 'w4a8', 'choices': [['w4a8','4-bit · smaller memory footprint'],['int8','8-bit · closer to original detail']], 'help': 'Both use P-H3. 4-bit needs less memory; 8-bit may preserve more detail. Missing files download when you generate.'},
    'width': {'label': 'Width', 'type': 'number', 'default': 1024, 'min': 256, 'max': 8192, 'step': 32, 'help': 'Output width in pixels. Larger images need more memory and time. Use multiples of 32.'},
    'height': {'label': 'Height', 'type': 'number', 'default': 1024, 'min': 256, 'max': 8192, 'step': 32, 'help': 'Output height in pixels. Width × height sets the total work; a sheet shares its pixels between views.'},
    'seed_mode': {'label': 'Seed behavior', 'type': 'select', 'default': 'random', 'choices': [['random','New variation'],['fixed','Use this seed']], 'help': 'New variation chooses new starting noise. A fixed seed helps repeat the same recipe; other changed settings can still change the image.'},
    'seed': {'label': 'Seed', 'type': 'text', 'default': '42', 'help': 'Starting noise number, saved exactly with each result including large 64-bit values.'},
    'sampler': {'label': 'Sampler', 'type': 'select', 'default': 'euler', 'advanced': True, 'choices': [['euler','Euler · publisher baseline'],['er_sde','ER SDE · alternate template']], 'help': 'How the model follows the noise schedule. Euler matches our baseline; alternatives can change detail and consistency.'},
    'sigmas': {'label': 'Noise schedule', 'type': 'text', 'default': SIGMAS, 'advanced': True, 'help': 'Nine numbers describe eight sampling steps. This distilled model was designed for this schedule. Custom values can reduce quality.'},
    'shift_video': {'label': 'Image noise shift', 'type': 'number', 'default': 1.0, 'min': 0.1, 'max': 20, 'step': 0.1, 'advanced': True, 'help': 'Balances early and late denoising. Keep 1 for P-H3; larger is not automatically better.'},
    'shift_audio': {'label': 'Companion latent shift', 'type': 'number', 'default': 1.0, 'min': 0.1, 'max': 20, 'step': 0.1, 'advanced': True, 'help': 'H3 retains companion latents internally for stills. Keep 1; this does not add sound.'},
    'upsample': {'label': 'P-H3 prompt upsampler', 'type': 'boolean', 'default': False, 'help': 'Uses the official separate helper to expand your prompt. Adds model loading and may add details; leave off for exact turnaround wording.'},
    'upsampler_precision': {'label': 'Upsampler precision', 'type': 'select', 'default': 'w4a8', 'advanced': True, 'choices': [['w4a8','4-bit'],['int8','8-bit']], 'help': 'The helper has its own precision. 4-bit uses less memory; 8-bit can produce different wording.'},
    'upsampler_tokens': {'label': 'Upsampler output limit', 'type': 'number', 'default': 2048, 'min': 256, 'max': 8192, 'step': 256, 'advanced': True, 'help': 'Maximum helper tokens including thinking. Higher gives more room to finish but can take longer.'},
    'upsampler_thinking': {'label': 'Upsampler thinking', 'type': 'boolean', 'default': True, 'advanced': True, 'help': 'Lets the helper reason before writing. Off may be quicker, but wording can change.'},
    'anchor_references': {'label':'Anchor reference shapes','type':'boolean','default':True,'advanced':True,'help':'Encodes pictures as visual reference latents as well as text/vision context. Leave on for identity and geometry; off uses only the vision encoder’s understanding.'},
    'decode_mode': {'label':'Image decoding','type':'select','default':'auto','advanced':True,'choices':[['auto','Native automatic'],['tiled','Tiled decoding']], 'help':'Automatic uses the VAE’s normal memory handling. Tiled uses smaller overlapping regions to reduce decode memory; seams or fine detail can change.'},
    'tile_size': {'label':'Decode tile size','type':'number','default':512,'min':64,'max':4096,'step':32,'advanced':True,'help':'Tiled mode only. Smaller tiles use less memory but require more work. Larger tiles can preserve more context.'},
    'tile_overlap': {'label':'Decode tile overlap','type':'number','default':64,'min':0,'max':4064,'step':32,'advanced':True,'help':'Tiled mode only. Overlap blends tile edges; more overlap can hide seams but adds work. Keep below the tile size.'},
    'upsampler_sampling': {'label':'Upsampler variation','type':'boolean','default':False,'advanced':True,'help':'Off uses greedy wording. On samples alternate wording with the helper controls below; it does not change the image’s noise seed.'},
    'upsampler_seed': {'label':'Upsampler seed','type':'text','default':'42','advanced':True,'help':'Separate starting number for sampled helper wording. Saved exactly as a 64-bit number. Used only when Upsampler variation is on.'},
    'upsampler_temperature': {'label':'Upsampler creativity','type':'number','default':0.7,'min':0.01,'max':2,'step':0.01,'advanced':True,'slider':True,'help':'Variation on only. Lower favors predictable words; higher allows more unexpected wording and may drift from your brief.'},
    'upsampler_top_k': {'label':'Upsampler word shortlist','type':'number','default':64,'min':0,'max':1000,'step':1,'advanced':True,'help':'Variation on only. Limits each word choice to this many candidates; zero removes this limit.'},
    'upsampler_top_p': {'label':'Upsampler probability coverage','type':'number','default':0.95,'min':0,'max':1,'step':0.01,'advanced':True,'slider':True,'help':'Variation on only. Lower narrows the likely word choices; one keeps the full probability range.'},
    'upsampler_min_p': {'label':'Upsampler rare-word cutoff','type':'number','default':0.05,'min':0,'max':1,'step':0.01,'advanced':True,'slider':True,'help':'Variation on only. Higher filters out less likely words more strongly; zero disables this filter.'},
    'upsampler_repetition_penalty': {'label':'Upsampler repetition penalty','type':'number','default':1.05,'min':0,'max':5,'step':0.01,'advanced':True,'help':'Variation on only. One is neutral; values above one discourage repeated wording. Large values can damage fluency.'},
    'upsampler_presence_penalty': {'label':'Upsampler repeated-topic penalty','type':'number','default':0,'min':0,'max':5,'step':0.01,'advanced':True,'help':'Variation on only. Zero is neutral; larger values discourage words already used and may introduce new topics.'},
    'upsampler_mtp': {'label':'Upsampler speculative decoding','type':'select','default':'auto','advanced':True,'choices':[[v,v] for v in ('auto','off','2','3','4','5','tree2s1','tree2s2','tree3s1','tree4s1m8')], 'help':'Auto adapts optional multi-token prediction for speed when weights support it. Off is the simplest path; fixed depths and tree modes are experimental speed controls.'},
    'upsampler_default_template': {'label':'Use official helper template','type':'boolean','default':True,'advanced':True,'help':'Keeps the model’s built-in prompting instructions. Leave on for normal use; off passes your text without that template.'},
    'upsampler_system_prompt': {'label':'Helper system instruction override','type':'text','default':'','advanced':True,'help':'Blank uses the official instructions. Advanced users can replace the helper’s system instruction when the default template is enabled.'},
}


def validate_recipe(data):
    if not isinstance(data, dict):
        raise ValueError('Generation settings must be an object.')
    result = {'schema': 1, 'kind': data.get('kind', 'create_image')}
    if result['kind'] not in ('create_image', 'turnaround'):
        raise ValueError('Choose an image or turnaround workflow.')
    prompt = str(data.get('prompt', '')).strip()
    if not prompt or len(prompt) > 16000:
        raise ValueError('Enter a prompt between 1 and 16,000 characters.')
    result['prompt'] = prompt
    for key, field in FIELDS.items():
        value = data.get(key, field['default'])
        if field['type'] == 'number':
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"{field['label']} must be a number.") from None
            if not math.isfinite(value) or not field['min'] <= value <= field['max']:
                raise ValueError(f"{field['label']} must be between {field['min']} and {field['max']}.")
            if field['step']>=1:
                if value != int(value) or value % field['step']:
                    raise ValueError(f"{field['label']} must use increments of {field['step']}.")
                value = int(value)
        elif field['type'] == 'select' and value not in [x[0] for x in field['choices']]:
            raise ValueError(f"Choose a supported {field['label'].lower()}.")
        elif field['type'] == 'boolean' and not isinstance(value, bool):
            raise ValueError(f"{field['label']} must be on or off.")
        result[key] = value
    if result['width']*result['height'] > 8_388_608:
        raise ValueError('Keep the canvas at or below 8 megapixels.')
    for key in ('seed','upsampler_seed'):
        try:seed=int(str(result[key]))
        except (TypeError,ValueError):raise ValueError(f'{FIELDS[key]["label"]} must be a whole number.') from None
        if not 0<=seed<=2**64-1:raise ValueError(f'{FIELDS[key]["label"]} must fit an unsigned 64-bit number.')
        result[key]=str(seed)
    if not isinstance(result['upsampler_system_prompt'],str) or len(result['upsampler_system_prompt'])>16000:raise ValueError('Keep helper instructions under 16,000 characters.')
    if result['decode_mode']=='tiled' and result['tile_overlap']>=result['tile_size']:raise ValueError('Tile overlap must be smaller than the tile size.')
    try:
        sigmas = [float(s.strip()) for s in str(result['sigmas']).split(',')]
    except ValueError:
        raise ValueError('Noise schedule needs comma-separated numbers.') from None
    if not 2 <= len(sigmas) <= 65 or sigmas[0] != 1 or sigmas[-1] != 0 or any(not math.isfinite(x) for x in sigmas) or any(a <= b for a,b in zip(sigmas,sigmas[1:])):
        raise ValueError('Noise schedule must descend from 1 to 0 without repeats.')
    result['sigmas'] = ', '.join(str(s) for s in sigmas)
    result['references'] = validate_cards(data.get('references', []))
    result['original_prompt'] = str(data.get('original_prompt',prompt))[:16000]
    result['accepted_enhancement'] = str(data.get('accepted_enhancement',''))[:16000]
    if result['kind']=='turnaround':
        from ..turnaround.schema import validate_turnaround
        result['turnaround']=validate_turnaround(data.get('turnaround',{}))
    return result


def freeze_seed(recipe):
    return {**recipe, 'seed': str(secrets.randbits(64)) if recipe['seed_mode']=='random' else recipe['seed']}
