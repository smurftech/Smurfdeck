from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps
from StreamDeck.ImageHelpers import PILHelper

from smurfdeck.rendering.images import load_animation


def numbered_key_image(deck: Any, number: int) -> bytes:
    return labeled_key_image(deck, str(number))


def key_preview(
    size: tuple[int, int],
    label: str,
    *,
    icon: str = "",
    foreground: str = "#F2F4F7",
    background: str = "#101827",
    state: str = "",
    image_path: str = "",
    elapsed_ms: int = 0,
) -> Image.Image:
    """Use the same composition for editor previews and hardware rendering."""
    image = Image.new("RGB", size, background)
    if image_path:
        try:
            animation = load_animation(image_path)
            frame = animation.frames[animation.frame_index(elapsed_ms)]
            frame = ImageOps.contain(frame, size, Image.Resampling.LANCZOS)
            image.paste(frame, ((size[0] - frame.width) // 2, (size[1] - frame.height) // 2), frame)
        except ValueError:
            icon = "!"
            image_path = ""
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (3, 3, image.width - 4, image.height - 4),
        radius=8,
        outline={"running": "#4FC3FF", "success": "#4FE0B6", "failure": "#F0A65B"}.get(
            state, "#0D6EFD"
        ),
        width=2,
    )
    display = (label if image_path else f"{icon}\n{label}").strip()
    if display:
        # Wrap long labels and measure actual glyph bounds, not just character count.
        words = display.split("\n")
        lines = []
        for line in words:
            if len(line) > 12 and " " in line:
                parts = line.split()
                midpoint = max(1, len(parts) // 2)
                lines.extend((" ".join(parts[:midpoint]), " ".join(parts[midpoint:])))
            else:
                lines.append(line)
        display = "\n".join(lines)
        font = _fitted_font(display, size)
        box = draw.multiline_textbbox((0, 0), display, font=font, spacing=2, align="center")
        x = (image.width - (box[2] - box[0])) / 2 - box[0]
        y = (image.height - (box[3] - box[1])) / 2 - box[1]
        draw.multiline_text(
            (x, y),
            display,
            font=font,
            fill=foreground,
            align="center",
            spacing=2,
            stroke_width=1 if image_path else 0,
            stroke_fill=background,
        )
    return image


def labeled_key_image(deck: Any, label: str, **options: Any) -> bytes:
    image = key_preview(deck.key_image_format()["size"], label, **options)
    return PILHelper.to_native_key_format(deck, image)


def _fitted_font(text: str, size: tuple[int, int]) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    draw = ImageDraw.Draw(Image.new("RGB", size))
    for name in ("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"):
        try:
            for point_size in range(int(min(size) * 0.30), 5, -1):
                font = ImageFont.truetype(name, point_size)
                box = draw.multiline_textbbox((0, 0), text, font=font, spacing=2)
                if box[2] - box[0] <= size[0] - 14 and box[3] - box[1] <= size[1] - 14:
                    return font
            return font
        except OSError:
            continue
    return ImageFont.load_default()
