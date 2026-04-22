"""Level 5 - The Echo Lord.

The Echo Lord captures SNAPSHOTS of the player - a frozen copy at a past
position and facing. After a ~1s warning glow, each snapshot fires a
straight sword-slash line along the facing the player had at that moment.

You have to juggle dodging the echo slashes while attacking the boss. Don't
repeat your own paths or you'll keep running into your own slashes. Phase 2
lowers the spawn interval and fires snapshots in small bursts.
"""
import math
import random
import pygame

from . import constants as C
from . import sprites
from .utils import clamp, vec_from_to, clamp_to_arena


class EchoSnapshot:
    """A frozen silhouette of the player at a past (x, y, facing). Glows red
    for EL_WARNING_FRAMES, then fires a slash line for EL_SLASH_FRAMES along
    the captured facing direction.
    """

    def __init__(self, x, y, facing):
        self.x = float(x)
        self.y = float(y)
        self.facing = facing
        self.state = "warning"
        self.timer = C.ECHO_WARNING_FRAMES
        self.alive = True
        self.has_hit = False
        self._sprite = sprites.make_echo_snapshot_sprite()
        self.age = 0

    def update(self):
        self.age += 1
        self.timer -= 1
        if self.state == "warning" and self.timer <= 0:
            self.state = "slash"
            self.timer = C.ECHO_SLASH_FRAMES
            self.has_hit = False
        elif self.state == "slash" and self.timer <= 0:
            self.alive = False

    def slash_rect(self):
        if self.state != "slash":
            return None
        length = C.ECHO_SLASH_LENGTH
        h = C.ECHO_SLASH_WIDTH
        if self.facing == 1:
            return pygame.Rect(int(self.x), int(self.y) - h // 2, length, h)
        return pygame.Rect(int(self.x) - length, int(self.y) - h // 2, length, h)

    def draw(self, surf):
        # silhouette
        spr = self._sprite
        drawn = pygame.transform.flip(spr, True, False) if self.facing == -1 else spr
        rect = drawn.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(drawn, rect)
        if self.state == "warning":
            raw_t = 1.0 - self.timer / C.ECHO_WARNING_FRAMES
            t = max(0.0, min(1.0, raw_t))
            # red pulsing warning ring + telegraph line of intended slash
            pulse = (math.sin(self.age * 0.35) + 1) * 0.5
            ring_r = int(18 + 8 * pulse)
            tmp = pygame.Surface((ring_r * 2 + 8, ring_r * 2 + 8), pygame.SRCALPHA)
            alpha = max(0, min(255, int(150 + 100 * t)))
            pygame.draw.circle(
                tmp, (255, 80, 100, alpha),
                (ring_r + 4, ring_r + 4), ring_r, 2,
            )
            surf.blit(tmp, tmp.get_rect(center=(int(self.x), int(self.y))))
            # telegraph line showing where the slash will fire
            length = C.ECHO_SLASH_LENGTH
            tip_x = self.x + self.facing * length
            tip_y = self.y
            line = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            line_a = max(0, min(255, int(80 + 120 * t)))
            pygame.draw.line(
                line, (255, 100, 120, line_a),
                (int(self.x), int(self.y)), (int(tip_x), int(tip_y)),
                max(2, int(C.ECHO_SLASH_WIDTH * t * 0.4)),
            )
            surf.blit(line, (0, 0))
        else:
            # active slash - bright red line with bloom
            length = C.ECHO_SLASH_LENGTH
            tip_x = self.x + self.facing * length
            tip_y = self.y
            w = C.ECHO_SLASH_WIDTH
            t = max(0.0, min(1.0, self.timer / C.ECHO_SLASH_FRAMES))
            alpha = max(0, min(255, int(255 * t)))
            tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.line(
                tmp, (255, 60, 90, alpha),
                (int(self.x), int(self.y)), (int(tip_x), int(tip_y)), w,
            )
            pygame.draw.line(
                tmp, (255, 180, 180, alpha),
                (int(self.x), int(self.y)), (int(tip_x), int(tip_y)), w // 2,
            )
            pygame.draw.line(
                tmp, (255, 255, 255, alpha),
                (int(self.x), int(self.y)), (int(tip_x), int(tip_y)), 2,
            )
            surf.blit(tmp, (0, 0))


class EchoLord:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.hp = C.ECHO_LORD_HP
        self.max_hp = C.ECHO_LORD_HP
        self.alive = True
        self.phase = 1
        self.facing = -1
        self.flash = 0
        self.bob = 0.0
        self.intro_timer = 90
        self.enraged_anim = 0
        self.state = "idle"
        self.state_timer = 90
        self.radius = 22
        self._sprite_cache = {}
        self.spawn_timer = C.ECHO_SPAWN_INTERVAL_P1
        self.echo_spawn_request = 0    # count of snapshots to spawn this frame
        self.cascade_request = False   # True -> spawn cascade-chain of echoes
        self.memory_surge_timer = 0    # countdown during Memory Surge telegraph
        self.memory_surge_active = False  # transient flag - game fires surge next frame
        self.attack_cooldown = 150
        self._secondary_cooldown = 260

    def _sprite(self):
        key = (self.phase, 1 if self.flash > 0 else 0)
        if key not in self._sprite_cache:
            self._sprite_cache[key] = sprites.make_echo_lord_sprite(self.phase)
        return self._sprite_cache[key]

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 28, int(self.y) - 44, 56, 84)

    def sweep_hitbox(self):
        return None

    def receive_player_hit(self, damage):
        self.hp -= damage
        if self.phase == 2:
            self.flash = 10
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return {"dealt": damage, "band": "safe"}

    def update(self, player):
        self.bob += 0.06
        if self.intro_timer > 0:
            self.intro_timer -= 1
        if self.flash > 0:
            self.flash -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if self._secondary_cooldown > 0:
            self._secondary_cooldown -= 1
        if self.memory_surge_timer > 0:
            self.memory_surge_timer -= 1
            if self.memory_surge_timer <= 0:
                self.memory_surge_active = True

        # phase transition
        if self.phase == 1 and self.hp <= self.max_hp * C.ECHO_LORD_ENRAGE_HP_PCT:
            self.phase = 2
            self.enraged_anim = 60
            self._sprite_cache.clear()
        if self.enraged_anim > 0:
            self.enraged_anim -= 1

        # drift toward player
        dx, dy, dist = vec_from_to(self.x, self.y, player.x, player.y)
        if dist > 200:
            self.x += dx * 1.1
            self.y += dy * 1.1
            self.facing = 1 if dx >= 0 else -1
        self.x, self.y = clamp_to_arena(self.x, self.y, pad=40)

        # spawn snapshots from player history
        if self.intro_timer == 0:
            self.spawn_timer -= 1
            interval = C.ECHO_SPAWN_INTERVAL_P2 if self.phase == 2 else C.ECHO_SPAWN_INTERVAL_P1
            if self.spawn_timer <= 0:
                self.spawn_timer = interval
                # spawn 1 (phase 1) or a small burst (phase 2)
                burst = random.choice([1, 2]) if self.phase == 2 else 1
                self.echo_spawn_request += burst

            # secondary skills on their own slower cadence
            if self._secondary_cooldown <= 0 and self.memory_surge_timer == 0:
                if random.random() < 0.55:
                    self.cascade_request = True
                else:
                    # start Memory Surge telegraph; Game fires it when active
                    self.memory_surge_timer = C.MEMORY_SURGE_TELEGRAPH
                self._secondary_cooldown = 260 if self.phase == 2 else 360

    def draw_memory_surge_warning(self, surf):
        """Screen-edge dark vignette + boss-outline glow during surge telegraph."""
        if self.memory_surge_timer <= 0:
            return
        t = 1.0 - self.memory_surge_timer / C.MEMORY_SURGE_TELEGRAPH
        # vignette frame
        vw = surf.get_width(); vh = surf.get_height()
        tmp = pygame.Surface((vw, vh), pygame.SRCALPHA)
        pygame.draw.rect(tmp, (255, 80, 120, int(120 * t)), tmp.get_rect(), int(6 + 8 * t))
        # boss aura
        r = int(40 + 16 * t)
        aura = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(aura, (255, 120, 160, int(140 * t)), (r + 4, r + 4), r, 3)
        pygame.draw.circle(aura, (255, 200, 220, int(180 * t)), (r + 4, r + 4), max(2, r - 10))
        tmp.blit(aura, aura.get_rect(center=(int(self.x), int(self.y) - 20)))
        surf.blit(tmp, (0, 0))

    def draw(self, surf):
        spr = self._sprite()
        bob_y = int(math.sin(self.bob) * 3)
        flip = self.facing == -1
        drawn = pygame.transform.flip(spr, True, False) if flip else spr
        rect = drawn.get_rect(midbottom=(int(self.x), int(self.y) + 44 + bob_y))
        if self.flash > 0:
            intensity = min(180, self.flash * 28)
            flashed = drawn.copy()
            overlay = pygame.Surface(flashed.get_size(), pygame.SRCALPHA)
            overlay.fill((intensity, intensity, intensity, 255))
            flashed.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            surf.blit(flashed, rect)
        else:
            surf.blit(drawn, rect)
        # telegraph for Memory Surge (drawn last so it lands on top)
        if self.memory_surge_timer > 0:
            self.draw_memory_surge_warning(surf)
