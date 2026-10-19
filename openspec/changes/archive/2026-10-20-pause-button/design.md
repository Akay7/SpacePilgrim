# Design

## Context

The game loop is `SpacePilgrimGame.update` on a 60 Hz `Clock.schedule_interval`, with asteroids spawned by a second interval. Explosions animate through a Kivy `Animation`; the engine sound is a looping `SoundLoader` sound. Menus (`Menu`, `ResultsScreen`) are `ButtonColumn` widgets added over the game and routed in `_input` by `*_active` properties. The touch "Menu" button is `MenuButton` inside `SpaceshipStatus`, calling `game_stop()`.

## Goals / Non-Goals

**Goals:**
- Pause and resume without losing any state; one pause screen for all players.

**Non-Goals:**
- Pausing automatically when the app goes to the background (Android's `on_pause` already stops the app).
- A pause button for keyboard/gamepad players (they pause with Back/Escape / Start).

## Decisions

- **Pause = cancel the two schedules, set a `paused` flag.** `update` and `generate_asteroid` simply stop being called, so nothing else needs a "paused" check; resume re-schedules them. Alternative (an `if paused: return` in `update`) leaves the spawn timer and is easy to forget in new code.
- **Explosions:** stop their `Animation`s on pause and restart from the current frame on resume (`Animation(frame=22, duration=0.6 * remaining)`), so they do not finish while frozen. Alternative: let them finish; rejected because it visibly changes the "frozen world".
- **Sounds:** stop the engine sound of each ship on pause and play again on resume if the ship was thrusting. One-shot sounds are short and left alone.
- **Inputs:** while paused, `_input` routes to the pause screen like the other menus (up/down/fire/back) and never reaches `ControlsManager`. On pause, release every held action and cancel the touch sticks (`show_touch_buttons` toggling already lets go of them) so nothing is stuck on resume.
- **Pause screen:** a `ButtonColumn` subclass `PauseScreen` (Continue, Main menu) centred over the world, with a translucent dark backdrop so the frozen world and status blocks stay visible; the status blocks are drawn above the backdrop, not hidden. Mirrors the pattern of `ResultsScreen`.
- **Button:** rename `MenuButton` to `PauseButton` (label "Pause"), `on_press` calls `game.pause()`. Styling stays as in the kv rule: transparent background and rounded blue outline.
- **Back key:** during play, Back/Escape/Start routes to `pause()` instead of `game_stop()`; on Android the Back key is still consumed so the app itself is not paused.
- **Leaving:** "Main menu" calls the existing `game_stop()` (which does not record results or open the results screen).

## Risks / Trade-offs

- [Explosion animation restart drifts slightly] → compute the remaining duration from the current frame.
- [A held key released while paused is missed] → clear `_inputs_down` and held actions on pause, and ignore key-ups of unknown keys (already the case).
- [Pause screen hides part of the field on small phones] → keep it compact and use a semi-transparent backdrop.
