"""Level 4 - The Fate-Weaver.

Four stone anchors sit at the arena midpoints. Every time you hit the
Weaver, a fate-thread is woven between her and the nearest anchor - threads
are visible, persistent barriers that also grant her damage resistance.

- Break individual threads by attacking them to strip her defense.
- She can PULL along a live thread: fast dash toward an anchor, damaging
  anything standing on the thread line.
- Phase 2 at 50% HP: new threads anchor to *you* instead of stone anchors,
  constraining your movement.
"""
import math
import random
import pygame

from . import constants as C
from . import sprites
from .utils import clamp, vec_from_to, clamp_to_arena


class Anchor:
    __slots__ = ("x", "y", "sprite", "radius")

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.sprite = sprites.make_anchor_sprite()
        self.radius = 14

    def draw(self, surf):
        rect = self.sprite.get_rect(midbottom=(int(self.x), int(self.y)))
        surf.blit(self.sprite, rect)


class Thread:
    """A fate-thread between two points. Lives until its HP is depleted by
    the player's sword. Grants the Weaver damage resistance while alive.
    """

    def __init__(self, ax, ay, bx, by, target_player=False):
        self.ax = float(ax)
        self.ay = float(ay)
        self.bx = float(bx)
        self.by = float(by)
        self.hp = C.WEAVER_THREAD_HP
        self.alive = True
        self.player_anchored = target_player
        self.age = 0

    def closest_point(self, px, py):
        """Project (px, py) onto this segment, return (cx, cy, distance)."""
        dx = self.bx - self.ax
        dy = self.by - self.ay
        L2 = dx * dx + dy * dy
        if L2 == 0:
            return self.ax, self.ay, math.hypot(px - self.ax, py - self.ay)
        t = max(0.0, min(1.0, ((px - self.ax) * dx + (py - self.ay) * dy) / L2))
        cx = self.ax + t * dx
        cy = self.ay + t * dy
        return cx, cy, math.hypot(px - cx, py - cy)

    def distance_to(self, px, py):
        return self.closest_point(px, py)[2]

    def intersects_rect(self, rect):
        """Approximate - check corners' distances, plus a few samples along."""
        # sample points along segment
        for k in range(12):
            t = k / 11.0
            px = self.ax + (self.bx - self.ax) * t
            py = self.ay + (self.by - self.ay) * t
            if rect.collidepoint(px, py):
                return True
        return False

    def take_hit(self, damage):
        self.hp -= damage
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def update(self, weaver):
        self.age += 1
        # threads anchored to weaver follow her
        if not self.player_anchored:
            # 'a' end is weaver, 'b' end is stone anchor
            self.ax = weaver.x
            self.ay = weaver.y - 20

    def draw(self, surf):
        # main thread body - silk color depending on type
        core_col = (220, 180, 240) if not self.player_anchored else (240, 140, 120)
        dark_col = (130, 80, 160) if not self.player_anchored else (160, 70, 60)
        alive_pct = max(0.1, self.hp / C.WEAVER_THREAD_HP)
        # pulsing animation
        pulse = (math.sin(self.age * 0.2) + 1) * 0.5
        thickness = max(2, int(3 + pulse * 2))
        tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.line(
            tmp, (*dark_col, int(200 * alive_pct)),
            (int(self.ax), int(self.ay)), (int(self.bx), int(self.by)),
            thickness + 2,
        )
        pygame.draw.line(
            tmp, (*core_col, int(255 * alive_pct)),
            (int(self.ax), int(self.ay)), (int(self.bx), int(self.by)),
            thickness,
        )
        surf.blit(tmp, (0, 0))


