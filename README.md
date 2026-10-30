<h1 align="center">Helium++</h1>

<p align="center">
  A privacy-first, Zen-inspired desktop browser built on <a href="https://github.com/imputnet/helium">Helium</a> (ungoogled-chromium).
</p>

<p align="center">
  <img alt="License: GPL-3.0" src="https://img.shields.io/badge/license-GPL--3.0-blue">
  <img alt="Chromium 155.0.8059.84" src="https://img.shields.io/badge/chromium-155.0.8059.84-4285F4">
  <img alt="Platform: Linux | Windows" src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey">
  <img alt="Status: early development" src="https://img.shields.io/badge/status-early%20development-orange">
</p>

> **Early development.** Linux and Windows (x64) builds exist. The Windows build is brand new: please try it and [report problems](https://github.com/someonevro/heliumpp/issues). Many features are implemented but not yet verified in a real window; see [Status](#status) for what has actually been tested.

## Download

Latest release: **[Helium++ 0.20.2.2 alpha](https://github.com/someonevro/heliumpp/releases/tag/v0.20.2.2-alpha)** (Windows installer: still 0.19.4.7 until the 0.20.2.2 build finishes)

| Platform | Download |
| --- | --- |
| **Windows** 10/11 x64 | [heliumpp_0.19.4.7_x64-installer.exe](https://github.com/someonevro/heliumpp/releases/download/v0.19.4.7-alpha/heliumpp_0.19.4.7_x64-installer.exe) |
| **Linux** x86_64 | [heliumpp-0.20.2.2-x86_64.AppImage](https://github.com/someonevro/heliumpp/releases/download/v0.20.2.2-alpha/heliumpp-0.20.2.2-x86_64.AppImage) |

**Windows:** run the installer. It installs for your user only, into `%LOCALAPPDATA%\heliumpp`, and keeps its data apart from Helium. Windows SmartScreen shows a warning because the installer does not have a paid code-signing certificate yet (this says nothing about the file being unsafe): click **More info**, then **Run anyway**. It does not update itself yet; download new versions from this page. This is the first Windows release, so if something does not work, please [open an issue](https://github.com/someonevro/heliumpp/issues).

**Linux:**

```bash
chmod +x heliumpp-0.20.2.2-x86_64.AppImage
./heliumpp-0.20.2.2-x86_64.AppImage
```

> **Data warning for 0.19.4.1 (withdrawn).** Version 0.19.4.1 used real Helium's profile folder (`~/.config/net.imput.helium`). If you also use Helium, it could change Helium's settings: the "High" privacy mode makes cookies and site data get deleted whenever the browser closes, and that setting stays in Helium. From 0.19.4.2 on, Helium++ uses its own folder (`~/.config/heliumpp`) and never touches Helium's data. If you ran 0.19.4.1 next to Helium: back up `~/.config/net.imput.helium`, then in Helium check Settings > Privacy and security > Site settings > Additional content settings > On-device site data, third-party cookies, site permissions and the theme.

On Linux it has been tested headless and on the developer's desktop; other distros are unverified. From 0.19.4.5 on, the Linux AppImage updates itself from GitHub releases (tested with local and GitHub test servers, not yet as a real AppImage replacing itself on a desktop). If you have 0.19.4.4 or older, download 0.19.4.5 by hand once.

## Vibecoded

This browser is vibecoded: the patches, scripts and documentation were written with an AI coding assistant (Claude Code), directed by a beginner in browser development. It has not had an independent security review or audit. Do not rely on it for anything where your safety depends on it, and read the [status table](#status) to see what has actually been tested.

## What this repository is

This repository does **not** contain the Chromium source tree. It holds the Helium++ changes on top of Helium:

| Path | Contents |
| --- | --- |
| `patches/` | Ordered patch series (`patches/series`) applied to the Helium/Chromium tree |
| `scripts/` | Build, run, packaging, signing and test scripts |
| `shared/` | Shared privacy-preset definitions and tests |
| `designs/` | Design mocks and snapshots of earlier states |
| `*.md` | Product notes, architecture, status and TODO |

## Features

- **Three privacy modes** chosen at first launch, changeable later: Low, Medium (recommended) and High.
- **Zen-inspired interface:** vertical tab sidebar, essentials tiles, folders, workspaces, floating page card.
- **Wallpaper-driven theme:** the UI color follows your desktop wallpaper or accent color.
- **New tab page:** your own wallpaper, softened, behind a clock, a search field, shortcuts, and small chips for time on the web, focus rounds and sleeping tabs. Privacy level and Performance mode live in Settings and the sidebar shield.
- **Performance mode:** aggressive tab discarding, energy saver, reduced animations, wallpaper colour sync paused. Also in Settings > Appearance.
- **Isolated tabs** (`Ctrl+Alt+N`): per-tab throwaway in-memory storage, no history or session traces, permissions denied by default. This is **not** a VM and does not hide your IP, DNS or fingerprint.
- **Secure DNS choice** at first run: Cloudflare, Google, system, or custom DoH.
- **Built-in ad blocking** inherited from Helium.
- **Signed AppImage updater** for Linux (Ed25519-verified manifest, SHA-256 checked download); checks GitHub 5 minutes after start and then daily, and installs updates for the next launch).

## Status

Honest summary of what has been demonstrated, not just coded:

| Area | State |
| --- | --- |
| Linux build (Chromium 156.0.8078.73) | Builds and runs; `helium --version` prints `Helium++ 0.20.2.2 (Chromium 156.0.8078.73)` |
| Windows x64 build | Compiles and packages on GitHub Actions (`.github/workflows/windows.yml`); installer not code-signed yet; first release, feedback welcome |
| Privacy modes, performance mode | Automated tests pass (`scripts/test_privacy_mode.sh`, `scripts/test_performance_mode.sh`) |
| Isolated tabs | Cookie isolation, popups, permissions, disk traces and wipe-on-close tested headlessly. Downloads blocked and kept off disk (tested); password manager off (not tested); clipboard writes are **not** blocked |
| Secure DNS onboarding | Implemented; page not yet seen and DoH use not observed |
| macOS, Android, iOS | **Not started** |
| DRM (Widevine) | **Not tested** |

Much of the new UI has only been checked in headless or virtual-display screenshots. Details are in [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

## Building and running (Linux)

Requires Docker and a Helium/Chromium source checkout in `build/src` (not included here; see [`PROJECT_STATUS.md`](PROJECT_STATUS.md) and `ARCHITECTURE.md` for setup notes). A full Chromium build needs a lot of disk space, RAM and time.

```bash
# Build (Docker, incremental builds take minutes, a full build hours)
scripts/compile.sh

# Run with a profile name (the profile name comes FIRST)
scripts/run.sh myprofile

# Print the version
build/src/out/Default/helium --version

# Package an AppImage
scripts/package_appimage.sh
```

## Documentation

- [`ARCHITECTURE.md`](ARCHITECTURE.md): decisions, alternatives and sources
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md): current state and next steps
- [`PLATFORM_SUPPORT.md`](PLATFORM_SUPPORT.md): per-platform compatibility

## Security

Helium++ keeps Chromium's sandbox, certificate validation and security updates intact. It does not protect against a compromised operating system, phishing, malicious downloads or advanced fingerprinting. Privacy modes reduce tracking; they do not make you anonymous.

## License

[GPL-3.0](LICENSE). Built on Helium (GPL-3.0), ungoogled-chromium (BSD-3-Clause) and Chromium; see [`NOTICE.md`](NOTICE.md).
