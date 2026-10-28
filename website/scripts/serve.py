"""Loopback-only static preview with HTTP byte ranges for accurate MP4 seeking."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2] / "docs"


class Handler(SimpleHTTPRequestHandler):
    range_length = None

    def translate_path(self, path):
        # Exercise both root hosting and the eventual GitHub Pages project path.
        prefix = '/astra-guide-vla-website'
        if path == prefix or path.startswith(prefix + '/'):
            path = path[len(prefix):] or '/'
        return super().translate_path(path)

    def send_head(self):
        self.range_length = None
        target = Path(self.translate_path(self.path))
        requested = self.headers.get('Range')
        if not requested or not target.is_file():
            return super().send_head()
        size = target.stat().st_size
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested.strip())
        if not match or not any(match.groups()):
            self.send_error(416, 'Unsupported byte range')
            return None
        first, last = match.groups()
        if first:
            start, end = int(first), min(int(last), size - 1) if last else size - 1
        else:
            start, end = max(0, size - int(last)), size - 1
        if start >= size or end < start:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        source = target.open('rb')
        source.seek(start)
        self.range_length = end - start + 1
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(str(target)))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(self.range_length))
        self.end_headers()
        return source

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def copyfile(self, source, output):
        if self.range_length is None:
            try:
                return super().copyfile(source, output)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                return
        remaining = self.range_length
        try:
            while remaining:
                chunk = source.read(min(65536, remaining))
                if not chunk:
                    break
                output.write(chunk)
                remaining -= len(chunk)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass  # Browser switches tasks or cancels a media request.


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(ROOT)))
    print(f'Preview: http://127.0.0.1:{args.port}/', flush=True)
    print(f'Project path: http://127.0.0.1:{args.port}/astra-guide-vla-website/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
