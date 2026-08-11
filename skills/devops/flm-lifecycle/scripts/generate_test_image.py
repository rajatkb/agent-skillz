#!/usr/bin/env python3
"""Generate a standard 400x200 test image for FLM vision pipeline validation.

Produces: red rect with white "Hello" (left), blue circle with green "TEST IMAGE" (right).

Usage:
    python3 generate_test_image.py                     # /tmp/flm_test_image.png
    python3 generate_test_image.py --output ~/test.png # custom path
"""
import argparse
from PIL import Image, ImageDraw, ImageFont
import os


def find_font(size=32, bold=True):
    """Find a suitable TrueType font, falling back to default."""
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'Bold' if bold else ''}.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def generate(output: str = "/tmp/flm_test_image.png"):
    img = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(img)

    font_large = find_font(32, bold=True)
    font_small = find_font(20, bold=False)

    # Left half: red rectangle with white "Hello" centered
    draw.rectangle([(10, 10), (190, 190)], fill="red")
    bbox = draw.textbbox((0, 0), "Hello", font=font_large)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((100 - tw // 2, 100 - th // 2), "Hello", fill="white", font=font_large)

    # Right half: green "TEST IMAGE" at top, blue circle below
    draw.text((210, 10), "TEST IMAGE", fill="green", font=font_small)
    draw.ellipse([(230, 40), (370, 180)], fill="blue", outline="darkblue", width=3)

    img.save(output)
    print(f"Test image saved: {output}  ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate FLM vision test image")
    parser.add_argument("--output", "-o", default="/tmp/flm_test_image.png",
                        help="Output file path (default: /tmp/flm_test_image.png)")
    args = parser.parse_args()
    generate(args.output)
