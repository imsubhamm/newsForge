from __future__ import annotations

from pathlib import Path

import freetype
import uharfbuzz as hb
from PIL import Image, ImageDraw

from app.config import repo_root

CANVASES = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
}

# Source overlay is 816×464. Green key sampled from banner.mp4.
TEMPLATE_SIZE = (816, 464)
CHROMAKEY = "chromakey=0x16B900:0.11:0.04"
PORTRAIT_TOP_RATIO = 0.24
PORTRAIT_BOTTOM_RATIO = 0.32
PORTRAIT_TOP_Y = 24

# Boxes in template pixels: left, top, right, bottom (measured from banner.mp4)
LOCATION_BOX = (70, 40, 180, 80)
LOCATION_MAX_BOX = (78, 10, 280, 50)
HEADER_BAR = (62, 0, 672, 56)
HEADER_TEXT_BOX = (200, 8, 662, 50)
FOOTER_BOX = (188, 372, 800, 414)
HEADLINE_BOX = FOOTER_BOX
HEADER_FILL = (204, 17, 1, 255)
HEADER_INK = (255, 255, 255, 255)
LOCATION_FILL = (236, 237, 239, 255)
LOCATION_INK = (32, 32, 36, 255)
DEFAULT_LOCATION = "দুর্গাপুর"


class FrameOverlayError(RuntimeError):
    pass


def canvas_size(aspect_ratio: str) -> tuple[int, int]:
    if aspect_ratio not in CANVASES:
        raise FrameOverlayError(f"unsupported aspect ratio '{aspect_ratio}'")
    return CANVASES[aspect_ratio]


def even(value: int) -> int:
    return value - (value % 2)


def banner_overlay_path() -> Path:
    candidates = [
        repo_root() / "storage" / "assets" / "amar-katha-banner.mp4",
        Path("/Users/imsub/Downloads/banner.mp4"),
    ]
    for path in candidates:
        if path.is_file() and path.stat().st_size > 1000:
            return path
    raise FrameOverlayError(
        "আমার কথা banner overlay is missing. Place banner.mp4 at storage/assets/amar-katha-banner.mp4"
    )


def portrait_overlay_height(width: int) -> int:
    tw, th = TEMPLATE_SIZE
    return even(round(width * th / tw))


def map_box(box: tuple[int, int, int, int], *, width: int, height: int, aspect_ratio: str) -> tuple[int, int, int, int]:
    tw, th = TEMPLATE_SIZE
    left, top, right, bottom = box
    if aspect_ratio == "16:9":
        return (
            round(left / tw * width),
            round(top / th * height),
            round(right / tw * width),
            round(bottom / th * height),
        )
    ov_h = portrait_overlay_height(width)
    top_h = even(int(ov_h * PORTRAIT_TOP_RATIO))
    bot_h = even(int(ov_h * PORTRAIT_BOTTOM_RATIO))
    scale_y = ov_h / th
    scale_x = width / tw
    mapped = (
        round(left * scale_x),
        round(top * scale_y),
        round(right * scale_x),
        round(bottom * scale_y),
    )
    # Location sits in the top slice; headline sits in the bottom slice.
    if top < th * 0.4:
        dy = PORTRAIT_TOP_Y
        return mapped[0], mapped[1] + dy, mapped[2], mapped[3] + dy
    crop_start = ov_h - bot_h
    dy = height - bot_h - crop_start
    return mapped[0], mapped[1] + dy, mapped[2], mapped[3] + dy


