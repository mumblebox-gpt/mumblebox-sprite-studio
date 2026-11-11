"""Loopback-only HTTP adapters; no inference or storage policy in route handlers."""
import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit
from aiohttp import web
from .application import StudioApplication
from .storage import safe_path
from .features.create_image.schema import validate_recipe
from .features.create_image.prompt import build_prompt

ROOT=Path(__file__).parent
PREFIX='/sprite-studio/v1'


def local_request(request):
    if request.remote not in ('127.0.0.1','::1'):
        return False
    if urlsplit('http://'+request.host).hostname not in ('localhost','127.0.0.1','::1'):
        return False
    origin=request.headers.get('Origin')
    return not origin or urlsplit(origin).netloc==request.host


def register(server, folders, port):
    application=None
    def app():
        nonlocal application
        if application is None:
            application=StudioApplication(folders,port)
        return application

    async def endpoint(request):
        if not local_request(request):
            return web.json_response({'error':'This interface is available only from the local ComfyUI app.'},status=403)
        try:
            owner=app()
            await owner.jobs.recover()
            action=request.match_info['action']
            if request.method=='GET':
                if action=='bootstrap': result=owner.bootstrap()
                elif action=='telemetry': result=await owner.telemetry()
                elif action=='job': result=owner.jobs.owned(request.query.get('id',''))
                elif action=='gallery': result=owner.gallery.list(sort=request.query.get('sort','newest'),kind=request.query.get('kind') or None,offset=int(request.query.get('offset','0')),trashed=request.query.get('trashed')=='true',favorite=request.query.get('favorite')=='true')
                elif action=='cache': result=await asyncio.to_thread(owner.temporary.inventory)
                elif action=='refmods':result=owner.refmods.list(int(request.query.get('offset','0')),request.query.get('trashed')=='true')
                elif action=='refmod':result=owner.refmods.get(request.query.get('id',''))
                elif action=='refmod-file':return web.FileResponse(owner.refmods.tensor_file(request.query.get('id','')),headers={'Content-Disposition':'attachment; filename="reference.safetensors"'})
                elif action=='library-export-file':return web.FileResponse(owner.refmods.export_file(request.query.get('id','')),headers={'Content-Disposition':'attachment; filename="reference.sprite-refmod.zip"'})
                elif action=='asset': return web.FileResponse(owner.references.file(request.query.get('id','')))
                elif action=='crop-review': result=await asyncio.to_thread(owner.exports.review,request.query.get('id',''))
                elif action=='export-file': return web.FileResponse(owner.exports.file(request.query.get('id','')),headers={'Content-Disposition':'attachment; filename="sprite-studio-turnaround.zip"'})
                else: raise ValueError('Unknown Studio action.')
            elif action in ('upload','refmod-import'):
                reader=await request.multipart()
                field=await reader.next()
                if field is None or not field.filename:
                    raise ValueError('Choose a reference image.')
                data=bytearray()
                while chunk:=await field.read_chunk():
                    data.extend(chunk)
                    limit=(256 if action=='refmod-import' else 32)*1024*1024
                    if len(data)>limit: raise ValueError(f'Choose a file up to {limit//1024//1024} MB.')
                operation=owner.refmods.import_file if action=='refmod-import' else owner.references.import_image
                result=await asyncio.to_thread(operation,bytes(data),field.filename)
            else:
                if request.content_type!='application/json' or (request.content_length or 0)>4_000_000:
                    raise ValueError('Invalid Studio request.')
                data=bytearray()
                async for chunk in request.content.iter_chunked(65536):
                    data.extend(chunk)
                    if len(data)>4_000_000:raise ValueError('Studio request is too large.')
                body=json.loads(data)
                if not isinstance(body,dict): raise ValueError('Expected settings object.')
                if action=='preview': result={'prompt':build_prompt(validate_recipe(body))}
                elif action=='draft':
                    kind=body.get('kind')
                    if kind not in ('create_image','turnaround','refmod'): raise ValueError('Unknown draft.')
                    owner.store.put_document('drafts',kind,body)
                    result={'saved':True}
                elif action=='prepare':
                    result=await owner.jobs.submit(body.get('recipe'),body.get('request_id'),body.get('client_id',''))
                elif action=='start': result=await owner.jobs.start(body.get('id'),body.get('workflow'))
                elif action=='cancel': result=await owner.jobs.cancel(body.get('id'))
                elif action=='crop-export': result=await asyncio.to_thread(owner.exports.export,body.get('id'),body.get('rectangles'),body.get('reviewed'))
                elif action=='crop-library':result=await asyncio.to_thread(owner.exports.to_library,body.get('id'),body.get('rectangles'),body.get('reviewed'),body.get('name'),owner.references,owner.refmods)
                elif action=='gallery-update': result=owner.gallery.update(body.get('id'),body.get('patch'))
                elif action=='gallery-trash': result=owner.gallery.trash(body.get('ids'),body.get('trashed'))
                elif action=='refmod-save':result=owner.refmods.save(body)
                elif action=='refmod-package':
                    path=await asyncio.to_thread(owner.refmods.export,body.get('id'))
                    result={'download':f'{PREFIX}/library-export-file?id={path.stem}'}
                elif action=='refmod-trash':result=owner.refmods.trash(body.get('id'),body.get('trashed'))
                elif action=='refmod-select':result={'references':owner.refmods.select(body.get('id'),body.get('indices'))}
                elif action=='purge-cache': result=await asyncio.to_thread(owner.temporary.purge)
                elif action=='reference-output':
                    _,path=owner.exports.source(body.get('id'))
                    result=await asyncio.to_thread(owner.references.import_image,path.read_bytes(),path.name)
                elif action=='settings':
                    result=owner.settings.update(body)
                elif action=='unload':
                    queue=await owner.engine.request('GET','/queue')
                    if queue['queue_running'] or queue['queue_pending']:
                        raise ValueError('Wait for the current ComfyUI jobs to finish before unloading models.')
                    await owner.engine.request('POST','/free',{'unload_models':True,'free_memory':True})
                    result={'unloaded':True}
                else: raise ValueError('Unknown Studio action.')
            return web.json_response(result)
        except (ValueError,KeyError,TypeError) as error:
            return web.json_response({'error':str(error)},status=400)
        except Exception as error:
            return web.json_response({'error':f'Studio could not finish this action: {error}'},status=500)

    async def module(request):
        if not local_request(request): return web.Response(status=403)
        try:
            path=safe_path(ROOT,request.match_info['path'])
            if path.suffix not in ('.mjs','.css','.png','.svg') or not path.is_file():
                return web.Response(status=404)
            return web.FileResponse(path,headers={'Cache-Control':'no-cache'})
        except ValueError:
            return web.Response(status=404)

    server.routes.get(PREFIX+'/{action}')(endpoint)
    server.routes.post(PREFIX+'/{action}')(endpoint)
    server.routes.get('/sprite-studio/ui/{path:.*}')(module)

    async def cleanup(_):
        if application is not None:
            await application.jobs.close()
            await application.engine.close()
            application.store.close()
    server.app.on_cleanup.append(cleanup)
