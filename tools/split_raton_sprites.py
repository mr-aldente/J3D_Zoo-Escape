"""Split raton_spritesheet.png into Fox-style per-frame PNG folders."""
from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

ROOT = os.path.join(os.path.dirname(__file__), "..", "src", "assets", "Raton")
SHEET = os.path.join(ROOT, "raton_spritesheet.png")

ANIMS = (
    ("Courir_animation", "Courir", 6),
    ("Saut_animation", "Saut", 5),
    ("accroupie_animation", "accr", 4),
)


def is_sprite_pixel(color: tuple[int, ...]) -> bool:
    r, g, b, a = color
    if a < 8:
        return False
    if r < 18 and g < 18 and b < 18:
        return False
    return True


def column_counts(sheet: pygame.Surface, y0: int, h: int) -> list[int]:
    w = sheet.get_width()
    counts = []
    for x in range(w):
        n = 0
        for y in range(y0, y0 + h):
            if is_sprite_pixel(sheet.get_at((x, y))):
                n += 1
        counts.append(n)
    return counts


def content_bounds(
    sheet: pygame.Surface, x0: int, y0: int, w: int, h: int, margin: int = 6
) -> pygame.Rect | None:
    x1 = min(sheet.get_width(), x0 + w)
    y1 = min(sheet.get_height(), y0 + h)
    min_x, min_y = x1, y1
    max_x, max_y = -1, -1
    for y in range(y0, y1):
        for x in range(x0, x1):
            if is_sprite_pixel(sheet.get_at((x, y))):
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if max_x < min_x:
        return None
    rect = pygame.Rect(
        max(0, min_x - margin),
        max(0, min_y - margin),
        max_x - min_x + 1 + 2 * margin,
        max_y - min_y + 1 + 2 * margin,
    )
    rect.clamp_ip(sheet.get_rect())
    return rect


def row_bands(sheet: pygame.Surface) -> list[pygame.Rect]:
    bands: list[pygame.Rect] = []
    in_band = False
    start = 0
    for y in range(sheet.get_height()):
        n = sum(
            1
            for x in range(sheet.get_width())
            if is_sprite_pixel(sheet.get_at((x, y)))
        )
        if n > 12:
            if not in_band:
                start = y
                in_band = True
        elif in_band:
            bands.append(pygame.Rect(0, start, sheet.get_width(), y - start))
            in_band = False
    if in_band:
        bands.append(pygame.Rect(0, start, sheet.get_width(), sheet.get_height() - start))
    return bands


def gap_regions(counts: list[int], threshold: int = 3, min_width: int = 8) -> list[tuple[int, int, int]]:
    regions: list[tuple[int, int, int]] = []
    in_gap = False
    gap_start = 0
    for x, n in enumerate(counts):
        if n <= threshold:
            if not in_gap:
                gap_start = x
                in_gap = True
        elif in_gap:
            gap_end = x - 1
            width = gap_end - gap_start + 1
            if width >= min_width:
                mid = (gap_start + gap_end) // 2
                regions.append((gap_start, gap_end, width))
            in_gap = False
    return regions


def column_slices(sheet: pygame.Surface, row: pygame.Rect, frame_count: int) -> list[pygame.Rect]:
    counts = column_counts(sheet, row.y, row.height)
    row_bounds = content_bounds(sheet, row.x, row.y, row.width, row.height, margin=0)
    if row_bounds is None:
        return []

    left = row_bounds.left
    right = row_bounds.right
    needed = frame_count - 1
    gaps: list[tuple[int, int, int, int]] = []
    for start, end, width in gap_regions(counts):
        mid = (start + end) // 2
        if left + 12 < mid < right - 12:
            gaps.append((start, end, width, mid))

    if len(gaps) >= needed:
        # Use left-to-right gaps (not widest) so frame order matches the sheet.
        picked = sorted(gaps, key=lambda g: g[3])[:needed]
        rects = []
        for i in range(frame_count):
            x0 = left if i == 0 else picked[i - 1][1] + 1
            x1 = picked[i][0] if i < needed else right
            if x1 > x0:
                rects.append(pygame.Rect(x0, row.y, x1 - x0, row.height))
        if len(rects) == frame_count:
            return rects

    span = right - left
    cell = span / frame_count
    return [
        pygame.Rect(int(left + i * cell), row.y, max(1, int(left + (i + 1) * cell) - int(left + i * cell)), row.height)
        for i in range(frame_count)
    ]


def keep_largest_component(frame: pygame.Surface) -> pygame.Surface:
    """Keep only the biggest connected sprite blob (drops bleed from neighbours)."""
    w, h = frame.get_size()
    visited = [[False] * h for _ in range(w)]
    best: list[tuple[int, int]] = []
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))

    for y in range(h):
        for x in range(w):
            if visited[x][y] or not is_sprite_pixel(frame.get_at((x, y))):
                continue
            stack = [(x, y)]
            visited[x][y] = True
            comp: list[tuple[int, int]] = []
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for dx, dy in dirs:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not visited[nx][ny]:
                        if is_sprite_pixel(frame.get_at((nx, ny))):
                            visited[nx][ny] = True
                            stack.append((nx, ny))
            if len(comp) > len(best):
                best = comp

    if len(best) < 8:
        return frame

    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.fill((0, 0, 0, 0))
    for x, y in best:
        out.set_at((x, y), frame.get_at((x, y)))
    return out


def trim_cell(sheet: pygame.Surface, cell: pygame.Rect) -> pygame.Surface | None:
    bounds = content_bounds(sheet, cell.x, cell.y, cell.width, cell.height, margin=8)
    if bounds is None:
        return None
    frame = pygame.Surface((bounds.width, bounds.height), pygame.SRCALPHA)
    frame.blit(sheet, (0, 0), bounds)
    frame = keep_largest_component(frame)
    bounds2 = content_bounds(
        frame, 0, 0, frame.get_width(), frame.get_height(), margin=4
    )
    if bounds2 is None:
        return None
    out = pygame.Surface((bounds2.width, bounds2.height), pygame.SRCALPHA)
    out.blit(frame, (0, 0), bounds2)
    return out


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    if not os.path.isfile(SHEET):
        print(f"Missing: {SHEET}", file=sys.stderr)
        sys.exit(1)

    sheet = pygame.image.load(SHEET).convert_alpha()
    rows = row_bands(sheet)
    print(f"Sheet {sheet.get_size()}, {len(rows)} rows")

    if len(rows) < 3:
        print("Not enough rows detected", file=sys.stderr)
        sys.exit(1)

    for idx, (folder, prefix, count) in enumerate(ANIMS):
        dest = os.path.join(ROOT, folder)
        os.makedirs(dest, exist_ok=True)
        slices = column_slices(sheet, rows[idx], count)
        print(f"{folder}: {len(slices)} frames")
        for i, cell in enumerate(slices):
            frame = trim_cell(sheet, cell)
            if frame is None:
                print(f"  warn empty {prefix}{i + 1}")
                continue
            path = os.path.join(dest, f"{prefix}{i + 1}.png")
            pygame.image.save(frame, path)

    print("Done.")


if __name__ == "__main__":
    main()
