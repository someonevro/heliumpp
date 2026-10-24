#!/usr/bin/env python3
"""Does "Copy clean link" in the link context menu drop tracking parameters (and only those)?
Runs the browser in a private Xvfb display (never the real desktop), right-clicks each link over DevTools,
presses the item's mnemonic "l" through the X test extension, then reads the clipboard in the page.
A link without trackers must not get the item: the clipboard keeps its sentinel.
Run from the project root: python3 -I scripts/test_clean_link.py"""
import base64, ctypes, functools, http.server, json, os, shutil, socket, struct, subprocess, threading, time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, HTTP, DISP = 9348, 8097, ":95"
CASES = [  # link, what "Copy clean link" must copy (None: item absent)
    ("https://example.com/a?id=5&utm_source=x&fbclid=y#frag", "https://example.com/a?id=5#frag"),
    ("https://www.youtube.com/watch?v=abc&si=XYZ", "https://www.youtube.com/watch?v=abc"),
    ("https://example.org/p?si=keep&UTM_Medium=x", "https://example.org/p?si=keep"),
    ("https://example.com/x?utm_a=1&gclid=2", "https://example.com/x"),
    ("https://example.com/clean?q=1", None),
]
ROW = 60

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

def press(key):  # a real key press on the Xvfb display, so it reaches the native menu
    x11, xtst = ctypes.CDLL('libX11.so.6'), ctypes.CDLL('libXtst.so.6')
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XStringToKeysym.restype = ctypes.c_ulong
    x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
    for f in (x11.XFlush, x11.XCloseDisplay): f.argtypes = [ctypes.c_void_p]
    d = x11.XOpenDisplay(DISP.encode())
    code = x11.XKeysymToKeycode(d, x11.XStringToKeysym(key.encode()))
    xtst.XTestFakeKeyEvent(d, code, 1, 0); xtst.XTestFakeKeyEvent(d, code, 0, 0)
    x11.XFlush(d); x11.XCloseDisplay(d)

www = os.path.join(BUILD, "cleanlink-www"); os.makedirs(www, exist_ok=True)
with open(os.path.join(www, "index.html"), "w") as f:
    f.write('<style>body{margin:0}a{display:block;height:%dpx;width:600px}</style>' % ROW
            + ''.join('<a href="%s">link %d</a>' % (u.replace('&', '&amp;'), i) for i, (u, _) in enumerate(CASES)))
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", HTTP), functools.partial(Quiet, directory=www))
threading.Thread(target=srv.serve_forever, daemon=True).start()

prof = os.path.join(BUILD, "profile-cleanlink")
shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof + "/Default")
with open(prof + "/Default/Preferences", "w") as f:
    json.dump({"helium": {"completed_onboarding": True, "privacy_mode": "medium",
                          "services": {"schema_version": 1, "user_consented": True}}}, f)
xvfb = subprocess.Popen(['Xvfb', DISP, '-screen', '0', '1200x800x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
env = dict(os.environ, DISPLAY=DISP, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
p = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--ozone-platform=x11",
                      "--no-sandbox", "--disable-gpu", "--no-first-run", "--force-device-scale-factor=1",
                      "--window-size=1200,800", "--remote-debugging-port=%d" % PORT, "about:blank"],
                     env=env, stdout=subprocess.DEVNULL, stderr=open(BUILD + "/test-cleanlink.log", "w"))
results = []
try:
    for _ in range(60):
        try: ver = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version')); break
        except OSError: time.sleep(0.5)
    ws = WS(ver['webSocketDebuggerUrl'])
    origin = f"http://127.0.0.1:{HTTP}"
    ws.call('Browser.grantPermissions', {'origin': origin, 'permissions': ['clipboardReadWrite', 'clipboardSanitizedWrite']})
    t = ws.call('Target.createTarget', {'url': origin + "/index.html"})['result']['targetId']
    s = ws.call('Target.attachToTarget', {'targetId': t, 'flatten': True})['result']['sessionId']
    def ev(js):
        r = ws.call('Runtime.evaluate', {'expression': js, 'returnByValue': True, 'awaitPromise': True}, s)
        return r.get('result', {}).get('result', {}).get('value')
    time.sleep(3)
    for i, (link, want) in enumerate(CASES):
        ev("navigator.clipboard.writeText('sentinel')")
        y = i * ROW + ROW // 2
        for kind in ('mousePressed', 'mouseReleased'):
            ws.call('Input.dispatchMouseEvent', {'type': kind, 'x': 100, 'y': y, 'button': 'right', 'clickCount': 1}, s)
        time.sleep(1); press('l'); time.sleep(1); press('Escape'); time.sleep(0.5)
        got = ev("navigator.clipboard.readText()")
        results.append((link, got, want if want else 'sentinel'))
finally:
    p.terminate()
    try: p.wait(20)
    except subprocess.TimeoutExpired: p.kill()
    xvfb.terminate(); srv.shutdown()

ok = len(results) == len(CASES)
for link, got, want in results:
    print("%-55s -> %s%s" % (link, got, "" if got == want else "  <-- FAIL (want %s)" % want))
    ok &= got == want
print("PASS" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
