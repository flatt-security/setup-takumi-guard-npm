# Stands in for GitHub's OIDC endpoint and for the STS on 127.0.0.1:18080, so
# the action completes its authenticated path without real credentials. Every
# GET returns an OIDC token and every POST returns the access token
# "standin-guard-token", which the real proxy rejects with 401, except a POST
# under /reject/, which answers the way the STS refuses an exchange, and a POST
# under /html/, which answers with an HTML error page the way a gateway in
# front of the STS does when the STS is down.
# The first POST under /flaky/ gets that HTML page and later ones succeed, the
# way a brief STS outage looks to a client that retries.
import http.server, json

flaky_seen = False

class Handler(http.server.BaseHTTPRequestHandler):
    def reply(self, body, status=200):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def bad_gateway(self):
        data = b'<html><body>502 Bad Gateway</body></html>'
        self.send_response(502)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.reply({'value': 'standin-oidc-token'})

    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length') or 0))
        if self.path.startswith('/reject/'):
            self.reply({'message': 'invalid ID token'}, 400)
            return
        global flaky_seen
        if self.path.startswith('/flaky/') and not flaky_seen:
            flaky_seen = True
            self.bad_gateway()
            return
        if self.path.startswith('/html/'):
            self.bad_gateway()
            return
        self.reply({'access_token': 'standin-guard-token', 'expires_in': 1800})

    def log_message(self, *args):
        pass

http.server.HTTPServer(('127.0.0.1', 18080), Handler).serve_forever()
