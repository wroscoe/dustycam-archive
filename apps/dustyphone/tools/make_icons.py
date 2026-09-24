#!/usr/bin/env python3
"""Generate the DustyCam launcher icons for apps/dustyphone.

No downloaded assets, no rsvg/inkscape/ImageMagick — only PIL.ImageDraw,
supersampled ~4x then downscaled, per the app's build constraints (no new
binary tools, everything reproducible from source).

The glyph is the DustyCam camera mark from dustycamsplash/index.html's
.brand-mark: viewBox 0 0 24 24, stroke-width 2.2, no fill —
    <path d="M3 8h4l2-3h6l2 3h4v11H3z"/>
    <circle cx="12" cy="13.5" r="3.5"/>
drawn in --paper on a --clay square with a 2px --ink border (see
dustycamsplash/index.html :root and .brand-mark).

Produces two icon families under res/:
  - Legacy per-density mipmap-*/ic_launcher.png (clay square + ink border +
    paper glyph, full bleed) for launchers that don't support adaptive icons.
  - Adaptive icon layers for API 26+ (minSdk is 26, so this is what almost
    every device actually shows): mipmap-*/ic_launcher_foreground.png (paper
    glyph only, transparent background, sized to fit the 66dp safe zone of
    the 108dp canvas so the OS mask/animation never crops it) plus
    res/mipmap-anydpi-v26/ic_launcher.xml + a solid clay background color.

Run: python3 tools/make_icons.py   (from apps/dustyphone/)
"""

from PIL import Image, ImageDraw
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "res")

# ---- palette (dustycamsplash/index.html :root) ----
CLAY = (0x93, 0x43, 0x33, 0xFF)
INK = (0x29, 0x29, 0x25, 0xFF)
PAPER = (0xFB, 0xF6, 0xED, 0xFF)
TRANSPARENT = (0, 0, 0, 0)

SUPERSAMPLE = 4

# Per-density legacy launcher icon sizes (px).
LAUNCHER_SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

# Adaptive icon foreground canvas is 108dp; same dp->px scale factor as the
# legacy sizes above (108/48 == 162/72 == ... == 2.25).
FOREGROUND_SIZES = {name: round(size * 108 / 48) for name, size in LAUNCHER_SIZES.items()}

# ---- glyph geometry (viewBox 0 0 24 24, stroke-width 2.2) ----
BODY_POINTS = [
    (3, 8), (7, 8), (9, 5), (15, 5), (17, 8), (21, 8), (21, 19), (3, 19), (3, 8),
]
LENS_CENTER = (12, 13.5)
LENS_RADIUS = 3.5
STROKE_W = 2.2

# Content bounding box of the glyph including half the stroke width, used to
# fit it into a target pixel box while preserving aspect ratio.
_half = STROKE_W / 2.0
_xs = [p[0] for p in BODY_POINTS] + [LENS_CENTER[0] - LENS_RADIUS, LENS_CENTER[0] + LENS_RADIUS]
_ys = [p[1] for p in BODY_POINTS] + [LENS_CENTER[1] - LENS_RADIUS, LENS_CENTER[1] + LENS_RADIUS]
GLYPH_BBOX = (min(_xs) - _half, min(_ys) - _half, max(_xs) + _half, max(_ys) + _half)


