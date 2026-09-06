"""Run the local NIA control panel: python narzedzia/panel.py [--no-open]."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
from pathlib import Path
import secrets
import sys
from urllib.parse import urlsplit, parse_qs
import webbrowser

from panel_core import Panel, PanelError, ROOT, preset


def make_server(port=8765, panel=None):
    panel = panel or Panel()
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log request bodies, API keys or session data.

        def respond(self, code, body, mime='application/json; charset=utf-8'):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; form-action 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def allowed(self, authenticated=False):
            host = '127.0.0.1:%s' % self.server.server_port
            if self.headers.get('Host') != host:
                self.respond(403, {'error': 'Invalid host.'})
                return False
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + host:
                self.respond(403, {'error': 'Invalid origin.'})
                return False
            if authenticated and not secrets.compare_digest(self.headers.get('X-NIA-Token', ''), token):
                self.respond(403, {'error': 'Reload the panel to establish a local session.'})
                return False
            return True

        def do_GET(self):
            route = urlsplit(self.path)
            if not self.allowed(route.path.startswith('/api/')):
                return
            try:
                if route.path == '/api/status':
                    return self.respond(200, panel.status())
                if route.path == '/api/preset':
                    return self.respond(200, panel.read(parse_qs(route.query).get('id', [''])[0]))
                files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
                if route.path not in files:
                    return self.respond(404, {'error': 'Not found.'})
                name, mime = files[route.path]
                body = (ROOT / 'panel' / name).read_bytes()
                if name == 'index.html':
                    body = body.replace(b'__NIA_TOKEN__', token.encode())
                self.respond(200, body, mime)
            except (PanelError, ValueError, OSError, preset.BladPresetu) as exc:
                self.respond(400, {'error': str(exc)})

        def do_POST(self):
            if not self.allowed(True):
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 2_000_000 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    return self.respond(400, {'error': 'Expected a JSON request under 2 MB.'})
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise PanelError('Expected a JSON object.')
                route = urlsplit(self.path).path
                if route == '/api/save':
                    result = panel.save(body)
                elif route == '/api/validate':
                    result = panel.save(body, validate_only=True)
                elif route == '/api/activate':
                    result = panel.activate(body.get('name'), body.get('instance'))
                elif route == '/api/account':
                    result = panel.account(body)
                elif route == '/api/start':
                    result = panel.start(body.get('action'))
                else:
                    return self.respond(404, {'error': 'Not found.'})
                self.respond(200, result)
            except (PanelError, ValueError, OSError, preset.BladPresetu) as exc:
                self.respond(400, {'error': str(exc)})
            except Exception:
                self.respond(500, {'error': 'Operation failed. Check the preset files and retry; no success was recorded.'})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server, panel, token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args()
    server, panel, _ = make_server(args.port)
    url = 'http://127.0.0.1:%s' % server.server_port
    print('NIA control panel:', url, flush=True)
    print('Keep this launcher open. Closing the browser tab does not stop a running bot job.', flush=True)
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nPanel stopped. An already running bot process may still be finishing.', flush=True)
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
