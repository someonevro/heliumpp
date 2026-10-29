"""Screenshot probe (scripts/shot_kwin.sh PROBE=...): waits for the wallpaper decode (MATCH=1), then reloads every
new tab page so it picks up the wallpaper thumbnail (read when the page loads). Argument: remote debugging port."""
import json, os, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

port = sys.argv[1]
for _ in range(30):
    try:
        ver = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version")); break
    except OSError:
        time.sleep(0.5)
time.sleep(3)
ws = WS(ver["webSocketDebuggerUrl"])
for t in ws.call("Target.getTargets")["result"]["targetInfos"]:
    if t["type"] == "page" and t["url"].startswith(("chrome://new-tab-page", "chrome://newtab")):
        s = ws.call("Target.attachToTarget", {"targetId": t["targetId"], "flatten": True})["result"]["sessionId"]
        ws.call("Page.reload", {}, s)
        time.sleep(2)
        expr = ("(() => { const w = document.querySelector('ntp-app').shadowRoot.querySelector('#wall');"
                " return JSON.stringify({thumb: typeof loadTimeData,"
                " bg: w && getComputedStyle(w).backgroundImage.slice(0, 80)}); })()")
        r = ws.call("Runtime.evaluate", {"expression": expr, "returnByValue": True}, s)
        open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "audit", "ntp_probe.txt"), "a").write(
            str(r.get("result", {}).get("result", {}).get("value") or r) + "\n")
time.sleep(float(os.environ.get("PROBE_WAIT", "4")))
