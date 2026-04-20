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


def make_floor_tile_level2():
    # Plain sand tinted strongly toward cool blue-grey stone.
    spr = assets.get(*assets.TILE_FLOOR, scale=FLOOR_SCALE, tint=(95, 125, 170, 255))
    if spr is None:
        return _fallback_floor_tile()
    return spr


def make_floor_tile_level2_alt():
    # Darker variant for irregular stone mottling.
    spr = assets.get(*assets.TILE_FLOOR_ALT, scale=FLOOR_SCALE, tint=(75, 100, 140, 255))
    if spr is None:
        return _fallback_floor_tile()
    return spr


def make_torch_tile():
    return assets.get(*assets.TILE_TORCH, scale=FLOOR_SCALE)


# ---------- procedural arena decor ----------


def make_throne_sprite():
    s = pygame.Surface((18, 26), pygame.SRCALPHA)
    # backrest
    pygame.draw.rect(s, (92, 80, 104), (3, 0, 12, 18))
    pygame.draw.rect(s, (128, 114, 142), (3, 0, 12, 2))        # top edge
    pygame.draw.rect(s, (68, 56, 82), (2, 1, 1, 16))           # left shadow
    pygame.draw.rect(s, (68, 56, 82), (15, 1, 1, 16))          # right shadow
    # gothic spikes
    pygame.draw.polygon(s, (108, 94, 120), [(3, 0), (5, -3), (7, 0)])
    pygame.draw.polygon(s, (108, 94, 120), [(11, 0), (13, -3), (15, 0)])
    # seat cushion + armrests
    pygame.draw.rect(s, (104, 90, 116), (1, 14, 16, 7))
    pygame.draw.rect(s, (136, 120, 150), (1, 14, 16, 1))
    pygame.draw.rect(s, (68, 56, 82), (0, 16, 2, 5))
    pygame.draw.rect(s, (68, 56, 82), (16, 16, 2, 5))
    # base platform
    pygame.draw.rect(s, (72, 60, 86), (0, 22, 18, 4))
    pygame.draw.rect(s, (48, 38, 58), (0, 25, 18, 1))
    # gem inlaid on backrest
    pygame.draw.rect(s, C.BLOOD, (8, 5, 2, 3))
    s.set_at((8, 5), (255, 180, 180))
    # gold trim
    pygame.draw.rect(s, C.GOLD, (3, 0, 2, 1))
    pygame.draw.rect(s, C.GOLD, (13, 0, 2, 1))
    pygame.draw.rect(s, C.GOLD, (1, 14, 16, 1))
    return pygame.transform.scale(s, (s.get_width() * SCALE, s.get_height() * SCALE))


def make_pillar_sprite():
    s = pygame.Surface((12, 44), pygame.SRCALPHA)
    # base
    pygame.draw.rect(s, (80, 70, 92), (0, 40, 12, 4))
    pygame.draw.rect(s, (50, 40, 62), (0, 43, 12, 1))
    # shaft
    pygame.draw.rect(s, (108, 96, 122), (2, 5, 8, 35))
    pygame.draw.rect(s, (80, 70, 92), (2, 5, 1, 35))            # left shadow
    pygame.draw.rect(s, (140, 128, 154), (9, 5, 1, 35))         # right highlight
    # fluting (vertical grooves)
    for gx in (4, 7):
        pygame.draw.line(s, (80, 70, 92), (gx, 6), (gx, 39))
    # capital
    pygame.draw.rect(s, (128, 116, 142), (1, 1, 10, 4))
    pygame.draw.rect(s, (160, 146, 176), (1, 1, 10, 1))
    pygame.draw.rect(s, (88, 76, 102), (1, 4, 10, 1))
    # subtle crack for ancient feel
    s.set_at((6, 15), (60, 50, 72))
    s.set_at((6, 16), (60, 50, 72))
    s.set_at((7, 17), (60, 50, 72))
    return pygame.transform.scale(s, (s.get_width() * SCALE, s.get_height() * SCALE))


def make_rubble_sprite(variant=0):
    s = pygame.Surface((10, 6), pygame.SRCALPHA)
    if variant % 3 == 0:
        pygame.draw.rect(s, (96, 82, 108), (1, 2, 4, 3))
        pygame.draw.rect(s, (128, 114, 142), (1, 2, 4, 1))
        pygame.draw.rect(s, (72, 60, 84), (6, 3, 3, 2))
    elif variant % 3 == 1:
        pygame.draw.rect(s, (80, 68, 92), (2, 1, 3, 4))
        pygame.draw.rect(s, (112, 98, 124), (2, 1, 3, 1))
        pygame.draw.rect(s, (60, 48, 70), (5, 3, 4, 2))
    else:
        pygame.draw.rect(s, (104, 90, 116), (0, 3, 5, 2))
        pygame.draw.rect(s, (72, 60, 84), (5, 2, 4, 3))
        pygame.draw.rect(s, (132, 118, 146), (5, 2, 4, 1))
    return pygame.transform.scale(s, (s.get_width() * SCALE, s.get_height() * SCALE))


