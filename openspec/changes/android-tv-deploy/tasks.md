## 1. Manifest snippets

- [x] 1.1 Create `android/extra_manifest.xml` with `uses-feature` for `android.hardware.touchscreen`, `android.software.leanback` and `android.hardware.gamepad`, all `android:required="false"`
- [x] 1.2 Create `android/intent_filters.xml` with a `MAIN` + `LEANBACK_LAUNCHER` + `DEFAULT` intent filter
- [x] 1.3 Create `android/application_args.xml` with `android:banner="@drawable/banner"`

## 2. Banner asset

- [x] 2.1 Produce `android/res/drawable/banner.png` at 320x180 px (game name over existing nebula/ship artwork)

## 3. Buildozer wiring

- [x] 3.1 Set `android.extra_manifest_xml`, `android.extra_manifest_application_arguments`, `android.manifest.intent_filters` and `android.add_resources` in `buildozer.spec`
- [ ] 3.2 Build a debug APK and inspect the generated `AndroidManifest.xml` and `aapt dump badging` output for the leanback launcher, banner and optional features
- [x] 3.3 Confirm `source.include_exts`/patterns do not package the `android/` directory

## 4. Verification on TV

- [ ] 4.1 Install on the Android Studio "Android TV (1080p)" emulator; confirm the tile and banner in the launcher
- [ ] 4.2 Play through start, steer, thrust, fire, back to menu using only the remote D-pad; fix keycode mapping in `main.py` if the centre button does not fire
- [ ] 4.3 Check HUD and object sizes on 1080p and 4K emulator profiles; fix in `main.py`/`spacepilgrim.kv` if needed
- [ ] 4.4 Install on a phone and confirm the regular launcher entry and touch buttons are unchanged
- [ ] 4.5 If available, test on a real TV device (Chromecast with Google TV / Nvidia Shield) with remote and gamepad

## 5. Docs

- [x] 5.1 Update the README Android TV checklist (tick completed items) and add emulator test + Play Console TV opt-in notes
- [x] 5.2 Run `pytest` to confirm existing tests still pass
