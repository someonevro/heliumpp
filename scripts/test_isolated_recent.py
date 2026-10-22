#!/usr/bin/env python3
"""Does closing an isolated tab put its URL in the 'recently closed' list on disk?
A normal tab (control) and an isolated tab each open a popup tab with a unique URL and close it.
After a clean shutdown the profile folder is searched for both markers.
Run from the project root: python3 -I scripts/test_isolated_recent.py"""
import http.server, os, shutil, subprocess, threading, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        if "/open" in self.path:  # open a tab with a marker URL, then close it again
            marker = self.path.split("/open", 1)[1]
            self.wfile.write(("<title>opener</title><script>setTimeout(()=>{const w=window.open('/%s');"
                              "setTimeout(()=>w.close(),3000)},2000)</script>" % marker).encode())
        else:
            self.wfile.write(b"<title>closed tab page</title>hello")

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
base = "http://127.0.0.1:%d" % srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
prof = os.path.join(BUILD, "profile-isorecent"); shutil.rmtree(prof, ignore_errors=True)
env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
cmd = [BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--headless=new", "--no-sandbox", "--disable-gpu",
       "--disable-popup-blocking", "--helium-isolated-tabs=" + base + "/open/ISOLCLOSED4417", base + "/open/NORMCLOSED9921"]
cmd = cmd[:-1] + [base + "/open/NORMCLOSED9921"]
p = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(22); p.terminate()
try: p.wait(20)
except subprocess.TimeoutExpired: p.kill()
srv.shutdown()

def hits(marker):
    out = []
    for dp, _, fns in os.walk(prof):
        for fn in fns:
            fp = os.path.join(dp, fn)
            try:
                if marker.encode() in open(fp, "rb").read(): out.append(os.path.relpath(fp, prof))
            except OSError: pass
    return out
n = hits("NORMCLOSED9921"); i = hits("ISOLCLOSED4417")
print("control: closed NORMAL tab URL found in :", n or "nowhere")
print("closed ISOLATED tab URL found in        :", i or "nowhere")
recent = [f for f in n if "Sessions/Tabs_" in f]
print("control reached the 'recently closed' file:", bool(recent))
print("PASS: closed isolated tab URL not on disk" if not i and n else ("FAIL: leaked" if i else "INCONCLUSIVE"))
raise SystemExit(0 if (not i and n) else 1)
