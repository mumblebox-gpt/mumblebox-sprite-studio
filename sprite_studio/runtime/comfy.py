"""Narrow supported HTTP boundary to the current Comfy server."""
import aiohttp


class ComfyClient:
    def __init__(self, port=8188):
        self.base = f'http://127.0.0.1:{int(port)}'
        self.session = None

    async def request(self, method, path, data=None):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120))
        async with self.session.request(method,self.base+path,json=data) as response:
            result = await response.json() if response.content_type=='application/json' else {}
            if response.status >= 400:
                message = result.get('error', result)
                raise ValueError(f'ComfyUI rejected this job: {message}')
            return result

    async def submit(self, graph, client_id, workflow, prompt_id=None):
        result = await self.request('POST','/prompt',{'prompt':graph,'prompt_id':prompt_id,'client_id':client_id,'extra_data':{'extra_pnginfo':{'workflow':workflow}}})
        return result['prompt_id']

    async def queue(self):return await self.request('GET','/queue')

    async def history(self, prompt_id):
        result = await self.request('GET','/history/'+prompt_id)
        return result.get(prompt_id)

    async def cancel(self, prompt_id):
        # Current native Comfy supports targeted interruption; never omit the ID.
        await self.request('POST','/queue',{'delete':[prompt_id]})
        await self.request('POST','/interrupt',{'prompt_id':prompt_id})

    async def close(self):
        if self.session:
            await self.session.close()
