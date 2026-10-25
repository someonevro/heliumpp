#!/usr/bin/env python3
"""Satoshi UI font (0102): browser pages (chrome://settings, chrome://newtab) load it; a normal web page can
neither render it by name (font-family / local()) nor fetch the file from chrome://resources.
Run from the project root: python3 -I scripts/test_ui_font.py"""
import sys, functools, http.server, json, os, shutil, subprocess, threading, time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, WEB = 9352, 8352

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

# Width of a test string in the asked font with monospace fallback: equal to plain monospace = font absent.
PROBE = """(async () => {
  const w = f => { const c = document.createElement('canvas').getContext('2d');
                   c.font = '32px ' + f; return c.measureText('Wahlfqkg Satoshi 0123').width; };
  try { const ff = new FontFace('LocalProbe', 'local("Satoshi"), local("Satoshi Variable")');
        document.fonts.add(ff); await ff.load(); } catch (e) {}
  let fetched = 'blocked';
  try { await fetch('chrome://resources/fonts/Satoshi-Variable.ttf'); fetched = 'loaded'; } catch (e) {}
  await document.fonts.ready;
  return JSON.stringify({byName: w('Satoshi, monospace') !== w('monospace'),
                         byLocal: w('LocalProbe, monospace') !== w('monospace'), fetched,
                         body: getComputedStyle(document.body).fontFamily});
})()"""

class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(b"<body>web page</body>")
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", WEB), Page)
threading.Thread(target=srv.serve_forever, daemon=True).start()
prof = os.path.join(BUILD, "profile-uifont"); shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof + "/Default")
json.dump({"helium": {"completed_onboarding": True}}, open(prof + "/Default/Preferences", "w"))
env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
b = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--headless=new", "--no-sandbox",
                      "--disable-gpu", "--remote-debugging-port=%d" % PORT, "about:blank"],
                     env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
fails = 0
try:
    time.sleep(4)
    ws = WS(json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/version" % PORT))["webSocketDebuggerUrl"])
    def probe(url):
        t = ws.call("Target.createTarget", {"url": url})["result"]["targetId"]
        s = ws.call("Target.attachToTarget", {"targetId": t, "flatten": True})["result"]["sessionId"]
        time.sleep(3)
        r = ws.call("Runtime.evaluate", {"expression": PROBE, "awaitPromise": True, "returnByValue": True}, s)
        return json.loads(r["result"]["result"]["value"])
    for url, want_used in (("http://127.0.0.1:%d/" % WEB, False), ("chrome://settings", True), ("chrome://newtab", True)):
        r = probe(url)
        if want_used:
            ok = r["byName"] and r["body"].strip('"').startswith("Satoshi")
        else:
            ok = not r["byName"] and not r["byLocal"] and r["fetched"] == "blocked"
        fails += not ok
        print("ok" if ok else "FAIL", url, r)
finally:
    b.terminate(); b.wait(30); srv.shutdown()
print("ALL PASS" if not fails else "%d FAILED" % fails)
raise SystemExit(1 if fails else 0)
