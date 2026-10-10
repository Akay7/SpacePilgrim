## Context

The game is a Kivy app built with Buildozer 1.6.0 / python-for-android (api 36, minapi 21, SDL2 bootstrap). TV input handling (D-pad, gamepad, `is_android_tv()`, touch buttons hidden on TV, menu navigation) is already in `main.py`. What is missing is purely packaging: manifest entries and the banner. Inspected p4a's generated `AndroidManifest.tmpl.xml`: it emits only a `MAIN`/`LAUNCHER` filter, no `uses-feature` for `--feature` args, and has hook points for extra manifest XML, extra application attributes and extra intent filters.

## Goals / Non-Goals

**Goals:**
- One APK/AAB that works on phones, tablets and Android TV.
- Manifest changes driven entirely from `buildozer.spec` and checked-in snippet files (no hand-edited `.buildozer/` templates).

**Non-Goals:**
- Separate TV-only build flavor or package id.
- Play Console submission, signing, screenshots.
- New gameplay or remapping features.

## Decisions

- **`android.extra_manifest_xml`** for `uses-feature` tags. Rationale: this p4a template version ignores `android.features`, so the dedicated `--feature` option would silently do nothing; the extra-XML hook is injected directly inside `<manifest>` and supports `android:required="false"`.
- **`android.manifest.intent_filters`** for the leanback filter. It is appended inside the activity after the default launcher filter, so phones keep their entry. A separate `<intent-filter>` is required (not a second category in the existing one) per Android TV docs.
- **`android.extra_manifest_application_arguments`** containing `android:banner="@drawable/banner"`.
- **`android.add_resources = android/res/drawable:drawable`** to ship `banner.png` into `res/drawable`. Banner is 320x180, generated from existing artwork (`images/splash.png` / nebula + title), checked in as a PNG; no text localisation needed beyond the game name.
- Snippet files live in `android/` (outside `source.include_exts`, so not packaged as Python assets).
- Keep `orientation = landscape,landscape-reverse` (already TV-compatible; TVs are landscape only).

## Risks / Trade-offs

- [D-pad centre keycode unverified on real hardware] -> check on emulator and a real device; add keycode to fire mapping if it differs.
- [`android.hardware.touchscreen` implied by permissions] -> project requests no touch-implying permissions; verify with `aapt dump badging` that no `uses-feature` is implicitly required.
- [Extra-manifest injection syntax is order sensitive] -> verify the generated manifest in `.buildozer/.../dists/spacepilgrim/src/main/AndroidManifest.xml` after a build.
- [Google Play TV review requirements (e.g. leanback-only UI quality, 1080p screenshots)] -> handled in Play Console outside the code; documented in README.
- [HUD sizes at 4K] -> emulator pass; adjust only if sizes are wrong.
