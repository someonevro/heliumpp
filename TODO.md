# TODO.md
Legend: [P]lanned [I]nvestigated [M]plemented [T]ested [V]erified [B]locked [D]eferred

## Phase 1 — Research
- [I] Foundation options (ungoogled-chromium, CEF, Helium) — README-level only; source read pending
- [V] Read helium-chromium patches: MV2 = 60-line patch, uBO as component, Chromium 155.0.8059.84, Widevine via component updater
- [P] Confirm current Chromium build docs + disk/RAM/time
- [T] Chromium 155 source prepared: tarballs + deps extracted, Helium patch series applied cleanly, gn gen OK (2026-10-19); compile NOT started
- [T] Full Helium/Chromium 155 build compiled on Linux (2026-10-20, 5h40m); binary `helium` produced, NOT yet launched/verified
- [T] Headless smoke test: --version OK, https://example.com loads, uBO component registered in profile (2026-10-20); GUI/blocking/DRM unverified
- [V] GUI window launches and shows upstream Helium onboarding (user-confirmed 2026-10-20)
- [V] Own patch series works end-to-end: patches/0001 -> 17 s incremental build -> "Helium Dev" seen in chrome://version (user-confirmed 2026-10-20)
- [T] --privacy-mode cookie prefs per mode verified headless (scripts/test_privacy_mode.sh); behavior untested, other settings not done (2026-10-20)
- [V] cookie rule verified by hand: maximum deletes cookies+site data on close, medium keeps login (WhatsApp Web, user-confirmed 2026-10-20); usability only verified via prefs
- [T] Mode now persists (helium.privacy_mode) and enforces WebRTC/HTTPS/permissions/preloading too; prefs-level test passes (2026-10-20); referrer+fingerprinting, chooser UI still open
- [V] Mode chooser page in onboarding works (user-confirmed 2026-10-20)
- [T] Fingerprinting/referrer flags per mode: stored + restart effect verified headless (hardwareConcurrency 2 in maximum after restart); referrer/client-hints behavior untested (2026-10-20)
- [T] Tab layout chooser in onboarding (vertical/horizontal, stored in helium.browser.layout); built, GUI untested (2026-10-20)
- [T] uBO network blocking verified headless: 10/10 ad+tracker hosts blocked after warm-up; fresh profile unprotected for first seconds; cosmetic/YouTube/allowlist/updates/malware lists unverified (2026-10-20)
- [T] Codecs H.264/AAC/VP9/AV1 supported; Widevine NOT installed on a fresh profile (needs Helium services + update fetching on); DRM playback untested, legal terms unresolved (2026-10-20)
- [T] Compact mode (Helium zen mode) option on tab layout onboarding step; built, GUI untested (2026-10-20)
- [T] Default dark theme color + opt-in wallpaper accent (Linux/Omarchy); headless tests pass; no UI toggle yet; user visual check pending (2026-10-20)
- [T] Sidebar footer buttons (settings/extensions/downloads/history/bookmarks) built; GUI check pending (2026-10-20)
- [T] Tab list top gap + experimental --sidebar-toolbar (toolbar in sidebar column); built, GUI untested (2026-10-20)
- [T] Sidebar toolbar two-row layout + pill address bar + hover copy-link button; built, GUI untested (2026-10-20)
- [T] Address bar above button row; window controls hidden until hovering top-right corner (slide-in); built, GUI untested (2026-10-20)
- [T] Nav row moved to sidebar bottom, address bar hosted inside the tab strip region (reparented); built, GUI untested (2026-10-20)
- [T] Nav row now hidden in sidebar mode (patch 0015); built, GUI untested (2026-10-20)
- [I] DRM approach (no bundling; user-side install) — legality of auto-fetch unverified
- [I] iOS = WKWebView (Blink only prototypes; EU/Japan status unverified)
- [P] Android feasibility detail (Cromite/Vanadium study)
- [P] Choose project name
- [P] Telemetry/network audit (needs a running build)
- [I] Architecture approved by user 2026-10-19 (desktop fork + uBO component); verification needs a build
- [V] Preset map prefs/flags checked against build/src (2026-10-20); see ARCHITECTURE.md

## Requirements tracker (from prompt.txt) — all [P] unless stated
- Zen-style UI: vertical tabs, pinned, groups, workspaces, split, compact, themes, new tab
- Onboarding + 3 modes (Prioritize usability / Medium privacy [recommended] / Maximum privacy; all with uBO), chooser shows what each mode does, persistence, change later
- Declarative preset config, validation, summary, reset, exceptions, restart notice, tests
- uBO-level blocking, lists, auto-update, cache, per-site, counter, private mode
- DRM/Widevine path, codecs, HW accel, diagnostics page
- Telemetry audit doc
- Tabs, omnibox, bookmarks, history, downloads, private, find, permissions, site data, search engine, shortcuts, settings, session restore, import, extensions
- Security: sandbox kept, IPC validation, threat model, update process
- Platforms: Linux, Windows, macOS, Android, iOS (see PLATFORM_SUPPORT.md)

## Resolved
- Preset count: user chose display order Low, Medium, High, Ultra, then Ad Blocking Only last (5 modes). Fifth-level question not explicitly answered; treated as closed unless user reopens.

## Phase 3 prep
- [T] `shared/presets.json` schema + 5 presets drafted (values are proposals, not yet enforced by any browser); `python3 -I shared/tests/test_presets.py` passes 7 tests (completeness, valid values, ladder monotonic, security floor, no telemetry, adblock_only light)
- [I] Setting -> mechanism map drafted in ARCHITECTURE.md (partly unverified); implementation needs Chromium source

## Session 2 additions (2026-10-21)
- [T] Window-controls bar drops down and pushes the page (0033/0042): built, user confirmed it works
- [T] New tab page greeting/search/glass tiles/privacy switch/performance switch (0034-0040, 0046-0048): headless screenshots + user said it works
- [I] First-run DNS step (0039): built; not seen, DoH not observed in use
- [T] Performance mode prefs (0047/0048): prefs verified by script, no measured saving, UI not watched
- [T] Isolated tabs (0049-0057): cookies, popups, permissions, disk traces, wipe, badge verified by scripts/virtual display; menu click not verified
- [ ] Isolated tabs: about:blank popup case, downloads, password manager, clipboard write
- [ ] General speed outside performance mode (measure first)
- [ ] Restyle: horizontal layout, menus/popups, Settings/onboarding pages, red close hover, wallpaper image on NTP, privacy chip
- [ ] Update CLAUDE.md (three modes, not six), ARCHITECTURE.md, PLATFORM_SUPPORT.md; replay the patch series on a pristine tree
