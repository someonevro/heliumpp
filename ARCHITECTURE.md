# ARCHITECTURE.md

Phase 1 research, written 2026-10-19. Method: web searches/fetches (READMEs, news) + shallow clones of Helium repos in `research/` (untrusted, read-only; patches read, nothing built). Items marked UNVERIFIED need a check before any commitment. Reviewed again 2026-10-19 after model switch to Sonnet 5.5; corrections below.

## Environment (verified by command)
- Linux (Omarchy/Arch), 12 cores, 15 GB RAM, 655 GB free on /home. Workspace: `/home/someone/Projects/browser`.
- Chromium docs (older revisions seen): >=100 GB disk, 8 GB RAM min, 16+ GB recommended. Here: 15 GB RAM is borderline for linking; expect long builds (hours, likely 4-10 h clean on 12 cores, ESTIMATE). Must confirm against current docs before building.

## Findings
### Foundation
- ungoogled-chromium: BSD-3, patch set + scripts (not a full fork). Linux packaged via many distro repos; macOS via Homebrew; Windows supported by build system. No official Android repo (Bromite is dead-ish/related). Source: github.com/ungoogled-software/ungoogled-chromium
- Helium (imputnet): beta; began as ungoogled-chromium fork, plus patches from Inox, Debian, Bromite, Iridium, Brave. Platforms: macOS, Linux, Windows only (no Android/iOS). Own code/patches GPL-3.0. Repos: `helium-chromium` (patches), `helium-linux/-macos/-windows` (packaging), `uBlock` (Helium-specific uBO fork: own filters/defaults, CNAME uncloaking), `helium-onboarding` (first-run at `helium://setup`), `helium-services` (extension proxy, filter lists, updates, crash reports), `helium-nonfree-assets`. Linux build: Docker + `scripts/build.sh`; output tar.xz/AppImage/.deb; PGP-signed releases; apt repo + COPR.
- VERIFIED from source (clone in `research/helium-chromium`, `research/uBlock`, 2026-10-19):
  - Helium pins Chromium **155.0.8059.84**; patches come from ungoogled-chromium, brave, bromite, debian, inox, iridium, plus `helium/` (core, ui, sync...).
  - MV2 is kept by a **60-line patch** `ungoogled-chromium/extensions-manifestv2.patch` (read in full): makes `ShouldDisableLegacyExtensions()` return false, removes the MV2 deprecation warning and the info-generator deprecation fields. It only switches off the *disable* logic, so **the MV2 runtime code still exists in Chromium 155**. Small today; if upstream later deletes the MV2 runtime, the patch grows into a real maintenance burden. Earlier news claim "151 deletes MV2 code" is contradicted by Helium working on 155 — treat as unverified.
  - uBO is installed as a **component extension** (`helium/core/ublock-install-as-component.patch`, id `blockjmkbacgjkknlgpkjjiijinjdanf`; webstore id `cjpalhdlnbpafiamejdnhcphjbkeiagm`), with patches for default settings, DNS CNAME uncloaking (`ublock-dns-uncloaking`), Helium-services filter list source, settings-page entry, and an extension-download proxy.
  - Forked uBO (`research/uBlock`): `manifest_version: 2`; `dist/version` = 1.75.0 (the 1.15.11.0 in `platform/chromium/manifest.json` is just the manifest field, not the release). GPL-3.0 (LICENSE.txt). Helium's own LICENSE: GPL-3.0.
  - `flags.gn`: `enable_widevine=true` (builds with Widevine hooks, no CDM bundled), `safe_browsing_mode=0`, `enable_reporting=false`, `enable_mdns=false`, no Google API keys. `component-updates.patch` blocks every component-updater registration except CRLSet (`hfnkpimlhhgieaddgfemjhofmfblmnib`) and WidevineCdm (`oimompecagnajdejgnnjijobebaeigek`). So Helium downloads Widevine through Chromium's normal component updater (Google servers) and nothing else. Whether it plays Netflix etc.: UNTESTED.
  - Dependence on `helium-services` (their servers) for extension proxy/lists: we must self-host or replace.

