#!/usr/bin/env python3
"""Copies from isolated tabs stay out of clipboard history (patch 0161).
In a private Xvfb display (never the real desktop) a normal tab and an isolated tab (--helium-isolated-tabs test
hook) each copy a marker text with document.execCommand('copy') (CDP userGesture gives the page activation).
The X CLIPBOARD selection is then read with Xlib:
  - both copies must work (the selection holds the tab's marker text)
  - the isolated copy must offer x-kde-passwordManagerHint = "secret" (Klipper/CopyQ then keep it out of history)
  - the normal copy must not (normal copies keep going to clipboard history)
Then the same for copies the browser makes itself (0163), with real X key/mouse input: the address bar
(Ctrl+L, Ctrl+C), the page context menu's "Copy link address" and Ctrl+Shift+C (copy page link, 0175).
Run from the project root: python3 -I scripts/test_isolated_clipboard.py"""
import http.server, json, os, shutil, subprocess, sys, threading, time, urllib.request

from Xlib import X, XK, Xatom, display
from Xlib.ext import xtest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, DISP = 9365, ":93"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

NORM, ISO = "NORMCLIP5521", "ISOCLIP7734"
class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        m = self.path.strip("/")
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(f"<title>{m}</title><p id=t>{m}</p><a id=l href=/LINK{m}>link</a>".encode())
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Page)
threading.Thread(target=srv.serve_forever, daemon=True).start()
# The isolated-tabs test switch takes a comma-separated list, so no data: URLs.
page = lambda m: f"http://127.0.0.1:{srv.server_address[1]}/{m}"
prof = f"{BUILD}/profile-test-clipboard"
shutil.rmtree(prof, ignore_errors=True); os.makedirs(f"{prof}/Default")
json.dump({"helium": {"completed_onboarding": True, "settings": {"a11y": {"copy_page_url_shortcut": True}}}}, open(f"{prof}/Default/Preferences", "w"))

