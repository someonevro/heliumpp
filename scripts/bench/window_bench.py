"""Windowed startup + memory bench in a private Xvfb display (never the real desktop).
Usage: python3 -I window_bench.py <label>=<binary>[,--flag...] [...]   env: N rounds (default 5), TABS (default 10)
Per label: one fresh profile (vertical layout, onboarding done), one warm-up launch, then N measured
launches of the same profile. Reports Chromium's own Startup.* histograms (ms), and on the last round
the summed PSS (MB) of all browser processes after opening TABS Wikipedia tabs. stdlib only."""
import base64, json, os, re, socket, struct, subprocess, sys, time, urllib.request

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
N, TABS, DISP = int(os.environ.get('N', 5)), int(os.environ.get('TABS', 10)), ':98'
HISTS = ['Startup.BrowserWindow.FirstPaint', 'Startup.FirstWebContents.NonEmptyPaint3',
         'Startup.BrowserMessageLoopFirstIdle']
ARTICLES = ['Web_browser', 'Chromium_(web_browser)', 'Linux', 'HTTP', 'JavaScript', 'Cascading_Style_Sheets',
            'World_Wide_Web', 'Internet', 'Computer', 'Operating_system', 'Encryption', 'Open-source_software']

class WS:  # minimal client, same as scripts/cdp_about.py
    def __init__(self, url):
        host, rest = url[5:].split('/', 1); h, p = host.split(':')
        self.s = socket.create_connection((h, int(p)), timeout=60); self.n = 0
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(f'GET /{rest} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                       f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'.encode())
        buf = b''
        while b'\r\n\r\n' not in buf: buf += self.s.recv(4096)
        assert b' 101 ' in buf.split(b'\r\n')[0], buf
        self.buf = buf.split(b'\r\n\r\n', 1)[1]
    def _need(self, n):
        while len(self.buf) < n: self.buf += self.s.recv(65536)
        out, self.buf = self.buf[:n], self.buf[n:]; return out
    def call(self, method, params=None):
        self.n += 1; data = json.dumps({'id': self.n, 'method': method, 'params': params or {}}).encode()
        mask = os.urandom(4)
        hdr = b'\x81' + (bytes([0x80 | len(data)]) if len(data) < 126 else b'\xfe' + struct.pack('>H', len(data)))
        self.s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))
        while True:
            b1, b2 = self._need(2); ln = b2 & 0x7f
            if ln == 126: ln = struct.unpack('>H', self._need(2))[0]
            elif ln == 127: ln = struct.unpack('>Q', self._need(8))[0]
            msg = json.loads(self._need(ln))
            if msg.get('id') == self.n: return msg.get('result', msg)

def seed(prof):
    os.makedirs(f'{prof}/Default', exist_ok=True)
    with open(f'{prof}/Default/Preferences', 'w') as f:
        json.dump({'helium': {'browser': {'layout': 2, 'zen_mode': False}, 'completed_onboarding': True,
                              'privacy_mode': 'medium', 'theme': {'match_wallpaper': os.environ.get('NO_WALLPAPER') != '1'}, 'services': {'schema_version': 1, 'user_consented': True}},
                   'vertical_tabs': {'collapsed_state': False, 'uncollapsed_width': 200}}, f)

def launch(binary, prof, flags=()):
    try: os.remove(f'{prof}/DevToolsActivePort')
    except FileNotFoundError: pass
    env = dict(os.environ, DISPLAY=DISP)
    p = subprocess.Popen([binary, f'--user-data-dir={prof}', '--ozone-platform=x11', '--no-sandbox', '--disable-gpu',
                          '--no-first-run', '--remote-debugging-port=0', '--window-size=1100,800',
                          '--enable-logging=stderr', *flags, 'chrome://new-tab-page'],
                         env=env, stdout=subprocess.DEVNULL, stderr=open(f'{prof}.log', 'w'))
    for _ in range(300):
        try:
            port = open(f'{prof}/DevToolsActivePort').read().split()[0]; break
        except (FileNotFoundError, IndexError): time.sleep(0.1)
    ver = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version'))
    return p, port, WS(ver['webSocketDebuggerUrl'])

def hist(ws, name):
    r = ws.call('Browser.getHistogram', {'name': name})
    h = r.get('histogram')
    return round(h['sum'] / h['count']) if h and h['count'] else None

def pss_mb(prof):
    total = 0
    for pid in filter(str.isdigit, os.listdir('/proc')):
        try:
            if prof.encode() not in open(f'/proc/{pid}/cmdline', 'rb').read(): continue
            m = re.search(r'^Pss:\s+(\d+)', open(f'/proc/{pid}/smaps_rollup').read(), re.M)
            total += int(m.group(1)) if m else 0
        except OSError: pass
    return round(total / 1024)

def stop(p, ws):
    try: ws.call('Browser.close')
    except Exception: pass
    try: p.wait(15)
    except subprocess.TimeoutExpired: p.kill(); p.wait()

xvfb = subprocess.Popen(['Xvfb', DISP, '-screen', '0', '1100x800x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
try:
    for spec in sys.argv[1:]:
        lab, binary = spec.split('=', 1); binary, *flags = binary.split(','); prof = f'{root}/build/bench-window-{lab}'
        subprocess.run(['rm', '-rf', prof]); seed(prof)
        p, port, ws = launch(binary, prof, flags); time.sleep(8); stop(p, ws)  # warm-up: creates the profile
        for r in range(N):
            t0 = time.time(); p, port, ws = launch(binary, prof, flags); t_devtools = time.time() - t0
            time.sleep(6)
            vals = {h.split('.', 1)[1]: hist(ws, h) for h in HISTS}
            theme = sum('Applied desktop accent' in l or 'grayscale theme' in l for l in open(f'{prof}.log'))
            line = f'{lab} round={r} devtools_s={t_devtools:.2f} ' + ' '.join(f'{k}={v}' for k, v in vals.items())
            line += f' theme_applies={theme}'
            if r == N - 1:
                for a in ARTICLES[:TABS]:
                    ws.call('Target.createTarget', {'url': f'https://en.wikipedia.org/wiki/{a}'})
                time.sleep(20); line += f' pss_mb_{TABS}tabs={pss_mb(prof)}'
            print(line, flush=True); stop(p, ws)
finally:
    xvfb.kill()