### Manifest V2 / uBlock Origin (key risk)
- News (not Chromium source): Chrome 150 removed the MV2 re-enable flag; CWS dropped MV2 extensions 2026-08-31. Helium's Chromium 155 build still carries MV2 runtime (patch above), so removal of the runtime has NOT happened as of 155. Watch each Chromium major.
- Brave keeps uBO/uMatrix/NoScript/AdGuard MV2 via own infrastructure (patched Chromium).
- Consequence: full uBO needs us to carry the MV2 patch and bundle uBO ourselves (not from CWS), rebased every Chromium major. Done by Brave and Helium. Alternatives: uBO Lite (MV3, declarativeNetRequest; weaker: no dynamic filtering, cosmetic/scriptlet limits) or native C++ engine (e.g. Brave's `adblock-rust`, MPL-2.0 — licence/fit UNVERIFIED).

### DRM
- Chrome/Edge ship Widevine; ungoogled-chromium/Helium do not. Google licenses Widevine CDM to vendors; no right to redistribute in our builds. Do not bundle.
- Legit path: on first use, user-triggered fetch of the CDM from Google's component update channel, or use CDM from user's own installed Chrome / distro package (`widevine-cdm` in nixpkgs). Legal status of automated fetch UNVERIFIED — need to read Widevine/Chrome ToS before building the feature. Expect L3 (software) only: Netflix likely capped at 720p; no L1 on Linux.
- Codecs: need `proprietary_codecs=true`, `ffmpeg_branding=Chrome` for H.264/AAC (patent licensing is the distributor's concern — document).

### Mobile
- Android: Chromium Android build is possible (own patched build, much bigger infra: Android SDK/NDK in tree). Extensions are not supported in stock Chromium Android. Best path: separate later effort, reuse patch set + shared privacy schema; blocking via native engine (not extensions). Prior art to study: Bromite (archived), Vanadium (GrapheneOS), Cromite.
- iOS: Only WebKit is allowed worldwide except EU (BrowserEngineKit, iOS 17.4+, entitlement) and Japan (law, deadline Dec 2025; actual state UNVERIFIED). Blink on iOS exists only as prototypes (Edge, June 2026); none shipped. Decision: iOS = **WKWebView app**, WKContentRuleList blocking (Firefox iOS, Brave, Vivaldi do this), shared preset schema. Not "ungoogled-chromium". Must be explicit to user.

### CEF / alternatives
- CEF: embeds stock Chromium; no ungoogled patches by default, limited control over browser UI/privacy internals, MV2/extensions poorly supported (Alloy style), Widevine needs CDM too. Rejected as main path: fails extension + privacy-depth goals. Electron/WebKitGTK rejected per spec.

## Recommended architecture (APPROVED by user 2026-10-19, subject to build-permission gate)
**Desktop: own patch-set repo on top of ungoogled-chromium (Helium-style), not a from-scratch fork.**
1. Pin one Chromium version; use ungoogled-chromium patches + our `patches/` series (branding, MV2/extension retention, privacy presets, UI).
2. UI: Zen-style vertical tabs implemented as Chromium WebUI (HTML/TS) loaded in privileged pages (`chrome://`-style), minimal C++ glue. Avoid rewriting Views UI.
3. Privacy presets: one declarative JSON schema (shared with mobile) -> compiled into Chromium prefs/policies/feature flags + blocker config. Enforcement tests via a browser test harness.
4. Blocking: **use uBO as component extension + small MV2 patch** (Helium-proven on 155). uBO Lite = fallback. Keep filter lists updated independently (own update service or upstream list URLs).
5. Widevine: user-side install path + diagnostics page; no bundling.
6. Reuse Helium's packaging layout (Docker build, tarball) as reference; check GPL-3.0 compatibility before copying patches (our code would be GPL-3.0 too if we reuse).
7. Android: later, Chromium Android build + native blocker. iOS: later, WKWebView.

**Cheap de-risking before the big build (not done yet):** run a prebuilt ungoogled-chromium/Helium binary in a project-local dir and test what uBO/Widevine/presets behave like, plus write the preset schema + tests (pure code, no Chromium needed).

## Build cost (ESTIMATE — confirm)
Source tarball ~2-3 GB, extracted tree ~30 GB+, build output 50-100 GB, 8+ GB RAM (15 GB here: use `-j` limit, ThinLTO off). Clean build hours; incremental minutes. Android adds ~50 GB. Fits in workspace disk. Needs system build deps (clang/ninja/gn/nodejs etc.): Helium uses a Docker image — Docker/system packages would need your permission.

## Licensing notes
- Chromium BSD-3; ungoogled-chromium BSD-3; Helium GPL-3.0; uBO GPL-3.0 (bundling OK if we comply; branding/name caution); filter lists have per-list licences (EasyList CC BY-SA/GPL dual; attribute). Widevine proprietary — not redistributed.
- Project name still undecided (avoid "Zen", "Helium").

## Open questions / UNVERIFIED
1. (resolved) Helium MV2 mechanism: see above.
2. Current Chromium build docs figures (only older doc revisions seen).
3. Legality of user-triggered Widevine fetch.
4. iOS Japan/EU current status; Apple distribution rules.
5. adblock-rust licence/integration viability.

## Sources
- https://github.com/imputnet/helium , /helium-linux , /helium-chromium
- https://github.com/ungoogled-software/ungoogled-chromium
- https://alternativeto.net/news/2026/9/google-has-removed-manifest-v2-extensions-from-chrome-web-store-including-ublock-origin/
- https://www.neowin.net/amp/forget-google-chrome-brave-makes-new-official-bypass-to-support-ublock-origin-and-more/
- https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.embedded-web-browser-engine.md
- https://gigazine.net/gsc_news/en/20260618-blink-on-ios
- https://chromium.googlesource.com/chromium/src/+/main/docs/linux/build_instructions.md (older revisions seen only)

## Preset enforcement map (Phase 3 prep, 2026-10-19)
"Source" = seen in `research/helium-chromium` patches (VERIFIED present). "Chromium" = standard Chromium pref/content setting named from memory, NOT yet checked against 155 source (UNVERIFIED). Nothing here is tested.

| Setting | Mechanism | Status |
|---|---|---|
| blocker_level | uBO filter-list set + dynamic config, written by our preset code | PLANNED; needs uBO managed-storage/config route (UNVERIFIED) |
| malicious_domains | uBO malware lists (e.g. URLhaus-style). Helium builds with `safe_browsing_mode=0`, so Chromium Safe Browsing is absent | PLANNED; weaker than Safe Browsing, say so in UI |
| third_party_cookies | Chromium pref `profile.cookie_controls_mode` | Chromium, unverified |
| session_only_cookies | content setting `cookies` = session-only | Chromium, unverified |
| storage_partitioning | Chromium already partitions third-party storage by default; "default" vs "strict" may be identical | PARTIAL; likely no extra control |
| referrer | Source: `ungoogled-chromium/add-flags-for-referrer-customization.patch` (command-line flags, not prefs) | Source; needs pref wiring or per-profile flags |
| fingerprinting | Source: Helium `core/noise/canvas.patch`, `noise/audio.patch` (features `kHeliumNoiseCanvas`/audio), bromite client-rects + measureText switches, `add-flag-to-remove-client-hints` | Source; basic=canvas+audio, strong=+rects/measureText/client hints. No claim beyond these. |
| permissions | content-setting defaults (`profile.default_content_setting_values.*`) | Chromium, unverified |
| background_activity | pref `background_mode.enabled` + feature flags; `disable-mei-preload` in source | PARTIAL |
| prefetch_predictive | pref `net.network_prediction_options` | Chromium, unverified |
| webrtc_ip | pref `webrtc.ip_handling_policy`; Source: `helium/core/webrtc-default-handling-policy.patch` sets public-interface-only default | Source (default only); other values via pref |
| https_mode | Source: `helium/core/prefer-https-by-default.patch`; prefs `https_only_mode_enabled`, HTTPS-First | Source + Chromium |
| optional_telemetry | Build: `enable_reporting=false`, `safe_browsing_mode=0`, no Google keys (flags.gn); patches `disable-webrtc-log-uploader`, `crash-reporter-privacy-tweaks`, `disable-privacy-sandbox` | Source; verify by network capture later |
| (extra) Global Privacy Control | Source: `helium/core/network/global-privacy-control-pref.patch` adds `kHeliumGlobalPrivacyControl` pref | candidate new setting |

Gaps: noise features are Blink `FEATURE_VALUE_TYPE` flags, so presets must set them via command line / feature list at startup => **fingerprinting and referrer changes need a restart**, not immediate. Design: a `PresetApplier` browser component that writes prefs live and records "restart required" keys.

### Preset map verification against build/src (2026-10-20, Chromium 155.0.8059.84 + Helium patches)
Checked by grep in `build/src`; nothing runtime-tested.
- VERIFIED pref names exist: `profile.cookie_controls_mode` (components/content_settings/core/common/pref_names.h; enum kOff=0, kBlockThirdParty=1, kIncognitoOnly=2; kOff now behaves like kIncognitoOnly), `background_mode.enabled`, `net.network_prediction_options`, `webrtc.ip_handling_policy`, `https_only_mode_enabled`, `helium.global_privacy_control` (chrome/common/pref_names.h). `CONTENT_SETTING_SESSION_ONLY` exists.
- VERIFIED fingerprinting = Blink feature flags, not prefs: `kHeliumNoise`, `kHeliumNoiseCanvas`, `kHeliumNoiseAudio`, CPU-cores noise (chrome/browser/helium_flag_entries.h), plus bromite `fingerprinting-client-rects-noise` etc. (bromite_flag_entries.h). => restart needed, confirmed.
- VERIFIED referrer = feature flags `remove-referrers`, `remove-cross-origin-referrers` (`features::kNoReferrers`, ungoogled patch), not prefs => restart needed.
- Cookie "session only": content setting `cookies` default = SESSION_ONLY; per-pref wiring still to confirm at implementation time.
- STILL UNVERIFIED: uBO managed-storage route for blocker level; per-site exceptions; actual runtime effect of any item.
- Design consequence: PresetApplier writes prefs live and, for flag-type settings, writes the enabled feature list for next start and flags "restart required". Check how Helium persists `chrome://flags` selections (Local State `browser.enabled_labs_experiments`) before choosing the mechanism.

## Decision log: three privacy modes (2026-10-20, user decision, supersedes CLAUDE.md §9 and prompt.txt six-preset wording)
- Modes: **Prioritize usability**, **Medium privacy** (recommended, default), **Maximum privacy**. All include uBlock Origin. No separate ad-block-only mode.
- uBlock Origin stays at its defaults in every mode; we harden the browser itself (removed `blocker_level` from `shared/presets.json`). Malicious-site blocking relies on uBO's default lists (unverified which are enabled by default in Helium's bundled copy).
- Cookies: usability + medium keep cookies after closing; maximum is session-only (deleted on close). Interpreted "not store" as session-only, because blocking all cookies breaks most logins. Confirm with user.
- Mapping from old presets: usability = old Low, medium = old Medium, maximum = old Ultra. Old High dropped.
- The chooser UI must show what each mode does: `shared/presets.json` now has per-setting `label` + per-value `effects` text and per-mode `meta` (name, tagline, tradeoff); a test requires text for every value in use. Show honest caveats (restart needed, weaker than Safe Browsing, no anonymity promise).
- UI direction: Zen-inspired look (vertical tabs, rounded, compact), original assets/branding only. Not started.
- Test: `python3 -I -m unittest discover -s shared/tests` -> 9 tests OK.

### How flag choices are stored (read from build/src 2026-10-20; not runtime-tested)
- Chrome flags persist in Local State pref `browser.enabled_labs_experiments` (components/webui/flags/flags_ui_pref_names.cc). Entries use `name@N` (kMultiSeparator `@`); for feature entries N = 0 default, 1 enabled, last option = disabled (2 for plain features); CONFIRMED in components/webui/flags/feature_entry.cc StateForOption, runtime not tested. The test profile's Local State currently has no entry (all defaults).
- Defaults in this build: `kHeliumNoise`, `kHeliumNoiseCanvas`, `kHeliumNoiseAudio`, `kHeliumNoiseCpuCores` = ENABLED by default (third_party/blink/common/features.cc). `kNoReferrers` (chrome_features.cc) and `kRemoveClientHints`, `kSpoofWebGLInfo` = DISABLED by default. => stock Helium already gives "basic" canvas/audio/CPU-core noise. The old "fingerprinting: off" would mean actively disabling those; for usability mode prefer keeping Helium's default (basic) unless a site-breakage reason appears. "strong" = also enable bromite client-rects/measureText noise, remove-client-hints, referrer flags.
- Design: PresetApplier writes (a) normal prefs live, (b) `browser.enabled_labs_experiments` for flag-type settings and shows "restart required" if the value changed. Cheaper alternative if that proves fiddly: our own patch changing the feature defaults per mode at startup.
- Decision (user, 2026-10-20): usability mode keeps Helium's default fingerprinting level `basic` (presets.json updated; 9 tests OK).
