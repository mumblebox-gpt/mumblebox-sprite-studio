"""Bounded safetensors header validation before allocating any tensor."""
import json
import math
import struct

MAX_FILE=256*1024*1024


def inspect_bytes(data):
    if not 8<=len(data)<=MAX_FILE:raise ValueError('Choose a RefMod file up to 256 MB.')
    length=struct.unpack('<Q',data[:8])[0]
    if not 2<=length<=2*1024*1024 or length+8>len(data):raise ValueError('Invalid safetensors header.')
    try:
        header=json.loads(data[8:8+length])
        meta=json.loads(header['__metadata__']['refmod_meta'])
        if not isinstance(meta,dict):raise ValueError('Malformed RefMod metadata.')
        version=meta.get('_format_version')
        if version==5 and meta.get('kind')=='bundle':members=meta['members'];keys=[f'ref_{i}' for i in range(len(members))]
        elif version==4:members=[meta];keys=['latent']
        else:raise ValueError('Supported RefMod versions are 4 (still) and 5 (still bundle).')
        if not isinstance(members,list) or not 1<=len(members)<=8:raise ValueError('Choose a bundle with one to eight still references.')
        offsets=[]
        for member,key in zip(members,keys):
            if not isinstance(member,dict):raise ValueError('Malformed RefMod member.')
            if member.get('kind')!='image':raise ValueError('Sprite Studio currently imports still-image RefMods. Audio and video members are not image references.')
            tensor=header[key];shape=tensor['shape'];item_bytes={'F16':2,'BF16':2,'F32':4}.get(tensor['dtype'])
            if not item_bytes or not isinstance(shape,list) or len(shape)!=5 or any(type(n) is not int for n in shape) or shape[:3]!=[1,24,1] or any(n<2 or n>128 or n%2 for n in shape[3:]):
                raise ValueError('RefMod shape must describe a still image up to 2048 pixels per edge.')
            start,end=tensor['data_offsets']
            if type(start) is not int or type(end) is not int or not 0<=start<end<=len(data)-8-length or end-start!=math.prod(shape)*item_bytes:
                raise ValueError('Invalid tensor offsets or truncated RefMod.')
            offsets.append((start,end))
        if set(header)-{'__metadata__'}!=set(keys):raise ValueError('Unexpected tensors in RefMod.')
        ordered=sorted(offsets)
        if ordered[0][0]!=0 or ordered[-1][1]!=len(data)-8-length or any(a[1]!=b[0] for a,b in zip(ordered,ordered[1:])):
            raise ValueError('Invalid or overlapping RefMod payload.')
        return {'metadata':meta,'member_count':len(members),'members':members}
    except (KeyError,TypeError,IndexError,UnicodeError,json.JSONDecodeError,struct.error) as error:
        raise ValueError('Malformed RefMod metadata or tensor layout.') from error
