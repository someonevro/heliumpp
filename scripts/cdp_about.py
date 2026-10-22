"""Open chrome://settings/help in a running browser over DevTools and print the update status text.
Usage: python3 -I cdp_about.py <debug-port> <seconds-to-wait>  (stdlib only, minimal websocket client)"""
import base64, json, os, socket, struct, sys, time, urllib.request

port, wait = int(sys.argv[1]), float(sys.argv[2])

def connect(url):
    host, rest = url[5:].split('/', 1)
    h, p = host.split(':')
    s = socket.create_connection((h, int(p)), timeout=30)
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
        hdr = b'\x81' + (bytes([0x80 | len(data)]) if len(data) < 126 else b'\xfe' + struct.pack('>H', len(data)) if len(data) < 65536 else b'\xff' + struct.pack('>Q', len(data)))
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

ver = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version'))
ws = WS(ver['webSocketDebuggerUrl'])
t = ws.call('Target.createTarget', {'url': 'chrome://settings/help'})['result']['targetId']
sess = ws.call('Target.attachToTarget', {'targetId': t, 'flatten': True})['result']['sessionId']
JS = """(function f(root){for(const el of root.querySelectorAll('*')){
 if(el.id==='updateStatusMessage') return el.innerText; if(el.shadowRoot){const r=f(el.shadowRoot); if(r!==undefined) return r;}}})(document)"""
deadline = time.time() + wait; last = None
while time.time() < deadline:
    r = ws.call('Runtime.evaluate', {'expression': JS, 'returnByValue': True}, sess)
    v = r.get('result', {}).get('result', {}).get('value')
    if v != last: print('status text:', repr(v), flush=True); last = v
    time.sleep(0.5)
