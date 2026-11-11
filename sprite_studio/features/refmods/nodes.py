"""A typed list join missing from the upstream pack; extraction stays upstream."""
class RefModJoin:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{'mods_1':('H3_REF_MODS',)},'optional':{f'mods_{i}':('H3_REF_MODS',) for i in range(2,9)}}
    RETURN_TYPES=('H3_REF_MODS',)
    FUNCTION='join'
    CATEGORY='mumblebox/Sprite Studio'

    def join(self,mods_1,**others):
        result=list(mods_1)
        for i in range(2,9):result.extend(others.get(f'mods_{i}',[]))
        if not 1<=len(result)<=8:raise ValueError('A Studio bundle contains one to eight still references.')
        return (result,)
