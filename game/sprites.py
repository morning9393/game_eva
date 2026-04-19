"""Sprite factories.

Tries the Kenney Tiny Dungeon pack first (via `assets.py`), falls back to
procedurally drawn pixel art if the pack is missing. This keeps the game
runnable without any external downloads while giving a richer look when
the assets are present.
"""
import pygame

from . import assets
from . import constants as C

SCALE = 3          # player / boss / shard / sword scaling
FLOOR_SCALE = 2    # floor tile scaling

# ---------- kenney-backed sprites (with procedural fallback) ----------


def _fallback_player(facing=1):
    s = pygame.Surface((12, 14), pygame.SRCALPHA)
    pygame.draw.rect(s, (40, 48, 72), (2, 6, 8, 7))
    pygame.draw.rect(s, (60, 72, 100), (3, 7, 6, 5))
    pygame.draw.rect(s, (110, 90, 70), (3, 10, 6, 3))
    pygame.draw.rect(s, (30, 34, 52), (3, 2, 6, 5))
    pygame.draw.rect(s, (210, 180, 150), (4, 5, 4, 2))
    eye_x = 6 if facing == 1 else 5
    s.set_at((eye_x, 5), (255, 255, 255))
    pygame.draw.rect(s, (80, 60, 44), (3, 9, 6, 1))
    pygame.draw.rect(s, (30, 30, 40), (3, 13, 2, 1))
    pygame.draw.rect(s, (30, 30, 40), (7, 13, 2, 1))
    if facing == -1:
        s = pygame.transform.flip(s, True, False)
    return pygame.transform.scale(s, (s.get_width() * SCALE, s.get_height() * SCALE))


def make_player_sprite(facing=1):
    spr = assets.get(*assets.TILE_PLAYER, scale=SCALE, flip_x=(facing == -1))
    if spr is not None:
        return spr
    return _fallback_player(facing)


def _fallback_boss(phase=1, flash=0):
    s = pygame.Surface((22, 30), pygame.SRCALPHA)
    cloak = (36, 16, 44) if phase == 1 else (70, 18, 30)
    pygame.draw.rect(s, cloak, (2, 10, 18, 18))
    pygame.draw.rect(s, (min(cloak[0] + 20, 255), min(cloak[1] + 20, 255), min(cloak[2] + 20, 255)), (3, 11, 16, 16))
    pygame.draw.rect(s, (80, 80, 100), (5, 12, 12, 10))
    pygame.draw.rect(s, (120, 120, 140), (5, 12, 12, 2))
    pygame.draw.rect(s, C.GOLD, (10, 15, 2, 2))
    pygame.draw.rect(s, C.EMBER if phase == 2 else C.AZURE, (10, 16, 2, 1))
    pygame.draw.rect(s, (200, 190, 170), (7, 4, 8, 7))
    pygame.draw.rect(s, (30, 10, 10), (9, 7, 1, 2))
    pygame.draw.rect(s, (30, 10, 10), (12, 7, 1, 2))
    crown_col = C.GOLD if phase == 1 else C.EMBER
    pygame.draw.rect(s, crown_col, (6, 2, 10, 2))
    for x in (6, 9, 12, 15):
        pygame.draw.rect(s, crown_col, (x, 0, 1, 3))
    pygame.draw.rect(s, (60, 60, 80), (2, 12, 3, 5))
    pygame.draw.rect(s, (60, 60, 80), (17, 12, 3, 5))
    pygame.draw.rect(s, (40, 40, 56), (7, 22, 3, 6))
    pygame.draw.rect(s, (40, 40, 56), (12, 22, 3, 6))
    pygame.draw.rect(s, (20, 20, 30), (6, 28, 4, 2))
    pygame.draw.rect(s, (20, 20, 30), (12, 28, 4, 2))
    if flash > 0:
        overlay = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, min(200, flash * 30)))
        s.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return pygame.transform.scale(s, (s.get_width() * SCALE, s.get_height() * SCALE))