def build_text_layer(
    dest: Path,
    *,
    aspect_ratio: str,
    headline: str = "",
    header: str = "",
    footer: str = "",
    location: str = "",
) -> Path | None:
    top_line = header.strip()
    bottom_line = footer.strip() or headline.strip()
    place = location.strip()
    if not top_line and not bottom_line and not place:
        return None
    width, height = canvas_size(aspect_ratio)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    fonts = _load_fonts(aspect_ratio)
    header_left = None
    if top_line:
        bar = map_box(HEADER_BAR, width=width, height=height, aspect_ratio=aspect_ratio)
        draw.rectangle(bar, fill=HEADER_FILL)
    if place:
        origin = map_box(LOCATION_MAX_BOX, width=width, height=height, aspect_ratio=aspect_ratio)
        path, size = _font_for(place, fonts["location"])
        plate, sprite = _fitted_location_plate(place, path, size, origin)
        _draw_location_plate(draw, plate)
        _paste_centered(image, sprite, plate)
        header_left = plate[2] + max(12, (plate[3] - plate[1]) // 3)
    if top_line:
        path, size = _font_for(top_line, fonts["header"])
        box = list(map_box(HEADER_TEXT_BOX, width=width, height=height, aspect_ratio=aspect_ratio))
        if header_left is not None:
            box[0] = max(box[0], header_left)
        sprite = _fit_shaped_sprite(
            top_line,
            path,
            size,
            max_width=max(8, box[2] - box[0] - 8),
            max_height=max(8, box[3] - box[1] - 4),
            fill=HEADER_INK,
        )
        image.alpha_composite(sprite, (box[0] + 4, box[1] + max(0, (box[3] - box[1] - sprite.height) // 2)))
    if bottom_line:
        path, size = _font_for(bottom_line, fonts["footer"])
        box = map_box(FOOTER_BOX, width=width, height=height, aspect_ratio=aspect_ratio)
        sprite = _fit_shaped_sprite(
            bottom_line,
            path,
            size,
            max_width=max(8, box[2] - box[0] - 8),
            max_height=max(8, box[3] - box[1]),
            fill=HEADER_INK,
        )
        image.alpha_composite(sprite, (box[0] + 4, box[1] + max(0, (box[3] - box[1] - sprite.height) // 2)))
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, "PNG")
    return dest


def overlay_filter(aspect_ratio: str, width: int, height: int, has_text: bool) -> str:
    base = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x070B14,setsar=1,format=rgba[base];"
    )
    erase = _erase_banner_plate(aspect_ratio, width, height)
    if aspect_ratio == "16:9":
        keyed = (
            f"[1:v]scale={width}:{height},{CHROMAKEY},format=rgba,{erase}[ov];"
            f"[base][ov]overlay=0:0:shortest=1[framed]"
        )
    else:
        ov_h = portrait_overlay_height(width)
        top_h = even(int(ov_h * PORTRAIT_TOP_RATIO))
        bot_h = even(int(ov_h * PORTRAIT_BOTTOM_RATIO))
        keyed = (
            f"[1:v]scale={width}:{ov_h},{CHROMAKEY},format=rgba,{erase},split=2[s1][s2];"
            f"[s1]crop={width}:{top_h}:0:0[top];"
            f"[s2]crop={width}:{bot_h}:0:{ov_h - bot_h}[bot];"
            f"[base][top]overlay=0:{PORTRAIT_TOP_Y}:shortest=1[tmp];"
            f"[tmp][bot]overlay=0:{height - bot_h}:shortest=1[framed]"
        )
    if has_text:
        return base + keyed + ";[framed][2:v]overlay=0:0:format=auto,format=yuv420p[vout]"
    return base + keyed + ";[framed]format=yuv420p[vout]"


def _draw_location_plate(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    radius = max(2, min(8, (bottom - top) // 6))
    draw.rounded_rectangle((left, top, right, bottom), radius=radius, fill=LOCATION_FILL)


def _paste_centered(image: Image.Image, sprite: Image.Image, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    x = left + max(0, (right - left - sprite.width) // 2)
    y = top + max(0, (bottom - top - sprite.height) // 2)
    image.alpha_composite(sprite, (x, y))


def _fitted_location_plate(
    text: str,
    font_path: str,
    start_size: int,
    origin: tuple[int, int, int, int],
) -> tuple[tuple[int, int, int, int], Image.Image]:
    left, top, max_right, bottom = origin
    plate_h = max(12, bottom - top)
    pad_x = max(10, plate_h // 5)
    max_text_w = max(8, max_right - left - pad_x * 2)
    sprite = _fit_shaped_sprite(text, font_path, start_size, max_width=max_text_w, max_height=max(8, plate_h - 6), fill=LOCATION_INK)
    plate_w = min(max_right - left, sprite.width + pad_x * 2)
    return (left, top, left + plate_w, bottom), sprite


def _fit_shaped_sprite(
    text: str,
    font_path: str,
    start_size: int,
    *,
    max_width: int,
    max_height: int,
    fill: tuple[int, int, int, int] = (255, 255, 255, 255),
) -> Image.Image:
    size = start_size
    sprite = render_shaped_text(text, font_path, size, fill)
    while size >= 12 and (sprite.width > max_width or sprite.height > max_height):
        size -= 2
        sprite = render_shaped_text(text, font_path, size, fill)
    return sprite


def render_shaped_text(
    text: str,
    font_path: str,
    size: int,
    fill: tuple[int, int, int, int],
) -> Image.Image:
    """Rasterize `text` with HarfBuzz so Bengali conjuncts like র্গা stay intact."""
    if not text:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    face = freetype.Face(font_path)
    face.set_pixel_sizes(0, size)
    blob = hb.Blob.from_file_path(font_path)
    hb_face = hb.Face(blob)
    hb_font = hb.Font(hb_face)
    hb_font.scale = (size * 64, size * 64)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf)

    glyphs: list[tuple[int, int, Image.Image]] = []
    pen_x = 0
    pen_y = 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions, strict=True):
        face.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
        bitmap = face.glyph.bitmap
        x = (pen_x + pos.x_offset >> 6) + face.glyph.bitmap_left
        y = -((pen_y + pos.y_offset) >> 6) - face.glyph.bitmap_top
        if bitmap.width and bitmap.rows:
            mask = _ft_bitmap_image(bitmap)
            ink = Image.new("RGBA", mask.size, fill)
            ink.putalpha(mask)
            glyphs.append((x, y, ink))
        pen_x += pos.x_advance
        pen_y += pos.y_advance

    if not glyphs:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    min_x = min(x for x, _y, _im in glyphs)
    min_y = min(y for _x, y, _im in glyphs)
    max_x = max(x + im.width for x, _y, im in glyphs)
    max_y = max(y + im.height for _x, y, im in glyphs)
    sprite = Image.new("RGBA", (max(1, max_x - min_x), max(1, max_y - min_y)), (0, 0, 0, 0))
    for x, y, ink in glyphs:
        sprite.alpha_composite(ink, (x - min_x, y - min_y))
    return sprite


def shaped_glyph_count(text: str, font_path: str, size: int = 32) -> int:
    blob = hb.Blob.from_file_path(font_path)
    hb_font = hb.Font(hb.Face(blob))
    hb_font.scale = (size * 64, size * 64)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf)
    return len(buf.glyph_infos)


def _ft_bitmap_image(bitmap: freetype.Bitmap) -> Image.Image:
    width, height, pitch = bitmap.width, bitmap.rows, bitmap.pitch
    raw = bytes(bitmap.buffer)
    if pitch == width:
        data = raw
    else:
        data = b"".join(raw[row * pitch : row * pitch + width] for row in range(height))
    return Image.frombytes("L", (width, height), data)


def _erase_banner_plate(aspect_ratio: str, width: int, height: int) -> str:
    left, top, right, bottom = _map_overlay_box(LOCATION_BOX, width=width, height=height, aspect_ratio=aspect_ratio)
    return (
        f"drawbox=x={left}:y={top}:w={max(2, right - left)}:h={max(2, bottom - top)}"
        f":color=black@0:t=fill:replace=1"
    )


def _map_overlay_box(
    box: tuple[int, int, int, int],
    *,
    width: int,
    height: int,
    aspect_ratio: str,
) -> tuple[int, int, int, int]:
    tw, th = TEMPLATE_SIZE
    left, top, right, bottom = box
    if aspect_ratio == "16:9":
        return map_box(box, width=width, height=height, aspect_ratio=aspect_ratio)
    ov_h = portrait_overlay_height(width)
    return (
        round(left / tw * width),
        round(top / th * ov_h),
        round(right / tw * width),
        round(bottom / th * ov_h),
    )


def _contains_bengali(text: str) -> bool:
    return any("\u0980" <= char <= "\u09FF" for char in text)


def _font_for(text: str, preset: tuple[str, str, int]) -> tuple[str, int]:
    bengali, latin, size = preset
    return (bengali if _contains_bengali(text) else latin, size)


def _load_fonts(aspect_ratio: str) -> dict[str, tuple[str, str, int]]:
    fonts_dir = repo_root() / "video" / "public" / "fonts"
    bengali = fonts_dir / "NotoSansBengali-Bold.ttf"
    if not bengali.is_file():
        raise FrameOverlayError("Bengali overlay fonts are missing. Run scripts/generate-sample-assets.sh")
    latin_candidates = [
        fonts_dir / "NotoSans-Bold.ttf",
        Path("/System/Library/Fonts/Helvetica.ttc"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
    ]
    latin = next((path for path in latin_candidates if path.is_file()), bengali)
    landscape = aspect_ratio == "16:9"
    return {
        "header": (str(bengali), str(latin), 36 if landscape else 28),
        "footer": (str(bengali), str(latin), 40 if landscape else 32),
        "headline": (str(bengali), str(latin), 40 if landscape else 32),
        "location": (str(bengali), str(latin), 24 if landscape else 18),
    }
