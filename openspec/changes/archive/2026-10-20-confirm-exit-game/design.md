# Design

## Context

The pause screen (`PauseScreen`, a `ButtonColumn`) is added to the root widget by `pause()`. While `paused`, `_input` routes up/down/fire/back to it; "Main menu" calls `game_stop()`, which runs `end_game()` and `show_menu()`. Escape is swallowed in `_on_keyboard` so Kivy does not quit. See proposal.md for the motivation.

## Goals / Non-Goals

**Goals:**
- A confirm step between "Main menu" on the pause screen and `game_stop()`.
- Same input handling as other screens (touch, keyboard, gamepad).

**Non-Goals:**
- Confirmation on the results screen.

## Decisions

- **A `ConfirmScreen` (`ButtonColumn`) shown in place of the pause screen**, not a Kivy `Popup`. Every other screen is a `ButtonColumn` added to the root and driven by `_input`, so keyboard and gamepad navigation, highlighting and the dimmed backdrop come for free; a Kivy `Popup` would need its own key and focus handling. Alternative rejected: stacking the popup over the pause screen — then both would take presses.
- **Opening it removes the pause screen widget; closing it creates a new `PauseScreen`.** The world stays frozen because `paused` stays true; only `self.pause_screen` is swapped, so `_input` needs one new branch: if a confirm screen is active, route up/down/fire to it and `back` to "No". `end_game()` and `resume()` must also remove the confirm screen if present.
- **Default selection "No"**, so a stray fire press cannot lose the game. "Yes" calls `game_stop()`.
- **Escape on the popup is "No"**, not "Continue": the user asked to stay where they were (paused); resuming is a separate choice on the pause screen.

- **One `ConfirmScreen(kind)` serves both questions**: 'leave' (game to menu) and 'exit' (quit app). Opening it from the main menu swaps the menu out; "No" calls `show_menu()`. Input routing checks for the popup before anything else, and it counts as a non-game screen so the ship controls ignore it.

## Risks / Trade-offs

- [Held keys or touches when swapping screens leave a ship thrusting] → pause already clears held inputs; the swap does not change the input state, and ignoring releases while paused is unchanged.
- [Android Back key reaching Kivy while the popup is shown] → `_on_keyboard` already swallows Escape/Back during play; verify it also covers the popup.
