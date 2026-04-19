"""The Hollow King - boss with the Resonance mechanic.

Core rule:
  Hitting the boss raises its Resonance. The higher the Resonance, the less
  damage you deal; at max Resonance the boss reflects damage and heals itself.
  You must break Crown Shards on the arena to drain Resonance before you can
  safely burst him down.
"""
import math
import random
import pygame

from . import constants as C
from . import sprites
from .projectile import CrownBolt
from .utils import clamp, vec_from_to, random_point_in_arena, clamp_to_arena


class Boss:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.hp = C.BOSS_MAX_HP
        self.max_hp = C.BOSS_MAX_HP
        self.resonance = 0.0
        self.phase = 1
        self.state = "idle"
        self.state_timer = 60
        self.facing = -1
        self.flash = 0
        self.alive = True
        self.radius = 22
        self.vx = 0.0
        self.vy = 0.0
        self.bob = 0.0
        self.teleport_target = None
        self.attack_hit_player_this_state = False
        self.spawn_shard_request = 0  # count of shards to spawn this frame
        self.bolts_to_fire = []       # list of (dx, dy) for this frame
        self.ring_slam_radius = 0
        self.ring_slam_active = False
        self.ring_slam_hit = False
        self._sprite_cache = {}
        self.intro_timer = 90
        self.enraged_anim = 0

    # ---------- sprites ----------

    def _sprite(self):
        key = (self.phase, 1 if self.flash > 0 else 0)
        if key not in self._sprite_cache:
            self._sprite_cache[key] = sprites.make_boss_sprite(self.phase, flash=1 if self.flash > 0 else 0)
        return self._sprite_cache[key]

    # ---------- collision ----------

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 30, int(self.y) - 44, 60, 84)

    def sweep_hitbox(self):
        if self.state != "sweep":
            return None
        w = 110
        if self.facing == 1:
            return pygame.Rect(int(self.x), int(self.y) - 40, w, 80)
        return pygame.Rect(int(self.x) - w, int(self.y) - 40, w, 80)

    # ---------- resonance logic ----------

    def damage_multiplier(self):
        r = self.resonance
        if r < C.RES_SAFE:
            return 1.0, "safe"
        if r < C.RES_WARN:
            return 0.7, "warn"
        if r < C.RES_DANGER:
            return 0.3, "warn"
        return 0.0, "danger"

    def receive_player_hit(self, damage):
        """Returns dict describing what happened for feedback layer."""
        mult, band = self.damage_multiplier()
        dealt = int(round(damage * mult))
        reflected = 0
        healed = 0
        if band == "danger":
            reflected = 1
            healed = 6
            self.hp = min(self.max_hp, self.hp + healed)
        else:
            self.hp -= dealt
            # Flash is a phase-2 tell: the crown no longer fully absorbs impact.
            if self.phase == 2:
                self.flash = 10
        self.resonance = clamp(self.resonance + C.BOSS_RESONANCE_PER_HIT, 0, C.BOSS_MAX_RESONANCE)
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return {"dealt": dealt, "reflected": reflected, "healed": healed, "band": band}

    def drain_resonance(self, amount):
        self.resonance = clamp(self.resonance - amount, 0, C.BOSS_MAX_RESONANCE)

    # ---------- AI ----------

    def pick_next_state(self, player):
        # intro grace
        if self.intro_timer > 0:
            return "idle", 40

        dist = math.hypot(player.x - self.x, player.y - self.y)
        in_phase2 = self.phase == 2

        if in_phase2:
            pool = [
                ("sweep_telegraph", 3),
                ("bolt_telegraph", 3),
                ("summon_shard", 2),
                ("teleport_out", 3),
                ("ring_slam_telegraph", 2),
            ]
        else:
            # Phase 1: no teleport in the attack pool - teleport is a phase-2 tell.
            pool = [
                ("sweep_telegraph", 3 if dist < 220 else 1),
                ("bolt_telegraph", 3),
                ("summon_shard", 2),
            ]

        total = sum(w for _, w in pool)
        pick = random.uniform(0, total)
        acc = 0
        choice = pool[0][0]
        for name, w in pool:
            acc += w
            if pick <= acc:
                choice = name
                break

        durations = {
            "sweep_telegraph": 34,
            "sweep": 22,
            "bolt_telegraph": 28,
            "bolt_spray": 1,
            "summon_shard": 48,
            "teleport_out": 28,
            "teleport_in": 22,
            "ring_slam_telegraph": 42,
            "ring_slam": 1,
            "idle": 35 if not in_phase2 else 22,
        }
        return choice, durations.get(choice, 30)

    def _enter_state(self, new_state, dur, player):
        self.state = new_state
        self.state_timer = dur
        self.attack_hit_player_this_state = False
        if new_state == "sweep_telegraph":
            self.facing = 1 if player.x >= self.x else -1
            self.vx = self.vy = 0
        elif new_state == "sweep":
            # lunge toward where the player was
            dx, dy, _ = vec_from_to(self.x, self.y, player.x, player.y)
            self.vx = dx * 5.4
            self.vy = dy * 5.4
            self.facing = 1 if dx >= 0 else -1
        elif new_state == "bolt_telegraph":
            self.facing = 1 if player.x >= self.x else -1
            self.vx = self.vy = 0
        elif new_state == "bolt_spray":
            # queue bolts - a narrow spread aimed at player
            dx, dy, _ = vec_from_to(self.x, self.y, player.x, player.y)
            base = math.atan2(dy, dx)
            spread = 5 if self.phase == 2 else 3
            angle_step = 0.22
            self.bolts_to_fire = []
            for i in range(spread):
                a = base + (i - spread // 2) * angle_step
                self.bolts_to_fire.append((math.cos(a), math.sin(a)))
        elif new_state == "summon_shard":
            self.vx = self.vy = 0
        elif new_state == "teleport_out":
            self.vx = self.vy = 0
            # pick a point ~180-280 away from player
            for _ in range(12):
                tx, ty = random_point_in_arena(pad=70)
                if math.hypot(tx - player.x, ty - player.y) > 180:
                    self.teleport_target = (tx, ty)
                    break
            else:
                self.teleport_target = random_point_in_arena(pad=70)
        elif new_state == "teleport_in":
            if self.teleport_target:
                self.x, self.y = self.teleport_target
                self.teleport_target = None
            self.facing = 1 if player.x >= self.x else -1
        elif new_state == "ring_slam_telegraph":
            self.vx = self.vy = 0
            self.ring_slam_radius = 0
            self.ring_slam_active = False
            self.ring_slam_hit = False
        elif new_state == "ring_slam":
            self.ring_slam_active = True
            self.ring_slam_radius = 30
            self.ring_slam_hit = False

    def update(self, player):
        self.bob += 0.06
        if self.intro_timer > 0:
            self.intro_timer -= 1
        if self.flash > 0:
            self.flash -= 1

        # phase transition
        if self.phase == 1 and self.hp <= self.max_hp * C.BOSS_ENRAGE_HP_PCT:
            self.phase = 2
            self.enraged_anim = 60
            # quick reset: clear sprite cache so new phase sprites render
            self._sprite_cache.clear()
            # phase shift always teleports out
            self._enter_state("teleport_out", 30, player)
            return

        if self.enraged_anim > 0:
            self.enraged_anim -= 1

        # passive resonance decay (very small)
        self.resonance = max(0.0, self.resonance - C.BOSS_RESONANCE_DECAY)

        # state logic
        self.state_timer -= 1

        if self.state == "sweep":
            self.x += self.vx
            self.y += self.vy
            self.vx *= 0.82
            self.vy *= 0.82
        elif self.state == "teleport_in":
            pass  # just wait out the reveal frames

        if self.state_timer <= 0:
            self._advance_state(player)

    def _advance_state(self, player):
        prev = self.state
        if prev == "sweep_telegraph":
            self._enter_state("sweep", 22, player)
            return
        if prev == "sweep":
            self._enter_state("idle", 24, player)
            return
        if prev == "bolt_telegraph":
            self._enter_state("bolt_spray", 2, player)
            return
        if prev == "bolt_spray":
            self._enter_state("idle", 28 if self.phase == 2 else 40, player)
            return
        if prev == "summon_shard":
            self.spawn_shard_request += 1 if self.phase == 1 else 2
            self._enter_state("idle", 28, player)
            return
        if prev == "teleport_out":
            self._enter_state("teleport_in", 22, player)
            return
        if prev == "teleport_in":
            self._enter_state("idle", 18, player)
            return
        if prev == "ring_slam_telegraph":
            self._enter_state("ring_slam", 1, player)
            return
        if prev == "ring_slam":
            self._enter_state("idle", 30, player)
            return

        # idle -> choose next
        choice, dur = self.pick_next_state(player)
        self._enter_state(choice, dur, player)

    def ring_slam_tick(self):
        """Called each frame to advance an active ring slam. Returns dict if danger active."""
        if not self.ring_slam_active:
            return None
        self.ring_slam_radius += 7
        if self.ring_slam_radius > 480:
            self.ring_slam_active = False
            return None
        return {"cx": self.x, "cy": self.y, "radius": self.ring_slam_radius}

    # ---------- rendering ----------

    def draw(self, surf):
        spr = self._sprite()
        # alpha fade during teleport
        if self.state == "teleport_out":
            t = 1.0 - (self.state_timer / 28.0)
            alpha = max(0, int(255 * (1 - t)))
            s2 = spr.copy()
            s2.set_alpha(alpha)
            spr = s2
        elif self.state == "teleport_in":
            t = 1.0 - (self.state_timer / 22.0)
            alpha = int(255 * t)
            s2 = spr.copy()
            s2.set_alpha(alpha)
            spr = s2

        bob_y = int(math.sin(self.bob) * 3)
        flip = self.facing == -1
        drawn = pygame.transform.flip(spr, True, False) if flip else spr
        rect = drawn.get_rect(midbottom=(int(self.x), int(self.y) + 44 + bob_y))
        surf.blit(drawn, rect)

        # sweep telegraph arc
        if self.state == "sweep_telegraph":
            t = 1.0 - (self.state_timer / 34.0)
            w = int(90 * t)
            color = (255, 80, 70, int(100 + 120 * t))
            overlay = pygame.Surface((120, 90), pygame.SRCALPHA)
            if self.facing == 1:
                pygame.draw.ellipse(overlay, color, (0, 10, w + 20, 70))
                surf.blit(overlay, (int(self.x), int(self.y) - 45))
            else:
                pygame.draw.ellipse(overlay, color, (100 - w, 10, w + 20, 70))
                surf.blit(overlay, (int(self.x) - 120, int(self.y) - 45))

        # bolt telegraph glow
        if self.state == "bolt_telegraph":
            t = 1.0 - (self.state_timer / 28.0)
            r = int(8 + 28 * t)
            glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (240, 140, 60, int(120 + 80 * t)), (r, r), r)
            surf.blit(glow, glow.get_rect(center=(int(self.x) + self.facing * 20, int(self.y) - 10)))

        # ring slam telegraph flash
        if self.state == "ring_slam_telegraph":
            t = 1.0 - (self.state_timer / 42.0)
            r = int(50 + 90 * t)
            overlay = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(overlay, (220, 80, 70, int(80 + 120 * t)), (r + 2, r + 2), r, 3)
            surf.blit(overlay, overlay.get_rect(center=(int(self.x), int(self.y))))

        # active ring slam wavefront
        if self.ring_slam_active and self.ring_slam_radius > 0:
            r = int(self.ring_slam_radius)
            overlay = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(overlay, (255, 160, 80, 180), (r + 4, r + 4), r, 5)
            pygame.draw.circle(overlay, (255, 220, 140, 90), (r + 4, r + 4), max(1, r - 6), 3)
            surf.blit(overlay, overlay.get_rect(center=(int(self.x), int(self.y))))
