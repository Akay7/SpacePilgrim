# Proposal

## Why

Space Pilgrim is about to be published on Google Play for phones, tablets and Android TV, and the store listing needs screenshots for each of those form factors plus the Android TV listing banner (1280x720, required to publish a TV-enabled app). Taking them by hand on emulators is slow and has to be redone after every visual change (multiplayer, touch controls and cabin colours have all changed the look recently), so the images should come from a script that anyone can rerun.

## What Changes

- Add a script that renders the store listing images straight from the game code, with no manual steps: it starts the real game widgets at each target size and density, sets up fixed scenes (menu, ship selection, join screen, single-player and multiplayer gameplay) and saves the images.
- Produce screenshot sets for **phone**, **7-inch tablet**, **10-inch tablet** and **Android TV**, landscape 16:9 at or above 1920x1080, as 24-bit PNG without alpha, so they meet the Play Console limits and the screenshot recommendation rules for games.
- Phone and tablet shots show the on-screen touch controls (and two touch players at the sides in multiplayer); TV shots show remote/gamepad play with no touch controls.
- Produce the **Android TV listing banner** (1280x720) in the style of the existing 320x180 launcher banner.
- Check the generated files (size, aspect, alpha, count per form factor) at the end of every run, so a broken image fails the run instead of failing the Play upload.
- Keep the generated images out of git (`store/play/` is ignored; the script is the source of truth and regenerates them in seconds) and exclude them, and the script, from the APK.
- Document how to regenerate the images in the README and point the Android TV checklist item about TV screenshots to them.
- Fix two game issues the screenshots revealed: on phones and tablets a touch player's lives/points overlap their own joystick and FIRE button in multiplayer, and the join screen shows "Tap to join by touch" strips on Android TV, which has no touchscreen.

## Capabilities

### New Capabilities
- `store-listing-assets`: The Google Play listing images of the game (screenshots per form factor and the Android TV listing banner): which images exist, the rules they must meet, and how they are regenerated from the game.

### Modified Capabilities
- `local-multiplayer`: a touch player's status block sits next to their controls instead of overlapping them; the touch join strips are shown only on devices with a touchscreen or after a touch.

## Impact

- New script `tools/play_listing.py` and scene module `tools/listing_scenes.py` (desktop Kivy, run with the project venv); output folder `store/play/` with `phone/`, `tablet-7/`, `tablet-10/`, `tv/` and `tv-banner.png`, listed in `.gitignore`.
- `buildozer.spec`: `source.exclude_dirs` gains `tools` and `store`, so neither the script nor the megabytes of PNGs end up in the APK.
- `main.py` / `spacepilgrim.kv`: touch players' status position follows their touch controls; touchscreen detection (Android feature check, first touch) decides whether the join screen shows its touch strips. Otherwise the script drives existing widgets (`SpacePilgrimGame`, `JoinScreen`, `ShipSelectScreen`, `Asteroid`, `Shot`, `Explosion`).
- `tests/`: tests for the listing rules, the alpha-free PNG output, the scene builders, the status/controls layout and the touch strips; `tests/conftest.py` uses a hidden Kivy window (a visible one blocks while the desktop session is locked).
- `README.md`: how to regenerate the listing images.
- Needs a desktop with a display (as for the existing manual screenshots); headless CI rendering, device frames, captions/marketing text, the feature graphic (1024x500), Chromebook screenshots, localised screenshots and the Play Console upload itself are out of scope.
