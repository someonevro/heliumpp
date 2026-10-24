#!/usr/bin/env python3
"""Two profiles open at once (0081, 0082). With 2+ profiles Chromium loads its internal System Profile for the
profile picker; our startup code used to crash on it. Then Performance mode in both profiles: memory saver is
browser-wide, so it must stay on until the LAST profile turns it off, and then come back to the user's value.
Run from the project root: python3 -I scripts/test_two_profiles.py"""
import base64, json, os, shutil, socket, struct, subprocess, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build"); PORT = 9352
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

d = os.path.join(BUILD, "profile-two"); shutil.rmtree(d, ignore_errors=True)
for p in ("Default", "Profile 1"):
    os.makedirs(os.path.join(d, p))
    json.dump({"helium": {"completed_onboarding": True, "privacy_mode": "medium", "privacy_mode_applied": "medium"},
               "session": {"restore_on_startup": 1}}, open(os.path.join(d, p, "Preferences"), "w"))
# The user's own memory saver choice: off (0). Performance mode must give it back.
json.dump({"profile": {"last_active_profiles": ["Default", "Profile 1"],
                       "info_cache": {"Default": {"name": "A"}, "Profile 1": {"name": "B"}}},
           "performance_tuning": {"high_efficiency_mode": {"state": 0}}}, open(os.path.join(d, "Local State"), "w"))
env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
b = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + d, "--headless=new", "--no-sandbox",
                      "--disable-gpu", "--remote-debugging-port=%d" % PORT],
                     env=env, stdout=subprocess.DEVNULL, stderr=open(BUILD + "/test-two.log", "w"))
results = []
try:
    for _ in range(60):
        try: ver = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version")); break
        except OSError: time.sleep(0.5)
    time.sleep(3)
    results.append(("browser still running with 2 profiles", b.poll() is None, True))
    ws = WS(ver["webSocketDebuggerUrl"])
    ctxs = sorted({t["browserContextId"] for t in ws.call("Target.getTargets")["result"]["targetInfos"]
                   if t["type"] == "background_page"})
    results.append(("profiles loaded", len(ctxs), 2))
    def targets(): return ws.call("Target.getTargets")["result"]["targetInfos"]
    def attach(t): return ws.call("Target.attachToTarget", {"targetId": t, "flatten": True})["result"]["sessionId"]
    def ev(s, js):
        r = ws.call("Runtime.evaluate", {"expression": js, "returnByValue": True, "awaitPromise": True}, s)
        return r.get("result", {}).get("result", {}).get("value")
    SET = "new Promise(r => chrome.settingsPrivate.setPref('helium.performance_mode', %s, '', r))"
    MEM = "new Promise(r => chrome.settingsPrivate.getPref('performance_tuning.high_efficiency_mode.state', p => r(p.value)))"
    # The profile picker (shown because there are 2 profiles) opens Settings in each profile.
    picker = attach(next(t["targetId"] for t in targets() if t["url"].startswith("chrome://profile-picker")))
    ev(picker, "chrome.send('openManageProfileSettingsSubPage', [%s]); chrome.send('openManageProfileSettingsSubPage', [%s])"
       % (json.dumps(os.path.join(d, "Default")), json.dumps(os.path.join(d, "Profile 1"))))
    tabs = []
    for _ in range(30):
        tabs = [t for t in targets() if t["type"] == "page" and t["url"].startswith("chrome://settings")]
        if len({t["browserContextId"] for t in tabs}) == 2: break
        time.sleep(0.5)
    results.append(("settings tabs are in different profiles", len({t["browserContextId"] for t in tabs}), 2))
    first = {t["browserContextId"]: t["targetId"] for t in tabs}
    a, bb = [attach(t) for t in first.values()][:2]
    time.sleep(2)
    ev(a, SET % "true"); time.sleep(1); ev(bb, SET % "true"); time.sleep(1)
    results.append(("both on: memory saver on (2 = enabled)", ev(a, MEM), 2))
    ev(a, SET % "false"); time.sleep(1)
    results.append(("first off, second still on: memory saver on", ev(a, MEM), 2))
    ev(bb, SET % "false"); time.sleep(1)
    results.append(("both off: memory saver back to the user's off", ev(a, MEM), 0))
finally:
    b.terminate()
    try: b.wait(20)
    except subprocess.TimeoutExpired: b.kill()

ok = True
for name, got, want in results:
    print("%-50s %-6s (want %s)%s" % (name, got, want, "" if got == want else "  <-- FAIL"))
    ok &= got == want
print("PASS" if ok and len(results) == 6 else "FAIL")
raise SystemExit(0 if ok and len(results) == 6 else 1)
