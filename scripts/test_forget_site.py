#!/usr/bin/env python3
"""Does "Forget this site" (page info bubble) wipe one site and nothing else?
www.example.com, sub.example.com and example.org (all mapped to a local server) each store a cookie and
localStorage and get a history entry. Then the real button is clicked in a private Xvfb display (never
the real desktop) on www.example.com and the dialog is accepted with Enter. Afterwards example.com and its
subdomains must have no cookies or history left, every tab on them (sub.example.com too) must have moved to
the new tab page, and example.org must keep its cookie, storage and history.
SHOT=1 saves screenshots of each step to build/forget-*.png (to re-find the click spots after UI changes);
GDB=1 runs the browser under gdb and writes a backtrace to build/test-forget.gdb if it crashes.
Run from the project root: python3 -I scripts/test_forget_site.py"""
import base64, ctypes, http.server, json, os, shutil, socket, sqlite3, struct, subprocess, threading, time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, HTTP, DISP = 9349, 8096, ":94"
SITES = ["www.example.com", "sub.example.com", "example.org"]
# Click spots at --force-device-scale-factor=1 in a 1200x800 window (from SHOT=1 screenshots).
PAGE_INFO_ICON = (115, 47)
FORGET_BUTTON = (205, 431)

def connect(url):
    host, rest = url[5:].split('/', 1)
    s = socket.create_connection(("127.0.0.1", int(host.split(':')[1])), timeout=30)
    key = base64.b64encode(os.urandom(16)).decode()
    s.sendall(f'GET /{rest} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
              f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'.encode())
    buf = b''
    while b'\r\n\r\n' not in buf:
        buf += s.recv(4096)
    assert b' 101 ' in buf.split(b'\r\n')[0], buf
    return s, buf.split(b'\r\n\r\n', 1)[1]

class WS:
    def __init__(self, url):
        self.s, self.buf = connect(url); self.n = 0
    def send(self, method, params=None, session=None):
        self.n += 1
        d = {'id': self.n, 'method': method, 'params': params or {}}
        if session: d['sessionId'] = session
        data = json.dumps(d).encode(); mask = os.urandom(4)
        hdr = b'\x81' + (bytes([0x80 | len(data)]) if len(data) < 126 else b'\xfe' + struct.pack('>H', len(data)))
        self.s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))
        return self.n
    def _need(self, n):
        while len(self.buf) < n: self.buf += self.s.recv(65536)
        out, self.buf = self.buf[:n], self.buf[n:]; return out
    def recv(self):
        b1, b2 = self._need(2); ln = b2 & 0x7f
        if ln == 126: ln = struct.unpack('>H', self._need(2))[0]
        elif ln == 127: ln = struct.unpack('>Q', self._need(8))[0]
        return json.loads(self._need(ln))
    def call(self, method, params=None, session=None):
        i = self.send(method, params, session)
        while True:
            m = self.recv()
            if m.get('id') == i: return m

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
        subprocess.run(["import", "-display", DISP, "-window", "root", f"{BUILD}/forget-{name}.png"])

class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        host = self.headers["Host"].split(":")[0]
        body = (f"<title>{host}</title><h1>{host}</h1><script>localStorage.setItem('k', '{host}')</script>").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Set-Cookie", f"c={host}; Max-Age=86400; Path=/")
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", HTTP), Page)
threading.Thread(target=srv.serve_forever, daemon=True).start()
prof = os.path.join(BUILD, "profile-forget")
shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof + "/Default")
with open(prof + "/Default/Preferences", "w") as f:
    # HTTPS-First would block the plain-http test sites; "applied" keeps the preset from turning it back on.
    json.dump({"helium": {"completed_onboarding": True, "privacy_mode": "medium", "privacy_mode_applied": "medium",
                          "services": {"schema_version": 1, "user_consented": True}},
               "https_only_mode_enabled": False, "https_first_balanced_mode_enabled": False}, f)
xvfb = subprocess.Popen(['Xvfb', DISP, '-screen', '0', '1200x800x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
env = dict(os.environ, DISPLAY=DISP, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
p = subprocess.Popen((["gdb", "-batch", "-ex", "set follow-fork-mode parent", "-ex", "run", "-ex", "bt 30", "--args"] if os.environ.get("GDB") else []) + [BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--ozone-platform=x11",
                      "--no-sandbox", "--disable-gpu", "--no-first-run", "--force-device-scale-factor=1",
                      "--window-size=1200,800", "--window-position=0,0", "--remote-debugging-port=%d" % PORT,
                      f"--host-resolver-rules=MAP * 127.0.0.1:{HTTP}", "about:blank"],
                     env=env, stdout=open(BUILD + "/test-forget.gdb", "w"), stderr=open(BUILD + "/test-forget.log", "w"))
results = []
try:
    for _ in range(60):
        try: ver = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version')); break
        except OSError: time.sleep(0.5)
    ws = WS(ver['webSocketDebuggerUrl'])
    tabs = {}
    for host in SITES:  # the last tab opened (example.org) is in front; www.example.com is activated below
        t = ws.call('Target.createTarget', {'url': f"http://{host}/"})['result']['targetId']
        tabs[host] = (t, ws.call('Target.attachToTarget', {'targetId': t, 'flatten': True})['result']['sessionId'])
    time.sleep(3)
    def ev(host, js):
        r = ws.call('Runtime.evaluate', {'expression': js, 'returnByValue': True}, tabs[host][1])
        return r.get('result', {}).get('result', {}).get('value')
    def cookies():
        got = ws.call('Storage.getCookies')['result']['cookies']
        return sorted(c['domain'] for c in got if c['name'] == 'c')
    results.append(("cookies before", cookies(), sorted(SITES)))
    ws.call('Target.activateTarget', {'targetId': tabs["www.example.com"][0]}); time.sleep(1)
    shot("1-page")
    xinput(click=PAGE_INFO_ICON); time.sleep(1.5); shot("2-bubble")
    if FORGET_BUTTON:
        xinput(click=FORGET_BUTTON); time.sleep(1.5); shot("3-dialog")
        xinput(key="Return"); time.sleep(15); shot("4-done")  # history commits to disk every ~10 s
    results.append(("cookies after", cookies(), ["example.org"]))
    for host in ("www.example.com", "sub.example.com"):
        results.append((f"tab {host} left", ev(host, "location.protocol"), "chrome:"))
    results.append(("localStorage example.org", ev("example.org", "localStorage.getItem('k')"), "example.org"))
finally:
    p.terminate()
    try: p.wait(20)
    except subprocess.TimeoutExpired: p.kill()
    xvfb.terminate(); srv.shutdown()

db = sqlite3.connect(f"file:{prof}/Default/History?mode=ro", uri=True)
left = sorted({u.split('/')[2] for (u,) in db.execute("SELECT url FROM urls") if u.startswith("http")})
results.append(("history hosts after", left, ["example.org"]))
ok = len(results) == 6
for name, got, want in results:
    print("%-30s %-45s%s" % (name, got, "" if got == want else "  <-- FAIL (want %s)" % want))
    ok &= got == want
print("PASS" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
