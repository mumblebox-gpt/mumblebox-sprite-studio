"""Gallery metadata and recoverable trash; recipes and files stay immutable."""
import re


class Gallery:
    def __init__(self,store): self.store=store

    def owned(self,run_id):
        if not re.fullmatch('[0-9a-f]{32}',str(run_id)): raise ValueError('Choose a Sprite Studio result.')
        run=self.store.get_run(run_id)
        if not run: raise ValueError('The result is unavailable.')
        return run

    def list(self,sort='newest',kind=None,offset=0,trashed=False,favorite=False):
        if kind not in (None,'create_image','turnaround'): raise ValueError('Unknown workflow filter.')
        runs=self.store.list_runs(sort=sort,kind=kind,offset=offset,trashed=trashed,favorite=favorite)
        return {'runs':runs,'offset':offset,'has_more':len(runs)==50}

    def update(self,run_id,patch):
        self.owned(run_id)
        if not isinstance(patch,dict) or set(patch)-{'name','favorite'}: raise ValueError('Only the result name and favorite can be changed.')
        fields=[];values=[]
        if 'name' in patch:
            if not isinstance(patch['name'],str) or len(patch['name'])>160: raise ValueError('Keep names under 160 characters.')
            fields.append('name=?');values.append(patch['name'].strip())
        if 'favorite' in patch:
            if type(patch['favorite']) is not bool: raise ValueError('Favorite must be on or off.')
            fields.append('favorite=?');values.append(int(patch['favorite']))
        if fields:
            with self.store.lock,self.store.db:
                self.store.db.execute('UPDATE runs SET '+','.join(fields)+' WHERE id=?',(*values,run_id))
        return self.owned(run_id)

    def trash(self,ids,trashed):
        if not isinstance(ids,list) or not 1<=len(ids)<=100 or type(trashed) is not bool: raise ValueError('Select between 1 and 100 results.')
        ids=list(dict.fromkeys(ids))
        with self.store.lock,self.store.db:
            for run_id in ids:
                run=self.owned(run_id)
                if run['status'] not in ('completed','failed','interrupted','canceled'): raise ValueError('Finish or cancel active jobs before moving them to Trash.')
            self.store.db.executemany('UPDATE runs SET trashed=? WHERE id=?',[(int(trashed),run_id) for run_id in ids])
        return {'ids':ids,'trashed':trashed,'files_preserved':True}
