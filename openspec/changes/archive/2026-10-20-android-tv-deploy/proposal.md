# Proposal

## Why

Controls for Android TV (D-pad, gamepad, menu navigation, TV detection) already exist in `main.py`, but the APK is not yet installable or discoverable on a TV: the manifest has no leanback launcher entry, no banner, and does not declare that a touchscreen is optional. Without these the app is hidden from the TV launcher and Google Play filters it out of TV devices.

## What Changes

- Add the `LEANBACK_LAUNCHER` intent filter so the game shows up in the Android TV launcher (alongside the existing phone launcher entry).
- Declare `android.hardware.touchscreen`, `android.software.leanback` and `android.hardware.gamepad` as `required="false"` so one build serves phones, tablets and TVs.
- Add a 320x180 px TV banner and reference it as `android:banner` on the application.
- Wire the above into `buildozer.spec` via small manifest snippet files in a new `android/` directory.
- Add a short TV test/verification checklist (emulator + real device) and Play Console release notes to the README, and tick off the finished README TODO items.
- Fix remaining TV-specific gaps found during emulator testing (D-pad centre keycode, HUD/object sizing at 1080p/4K) if they show up.

## Capabilities

### New Capabilities
- `android-tv-packaging`: How the Android build identifies itself to Android TV and Google Play (launcher entry, banner, optional hardware features) so the same package installs and launches on TVs and phones.

### Modified Capabilities

## Impact

- `buildozer.spec`: `android.extra_manifest_xml`, `android.extra_manifest_application_arguments`, `android.manifest.intent_filters`, `android.add_resources`.
- New files: `android/extra_manifest.xml`, `android/application_args.xml`, `android/intent_filters.xml`, `android/res/drawable/banner.png`; `source.include_exts`/patterns must not need changes (resources are not app source).
- `README.md`: Android TV checklist and build/test instructions.
- `main.py`: only if emulator testing reveals input/layout bugs.
- Out of scope: Play Console upload itself, signing keys, TV screenshots capture, gamepad remapping, new gameplay features, AAB/APK pipeline changes, CI.
