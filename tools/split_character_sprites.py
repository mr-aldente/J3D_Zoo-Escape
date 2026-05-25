"""Split a character spritesheet into per-frame PNG folders (Fox-style layout).

Expects a sheet with left/right halves (uses left = facing right) and rows:
  jump, run, slide, then optional idle states (ignored).
"""
from __future__ import annotations

import argparse
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

# Import shared helpers from the Raton splitter
sys.path.insert(0, os.path.dirname(__file__))
from split_raton_sprites import (  # noqa: E402
    ANIMS,
    column_slices,
    is_sprite_pixel,
    row_bands,
    trim_cell,
)

# Slide row is shorter than jump/run; états divers row is tall but must be skipped.
MIN_ROW_HEIGHT = 30
MIN_ROW_Y = 60  # ignore title / header bands
FRAME_COUNTS = {
    "Courir_animation": 6,
    "Saut_animation": 6,
    "accroupie_animation": 4,
}
PREFIXES = {
    "Courir_animation": "Courir",
    "Saut_animation": "Saut",
    "accroupie_animation": "accr",
}


def animation_rows(sheet: pygame.Surface) -> list[pygame.Rect]:
    """Return jump, run, slide rows (first 3 sprite bands; skip états divers)."""
    bands = [
        r for r in row_bands(sheet)
        if r.height >= MIN_ROW_HEIGHT and r.y >= MIN_ROW_Y
    ]
    if len(bands) < 3:
        raise RuntimeError(f"Expected >= 3 animation rows, found {len(bands)}")
    # Sheet order: saut, course, glissade, then états divers (debout, assis, …)
    return bands[:3]


def split_sheet(sheet_path: str, dest_root: str) -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))

    if not os.path.isfile(sheet_path):
        raise FileNotFoundError(sheet_path)

    sheet = pygame.image.load(sheet_path).convert_alpha()
    w, h = sheet.get_size()
    # Left half: character facing right (game default)
    sheet = sheet.subsurface((0, 0, w // 2, h))

    rows = animation_rows(sheet)
    print(f"Sheet {sheet_path} -> {dest_root} ({sheet.get_size()}, {len(rows)} anim rows)")

    for idx, (folder, _prefix, _count) in enumerate(ANIMS):
        folder_name = folder
        prefix = PREFIXES[folder_name]
        count = FRAME_COUNTS[folder_name]
        dest = os.path.join(dest_root, folder_name)
        os.makedirs(dest, exist_ok=True)

        # Clear old frames
        for name in os.listdir(dest):
            if name.lower().endswith(".png"):
                os.remove(os.path.join(dest, name))

        slices = column_slices(sheet, rows[idx], count)
        saved = 0
        for i, cell in enumerate(slices):
            frame = trim_cell(sheet, cell)
            if frame is None or frame.get_width() < 40:
                print(f"    warn skip {prefix}{i + 1} (empty or too narrow)")
                continue
            path = os.path.join(dest, f"{prefix}{saved + 1}.png")
            pygame.image.save(frame, path)
            saved += 1
        print(f"  {folder_name}: {saved} frames")


def main() -> None:
    parser = argparse.ArgumentParser(description="Split character spritesheet into animation folders.")
    parser.add_argument("character", help="Character folder name (Shark, Parrot, Lion, Penguin)")
    parser.add_argument(
        "--sheet",
        help="Path to spritesheet PNG (default: assets/<character>/spritesheet.png)",
    )
    args = parser.parse_args()

    assets = os.path.join(os.path.dirname(__file__), "..", "src", "assets", args.character)
    sheet = args.sheet or os.path.join(assets, "spritesheet.png")
    split_sheet(sheet, assets)
    print("Done.")


if __name__ == "__main__":
    main()
