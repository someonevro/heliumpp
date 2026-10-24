#!/usr/bin/env python3
"""Does "Insert throwaway email (addy.io)" create an alias and type it into the field?
A local sign-up page (signup.example) and a local HTTPS server playing app.addy.io run in a private Xvfb
display (never the real desktop). The menu item asks for the API key (typed into the dialog), then the
alias appears in the email field; a second use gives a new alias. addy.io must get the key as a Bearer token
with X-Requested-With, the account's default domain/format and the site as description. This display has no
system keyring, so the key must not be saved at all (Chromium's fallback key only scrambles): the second
use asks again, and the profile holds no key.
SHOT=1 saves build/addy-*.png. Run from the project root: python3 -I scripts/test_addy_alias.py"""
import base64, ctypes, http.server, json, os, shutil, socket, ssl, struct, subprocess, threading, time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, HTTP, HTTPS, DISP = 9355, 8093, 8445, ":90"
KEY = "testkey123"
SIGNUP = b'<title>Sign up</title><input id="email" type="email" style="margin:40px;width:300px">'
requests = []  # (method, path, Authorization, X-Requested-With, body)
aliases = iter(["first.alias@anonaddy.me", "second.alias@anonaddy.me"])

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
        subprocess.run(["import", "-display", DISP, "-window", "root", f"{BUILD}/addy-{name}.png"])

class Addy(http.server.BaseHTTPRequestHandler):
    def reply(self, code, data):
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps({"data": data}).encode())
    def log(self, body=None):
        requests.append((self.command, self.path, self.headers.get("Authorization"),
                         self.headers.get("X-Requested-With"), body))
    def do_GET(self):
        self.log()
        self.reply(200, {"default_alias_domain": "anonaddy.me", "default_alias_format": "random_words"})
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        self.log(body)
        self.reply(201, {"email": next(aliases)})
    def log_message(self, *a): pass

class Site(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(SIGNUP)
    def log_message(self, *a): pass

cert = os.path.join(BUILD, "addy-cert.pem")
if not os.path.exists(cert):
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3650", "-subj",
                    "/CN=app.addy.io", "-keyout", cert, "-out", cert], check=True, capture_output=True)
api = http.server.ThreadingHTTPServer(("127.0.0.1", HTTPS), Addy)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(cert)
api.socket = ctx.wrap_socket(api.socket, server_side=True)
site = http.server.ThreadingHTTPServer(("127.0.0.1", HTTP), Site)
for srv in (api, site): threading.Thread(target=srv.serve_forever, daemon=True).start()
prof = os.path.join(BUILD, "profile-addy")
shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof + "/Default")
with open(prof + "/Default/Preferences", "w") as f:  # plain-http page: HTTPS-First off
    json.dump({"helium": {"completed_onboarding": True, "privacy_mode": "medium", "privacy_mode_applied": "medium",
                          "services": {"schema_version": 1, "user_consented": True}},
               "https_only_mode_enabled": False, "https_first_balanced_mode_enabled": False}, f)
xvfb = subprocess.Popen(['Xvfb', DISP, '-screen', '0', '1200x800x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
env = dict(os.environ, DISPLAY=DISP, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
p = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--ozone-platform=x11",
                      "--no-sandbox", "--disable-gpu", "--no-first-run", "--force-device-scale-factor=1",
                      "--window-size=1200,800", "--window-position=0,0", "--remote-debugging-port=%d" % PORT,
                      "--ignore-certificate-errors", "--password-store=basic",
                      f"--host-resolver-rules=MAP app.addy.io 127.0.0.1:{HTTPS}, MAP signup.example 127.0.0.1:{HTTP}",
                      "about:blank"], env=env, stdout=subprocess.DEVNULL, stderr=open(BUILD + "/test-addy.log", "w"))
values = []
try:
    for _ in range(60):
        try: ver = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version')); break
        except OSError: time.sleep(0.5)
    ws = WS(ver['webSocketDebuggerUrl'])
    t = ws.call('Target.createTarget', {'url': "http://signup.example/"})['result']['targetId']
    s = ws.call('Target.attachToTarget', {'targetId': t, 'flatten': True})['result']['sessionId']
    time.sleep(2)
    def value():
        r = ws.call('Runtime.evaluate', {'expression': "document.getElementById('email').value", 'returnByValue': True}, s)
        return r.get('result', {}).get('result', {}).get('value')
    for n in (1, 2):
        ws.call('Runtime.evaluate', {'expression': "e = document.getElementById('email'); e.focus(); e.select()"}, s)
        for kind in ('mousePressed', 'mouseReleased'):
            ws.call('Input.dispatchMouseEvent', {'type': kind, 'x': 120, 'y': 50, 'button': 'right', 'clickCount': 1}, s)
        time.sleep(1); shot(f"{n}-menu"); xinput(key="w"); time.sleep(1.5)
        if True:  # the key dialog, both times: no keyring, so nothing was saved
            shot(f"{n}-dialog")
            for ch in KEY: xinput(key=ch)
            xinput(key="Return")
        time.sleep(3); shot(f"{n}-done")
        values.append(value())
finally:
    p.terminate()
    try: p.wait(20)
    except subprocess.TimeoutExpired: p.kill()
    xvfb.terminate(); api.shutdown(); site.shutdown()

prefs = open(prof + "/Default/Preferences").read()
stored = json.loads(prefs).get("helium", {}).get("addy_key", "")
posts = [r for r in requests if r[0] == "POST"]
results = [
    ("field values", values, ["first.alias@anonaddy.me", "second.alias@anonaddy.me"]),
    ("auth on every request", sorted({(r[2], r[3]) for r in requests}), [("Bearer " + KEY, "XMLHttpRequest")]),
    ("alias request", posts[0][4] if posts else None,
     {"domain": "anonaddy.me", "format": "random_words", "description": "Helium++: signup.example"}),
    ("key not saved (no keyring)", not stored and KEY not in prefs, True),
]
ok = True
for name, got, want in results:
    print("%-22s %s%s" % (name, got, "" if got == want else "  <-- FAIL (want %s)" % want))
    ok &= got == want
print("PASS" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
