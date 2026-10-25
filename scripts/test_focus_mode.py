#!/usr/bin/env python3
"""Does focus mode (page info switch) hide YouTube's Shorts and recommendations, and only those?
A fake www.youtube.com (local HTTPS server, self-signed certificate) has an "up next" column, a Shorts shelf
and a normal video. In a private Xvfb display (never the real desktop) the page info switch is clicked:
the column and shelf must hide at once, stay hidden after a reload, and come back when switched off.
SHOT=1 saves screenshots of each step to build/focus-*.png (to re-find the click spots after UI changes).
Run from the project root: python3 -I scripts/test_focus_mode.py"""
import sys, ctypes, http.server, json, os, shutil, ssl, subprocess, threading, time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, HTTPS, DISP = 9351, 8443, ":93"
# Click spots at --force-device-scale-factor=1 in a 1200x800 window (from SHOT=1 screenshots).
PAGE_INFO_ICON = (115, 47)
FOCUS_BUTTON = (200, 526)
PAGE = (b'<title>YouTube</title><ytd-video-renderer id="normal">normal video</ytd-video-renderer>'
        b'<grid-shelf-view-model id="shelf"><ytm-shorts-lockup-view-model>a short</ytm-shorts-lockup-view-model>'
        b'</grid-shelf-view-model><div id="related">up next</div>')

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
    if os.environ.get("SHOT"):
        subprocess.run(["import", "-display", DISP, "-window", "root", f"{BUILD}/focus-{name}.png"])

class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(PAGE)
    def log_message(self, *a): pass

cert = os.path.join(BUILD, "focus-cert.pem")
if not os.path.exists(cert):
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3650", "-subj", "/CN=www.youtube.com",
                    "-keyout", cert, "-out", cert], check=True, capture_output=True)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", HTTPS), Page)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(cert)
srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
threading.Thread(target=srv.serve_forever, daemon=True).start()
prof = os.path.join(BUILD, "profile-focus")
shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof + "/Default")
with open(prof + "/Default/Preferences", "w") as f:
    json.dump({"helium": {"completed_onboarding": True, "privacy_mode": "medium", "privacy_mode_applied": "medium",
                          "services": {"schema_version": 1, "user_consented": True}}}, f)
xvfb = subprocess.Popen(['Xvfb', DISP, '-screen', '0', '1200x800x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
env = dict(os.environ, DISPLAY=DISP, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
p = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--ozone-platform=x11",
                      "--no-sandbox", "--disable-gpu", "--no-first-run", "--force-device-scale-factor=1",
                      "--window-size=1200,800", "--window-position=0,0", "--remote-debugging-port=%d" % PORT,
                      "--ignore-certificate-errors", f"--host-resolver-rules=MAP * 127.0.0.1:{HTTPS}", "about:blank"],
                     env=env, stdout=subprocess.DEVNULL, stderr=open(BUILD + "/test-focus.log", "w"))
results = []
try:
    for _ in range(60):
        try: ver = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version')); break
        except OSError: time.sleep(0.5)
    ws = WS(ver['webSocketDebuggerUrl'])
    t = ws.call('Target.createTarget', {'url': "https://www.youtube.com/"})['result']['targetId']
    s = ws.call('Target.attachToTarget', {'targetId': t, 'flatten': True})['result']['sessionId']
    time.sleep(3)
    def shown():  # which of the three elements are visible
        js = "['normal','shelf','related'].filter(id => getComputedStyle(document.getElementById(id)).display != 'none')"
        r = ws.call('Runtime.evaluate', {'expression': js, 'returnByValue': True}, s)
        return r.get('result', {}).get('result', {}).get('value')
    def toggle(name):
        xinput(click=PAGE_INFO_ICON); time.sleep(1.5); shot(name)
        if FOCUS_BUTTON:
            xinput(click=FOCUS_BUTTON); time.sleep(1); shot(name + "-after")
        xinput(key="Escape"); time.sleep(0.5)
    results.append(("off at start", shown(), ["normal", "shelf", "related"]))
    toggle("1-on")
    results.append(("switched on", shown(), ["normal"]))
    ws.call('Page.reload', {}, s); time.sleep(3)
    results.append(("after reload", shown(), ["normal"]))
    toggle("2-off")
    results.append(("switched off", shown(), ["normal", "shelf", "related"]))
finally:
    p.terminate()
    try: p.wait(20)
    except subprocess.TimeoutExpired: p.kill()
    xvfb.terminate(); srv.shutdown()

ok = len(results) == 4
for name, got, want in results:
    print("%-15s %-30s%s" % (name, got, "" if got == want else "  <-- FAIL (want %s)" % want))
    ok &= got == want
print("PASS" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
