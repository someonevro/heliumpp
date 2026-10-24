#!/usr/bin/env python3
"""Does the new tab page say how much memory sleeping tabs free (Performance row)?
Opens 3 tabs that each hold ~150 MB, waits for Chromium to measure them, puts them to sleep through
chrome://discards, then reads the new tab page: it must name 3 sleeping tabs and at least 300 MB.
Run from the project root: python3 -I scripts/test_sleeping_tabs.py"""
import base64, json, os, re, shutil, socket, struct, subprocess, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT = 9352
HEAVY = "data:text/html,<title>heavy</title><script>window.x = new Uint8Array(150e6).fill(1)</script>"

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

prof = os.path.join(BUILD, "profile-sleeping")
shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof + "/Default")
with open(prof + "/Default/Preferences", "w") as f:
    json.dump({"helium": {"completed_onboarding": True, "privacy_mode": "medium", "privacy_mode_applied": "medium",
                          "services": {"schema_version": 1, "user_consented": True}}}, f)
with open(prof + "/Local State", "w") as f:  # chrome://discards is a debug page, off by default
    json.dump({"internal_only_uis_enabled": True}, f)
env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
p = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--headless=new", "--no-sandbox",
                      "--disable-gpu", "--remote-debugging-port=%d" % PORT, "about:blank"],
                     env=env, stdout=subprocess.DEVNULL, stderr=open(BUILD + "/test-sleeping.log", "w"))
note = None
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
    for _ in range(3): tab(HEAVY)
    time.sleep(int(os.environ.get("WAIT", 10)))  # memory is measured soon after load, then every 2 min
    discards = tab("chrome://discards/")
    time.sleep(2)
    ev(discards, "(async () => { const m = await import('chrome://discards/discards.js');"
                 " const d = m.getOrCreateDetailsProvider(); const r = await d.getTabDiscardsInfo();"
                 " for (const i of r.infos) if (i.title == 'heavy') await d.discardById(i.id, 0); })()")
    ntp = tab("chrome://new-tab-page/")
    for _ in range(20):
        time.sleep(1)
        note = ev(ntp, "document.querySelector('ntp-app')?.shadowRoot?.getElementById('sleepingNote')?.textContent")
        if note: break
finally:
    p.terminate()
    try: p.wait(20)
    except subprocess.TimeoutExpired: p.kill()

print("note:", note)
m = re.match(r"3 sleeping tabs are freeing about ([0-9.]+) (MB|GB)\.$", (note or "").strip())
mb = m and float(m.group(1)) * (1024 if m.group(2) == "GB" else 1)
print("PASS" if mb and mb >= 300 else "FAIL")
raise SystemExit(0 if mb and mb >= 300 else 1)
