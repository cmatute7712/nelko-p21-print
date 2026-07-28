"""Serializable label document and Pillow renderer."""

import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from printer import LABEL_HEIGHT, LABEL_WIDTH


@dataclass
class LabelElement:
    kind: str
    x: int = 8
    y: int = 8
    text: str = "Text"
    font_size: int = 18
    image_path: str = ""
    width: int = 72
    height: int = 72
    element_id: str = ""

    def __post_init__(self):
        if not self.element_id:
            self.element_id = uuid.uuid4().hex


class LabelDocument:
    def __init__(self, elements=None):
        self.elements = elements or []

    def add_text(self, text="Text"):
        element = LabelElement("text", text=text)
        self.elements.append(element)
        return element

    def add_image(self, path):
        with Image.open(path) as source:
            width, height = source.size
        scale = min(80 / width, 120 / height, 1)
        element = LabelElement(
            "image", image_path=str(Path(path).resolve()), width=max(1, int(width * scale)),
            height=max(1, int(height * scale))
        )
        self.elements.append(element)
        return element

    @staticmethod
    def _font(size):
        for name in ("arial.ttf", "DejaVuSans.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                pass
        return ImageFont.load_default()

    def render(self):
        canvas = Image.new("L", (LABEL_WIDTH, LABEL_HEIGHT), "white")
        draw = ImageDraw.Draw(canvas)
        for element in self.elements:
            if element.kind == "text":
                draw.multiline_text(
                    (element.x, element.y), element.text, font=self._font(element.font_size),
                    fill="black", spacing=2
                )
            elif element.kind == "image" and Path(element.image_path).is_file():
                with Image.open(element.image_path) as source:
                    source = ImageOps.exif_transpose(source).convert("RGBA")
                    source.thumbnail((max(1, element.width), max(1, element.height)))
                    background = Image.new("RGBA", source.size, "white")
                    background.alpha_composite(source)
                    canvas.paste(background.convert("L"), (element.x, element.y))
        return canvas

    def save(self, path):
        Path(path).write_text(
            json.dumps({"version": 1, "elements": [asdict(item) for item in self.elements]}, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("version") != 1:
            raise ValueError("Unsupported label file version")
        return cls([LabelElement(**item) for item in data.get("elements", [])])
