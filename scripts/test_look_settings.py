#!/usr/bin/env python3
"""Settings > Appearance look switches (0153): Classic look, Rounded window corners and Acrylic window are shown;
Classic look flips its pref and a new tab page opened afterwards carries the classic attribute. Window corners and the
sidebar markup are checked by screenshot (scripts/shot_kwin.sh CLASSIC=true / CORNERS=false), not here.
Run from the project root: python3 -I scripts/test_look_settings.py"""
import sys, json, os, shutil, subprocess, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT = 9351

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

prof = os.path.join(BUILD, "profile-looksettings")
shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof)
env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
p = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--headless=new", "--no-sandbox",
                      "--disable-gpu", "--remote-debugging-port=%d" % PORT, "about:blank"],
                     env=env, stdout=subprocess.DEVNULL, stderr=open(BUILD + "/test-looksettings.log", "w"))
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
    settings = tab("chrome://settings/appearance")
    FIND = """(function f(root){for(const el of root.querySelectorAll('*')){
      if(el.matches('settings-toggle-button[pref-key="%s"]')) return el;
      if(el.shadowRoot){const r=f(el.shadowRoot); if(r) return r;}}})(document)"""
    PREF = "new Promise(r => chrome.settingsPrivate.getPref('%s', p => r(p.value)))"
    keys = ("helium.theme.classic_look", "helium.browser.rounded_window_corners",
            "helium.browser.native_frame_materials")
    for _ in range(40):
        if ev(settings, "!!" + FIND % keys[0]): break
        time.sleep(0.25)
    for k in keys:
        results.append(("shown: " + k, ev(settings, "!!(%s) && !(%s).hidden" % (FIND % k, FIND % k)), True))
    results.append(("default classic_look", ev(settings, PREF % keys[0]), False))
    results.append(("default rounded_window_corners", ev(settings, PREF % keys[1]), True))
    results.append(("default acrylic", ev(settings, PREF % keys[2]), False))
    ntp = tab("chrome://new-tab-page"); time.sleep(2)
    results.append(("new tab page default: no classic", ev(ntp, "document.querySelector('ntp-app').hasAttribute('classic')"), False))
    ev(settings, (FIND % keys[0]) + ".click()"); time.sleep(1.5)
    results.append(("classic_look after click", ev(settings, PREF % keys[0]), True))
    ntp2 = tab("chrome://new-tab-page"); time.sleep(2)
    results.append(("new tab page after: classic", ev(ntp2, "document.querySelector('ntp-app').hasAttribute('classic')"), True))
finally:
    p.terminate()
    try: p.wait(20)
    except subprocess.TimeoutExpired: p.kill()

ok = True
for name, got, want in results:
    print("%-52s %-6s (want %s)%s" % (name, got, want, "" if got == want else "  <-- FAIL"))
    ok &= got == want
print("PASS" if ok and len(results) == 9 else "FAIL")
raise SystemExit(0 if ok and len(results) == 9 else 1)
