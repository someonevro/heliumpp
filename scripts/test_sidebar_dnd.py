#!/usr/bin/env python3
"""Drag and drop of tabs in the web sidebar (patch 0166).
In a private Xvfb display (never the real desktop) three tabs p1, p2, p3 are opened. Real mouse drags
(XTest press, move, release) are made on the sidebar's rows, and the browser's own tab order is read back
over CDP from the sidebar's list, which mirrors the tab strip:
  - p1 dropped on the lower half of p3   -> order p2, p3, p1
  - p1 dropped on the upper half of p2   -> order p1, p2, p3
  - p1 dropped on the list's empty end   -> order p2, p3, p1
The sidebar page's screen offset is measured, not guessed: a real mouse move is read back as clientX/clientY.
Run from the project root: python3 -I scripts/test_sidebar_dnd.py"""
import http.server, json, os, shutil, subprocess, sys, threading, time, urllib.request

from Xlib import X, display
from Xlib.ext import xtest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, DISP = 9366, ":92"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        m = self.path.strip("/")
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(f"<title>{m}</title>{m}".encode())
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Page)
threading.Thread(target=srv.serve_forever, daemon=True).start()
page = lambda m: f"http://127.0.0.1:{srv.server_address[1]}/{m}"

prof = f"{BUILD}/profile-test-dnd"
shutil.rmtree(prof, ignore_errors=True); os.makedirs(f"{prof}/Default")
json.dump({"helium": {"completed_onboarding": True, "browser": {"layout": 2, "zen_mode": False}},
           "vertical_tabs": {"collapsed_state": False, "uncollapsed_width": 232}},
          open(f"{prof}/Default/Preferences", "w"))

xvfb = subprocess.Popen(["Xvfb", DISP, "-screen", "0", "1400x900x24", "-nolisten", "tcp"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
d = display.Display(DISP)
env = {**os.environ, "DISPLAY": DISP, "XDG_CONFIG_HOME": f"{BUILD}/xdg/config", "XDG_CACHE_HOME": f"{BUILD}/xdg/cache"}
env.pop("WAYLAND_DISPLAY", None)
br = subprocess.Popen([f"{BUILD}/src/out/Default/helium", "--ozone-platform=x11", f"--user-data-dir={prof}",
                       "--no-first-run", f"--remote-debugging-port={PORT}", "--window-size=1200,800",
                       "--window-position=0,0", page("p1"), page("p2"), page("p3")], env=env,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
fails = []

def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  ({detail})" if detail != "" else ""))
    if not ok: fails.append(name)

def wait(pred, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        try:
            v = pred()
            if v: return v
        except OSError:
            pass
        time.sleep(0.25)
    return pred()

def drag(x0, y0, x1, y1):
    """A real left-button drag from (x0, y0) to (x1, y1), screen pixels."""
    xtest.fake_input(d, X.MotionNotify, x=x0, y=y0); d.sync(); time.sleep(0.2)
    xtest.fake_input(d, X.ButtonPress, 1); d.sync(); time.sleep(0.2)
    steps = 12
    for i in range(1, steps + 1):
        xtest.fake_input(d, X.MotionNotify, x=int(x0 + (x1 - x0) * i / steps), y=int(y0 + (y1 - y0) * i / steps))
        d.sync(); time.sleep(0.06)
    # Hold still a moment with a small wiggle: the X drag protocol answers each move (XdndStatus) and the
    # drop is only delivered once the target has accepted.
    for dx in (2, -2, 0):
        xtest.fake_input(d, X.MotionNotify, x=x1 + dx, y=y1); d.sync(); time.sleep(0.25)
    xtest.fake_input(d, X.ButtonRelease, 1); d.sync(); time.sleep(0.8)

try:
    ver = wait(lambda: json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version")), 20)
    ws = WS(ver["webSocketDebuggerUrl"])
    targets = lambda: ws.call("Target.getTargets")["result"]["targetInfos"]
    side = wait(lambda: next((t for t in targets() if t["url"].startswith("chrome://helium-sidebar")), None), 15)
    check("sidebar page exists", bool(side))
    s = ws.call("Target.attachToTarget", {"targetId": side["targetId"], "flatten": True})["result"]["sessionId"]
    def ev(expr):
        r = ws.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True}, s)
        return r["result"]["result"].get("value")
    sr = "document.querySelector('helium-sidebar-app').shadowRoot"
    order = lambda: ev(f"[...{sr}.querySelectorAll('.scroll .tab .t')].map(e => e.textContent.trim())") or []
    check("three tabs listed", bool(wait(lambda: order() == ["p1", "p2", "p3"], 15)), order())

    ev("window.__m = null; addEventListener('mousemove', e => window.__m = [e.clientX, e.clientY])")
    probe = (60, 420)
    xtest.fake_input(d, X.MotionNotify, x=probe[0], y=probe[1]); d.sync()
    m = wait(lambda: ev("window.__m"), 5)
    check("pointer reaches the sidebar page", bool(m), m)
    ox, oy = probe[0] - m[0], probe[1] - m[1]

    def row(title):
        """Screen rect (left, top, right, bottom) of the row titled `title`."""
        r = ev(f"(r => [r.left, r.top, r.right, r.bottom])([...{sr}.querySelectorAll('.scroll .tab')]"
               f".find(e => e.querySelector('.t').textContent.trim() === {json.dumps(title)}).getBoundingClientRect())")
        return [r[0] + ox, r[1] + oy, r[2] + ox, r[3] + oy]

    def drag_rows(src, dst, frac):
        a, b = row(src), row(dst)
        drag(int(a[0] + 40), int((a[1] + a[3]) / 2), int(b[0] + 40), int(b[1] + (b[3] - b[1]) * frac))

    drag_rows("p1", "p3", 0.8)
    check("drop on lower half of p3 moves p1 after it", bool(wait(lambda: order() == ["p2", "p3", "p1"], 5)), order())
    drag_rows("p1", "p2", 0.2)
    check("drop on upper half of p2 moves p1 before it", bool(wait(lambda: order() == ["p1", "p2", "p3"], 5)), order())
    a = row("p1"); last = row("p3")
    drag(int(a[0] + 40), int((a[1] + a[3]) / 2), int(a[0] + 40), int(last[3] + 120))
    check("drop on the list's empty end moves p1 last", bool(wait(lambda: order() == ["p2", "p3", "p1"], 5)), order())
    # The browser agrees (not only the page): CDP's own target list in tab order is not exposed, so read the
    # sidebar again after a fresh snapshot (reload of the sidebar page rebuilds the list from the tab strip).
    ev("location.reload()")
    time.sleep(2)
    check("order survives a fresh read from the tab strip", bool(wait(lambda: order() == ["p2", "p3", "p1"], 10)), order())
except Exception:
    import traceback; traceback.print_exc(); fails.append("exception")
finally:
    if br.poll() is None: br.kill()
    xvfb.kill(); srv.shutdown()
print("RESULT", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
