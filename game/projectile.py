"""Projectiles fired by the boss."""
import math
import pygame
from . import constants as C
from . import sprites
from .utils import inside_arena


class CrownBolt:
    def __init__(self, x, y, dx, dy, speed=C.CROWN_BOLT_SPEED):
        n = math.hypot(dx, dy) or 1.0
        self.x = float(x)
        self.y = float(y)
        self.vx = dx / n * speed
        self.vy = dy / n * speed
        self.alive = True
        self.life = 240
        self._spr = sprites.make_bolt_sprite()
        self.radius = 7

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.life <= 0 or not inside_arena(self.x, self.y, pad=-8):
            self.alive = False

    def draw(self, surf):
        surf.blit(self._spr, self._spr.get_rect(center=(int(self.x), int(self.y))))
