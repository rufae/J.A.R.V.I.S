from __future__ import annotations

import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class MediaActions:
    def __init__(self, music_dir: Path) -> None:
        self._music_dir = music_dir
        self._initialized = False
        self._paused = False
        self._current_track: Path | None = None

        try:
            import pygame

            pygame.mixer.init()
            self._pygame = pygame
            self._initialized = True
        except Exception:
            self._pygame = None
            LOGGER.warning("pygame is not available, media controls will be no-op")

    def play(self) -> tuple[bool, str]:
        if not self._initialized:
            return False, "Media engine is not available."

        if self._paused:
            self._pygame.mixer.music.unpause()
            self._paused = False
            return True, "Resuming music."

        track = self._pick_track()
        if track is None:
            return False, "No music files found in audio_assets/music."

        self._pygame.mixer.music.load(str(track))
        self._pygame.mixer.music.play()
        self._current_track = track
        return True, f"Playing {track.name}."

    def pause(self) -> tuple[bool, str]:
        if not self._initialized:
            return False, "Media engine is not available."

        if self._pygame.mixer.music.get_busy():
            self._pygame.mixer.music.pause()
            self._paused = True
            return True, "Music paused."

        return False, "There is no active music playback."

    def stop(self) -> tuple[bool, str]:
        if not self._initialized:
            return False, "Media engine is not available."

        self._pygame.mixer.music.stop()
        self._paused = False
        return True, "Music stopped."

    def _pick_track(self) -> Path | None:
        if not self._music_dir.exists():
            return None
        tracks = sorted(
            [
                path
                for path in self._music_dir.iterdir()
                if path.suffix.lower() in {".mp3", ".wav", ".ogg"}
            ]
        )
        return tracks[0] if tracks else None