class FatedStrike:
    """Violet foresight-strike. A mark is placed on the player's location;
    after FATED_STRIKE_DELAY frames a circular impact drops there.
    """

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.timer = C.FATED_STRIKE_DELAY
        self.phase = "warning"
        self.alive = True
        self.has_hit = False
        self.age = 0

    def update(self):
        self.age += 1
        self.timer -= 1
        if self.phase == "warning" and self.timer <= 0:
            self.phase = "impact"
            self.timer = 18
            self.has_hit = False
        elif self.phase == "impact" and self.timer <= 0:
            self.alive = False

    def hits_player(self, player):
        if self.phase != "impact":
            return False
        return math.hypot(self.x - player.x, self.y - player.y) <= C.FATED_STRIKE_RADIUS

    def draw(self, surf):
        cx, cy = int(self.x), int(self.y)
        r = C.FATED_STRIKE_RADIUS
        if self.phase == "warning":
            t = 1.0 - self.timer / C.FATED_STRIKE_DELAY
            pulse = (math.sin(self.age * 0.28) + 1) * 0.5
            alpha = int(80 + 150 * t)
            ring = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(ring, (200, 130, 240, alpha), (r + 4, r + 4), r, 3)
            pygame.draw.circle(
                ring, (220, 160, 250, int(alpha * 0.7)),
                (r + 4, r + 4), max(4, int(r * 0.6 + pulse * 4)), 2,
            )
            surf.blit(ring, ring.get_rect(center=(cx, cy)))
            # crosshair lines that converge
            reach = int(80 * (1 - t))
            tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                pygame.draw.line(
                    tmp, (220, 170, 250, alpha),
                    (cx + dx * (r + reach), cy + dy * (r + reach)),
                    (cx + dx * (r + 4), cy + dy * (r + 4)), 2,
                )
            surf.blit(tmp, (0, 0))
        else:
            t = self.timer / 18.0
            rr = int(r * (1 - t * 0.4))
            overlay = pygame.Surface((rr * 2 + 10, rr * 2 + 10), pygame.SRCALPHA)
            pygame.draw.circle(overlay, (180, 120, 240, int(230 * t)),
                               (rr + 5, rr + 5), rr)
            pygame.draw.circle(overlay, (255, 220, 255, int(230 * t)),
                               (rr + 5, rr + 5), max(1, rr - 8))
            pygame.draw.circle(overlay, (100, 60, 160, int(220 * t)),
                               (rr + 5, rr + 5), rr, 4)
            surf.blit(overlay, overlay.get_rect(center=(cx, cy)))


class WeftPulse:
    """Snapshot of the weaver's threads at cast time. Telegraph first, then
    the captured thread lines flash into damaging pulses. Each pulse has its
    own line geometry independent of subsequent thread changes.
    """

    def __init__(self, lines):
        # lines: list of (ax, ay, bx, by) tuples captured at cast time
        self.lines = lines
        self.phase = "warning"
        self.timer = C.WEFT_PULSE_TELEGRAPH
        self.alive = True
        self.has_hit = False
        self.age = 0

    def update(self):
        self.age += 1
        self.timer -= 1
        if self.phase == "warning" and self.timer <= 0:
            self.phase = "active"
            self.timer = C.WEFT_PULSE_ACTIVE
            self.has_hit = False
        elif self.phase == "active" and self.timer <= 0:
            self.alive = False

    def hits_player(self, player):
        if self.phase != "active":
            return False
        for (ax, ay, bx, by) in self.lines:
            if self._line_distance(ax, ay, bx, by, player.x, player.y) < C.WEFT_PULSE_HALF_WIDTH:
                return True
        return False

    @staticmethod
    def _line_distance(ax, ay, bx, by, px, py):
        dx = bx - ax; dy = by - ay
        L2 = dx * dx + dy * dy
        if L2 == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        cx = ax + t * dx; cy = ay + t * dy
        return math.hypot(px - cx, py - cy)

    def draw(self, surf):
        tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        if self.phase == "warning":
            t = 1.0 - self.timer / C.WEFT_PULSE_TELEGRAPH
            alpha = int(120 + 120 * t)
            thickness = 3
            for (ax, ay, bx, by) in self.lines:
                pygame.draw.line(
                    tmp, (250, 220, 255, alpha),
                    (int(ax), int(ay)), (int(bx), int(by)),
                    thickness,
                )
            # pulsing highlight overlay
            pulse = (math.sin(self.age * 0.4) + 1) * 0.5
            if pulse > 0.6:
                for (ax, ay, bx, by) in self.lines:
                    pygame.draw.line(
                        tmp, (255, 255, 255, 200),
                        (int(ax), int(ay)), (int(bx), int(by)), 1,
                    )
        else:
            t = self.timer / C.WEFT_PULSE_ACTIVE
            alpha = int(240 * t)
            for (ax, ay, bx, by) in self.lines:
                pygame.draw.line(
                    tmp, (255, 140, 220, alpha),
                    (int(ax), int(ay)), (int(bx), int(by)),
                    C.WEFT_PULSE_HALF_WIDTH * 2,
                )
                pygame.draw.line(
                    tmp, (255, 220, 255, alpha),
                    (int(ax), int(ay)), (int(bx), int(by)),
                    max(2, C.WEFT_PULSE_HALF_WIDTH),
                )
                pygame.draw.line(
                    tmp, (255, 255, 255, alpha),
                    (int(ax), int(ay)), (int(bx), int(by)), 2,
                )
        surf.blit(tmp, (0, 0))


