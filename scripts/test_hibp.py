#!/usr/bin/env python3
"""Does signing in with a breached password show a warning (Have I Been Pwned, password saving off)?
A local login page (login.example) and a local HTTPS server playing api.pwnedpasswords.com run in a private
Xvfb display (never the real desktop). The test types and submits "password123", then a random password.
The service must be asked once per password with only the 5-hex-digit prefix of its SHA-1, with padding
and no cookies; the random password is listed only as a count-0 padding line. A warning dialog must show
for the first and not for the second: SHOT=1 saves build/hibp-1-weak.png and hibp-2-strong.png to look at
(the dialog is native UI that DevTools cannot see).
Run from the project root: python3 -I scripts/test_hibp.py"""
import sys, ctypes, hashlib, http.server, json, os, secrets, shutil, ssl, subprocess, threading, time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, HTTP, HTTPS, DISP = 9353, 8095, 8444, ":92"
WEAK, STRONG = "password123", "Hpp-" + secrets.token_urlsafe(24)
RETRY = "Hpp-retry-" + secrets.token_urlsafe(16)  # its first lookup gets a server error
HASH = {pw: hashlib.sha1(pw.encode()).hexdigest().upper() for pw in (WEAK, STRONG, RETRY)}
fail_next = [True]
LOGIN = (b'<title>Login</title><form action="/done" method="post">'
         b'<input id="u" name="u" autocomplete="username"><input id="p" type="password" name="p"'
         b' autocomplete="current-password"><button id="go">Sign in</button></form>')
requests = []  # (path, Add-Padding header, cookie header)

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
        subprocess.run(["import", "-display", DISP, "-window", "root", f"{BUILD}/hibp-{name}.png"])

class Range(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        requests.append((self.path, self.headers.get("Add-Padding"), self.headers.get("Cookie")))
        prefix = self.path.rsplit("/", 1)[-1]
        if prefix == HASH[RETRY][:5] and fail_next[0]:
            fail_next[0] = False; self.send_response(500); self.end_headers(); return
        lines = ["%035X:0" % secrets.randbits(140) for _ in range(5)]  # padding
        if prefix == HASH[WEAK][:5]: lines.append(HASH[WEAK][5:] + ":42")
        if prefix == HASH[STRONG][:5]: lines.append(HASH[STRONG][5:] + ":0")
        self.send_response(200); self.send_header("Content-Type", "text/plain"); self.end_headers()
        self.wfile.write("\r\n".join(lines).encode())
    def log_message(self, *a): pass

class Site(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(LOGIN)
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(b"<title>Welcome</title><h1>Signed in</h1>")
    def log_message(self, *a): pass

cert = os.path.join(BUILD, "hibp-cert.pem")
if not os.path.exists(cert):
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3650", "-subj",
                    "/CN=api.pwnedpasswords.com", "-keyout", cert, "-out", cert], check=True, capture_output=True)
api = http.server.ThreadingHTTPServer(("127.0.0.1", HTTPS), Range)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(cert)
api.socket = ctx.wrap_socket(api.socket, server_side=True)
site = http.server.ThreadingHTTPServer(("127.0.0.1", HTTP), Site)
for srv in (api, site): threading.Thread(target=srv.serve_forever, daemon=True).start()
prof = os.path.join(BUILD, "profile-hibp")
shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof + "/Default")
with open(prof + "/Default/Preferences", "w") as f:  # plain-http login page: HTTPS-First off
    json.dump({"helium": {"completed_onboarding": True, "privacy_mode": "medium", "privacy_mode_applied": "medium",
                          "services": {"schema_version": 1, "user_consented": True}},
               "https_only_mode_enabled": False, "https_first_balanced_mode_enabled": False}, f)
xvfb = subprocess.Popen(['Xvfb', DISP, '-screen', '0', '1200x800x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
env = dict(os.environ, DISPLAY=DISP, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
p = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--ozone-platform=x11",
                      "--no-sandbox", "--disable-gpu", "--no-first-run", "--force-device-scale-factor=1",
                      "--window-size=1200,800", "--window-position=0,0", "--remote-debugging-port=%d" % PORT,
                      "--ignore-certificate-errors",
                      f"--host-resolver-rules=MAP api.pwnedpasswords.com 127.0.0.1:{HTTPS}, MAP login.example 127.0.0.1:{HTTP}",
                      "about:blank"], env=env, stdout=subprocess.DEVNULL, stderr=open(BUILD + "/test-hibp.log", "w"))
results = []
try:
    for _ in range(60):
        try: ver = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version')); break
        except OSError: time.sleep(0.5)
    ws = WS(ver['webSocketDebuggerUrl'])
    for n, (name, pw) in enumerate((("weak", WEAK), ("strong", STRONG)), 1):
        t = ws.call('Target.createTarget', {'url': "http://login.example/"})['result']['targetId']
        s = ws.call('Target.attachToTarget', {'targetId': t, 'flatten': True})['result']['sessionId']
        time.sleep(2)
        for field, text in (("u", "user%d" % n), ("p", pw)):
            ws.call('Runtime.evaluate', {'expression': f"document.getElementById('{field}').focus()"}, s)
            ws.call('Input.insertText', {'text': text}, s)
        before = len(requests)
        ws.call('Runtime.evaluate', {'expression': "document.getElementById('go').click()"}, s)
        time.sleep(4); shot(f"{n}-{name}")
        results.append((f"{name}: asked service", [r[0] for r in requests[before:]], ["/range/" + HASH[pw][:5]]))
        ws.call('Target.closeTarget', {'targetId': t}); time.sleep(1)
    # Same tab, same password twice: the first lookup fails (HTTP 500), so the second sign-in must ask again
    # (it used to stay marked "checked" and was never looked up).
    t = ws.call('Target.createTarget', {'url': "http://login.example/"})['result']['targetId']
    s = ws.call('Target.attachToTarget', {'targetId': t, 'flatten': True})['result']['sessionId']
    before = len(requests)
    for attempt in range(2):
        if attempt:
            ws.call('Page.navigate', {'url': "http://login.example/"}, s)
        time.sleep(2)
        for field, text in (("u", "retry"), ("p", RETRY)):
            ws.call('Runtime.evaluate', {'expression': f"document.getElementById('{field}').focus()"}, s)
            ws.call('Input.insertText', {'text': text}, s)
        ws.call('Runtime.evaluate', {'expression': "document.getElementById('go').click()"}, s)
        time.sleep(4)
    results.append(("retry after error", [r[0] for r in requests[before:]], ["/range/" + HASH[RETRY][:5]] * 2))
    ws.call('Target.closeTarget', {'targetId': t})
finally:
    p.terminate()
    try: p.wait(20)
    except subprocess.TimeoutExpired: p.kill()
    xvfb.terminate(); api.shutdown(); site.shutdown()

results += [("padding asked", all(r[1] == "true" for r in requests) and bool(requests), True),
            ("no cookies", all(r[2] is None for r in requests), True)]
ok = True
for name, got, want in results:
    print("%-22s %-30s%s" % (name, got, "" if got == want else "  <-- FAIL (want %s)" % want))
    ok &= got == want
print("PASS (with SHOT=1, look at build/hibp-1-weak.png: warning; hibp-2-strong.png: none)" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
