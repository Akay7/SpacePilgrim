# Spec Delta

## Purpose

Keeps the Google Play listing images of Space Pilgrim (screenshots for phone, tablets and Android TV, and the Android TV listing banner) valid for upload and reproducible from the game with a single command.

## ADDED Requirements

### Requirement: One command regenerates all listing images
The project SHALL provide one command that produces every Google Play listing image from the current game code without manual steps (no emulator, device or hand-taken screenshot). Running it again SHALL replace the previous images with the same scenes. It SHALL be possible to regenerate a single form factor on its own.

#### Scenario: Full regeneration
- **WHEN** a developer runs the listing command on a desktop with a display
- **THEN** the phone, 7-inch tablet, 10-inch tablet and Android TV screenshots and the Android TV banner are written to the listing folder, replacing the previous ones

#### Scenario: Only one form factor
- **WHEN** the developer runs the command for the TV form factor only
- **THEN** only the TV screenshots are rewritten and the other images are unchanged

#### Scenario: Reflects the current game
- **WHEN** the look of the game changes (for example a new cabin colour or a changed HUD) and the command is run
- **THEN** the new screenshots show the changed look

### Requirement: Screenshot sets per form factor
The listing SHALL contain a screenshot set for phone, 7-inch tablet, 10-inch tablet and Android TV, each with at least 4 and at most 8 screenshots, named so that they sort in the intended listing order.

#### Scenario: Sets present
- **WHEN** the listing command has finished
- **THEN** each of the four form factors has between 4 and 8 screenshots in its own folder, numbered in listing order

### Requirement: Google Play image rules
Every screenshot SHALL be a 24-bit PNG without an alpha channel, in landscape 16:9, at least 1920x1080 and at most 3840 pixels on its long side. The Android TV banner SHALL be a 24-bit PNG without alpha of exactly 1280x720 pixels.

#### Scenario: Valid screenshot
- **WHEN** any generated screenshot is inspected
- **THEN** it has no alpha channel, a 16:9 landscape size between 1920x1080 and 3840x2160, and a PNG colour depth of 24 bits

#### Scenario: Valid TV banner
- **WHEN** the generated Android TV banner is inspected
- **THEN** it is a 1280x720 PNG without alpha

### Requirement: Generated images are checked
The listing command SHALL check every image it wrote against the image rules and the per-form-factor counts, SHALL report each violation with the file name, and SHALL exit with a failure status if any image breaks a rule.

#### Scenario: Rule broken
- **WHEN** a generated screenshot has an alpha channel or a wrong size
- **THEN** the command names that file and the broken rule and exits with a failure status

#### Scenario: All rules met
- **WHEN** every image meets the rules
- **THEN** the command reports the number of images per form factor and exits successfully

### Requirement: Scenes shown
Each screenshot set SHALL show the game's own screens rendered at that form factor's size and density: single-player gameplay, multiplayer gameplay, the multiplayer join screen, the ship selection and the main menu. The first screenshot of each set SHALL be single-player gameplay.

#### Scenario: Gameplay first
- **WHEN** the screenshots of any form factor are listed in order
- **THEN** the first one shows the ship firing at asteroids with the lives/points HUD

#### Scenario: Multiplayer shown
- **WHEN** the multiplayer screenshots are viewed
- **THEN** the gameplay shows at least two ships in different cabin colours and the join screen shows several joined players

### Requirement: Fixed composition
Scenes SHALL be set up the same way on every run, so that two runs without code changes give the same composition.

#### Scenario: Same composition on rerun
- **WHEN** the command is run twice without code changes
- **THEN** each screenshot shows the same ships, asteroids, shots and screens in the same places both times

### Requirement: Controls match the form factor
Phone and tablet screenshots SHALL show the on-screen touch controls during gameplay, and their multiplayer gameplay SHALL show two touch players with their controls at the left and right sides. Android TV screenshots SHALL show no touch controls, and their multiplayer scenes SHALL show keyboard or gamepad players only.

#### Scenario: Phone gameplay
- **WHEN** the phone single-player gameplay screenshot is viewed
- **THEN** the joystick and the FIRE button are visible

#### Scenario: TV gameplay
- **WHEN** any Android TV screenshot is viewed
- **THEN** no joystick or FIRE button is shown, and the join screen shows keyboard or gamepad players

### Requirement: Android TV listing banner
The listing SHALL include a 1280x720 Android TV banner that shows the game name "Space Pilgrim" over the game's space background with the ship, matching the style of the 320x180 launcher banner shipped in the app.

#### Scenario: Banner content
- **WHEN** the TV banner is viewed
- **THEN** it shows the title "Space Pilgrim", the ship and the nebula background, readable at TV distance

### Requirement: Listing images are not packaged
The listing images and the tooling that generates them SHALL NOT be included in the Android package.

#### Scenario: APK contents
- **WHEN** a debug APK is built after generating the listing images
- **THEN** the APK contains none of the listing images or the generation script