def draw_camera_glyph(draw, box, color):
    """Draw the stroked camera glyph centered in `box` (l, t, r, b), preserving
    aspect ratio. `color` is an RGBA tuple."""
    bx0, by0, bx1, by1 = box
    box_w, box_h = bx1 - bx0, by1 - by0
    gx0, gy0, gx1, gy1 = GLYPH_BBOX
    gw, gh = gx1 - gx0, gy1 - gy0
    scale = min(box_w / gw, box_h / gh)
    # Center the scaled glyph bbox within the target box.
    off_x = bx0 + (box_w - gw * scale) / 2.0 - gx0 * scale
    off_y = by0 + (box_h - gh * scale) / 2.0 - gy0 * scale

    def tx(pt):
        return (off_x + pt[0] * scale, off_y + pt[1] * scale)

    stroke_px = max(1, round(STROKE_W * scale))
    pts = [tx(p) for p in BODY_POINTS]
    draw.line(pts, fill=color, width=stroke_px, joint="curve")
    # Round the joints (PIL's polyline joints only cover interior vertices
    # cleanly) by stamping a small disc at every vertex.
    r = stroke_px / 2.0
    for (x, y) in pts:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)

    lcx, lcy = tx(LENS_CENTER)
    lr = LENS_RADIUS * scale
    draw.ellipse([lcx - lr, lcy - lr, lcx + lr, lcy + lr], outline=color, width=stroke_px)


def render(size_px, draw_fn):
    """Render at SUPERSAMPLE x size_px, run draw_fn(draw, ss_size), then
    downscale with LANCZOS for clean edges."""
    ss = size_px * SUPERSAMPLE
    img = Image.new("RGBA", (ss, ss), TRANSPARENT)
    draw = ImageDraw.Draw(img)
    draw_fn(draw, ss)
    return img.resize((size_px, size_px), Image.LANCZOS)


def make_legacy_icon(size_px):
    """Full-bleed clay square, 2px(-equivalent) ink border, paper glyph —
    matches dustycamsplash's .brand-mark exactly."""

    def draw_fn(draw, ss):
        draw.rectangle([0, 0, ss - 1, ss - 1], fill=CLAY)
        border_w = max(1, round(ss * (2.0 / 28.0)))  # brand-mark: 2px border / 28px square
        draw.rectangle(
            [border_w / 2.0, border_w / 2.0, ss - 1 - border_w / 2.0, ss - 1 - border_w / 2.0],
            outline=INK, width=border_w,
        )
        margin = ss * ((1 - 19.0 / 28.0) / 2.0)  # brand-mark: 19px glyph / 28px square, centered
        draw_camera_glyph(draw, (margin, margin, ss - margin, ss - margin), PAPER)

    return render(size_px, draw_fn)


def make_foreground(size_px):
    """Transparent background, paper glyph inscribed in the 66dp safe *circle*
    of the 108dp adaptive-icon canvas.

    Fitting the glyph's bounding box to a 66dp square is not enough: the glyph
    is wider than it is tall, so it ends up spanning the full 66dp width and
    its corners sit at radius > 33dp, which a circular launcher mask cuts off
    flat (observed on the Pixel 6, 2026-09-20). Scaling the box so its diagonal
    equals the safe circle's diameter puts the corners exactly on that circle.
    """
    gx0, gy0, gx1, gy1 = GLYPH_BBOX
    gw, gh = gx1 - gx0, gy1 - gy0
    diag = math.hypot(gw, gh)

    def draw_fn(draw, ss):
        safe_d = ss * 66.0 / 108.0
        box_w, box_h = safe_d * gw / diag, safe_d * gh / diag
        cx = cy = ss / 2.0
        draw_camera_glyph(
            draw,
            (cx - box_w / 2, cy - box_h / 2, cx + box_w / 2, cy + box_h / 2),
            PAPER,
        )

    return render(size_px, draw_fn)


def main():
    for dirname, size in LAUNCHER_SIZES.items():
        out_dir = os.path.join(RES, dirname)
        os.makedirs(out_dir, exist_ok=True)
        make_legacy_icon(size).save(os.path.join(out_dir, "ic_launcher.png"))
        make_foreground(FOREGROUND_SIZES[dirname]).save(
            os.path.join(out_dir, "ic_launcher_foreground.png"))
        print(f"{dirname}: ic_launcher.png {size}x{size}, "
              f"ic_launcher_foreground.png {FOREGROUND_SIZES[dirname]}x{FOREGROUND_SIZES[dirname]}")


if __name__ == "__main__":
    main()
