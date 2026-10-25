#!/usr/bin/env python3
"""Does the Performance mode switch in Settings > Appearance work (0077)? Clicks it on, then off, and checks
the side effects that only the native pref observer applies: spellcheck off and prefers-reduced-motion on an
open page, then both restored. Run from the project root: python3 -I scripts/test_performance_toggle.py"""
import sys, json, os, shutil, subprocess, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT = 9347

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

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
