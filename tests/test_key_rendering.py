from io import BytesIO

from PIL import Image

from smurfdeck.rendering.keys import numbered_key_image


class FakeVisualDeck:
    def key_image_format(self) -> dict[str, object]:
        return {
            "size": (72, 72),
            "rotation": 0,
            "flip": (False, False),
            "format": "JPEG",
        }


def test_numbered_key_image_uses_native_geometry_and_format() -> None:
    native_image = numbered_key_image(FakeVisualDeck(), 12)
    with Image.open(BytesIO(native_image)) as image:
        assert image.size == (72, 72)
        assert image.format == "JPEG"
