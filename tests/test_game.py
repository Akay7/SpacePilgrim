import pytest

import main
from main import Asteroid, Shot, Spaceship, SpacePilgrimGame


def test_sounds_loaded_at_import():
    # SoundLoader.load returns None when decoding fails; every class that
    # plays a sound would then crash on first use.
    assert main.Explosion.sound is not None
    assert main.Shot.sound is not None
    assert main.Spaceship.sound is not None


def test_thrust_accelerates_and_drag_slows():
    ship = Spaceship()
    ship.thrust_on()
    ship.update(0)
    assert ship.speed == 3
    ship.thrust_off()
    ship.update(0)
    assert ship.speed == pytest.approx(3 * 0.98)


def test_rotation_controls():
    ship = Spaceship()
    ship.turn_left()
    ship.update(0)
    assert ship.angle == 3
    ship.turn_right()
    ship.update(0)
    assert ship.angle == 0
    ship.stop_rotation()
    assert ship.angle_rotation == 0


def test_asteroid_moves_along_angle():
    asteroid = Asteroid(speed=5, angle=90)
    asteroid.pos = (100, 100)
    asteroid.update(0)
    assert asteroid.pos[0] == pytest.approx(100)
    assert asteroid.pos[1] == pytest.approx(105)


def test_shot_moves_along_angle():
    shot = Shot(speed=4, angle=0)
    shot.pos = (10, 10)
    shot.update(0)
    assert shot.pos == [14, 10]


@pytest.fixture
def game():
    g = SpacePilgrimGame()
    g.game_stop()
    g.game_start()
    yield g
    g.frame_schedule.cancel()
    g.asteroid_schedule.cancel()


def test_game_start_adds_spaceship(game):
    assert len(game.spaceships) == 1
    assert game.splash not in game.children


def test_shoot_adds_shot(game):
    game.spaceships[0].shot()
    assert len(game.shots) == 1


def test_shot_destroys_asteroid_and_scores(game):
    ship = game.spaceships[0]
    ship.shot()
    shot = game.shots[0]
    # move the ship away so only the shot touches the asteroid
    ship.pos = (shot.x + 500, shot.y + 500)
    asteroid = Asteroid()
    asteroid.pos = shot.pos
    game.add_widget(asteroid)
    game.asteroids.append(asteroid)

    game.update(0)

    assert asteroid not in game.asteroids
    assert shot not in game.shots
    assert ship.points == 1
    assert len(game.explosions) == 1


def test_asteroid_hit_costs_life_then_game_over(game):
    ship = game.spaceships[0]
    for expected in (2, 1, 0):
        asteroid = Asteroid()
        asteroid.pos = ship.pos
        game.add_widget(asteroid)
        game.asteroids.append(asteroid)
        game.update(0)
        assert ship.lives == expected

    assert game.spaceships == []
    assert game.splash in game.children
