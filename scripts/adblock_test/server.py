"""Local test server for the ad-blocking check. Logs every request path+Host to the file in argv[2]."""
import http.server, sys

PAGE = b"""<!doctype html><meta charset=utf-8><body><script>
// Wait so the blocker has started, then request ad/tracker/control scripts and record results.
const base = location.port;
const tests = {
  'pagead2.googlesyndication.com': 'http://pagead2.googlesyndication.com:' + base + '/x.js',
  'securepubads.g.doubleclick.net': 'http://securepubads.g.doubleclick.net:' + base + '/x.js',
  'www.google-analytics.com': 'http://www.google-analytics.com:' + base + '/x.js',
  'connect.facebook.net': 'http://connect.facebook.net:' + base + '/x.js',
  'static.ads-twitter.com': 'http://static.ads-twitter.com:' + base + '/x.js',
  'cdn.taboola.com': 'http://cdn.taboola.com:' + base + '/x.js',
  'sb.scorecardresearch.com': 'http://sb.scorecardresearch.com:' + base + '/x.js',
  'c.amazon-adsystem.com': 'http://c.amazon-adsystem.com:' + base + '/x.js',
  'ads.pubmatic.com': 'http://ads.pubmatic.com:' + base + '/x.js',
  'widget.criteo.com': 'http://widget.criteo.com:' + base + '/x.js',
  control: 'http://control.example:' + base + '/ok.js',
};
const result = {};
function run() {
  let pending = Object.keys(tests).length;
  for (const [name, url] of Object.entries(tests)) {
    const s = document.createElement('script');
    s.onload = () => { result[name] = 'loaded'; if (!--pending) done(); };
    s.onerror = () => { result[name] = 'blocked'; if (!--pending) done(); };
    s.src = url + '?t=' + Date.now();
    document.head.appendChild(s);
  }
}
function done() { document.body.textContent = 'RESULT ' + JSON.stringify(result); }
setTimeout(run, parseInt(new URLSearchParams(location.search).get('delay') || '0'));
</script>"""

log = open(sys.argv[2], "a", buffering=1)

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        log.write(f"{self.headers.get('Host')} {self.path}\n")
        if self.path.startswith("/test"):
            body, ctype = PAGE, "text/html"
        else:
            body, ctype = b"window.__loaded=1;", "application/javascript"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass

http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
