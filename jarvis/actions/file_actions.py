from __future__ import annotations

import fnmatch
import logging
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class FileActions:
    def __init__(self, allowed_roots: list[Path]) -> None:
        self._allowed_roots = [root.expanduser().resolve() for root in allowed_roots]

    def list_directory(self, raw_path: str) -> tuple[bool, str, list[str]]:
        try:
            path = self._resolve_allowed_path(raw_path)
        except ValueError as exc:
            return False, str(exc), []

        if not path.exists() or not path.is_dir():
            return False, f"Directory not found: {path}", []

        entries = sorted(item.name for item in path.iterdir())
        preview = ", ".join(entries[:10]) if entries else "empty"
        return True, f"Directory contents for {path}: {preview}", entries

    def read_text_file(self, raw_path: str, max_chars: int = 6000) -> tuple[bool, str, str]:
        try:
            path = self._resolve_allowed_path(raw_path)
        except ValueError as exc:
            return False, str(exc), ""

        if not path.exists() or not path.is_file():
            return False, f"File not found: {path}", ""

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return False, f"File is not valid UTF-8 text: {path}", ""
        except Exception:
            LOGGER.exception("Failed to read file %s", path)
            return False, f"Could not read file: {path}", ""

        truncated = content[:max_chars]
        suffix = "" if len(content) <= max_chars else " [truncated]"
        return True, f"Read file {path}{suffix}", truncated

    def write_text_file(self, raw_path: str, content: str) -> tuple[bool, str]:
        try:
            path = self._resolve_allowed_path(raw_path, allow_create=True)
        except ValueError as exc:
            return False, str(exc)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except Exception:
            LOGGER.exception("Failed to write file %s", path)
            return False, f"Could not write file: {path}"

        return True, f"Saved file {path}"

    def search_files(self, pattern: str, base_path: str = ".", limit: int = 25) -> tuple[bool, str, list[str]]:
        try:
            root = self._resolve_allowed_path(base_path)
        except ValueError as exc:
            return False, str(exc), []

        if not root.exists() or not root.is_dir():
            return False, f"Search path not found: {root}", []

        matches: list[str] = []
        for candidate in root.rglob("*"):
            if fnmatch.fnmatch(candidate.name.lower(), pattern.lower()):
                matches.append(str(candidate))
                if len(matches) >= limit:
                    break

        preview = ", ".join(matches[:5]) if matches else "no matches"
        return True, f"Search results for pattern '{pattern}': {preview}", matches

    def _resolve_allowed_path(self, raw_path: str, allow_create: bool = False) -> Path:
        requested = Path(raw_path).expanduser()
        candidate = requested.resolve(strict=False if allow_create else True)
        for root in self._allowed_roots:
            if candidate == root or root in candidate.parents:
                return candidate
        raise ValueError(f"Path is outside allowed roots: {candidate}")
