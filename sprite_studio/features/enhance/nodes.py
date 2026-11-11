"""Record native generation output and its actual Comfy execution device; no inference here."""

class EnhanceResult:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{'clip':('CLIP',),'text':('STRING',{'forceInput':True})}}
    RETURN_TYPES=()
    FUNCTION='record'
    OUTPUT_NODE=True
    CATEGORY='Sprite Studio'

    def record(self,clip,text):
        return {'ui':{'text':[text],'device':[str(clip.patcher.load_device)]}}
