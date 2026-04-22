"""Level 2 boss: The Mirrorwright.

Core mechanic - Mirror Orb:
  Hits on the boss don't reduce HP directly. Instead, damage accumulates in a
  mirror orb on his chest. Two outcomes:

  - Auto-shatter: if the orb reaches the shatter threshold, it bursts on the
    player, reflecting accumulated damage back. Punishes greedy aggression.
  - Dash-shatter: if the player dashes into the orb while it has stored
    damage, the full queue (multiplied) is dumped onto the boss's HP - a
    risky, committed high-damage combo.

Sub-mechanic - Phantom Reflections: the boss fires ghost-images that retrace
the player's recent movement path. Dodge by breaking your own pattern.
"""
import math
import random
import pygame

from . import assets
from . import constants as C
from . import sprites
from .utils import clamp, vec_from_to, clamp_to_arena, random_point_in_arena, inside_arena


class Phantom:
    """A projectile that replays the player's recorded movement path.

    Moves along the path from oldest to newest position, optionally with a
    small approach segment from the boss to the path's first point.
    """

    def __init__(self, boss_x, boss_y, path):
        # path entries are (x, y) or (x, y, facing); normalize to (x, y)
        self.path = [(p[0], p[1]) for p in path] if path else []
        self.index = 0
        self.alive = True
        self.life = len(self.path) + 40
        self.radius = 14
        self._sprite = sprites.make_phantom_sprite()
        if not self.path:
            self.alive = False
            self.x = boss_x
            self.y = boss_y
        else:
            self.x, self.y = self.path[0]
        self.age = 0

    def update(self):
        self.age += 1
        self.life -= 1
        if self.life <= 0:
            self.alive = False
            return
        # advance two steps per frame so the phantom noticeably chases
        for _ in range(2):
            if self.index < len(self.path) - 1:
                self.index += 1
                self.x, self.y = self.path[self.index]
            else:
                break
        # once we hit the end of the path, linger briefly then vanish
        if self.index >= len(self.path) - 1 and self.life > 20:
            self.life = 20

    def draw(self, surf):
        # trailing fade - draw past positions at low alpha
        tail_n = 8
        tail_surf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        for k in range(1, tail_n + 1):
            idx = max(0, self.index - k * 3)
            if idx == self.index:
                break
            tx, ty = self.path[idx]
            alpha = int(70 * (1 - k / tail_n))
            pygame.draw.circle(
                tail_surf, (180, 200, 230, alpha),
                (int(tx), int(ty)), 6
            )
        surf.blit(tail_surf, (0, 0))
        # main phantom body - ghostly silver
        spr = self._sprite
        rect = spr.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(spr, rect)


class SilverRainZone:
    """Ground zone for Mirrorwright's Silver Rain. Warns for
    SILVER_RAIN_TELEGRAPH, then rains shards for SILVER_RAIN_ACTIVE.
    """

    __slots__ = ("x", "y", "phase", "timer", "alive", "has_hit", "age")

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.phase = "telegraph"
        self.timer = C.SILVER_RAIN_TELEGRAPH
        self.alive = True
        self.has_hit = False
        self.age = 0

    def update(self):
        self.age += 1
        self.timer -= 1
        if self.timer <= 0:
            if self.phase == "telegraph":
                self.phase = "active"
                self.timer = C.SILVER_RAIN_ACTIVE
                self.has_hit = False
            else:
                self.alive = False

    def hits_player(self, player):
        if self.phase != "active":
            return False
        return math.hypot(self.x - player.x, self.y - player.y) <= C.SILVER_RAIN_RADIUS

    def draw(self, surf):
        cx, cy = int(self.x), int(self.y)
        r = C.SILVER_RAIN_RADIUS
        if self.phase == "telegraph":
            t = 1.0 - self.timer / C.SILVER_RAIN_TELEGRAPH
            pulse = (math.sin(self.age * 0.35) + 1) * 0.5
            alpha = int(80 + 130 * t)
            ring = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(ring, (190, 215, 245, alpha), (r + 4, r + 4), r, 3)
            pygame.draw.circle(
                ring, (230, 245, 255, int(alpha * 0.7)),
                (r + 4, r + 4), max(4, int(r * 0.6 + pulse * 4)), 2,
            )
            surf.blit(ring, ring.get_rect(center=(cx, cy)))
            # converging warning streaks from above
            if t > 0.35:
                tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
                for k in range(3):
                    sx = cx + (k - 1) * 14
                    pygame.draw.line(
                        tmp, (200, 220, 250, int(120 * t)),
                        (sx, cy - 70), (sx + (k - 1) * 2, cy - 4), 1,
                    )
                surf.blit(tmp, (0, 0))
        else:
            # active rain - falling shard streaks
            t = self.timer / C.SILVER_RAIN_ACTIVE
            tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            # circle fill hint
            fill = pygame.Surface((r * 2 + 6, r * 2 + 6), pygame.SRCALPHA)
            pygame.draw.circle(fill, (200, 220, 245, 60), (r + 3, r + 3), r)
            pygame.draw.circle(fill, (220, 240, 255, 120), (r + 3, r + 3), r, 3)
            surf.blit(fill, fill.get_rect(center=(cx, cy)))
            # a dozen quick falling streaks scattered in the zone
            for k in range(12):
                offset = (k * 23) % (r * 2) - r
                sx = cx + offset
                sy_top = cy - 50 - ((self.age + k * 5) % 60)
                sy_bot = sy_top + 22
                pygame.draw.line(
                    tmp, (230, 245, 255, 220),
                    (sx, sy_top), (sx, sy_bot), 2,
                )
            surf.blit(tmp, (0, 0))


