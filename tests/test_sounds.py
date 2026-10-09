"""Guards against the sound assets being lost, corrupted or re-encoded."""
import hashlib
from pathlib import Path

import pytest

from kivy.core.audio import SoundLoader

SOUNDS = Path(__file__).resolve().parent.parent / "sounds"

# name: (sha256, expected length in seconds)
EXPECTED = {
    "engine.ogg": ("e3510e403f5b71e0a7a59cf041c0ae5e0a81c184bc89a7af2973e29a2a3c2ecf", 13.07),
    "explosion.ogg": ("7153c9aae7adaf8b914321bd4876f7f293d12c097f359c8d248b071f1108c685", 1.10),
    "gun.ogg": ("e7cca526470e15be1ad354601dcd7fe80e057b8694c278969ba511fac2614e3a", 0.83),
}


def test_all_sound_files_present():
    assert {p.name for p in SOUNDS.glob("*.ogg")} == set(EXPECTED)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_sound_file_unchanged(name):
    digest = hashlib.sha256((SOUNDS / name).read_bytes()).hexdigest()
    assert digest == EXPECTED[name][0]


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_ogg_container_is_valid_vorbis(name):
    data = (SOUNDS / name).read_bytes()
    assert data[:4] == b"OggS"
    assert b"\x01vorbis" in data[:100]  # Vorbis identification header
    assert len(data) > 1000


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_sound_decodes_with_expected_length(name):
    sound = SoundLoader.load(str(SOUNDS / name))
    assert sound is not None, "no audio provider could decode %s" % name
    assert sound.length == pytest.approx(EXPECTED[name][1], abs=0.02)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_sound_play_stop(name):
    sound = SoundLoader.load(str(SOUNDS / name))
    sound.play()
    sound.stop()
