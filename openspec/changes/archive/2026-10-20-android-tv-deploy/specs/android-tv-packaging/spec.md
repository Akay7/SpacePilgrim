# Spec Delta

## Purpose

Makes the Android build discoverable and installable on Android TV devices while keeping phones and tablets supported by the same package.

## ADDED Requirements

### Requirement: TV launcher entry
The built manifest SHALL declare an intent filter with action `android.intent.action.MAIN` and category `android.intent.category.LEANBACK_LAUNCHER` on the main activity, in addition to the existing `LAUNCHER` entry.

#### Scenario: App appears on TV home screen
- **WHEN** the APK is installed on an Android TV (e.g. the "Android TV (1080p)" emulator)
- **THEN** Space Pilgrim is listed in the TV launcher and starts the game when selected

#### Scenario: Phone launcher still works
- **WHEN** the APK is installed on a phone
- **THEN** the app still appears in the regular app drawer

### Requirement: Optional hardware features
The manifest SHALL declare `android.hardware.touchscreen`, `android.software.leanback` and `android.hardware.gamepad` as `uses-feature` with `android:required="false"`.

#### Scenario: Installable on device without touchscreen
- **WHEN** the package is checked against a device lacking a touchscreen
- **THEN** Google Play and the package installer do not reject it for a missing touchscreen

### Requirement: TV banner
The application SHALL reference a 320x180 px banner image through `android:banner` so the launcher shows a proper tile.

#### Scenario: Banner shown in launcher
- **WHEN** the app is listed on the TV home screen
- **THEN** its tile shows the banner image rather than a scaled-up icon

### Requirement: Playable without touch
The game SHALL be fully playable on Android TV with only a D-pad remote or gamepad: starting a game, steering, thrusting, firing, pausing/returning to the menu and leaving the game.

#### Scenario: Remote-only session
- **WHEN** a player uses only the TV remote D-pad and centre button
- **THEN** they can start a game from the menu, play, die, and return to the menu without touching the screen
