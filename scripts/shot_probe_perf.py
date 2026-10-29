"""Screenshot probe (scripts/shot_kwin.sh PROBE=...): turns performance mode on (PERF=1, default) or off through
the web sidebar's page handler, then reloads new tab pages. Argument: remote debugging port."""
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
targets = ws.call("Target.getTargets")["result"]["targetInfos"]
attach = lambda t: ws.call("Target.attachToTarget", {"targetId": t["targetId"], "flatten": True})["result"]["sessionId"]
side = next(t for t in targets if t["url"].startswith("chrome://helium-sidebar"))
on = "true" if os.environ.get("PERF", "1") == "1" else "false"
ws.call("Runtime.evaluate", {"expression":
        f"document.querySelector('helium-sidebar-app').proxy_.handler.setPerformanceMode({on})"}, attach(side))
time.sleep(1)
for t in targets:
    if t["type"] == "page" and t["url"].startswith(("chrome://newtab", "chrome://new-tab-page")):
        ws.call("Page.reload", {}, attach(t))
time.sleep(4)