xvfb = subprocess.Popen(["Xvfb", DISP, "-screen", "0", "1200x800x24", "-nolisten", "tcp"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
env = {**os.environ, "DISPLAY": DISP, "XDG_CONFIG_HOME": f"{BUILD}/xdg/config", "XDG_CACHE_HOME": f"{BUILD}/xdg/cache"}
env.pop("WAYLAND_DISPLAY", None)
br = subprocess.Popen([f"{BUILD}/src/out/Default/helium", "--ozone-platform=x11", f"--user-data-dir={prof}",
                       "--no-first-run", f"--remote-debugging-port={PORT}", "--window-size=1100,750",
                       "--helium-isolated-tabs=" + page(ISO), page(NORM)], env=env,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

d = display.Display(DISP)
win = d.screen().root.create_window(0, 0, 1, 1, 0, X.CopyFromParent)
CLIP, PROP = d.intern_atom("CLIPBOARD"), d.intern_atom("HPP_CLIP_TEST")
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

def selection(target):
    """CLIPBOARD converted to `target` (an atom name): (type name, bytes or atom list), or None."""
    if d.get_selection_owner(CLIP) == win: return None  # cleared by the test itself
    win.convert_selection(CLIP, d.intern_atom(target), PROP, X.CurrentTime); d.flush()
    end = time.time() + 5
    while time.time() < end:
        while d.pending_events():
            e = d.next_event()
            if e.type == X.SelectionNotify:
                if e.property == X.NONE: return None
                p = win.get_full_property(PROP, X.AnyPropertyType)
                return (d.get_atom_name(p.property_type), p.value) if p else None
        time.sleep(0.05)
    return None

def targets():
    r = selection("TARGETS")
    return [d.get_atom_name(a) for a in r[1]] if r else []

def text():
    r = selection("UTF8_STRING")
    return bytes(r[1]).decode() if r else None

try:
    ver = wait(lambda: json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version")), 20)
    ws = WS(ver["webSocketDebuggerUrl"])
    tabs = lambda: [t for t in ws.call("Target.getTargets")["result"]["targetInfos"] if t["type"] == "page"]
    find = lambda m: next((t for t in tabs() if m in t["url"]), None)
    check("both tabs open", bool(wait(lambda: find(NORM) and find(ISO), 15)))

    def copy_from(marker):
        t = find(marker)
        ws.call("Target.activateTarget", {"targetId": t["targetId"]})
        s = ws.call("Target.attachToTarget", {"targetId": t["targetId"], "flatten": True})["result"]["sessionId"]
        time.sleep(0.5)
        r = ws.call("Runtime.evaluate", {"expression": "getSelection().selectAllChildren(document.getElementById('t')),"
                                         " document.execCommand('copy')", "returnByValue": True,
                                         "userGesture": True}, s)
        return r["result"]["result"].get("value")

    for marker, isolated in ((NORM, False), (ISO, True)):
        kind = "isolated" if isolated else "normal"
        check(f"{kind} tab: copy command succeeds", copy_from(marker) is True)
        got = wait(lambda: (text() or "").strip() == marker, 5)
        check(f"{kind} tab: clipboard holds its text", bool(got), text())
        offered = targets()
        hint = "x-kde-passwordManagerHint" in offered
        if isolated:
            value = selection("x-kde-passwordManagerHint")
            check("isolated tab: copy offers x-kde-passwordManagerHint=secret",
                  hint and value and bytes(value[1]) == b"secret", offered)
        else:
            check("normal tab: copy does not offer the history hint", not hint, offered)

    # Copies the browser makes itself (0163): address bar (Ctrl+L, Ctrl+C) and the page's context menu
    # ("Copy link addr&ess", accelerator e), with real X input.
    def key(*names):
        codes = [d.keysym_to_keycode(XK.string_to_keysym(n)) for n in names]
        for c in codes: xtest.fake_input(d, X.KeyPress, c)
        for c in reversed(codes): xtest.fake_input(d, X.KeyRelease, c)
        d.sync(); time.sleep(0.4)
    def mouse(x, y, button=None):
        xtest.fake_input(d, X.MotionNotify, x=x, y=y); d.sync(); time.sleep(0.2)
        if button:
            xtest.fake_input(d, X.ButtonPress, button); xtest.fake_input(d, X.ButtonRelease, button)
            d.sync(); time.sleep(0.8)
    def hint_check(what, isolated, expect_text):
        got = wait(lambda: expect_text in (text() or ""), 5)
        check(f"{what}: clipboard holds it", bool(got), text())
        offered = targets(); hint = "x-kde-passwordManagerHint" in offered
        check(f"{what}: {'offers' if isolated else 'does not offer'} the history hint", hint == isolated)

    for marker, isolated in ((NORM, False), (ISO, True)):
        kind = "isolated" if isolated else "normal"
        t = find(marker)
        ws.call("Target.activateTarget", {"targetId": t["targetId"]})
        s = ws.call("Target.attachToTarget", {"targetId": t["targetId"], "flatten": True})["result"]["sessionId"]
        ev = lambda e: ws.call("Runtime.evaluate", {"expression": e, "returnByValue": True}, s)["result"]["result"].get("value")
        ev("window.__m = null; addEventListener('mousemove', e => window.__m = [e.clientX, e.clientY])")
        mouse(700, 400, 1)  # focus the window on the page
        m = wait(lambda: ev("window.__m"), 5)
        ox, oy = 700 - m[0], 400 - m[1]
        key("Control_L", "l"); key("Control_L", "c")
        hint_check(f"{kind} tab address bar copy", isolated, marker)
        r = ev("(r => [r.left + r.width / 2, r.top + r.height / 2])(document.getElementById('l').getBoundingClientRect())")
        mouse(int(r[0] + ox), int(r[1] + oy), 3)
        key("e")
        hint_check(f"{kind} tab context menu Copy link address", isolated, "LINK" + marker)
        key("Escape"); mouse(700, 400, 1)
        win.set_selection_owner(CLIP, X.CurrentTime); d.sync()  # clear, so the link copy above cannot pass this check
        key("Control_L", "Shift_L", "c")  # Copy page link shortcut (IDC_COPY_URL, 0175)
        hint_check(f"{kind} tab Ctrl+Shift+C copy page link", isolated, marker)
except Exception:
    import traceback; traceback.print_exc(); fails.append("exception")
finally:
    if br.poll() is None: br.kill()
    xvfb.kill(); srv.shutdown()
print("RESULT", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
