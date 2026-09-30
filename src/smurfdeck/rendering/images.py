"""Bounded image decoding shared by the editor and physical keys."""

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 4_000_000
MAX_FRAMES = 120


@dataclass(frozen=True)
class KeyAnimation:
    frames: tuple[Image.Image, ...]
    durations: tuple[int, ...]

    def frame_index(self, elapsed_ms: int) -> int:
        position = elapsed_ms % sum(self.durations)
        for index, duration in enumerate(self.durations):
            if position < duration:
                return index
            position -= duration
        return 0


@lru_cache(maxsize=64)
def _decode(path: str, mtime_ns: int, file_size: int) -> KeyAnimation:
    del mtime_ns
    if file_size > MAX_FILE_BYTES:
        raise ValueError("Choose an image smaller than 10 MiB")
    frames, durations = [], []
    with Image.open(path) as source:
        if source.format not in {"PNG", "JPEG", "GIF", "WEBP", "BMP"}:
            raise ValueError("Choose a PNG, JPEG, GIF, WebP or BMP image")
        if source.width * source.height > MAX_PIXELS:
            raise ValueError("Choose an image with at most 4 million pixels")
        count = getattr(source, "n_frames", 1)
        if count > MAX_FRAMES:
            raise ValueError("Animations may contain at most 120 frames")
        for index in range(count):
            source.seek(index)
            frame = ImageOps.exif_transpose(source).convert("RGBA")
            frame.thumbnail((144, 144), Image.Resampling.LANCZOS)
            frames.append(frame)
            durations.append(max(100, int(source.info.get("duration", 100))))
    return KeyAnimation(tuple(frames), tuple(durations))


def load_animation(path: str) -> KeyAnimation:
    try:
        file = Path(path)
        stat = file.stat()
        return _decode(str(file), stat.st_mtime_ns, stat.st_size)
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise ValueError(f"Cannot read key image: {error}") from error


def import_image(source: Path, asset_directory: Path) -> str:
    """Copy an accepted image into app-owned storage so originals can be moved."""
    load_animation(str(source))
    data = source.read_bytes()
    name = sha256(data).hexdigest() + source.suffix.lower()
    asset_directory.mkdir(parents=True, exist_ok=True)
    target = asset_directory / name
    if not target.exists():
        target.write_bytes(data)
    return str(target.resolve())
