#!/usr/bin/env python3
"""Does the page info bubble say which fingerprinting APIs a page used (fingerprint report)?
Two local pages run in a private Xvfb display (never the real desktop): fp.example reads canvas pixels,
WebGL parameters, offline-rendered audio and the CPU count; plain.example uses none of them. The bubble is
opened on each and saved as build/fingerprint-fp.png and build/fingerprint-plain.png: the "Fingerprinting
protection" row must read "This page read canvas, WebGL, audio and device details" (WebGL only if the GPU
emulation is available) and "No common fingerprinting calls seen". Then fp.example, plain.example and Back
in one tab: build/fingerprint-back.png must show fp.example's report again. Native UI: check the pictures.
Run from the project root: python3 -I scripts/test_fingerprint_report.py"""
import sys, ctypes, http.server, json, os, shutil, subprocess, threading, time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, HTTP, DISP = 9354, 8094, ":91"
PAGE_INFO_ICON = (115, 47)  # at --force-device-scale-factor=1, 1200x800 window
SHOT = "1"  # this test is only screenshots
PAGES = {
    "fp.example": b"""<title>fp</title><script>
      const c = document.createElement('canvas'); c.getContext('2d').fillText('fp', 2, 10); c.toDataURL();
      const gl = document.createElement('canvas').getContext('webgl'); if (gl) gl.getParameter(gl.VERSION);
      new OfflineAudioContext(1, 4410, 44100).startRendering();
      navigator.hardwareConcurrency;</script><h1>fingerprinting page</h1>""",
    "plain.example": b"<title>plain</title><h1>plain page</h1>",
}

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
    if SHOT:
        subprocess.run(["import", "-display", DISP, "-window", "root", f"{BUILD}/fingerprint-{name}.png"])

class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(PAGES[self.headers["Host"].split(":")[0]])
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", HTTP), Page)
threading.Thread(target=srv.serve_forever, daemon=True).start()
prof = os.path.join(BUILD, "profile-fingerprint")
shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof + "/Default")
with open(prof + "/Default/Preferences", "w") as f:  # plain-http pages: HTTPS-First off
    json.dump({"helium": {"completed_onboarding": True, "privacy_mode": "medium", "privacy_mode_applied": "medium",
                          "services": {"schema_version": 1, "user_consented": True}},
               "https_only_mode_enabled": False, "https_first_balanced_mode_enabled": False}, f)
xvfb = subprocess.Popen(['Xvfb', DISP, '-screen', '0', '1200x800x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
env = dict(os.environ, DISPLAY=DISP, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
p = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--ozone-platform=x11",
                      "--no-sandbox", "--no-first-run", "--force-device-scale-factor=1", "--window-size=1200,800",
                      "--window-position=0,0", "--remote-debugging-port=%d" % PORT,
                      f"--host-resolver-rules=MAP * 127.0.0.1:{HTTP}", "about:blank"],
                     env=env, stdout=subprocess.DEVNULL, stderr=open(BUILD + "/test-fingerprint.log", "w"))
try:
    for _ in range(60):
        try: ver = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version')); break
        except OSError: time.sleep(0.5)
    ws = WS(ver['webSocketDebuggerUrl'])
    for host in PAGES:
        t = ws.call('Target.createTarget', {'url': f"http://{host}/"})['result']['targetId']
        time.sleep(4)  # use counters reach the browser in batches
        xinput(click=PAGE_INFO_ICON); time.sleep(1.5); shot(host.split(".")[0])
        xinput(key="Escape"); ws.call('Target.closeTarget', {'targetId': t}); time.sleep(1)
    # Back restores fp.example from the back/forward cache: it must keep its own report.
    t = ws.call('Target.createTarget', {'url': "http://fp.example/"})['result']['targetId']
    s = ws.call('Target.attachToTarget', {'targetId': t, 'flatten': True})['result']['sessionId']
    time.sleep(4)
    ws.call('Page.navigate', {'url': "http://plain.example/"}, s); time.sleep(2)
    ws.call('Runtime.evaluate', {'expression': "history.back()"}, s); time.sleep(3)
    xinput(click=PAGE_INFO_ICON); time.sleep(1.5); shot("back"); xinput(key="Escape")
finally:
    p.terminate()
    try: p.wait(20)
    except subprocess.TimeoutExpired: p.kill()
    xvfb.terminate(); srv.shutdown()
print("Saved build/fingerprint-fp.png, -plain.png and -back.png; check the Fingerprinting protection row.")
