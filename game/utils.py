"""Small math / helper utilities."""
import math
import random
from . import constants as C


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def vec_from_to(ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    d = math.hypot(dx, dy) or 1.0
    return dx / d, dy / d, d


def inside_arena(x, y, pad=0):
    return (
        C.ARENA_X + pad <= x <= C.ARENA_X + C.ARENA_W - pad
        and C.ARENA_Y + pad <= y <= C.ARENA_Y + C.ARENA_H - pad
    )


def clamp_to_arena(x, y, pad=0):
    return (
        clamp(x, C.ARENA_X + pad, C.ARENA_X + C.ARENA_W - pad),
        clamp(y, C.ARENA_Y + pad, C.ARENA_Y + C.ARENA_H - pad),
    )


def random_point_in_arena(pad=30):
    return (
        random.randint(C.ARENA_X + pad, C.ARENA_X + C.ARENA_W - pad),
        random.randint(C.ARENA_Y + pad, C.ARENA_Y + C.ARENA_H - pad),
    )


def circle_rect_collide(cx, cy, r, rect):
    nearest_x = clamp(cx, rect.left, rect.right)
    nearest_y = clamp(cy, rect.top, rect.bottom)
    return (cx - nearest_x) ** 2 + (cy - nearest_y) ** 2 <= r * r


def ease_out(t):
    return 1 - (1 - t) * (1 - t)
