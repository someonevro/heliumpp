#!/usr/bin/env python3
"""Screenshot of one first-run setup page (chrome://setup) in a private Xvfb display, never the real desktop.
Usage: python3 -I scripts/shot_setup_page.py <PageName> <out.png> [light|dark]
Walks the flow with the page's own Next button until the page is shown, then captures the window via CDP."""
import base64, json, os, shutil, subprocess, sys, time, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from cdp import WS  # noqa: E402
page, out = sys.argv[1], sys.argv[2]
scheme = {"light": 1, "dark": 2}.get(sys.argv[3] if len(sys.argv) > 3 else "", 0)
PORT, DISP = 9363, ":95"
prof = os.path.join(ROOT, "build", "profile-setup-shot")
shutil.rmtree(prof, ignore_errors=True); os.makedirs(f"{prof}/Default")
json.dump({"browser": {"theme": {"color_scheme2": scheme}}}, open(f"{prof}/Default/Preferences", "w"))
xvfb = subprocess.Popen(["Xvfb", DISP, "-screen", "0", "1300x900x24", "-nolisten", "tcp"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
env = {**os.environ, "DISPLAY": DISP}; env.pop("WAYLAND_DISPLAY", None)
br = subprocess.Popen([f"{ROOT}/build/src/out/Default/helium", "--ozone-platform=x11", f"--user-data-dir={prof}",
                       f"--remote-debugging-port={PORT}", "--window-size=1200,820",
                       "--host-resolver-rules=MAP * ~NOTFOUND", "chrome://setup/"],
                      env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try: ver = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version")); break
        except OSError: time.sleep(0.5)
    ws = WS(ver["webSocketDebuggerUrl"]); time.sleep(3)
    t = next(t for t in ws.call("Target.getTargets")["result"]["targetInfos"] if t["url"].startswith("chrome://setup"))
    s = ws.call("Target.attachToTarget", {"targetId": t["targetId"], "flatten": True})["result"]["sessionId"]
    ev = lambda e: ws.call("Runtime.evaluate", {"expression": e, "returnByValue": True}, s)["result"].get("result", {}).get("value")
    sel = f"#{page[0].lower()}{''.join('-' + c.lower() if c.isupper() else c for c in page[1:])}-page.visible"
    for _ in range(15):
        if ev(f"!!document.querySelector({json.dumps(sel)})"): break
        ev("([...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Configure')"
           " || [...document.querySelectorAll('#setup-buttons button')].pop())?.click()"); time.sleep(1.2)
    time.sleep(1)
    png = ws.call("Page.captureScreenshot", {"format": "png"}, s)["result"]["data"]
    open(out, "wb").write(base64.b64decode(png)); print(out, "shown" if ev(f"!!document.querySelector({json.dumps(sel)})") else "NOT REACHED")
finally:
    br.kill(); xvfb.kill(); shutil.rmtree(prof, ignore_errors=True)