class FateWeaver:
    def __init__(self, x, y, arena_rect):
        self.x = float(x)
        self.y = float(y)
        self.hp = C.WEAVER_MAX_HP
        self.max_hp = C.WEAVER_MAX_HP
        self.alive = True
        self.phase = 1
        self.facing = -1
        self.flash = 0
        self.bob = 0.0
        self.intro_timer = 90
        self.enraged_anim = 0
        self.state = "idle"
        self.state_timer = 120
        self.radius = 22
        self._sprite_cache = {}
        self.vx = 0.0
        self.vy = 0.0
        # 4 stone anchors at arena-midpoint positions
        ax, ay, aw, ah = arena_rect
        self.anchors = [
            Anchor(ax + aw // 2, ay + 60),            # top
            Anchor(ax + aw // 2, ay + ah - 60),       # bottom
            Anchor(ax + 80, ay + ah // 2),            # left
            Anchor(ax + aw - 80, ay + ah // 2),       # right
        ]
        self.threads = []
        self.pull_target = None         # (target_x, target_y) during pull
        self.pull_origin = None
        self.pull_timer = 0
        self.pull_active = False
        self.pull_hit_player = False
        self.attack_cooldown = 100
        # new-skill queued side effects - picked up by Game loop
        self.fated_strike_request = None    # (x, y) player-snapshot to place mark
        self.weft_pulse_request = False     # True -> capture current thread lines
        self._secondary_cooldown = 180      # separate timer for secondary skills

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 26, int(self.y) - 40, 52, 76)

    def sweep_hitbox(self):
        return None

    def _sprite(self):
        key = (self.phase, 1 if self.flash > 0 else 0)
        if key not in self._sprite_cache:
            self._sprite_cache[key] = sprites.make_fate_weaver_sprite(self.phase)
        return self._sprite_cache[key]

    @property
    def defense_multiplier(self):
        """Damage multiplier based on live threads (1.0 = full damage)."""
        live = sum(1 for t in self.threads if t.alive)
        # each thread absorbs WEAVER_THREAD_DEFENSE of incoming damage
        dr = min(0.85, live * C.WEAVER_THREAD_DEFENSE)
        return 1.0 - dr

    @property
    def live_thread_count(self):
        return sum(1 for t in self.threads if t.alive)

    def receive_player_hit(self, damage):
        mult = self.defense_multiplier
        dealt = max(0, int(damage * mult))
        if dealt > 0:
            self.hp -= dealt
            self.flash = 8
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        # weave a new thread to the closest anchor (or player in phase 2)
        if self.alive:
            self._weave_thread()
        return {"dealt": dealt, "band": "threaded", "threads": self.live_thread_count}

    def _weave_thread(self):
        """Spawn a new thread. Prefer anchors that don't already hold a thread
        so the web spreads across the arena rather than stacking on one stone.
        """
        self.threads = [t for t in self.threads if t.alive]
        # phase 2: 50% chance the thread anchors to the player instead
        if self.phase == 2 and random.random() < 0.5:
            # thread to player - caller fills 'b' end after spawn
            self.threads.append(Thread(self.x, self.y - 20, self.x, self.y - 20, target_player=True))
            return

        # count threads currently attached to each stone anchor
        def thread_count(anchor):
            return sum(
                1 for t in self.threads
                if not t.player_anchored
                and abs(t.bx - anchor.x) < 2
                and abs(t.by - (anchor.y - 20)) < 2
            )
        # rank anchors: fewest existing threads first, then nearest to weaver;
        # small random nudge to break ties so repeated draws don't always pick
        # the same anchor when the boss barely moves
        def anchor_rank(a):
            return (
                thread_count(a),
                math.hypot(a.x - self.x, a.y - self.y) + random.uniform(0, 20),
            )
        chosen = min(self.anchors, key=anchor_rank)
        self.threads.append(Thread(self.x, self.y - 20, chosen.x, chosen.y - 20))
        # cap to MAX_THREADS (drop oldest)
        if len(self.threads) > C.WEAVER_MAX_THREADS:
            self.threads.pop(0)

    def complete_player_anchored_thread(self, player):
        """Fill in the 'b' endpoint of newly woven player-anchored threads."""
        for t in self.threads:
            if t.player_anchored and t.bx == self.x and t.by == self.y - 20:
                t.bx = player.x
                t.by = player.y

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

        # phase transition
        if self.phase == 1 and self.hp <= self.max_hp * C.WEAVER_ENRAGE_HP_PCT:
            self.phase = 2
            self.enraged_anim = 60
            self._sprite_cache.clear()

        if self.enraged_anim > 0:
            self.enraged_anim -= 1

        # pull attack motion
        if self.pull_active:
            self._update_pull()
        else:
            # drift around the center slowly
            dx, dy, dist = vec_from_to(self.x, self.y, player.x, player.y)
            if dist > 160:
                self.x += dx * 1.0
                self.y += dy * 1.0
                self.facing = 1 if dx >= 0 else -1
            self.x, self.y = clamp_to_arena(self.x, self.y, pad=50)
            # periodically trigger a pull along a live thread
            if self.attack_cooldown <= 0 and self.live_thread_count > 0:
                self._begin_pull()
            # secondary skills fire on their own cooldown, offset from pulls
            if self._secondary_cooldown <= 0 and self.intro_timer == 0:
                # Fated Strike is always available; Weft Pulse only if threads exist
                if self.live_thread_count > 0 and random.random() < 0.5:
                    self.weft_pulse_request = True
                else:
                    self.fated_strike_request = (player.x, player.y)
                self._secondary_cooldown = 220 if self.phase == 2 else 300

        # update all threads
        for t in self.threads:
            t.update(self)
        # clean up dead
        self.threads = [t for t in self.threads if t.alive]

    def _begin_pull(self):
        # pick a live thread at random
        live = [t for t in self.threads if t.alive]
        if not live:
            return
        t = random.choice(live)
        self.pull_origin = (self.x, self.y)
        self.pull_target = (t.bx, t.by)
        self.pull_timer = 0
        self.pull_active = True
        self.pull_hit_player = False
        self.attack_cooldown = 180

    def _update_pull(self):
        self.pull_timer += 1
        if self.pull_timer < C.WEAVER_PULL_WINDUP:
            # windup - stand still, telegraph
            return
        # dash
        tx, ty = self.pull_target
        dx, dy, dist = vec_from_to(self.x, self.y, tx, ty)
        if dist < 8 or self.pull_timer > C.WEAVER_PULL_WINDUP + 60:
            self.pull_active = False
            return
        self.x += dx * C.WEAVER_PULL_SPEED
        self.y += dy * C.WEAVER_PULL_SPEED

    def pull_line_rect(self):
        """Rect representing the pull's current damaging line (during dash)."""
        if not self.pull_active or self.pull_origin is None:
            return None
        if self.pull_timer < C.WEAVER_PULL_WINDUP:
            return None
        ox, oy = self.pull_origin
        tx, ty = self.pull_target
        min_x = int(min(ox, tx)) - C.WEAVER_PULL_WIDTH // 2
        min_y = int(min(oy, ty)) - C.WEAVER_PULL_WIDTH // 2
        max_x = int(max(ox, tx)) + C.WEAVER_PULL_WIDTH // 2
        max_y = int(max(oy, ty)) + C.WEAVER_PULL_WIDTH // 2
        return pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)

    def draw(self, surf):
        # threads behind everything
        for t in self.threads:
            t.draw(surf)
        # anchors in front of arena
        for a in self.anchors:
            a.draw(surf)
        # pull telegraph
        if self.pull_active and self.pull_timer < C.WEAVER_PULL_WINDUP:
            t = self.pull_timer / C.WEAVER_PULL_WINDUP
            ox, oy = self.pull_origin
            tx, ty = self.pull_target
            tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.line(
                tmp, (255, 120, 120, int(140 + 100 * t)),
                (int(ox), int(oy)), (int(tx), int(ty)),
                max(2, int(C.WEAVER_PULL_WIDTH * t / 2)),
            )
            surf.blit(tmp, (0, 0))
        # sprite
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
