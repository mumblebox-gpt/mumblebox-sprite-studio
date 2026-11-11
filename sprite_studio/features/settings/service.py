"""One owner for validated, persistent application preferences."""
DEFAULTS={'theme':'dark','font':100,'language':'en','last_tab':'create_image'}


class Settings:
    def __init__(self,store):self.store=store
    def get(self):return {**DEFAULTS,**self.store.get_document('settings','global',{})}

    def update(self,patch):
        if not isinstance(patch,dict) or set(patch)-set(DEFAULTS):raise ValueError('Unknown application setting.')
        with self.store.lock:
            result={**self.get(),**patch}
            if result['theme'] not in ('dark','light') or result['font'] not in (100,112,125,150,175,200) or result['language']!='en':
                raise ValueError('Choose an available theme, text size and language.')
            if result['last_tab'] not in ('create_image','turnaround','refmods','gallery','roadmap','about','settings'):raise ValueError('Unknown Studio tab.')
            self.store.put_document('settings','global',result)
            return result