def make_boss_sprite(phase=1, flash=0):
    # boss renders 2x player scale so he physically looms
    tint = (255, 170, 150, 255) if phase == 2 else None
    base = assets.get(*assets.TILE_BOSS, scale=SCALE * 2, flip_x=False, tint=tint)
    if base is None:
        return _fallback_boss(phase, flash)

    # overlay a jagged crown within the top band of the sprite (above head)
    out = base.copy()
    w, h = out.get_size()
    crown_col = C.GOLD if phase == 1 else C.EMBER
    band_h = max(4, h // 12)
    band_w = int(w * 0.55)
    bx = (w - band_w) // 2
    by = 0
    pygame.draw.rect(out, crown_col, (bx, by + band_h, band_w, band_h // 2))
    # spikes pointing up within the sprite's top margin
    spike_h = band_h + band_h // 2
    n = 5
    for i in range(n):
        sx = bx + int((i + 0.5) * band_w / n) - band_h // 2
        pygame.draw.polygon(
            out,
            crown_col,
            [(sx, by + band_h), (sx + band_h // 2, by), (sx + band_h, by + band_h)],
        )
    # center jewel
    jewel = C.BLOOD if phase == 2 else C.AZURE
    jx = bx + band_w // 2
    pygame.draw.rect(out, jewel, (jx - band_h // 3, by + band_h, band_h // 2, band_h // 3))

    if flash > 0:
        overlay = pygame.Surface(out.get_size(), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, min(180, flash * 28)))
        out.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return out


def _fallback_sword(facing=1):
    s = pygame.Surface((16, 6), pygame.SRCALPHA)
    pygame.draw.rect(s, (220, 220, 230), (1, 2, 12, 2))
    pygame.draw.rect(s, (255, 255, 255), (1, 2, 12, 1))
    pygame.draw.rect(s, (140, 100, 60), (13, 1, 2, 4))
    pygame.draw.rect(s, (230, 200, 110), (12, 2, 1, 2))
    if facing == -1:
        s = pygame.transform.flip(s, True, False)
    return pygame.transform.scale(s, (s.get_width() * SCALE, s.get_height() * SCALE))


def make_sword(facing=1):
    # Legacy helper - returns a horizontally oriented sword sprite.
    base = assets.get(*assets.TILE_SWORD, scale=SCALE)
    if base is None:
        return _fallback_sword(facing)
    rotated = pygame.transform.rotate(base, -90 if facing == 1 else 90)
    return rotated


def make_sword_pivot():
    """Return a square canvas with the sword positioned so its hilt is at the
    canvas center. Rotating this canvas around its center pivots the blade
    around the hilt, producing a proper swing arc.
    """
    base = assets.get(*assets.TILE_SWORD, scale=SCALE)
    if base is None:
        base = _fallback_sword(1)
        # normalize fallback (horizontal) to pointing up for consistent rotation
        base = pygame.transform.rotate(base, 90)
    bw, bh = base.get_size()
    # canvas big enough to keep the rotated sprite inside after 360deg rotation
    size = int(max(bw, bh) * 2.2)
    canvas = pygame.Surface((size, size), pygame.SRCALPHA)
    # sword blade points up in source. Place so the hilt (bottom of sprite) sits
    # at the canvas center.
    cx = size // 2 - bw // 2
    cy = size // 2 - bh
    canvas.blit(base, (cx, cy))
    return canvas


def _fallback_shard(pulsing=False):
    s = pygame.Surface((10, 12), pygame.SRCALPHA)
    body = C.EMBER if pulsing else C.GOLD
    pts = [(5, 0), (9, 4), (8, 10), (5, 11), (2, 10), (1, 4)]
    pygame.draw.polygon(s, body, pts)
    pygame.draw.polygon(s, (255, 240, 200), [(5, 1), (7, 4), (5, 7), (3, 4)])
    pygame.draw.rect(s, (50, 44, 38), (1, 11, 8, 1))
    return pygame.transform.scale(s, (s.get_width() * SCALE, s.get_height() * SCALE))


def make_shard_sprite(pulsing=False):
    tint = (255, 150, 90, 255) if pulsing else None
    spr = assets.get(*assets.TILE_SHARD, scale=SCALE, tint=tint)
    if spr is None:
        return _fallback_shard(pulsing)
    return spr


def _fallback_floor_tile():
    s = pygame.Surface((16, 16))
    s.fill((34, 30, 44))
    for y in (0, 8):
        pygame.draw.line(s, (48, 44, 60), (0, y), (16, y))
    for x in (0, 8):
        pygame.draw.line(s, (48, 44, 60), (x, 0), (x, 16))
    import random as _r
    rnd = _r.Random(0xC0FFEE)
    for _ in range(8):
        px, py = rnd.randint(1, 14), rnd.randint(1, 14)
        s.set_at((px, py), (60, 54, 70))
    return pygame.transform.scale(s, (s.get_width() * FLOOR_SCALE, s.get_height() * FLOOR_SCALE))


def make_floor_tile():
    spr = assets.get(*assets.TILE_FLOOR, scale=FLOOR_SCALE)
    if spr is None:
        return _fallback_floor_tile()
    return spr


def make_floor_tile_alt():
    spr = assets.get(*assets.TILE_FLOOR_ALT, scale=FLOOR_SCALE)
    if spr is None:
        return _fallback_floor_tile()
    return spr


def make_torch_tile():
    return assets.get(*assets.TILE_TORCH, scale=FLOOR_SCALE)


# ---------- always-procedural sprites (no kenney equivalent) ----------


def make_bolt_sprite():
    s = pygame.Surface((6, 6), pygame.SRCALPHA)
    pygame.draw.circle(s, C.EMBER, (3, 3), 3)
    pygame.draw.circle(s, C.GOLD, (3, 3), 2)
    pygame.draw.circle(s, (255, 250, 220), (3, 3), 1)
    return pygame.transform.scale(s, (s.get_width() * 2, s.get_height() * 2))


def make_heart(filled=True):
    s = pygame.Surface((8, 7), pygame.SRCALPHA)
    col = C.BLOOD if filled else (50, 28, 30)
    pygame.draw.rect(s, col, (1, 1, 2, 2))
    pygame.draw.rect(s, col, (5, 1, 2, 2))
    pygame.draw.rect(s, col, (0, 2, 8, 2))
    pygame.draw.rect(s, col, (1, 4, 6, 1))
    pygame.draw.rect(s, col, (2, 5, 4, 1))
    pygame.draw.rect(s, col, (3, 6, 2, 1))
    if filled:
        s.set_at((2, 2), (255, 180, 180))
    return pygame.transform.scale(s, (s.get_width() * 3, s.get_height() * 3))
