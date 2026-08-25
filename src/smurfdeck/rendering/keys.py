from __future__ import annotations

from typing import Any

from PIL import ImageDraw, ImageFont
from StreamDeck.ImageHelpers import PILHelper


def numbered_key_image(deck: Any, number: int) -> bytes:
    """Render a high-contrast numbered test image in native device format."""
    return labeled_key_image(deck, str(number))


def labeled_key_image(
    deck: Any,
    label: str,
    *,
    icon: str = "",
    foreground: str = "#F2F4F7",
    background: str = "#101827",
    state: str = "",
) -> bytes:
    """Render a label in the device's native key image format."""
    image = PILHelper.create_key_image(deck, background=background)
    draw = ImageDraw.Draw(image)
    text = label.strip()
    font = _fitted_font(text, image.size)
    draw.rounded_rectangle(
        (3, 3, image.width - 4, image.height - 4),
        radius=8,
        outline={"running": "#4FC3FF", "success": "#4FE0B6", "failure": "#F0A65B"}.get(
            state, "#0D6EFD"
        ),
        width=3,
    )
    display = f"{icon}\n{text}".strip()
    if display:
        font = _fitted_font(display, image.size)
        box = draw.multiline_textbbox((0, 0), display, font=font, align="center", spacing=2)
        x = (image.width - (box[2] - box[0])) / 2 - box[0]
        y = (image.height - (box[3] - box[1])) / 2 - box[1]
        draw.multiline_text((x, y), display, font=font, fill=foreground, align="center", spacing=2)
    return PILHelper.to_native_key_format(deck, image)


def _fitted_font(
    text: str, size: tuple[int, int]
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    longest_line = max((len(line) for line in text.splitlines()), default=1)
    target = int(min(size) * (0.58 if longest_line < 2 else 0.34 if longest_line > 7 else 0.44))
    for name in ("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, target)
        except OSError:
            continue
    return ImageFont.load_default()
