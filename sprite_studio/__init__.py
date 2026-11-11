"""mumblebox Sprite Studio ComfyUI extension."""
import sys

from .features.refmods.nodes import RefModJoin
from .features.enhance.nodes import EnhanceResult
NODE_CLASS_MAPPINGS={'SpriteStudioRefModJoin':RefModJoin,'SpriteStudioEnhanceResult':EnhanceResult}
NODE_DISPLAY_NAME_MAPPINGS={'SpriteStudioRefModJoin':'Join independent still RefMods','SpriteStudioEnhanceResult':'Review enhanced prompt and device'}
WEB_DIRECTORY='./web'

# Pure contract tests import the same package outside the Comfy process.
if 'server' in sys.modules and getattr(sys.modules['server'].PromptServer,'instance',None):
    import folder_paths
    from comfy.cli_args import args
    from .api import register
    register(sys.modules['server'].PromptServer.instance,folder_paths,args.port)
