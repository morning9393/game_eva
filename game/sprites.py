"""Procedurally drawn pixel-art sprites.

Each sprite is drawn to a small surface then scaled up with nearest-neighbor
for a pixelated look. No external assets required.
"""
import pygame
from . import constants as C

SCALE = 3


def _pixelate(surf, scale=SCALE):
    w, h = surf.get_size()
    return pygame.transform.scale(surf, (w * scale, h * scale))


def make_player_sprite(facing=1):
    """Small hooded crownbreaker. facing: 1 right, -1 left."""
    s = pygame.Surface((12, 14), pygame.SRCALPHA)
    # cloak
    pygame.draw.rect(s, (40, 48, 72), (2, 6, 8, 7))
    pygame.draw.rect(s, (60, 72, 100), (3, 7, 6, 5))
    # body / tunic
    pygame.draw.rect(s, (110, 90, 70), (3, 10, 6, 3))
    # head / hood
    pygame.draw.rect(s, (30, 34, 52), (3, 2, 6, 5))
    pygame.draw.rect(s, (210, 180, 150), (4, 5, 4, 2))  # face
    # eye glint
    eye_x = 6 if facing == 1 else 5
    s.set_at((eye_x, 5), (255, 255, 255))
    # belt
    pygame.draw.rect(s, (80, 60, 44), (3, 9, 6, 1))
    # feet
    pygame.draw.rect(s, (30, 30, 40), (3, 13, 2, 1))
    pygame.draw.rect(s, (30, 30, 40), (7, 13, 2, 1))
    if facing == -1:
        s = pygame.transform.flip(s, True, False)
    return _pixelate(s)


def make_sword(facing=1):
    s = pygame.Surface((16, 6), pygame.SRCALPHA)
    pygame.draw.rect(s, (220, 220, 230), (1, 2, 12, 2))
    pygame.draw.rect(s, (255, 255, 255), (1, 2, 12, 1))
    pygame.draw.rect(s, (140, 100, 60), (13, 1, 2, 4))  # hilt
    pygame.draw.rect(s, (230, 200, 110), (12, 2, 1, 2))  # guard
    if facing == -1:
        s = pygame.transform.flip(s, True, False)
    return _pixelate(s)


def make_boss_sprite(phase=1, flash=0):
    """The Hollow King — a tall, gaunt armored figure with a jagged crown."""
    s = pygame.Surface((22, 30), pygame.SRCALPHA)
    # cloak / mantle
    cloak = (36, 16, 44) if phase == 1 else (70, 18, 30)
    pygame.draw.rect(s, cloak, (2, 10, 18, 18))
    pygame.draw.rect(s, (min(cloak[0] + 20, 255), min(cloak[1] + 20, 255), min(cloak[2] + 20, 255)), (3, 11, 16, 16))
    # armor chest
    pygame.draw.rect(s, (80, 80, 100), (5, 12, 12, 10))
    pygame.draw.rect(s, (120, 120, 140), (5, 12, 12, 2))
    # gem in chest
    pygame.draw.rect(s, C.GOLD, (10, 15, 2, 2))
    pygame.draw.rect(s, C.EMBER if phase == 2 else C.AZURE, (10, 16, 2, 1))
    # head (skull-like)
    pygame.draw.rect(s, (200, 190, 170), (7, 4, 8, 7))
    pygame.draw.rect(s, (30, 10, 10), (9, 7, 1, 2))  # eye
    pygame.draw.rect(s, (30, 10, 10), (12, 7, 1, 2))  # eye
    # crown (jagged)
    crown_col = C.GOLD if phase == 1 else C.EMBER
    pygame.draw.rect(s, crown_col, (6, 2, 10, 2))
    for x in (6, 9, 12, 15):
        pygame.draw.rect(s, crown_col, (x, 0, 1, 3))
    # pauldrons
    pygame.draw.rect(s, (60, 60, 80), (2, 12, 3, 5))
    pygame.draw.rect(s, (60, 60, 80), (17, 12, 3, 5))
    # legs
    pygame.draw.rect(s, (40, 40, 56), (7, 22, 3, 6))
    pygame.draw.rect(s, (40, 40, 56), (12, 22, 3, 6))
    # feet
    pygame.draw.rect(s, (20, 20, 30), (6, 28, 4, 2))
    pygame.draw.rect(s, (20, 20, 30), (12, 28, 4, 2))

    if flash > 0:
        overlay = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, min(200, flash * 30)))
        s.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return _pixelate(s)


def make_shard_sprite(pulsing=False):
    s = pygame.Surface((10, 12), pygame.SRCALPHA)
    body = C.EMBER if pulsing else C.GOLD
    # jagged crystal shape
    pts = [(5, 0), (9, 4), (8, 10), (5, 11), (2, 10), (1, 4)]
    pygame.draw.polygon(s, body, pts)
    pygame.draw.polygon(s, (255, 240, 200), [(5, 1), (7, 4), (5, 7), (3, 4)])
    # base rubble
    pygame.draw.rect(s, (50, 44, 38), (1, 11, 8, 1))
    return _pixelate(s)


def make_bolt_sprite():
    s = pygame.Surface((6, 6), pygame.SRCALPHA)
    pygame.draw.circle(s, C.EMBER, (3, 3), 3)
    pygame.draw.circle(s, C.GOLD, (3, 3), 2)
    pygame.draw.circle(s, (255, 250, 220), (3, 3), 1)
    return _pixelate(s, 2)


def make_heart(filled=True):
    s = pygame.Surface((8, 7), pygame.SRCALPHA)
    col = C.BLOOD if filled else (50, 28, 30)
    # heart shape
    pygame.draw.rect(s, col, (1, 1, 2, 2))
    pygame.draw.rect(s, col, (5, 1, 2, 2))
    pygame.draw.rect(s, col, (0, 2, 8, 2))
    pygame.draw.rect(s, col, (1, 4, 6, 1))
    pygame.draw.rect(s, col, (2, 5, 4, 1))
    pygame.draw.rect(s, col, (3, 6, 2, 1))
    if filled:
        s.set_at((2, 2), (255, 180, 180))
    return _pixelate(s, 3)


def make_floor_tile():
    """Arena floor tile - cracked cathedral stone."""
    s = pygame.Surface((16, 16))
    s.fill((34, 30, 44))
    for y in (0, 8):
        pygame.draw.line(s, (48, 44, 60), (0, y), (16, y))
    for x in (0, 8):
        pygame.draw.line(s, (48, 44, 60), (x, 0), (x, 16))
    # speckle
    import random as _r
    rnd = _r.Random(0xC0FFEE)
    for _ in range(8):
        px, py = rnd.randint(1, 14), rnd.randint(1, 14)
        s.set_at((px, py), (60, 54, 70))
    return _pixelate(s, 2)
