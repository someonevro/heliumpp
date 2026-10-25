#!/usr/bin/env python3
"""Does closing a window with a download running ask first, inside the browser window?
In a private Xvfb display (never the real desktop) a slow download runs, then Ctrl+Shift+W closes the
window. The browser must stay open, the warning must be drawn inside the window (no separate top-level
dialog window, which Wayland compositors may place out of sight), and "Continue downloading" (the default,
Enter) must keep the browser and the download going. Screenshots: build/dlclose-*.png.
Run from the project root: python3 -I scripts/test_close_with_download.py"""
import sys, ctypes, http.server, json, os, shutil, subprocess, threading, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, HTTP, DISP = 9356, 8092, ":89"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

def xinput(key=None, click=None):  # real input on the Xvfb display, so it reaches browser UI
    x11, xtst = ctypes.CDLL('libX11.so.6'), ctypes.CDLL('libXtst.so.6')
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XStringToKeysym.restype = ctypes.c_ulong
    x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
    xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
    xtst.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
    for f in (x11.XFlush, x11.XCloseDisplay): f.argtypes = [ctypes.c_void_p]
    d = x11.XOpenDisplay(DISP.encode())
    if key:
        code = x11.XKeysymToKeycode(d, x11.XStringToKeysym(key.encode()))
        xtst.XTestFakeKeyEvent(d, code, 1, 0); xtst.XTestFakeKeyEvent(d, code, 0, 0)
    if click:
        xtst.XTestFakeMotionEvent(d, -1, click[0], click[1], 0); x11.XFlush(d); time.sleep(0.3)
        xtst.XTestFakeButtonEvent(d, 1, 1, 0); xtst.XTestFakeButtonEvent(d, 1, 0, 0)
    x11.XFlush(d); x11.XCloseDisplay(d)

def shot(name):
    if True:
        subprocess.run(["import", "-display", DISP, "-window", "root", f"{BUILD}/dlclose-{name}.png"])


def combo(*keys):
    x11, xtst = ctypes.CDLL('libX11.so.6'), ctypes.CDLL('libXtst.so.6')
    x11.XOpenDisplay.restype = ctypes.c_void_p; x11.XStringToKeysym.restype = ctypes.c_ulong
    x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
    for f in (x11.XFlush, x11.XCloseDisplay): f.argtypes = [ctypes.c_void_p]
    d = x11.XOpenDisplay(DISP.encode()); codes = [x11.XKeysymToKeycode(d, x11.XStringToKeysym(k.encode())) for k in keys]
    for c in codes: xtst.XTestFakeKeyEvent(d, c, 1, 0)
    for c in reversed(codes): xtst.XTestFakeKeyEvent(d, c, 0, 0)
    x11.XFlush(d); x11.XCloseDisplay(d)
class XWindowAttributes(ctypes.Structure):  # Xlib's struct, only map_state is read
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int), ("width", ctypes.c_int), ("height", ctypes.c_int),
                ("border_width", ctypes.c_int), ("depth", ctypes.c_int), ("visual", ctypes.c_void_p),
                ("root", ctypes.c_ulong), ("c_class", ctypes.c_int), ("bit_gravity", ctypes.c_int),
                ("win_gravity", ctypes.c_int), ("backing_store", ctypes.c_int), ("backing_planes", ctypes.c_ulong),
                ("backing_pixel", ctypes.c_ulong), ("save_under", ctypes.c_int), ("colormap", ctypes.c_ulong),
                ("map_installed", ctypes.c_int), ("map_state", ctypes.c_int), ("all_event_masks", ctypes.c_long),
                ("your_event_mask", ctypes.c_long), ("do_not_propagate_mask", ctypes.c_long),
                ("override_redirect", ctypes.c_int), ("screen", ctypes.c_void_p)]

