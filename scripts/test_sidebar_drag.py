#!/usr/bin/env python3
"""Window drag from the web sidebar's top row (patch 0159).
In a private Xvfb display (never the real desktop) this script stands in for a window manager: it advertises
EWMH support as "KWin" and watches the root window for _NET_WM_MOVERESIZE, the message Chromium sends the window
manager when the user grabs a title bar. Real mouse presses are injected with XTest (not element.click(), which
never reaches the frame's hit test) at:
  - the empty part of the top row        -> must ask for a window move (direction 8, _NET_WM_MOVERESIZE_MOVE)
  - the empty band above its buttons     -> must too (0160)
  - the Reload button in that row        -> must not (the button stays clickable)
  - the tab list below the row           -> must not
  - the web page                         -> must not
The sidebar page's screen offset is measured, not guessed: a real mouse move is read back as clientX/clientY.
Run from the project root: python3 -I scripts/test_sidebar_drag.py"""
import json, os, shutil, subprocess, sys, time, urllib.request

from Xlib import X, display
from Xlib.ext import xtest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, DISP = 9364, ":94"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

prof = f"{BUILD}/profile-test-drag"
shutil.rmtree(prof, ignore_errors=True); os.makedirs(f"{prof}/Default")
json.dump({"helium": {"completed_onboarding": True, "browser": {"layout": 2, "zen_mode": False}},
           "browser": {"custom_chrome_frame": True},
           "vertical_tabs": {"collapsed_state": False, "uncollapsed_width": 232}},
          open(f"{prof}/Default/Preferences", "w"))

xvfb = subprocess.Popen(["Xvfb", DISP, "-screen", "0", "1400x900x24", "-nolisten", "tcp"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)

# The stand-in window manager: enough EWMH for Chromium to use its own frame and send move requests.
d = display.Display(DISP)
root = d.screen().root
atom = lambda n: d.intern_atom(n)
chk = root.create_window(0, 0, 1, 1, 0, X.CopyFromParent)
for w in (root, chk):
    w.change_property(atom("_NET_SUPPORTING_WM_CHECK"), atom("WINDOW"), 32, [chk.id])
chk.change_property(atom("_NET_WM_NAME"), atom("UTF8_STRING"), 8, b"KWin")
root.change_property(atom("_NET_SUPPORTED"), atom("ATOM"), 32,
                     [atom("_NET_WM_MOVERESIZE"), atom("_NET_WM_STATE"), atom("_NET_SUPPORTING_WM_CHECK")])
root.change_attributes(event_mask=X.SubstructureNotifyMask)
d.sync()
MOVERESIZE = atom("_NET_WM_MOVERESIZE")

env = {**os.environ, "DISPLAY": DISP, "XDG_CONFIG_HOME": f"{BUILD}/xdg/config", "XDG_CACHE_HOME": f"{BUILD}/xdg/cache"}
env.pop("WAYLAND_DISPLAY", None)
br = subprocess.Popen([f"{BUILD}/src/out/Default/helium", "--ozone-platform=x11", f"--user-data-dir={prof}",
                       "--no-first-run", f"--remote-debugging-port={PORT}", "--window-size=1200,800",
                       "--window-position=0,0", "data:text/html,<title>page</title>page"], env=env,
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

def drain():
    """Move requests seen since the last call (their direction values)."""
    seen = []
    while d.pending_events():
        e = d.next_event()
        if e.type == X.ClientMessage and e.client_type == MOVERESIZE:
            seen.append(e.data[1][2])
    return seen

def press_at(x, y):
    """A real left click at screen (x, y); returns the move requests it caused."""
    xtest.fake_input(d, X.MotionNotify, x=x, y=y); d.sync(); time.sleep(0.2)
    drain()
    xtest.fake_input(d, X.ButtonPress, 1); d.sync(); time.sleep(0.3)
    # A title-bar press only becomes a move once the pointer passes the drag threshold.
    for step in range(1, 6):
        xtest.fake_input(d, X.MotionNotify, x=x + 6 * step, y=y + 3 * step); d.sync(); time.sleep(0.05)
    time.sleep(0.4)
    xtest.fake_input(d, X.ButtonRelease, 1); d.sync(); time.sleep(0.3)
    d.sync()
    return drain()

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
    rect = lambda sel: ev(f"(r => r && [r.left, r.top, r.right, r.bottom])"
                          f"({sr}.querySelector({json.dumps(sel)})?.getBoundingClientRect())")
    wait(lambda: rect("header.row1"), 10)
    time.sleep(1.5)  # first layout reported to the browser

    # Page pixel -> screen pixel: move the real pointer into the sidebar and read it back.
    ev("window.__m = null; addEventListener('mousemove', e => window.__m = [e.clientX, e.clientY])")
    probe = (60, 420)
    xtest.fake_input(d, X.MotionNotify, x=probe[0], y=probe[1]); d.sync()
    m = wait(lambda: ev("window.__m"), 5)
    check("pointer reaches the sidebar page", bool(m), m)
    ox, oy = probe[0] - m[0], probe[1] - m[1]
    scr = lambda px, py: (int(px + ox), int(py + oy))

    row, nav, ctl = rect("header.row1"), rect("header.row1 .nav"), rect("header.row1 .winctl")
    reload_btn = rect("[aria-label='Reload']")
    print(f"offset ({ox},{oy}) row {row} nav {nav} winctl {ctl}")
    gap_x = (nav[2] + ctl[0]) / 2 if ctl else (nav[2] + row[2]) / 2
    mid_y = (row[1] + row[3]) / 2

    got = press_at(*scr(gap_x, mid_y))
    check("empty part of the top row moves the window", 8 in got, got)
    got = press_at(*scr(100, (row[1] + nav[1]) / 2))
    check("band above the row's buttons moves the window (0160)", 8 in got, got)
    got = press_at(*scr((reload_btn[0] + reload_btn[2]) / 2, (reload_btn[1] + reload_btn[3]) / 2))
    check("Reload button in the row does not move the window", not got, got)
    got = press_at(*scr(gap_x, row[3] + 250))
    check("tab list does not move the window", not got, got)
    got = press_at(700, 450)
    check("web page does not move the window", not got, got)
except Exception:
    import traceback; traceback.print_exc(); fails.append("exception")
finally:
    if br.poll() is None: br.kill()
    xvfb.kill()
print("RESULT", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
