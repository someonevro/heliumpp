"""Screenshot probe (scripts/shot_kwin.sh PROBE=...): switches to workspace "work" (SEED=1), waits for its tabs,
then opens the web sidebar's shield panel. Argument: remote debugging port."""
import json, os, subprocess, sys, time
here = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("PROBE_WAIT", "8")
subprocess.run([sys.executable, "-I", os.path.join(here, "shot_probe_workspace.py"), sys.argv[1]], env=os.environ)
sys.path.insert(0, here)
import urllib.request  # noqa: E402
from cdp import WS  # noqa: E402
ws = WS(json.load(urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/json/version"))["webSocketDebuggerUrl"])
side = next(t for t in ws.call("Target.getTargets")["result"]["targetInfos"]
            if t["url"].startswith("chrome://helium-sidebar"))
s = ws.call("Target.attachToTarget", {"targetId": side["targetId"], "flatten": True})["result"]["sessionId"]
ws.call("Runtime.evaluate", {"expression":
        "document.querySelector('helium-sidebar-app').shadowRoot.querySelector('.shield').click()"}, s)
time.sleep(1)
