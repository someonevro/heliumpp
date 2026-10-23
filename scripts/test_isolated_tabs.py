#!/usr/bin/env python3
"""Spike test: does an isolated tab keep its cookies to itself?
Starts a local server, launches the browser headless with one normal tab (N) and three isolated tabs
(A sets a cookie, B and C only read), then checks which Cookie headers the server saw.
Run from the project root: python3 -I scripts/test_isolated_tabs.py"""
import http.server, json, os, shutil, subprocess, sys, threading, time, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
seen = []  # (id, cookie header)
reports = {}  # id -> permission states reported by the page

PERM_JS = ("<script>(async()=>{const r={};for(const n of ['geolocation','notifications','camera',"
           "'microphone','clipboard-read']){try{r[n]=(await navigator.permissions.query({name:n})).state}"
           "catch(e){r[n]='err'}}fetch('/report?id=%s&'+new URLSearchParams(r))})()</script>")

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        ident = q.get("id", ["?"])[0]
        if u.path == "/favicon.ico":
            self.send_response(404); self.end_headers(); return
        if u.path == "/slow":
            # Not recorded: this page waits in the TAB, then navigates to /read, so the
            # read happens only after the other tabs have set their cookies.
            seen.append((ident + "-loaded", self.headers.get("Cookie")))
            wait = float(q.get("wait", ["2"])[0]) * 1000
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
            self.wfile.write(("wait <script>setTimeout(()=>location='/read?id=%s',%d)</script>" % (ident, wait)).encode())
            return
        seen.append((ident, self.headers.get("Cookie")))
        self.send_response(200); self.send_header("Content-Type", "text/html")
        if u.path == "/report":
            reports[ident] = {k: v[0] for k, v in q.items() if k != "id"}
            self.send_response(200); self.end_headers(); return
        if u.path == "/perm":
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
            self.wfile.write(("perm <script>(async()=>{const r={};for(const n of ['geolocation','notifications','camera',"
                              "'microphone','clipboard-read']){try{r[n]=(await navigator.permissions.query({name:n})).state}"
                              "catch(e){r[n]='err'}}fetch('/report?id=%s&'+new URLSearchParams(r))})()</script>" % ident).encode())
            return
        if u.path == "/open":
            # Sets a cookie, then opens two popups: one with noopener, one with an opener.
            self.send_header("Set-Cookie", "t=%s; Path=/" % q["c"][0])
            self.end_headers()
            # P3: an about:blank popup that the opener then sends to a URL (the known about:blank hole).
            self.wfile.write(("open <script>setTimeout(()=>{window.open('/read?id=P1','_blank','noopener');"
                              "window.open('/read?id=P2','_blank');"
                              "const w=window.open('about:blank','_blank');setTimeout(()=>{w.location='/read?id=P3'},800);},1500)"
                              "</script>").encode())
            return
        if u.path == "/set":
            self.send_header("Set-Cookie", "t=%s; Path=/" % q["c"][0])
            body = "set %s<meta http-equiv=refresh content='1;url=/read?id=%s2'>" % (ident, ident)
        else:
            body = "read " + ident
            if ident == "N2":  # the normal tab also reports its permission states (headless allows only one start URL)
                body += PERM_JS % "PN"
        self.end_headers(); self.wfile.write(body.encode())

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = "http://127.0.0.1:%d" % port
prof = os.path.join(BUILD, "profile-isotest"); shutil.rmtree(prof, ignore_errors=True)
env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
iso = ",".join([base + "/set?id=A&c=A", base + "/slow?id=B&wait=4", base + "/slow?id=C&wait=6",
                base + "/open?id=O&c=O", base + "/perm?id=PI"])
cmd = [BUILD + "/src/out/Default/helium", "--user-data-dir=" + prof, "--headless=new", "--no-sandbox",
       "--disable-gpu", "--disable-popup-blocking", "--helium-isolated-tabs=" + iso, base + "/set?id=N&c=N"]
p = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=open(BUILD + "/isotest.log", "w"))
time.sleep(40); p.terminate()
try: p.wait(10)
except subprocess.TimeoutExpired: p.kill()
srv.shutdown()
by = {}
for ident, ck in seen: by.setdefault(ident, []).append(ck)
print(json.dumps(by, indent=1))
ok = True
def check(name, cond):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name)
check("normal tab reached the server", "N" in by and "N2" in by)
check("normal tab keeps its own cookie (N2 sees t=N)", by.get("N2") and by["N2"][0] == "t=N")
check("isolated tabs opened (A, B, C reached the server)", all(k in by for k in "ABC"))
check("isolated A keeps its cookie across navigation (A2 sees t=A)", by.get("A2") and by["A2"][0] == "t=A")
check("isolated B does NOT see normal or A cookies", by.get("B") and by["B"][0] is None)
check("isolated C does NOT see normal or A cookies", by.get("C") and by["C"][0] is None)
check("isolated A does NOT see the normal tab's cookie (A first request)", by.get("A") and by["A"][0] is None)
print("permission states, normal tab :", reports.get("PN"))
print("permission states, isolated tab:", reports.get("PI"))
check("normal tab reported permission states", reports.get("PN"))
check("normal tab: geolocation is 'prompt' (test is meaningful)", reports.get("PN", {}).get("geolocation") == "prompt")
check("isolated tab: every permission is 'denied'",
      reports.get("PI") and all(v == "denied" for v in reports["PI"].values()))
check("popup with noopener opened from isolated O stays in O's container (sees t=O)", by.get("P1") and by["P1"][0] == "t=O")
check("popup with opener opened from isolated O stays in O's container (sees t=O)", by.get("P2") and by["P2"][0] == "t=O")
check("about:blank popup from isolated O, then sent to a URL, stays in O's container (sees t=O)", by.get("P3") and by["P3"][0] == "t=O")
sys.exit(0 if ok else 1)

