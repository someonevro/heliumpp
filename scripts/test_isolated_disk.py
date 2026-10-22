#!/usr/bin/env python3
"""Does an isolated tab leave its URL on disk? Visits a URL with a unique marker in an isolated tab
(and, as a control, in a normal tab), shuts the browser down, then searches the profile folder.
Run from the project root: python3 -I scripts/test_isolated_disk.py"""
import http.server, os, shutil, subprocess, threading, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(b"<title>marker page</title>hello")

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = "http://127.0.0.1:%d" % port
prof = os.path.join(BUILD, "profile-isodisk"); shutil.rmtree(prof, ignore_errors=True)
env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
cmd = [BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--headless=new", "--no-sandbox", "--disable-gpu",
       "--helium-isolated-tabs=" + base + "/ISOLATEDMARKER7731", base + "/NORMALMARKER5512"]
cmd = cmd[:-1] + [base + "/NORMALMARKER5512"]
p = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(14); p.terminate()
try: p.wait(20)
except subprocess.TimeoutExpired: p.kill()
srv.shutdown()

def hits(marker):
    out = []
    for dp, _, fns in os.walk(prof):
        for fn in fns:
            fp = os.path.join(dp, fn)
            try:
                if marker.encode() in open(fp, "rb").read():
                    out.append(os.path.relpath(fp, prof))
            except OSError:
                pass
    return out

n = hits("NORMALMARKER5512"); i = hits("ISOLATEDMARKER7731")
print("control, normal tab URL found in :", n or "nowhere")
print("isolated tab URL found in        :", i or "nowhere")
print("PASS: isolated URL not on disk" if n and not i else
      ("FAIL: isolated URL leaked to disk" if i else "INCONCLUSIVE: control found nothing, test not meaningful"))
raise SystemExit(0 if n and not i else 1)
