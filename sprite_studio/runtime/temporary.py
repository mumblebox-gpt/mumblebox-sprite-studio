"""Purge only this application's leased scratch folders, never model or asset roots."""
from contextlib import contextmanager
from pathlib import Path
import re
import threading
import uuid


class TemporaryFiles:
    def __init__(self,root):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.active=set();self.lock=threading.RLock()

    @contextmanager
    def lease(self):
        with self.lock:
            ident=uuid.uuid4().hex;path=self.root/ident;path.mkdir();self.active.add(ident)
        try: yield path
        finally:
            with self.lock:self.active.discard(ident)

    def _entries(self):
        files=[];directories=[];count=0
        for group in self.root.iterdir():
            if not re.fullmatch('[0-9a-f]{32}',group.name) or group.name in self.active or not group.is_dir():continue
            stack=[group]
            while stack:
                path=stack.pop();count+=1
                if count>10000:raise ValueError('Temporary inventory is too large for one purge. No files were removed.')
                if path.is_symlink() or path.is_junction():continue
                resolved=path.resolve()
                if not resolved.is_relative_to(self.root):raise ValueError('Temporary path escaped its owned folder.')
                if path.is_dir():directories.append(path);stack.extend(path.iterdir())
                elif path.is_file():files.append((path,path.stat().st_size))
        return files,directories

    def inventory(self):
        with self.lock:
            files,_=self._entries()
            return {'files':len(files),'bytes':sum(size for _,size in files),'active_folders':len(self.active)}

    def purge(self):
        with self.lock:
            files,directories=self._entries();removed=0;size=0
            for path,length in files:
                if path.is_symlink() or not path.resolve().is_relative_to(self.root):raise ValueError('Temporary file changed during purge.')
                path.unlink();removed+=1;size+=length
            for path in sorted(directories,key=lambda p:len(p.parts),reverse=True):
                try:path.rmdir()
                except OSError:pass
            return {'files':removed,'bytes':size,'active_folders':len(self.active)}
