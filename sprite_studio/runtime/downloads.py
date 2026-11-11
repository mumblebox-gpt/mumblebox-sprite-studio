"""Verified resumable first-use transfers; no downloads happen on import."""
import hashlib
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from ..storage import safe_path

CHUNK=4*1024*1024


def sha256(path,cancel,progress):
    digest=hashlib.sha256()
    total=path.stat().st_size
    count=0
    with path.open('rb') as stream:
        while data:=stream.read(CHUNK):
            if cancel.is_set(): raise InterruptedError('Verification canceled; downloaded data retained.')
            digest.update(data)
            count+=len(data)
            progress({'stage':'verifying','file':path.name,'bytes':count,'total':total})
    return digest.hexdigest()


def download_file(spec,model_root,progress,cancel):
    target=safe_path(model_root,spec['path'])
    if not re.fullmatch('[0-9a-f]{64}',spec['sha256']) or not isinstance(spec['size'],int) or spec['size']<=0:
        raise ValueError('Invalid model manifest.')
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if target.stat().st_size==spec['size'] and sha256(target,cancel,progress)==spec['sha256']:
            progress({'stage':'ready','file':target.name,'bytes':spec['size'],'total':spec['size']})
            return target
        raise ValueError(f'{target.name} exists but does not match the expected model. It was preserved; select the correct model or relocate it.')
    partial=target.with_suffix(target.suffix+'.part')
    if partial.exists() and partial.stat().st_size>spec['size']:
        raise ValueError('Partial model is larger than expected; preserved for inspection.')
    errors=[]
    for index,url in enumerate(spec['urls']):
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost')):
            raise ValueError('Model sources require HTTPS.')
        if cancel.is_set(): raise InterruptedError('Download canceled; partial data retained.')
        if index:
            progress({'stage':'fallback','file':target.name,'source':parsed.hostname,'bytes':partial.stat().st_size if partial.exists() else 0,'total':spec['size']})
        try:
            start=partial.stat().st_size if partial.exists() else 0
            if start<spec['size']:
                headers={'User-Agent':'MumbleboxSpriteStudio/0.1','Accept-Encoding':'identity'}
                if start: headers['Range']=f'bytes={start}-'
                with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=40) as response:
                    if start and response.status==206:
                        match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
                        if not match or int(match[1])!=start or int(match[3])!=spec['size']:
                            raise ValueError('Source returned an incompatible resume range.')
                    elif response.status==200: start=0
                    else: raise ValueError('Unexpected model download response.')
                    with partial.open('ab' if start else 'wb') as output:
                        count=start
                        while True:
                            if cancel.is_set(): raise InterruptedError('Download canceled; partial data retained.')
                            data=response.read(CHUNK)
                            if not data: break
                            count+=len(data)
                            if count>spec['size']: raise ValueError('Download exceeded expected size.')
                            output.write(data)
                            progress({'stage':'downloading','file':target.name,'source':parsed.hostname,'bytes':count,'total':spec['size']})
                        output.flush()
                        os.fsync(output.fileno())
            if partial.stat().st_size!=spec['size']: raise OSError('Transfer stopped early. Retry to resume.')
            if sha256(partial,cancel,progress)!=spec['sha256']:
                partial.unlink()  # Only our unpromoted corrupt transfer, never an installed model.
                raise ValueError('Publisher checksum mismatch; corrupt transfer discarded.')
            if target.exists(): raise ValueError('Another model appeared during transfer. Preserved; retry to verify.')
            partial.rename(target)
            progress({'stage':'ready','file':target.name,'bytes':spec['size'],'total':spec['size']})
            return target
        except InterruptedError: raise
        except (OSError,ValueError,urllib.error.URLError) as error:
            errors.append(f'{parsed.hostname}: {error}')
    raise ValueError('Could not obtain a verified model. '+'; '.join(errors))
