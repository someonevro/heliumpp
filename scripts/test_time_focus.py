#!/usr/bin/env python3
"""Time per site + focus rounds (0106). In a private Xvfb display (never the real desktop):
1. a page on 127.0.0.1 open in the focused window for ~40 s is counted (helium.time.days) and the new tab
   page lists it; 2. with 127.0.0.1 on the focus list and a round running, opening it shows the
   "Focus round" page while localhost (same server, not on the list) loads, also via Back (back-forward
   cache); 3. after Stop it loads again; 4. clearing history empties the list; 5. Maximum records nothing.
Run from the project root: python3 -I scripts/test_time_focus.py"""
import sys, http.server, json, os, shutil, subprocess, threading, time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, WEB, DISP = 9362, 8362, ":95"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(b"<title>t</title><body>normal page</body>")
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", WEB), Page)
threading.Thread(target=srv.serve_forever, daemon=True).start()
xvfb = subprocess.Popen(["Xvfb", DISP, "-screen", "0", "1200x800x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
prof = os.path.join(BUILD, "profile-timefocus"); shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof + "/Default")
json.dump({"helium": {"completed_onboarding": True, "privacy_mode": "medium"}}, open(prof + "/Default/Preferences", "w"))
env = dict(os.environ, DISPLAY=DISP, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
b = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--ozone-platform=x11", "--no-sandbox",
                      "--disable-gpu", "--no-first-run", "--remote-debugging-port=%d" % PORT,
                      "http://127.0.0.1:%d/" % WEB], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
fails = 0
def check(ok, what):
    global fails
    fails += not ok
    print("ok" if ok else "FAIL", what)
try:
    time.sleep(42)  # two or three 15 s ticks on the open page
    ws = WS(json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/version" % PORT))["webSocketDebuggerUrl"])
    def tab(url, wait=3):
        t = ws.call("Target.createTarget", {"url": url})["result"]["targetId"]
        s = ws.call("Target.attachToTarget", {"targetId": t, "flatten": True})["result"]["sessionId"]
        time.sleep(wait)
        return s
    def ev(s, js):
        return ws.call("Runtime.evaluate", {"expression": js, "returnByValue": True, "awaitPromise": True}, s)["result"].get("result", {}).get("value")
    ntp = tab("chrome://newtab/")
    # The "on the web today" chip opens the per-site list.
    ev(ntp, "document.querySelector('ntp-app').shadowRoot.querySelector(\".chip[data-chip='time']\")?.click()")
    time.sleep(0.5)
    text = ev(ntp, "document.querySelector('ntp-app').shadowRoot.querySelector('#foot')?.innerText") or ""
    check("on the web today" in text and "127.0.0.1" in text, "new tab page lists today's time: " + repr(text))
    # Focus: the page's own handler, as its buttons use it.
    APP = "document.querySelector('ntp-app')"
    # A tab that was on the site before the round: Back must not restore it from memory.
    back = tab("http://127.0.0.1:%d/before" % WEB)
    ev(back, "location.href = 'http://localhost:%d/away'" % WEB); time.sleep(2)
    ev(ntp, APP + ".pageHandler_.setFocusSites(['http://127.0.0.1/'])")
    ev(ntp, APP + ".pageHandler_.startFocus(25)"); time.sleep(1)
    shut = tab("http://127.0.0.1:%d/a" % WEB)
    check("Focus round" in (ev(shut, "document.body.innerText") or ""), "shut site shows the focus page")
    ev(back, "history.back()"); time.sleep(3)
    check("Focus round" in (ev(back, "document.body.innerText") or ""), "Back to a shut site shows the focus page")
    other = tab("http://localhost:%d/b" % WEB)
    check("normal page" in (ev(other, "document.body.innerText") or ""), "site not on the list loads")
    ev(ntp, APP + ".pageHandler_.stopFocus()"); time.sleep(1)
    again = tab("http://127.0.0.1:%d/c" % WEB)
    check("normal page" in (ev(again, "document.body.innerText") or ""), "after Stop the site loads again")
    settings = tab("chrome://settings/clearBrowserData")
    ev(settings, "chrome.send('clearBrowsingData', ['t1', ['browser.clear_data.browsing_history'], 4])"); time.sleep(3)
    left = ev(ntp, APP + ".pageHandler_.getTimeToday().then(r => r.sites.length)")
    check(left == 0, "clearing history empties time per site (sites left: %s)" % left)
finally:
    b.terminate(); b.wait(30); xvfb.terminate(); xvfb.wait()

def recorded(mode):  # seconds stored on disk after ~40 s on the page (written at quit)
    xv = subprocess.Popen(["Xvfb", DISP, "-screen", "0", "1200x800x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof + "/Default")
    json.dump({"helium": {"completed_onboarding": True, "privacy_mode": mode}}, open(prof + "/Default/Preferences", "w"))
    br = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--ozone-platform=x11", "--no-sandbox",
                           "--disable-gpu", "--no-first-run", "http://127.0.0.1:%d/" % WEB], env=env,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(42); br.terminate(); br.wait(30); xv.terminate(); xv.wait()
    days = json.load(open(prof + "/Default/Preferences")).get("helium", {}).get("time", {}).get("days", {})
    return max((d.get("127.0.0.1", 0) for d in days.values()), default=0)

check(recorded("medium") >= 15, "medium: seconds written to disk at quit")
check(recorded("maximum") == 0, "maximum: nothing recorded")
srv.shutdown()
shutil.rmtree(prof, ignore_errors=True)
print("ALL PASS" if not fails else "%d FAILED" % fails)
raise SystemExit(1 if fails else 0)
