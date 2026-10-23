#!/usr/bin/env python3
"""Are downloads from isolated tabs blocked and kept off disk (0071)? An isolated tab and, as a control, a
normal tab each open a file download. PASS = normal file saved + its URL in the profile, isolated file NOT
saved and its URL nowhere in the profile. Run from the project root: python3 -I scripts/test_isolated_downloads.py"""
import http.server, json, os, shutil, subprocess, threading, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        name = self.path.rsplit("/", 1)[-1]
        self.send_response(200); self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", 'attachment; filename="%s.bin"' % name); self.end_headers()
        self.wfile.write(b"payload " + name.encode())

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = "http://127.0.0.1:%d" % srv.server_address[1]
prof = os.path.join(BUILD, "profile-isodl"); dl = os.path.join(BUILD, "test-isodl-downloads")
for d in (prof, dl): shutil.rmtree(d, ignore_errors=True)
os.makedirs(prof + "/Default"); os.makedirs(dl)
json.dump({"download": {"default_directory": dl, "prompt_for_download": False, "directory_upgrade": True}},
          open(prof + "/Default/Preferences", "w"))
env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
p = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--headless=new", "--no-sandbox",
                      "--disable-gpu", "--enable-logging=stderr", "--helium-isolated-tabs=" + base + "/ISODLMARKER4417", base + "/NORMDLMARKER9902"],
                     env=env, stdout=subprocess.DEVNULL, stderr=open(BUILD + "/test-isodl.log", "w"))
time.sleep(14); p.terminate()
try: p.wait(20)
except subprocess.TimeoutExpired: p.kill()
srv.shutdown()

def hits(marker):
    out = []
    for dp, _, fns in os.walk(prof):
        for fn in fns:
            try:
                if marker.encode() in open(os.path.join(dp, fn), "rb").read(): out.append(os.path.relpath(os.path.join(dp, fn), prof))
            except OSError: pass
    return out

files = sorted(os.listdir(dl))
normal_saved = any(f.startswith("NORMDLMARKER9902") and not f.endswith(".crdownload") for f in files)
iso_saved = any(f.startswith("ISODLMARKER4417") for f in files)
n, i = hits("NORMDLMARKER9902"), hits("ISODLMARKER4417")
print("download folder           :", files or "empty")
print("normal download URL in    :", n or "nowhere")
print("isolated download URL in  :", i or "nowhere")
ok = normal_saved and n and not iso_saved and not i
print("PASS: isolated download blocked and not on disk" if ok else
      ("INCONCLUSIVE: control download did not happen" if not normal_saved else "FAIL"))
raise SystemExit(0 if ok else 1)
