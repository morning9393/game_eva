"""Player (Crownbreaker) entity."""
import math
import pygame
from . import constants as C
from . import sprites
from .utils import clamp_to_arena, vec_from_to


class Player:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.hp = C.PLAYER_MAX_HP
        self.facing = 1
        self.iframes = 0
        self.hit_flash = 0
        # attack state machine: idle/windup/active/recover
        self.attack_phase = "idle"
        self.attack_timer = 0
        self.attack_hit_set = set()  # entity ids already hit this swing
        # dash
        self.dash_timer = 0
        self.dash_cd = 0
        self.dash_dx = 0.0
        self.dash_dy = 0.0
        # sprites (cached facings)
        self._spr_r = sprites.make_player_sprite(1)
        self._spr_l = sprites.make_player_sprite(-1)
        self._sword_r = sprites.make_sword(1)
        self._sword_l = sprites.make_sword(-1)
        # visuals
        self.bob = 0.0
        self.moving = False
        self.radius = 14  # collision radius for enemy hits

    # ---------- collision ----------

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 12, int(self.y) - 20, 24, 40)

    def attack_rect(self):
        if self.attack_phase != "active":
            return None
        reach = C.PLAYER_ATTACK_REACH
        if self.facing == 1:
            return pygame.Rect(int(self.x), int(self.y) - 14, reach, 28)
        return pygame.Rect(int(self.x) - reach, int(self.y) - 14, reach, 28)

    # ---------- control ----------

    def update(self, keys, enemies_for_facing=None):
        self.moving = False

        # dash motion overrides normal movement
        if self.dash_timer > 0:
            self.x += self.dash_dx * C.PLAYER_DASH_SPEED
            self.y += self.dash_dy * C.PLAYER_DASH_SPEED
            self.dash_timer -= 1
        else:
            dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
            dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
            if dx or dy:
                self.moving = True
                norm = math.hypot(dx, dy) or 1.0
                # cannot move while swinging sword (rooted commitment)
                speed = C.PLAYER_SPEED if self.attack_phase == "idle" else C.PLAYER_SPEED * 0.35
                self.x += dx / norm * speed
                self.y += dy / norm * speed
                if dx > 0:
                    self.facing = 1
                elif dx < 0:
                    self.facing = -1

        self.x, self.y = clamp_to_arena(self.x, self.y, pad=18)

        # attack FSM
        if self.attack_phase == "windup":
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attack_phase = "active"
                self.attack_timer = C.PLAYER_ATTACK_ACTIVE
                self.attack_hit_set.clear()
        elif self.attack_phase == "active":
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attack_phase = "recover"
                self.attack_timer = C.PLAYER_ATTACK_RECOVER
        elif self.attack_phase == "recover":
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attack_phase = "idle"

        if self.dash_cd > 0:
            self.dash_cd -= 1
        if self.iframes > 0:
            self.iframes -= 1
        if self.hit_flash > 0:
            self.hit_flash -= 1

        if self.moving:
            self.bob += 0.25
        else:
            self.bob *= 0.9

    # ---------- actions ----------

    def try_attack(self):
        if self.attack_phase == "idle":
            self.attack_phase = "windup"
            self.attack_timer = C.PLAYER_ATTACK_WINDUP
            return True
        return False

    def try_dash(self, keys):
        if self.dash_cd > 0 or self.dash_timer > 0:
            return False
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        if dx == 0 and dy == 0:
            dx = self.facing
        n = math.hypot(dx, dy) or 1.0
        self.dash_dx, self.dash_dy = dx / n, dy / n
        self.dash_timer = C.PLAYER_DASH_FRAMES
        self.dash_cd = C.PLAYER_DASH_COOLDOWN
        self.iframes = max(self.iframes, C.PLAYER_DASH_FRAMES + 4)
        return True

    def take_hit(self, dmg=1):
        if self.iframes > 0:
            return False
        self.hp -= dmg
        self.iframes = C.PLAYER_IFRAMES
        self.hit_flash = 10
        return True

    # ---------- rendering ----------

    def draw(self, surf):
        flicker = (self.iframes // 3) % 2 == 1 and self.iframes > C.PLAYER_DASH_FRAMES
        if flicker:
            return
        spr = self._spr_r if self.facing == 1 else self._spr_l
        bob_y = int(math.sin(self.bob) * 2) if self.moving else 0
        rect = spr.get_rect(center=(int(self.x), int(self.y) + bob_y))
        surf.blit(spr, rect)

        # sword during swing
        if self.attack_phase in ("windup", "active", "recover"):
            sw = self._sword_r if self.facing == 1 else self._sword_l
            t = 0.0
            if self.attack_phase == "windup":
                t = -0.3
            elif self.attack_phase == "active":
                t = 1.0 - self.attack_timer / C.PLAYER_ATTACK_ACTIVE
            else:
                t = 1.0 + (1 - self.attack_timer / C.PLAYER_ATTACK_RECOVER) * 0.2
            offset = int(12 + t * 20)
            sx = int(self.x) + self.facing * offset
            sy = int(self.y) - 4
            surf.blit(sw, sw.get_rect(center=(sx, sy)))

        if self.hit_flash > 0:
            overlay = pygame.Surface(spr.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 80, 80, 140))
            surf.blit(overlay, rect)
