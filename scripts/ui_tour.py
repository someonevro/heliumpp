"""Drive the browser in a private Xvfb display (never the real desktop) and screenshot each step.
Usage: python3 -I ui_tour.py <out-dir> <scenario> [browser binary]
Scenarios: see SCENARIOS below. Input goes through XTEST on that display only. stdlib + ctypes."""
import ctypes, json, os, shutil, subprocess, sys, time

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out, scenario = sys.argv[1], sys.argv[2]
binary = sys.argv[3] if len(sys.argv) > 3 else f'{root}/build/src/out/Default/helium'
DISP, W, H = ':95', 1100, 800

x11, xtst = ctypes.CDLL('libX11.so.6'), ctypes.CDLL('libXtst.so')
x11.XOpenDisplay.restype = ctypes.c_void_p
x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
x11.XStringToKeysym.restype = ctypes.c_ulong
for f in (xtst.XTestFakeMotionEvent, xtst.XTestFakeButtonEvent, xtst.XTestFakeKeyEvent, x11.XFlush):
    f.argtypes = None
dpy = None

def flush(): x11.XFlush(ctypes.c_void_p(dpy))
def move(x, y): xtst.XTestFakeMotionEvent(ctypes.c_void_p(dpy), -1, x, y, 0); flush()
def click(x, y, button=1):
    move(x, y); time.sleep(0.15)
    xtst.XTestFakeButtonEvent(ctypes.c_void_p(dpy), button, 1, 0); flush(); time.sleep(0.05)
    xtst.XTestFakeButtonEvent(ctypes.c_void_p(dpy), button, 0, 0); flush()
def key(combo):  # e.g. "ctrl+alt+n", "Escape", "Return"
    names = {'ctrl': 'Control_L', 'alt': 'Alt_L', 'shift': 'Shift_L'}
    codes = [x11.XKeysymToKeycode(ctypes.c_void_p(dpy), x11.XStringToKeysym(names.get(k, k).encode()))
             for k in combo.split('+')]
    for c in codes: xtst.XTestFakeKeyEvent(ctypes.c_void_p(dpy), c, 1, 0); flush(); time.sleep(0.03)
    for c in reversed(codes): xtst.XTestFakeKeyEvent(ctypes.c_void_p(dpy), c, 0, 0); flush()
def type_text(s):
    for ch in s: key({' ': 'space', '.': 'period', '/': 'slash', ':': 'colon'}.get(ch, ch))
def shot(name):
    subprocess.run(['import', '-display', DISP, '-window', 'root', f'{out}/{name}.png'], check=True)
    print('shot', name, flush=True)

SEED = {'helium': {'browser': {'layout': 2, 'zen_mode': False}, 'completed_onboarding': True, 'privacy_mode': 'medium',
                   'services': {'schema_version': 1, 'user_consented': True}},
        'vertical_tabs': {'collapsed_state': False, 'uncollapsed_width': 200}}