class MirrorShard:
    """Silver-shard projectile fired by the Mirrorwright's Shard Volley.
    Straight trajectory; damages the player on contact.
    """

    __slots__ = ("x", "y", "vx", "vy", "life", "alive", "radius", "_angle")

    def __init__(self, x, y, dx, dy):
        n = math.hypot(dx, dy) or 1.0
        self.x = float(x)
        self.y = float(y)
        self.vx = dx / n * C.MIRROR_SHARD_SPEED
        self.vy = dy / n * C.MIRROR_SHARD_SPEED
        self.life = 220
        self.alive = True
        self.radius = 9
        self._angle = math.degrees(math.atan2(dy, dx))

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.life <= 0 or not inside_arena(self.x, self.y, pad=-12):
            self.alive = False

    def draw(self, surf):
        cx, cy = int(self.x), int(self.y)
        pts = [
            (cx + 10, cy), (cx, cy - 6),
            (cx - 10, cy), (cx, cy + 6),
        ]
        pygame.draw.polygon(surf, (160, 190, 230), pts)
        pygame.draw.polygon(surf, (230, 245, 255), [
            (cx + 7, cy), (cx, cy - 4),
            (cx - 7, cy), (cx, cy + 4),
        ])
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 2)


class Mirrorwright:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.hp = C.MIRROR_BOSS_MAX_HP
        self.max_hp = C.MIRROR_BOSS_MAX_HP
        self.orb = 0.0               # queued damage in the mirror orb
        self.phase = 1
        self.state = "idle"
        self.state_timer = 60
        self.facing = -1
        self.flash = 0
        self.alive = True
        self.vx = 0.0
        self.vy = 0.0
        self.bob = 0.0
        self.teleport_target = None
        self.attack_hit_player_this_state = False
        self.intro_timer = 90
        self.enraged_anim = 0
        self._sprite_cache = {}
        # queued side effects the Game loop picks up
        self.phantom_request = False       # True -> Game spawns phantom next frame
        self.silver_rain_request = None    # list of (x, y) zone centers or None
        self.volley_request = None         # list of (dx, dy) or None
        self._anim_tick = 0
        self.shatter_flash = 0    # frames counting how long to show a shatter burst
        self.shatter_center = None
        # sweep blade trail for afterimage visuals
        self._sweep_trail = []
        self._swing_ghosts = []   # list of (angle_deg, life) for sprite afterimages
        # silver curved scimitar sprite, pivots around the hilt
        self._blade_sprite = sprites.make_boss_sword_pivot(
            assets.TILE_SWORD_CURVED, scale=5,
        )
        # cached queued attack params
        self._pending_rain_zones = []
        self._pending_volley_dirs = []

    # ---------- sprite ----------

    def _sprite(self):
        key = (self.phase, 1 if self.flash > 0 else 0)
        if key not in self._sprite_cache:
            self._sprite_cache[key] = sprites.make_mirrorwright_sprite(
                self.phase, flash=1 if self.flash > 0 else 0
            )
        return self._sprite_cache[key]

    # ---------- collision ----------

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 28, int(self.y) - 44, 56, 84)

    def orb_rect(self):
        """Rect around the boss's chest where the dash-shatter can hit."""
        return pygame.Rect(
            int(self.x) - C.MIRROR_DASH_SHATTER_RADIUS // 2,
            int(self.y) - 40,
            C.MIRROR_DASH_SHATTER_RADIUS,
            50,
        )

    def sweep_hitbox(self):
        if self.state != "sweep":
            return None
        w = 100
        if self.facing == 1:
            return pygame.Rect(int(self.x), int(self.y) - 36, w, 72)
        return pygame.Rect(int(self.x) - w, int(self.y) - 36, w, 72)

    # ---------- orb handling ----------

    @property
    def shatter_threshold(self):
        return C.MIRROR_ORB_SHATTER_P2 if self.phase == 2 else C.MIRROR_ORB_SHATTER_P1

    def receive_player_hit(self, damage):
        """Queue damage inside the mirror orb instead of reducing HP."""
        self.orb = clamp(self.orb + damage, 0, C.MIRROR_ORB_MAX)
        if self.phase == 2:
            self.flash = 8
        return {"queued": damage, "orb": self.orb}

    def trigger_auto_shatter(self):
        """Called by the Game when orb reaches threshold. Returns damage
        dealt to the player."""
        queued = self.orb
        self.orb = 0.0
        self.shatter_flash = 20
        self.shatter_center = (self.x, self.y - 20)
        return min(C.MIRROR_AUTO_SHATTER_DAMAGE, int(max(1, queued // 20)))

    def trigger_dash_shatter(self):
        """Player dashed through the orb - dump the queue onto boss HP."""
        queued = self.orb
        self.orb = 0.0
        dealt = int(queued * C.MIRROR_DASH_DAMAGE_MULT)
        self.hp -= dealt
        self.flash = 14
        self.shatter_flash = 28
        self.shatter_center = (self.x, self.y - 20)
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return dealt

    # ---------- AI ----------

    def pick_next_state(self, player):
        if self.intro_timer > 0:
            return "idle", 40
        in_p2 = self.phase == 2
        pool = [
            ("sweep_telegraph", 3 if in_p2 else 2),
            ("phantom_telegraph", 4 if in_p2 else 3),
            ("silver_rain_telegraph", 3 if in_p2 else 2),
            ("volley_telegraph", 3 if in_p2 else 2),
        ]
        if in_p2:
            pool.append(("teleport_out", 2))
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
            "sweep_telegraph": 30,
            "sweep": 20,
            "phantom_telegraph": 34,
            "phantom_cast": 1,
            "teleport_out": 28,
            "teleport_in": 22,
            "silver_rain_telegraph": 40,
            "silver_rain_cast": 1,
            "volley_telegraph": 28,
            "volley_fire": 1,
            "idle": 24 if in_p2 else 34,
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
            dx, dy, _ = vec_from_to(self.x, self.y, player.x, player.y)
            self.vx = dx * 5.0
            self.vy = dy * 5.0
            self.facing = 1 if dx >= 0 else -1
        elif new_state == "phantom_telegraph":
            self.facing = 1 if player.x >= self.x else -1
            self.vx = self.vy = 0
        elif new_state == "phantom_cast":
            self.phantom_request = True
        elif new_state == "teleport_out":
            self.vx = self.vy = 0
            for _ in range(10):
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
        elif new_state == "silver_rain_telegraph":
            # pre-pick 4 zone centers spread across the arena
            self._pending_rain_zones = []
            for _ in range(C.SILVER_RAIN_ZONES):
                for _try in range(8):
                    zx, zy = random_point_in_arena(pad=80)
                    # avoid stacking zones too close
                    if all(math.hypot(zx - px, zy - py) > 100
                           for (px, py) in self._pending_rain_zones):
                        self._pending_rain_zones.append((zx, zy))
                        break
                else:
                    self._pending_rain_zones.append(random_point_in_arena(pad=80))
        elif new_state == "silver_rain_cast":
            self.silver_rain_request = list(self._pending_rain_zones)
            self._pending_rain_zones = []
        elif new_state == "volley_telegraph":
            self.facing = 1 if player.x >= self.x else -1
        elif new_state == "volley_fire":
            # fan of SHARD_VOLLEY_COUNT shards centered on player direction
            dx, dy, _ = vec_from_to(self.x, self.y, player.x, player.y)
            base = math.atan2(dy, dx)
            step = C.SHARD_VOLLEY_SPREAD / max(1, C.SHARD_VOLLEY_COUNT - 1)
            dirs = []
            for i in range(C.SHARD_VOLLEY_COUNT):
                a = base + (i - (C.SHARD_VOLLEY_COUNT - 1) / 2) * step
                dirs.append((math.cos(a), math.sin(a)))
            self.volley_request = dirs

    def update(self, player):
        self.bob += 0.06
        self._anim_tick += 1
        if self.intro_timer > 0:
            self.intro_timer -= 1
        if self.flash > 0:
            self.flash -= 1
        if self.shatter_flash > 0:
            self.shatter_flash -= 1
        # fade out old sweep-trail samples
        self._sweep_trail = [
            (hx, hy, tx, ty, life - 1)
            for (hx, hy, tx, ty, life) in self._sweep_trail
            if life > 1
        ]
        self._swing_ghosts = [
            (ang, life - 1) for (ang, life) in self._swing_ghosts if life > 1
        ]

        # phase shift
        if self.phase == 1 and self.hp <= self.max_hp * C.MIRROR_BOSS_ENRAGE_HP_PCT:
            self.phase = 2
            self.enraged_anim = 60
            self._sprite_cache.clear()
            self._enter_state("teleport_out", 30, player)
            return

        if self.enraged_anim > 0:
            self.enraged_anim -= 1

        self.state_timer -= 1
        if self.state == "sweep":
            self.x += self.vx
            self.y += self.vy
            self.vx *= 0.82
            self.vy *= 0.82
            # record current blade position for afterimage trail
            t = 1.0 - self.state_timer / 20.0
            ang = self.sweep_blade_angle(t)
            rad = math.radians(ang)
            hx = self.x + self.facing * 10
            hy = self.y - 20
            tip_x = hx + math.cos(rad) * 94
            tip_y = hy + math.sin(rad) * 94
            self._sweep_trail.append((hx, hy, tip_x, tip_y, 10))
            self._swing_ghosts.append((ang, 8))

        if self.state_timer <= 0:
            self._advance_state(player)

    def sweep_blade_angle(self, t):
        """Blade angle at normalized sweep progress t in [0, 1]."""
        start, end = -70, 120
        angle = start + (end - start) * max(0.0, min(1.0, t))
        if self.facing == -1:
            angle = 180 - angle
        return angle

    def _advance_state(self, player):
        prev = self.state
        if prev == "sweep_telegraph":
            self._enter_state("sweep", 20, player); return
        if prev == "sweep":
            self._enter_state("idle", 24, player); return
        if prev == "phantom_telegraph":
            self._enter_state("phantom_cast", 1, player); return
        if prev == "phantom_cast":
            self._enter_state("idle", 30 if self.phase == 2 else 40, player); return
        if prev == "teleport_out":
            self._enter_state("teleport_in", 22, player); return
        if prev == "teleport_in":
            self._enter_state("idle", 18, player); return
        if prev == "silver_rain_telegraph":
            self._enter_state("silver_rain_cast", 1, player); return
        if prev == "silver_rain_cast":
            self._enter_state("idle", 36 if self.phase == 2 else 48, player); return
        if prev == "volley_telegraph":
            self._enter_state("volley_fire", 1, player); return
        if prev == "volley_fire":
            self._enter_state("idle", 28 if self.phase == 2 else 40, player); return
        choice, dur = self.pick_next_state(player)
        self._enter_state(choice, dur, player)

    # ---------- rendering ----------

    def draw(self, surf):
        spr = self._sprite()
        tp_out_t = tp_in_t = None
        if self.state == "teleport_out":
            tp_out_t = 1.0 - (self.state_timer / 28.0)
            self._draw_mirror_plane(surf, tp_out_t, emerging=False)
            alpha = max(0, int(255 * (1 - tp_out_t)))
            squash = max(0.4, 1.0 - tp_out_t * 0.55)
            s2 = spr.copy(); s2.set_alpha(alpha)
            w, h = s2.get_size()
            s2 = pygame.transform.scale(s2, (w, max(8, int(h * squash))))
            spr = s2
        elif self.state == "teleport_in":
            tp_in_t = 1.0 - (self.state_timer / 22.0)
            self._draw_mirror_plane(surf, tp_in_t, emerging=True)
            alpha = int(255 * tp_in_t)
            squash = min(1.0, 0.5 + tp_in_t * 0.7)
            s2 = spr.copy(); s2.set_alpha(alpha)
            w, h = s2.get_size()
            s2 = pygame.transform.scale(s2, (w, max(8, int(h * squash))))
            spr = s2

        bob_y = int(math.sin(self.bob) * 3)
        flip = self.facing == -1
        drawn = pygame.transform.flip(spr, True, False) if flip else spr
        rect = drawn.get_rect(midbottom=(int(self.x), int(self.y) + 44 + bob_y))
        surf.blit(drawn, rect)

        # silver flash at the peak of dissolve / materialize
        if tp_out_t is not None and tp_out_t > 0.82:
            self._draw_tp_flash(surf, (220, 235, 255), 1.0 - (1.0 - tp_out_t) / 0.18)
        elif tp_in_t is not None and tp_in_t < 0.22:
            self._draw_tp_flash(surf, (220, 235, 255), 1.0 - tp_in_t / 0.22)

        # orb on chest
        if self.orb > 0 or self.shatter_flash > 0:
            self._draw_mirror_orb(surf)

        # sweep telegraph
        if self.state == "sweep_telegraph":
            t = 1.0 - self.state_timer / 30.0
            self._draw_sweep_telegraph(surf, t)
        # sweep active
        if self.state == "sweep":
            self._draw_sweep_active(surf)
        # phantom telegraph
        if self.state == "phantom_telegraph":
            t = 1.0 - self.state_timer / 34.0
            self._draw_phantom_telegraph(surf, t)
        # silver rain telegraph: a glowing inventory of the zones over boss head
        if self.state == "silver_rain_telegraph":
            t = 1.0 - self.state_timer / 40.0
            self._draw_silver_rain_cast_pose(surf, t)
        # volley telegraph: 5 charging points around the weaving hand
        if self.state == "volley_telegraph":
            t = 1.0 - self.state_timer / 28.0
            self._draw_volley_telegraph(surf, t)

    # ---------- teleport visuals ----------

    def _draw_mirror_plane(self, surf, t, emerging):
        """Vertical silver mirror-plane at the boss's position.
        Opens on teleport_out, collapses on teleport_in.
        """
        cx = int(self.x)
        top_y = int(self.y) - 90
        bottom_y = int(self.y) + 44
        if emerging:
            openness = 1.0 - t     # mirror closes as he steps out
        else:
            openness = t           # mirror opens as he dissolves into it
        width = max(3, int(40 * openness))
        height = bottom_y - top_y
        plane = pygame.Surface((width + 12, height + 12), pygame.SRCALPHA)
        # reflective back
        pygame.draw.ellipse(plane, (140, 170, 210, 200), (3, 3, width + 6, height + 6))
        # bright silver edges
        pygame.draw.ellipse(plane, (230, 240, 255, 255), (4, 4, width + 4, height + 4), 3)
        # vertical shimmer seam
        seam_a = int(180 + 60 * math.sin(self._anim_tick * 0.45))
        pygame.draw.line(
            plane, (255, 255, 255, seam_a),
            (width // 2 + 6, 4), (width // 2 + 6, height + 4), 2,
        )
        # a sweeping highlight band (slides up and down the mirror)
        band_y = int((self._anim_tick * 6) % (height + 12))
        pygame.draw.line(
            plane, (255, 255, 255, 140),
            (4, band_y), (width + 6, band_y), 1,
        )
        surf.blit(plane, plane.get_rect(midbottom=(cx, bottom_y + 2)))
        # cracks radiating outward - pronounced just before shatter / just after reassembly
        if 0.3 < openness < 0.9:
            for i in range(5):
                a = (i / 5) * math.tau + self._anim_tick * 0.04
                length = int(22 + 28 * openness)
                x0 = cx + math.cos(a) * 10
                y0 = (top_y + bottom_y) // 2 + math.sin(a) * 10
                x1 = cx + math.cos(a) * length
                y1 = (top_y + bottom_y) // 2 + math.sin(a) * length
                pygame.draw.line(
                    surf, (220, 230, 250),
                    (int(x0), int(y0)), (int(x1), int(y1)), 1,
                )
        # ground glow at the mirror's foot
        glow_w = int(68 * openness + 16)
        glow = pygame.Surface((glow_w * 2 + 8, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(
            glow, (200, 220, 245, 160),
            (0, 0, glow_w * 2 + 8, 14), 2,
        )
        surf.blit(glow, glow.get_rect(center=(cx, bottom_y)))

    def _draw_tp_flash(self, surf, color, intensity):
        intensity = max(0.0, min(1.0, intensity))
        r = int(56 + 46 * intensity)
        flash = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(flash, (*color, int(130 * intensity)), (r + 4, r + 4), r)
        pygame.draw.circle(
            flash, (255, 255, 255, int(230 * intensity)),
            (r + 4, r + 4), max(1, r - 26),
        )
        surf.blit(flash, flash.get_rect(center=(int(self.x), int(self.y) - 20)))

    def _draw_mirror_orb(self, surf):
        pct = clamp(self.orb / self.shatter_threshold, 0.0, 1.0)
        base_r = int(10 + 16 * pct)
        cx, cy = int(self.x), int(self.y) - 22
        # shatter burst overlay
        if self.shatter_flash > 0:
            t = self.shatter_flash / 28.0
            r = int(20 + 80 * (1 - t))
            overlay = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(overlay, (220, 240, 255, int(220 * t)), (r + 4, r + 4), r, 4)
            pygame.draw.circle(overlay, (160, 200, 240, int(140 * t)), (r + 4, r + 4), max(1, r - 10), 3)
            surf.blit(overlay, overlay.get_rect(center=(cx, cy)))
        # orb glow (growing, pulsing)
        pulse = 1.0 + 0.08 * math.sin(self._anim_tick * 0.25)
        glow_r = int(base_r * 1.6 * pulse)
        glow = pygame.Surface((glow_r * 2 + 6, glow_r * 2 + 6), pygame.SRCALPHA)
        # color shifts from blue -> violet -> red as orb fills
        inner_col = (
            int(160 + 90 * pct),
            int(180 - 80 * pct),
            int(230 - 80 * pct),
            180,
        )
        pygame.draw.circle(glow, inner_col, (glow_r + 3, glow_r + 3), glow_r)
        surf.blit(glow, glow.get_rect(center=(cx, cy)))
        # orb body (silver/blue - shifts red when near shatter)
        orb = pygame.Surface((base_r * 2 + 6, base_r * 2 + 6), pygame.SRCALPHA)
        body_col = (
            int(200 + 55 * pct),
            int(220 - 80 * pct),
            int(240 - 120 * pct),
        )
        pygame.draw.circle(orb, body_col, (base_r + 3, base_r + 3), base_r)
        # bright highlight
        pygame.draw.circle(orb, (255, 255, 255), (base_r, base_r - 1), max(1, base_r // 3))
        # crack pattern when near threshold
        if pct > 0.7:
            crack_col = (255, 120, 100, 200)
            for ang_deg in (30, 150, 260):
                a = math.radians(ang_deg)
                x0 = base_r + 3 + math.cos(a) * 2
                y0 = base_r + 3 + math.sin(a) * 2
                x1 = base_r + 3 + math.cos(a) * (base_r - 2)
                y1 = base_r + 3 + math.sin(a) * (base_r - 2)
                pygame.draw.line(orb, crack_col, (int(x0), int(y0)), (int(x1), int(y1)), 2)
        surf.blit(orb, orb.get_rect(center=(cx, cy)))

    def _draw_sweep_telegraph(self, surf, t):
        cx = self.x + self.facing * 10
        cy = self.y - 20
        radius = 86
        start_deg, end_deg = -70, 120
        if self.facing == -1:
            start_deg, end_deg = 250, 60
        segs = 26
        pts = []
        for i in range(segs + 1):
            a = math.radians(start_deg + (end_deg - start_deg) * i / segs)
            pts.append((cx + math.cos(a) * radius, cy + math.sin(a) * radius))
        guide_alpha = int(70 + 140 * t)
        for i in range(0, len(pts) - 1, 2):
            p0, p1 = pts[i], pts[i + 1]
            pygame.draw.line(
                surf, (180, 210, 240, guide_alpha),
                (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), 2
            )
        reveal = int((segs + 1) * t)
        if reveal >= 2:
            seg_pts = [(int(x), int(y)) for (x, y) in pts[:reveal]]
            pygame.draw.lines(surf, (220, 240, 255), False, seg_pts, 3)
            if len(seg_pts) >= 1:
                pygame.draw.circle(surf, (230, 240, 255), seg_pts[-1], 5)
                pygame.draw.circle(surf, (255, 255, 255), seg_pts[-1], 2)
        # silver charge orb at the hand
        orb_r = 4 + int(t * 8) + (self._anim_tick // 4) % 2
        orb = pygame.Surface((orb_r * 2 + 8, orb_r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(orb, (170, 200, 235, 200), (orb_r + 4, orb_r + 4), orb_r)
        pygame.draw.circle(orb, (220, 235, 250, 255), (orb_r + 4, orb_r + 4), max(1, orb_r - 3))
        pygame.draw.circle(orb, (255, 255, 255), (orb_r + 4, orb_r + 4), max(1, orb_r - 7))
        surf.blit(orb, orb.get_rect(center=(int(cx), int(cy))))
        # mirror-runic sigil on the ground late in the windup
        if t > 0.35:
            self._draw_rune_sigil(
                surf, int(self.x), int(self.y) + 10, (t - 0.3) * 1.4,
                ring_col=(180, 210, 240), glyph_col=(240, 250, 255),
            )

    def _draw_sweep_active(self, surf):
        """Silver whoosh crescent + rotated scimitar sprite + sprite ghosts."""
        t = 1.0 - self.state_timer / 20.0
        cx = self.x + self.facing * 10
        cy = self.y - 20
        self._draw_swing_crescent(
            surf, cx, cy, t,
            inner_r=30, outer_r=98,
            body_col=(170, 200, 235, 85),
            core_col=(230, 245, 255, 130),
            edge_col=(120, 170, 220, 160),
        )
        # sprite ghosts
        for (ghost_ang, life) in self._swing_ghosts[-5:]:
            self._blit_rotated_blade(
                surf, cx, cy, ghost_ang, alpha=int(180 * (life / 8.0))
            )
        # current blade sprite
        ang = self.sweep_blade_angle(t)
        self._blit_rotated_blade(surf, cx, cy, ang)
        # tip sparkle
        rad = math.radians(ang)
        tip_x = cx + math.cos(rad) * 90
        tip_y = cy + math.sin(rad) * 90
        pygame.draw.circle(surf, (240, 250, 255), (int(tip_x), int(tip_y)), 5)
        pygame.draw.circle(surf, (255, 255, 255), (int(tip_x), int(tip_y)), 2)

    def _blit_rotated_blade(self, surf, pivot_x, pivot_y, swing_deg, alpha=255):
        if self._blade_sprite is None:
            return
        pygame_rot = -(swing_deg + 90)
        rotated = pygame.transform.rotate(self._blade_sprite, pygame_rot)
        if alpha < 255:
            fade = pygame.Surface(rotated.get_size(), pygame.SRCALPHA)
            fade.fill((255, 255, 255, max(0, min(255, alpha))))
            rotated = rotated.copy()
            rotated.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(rotated, rotated.get_rect(center=(int(pivot_x), int(pivot_y))))

    # ---------- shared sweep helpers ----------
    # Visually-generic helpers (kept on the class since both bosses have
    # `sweep_blade_angle` and `_anim_tick`; they're intentionally duplicated
    # from boss.py so each boss stays self-contained).

    def _draw_swing_crescent(self, surf, cx, cy, t, inner_r, outer_r,
                             body_col, core_col, edge_col):
        if t < 0.05:
            return
        n = 22
        inner_pts = []
        outer_pts = []
        for i in range(n):
            sub_t = t * (i / (n - 1))
            ang = math.radians(self.sweep_blade_angle(sub_t))
            inner_pts.append((cx + math.cos(ang) * inner_r, cy + math.sin(ang) * inner_r))
            outer_pts.append((cx + math.cos(ang) * outer_r, cy + math.sin(ang) * outer_r))
        whoosh = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        poly = inner_pts + list(reversed(outer_pts))
        pygame.draw.polygon(whoosh, body_col, [(int(x), int(y)) for x, y in poly])
        mid_in_r = inner_r + (outer_r - inner_r) * 0.35
        mid_out_r = inner_r + (outer_r - inner_r) * 0.75
        band_in = []
        band_out = []
        for i in range(n):
            sub_t = t * (i / (n - 1))
            ang = math.radians(self.sweep_blade_angle(sub_t))
            band_in.append((cx + math.cos(ang) * mid_in_r, cy + math.sin(ang) * mid_in_r))
            band_out.append((cx + math.cos(ang) * mid_out_r, cy + math.sin(ang) * mid_out_r))
        pygame.draw.polygon(
            whoosh, core_col,
            [(int(x), int(y)) for x, y in band_in + list(reversed(band_out))],
        )
        lead_n = max(2, n // 3)
        lead_out = outer_pts[-lead_n:]
        lead_in = inner_pts[-lead_n:]
        pygame.draw.polygon(
            whoosh, edge_col,
            [(int(x), int(y)) for x, y in lead_in + list(reversed(lead_out))],
        )
        pygame.draw.lines(
            whoosh, (*edge_col[:3], 220), False,
            [(int(x), int(y)) for x, y in outer_pts], 2,
        )
        surf.blit(whoosh, (0, 0))

    def _draw_curved_blade(self, surf, cx, cy, rad, length, curve_amount,
                           outer_col, body_col, core_col):
        pcos = math.cos(rad + math.pi / 2)
        psin = math.sin(rad + math.pi / 2)
        hilt = (cx, cy)
        tip = (cx + math.cos(rad) * length, cy + math.sin(rad) * length)
        m1 = (cx + math.cos(rad) * (length * 0.35), cy + math.sin(rad) * (length * 0.35))
        m2 = (cx + math.cos(rad) * (length * 0.70), cy + math.sin(rad) * (length * 0.70))
        outer = [
            hilt,
            (m1[0] + pcos * curve_amount, m1[1] + psin * curve_amount),
            (m2[0] + pcos * (curve_amount * 0.9), m2[1] + psin * (curve_amount * 0.9)),
            tip,
            (m2[0] - pcos * (curve_amount * 0.5), m2[1] - psin * (curve_amount * 0.5)),
            (m1[0] - pcos * (curve_amount * 0.6), m1[1] - psin * (curve_amount * 0.6)),
        ]
        pygame.draw.polygon(surf, outer_col, [(int(x), int(y)) for x, y in outer])
        inner = [
            hilt,
            (m1[0] + pcos * (curve_amount * 0.65), m1[1] + psin * (curve_amount * 0.65)),
            (m2[0] + pcos * (curve_amount * 0.55), m2[1] + psin * (curve_amount * 0.55)),
            tip,
            (m2[0] - pcos * (curve_amount * 0.25), m2[1] - psin * (curve_amount * 0.25)),
            (m1[0] - pcos * (curve_amount * 0.3), m1[1] - psin * (curve_amount * 0.3)),
        ]
        pygame.draw.polygon(surf, body_col, [(int(x), int(y)) for x, y in inner])
        pygame.draw.line(surf, core_col, (int(cx), int(cy)), (int(tip[0]), int(tip[1])), 2)
        pygame.draw.circle(surf, core_col, (int(tip[0]), int(tip[1])), 6)
        pygame.draw.circle(surf, (255, 255, 255), (int(tip[0]), int(tip[1])), 3)
        for da in (0, math.pi / 2):
            ang = rad + da
            sx = tip[0] + math.cos(ang) * 10
            sy = tip[1] + math.sin(ang) * 10
            pygame.draw.line(
                surf, (255, 255, 255, 180),
                (int(tip[0]), int(tip[1])), (int(sx), int(sy)), 1,
            )
            sx = tip[0] - math.cos(ang) * 10
            sy = tip[1] - math.sin(ang) * 10
            pygame.draw.line(
                surf, (255, 255, 255, 180),
                (int(tip[0]), int(tip[1])), (int(sx), int(sy)), 1,
            )

    def _draw_hilt(self, surf, cx, cy, rad, accent_col, dark_col):
        pcos = math.cos(rad + math.pi / 2)
        psin = math.sin(rad + math.pi / 2)
        g0 = (cx + pcos * 7, cy + psin * 7)
        g1 = (cx - pcos * 7, cy - psin * 7)
        pygame.draw.line(surf, dark_col, (int(g0[0]), int(g0[1])), (int(g1[0]), int(g1[1])), 4)
        pygame.draw.line(surf, accent_col, (int(g0[0]), int(g0[1])), (int(g1[0]), int(g1[1])), 2)
        pygame.draw.circle(surf, accent_col, (int(cx), int(cy)), 4)
        pygame.draw.circle(surf, (255, 255, 255), (int(cx), int(cy)), 2)

    def _draw_rune_sigil(self, surf, cx, cy, t, ring_col, glyph_col):
        t = max(0.0, min(1.0, t))
        rx = int(44 * t + 6)
        ry = int(rx * 0.40)
        ring = pygame.Surface((rx * 2 + 8, ry * 2 + 8), pygame.SRCALPHA)
        alpha = int(100 + 120 * t)
        pygame.draw.ellipse(ring, (*ring_col, alpha), (2, 2, rx * 2 + 4, ry * 2 + 4), 2)
        pygame.draw.ellipse(
            ring, (*ring_col, alpha // 2),
            (6, 4, rx * 2 - 4, ry * 2),
            1,
        )
        for a_deg in (0, 90, 180, 270):
            a = math.radians(a_deg + self._anim_tick * 1.5)
            gx = rx + 4 + math.cos(a) * rx
            gy = ry + 4 + math.sin(a) * ry
            pygame.draw.line(
                ring, (*glyph_col, alpha),
                (int(gx) - 3, int(gy) - 3), (int(gx) + 3, int(gy) + 3), 2,
            )
            pygame.draw.line(
                ring, (*glyph_col, alpha),
                (int(gx) - 3, int(gy) + 3), (int(gx) + 3, int(gy) - 3), 2,
            )
        surf.blit(ring, ring.get_rect(midbottom=(cx, cy)))

    def _draw_silver_rain_cast_pose(self, surf, t):
        """While casting Silver Rain the boss draws a ring of silver runes
        above her head + upward-streaming motes. Ground-zone circles are
        drawn by the SilverRainZone entities after they spawn.
        """
        cx = int(self.x)
        cy = int(self.y) - 60
        # halo ring of 6 orbiting motes
        for i in range(6):
            a = (i / 6) * math.tau + self._anim_tick * 0.07
            r = 22 + int(math.sin(self._anim_tick * 0.15 + i) * 2)
            px = cx + math.cos(a) * r
            py = cy + math.sin(a) * r * 0.45
            pygame.draw.circle(surf, (220, 235, 250), (int(px), int(py)), 3)
        # central charge orb that brightens over the telegraph
        orb_r = int(6 + 8 * t)
        orb = pygame.Surface((orb_r * 2 + 6, orb_r * 2 + 6), pygame.SRCALPHA)
        pygame.draw.circle(orb, (170, 200, 230, 200), (orb_r + 3, orb_r + 3), orb_r)
        pygame.draw.circle(orb, (240, 250, 255, 255), (orb_r + 3, orb_r + 3), max(1, orb_r - 3))
        surf.blit(orb, orb.get_rect(center=(cx, cy)))
        # upward streaks
        if t > 0.3 and self._anim_tick % 3 == 0:
            tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            for k in range(3):
                sx = cx + (k - 1) * 6
                pygame.draw.line(
                    tmp, (230, 245, 255, int(120 * t)),
                    (sx, cy), (sx, cy - 30), 1,
                )
            surf.blit(tmp, (0, 0))

    def _draw_volley_telegraph(self, surf, t):
        """5 charging shard-points around the weaver's hand, pointing at
        the player. Fan spreads open as t approaches 1.
        """
        cx = int(self.x + self.facing * 20)
        cy = int(self.y - 14)
        # five small diamond charge points in an arc
        spread = C.SHARD_VOLLEY_SPREAD * t
        step = spread / max(1, C.SHARD_VOLLEY_COUNT - 1)
        base = 0 if self.facing == 1 else math.pi
        for i in range(C.SHARD_VOLLEY_COUNT):
            a = base + (i - (C.SHARD_VOLLEY_COUNT - 1) / 2) * step
            rr = 22 + int(t * 16)
            px = cx + math.cos(a) * rr
            py = cy + math.sin(a) * rr
            pts = [
                (int(px) + 5, int(py)), (int(px), int(py) - 4),
                (int(px) - 5, int(py)), (int(px), int(py) + 4),
            ]
            pygame.draw.polygon(surf, (170, 200, 230), pts)
            pygame.draw.polygon(surf, (230, 245, 255), [
                (int(px) + 3, int(py)), (int(px), int(py) - 2),
                (int(px) - 3, int(py)), (int(px), int(py) + 2),
            ])
        # central hand glow
        core = pygame.Surface((14, 14), pygame.SRCALPHA)
        pygame.draw.circle(core, (200, 225, 245, 200), (7, 7), 5)
        pygame.draw.circle(core, (255, 255, 255, 240), (7, 7), 2)
        surf.blit(core, core.get_rect(center=(cx, cy)))

    def _draw_phantom_telegraph(self, surf, t):
        """A silver-tinted outline traces the player's recent path."""
        # The path is held by the player; we just show the boss charging.
        cx = int(self.x + self.facing * 20)
        cy = int(self.y - 14)
        # rotating triple-ring charge
        for i in range(3):
            r = int(8 + 18 * t + i * 3)
            phase = self._anim_tick * 0.15 + i * math.tau / 3
            ox = cx + int(math.cos(phase) * 3)
            oy = cy + int(math.sin(phase) * 3)
            ring = pygame.Surface((r * 2 + 6, r * 2 + 6), pygame.SRCALPHA)
            pygame.draw.circle(
                ring, (180, 210, 240, int(180 * (1 - i * 0.2))),
                (r + 3, r + 3), r, 2
            )
            surf.blit(ring, ring.get_rect(center=(ox, oy)))
        # central core
        core = pygame.Surface((14, 14), pygame.SRCALPHA)
        pygame.draw.circle(core, (220, 235, 250), (7, 7), 4)
        pygame.draw.circle(core, (255, 255, 255), (7, 7), 2)
        surf.blit(core, core.get_rect(center=(cx, cy)))
