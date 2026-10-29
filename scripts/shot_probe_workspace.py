"""Screenshot probe (scripts/shot_kwin.sh PROBE=...): switches the window to workspace WS (default "work") through
the web sidebar's own page handler, then gives the restored tabs time to load. Argument: remote debugging port."""
import json, os, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

port = sys.argv[1]
for _ in range(30):
    try:
        ver = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version")); break
    except OSError:
        time.sleep(0.5)
ws = WS(ver["webSocketDebuggerUrl"])
targets = ws.call("Target.getTargets")["result"]["targetInfos"]
side = next(t for t in targets if t["url"].startswith("chrome://helium-sidebar"))
session = ws.call("Target.attachToTarget", {"targetId": side["targetId"], "flatten": True})["result"]["sessionId"]
expr = ("document.querySelector('helium-sidebar-app').proxy_.handler.switchWorkspace(%s)"
        % json.dumps(os.environ.get("WS", "work")))
print(ws.call("Runtime.evaluate", {"expression": expr}, session).get("result", {}).get("exceptionDetails", "ok"))
time.sleep(float(os.environ.get("PROBE_WAIT", "8")))
