#!/usr/bin/env python3
"""Do isolated tabs that START on a blank/internal page stay isolated after a URL is loaded in them?
Variants (each opened with its own storage): about:blank, chrome://version, chrome://new-tab-page. Each then loads
/set (sets a cookie). A normal tab reads later and must NOT see any of those cookies.
Run from the project root: python3 -I scripts/test_isolated_blank.py"""
import http.server, os, shutil, subprocess, sys, threading, time, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
seen = {}

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        ident = q.get("id", ["?"])[0]
        if u.path == "/favicon.ico":
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type", "text/html")
        if u.path == "/wait":
            self.end_headers()
            self.wfile.write(("wait<script>setTimeout(()=>location='/read?id=%s',9000)</script>" % ident).encode()); return
        seen.setdefault(ident, []).append(self.headers.get("Cookie"))
        if u.path == "/set":
            self.send_header("Set-Cookie", "c%s=1; Path=/" % ident)
        self.end_headers(); self.wfile.write(b"ok")

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
base = "http://127.0.0.1:%d" % srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
prof = os.path.join(BUILD, "profile-isoblank"); shutil.rmtree(prof, ignore_errors=True)
env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
iso = ",".join(["about:blank|%s/set?id=BL" % base,
                "chrome://version|%s/set?id=CV" % base,
                "chrome://new-tab-page|%s/set?id=DT" % base])
cmd = [BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--headless=new", "--no-sandbox", "--disable-gpu",
       "--helium-isolated-tabs=" + iso, base + "/wait?id=NORMAL"]
p = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(30); p.terminate()
try: p.wait(10)
except subprocess.TimeoutExpired: p.kill()
srv.shutdown()
print(seen)
ok = True
for ident, label in [("BL", "about:blank"), ("CV", "chrome://version"), ("DT", "chrome://new-tab-page")]:
    reached = ident in seen
    print("%-17s tab reached /set: %s" % (label, reached))
normal = seen.get("NORMAL", [None])[0]
print("normal tab cookie header when reading later:", normal)
for ident, label in [("BL", "about:blank"), ("CV", "chrome://version"), ("DT", "chrome://new-tab-page")]:
    leaked = normal is not None and ("c%s=1" % ident) in normal
    print(("LEAK " if leaked else "ok   ") + label + ": cookie set by the tab " + ("is visible to a NORMAL tab (NOT isolated)" if leaked else "is not visible to a normal tab"))
    ok &= not leaked and ident in seen
sys.exit(0 if ok and "NORMAL" in seen else 1)
