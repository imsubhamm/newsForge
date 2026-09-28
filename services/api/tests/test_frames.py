from pathlib import Path

import pytest

from app.services.frame_overlay import (
    CANVASES,
    FrameOverlayError,
    banner_overlay_path,
    build_text_layer,
    canvas_size,
    overlay_filter,
)


def test_banner_overlay_file_is_present() -> None:
    path = banner_overlay_path()
    assert path.is_file()
    assert path.stat().st_size > 1000


def test_canvas_rejects_unknown_ratio() -> None:
    with pytest.raises(FrameOverlayError):
        canvas_size("4:3")


def test_text_layer_is_transparent_except_when_text(tmp_path: Path) -> None:
    dest = tmp_path / "text.png"
    assert build_text_layer(dest, aspect_ratio="16:9") is None
    result = build_text_layer(dest, aspect_ratio="16:9", footer="দুর্গাপুর", location="Asansol")
    assert result == dest
    from PIL import Image

    image = Image.open(dest)
    assert image.size == CANVASES["16:9"]
    assert image.mode == "RGBA"
    assert image.getpixel((960, 540))[3] == 0


def _opaque_bbox_in(image, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    pixels = image.load()
    left, top, right, bottom = box
    xs: list[int] = []
    ys: list[int] = []
    for y in range(max(0, top), min(image.size[1], bottom)):
        for x in range(max(0, left), min(image.size[0], right)):
            if pixels[x, y][3] > 0:
                xs.append(x)
                ys.append(y)
    assert xs and ys
    return min(xs), min(ys), max(xs), max(ys)


def test_location_plate_fills_the_white_box(tmp_path: Path) -> None:
    from PIL import Image

    from app.services.frame_overlay import LOCATION_FILL, LOCATION_MAX_BOX, map_box

    dest = tmp_path / "location.png"
    assert build_text_layer(dest, aspect_ratio="16:9", location="Asansol") == dest
    image = Image.open(dest)
    box = map_box(LOCATION_MAX_BOX, width=1920, height=1080, aspect_ratio="16:9")
    left, top, right, bottom = _opaque_bbox_in(image, box)
    assert left >= box[0] - 2
    assert top >= box[1] - 2
    assert right <= box[2] + 2
    opaque = [
        image.getpixel((x, y))
        for y in range(top, bottom, 2)
        for x in range(left, right, 2)
        if image.getpixel((x, y))[3] == 255
    ]
    assert any(pixel[:3] == LOCATION_FILL[:3] for pixel in opaque)
    assert any(pixel[0] < 80 for pixel in opaque), "location text should be drawn in dark ink on the white plate"


def test_location_plate_shrinks_to_the_word(tmp_path: Path) -> None:
    from PIL import Image

    from app.services.frame_overlay import LOCATION_MAX_BOX, map_box

    short_path = tmp_path / "short.png"
    long_path = tmp_path / "long.png"
    build_text_layer(short_path, aspect_ratio="16:9", location="Go")
    build_text_layer(long_path, aspect_ratio="16:9", location="দুর্গাপুর পশ্চিম বর্ধমান")
    box = map_box(LOCATION_MAX_BOX, width=1920, height=1080, aspect_ratio="16:9")
    short = _opaque_bbox_in(Image.open(short_path), box)
    long = _opaque_bbox_in(Image.open(long_path), box)
    assert (short[2] - short[0]) < (long[2] - long[0])
    assert short[2] - short[0] < 280


def test_bengali_location_uses_shaped_conjuncts(tmp_path: Path) -> None:
    from app.config import repo_root
    from app.services.frame_overlay import render_shaped_text, shaped_glyph_count

    fonts = repo_root() / "video" / "public" / "fonts" / "NotoSansBengali-Bold.ttf"
    word = "দুর্গাপুর"
    assert len(word) == 9
    assert shaped_glyph_count(word, str(fonts)) == 8
    sprite = render_shaped_text(word, str(fonts), 48, (32, 32, 36, 255))
    dest = tmp_path / "shaped.png"
    sprite.save(dest)
    assert sprite.size[0] > 80
    assert sprite.size[1] > 20


def test_header_and_footer_land_on_red_bars(tmp_path: Path) -> None:
    from PIL import Image

    from app.services.frame_overlay import FOOTER_BOX, HEADER_BAR, HEADER_FILL, map_box

    dest = tmp_path / "bars.png"
    build_text_layer(
        dest,
        aspect_ratio="16:9",
        header="সর্বদলীয় বৈঠকে প্রশ্ন",
        footer="বাদ যাওয়া ভোটার",
        location="দুর্গাপুর",
    )
    image = Image.open(dest)
    header = map_box(HEADER_BAR, width=1920, height=1080, aspect_ratio="16:9")
    footer = map_box(FOOTER_BOX, width=1920, height=1080, aspect_ratio="16:9")
    hx = header[0] + 12
    hy = header[1] + 4
    assert image.getpixel((hx, hy))[:3] == HEADER_FILL[:3]
    fy = (footer[1] + footer[3]) // 2
    ink = [
        image.getpixel((x, fy))
        for x in range(footer[0], footer[2], 4)
        if image.getpixel((x, fy))[3] == 255
    ]
    assert any(pixel[0] > 200 and pixel[1] > 200 for pixel in ink)


def test_overlay_filter_chromakeys_banner() -> None:
    landscape = overlay_filter("16:9", 1920, 1080, False)
    assert "chromakey=0x16B900" in landscape
    assert "[0:v]scale=1920:1080" in landscape
    assert "drawbox=" in landscape
    portrait = overlay_filter("9:16", 1080, 1920, True)
    assert "crop=" in portrait
    assert "[2:v]overlay" in portrait
    assert "replace=1" in portrait
