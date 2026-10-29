#!/usr/bin/env python3
"""Web sidebar marks isolated tabs (patch 0137): in a private Xvfb display (never the real desktop) the browser starts
with one normal tab and one isolated tab (--helium-isolated-tabs); the sidebar row of the isolated tab must carry
data-isolated, the mask icon and the explanatory title, and the normal row none of them.
Run from the project root: python3 -I scripts/test_sidebar_isolated.py"""
import http.server, json, os, shutil, subprocess, sys, threading, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, HTTP, DISP = 9364, 8364, ":94"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        name = self.path.strip("/")
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(f"<title>{name}</title>".encode())
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", HTTP), Page)
threading.Thread(target=srv.serve_forever, daemon=True).start()
U = lambda p: f"http://127.0.0.1:{HTTP}/{p}"
prof = os.path.join(BUILD, "profile-sidebar-iso-test")
shutil.rmtree(prof, ignore_errors=True); os.makedirs(f"{prof}/Default")
json.dump({"helium": {"completed_onboarding": True, "browser": {"layout": 2}}}, open(f"{prof}/Default/Preferences", "w"))
xvfb = subprocess.Popen(["Xvfb", DISP, "-screen", "0", "1200x800x24", "-nolisten", "tcp"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
env = {**os.environ, "DISPLAY": DISP, "XDG_CONFIG_HOME": f"{BUILD}/xdg/config", "XDG_CACHE_HOME": f"{BUILD}/xdg/cache"}
env.pop("WAYLAND_DISPLAY", None)
br = subprocess.Popen([f"{BUILD}/src/out/Default/helium", "--ozone-platform=x11", f"--user-data-dir={prof}",
                       "--no-first-run", f"--remote-debugging-port={PORT}", "--window-size=1100,750",
                       "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1",
                       f"--helium-isolated-tabs={U('secret')}", U("plain")],
                      env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" ({detail})" if detail and not ok else ""))
    if not ok: fails.append(name)

def wait(pred, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        try:
            v = pred()
            if v: return v
        except OSError:
            pass
        time.sleep(0.25)
    return pred()

try:
    ver = wait(lambda: json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version")), 20)
    ws = WS(ver["webSocketDebuggerUrl"])
    targets = lambda: ws.call("Target.getTargets")["result"]["targetInfos"]
    side = wait(lambda: next((t for t in targets() if t["url"].startswith("chrome://helium-sidebar")), None))
    s = ws.call("Target.attachToTarget", {"targetId": side["targetId"], "flatten": True})["result"]["sessionId"]
    def ev(expr):
        r = ws.call("Runtime.evaluate", {"expression": expr, "returnByValue": True}, s)
        return r["result"].get("result", {}).get("value")
    rows = ("[...document.querySelector('helium-sidebar-app').shadowRoot.querySelectorAll('.scroll .tab')]"
            ".map(r => ({t: r.querySelector('.t').textContent.trim(), iso: r.hasAttribute('data-isolated'),"
            " mask: !!r.querySelector('.iso svg'), title: r.title}))")
    got = wait(lambda: (lambda r: r if {x["t"] for x in r} >= {"secret", "plain"} and
                        any(x["iso"] for x in r) else None)(ev(rows) or []))
    got = got or ev(rows) or []
    by = {x["t"]: x for x in got}
    secret, plain = by.get("secret", {}), by.get("plain", {})
    check("isolated tab row is marked", secret.get("iso") is True, got)
    check("isolated tab row shows the mask icon", secret.get("mask") is True, got)
    check("isolated tab title explains it", "isolated tab" in secret.get("title", ""), secret.get("title"))
    check("normal tab row is not marked", plain and not plain["iso"] and not plain["mask"], got)
except Exception:
    import traceback; traceback.print_exc(); fails.append("exception")
finally:
    if br.poll() is None: br.kill()
    xvfb.kill(); srv.shutdown()
    shutil.rmtree(prof, ignore_errors=True)
print("RESULT", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
