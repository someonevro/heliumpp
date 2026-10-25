"""Open chrome://settings/help in a running browser over DevTools and print the update status text.
Usage: python3 -I cdp_about.py <debug-port> <seconds-to-wait> [close]  (close: close the tab afterwards)  (stdlib only; DevTools client in cdp.py)"""
import json, os, sys, time, urllib.request

port, wait = int(sys.argv[1]), float(sys.argv[2])

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

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
if sys.argv[3:] == ['close']:
    ws.call('Target.closeTarget', {'targetId': t})
