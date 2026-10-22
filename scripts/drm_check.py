"""Ask a built helium whether Widevine/EME is usable. stdlib only; needs chromedriver on :9515.
usage: drm_check.py <profile-dir>"""
import json, os, sys, urllib.request

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
D = "http://127.0.0.1:9515"
def call(method, path, body=None):
    req = urllib.request.Request(D + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))["value"]

caps = {"capabilities": {"alwaysMatch": {"goog:chromeOptions": {
    "binary": f"{root}/build/src/out/Default/helium", "excludeSwitches": ["disable-extensions"],
    "args": ["--headless=new", f"--user-data-dir={sys.argv[1]}", "--no-first-run"]}}}}
sid = call("POST", "/session", caps)["sessionId"]
try:
    call("POST", f"/session/{sid}/url", {"url": "http://127.0.0.1:8765/ok.js"})  # any secure-context (localhost) page
    js = """
    const done = arguments[arguments.length-1];
    const cfg = [{initDataTypes:['cenc'], videoCapabilities:[{contentType:'video/mp4; codecs="avc1.42E01E"', robustness:'SW_SECURE_DECODE'}],
                  audioCapabilities:[{contentType:'audio/mp4; codecs="mp4a.40.2"'}]}];
    const out = {h264: MediaSource.isTypeSupported('video/mp4; codecs="avc1.42E01E"'),
                 aac: MediaSource.isTypeSupported('audio/mp4; codecs="mp4a.40.2"'),
                 vp9: MediaSource.isTypeSupported('video/webm; codecs="vp9"'),
                 av1: MediaSource.isTypeSupported('video/mp4; codecs="av01.0.05M.08"')};
    navigator.requestMediaKeySystemAccess('com.widevine.alpha', cfg)
      .then(a => { out.widevine = 'available: ' + a.keySystem; done(out); })
      .catch(e => { out.widevine = 'unavailable: ' + e.name + ': ' + e.message; done(out); });
    """
    print(json.dumps(call("POST", f"/session/{sid}/execute/async", {"script": js, "args": []}), indent=1))
finally:
    call("DELETE", f"/session/{sid}")
