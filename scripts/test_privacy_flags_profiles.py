#!/usr/bin/env python3
"""Privacy flags are browser-wide (Local State), levels are per profile (0096). A profile on Maximum must keep
its fingerprinting/referrer flags when a NEW second profile (no level yet, so Medium by default) starts with it,
in either load order. Run from the project root: python3 -I scripts/test_privacy_flags_profiles.py"""
import json, os, shutil, subprocess, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
STRONG = {"fingerprinting-client-rects-noise", "remove-client-hints@1", "remove-cross-origin-referrers@1"}
fails = 0
# Last case: only the new profile starts; Default (on Maximum) is not loaded at all.
for order in (["Default", "Profile 1"], ["Profile 1", "Default"], ["Profile 1"]):
    d = os.path.join(BUILD, "profile-flags"); shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(d, "Default")); os.makedirs(os.path.join(d, "Profile 1"))
    json.dump({"helium": {"completed_onboarding": True, "privacy_mode": "maximum",
                          "privacy_mode_applied": "maximum"}}, open(os.path.join(d, "Default", "Preferences"), "w"))
    json.dump({"helium": {"completed_onboarding": True}}, open(os.path.join(d, "Profile 1", "Preferences"), "w"))
    json.dump({"profile": {"last_active_profiles": order,
                           "info_cache": {"Default": {"name": "A"}, "Profile 1": {"name": "B"}}},
               "browser": {"enabled_labs_experiments": sorted(STRONG | {"fingerprinting-canvas-measuretext-noise",
                                                                         "reduced-system-info@1"})}},
              open(os.path.join(d, "Local State"), "w"))
    env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
    extra = ["--profile-directory=Profile 1"] if order == ["Profile 1"] else []
    b = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + d, "--headless=new", *extra,
                          "--no-sandbox", "--disable-gpu", "about:blank"],
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(8); b.terminate(); b.wait(30)
    flags = set(json.load(open(os.path.join(d, "Local State")))["browser"].get("enabled_labs_experiments", []))
    mode = json.load(open(os.path.join(d, "Profile 1", "Preferences")))["helium"].get("privacy_mode")
    ok = STRONG <= flags and mode == "medium"
    fails += not ok
    print("ok" if ok else "FAIL", "order", order, "new profile mode", mode, "missing", sorted(STRONG - flags))

def run(d, profile, *args):
    env = dict(os.environ, XDG_CONFIG_HOME=BUILD + "/xdg/config", XDG_CACHE_HOME=BUILD + "/xdg/cache")
    b = subprocess.Popen([BUILD + "/src/out/Default/helium", "--user-data-dir=" + d, "--headless=new",
                          "--profile-directory=" + profile, *args, "--no-sandbox", "--disable-gpu", "about:blank"],
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(8); b.terminate(); b.wait(30)
    return set(json.load(open(os.path.join(d, "Local State")))["browser"].get("enabled_labs_experiments", []))

# Explicit Medium in Profile 1 while Default (Maximum) is closed: Default's level is remembered in Local State
# from its own last start, so the flags stay. A deleted profile's remembered Maximum must not keep them.
for name, deleted in (("closed profile", False), ("deleted profile", True)):
    d = os.path.join(BUILD, "profile-flags"); shutil.rmtree(d, ignore_errors=True)
    for prof in ("Default", "Profile 1"):
        os.makedirs(os.path.join(d, prof))
        json.dump({"helium": {"completed_onboarding": True}}, open(os.path.join(d, prof, "Preferences"), "w"))
    json.dump({"profile": {"info_cache": {"Default": {"name": "A"}, "Profile 1": {"name": "B"}}}},
              open(os.path.join(d, "Local State"), "w"))
    run(d, "Default", "--privacy-mode=maximum")
    if deleted:  # what Chromium's profile deletion leaves: no info_cache entry
        ls = json.load(open(os.path.join(d, "Local State"))); del ls["profile"]["info_cache"]["Default"]
        json.dump(ls, open(os.path.join(d, "Local State"), "w"))
    flags = run(d, "Profile 1", "--privacy-mode=medium")
    ok = (STRONG.isdisjoint(flags)) if deleted else (STRONG <= flags)
    fails += not ok
    print("ok" if ok else "FAIL", name, "strong flags kept:", STRONG <= flags, "(want", (not deleted), ")")
print("ALL PASS" if not fails else f"{fails} FAILED")
raise SystemExit(1 if fails else 0)
