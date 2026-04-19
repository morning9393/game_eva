"""Crown Shards - the strategic heart of the fight.

Attacking a shard drains the boss's Resonance. Shards also pulse a damaging
shockwave that forces the player to keep moving and to pick targets.
"""
import math
import pygame
from . import constants as C
from . import sprites
from .utils import clamp

CHARGE_WINDOW = 70       # frames before pulse in which the telegraph is visible
PULSE_VISUAL_LEN = 32    # frames the active shockwave is drawn


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
        return self.pulse_timer < CHARGE_WINDOW

    def update(self):
        self.age += 1
        self.pulse_timer -= 1
        if self.pulse_visual > 0:
            self.pulse_visual -= 1
        if self.pulse_timer <= 0:
            self.pulse_timer = C.SHARD_PULSE_INTERVAL
            self.pulse_visual = PULSE_VISUAL_LEN
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
        # telegraph: bright thick pulsing ring + flashing exclamation marker
        if self.is_charging:
            t = 1.0 - (self.pulse_timer / float(CHARGE_WINDOW))
            # outer ring grows and brightens as pulse nears
            r = int(14 + t * C.SHARD_PULSE_RADIUS)
            alpha = int(120 + 130 * t)
            thickness = 4 if t < 0.7 else 6
            ring = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(ring, (255, 150, 70, alpha), (r + 4, r + 4), r, thickness)
            # inner ring for emphasis
            inner_r = max(6, int(r * 0.7))
            pygame.draw.circle(
                ring, (255, 220, 140, int(80 + 100 * t)), (r + 4, r + 4), inner_r, 2
            )
            surf.blit(ring, ring.get_rect(center=(int(self.x), int(self.y))))
            # strobing exclamation above the shard - only when close to firing
            if t > 0.4 and (self.age // 6) % 2 == 0:
                mark = pygame.Surface((14, 22), pygame.SRCALPHA)
                pygame.draw.rect(mark, (255, 60, 60), (5, 0, 4, 12))
                pygame.draw.rect(mark, (255, 60, 60), (5, 15, 4, 4))
                pygame.draw.rect(mark, (255, 220, 140), (6, 1, 2, 10))
                surf.blit(mark, mark.get_rect(midbottom=(int(self.x), int(self.y) - 28)))

        # active pulse: two chasing ring outlines, no filled disc
        if self.pulse_visual > 0:
            t = 1.0 - (self.pulse_visual / float(PULSE_VISUAL_LEN))  # 0 -> 1
            max_r = C.SHARD_PULSE_RADIUS + 30
            r = int(20 + max_r * t)
            alpha = int(240 * (1.0 - t))
            ring = pygame.Surface((r * 2 + 12, r * 2 + 12), pygame.SRCALPHA)
            # bright leading edge
            pygame.draw.circle(ring, (255, 200, 110, alpha), (r + 6, r + 6), r, 6)
            # warm inner echo (trailing ring outline only)
            inner = max(4, r - 14)
            pygame.draw.circle(ring, (255, 140, 70, int(alpha * 0.6)), (r + 6, r + 6), inner, 4)
            surf.blit(ring, ring.get_rect(center=(int(self.x), int(self.y))))

        spr = self._spr_hot if self.is_charging else self._spr_normal
        bob = int(math.sin(self.age * 0.07) * 2)
        surf.blit(spr, spr.get_rect(center=(int(self.x), int(self.y) + bob)))

        # HP bar: only meaningful when damaged or when the shard is charging
        if self.hp < C.SHARD_MAX_HP or self.is_charging:
            self._draw_hp_bar(surf)

    def _draw_hp_bar(self, surf):
        w = 46
        h = 7
        bx = int(self.x) - w // 2
        by = int(self.y) - 34
        # drop shadow
        pygame.draw.rect(surf, (0, 0, 0, 180), (bx + 1, by + 1, w, h))
        # dark backdrop
        pygame.draw.rect(surf, (30, 18, 18), (bx, by, w, h))
        # thin outline
        pygame.draw.rect(surf, (90, 60, 40), (bx, by, w, h), 1)
        pct = clamp(self.hp / float(C.SHARD_MAX_HP), 0.0, 1.0)
        fill = max(1, int((w - 2) * pct))
        # colored fill: ember when charging, otherwise gold
        color = C.EMBER if self.is_charging else C.GOLD
        pygame.draw.rect(surf, color, (bx + 1, by + 1, fill, h - 2))
        # highlight stripe along top of fill for readability
        pygame.draw.line(
            surf, (255, 240, 180), (bx + 1, by + 1), (bx + fill, by + 1)
        )
