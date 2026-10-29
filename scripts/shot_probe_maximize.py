"""Probe for scripts/shot_kwin.sh (nested KWin, a real window manager): clicks the web sidebar's maximize dot
twice and the minimize dot once and writes the window states to build/audit/maximize.txt.
Expected: maximized, normal, minimized. Argument: remote debugging port."""
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
infos = ws.call("Target.getTargets")["result"]["targetInfos"]
side = next(t for t in infos if t["url"].startswith("chrome://helium-sidebar"))
page = next(t for t in infos if t["type"] == "page" and t is not side)
s = ws.call("Target.attachToTarget", {"targetId": side["targetId"], "flatten": True})["result"]["sessionId"]
win = ws.call("Browser.getWindowForTarget", {"targetId": page["targetId"]})["result"]["windowId"]
state = lambda: ws.call("Browser.getWindowBounds", {"windowId": win})["result"]["bounds"]["windowState"]
states = []
for label in ("Maximize", "Maximize", "Minimize"):
    ws.call("Runtime.evaluate", {"expression": "document.querySelector('helium-sidebar-app').shadowRoot"
                                 f".querySelector(\"[aria-label='{label}']\").click()"}, s)
    time.sleep(2)
    states.append(state())
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build/audit/maximize.txt")
open(out, "w").write(" ".join(states) + "\n")
