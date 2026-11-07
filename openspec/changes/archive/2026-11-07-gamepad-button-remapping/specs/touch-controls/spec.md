# Spec Delta

## MODIFIED Requirements

### Requirement: Joystick directions
Dragging the knob SHALL activate the thrust, turn-left and turn-right actions: up gives thrust, left turns left, right turns right, and a position between up and left or right SHALL activate both actions at once. Thrust power SHALL grow with how far up the knob is, from none near the centre to full at the edge. Dragging down or leaving the knob near the centre SHALL activate nothing. The fire button SHALL work independently, so the joystick and fire can be used with two fingers at once.

#### Scenario: Pure directions
- **WHEN** the player drags the knob straight up, then straight left
- **THEN** the ship thrusts, and then turns left without thrusting

#### Scenario: Between positions
- **WHEN** the player drags the knob to the upper-left
- **THEN** the ship thrusts and turns left at the same time

#### Scenario: Thrust power follows the knob
- **WHEN** the player drags the knob half way up, then all the way up
- **THEN** the ship thrusts at about half power, then at full power

#### Scenario: Release
- **WHEN** the player lifts the finger from the joystick
- **THEN** thrust and turning stop

#### Scenario: Steer and fire
- **WHEN** the player holds the knob to the left and presses the fire button
- **THEN** the ship keeps turning left while a shot is fired
