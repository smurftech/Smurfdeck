from __future__ import annotations

from typing import Any

from PIL import ImageDraw, ImageFont
from StreamDeck.ImageHelpers import PILHelper


def numbered_key_image(deck: Any, number: int) -> bytes:
    """Render a high-contrast numbered test image in native device format."""
    image = PILHelper.create_scaled_key_image(deck, background="#101827")
    draw = ImageDraw.Draw(image)
    text = str(number)
    font = _fitted_font(text, image.size)
    box = draw.textbbox((0, 0), text, font=font)
    x = (image.width - (box[2] - box[0])) / 2 - box[0]
    y = (image.height - (box[3] - box[1])) / 2 - box[1]
    draw.rounded_rectangle(
        (3, 3, image.width - 4, image.height - 4),
        radius=8,
        outline="#38bdf8",
        width=3,
    )
    draw.text((x, y), text, font=font, fill="#f8fafc")
    return PILHelper.to_native_key_format(deck, image)


def _fitted_font(
    text: str, size: tuple[int, int]
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    target = int(min(size) * (0.58 if len(text) < 2 else 0.44))
    for name in ("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, target)
        except OSError:
            continue
    return ImageFont.load_default()

