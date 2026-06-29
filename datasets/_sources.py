"""Shared helper for downloading and caching zipped datasets on disk."""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

import requests

# Anchor the cache to <repo>/data so the location is independent of the
# working directory Quarto happens to render from.
_DATA_ROOT = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class ZipDataset:
    """A remote zip archive cached under a local extraction directory.

    The ``sentinel`` file is used to detect a warm cache: if it already
    exists, the archive is not re-downloaded.
    """

    url: str
    dest: Path  # directory the zip extracts into
    sentinel: str  # file expected to exist once extracted

    def ensure(self) -> Path:
        """Return the extraction directory, downloading the zip if missing."""
        if not (self.dest / self.sentinel).exists():
            self.dest.mkdir(parents=True, exist_ok=True)
            resp = requests.get(self.url, stream=True, timeout=120)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                zf.extractall(self.dest)
        return self.dest
