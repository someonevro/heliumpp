#!/usr/bin/env python3
"""Is an isolated tab's storage deleted when the tab closes?
Tab X (named storage 'fixed') sets a cookie. Later a new tab Y reuses the SAME storage name and reads.
 - run WITHOUT closing X: Y must see the cookie  (control: proves the test can detect leftovers)
 - run WITH X closed first: Y must see nothing    (the wipe worked)
Run from the project root: python3 -I scripts/test_isolated_wipe.py"""
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
        seen.setdefault(ident, []).append(self.headers.get("Cookie"))
        self.send_response(200); self.send_header("Content-Type", "text/html")
        if u.path == "/set":
            self.send_header("Set-Cookie", "t=X; Path=/")
        self.end_headers(); self.wfile.write(b"ok")

def run(close_x):
    seen.clear()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    base = "http://127.0.0.1:%d" % srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    prof = os.path.join(BUILD, "profile-isowipe"); shutil.rmtree(prof, ignore_errors=True)
    env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
    cmd = [BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--headless=new", "--no-sandbox",
           "--disable-gpu", "--helium-isolated-tabs=fixed@" + base + "/set?id=X",
           "--helium-isolated-tabs-late=fixed@" + base + "/read?id=Y", base + "/read?id=N"]
    if close_x:
        cmd.insert(-1, "--helium-isolated-close-after=6")
    p = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(28); p.terminate()
    try: p.wait(10)
    except subprocess.TimeoutExpired: p.kill()
    srv.shutdown()
    return dict(seen)

ok = True
def check(name, cond):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name)

a = run(close_x=False); print("control (X stays open):", a)
check("control: X set its cookie and Y reached the server", "X" in a and "Y" in a)
check("control: Y (same storage name, X still open) sees t=X", a.get("Y") and a["Y"][0] == "t=X")
b = run(close_x=True); print("X closed first       :", b)
check("closed run: Y reached the server", "Y" in b)
check("closed run: Y sees NO cookie, X's storage was deleted", b.get("Y") and b["Y"][0] is None)
sys.exit(0 if ok else 1)