def make_mirrorwright_sprite(phase=1, flash=0):
    """Level 2 boss. White-haired mage tinted silver-blue for phase 1,
    violet-shifted for phase 2, with a procedural mirror crown on top."""
    tint = (180, 210, 250, 255) if phase == 1 else (220, 170, 210, 255)
    base = assets.get(*assets.TILE_MIRRORWRIGHT, scale=SCALE * 2, tint=tint)
    if base is None:
        # fallback: reuse the hollow-king procedural fallback but differently colored
        return make_boss_sprite(phase, flash)

    out = base.copy()
    w, h = out.get_size()
    # floating mirror shards ringing the head like a crown
    band_w = int(w * 0.5)
    band_h = max(4, h // 14)
    bx = (w - band_w) // 2
    # a thin silver coronet
    silver = (220, 230, 245)
    accent = (150, 180, 220) if phase == 1 else (200, 120, 160)
    pygame.draw.rect(out, silver, (bx, band_h, band_w, band_h // 2))
    # upright mirror shard triangles
    n = 5
    for i in range(n):
        sx = bx + int((i + 0.5) * band_w / n) - band_h // 2
        pygame.draw.polygon(
            out, silver,
            [(sx, band_h), (sx + band_h // 2, 0), (sx + band_h, band_h)],
        )
        # inner tint
        pygame.draw.polygon(
            out, accent,
            [(sx + 1, band_h - 1),
             (sx + band_h // 2, max(0, band_h // 4)),
             (sx + band_h - 1, band_h - 1)],
        )
    # central mirror gem (oval)
    jew_x = bx + band_w // 2
    pygame.draw.ellipse(out, accent, (jew_x - band_h, band_h + 1, band_h * 2, band_h))
    pygame.draw.ellipse(out, (255, 255, 255), (jew_x - band_h + 2, band_h + 2, band_h * 2 - 4, band_h - 2), 1)

    if flash > 0:
        overlay = pygame.Surface(out.get_size(), pygame.SRCALPHA)
        overlay.fill((220, 240, 255, min(180, flash * 24)))
        out.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return out


def make_phantom_sprite():
    """Ghostly silver-blue silhouette of the player, used for phantom reflections."""
    base = assets.get(*assets.TILE_PLAYER, scale=SCALE, tint=(140, 180, 230, 255))
    if base is None:
        base = _fallback_player(1)
    out = base.copy()
    out.set_alpha(170)
    return out


def make_mirror_shard_sprite():
    """Small broken mirror-shard decor prop used in the Mirrorwright room."""
    s = pygame.Surface((10, 12), pygame.SRCALPHA)
    pygame.draw.polygon(s, (210, 225, 240), [(5, 0), (9, 5), (6, 11), (2, 8), (1, 3)])
    pygame.draw.polygon(s, (240, 250, 255), [(5, 1), (7, 4), (5, 7), (3, 4)])
    pygame.draw.line(s, (150, 170, 200), (2, 3), (8, 10), 1)
    pygame.draw.rect(s, (60, 60, 78), (1, 11, 8, 1))
    return pygame.transform.scale(s, (s.get_width() * SCALE, s.get_height() * SCALE))


def make_vanity_sprite():
    """Centerpiece for level 2 - a cracked standing mirror on a stone base."""
    s = pygame.Surface((20, 30), pygame.SRCALPHA)
    # stone base
    pygame.draw.rect(s, (76, 74, 92), (2, 24, 16, 6))
    pygame.draw.rect(s, (50, 48, 64), (2, 29, 16, 1))
    # mirror frame
    pygame.draw.rect(s, (180, 150, 80), (2, 2, 16, 24))
    pygame.draw.rect(s, (230, 200, 110), (2, 2, 16, 2))
    pygame.draw.rect(s, (140, 110, 50), (2, 23, 16, 2))
    # reflective glass
    pygame.draw.rect(s, (190, 215, 240), (4, 4, 12, 20))
    # crack pattern
    pygame.draw.line(s, (100, 120, 150), (4, 10), (10, 15), 1)
    pygame.draw.line(s, (100, 120, 150), (10, 15), (8, 22), 1)
    pygame.draw.line(s, (100, 120, 150), (10, 15), (15, 9), 1)
    # faint ghost reflection
    pygame.draw.rect(s, (230, 240, 250), (7, 6, 2, 3))
    pygame.draw.rect(s, (230, 240, 250), (13, 14, 1, 2))
    return pygame.transform.scale(s, (s.get_width() * SCALE, s.get_height() * SCALE))


def make_brazier_sprite():
    s = pygame.Surface((10, 12), pygame.SRCALPHA)
    # bowl
    pygame.draw.rect(s, (64, 50, 40), (1, 7, 8, 4))
    pygame.draw.rect(s, (100, 80, 60), (1, 7, 8, 1))
    pygame.draw.rect(s, (44, 32, 24), (0, 10, 10, 1))
    # base pole
    pygame.draw.rect(s, (52, 40, 30), (4, 11, 2, 1))
    # flame core (static portion - animated particles added on top)
    pygame.draw.rect(s, C.EMBER, (3, 3, 4, 5))
    pygame.draw.rect(s, C.GOLD, (4, 4, 2, 3))
    pygame.draw.rect(s, (255, 250, 220), (4, 5, 2, 1))
    return pygame.transform.scale(s, (s.get_width() * SCALE, s.get_height() * SCALE))


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
