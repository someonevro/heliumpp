#!/usr/bin/env python3
"""Web sidebar (--helium-web-sidebar, patches 0124/0126): do its controls drive the real browser?
In a private Xvfb display (never the real desktop) the sidebar page's own buttons are clicked (element.click()
inside chrome://helium-sidebar.top-chrome) and the effect is read back from the browser over CDP:
new tab, activate a tab, close a tab, back / forward / reload, workspace switch (restores seeded tabs),
sidebar collapse (the page becomes a narrow rail), the footer shield showing uBlock Origin's blocked count for
the active tab (ad hosts mapped to the local server, all other hosts unreachable), the tab list following title changes of background tabs,
and finally the close-window dot ending the browser (maximize needs a window manager: not in Xvfb).
Run from the project root: python3 -I scripts/test_web_sidebar.py"""
import http.server, json, os, shutil, subprocess, sys, threading, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, HTTP, DISP = 9361, 8361, ":97"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        name = self.path.strip("/") or "root"
        # /late sets its title after a second, while in the background.
        script = "<script>setTimeout(()=>document.title='late-done',1000)</script>" if name == "late" else ""
        if name == "ads":  # requests uBlock Origin's default lists block
            script = "".join(f'<script src="http://{h}:{HTTP}/a.js"></script>' for h in ADS)
        body = f"<title>{name}</title><h1>{name}</h1>{script}".encode()
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", HTTP), Page)
threading.Thread(target=srv.serve_forever, daemon=True).start()
U = lambda p: f"http://127.0.0.1:{HTTP}/{p}"
ADS = ["pagead2.googlesyndication.com", "securepubads.g.doubleclick.net", "www.google-analytics.com",
       "connect.facebook.net", "cdn.taboola.com"]
# Ad hosts lead to the local server; nothing else leaves the machine.
RULES = ", ".join([f"MAP {h} 127.0.0.1" for h in ADS] + ["MAP * ~NOTFOUND", "EXCLUDE 127.0.0.1"])

prof = os.path.join(BUILD, "profile-websidebar-test")
shutil.rmtree(prof, ignore_errors=True); os.makedirs(f"{prof}/Default")
workspaces = [{"id": "home", "name": "Home", "tabs": [], "groups": []},
              {"id": "work", "name": "Work", "groups": [],
               "tabs": [{"url": U("w1"), "pinned": True}, {"url": U("w2"), "pinned": False}]}]
json.dump({"helium": {"workspaces": workspaces, "workspaces_active": "home", "completed_onboarding": True,
                      "browser": {"layout": 2, "zen_mode": False}},
           "vertical_tabs": {"collapsed_state": False, "uncollapsed_width": 232}},
          open(f"{prof}/Default/Preferences", "w"))

