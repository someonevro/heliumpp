#!/usr/bin/env python3
"""Does the Performance mode switch in Settings > Appearance work (0077)? Clicks it on, then off, and checks
the side effects that only the native pref observer applies: spellcheck off and prefers-reduced-motion on an
open page, then both restored. Run from the project root: python3 -I scripts/test_performance_toggle.py"""
import base64, json, os, shutil, socket, struct, subprocess, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT = 9347

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

prof = os.path.join(BUILD, "profile-perftoggle")
shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof)
env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
p = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--headless=new", "--no-sandbox",
                      "--disable-gpu", "--remote-debugging-port=%d" % PORT, "about:blank"],
                     env=env, stdout=subprocess.DEVNULL, stderr=open(BUILD + "/test-perftoggle.log", "w"))
results = []
try:
    for _ in range(60):
        try: ver = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version')); break
        except OSError: time.sleep(0.5)
    ws = WS(ver['webSocketDebuggerUrl'])
    def tab(url):
        t = ws.call('Target.createTarget', {'url': url})['result']['targetId']
        return ws.call('Target.attachToTarget', {'targetId': t, 'flatten': True})['result']['sessionId']
    def ev(sess, js):
        r = ws.call('Runtime.evaluate', {'expression': js, 'returnByValue': True, 'awaitPromise': True}, sess)
        return r.get('result', {}).get('result', {}).get('value')
    page, settings = tab("data:text/html,<p>page</p>"), tab("chrome://settings/appearance")
    FIND = """(function f(root){for(const el of root.querySelectorAll('*')){
      if(el.matches('settings-toggle-button[pref-key="helium.performance_mode"]')) return el;
      if(el.shadowRoot){const r=f(el.shadowRoot); if(r) return r;}}})(document)"""
    PREF = "new Promise(r => chrome.settingsPrivate.getPref('%s', p => r(p.value)))"
    found = False
    for _ in range(40):
        if ev(settings, "!!" + FIND): found = True; break
        time.sleep(0.25)
    results.append(("switch shown in Settings > Appearance", found, True))
    for want in (True, False):
        ev(settings, FIND + ".click()"); time.sleep(1.5)
        results.append(("pref after click", ev(settings, PREF % "helium.performance_mode"), want))
        results.append(("spellcheck", ev(settings, PREF % "browser.enable_spellchecking"), not want))
        results.append(("open page prefers reduced motion",
                        ev(page, "matchMedia('(prefers-reduced-motion: reduce)').matches"), want))
finally:
    p.terminate()
    try: p.wait(20)
    except subprocess.TimeoutExpired: p.kill()

ok = True
for name, got, want in results:
    print("%-40s %-6s (want %s)%s" % (name, got, want, "" if got == want else "  <-- FAIL"))
    ok &= got == want
print("PASS" if ok and len(results) == 7 else "FAIL")
raise SystemExit(0 if ok and len(results) == 7 else 1)
