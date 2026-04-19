"""Asset loader for the Kenney Tiny Dungeon CC0 pack.

The pack is a 12 x 11 grid of 16x16 tiles with 1px spacing, at
`assets/kenney_tiny-dungeon/Tilemap/tilemap.png`.

We expose a `get(row, col, scale=3)` helper that returns a cached, scaled
Surface for a given tile. All callers degrade gracefully if the pack is
missing - `loaded()` reports whether the tilesheet was found.
"""
import os
import pygame

TILE = 16
GAP = 1
PACK_REL = os.path.join("assets", "kenney_tiny-dungeon", "Tilemap", "tilemap.png")

_sheet = None
_cache = {}


def _project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _ensure_loaded():
    global _sheet
    if _sheet is not None:
        return _sheet
    path = os.path.join(_project_root(), PACK_REL)
    if not os.path.exists(path):
        return None
    try:
        img = pygame.image.load(path)
        # convert_alpha requires a display; callers guard by checking .loaded()
        if pygame.display.get_surface() is not None:
            img = img.convert_alpha()
        _sheet = img
    except pygame.error:
        _sheet = None
    return _sheet


def loaded():
    return _ensure_loaded() is not None


def raw(row, col):
    """Return the untouched 16x16 tile, or None if the pack is missing."""
    sheet = _ensure_loaded()
    if sheet is None:
        return None
    x = col * (TILE + GAP)
    y = row * (TILE + GAP)
    return sheet.subsurface((x, y, TILE, TILE)).copy()


def get(row, col, scale=3, flip_x=False, tint=None):
    """Return a cached, scaled (and optionally tinted / flipped) tile."""
    key = (row, col, scale, flip_x, tint)
    if key in _cache:
        return _cache[key]
    tile = raw(row, col)
    if tile is None:
        return None
    if tint is not None:
        overlay = pygame.Surface(tile.get_size(), pygame.SRCALPHA)
        overlay.fill(tint)
        tile.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    if flip_x:
        tile = pygame.transform.flip(tile, True, False)
    out = pygame.transform.scale(tile, (TILE * scale, TILE * scale))
    _cache[key] = out
    return out


# ---------- named tile aliases ----------
# (row, col) picks verified against the Tiny Dungeon preview
TILE_PLAYER = (8, 0)            # silver plate knight
TILE_BOSS = (7, 3)              # horned warrior-king
TILE_FLOOR = (4, 0)             # plain sand floor - tiles cleanly
TILE_FLOOR_ALT = (4, 3)         # speckled sand variant
TILE_SHARD = (2, 8)             # green crystal in stone
TILE_SWORD = (8, 7)             # short sword (points up in source)
TILE_SWORD_BIG = (8, 10)        # larger sword for boss sweep flair
TILE_POTION_RED = (9, 7)        # future - healing pickup
TILE_CHEST_CLOSED = (7, 5)
TILE_TORCH = (2, 5)             # torch with flame
