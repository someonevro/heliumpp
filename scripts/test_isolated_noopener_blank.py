#!/usr/bin/env python3
"""An isolated tab opens window.open('about:blank', '_blank', 'noopener'); the user then loads a URL in that popup
(simulated with CDP Page.navigate, a browser-initiated load like typing). The popup must stay in the opener's private
storage (it sees the opener's cookie) and a normal tab must not see that cookie (patch 0138).
Run from the project root: python3 -I scripts/test_isolated_noopener_blank.py   (HELIUM_BIN=... for another build)"""
import http.server, json, os, shutil, subprocess, sys, threading, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from cdp import WS  # noqa: E402

BIN = os.environ.get("HELIUM_BIN", BUILD + "/src/out/Default/helium")
PORT = 9347
seen = {}

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        ident = q.get("id", ["?"])[0]
        if u.path == "/favicon.ico":
            self.send_response(404); self.end_headers(); return
        seen.setdefault(ident, []).append(self.headers.get("Cookie"))
        self.send_response(200); self.send_header("Content-Type", "text/html")
        if u.path == "/opener":
            self.send_header("Set-Cookie", "t=O; Path=/"); self.end_headers()
            self.wfile.write(b"opener<script>setTimeout(()=>window.open('about:blank','_blank','noopener'),1500)</script>")
            return
        if u.path == "/wait":  # normal start tab: reads cookies only after the popup has loaded its URL
            self.end_headers(); self.wfile.write(b"wait<script>setTimeout(()=>location='/read?id=NORMAL',15000)</script>")
            return
        self.end_headers(); self.wfile.write(b"ok")

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
base = "http://127.0.0.1:%d" % srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
prof = os.path.join(BUILD, "profile-isonoopener"); shutil.rmtree(prof, ignore_errors=True)
env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
p = subprocess.Popen([BIN, "--user-data-dir=" + prof, "--headless=new", "--no-sandbox", "--disable-gpu",
                      "--disable-popup-blocking", "--remote-debugging-port=%d" % PORT,
                      "--helium-isolated-tabs=%s/opener?id=O" % base, base + "/wait?id=W"],
                     env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
popup = None
try:
    for _ in range(60):
        try: ver = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/version" % PORT)); break
        except OSError: time.sleep(0.5)
    ws = WS(ver["webSocketDebuggerUrl"])
    for _ in range(40):  # wait for the opener to load and open its popup
        time.sleep(0.5)
        pages = [t for t in ws.call("Target.getTargets")["result"]["targetInfos"] if t["type"] == "page"]
        if "O" in seen and any(t["url"] == "about:blank" for t in pages):
            break
    blanks = [t for t in pages if t["url"] == "about:blank"]
    popup = blanks[-1]["targetId"] if blanks else None
    if popup:
        sid = ws.call("Target.attachToTarget", {"targetId": popup, "flatten": True})["result"]["sessionId"]
        ws.call("Page.navigate", {"url": base + "/read?id=POP"}, sid)
    # Not Target.createTarget: a tab opened while the isolated popup is active inherits its isolation (0051).
    for _ in range(40):
        time.sleep(0.5)
        if "NORMAL" in seen: break
finally:
    p.terminate()
    try: p.wait(10)
    except subprocess.TimeoutExpired: p.kill()
    srv.shutdown()

print(seen)
pop = (seen.get("POP") or [None])[0]
normal = (seen.get("NORMAL") or [None])[0]
results = [("isolated opener loaded", "O" in seen, True),
           ("noopener about:blank popup found", popup is not None, True),
           ("popup sent to a URL stays in the opener's storage (sees t=O)", pop == "t=O", True),
           ("normal tab does not see the isolated cookie", "NORMAL" in seen and "t=O" not in (normal or ""), True)]
ok = True
for name, got, want in results:
    print("%-62s %s%s" % (name, got, "" if got == want else "  <-- FAIL (want %s)" % want))
    ok &= got == want
print("PASS" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
