import hashlib
import importlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest


PAYLOAD = b'qualified-model-bytes' * 2048


class ModelHandler(BaseHTTPRequestHandler):
    ranges = []
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/missing':
            self.send_error(503)
            return
        start = int(self.headers.get('Range', 'bytes=0-').split('=')[1].split('-')[0])
        self.ranges.append(start)
        body = PAYLOAD[start:]
        self.send_response(206 if start else 200)
        self.send_header('Content-Length', str(len(body)))
        if start:
            self.send_header('Content-Range', f'bytes {start}-{len(PAYLOAD)-1}/{len(PAYLOAD)}')
        self.end_headers()
        self.wfile.write(body)


class DownloadTests(unittest.TestCase):
    def setUp(self):
        try:
            self.module = importlib.import_module('sprite_studio.runtime.downloads')
        except ModuleNotFoundError:
            self.fail('First-use download owner is not implemented')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), ModelHandler)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        self.spec = {'path': 'text_encoders/test.safetensors', 'size': len(PAYLOAD), 'sha256': hashlib.sha256(PAYLOAD).hexdigest(), 'urls': [self.url+'/missing', self.url+'/model']}

    def test_fallback_verifies_and_promotes_exact_file(self):
        events = []
        target = self.module.download_file(self.spec, self.root, events.append, threading.Event())
        self.assertEqual(target.read_bytes(), PAYLOAD)
        self.assertTrue(any(e['stage'] == 'fallback' for e in events))
        self.assertFalse(target.with_suffix(target.suffix+'.part').exists())

    def test_resume_preserves_partial_and_requests_remaining_range(self):
        target = self.root / self.spec['path']
        target.parent.mkdir(parents=True)
        target.with_suffix(target.suffix+'.part').write_bytes(PAYLOAD[:1000])
        self.module.download_file(self.spec, self.root, lambda event: None, threading.Event())
        self.assertEqual(target.read_bytes(), PAYLOAD)
        self.assertIn(1000, ModelHandler.ranges)

    def test_bad_digest_never_becomes_installed_model(self):
        self.spec['sha256'] = '0'*64
        with self.assertRaises(ValueError):
            self.module.download_file(self.spec, self.root, lambda event: None, threading.Event())
        self.assertFalse((self.root/self.spec['path']).exists())

    def test_existing_unknown_file_is_not_overwritten(self):
        target = self.root/self.spec['path']
        target.parent.mkdir(parents=True)
        target.write_bytes(b'user-owned')
        with self.assertRaises(ValueError):
            self.module.download_file(self.spec, self.root, lambda event: None, threading.Event())
        self.assertEqual(target.read_bytes(), b'user-owned')


if __name__ == '__main__':
    unittest.main()