def visible_toplevels():  # mapped top-level X windows: a separate dialog window adds one
    x11 = ctypes.CDLL('libX11.so.6')
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XDefaultRootWindow.restype = ctypes.c_ulong; x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x11.XQueryTree.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
                               ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)), ctypes.POINTER(ctypes.c_uint)]
    x11.XGetWindowAttributes.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(XWindowAttributes)]
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    d = x11.XOpenDisplay(DISP.encode()); root, parent = ctypes.c_ulong(), ctypes.c_ulong()
    kids, n = ctypes.POINTER(ctypes.c_ulong)(), ctypes.c_uint()
    x11.XQueryTree(d, x11.XDefaultRootWindow(d), ctypes.byref(root), ctypes.byref(parent), ctypes.byref(kids), ctypes.byref(n))
    count = 0
    for i in range(n.value):
        attrs = XWindowAttributes()
        if x11.XGetWindowAttributes(d, kids[i], ctypes.byref(attrs)) and attrs.map_state == 2:  # IsViewable
            count += 1
    x11.XCloseDisplay(d)
    return count

class Slow(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", "attachment; filename=big.bin"); self.send_header("Content-Length", str(200*1024*1024)); self.end_headers()
        try:
            for _ in range(20000): self.wfile.write(b"x" * 10240); time.sleep(0.05)
        except Exception: pass
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", HTTP), Slow); threading.Thread(target=srv.serve_forever, daemon=True).start()
prof = BUILD + "/profile-dlclose"; shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof + "/Default")
shutil.rmtree(BUILD + "/dlclose-downloads", ignore_errors=True); os.makedirs(BUILD + "/dlclose-downloads")
json.dump({"helium": {"completed_onboarding": True, "privacy_mode": "medium", "privacy_mode_applied": "medium", "services": {"schema_version": 1, "user_consented": True}},
           "https_only_mode_enabled": False, "https_first_balanced_mode_enabled": False,
           "download": {"default_directory": BUILD + "/dlclose-downloads", "prompt_for_download": False}}, open(prof + "/Default/Preferences", "w"))
xvfb = subprocess.Popen(["Xvfb", DISP, "-screen", "0", "1200x800x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
env = dict(os.environ, DISPLAY=DISP, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
p = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--ozone-platform=x11", "--no-sandbox", "--disable-gpu", "--no-first-run",
     "--force-device-scale-factor=1", "--window-size=1200,800", "--window-position=0,0", "--remote-debugging-port=%d" % PORT, "about:blank"],
     env=env, stdout=subprocess.DEVNULL, stderr=open(BUILD + "/dlclose.log", "w"))
results = []
try:
    for _ in range(60):
        try: ver = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version")); break
        except OSError: time.sleep(0.5)
    ws = WS(ver["webSocketDebuggerUrl"])
    t = ws.call("Target.createTarget", {"url": f"http://127.0.0.1:{HTTP}/big.bin"})["result"]["targetId"]
    time.sleep(4); shot("1-downloading"); before = visible_toplevels()
    combo("Control_L", "Shift_L", "w"); time.sleep(3); shot("2-after-close")
    results.append(("close blocked, browser still running", p.poll() is None, True))
    results.append(("no separate dialog window", visible_toplevels() - before, 0))
    xinput(key="Return"); time.sleep(2)  # default button: Continue downloading
    part = [f for f in os.listdir(BUILD + "/dlclose-downloads") if f.endswith(".crdownload")]
    size = os.path.getsize(os.path.join(BUILD + "/dlclose-downloads", part[0])) if part else 0
    time.sleep(2)
    grew = bool(part) and os.path.getsize(os.path.join(BUILD + "/dlclose-downloads", part[0])) > size
    results.append(("Continue keeps browser and download", p.poll() is None and grew, True))
finally:
    p.kill(); xvfb.terminate(); srv.shutdown()

ok = len(results) == 3
for name, got, want in results:
    print("%-38s %s%s" % (name, got, "" if got == want else "  <-- FAIL (want %s)" % want))
    ok &= got == want
print("PASS" if ok else "FAIL")
raise SystemExit(0 if ok else 1)