xvfb = subprocess.Popen(["Xvfb", DISP, "-screen", "0", "1400x900x24", "-nolisten", "tcp"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
env = {**os.environ, "DISPLAY": DISP, "XDG_CONFIG_HOME": f"{BUILD}/xdg/config", "XDG_CACHE_HOME": f"{BUILD}/xdg/cache"}
env.pop("WAYLAND_DISPLAY", None)
br = subprocess.Popen([f"{BUILD}/src/out/Default/helium", "--ozone-platform=x11", f"--user-data-dir={prof}",
                       "--no-first-run", "--helium-web-sidebar", f"--remote-debugging-port={PORT}",
                       "--window-size=1200,800", f"--host-resolver-rules={RULES}", U("a")], env=env,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" ({detail})" if detail and not ok else ""))
    if not ok: fails.append(name)

def wait(pred, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        try:
            v = pred()
            if v: return v
        except OSError:  # browser not listening yet
            pass
        time.sleep(0.25)
    return pred()

try:
    ver = wait(lambda: json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version")), 20)
    ws = WS(ver["webSocketDebuggerUrl"])
    targets = lambda: ws.call("Target.getTargets")["result"]["targetInfos"]
    pages = lambda: [t for t in targets() if t["type"] == "page" and not t["url"].startswith("chrome://helium-sidebar")]
    side = wait(lambda: next((t for t in targets() if t["url"].startswith("chrome://helium-sidebar")), None), 15)
    check("sidebar page exists", bool(side))
    s = ws.call("Target.attachToTarget", {"targetId": side["targetId"], "flatten": True})["result"]["sessionId"]
    def ev(expr):
        r = ws.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True}, s)
        return r["result"]["result"].get("value")
    root = "document.querySelector('helium-sidebar-app').shadowRoot"
    click = lambda sel: ev(f"{root}.querySelector({json.dumps(sel)}).click(), true")
    titles = lambda: ev(f"[...{root}.querySelectorAll('.scroll .tab .t')].map(e => e.textContent.trim())") or []
    active = lambda: ev(f"{root}.querySelector(\".scroll .tab[aria-selected='true'] .t\")?.textContent.trim()")
    wait(lambda: "a" in titles())
    check("tab list shows the page title", titles() == ["a"], titles())

    n = len(pages()); click(".newtab")
    check("new tab button opens a tab", wait(lambda: len(pages()) == n + 1), len(pages()))
    check("new tab is listed and active", wait(lambda: len(titles()) == 2 and active() == "New tab"), titles())

    ev(f"{root}.querySelector(\".scroll .tab[data-id]\").click()")  # first row: "a"
    check("clicking a row activates it", wait(lambda: active() == "a"), active())

    # Navigate tab "a" to /b with the page itself, then use the sidebar's back / forward / reload.
    a = next(t for t in pages() if t["url"] == U("a"))
    ps = ws.call("Target.attachToTarget", {"targetId": a["targetId"], "flatten": True})["result"]["sessionId"]
    ws.call("Page.navigate", {"url": U("b")}, ps)
    wait(lambda: active() == "b")
    click("[aria-label='Back']")
    check("back button", wait(lambda: active() == "a"), active())
    click("[aria-label='Forward']")
    check("forward button", wait(lambda: active() == "b"), active())
    ws.call("Runtime.evaluate", {"expression": "window.marker = 1"}, ps)
    click("[aria-label='Reload']")
    reloaded = wait(lambda: ws.call("Runtime.evaluate", {"expression": "window.marker === undefined && document.readyState === 'complete'", "returnByValue": True}, ps)["result"]["result"].get("value"))
    check("reload button", bool(reloaded))

    # Background tab changing its title must update the list (event stream, not a stale snapshot).
    ws.call("Target.createTarget", {"url": U("late"), "background": True})
    check("background title change reaches the list", wait(lambda: "late-done" in titles(), 12), titles())

    n = len(pages())
    ev(f"{root}.querySelector(\".scroll .tab:not([aria-selected='true']) .x\").click()")
    check("close button closes a tab", wait(lambda: len(pages()) == n - 1), len(pages()))

    click(".spaces button[data-id='work']")
    check("workspace switch restores its tabs",
          wait(lambda: ev(f"{root}.querySelector(\".spaces button[aria-pressed='true']\")?.dataset.id") == "work"
               and "w2" in titles() and ev(f"{root}.querySelectorAll('.essentials .tile').length") == 1, 12),
          titles())
    click(".spaces button[data-id='home']")
    wait(lambda: ev(f"{root}.querySelector(\".spaces button[aria-pressed='true']\")?.dataset.id") == "home")

    # Footer shield: uBlock Origin's count for the active tab (its badge), as in the mock ("214 blocked").
    ws.call("Target.createTarget", {"url": U("ads")})
    shield = lambda: ev(f"{root}.querySelector('.shield b')?.textContent.trim()") or ""
    check("shield shows the tab's blocked count",
          wait(lambda: shield().isdigit() and int(shield()) >= 3, 30), shield())
    check("shield label names count and level",
          "blocked on this page" in (ev(f"{root}.querySelector('.shield').getAttribute('aria-label')") or ""))

    # Performance mode: the sidebar drops its motion (and the window its acrylic, checked in nested KWin).
    ev("document.querySelector('helium-sidebar-app').proxy_.handler.setPerformanceMode(true)")
    check("performance mode turns sidebar motion off",
          wait(lambda: ev("document.querySelector('helium-sidebar-app').hasAttribute('reduced')"), 5))
    ev("document.querySelector('helium-sidebar-app').proxy_.handler.setPerformanceMode(false)")
    check("motion back when performance mode is off",
          wait(lambda: ev("!document.querySelector('helium-sidebar-app').hasAttribute('reduced')"), 5))

    wide = ev("innerWidth")
    click("[aria-label='Toggle sidebar']")
    check("toggle collapses to a rail", wait(lambda: (ev("innerWidth") or 999) < 100), f"{wide} -> {ev('innerWidth')}")
    click("[aria-label='Toggle sidebar']")
    check("toggle expands again", wait(lambda: (ev("innerWidth") or 0) > 150), ev("innerWidth"))

    # Maximize/minimize need a window manager; Xvfb has none (checked in nested KWin: shot_probe_maximize.py).
    print("SKIP maximize/minimize dots (no window manager in Xvfb)")

    # The page is gone before it could answer: send without waiting for a reply.
    ws.send("Runtime.evaluate", {"expression": f"{root}.querySelector(\"[aria-label='Close window']\").click()"}, s)
    check("close dot ends the browser (last window)", wait(lambda: br.poll() is not None, 10))
except Exception as e:  # report, then clean up
    import traceback; traceback.print_exc(); fails.append("exception")
finally:
    if br.poll() is None: br.kill()
    xvfb.kill(); srv.shutdown()
print("RESULT", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