def s_main():  # NTP, hover window controls, app menu, isolated tab, settings
    time.sleep(10); shot('01-ntp')
    move(W - 60, 6); time.sleep(1.5); shot('02-controls-hover')
    move(W // 2, H // 2); time.sleep(1.5); shot('03-controls-left')
    key('alt+e'); time.sleep(1.5); shot('04-app-menu')
    key('Escape'); time.sleep(0.5)
    key('ctrl+alt+n'); time.sleep(4); shot('05-isolated-tab')
    key('ctrl+l'); type_text('chrome://settings'); key('Return'); time.sleep(4); shot('06-settings')
    key('ctrl+l'); type_text('chrome://settings/help'); key('Return'); time.sleep(4); shot('07-about')
def s_horizontal():
    time.sleep(10); shot('01-ntp-horizontal')
    move(W - 60, 6); time.sleep(1.5); shot('02-controls-hover-horizontal')
    key('alt+e'); time.sleep(1.5); shot('03-app-menu-horizontal')
def s_onboarding():  # fresh profile: onboarding pages; Return/Tab walk through the flow
    time.sleep(12); shot('01-onboarding')
    for i in range(2, 9):
        key('Tab'); key('Return'); time.sleep(2.5); shot(f'{i:02d}-onboarding')
def s_perfmotion():  # an open page must follow the NTP Performance switch at runtime
    time.sleep(8); shot('01-probe-before')
    key('ctrl+t'); time.sleep(3); click(577, 462); time.sleep(2); shot('02-ntp-switch-on')
    key('ctrl+1'); time.sleep(2); shot('03-probe-after-on')
    key('ctrl+2'); time.sleep(2); click(452, 462); time.sleep(2); key('ctrl+1'); time.sleep(2); shot('04-probe-after-off')
def s_hold():  # keep the window open with the controls hovered, for UI DevTools inspection (TOUR_HOLD seconds)
    time.sleep(8); move(W - 60, 6); time.sleep(2); shot('hold-hover')
    time.sleep(float(os.environ.get('TOUR_HOLD', 20)))
def s_clicks():  # fresh profile; TOUR_CLICKS="x,y x,y ..." with a screenshot after each click
    time.sleep(12); shot('00')
    for i, xy in enumerate(os.environ.get('TOUR_CLICKS', '').split(), 1):
        x, y = map(int, xy.split(',')); click(x, y); time.sleep(3); shot(f'{i:02d}')
def s_newtab():  # what does Ctrl+T open
    time.sleep(8); key('ctrl+t'); time.sleep(4); shot('01-ctrl-t')
def s_shot():  # one screenshot after startup
    time.sleep(10); shot('01')
def s_settings_appearance():  # Settings > Appearance, then the page after a click at TOUR_CLICKS (if set)
    time.sleep(8); key('ctrl+l'); type_text('chrome://settings/appearance'); key('Return'); time.sleep(4); shot('01')
    for i, xy in enumerate(os.environ.get('TOUR_CLICKS', '').split(), 2):
        x, y = map(int, xy.split(',')); click(x, y); time.sleep(3); shot(f'{i:02d}')
    key('ctrl+t'); time.sleep(4); shot('99-ctrl-t')
SCENARIOS = {'main': (s_main, SEED), 'horizontal': (s_horizontal, {**SEED, 'helium': {**SEED['helium'], 'browser': {'layout': 1, 'zen_mode': False}}}),
             'onboarding': (s_onboarding, None), 'perfmotion': (s_perfmotion, SEED), 'hold': (s_hold, SEED), 'clicks': (s_clicks, None), 'newtab': (s_newtab, SEED), 'shot': (s_shot, SEED), 'settings': (s_settings_appearance, SEED)}

fn, seed = SCENARIOS[scenario]
os.makedirs(out, exist_ok=True)
prof = f'{root}/build/profile-tour-{scenario}'; shutil.rmtree(prof, ignore_errors=True); os.makedirs(f'{prof}/Default')
if seed and os.environ.get('TOUR_CUSTOM_FRAME') == '1':  # Chromium-drawn title bar + buttons
    seed = {**seed, 'browser': {'custom_chrome_frame': True}}
if seed and os.environ.get('TOUR_BONJOURR') == '1':  # bundled Bonjourr as the new tab page
    seed = {**seed, 'helium': {**seed['helium'], 'ntp': {'bonjourr': True}}}
if seed: json.dump(seed, open(f'{prof}/Default/Preferences', 'w'))
xvfb = subprocess.Popen(['Xvfb', DISP, '-screen', '0', f'{W}x{H}x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
dpy = x11.XOpenDisplay(DISP.encode())
assert dpy, 'cannot open private display'
env = {k: v for k, v in os.environ.items() if k not in ('GDK_SCALE', 'GDK_DPI_SCALE', 'QT_SCALE_FACTOR')}  # host HiDPI vars
env = dict(env, DISPLAY=DISP, XDG_CONFIG_HOME=f'{root}/build/xdg/config', XDG_CACHE_HOME=f'{root}/build/xdg/cache')
br = subprocess.Popen([binary, '--ozone-platform=x11', f'--user-data-dir={prof}', '--no-sandbox', '--test-type', '--disable-gpu',
                       f'--window-size={W},{H}', '--window-position=0,0', '--enable-logging=stderr',
                       *os.environ.get('TOUR_URLS', '').split(), *os.environ.get('TOUR_ARGS', '').split()],
                      env=env, stdout=subprocess.DEVNULL, stderr=open(f'{out}/{scenario}.log', 'w'))
try:
    fn()
finally:
    br.terminate()
    try: br.wait(15)
    except subprocess.TimeoutExpired: br.kill()
    xvfb.kill()
