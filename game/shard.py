"""Crown Shards - the strategic heart of the fight.

Attacking a shard drains the boss's Resonance. Shards also pulse a damaging
shockwave that forces the player to keep moving and to pick targets.
"""
import math
import pygame
from . import constants as C
from . import sprites
from .utils import clamp


class Shard:
    _id_counter = 0

    def __init__(self, x, y):
        Shard._id_counter += 1
        self.id = Shard._id_counter
        self.x = float(x)
        self.y = float(y)
        self.hp = C.SHARD_MAX_HP
        self.pulse_timer = C.SHARD_PULSE_INTERVAL
        self.pulse_visual = 0
        self.alive = True
        self.broken_reason = None  # "player" or "decayed"
        self._spr_normal = sprites.make_shard_sprite(pulsing=False)
        self._spr_hot = sprites.make_shard_sprite(pulsing=True)
        self.radius = 14
        self.age = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 14, int(self.y) - 20, 28, 36)

    @property
    def is_charging(self):
        return self.pulse_timer < 50

    def update(self):
        self.age += 1
        self.pulse_timer -= 1
        if self.pulse_visual > 0:
            self.pulse_visual -= 1
        if self.pulse_timer <= 0:
            self.pulse_timer = C.SHARD_PULSE_INTERVAL
            self.pulse_visual = 22
            return "pulse"
        return None

    def take_hit(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False
            self.broken_reason = "player"
            return True
        return False

    def draw(self, surf):
        # telegraph ring when pulse is imminent
        if self.is_charging:
            t = 1.0 - (self.pulse_timer / 50.0)
            r = int(8 + t * C.SHARD_PULSE_RADIUS)
            alpha = int(80 + 120 * t)
            ring = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring, (240, 140, 60, alpha), (r + 2, r + 2), r, 2)
            surf.blit(ring, ring.get_rect(center=(int(self.x), int(self.y))))

        # active pulse visual (fading)
        if self.pulse_visual > 0:
            t = self.pulse_visual / 22.0
            r = int(C.SHARD_PULSE_RADIUS * (1.0 - t) + 20)
            alpha = int(200 * t)
            ring = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring, (255, 180, 80, alpha), (r + 2, r + 2), r, 3)
            surf.blit(ring, ring.get_rect(center=(int(self.x), int(self.y))))

        spr = self._spr_hot if self.is_charging else self._spr_normal
        bob = int(math.sin(self.age * 0.07) * 2)
        surf.blit(spr, spr.get_rect(center=(int(self.x), int(self.y) + bob)))

        # hp pip
        if self.hp < C.SHARD_MAX_HP:
            w = 24
            pct = clamp(self.hp / C.SHARD_MAX_HP, 0.0, 1.0)
            pygame.draw.rect(surf, (30, 20, 20), (int(self.x) - w // 2, int(self.y) - 26, w, 3))
            pygame.draw.rect(surf, C.EMBER, (int(self.x) - w // 2, int(self.y) - 26, int(w * pct), 3))
