"""Drive helium with chromedriver (stdlib only) against the local ad test server.
usage: run.py <profile-dir> <wait-seconds> [extra chrome args...]   (server.py must be running on :8765)"""
import json, sys, time, urllib.request, os

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = "http://127.0.0.1:9515"

def call(method, path, body=None):
    req = urllib.request.Request(D + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))["value"]

profile, wait, extra = sys.argv[1], float(sys.argv[2]), sys.argv[3:]
hosts = ['pagead2.googlesyndication.com', 'securepubads.g.doubleclick.net', 'www.google-analytics.com', 'connect.facebook.net', 'static.ads-twitter.com', 'cdn.taboola.com', 'sb.scorecardresearch.com', 'c.amazon-adsystem.com', 'ads.pubmatic.com', 'widget.criteo.com', 'control.example']
rules = ", ".join(f"MAP {h} 127.0.0.1" for h in hosts)
caps = {"capabilities": {"alwaysMatch": {"goog:chromeOptions": {
    "binary": f"{root}/build/src/out/Default/helium",
    "excludeSwitches": [] if "--disable-extensions" in extra else ["disable-extensions"],
    "args": ["--headless=new", f"--user-data-dir={profile}", "--no-first-run", f"--host-resolver-rules={rules}", *extra]}}}}
sid = call("POST", "/session", caps)["sessionId"]
try:
    time.sleep(wait)  # let the blocker start and compile its lists
    call("POST", f"/session/{sid}/url", {"url": "http://127.0.0.1:8765/test"})
    out = None
    for _ in range(40):
        time.sleep(0.5)
        txt = call("POST", f"/session/{sid}/execute/sync", {"script": "return document.body.textContent", "args": []})
        if txt.startswith("RESULT"):
            out = json.loads(txt[7:]); break
    print(json.dumps(out))
finally:
    call("DELETE", f"/session/{sid}")
