#!/usr/bin/env python3
"""New tab page (patch 0128, designs/redesign/mock.html): in a private Xvfb display (never the real desktop), checks
the seeded wallpaper thumbnail is shown softened behind the page, the clock and date, the "/" shortcut focusing the
search field, the search field navigating (host and search query), the focus-round chip opening its popover and
Escape closing it, and that the privacy level / performance switches are no longer on the page.
Run from the project root: python3 -I scripts/test_ntp.py"""
import http.server, json, os, shutil, subprocess, sys, threading, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PORT, HTTP, DISP = 9362, 8362, ":96"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS  # noqa: E402

class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = f"<title>{self.path}</title>".encode()
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", HTTP), Page)
threading.Thread(target=srv.serve_forever, daemon=True).start()

prof = os.path.join(BUILD, "profile-ntp-test")
shutil.rmtree(prof, ignore_errors=True); os.makedirs(f"{prof}/Default")
# The browser decodes this file (--match-wallpaper=<path>) and saves the thumbnail the page shows.
wall = f"{prof}/wall.jpg"
subprocess.run(["magick", "-size", "640x360", "gradient:navy-teal", wall], check=True)
json.dump({"helium": {"completed_onboarding": True, "browser": {"layout": 2}}},
          open(f"{prof}/Default/Preferences", "w"))

xvfb = subprocess.Popen(["Xvfb", DISP, "-screen", "0", "1400x900x24", "-nolisten", "tcp"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
env = {**os.environ, "DISPLAY": DISP, "XDG_CONFIG_HOME": f"{BUILD}/xdg/config", "XDG_CACHE_HOME": f"{BUILD}/xdg/cache"}
env.pop("WAYLAND_DISPLAY", None)
br = subprocess.Popen([f"{BUILD}/src/out/Default/helium", "--ozone-platform=x11", f"--user-data-dir={prof}",
                       "--no-first-run", f"--remote-debugging-port={PORT}", "--window-size=1200,800",
                       # Nothing leaves the machine (the search check would reach the real engine).
                       "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1", f"--match-wallpaper={wall}",
                       "chrome://newtab/"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        except OSError:
            pass
        time.sleep(0.25)
    return pred()

try:
    ver = wait(lambda: json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version")), 20)
    ws = WS(ver["webSocketDebuggerUrl"])
    pages = lambda: [t for t in ws.call("Target.getTargets")["result"]["targetInfos"] if t["type"] == "page"]
    ntp = wait(lambda: next((t for t in pages() if t["url"].startswith(("chrome://newtab", "chrome://new-tab-page"))), None), 15)
    s = ws.call("Target.attachToTarget", {"targetId": ntp["targetId"], "flatten": True})["result"]["sessionId"]
    def ev(expr):
        r = ws.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True}, s)
        return r["result"].get("result", {}).get("value")
    root = "document.querySelector('ntp-app').shadowRoot"
    # The first page may load before the decode; a reload reads the saved thumbnail.
    time.sleep(4)
    ws.call("Page.reload", {}, s)
    time.sleep(2)
    q = lambda sel: f"{root}.querySelector({json.dumps(sel)})"
    wait(lambda: ev(f"!!{q('#time')}"))

    bg = ev(f"getComputedStyle({q('#wall')}).backgroundImage") or ""
    check("wallpaper thumbnail behind the page", bg.startswith('url("data:image/jpeg;base64,'), bg[:60])
    check("wallpaper is softened (blur)", "blur" in (ev(f"getComputedStyle({q('#wall')}).filter") or ""))
    t = ev(f"{q('#time')}.textContent.trim()") or ""
    check("clock shows hh:mm", len(t) >= 4 and ":" in t, t)
    check("date shown", bool(ev(f"{q('#date')}.textContent.trim()")))
    check("no privacy or performance switch on the page",
          ev(f"!{q('#privacySwitch')} && !{q('#performanceSwitch')} && !{q('#greeting')}") is True)

    ws.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape"}, s)
    ev(f"{q('#searchInput')}.blur()")
    ws.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "/", "text": "/"}, s)
    ws.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "/"}, s)
    check("'/' focuses the search field",
          wait(lambda: ev(f"{root}.activeElement?.id") == "searchInput", 3), ev(f"{root}.activeElement?.id"))
    check("'/' is not typed into the field", ev(f"{q('#searchInput')}.value") == "", ev(f"{q('#searchInput')}.value"))

    ev(q(".chip[data-chip='focus']") + ".click()")
    check("focus chip opens its popover", wait(lambda: ev(f"!!{q('.pop')}") and
          "25 min" in (ev(f"{q('.pop')}.innerText") or ""), 3), ev(f"{q('#foot')}.innerText"))
    ev(f"{q('.pop button')}.focus()")
    ws.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape",
                                      "windowsVirtualKeyCode": 27}, s)
    check("Escape closes the popover", wait(lambda: ev(f"!{q('.pop')}"), 3))

    # Performance mode: no wallpaper blur, the plain theme gradient instead.
    ev("document.querySelector('ntp-app').pageHandler_.setPerformanceMode(true)")
    ws.call("Page.reload", {}, s); time.sleep(2)
    check("performance mode: no wallpaper blur",
          wait(lambda: ev(f"getComputedStyle({q('#wall')}).filter") == "none" and
               not (ev(f"getComputedStyle({q('#wall')}).backgroundImage") or "").startswith('url('), 5),
          ev(f"getComputedStyle({q('#wall')}).filter"))
    ev("document.querySelector('ntp-app').pageHandler_.setPerformanceMode(false)")
    ws.call("Page.reload", {}, s); time.sleep(2)

    ev(f"{q('#searchInput')}.value = 'hello helium'; {q('#searchForm')}.requestSubmit()")
    check("search field sends a query to the search engine",
          wait(lambda: any("hello" in p["url"] and "helium" in p["url"] for p in pages()), 8),
          [p["url"] for p in pages()])
    s = ws.call("Target.attachToTarget", {"targetId": ws.call("Target.createTarget", {"url": "chrome://newtab/"})
                                          ["result"]["targetId"], "flatten": True})["result"]["sessionId"]
    wait(lambda: ev(f"!!{q('#searchForm')}"))
    ev(f"{q('#searchInput')}.value = 'http://127.0.0.1:{HTTP}/typed'; {q('#searchForm')}.requestSubmit()")
    check("search field opens a typed address",
          wait(lambda: any(p["url"] == f"http://127.0.0.1:{HTTP}/typed" for p in pages()), 8),
          [p["url"] for p in pages()])
except Exception:
    import traceback; traceback.print_exc(); fails.append("exception")
finally:
    if br.poll() is None: br.kill()
    xvfb.kill(); srv.shutdown()
    shutil.rmtree(prof, ignore_errors=True)
print("RESULT", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
