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
        # transient per-state data for rich visuals
        self._sweep_trail = []    # list of (x, y, tip_x, tip_y, life)
        self._anim_tick = 0       # monotonic for orbiting particle phases

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
        self._anim_tick += 1
        if self.intro_timer > 0:
            self.intro_timer -= 1
        if self.flash > 0:
            self.flash -= 1
        # fade out sweep-trail ghosts
        self._sweep_trail = [
            (x, y, tx, ty, life - 1)
            for (x, y, tx, ty, life) in self._sweep_trail
            if life > 1
        ]

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
            # record a blade-trail sample for the current swing angle
            t = 1.0 - self.state_timer / 22.0
            ang = self.sweep_blade_angle(t)
            rad = math.radians(ang)
            hx = self.x + self.facing * 10
            hy = self.y - 20
            tip_x = hx + math.cos(rad) * 90
            tip_y = hy + math.sin(rad) * 90
            self._sweep_trail.append((hx, hy, tip_x, tip_y, 10))
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

    # ---------- attack geometry ----------

    def sweep_blade_angle(self, t):
        """Blade angle in degrees at normalized sweep progress t in [0, 1].
        The sword starts raised overhead and sweeps down past the boss.
        """
        # for facing right: -75 -> +115 (overhead to downward-forward)
        start, end = -75, 115
        angle = start + (end - start) * max(0.0, min(1.0, t))
        if self.facing == -1:
            angle = 180 - angle
        return angle

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

        # ---- sweep telegraph: crescent arc outline revealing swing path ----
        if self.state == "sweep_telegraph":
            t = 1.0 - (self.state_timer / 34.0)
            self._draw_sweep_telegraph(surf, t)

        # ---- sweep active: glowing blade swung through an arc, with trail ----
        if self.state == "sweep":
            self._draw_sweep_active(surf)

        # ---- bolt telegraph: orbiting energy + growing crown orb ----
        if self.state == "bolt_telegraph":
            t = 1.0 - (self.state_timer / 28.0)
            self._draw_bolt_telegraph(surf, t)

        # ---- ring slam telegraph: runic circle of glyphs around the feet ----
        if self.state == "ring_slam_telegraph":
            t = 1.0 - (self.state_timer / 42.0)
            self._draw_ring_telegraph(surf, t)

        # ---- active ring slam: jagged shockwave with leading sparks ----
        if self.ring_slam_active and self.ring_slam_radius > 0:
            self._draw_ring_slam(surf)

    # ---------- rich attack visuals ----------

    def _draw_sweep_telegraph(self, surf, t):
        """Arc outline tracing where the blade will pass + charging spark at the
        weapon hand. t in [0, 1] through the 34-frame windup.
        """
        cx = self.x + self.facing * 10
        cy = self.y - 20
        radius = 88
        start_deg, end_deg = -75, 115
        if self.facing == -1:
            start_deg, end_deg = 255, 65
        # sample points along the arc
        segs = 28
        pts = []
        for i in range(segs + 1):
            a = math.radians(start_deg + (end_deg - start_deg) * i / segs)
            pts.append((cx + math.cos(a) * radius, cy + math.sin(a) * radius))
        # faint outer guideline (full arc)
        guide_alpha = int(60 + 120 * t)
        for i in range(0, len(pts) - 1, 2):
            p0, p1 = pts[i], pts[i + 1]
            pygame.draw.line(
                surf, (255, 90, 70, guide_alpha),
                (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), 2
            )
        # growing bright leading edge that reveals the strike direction
        reveal = int((segs + 1) * t)
        if reveal >= 2:
            seg_pts = [(int(x), int(y)) for (x, y) in pts[:reveal]]
            pygame.draw.lines(surf, (255, 180, 90), False, seg_pts, 3)
            if len(seg_pts) >= 1:
                pygame.draw.circle(surf, (255, 240, 180), seg_pts[-1], 4)
        # pulsing charge orb at the hand
        orb_r = 4 + int(t * 8) + (self._anim_tick // 4) % 2
        orb = pygame.Surface((orb_r * 2 + 6, orb_r * 2 + 6), pygame.SRCALPHA)
        pygame.draw.circle(orb, (255, 140, 70, 200), (orb_r + 3, orb_r + 3), orb_r)
        pygame.draw.circle(orb, (255, 220, 150, 255), (orb_r + 3, orb_r + 3), max(1, orb_r - 3))
        surf.blit(orb, orb.get_rect(center=(int(cx), int(cy))))

    def _draw_sweep_active(self, surf):
        """Glowing blade swept through an arc, with afterimage trail."""
        t = 1.0 - self.state_timer / 22.0
        cx = self.x + self.facing * 10
        cy = self.y - 20
        # afterimage ghosts
        for (hx, hy, tx, ty, life) in self._sweep_trail:
            alpha = int(200 * (life / 10.0))
            col = (255, 180, 90, alpha)
            trail = pygame.Surface(
                (surf.get_width(), surf.get_height()), pygame.SRCALPHA
            )
            pygame.draw.line(trail, col, (int(hx), int(hy)), (int(tx), int(ty)), 3)
            surf.blit(trail, (0, 0))
        # current blade
        ang = self.sweep_blade_angle(t)
        rad = math.radians(ang)
        tip_x = cx + math.cos(rad) * 96
        tip_y = cy + math.sin(rad) * 96
        # blade body (thick white-hot core + warmer outer stroke)
        pygame.draw.line(surf, (180, 60, 40), (int(cx), int(cy)), (int(tip_x), int(tip_y)), 7)
        pygame.draw.line(surf, (255, 180, 90), (int(cx), int(cy)), (int(tip_x), int(tip_y)), 4)
        pygame.draw.line(surf, (255, 250, 220), (int(cx), int(cy)), (int(tip_x), int(tip_y)), 2)
        # bright tip
        pygame.draw.circle(surf, (255, 240, 200), (int(tip_x), int(tip_y)), 5)

    def _draw_bolt_telegraph(self, surf, t):
        """Orbiting particles converging on the crown + central charge orb."""
        cx = self.x + self.facing * 20
        cy = self.y - 10
        # orbiting charge points (spiral inward as t grows)
        orbit_count = 8
        base_r = 42 * (1 - t) + 10
        for i in range(orbit_count):
            phase = (self._anim_tick * 0.18) + i * (math.tau / orbit_count)
            r = base_r + math.sin(phase * 2) * 2
            ox = cx + math.cos(phase) * r
            oy = cy + math.sin(phase) * r
            col = (255, 200, 120)
            pygame.draw.circle(surf, col, (int(ox), int(oy)), 2)
            # trailing streak
            tail_phase = phase - 0.15
            tx = cx + math.cos(tail_phase) * r
            ty = cy + math.sin(tail_phase) * r
            pygame.draw.line(
                surf, (200, 120, 60),
                (int(ox), int(oy)), (int(tx), int(ty)), 1
            )
        # central charge orb with inner hot core
        rr = int(6 + 14 * t)
        orb = pygame.Surface((rr * 2 + 8, rr * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(orb, (240, 140, 60, 150), (rr + 4, rr + 4), rr)
        pygame.draw.circle(orb, (255, 220, 150, 220), (rr + 4, rr + 4), max(1, rr - 4))
        pygame.draw.circle(orb, (255, 255, 230, 255), (rr + 4, rr + 4), max(1, rr - 9))
        surf.blit(orb, orb.get_rect(center=(int(cx), int(cy))))

    def _draw_ring_telegraph(self, surf, t):
        """Runic glyphs around the boss's feet with a pulsing dashed ring."""
        cx, cy = int(self.x), int(self.y) + 18
        radius = 60
        glyph_count = 6
        pulse = (math.sin(self._anim_tick * 0.3) + 1) * 0.5     # 0..1
        # dashed outer ring
        segs = 48
        for i in range(segs):
            if i % 2 == 0:
                continue
            a0 = (i / segs) * math.tau
            a1 = ((i + 1) / segs) * math.tau
            p0 = (cx + math.cos(a0) * radius, cy + math.sin(a0) * radius * 0.5)
            p1 = (cx + math.cos(a1) * radius, cy + math.sin(a1) * radius * 0.5)
            alpha = int(130 + 100 * t)
            tmp = pygame.Surface(
                (surf.get_width(), surf.get_height()), pygame.SRCALPHA
            )
            pygame.draw.line(
                tmp, (220, 90, 80, alpha),
                (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), 2
            )
            surf.blit(tmp, (0, 0))
        # runic glyphs
        for i in range(glyph_count):
            a = (i / glyph_count) * math.tau + self._anim_tick * 0.01
            gx = cx + math.cos(a) * radius
            gy = cy + math.sin(a) * radius * 0.5
            brightness = int(140 + 115 * (pulse * t))
            col = (brightness, min(255, int(brightness * 0.55)), 60)
            # small cross glyph (rotated X)
            pygame.draw.line(surf, col, (int(gx) - 4, int(gy) - 4), (int(gx) + 4, int(gy) + 4), 2)
            pygame.draw.line(surf, col, (int(gx) - 4, int(gy) + 4), (int(gx) + 4, int(gy) - 4), 2)
            # vertical light beam shooting up as t grows
            if t > 0.35:
                beam_h = int(30 * (t - 0.3) * 1.5)
                tmp = pygame.Surface((4, beam_h + 4), pygame.SRCALPHA)
                for by in range(beam_h):
                    a2 = max(0, 200 - by * 6)
                    pygame.draw.line(tmp, (240, 120, 70, a2), (1, beam_h - by), (3, beam_h - by))
                surf.blit(tmp, tmp.get_rect(midbottom=(int(gx), int(gy))))
        # converging cross marks aimed at the boss
        if t > 0.5:
            for sign in (-1, 1):
                axis_alpha = int(200 * (t - 0.5) * 2)
                tmp = pygame.Surface(
                    (surf.get_width(), surf.get_height()), pygame.SRCALPHA
                )
                pygame.draw.line(
                    tmp, (255, 160, 90, axis_alpha),
                    (cx + sign * radius, cy), (cx + sign * (radius - 18), cy), 3
                )
                pygame.draw.line(
                    tmp, (255, 160, 90, axis_alpha),
                    (cx, cy + sign * int(radius * 0.5)),
                    (cx, cy + sign * int(radius * 0.5 - 14)), 3
                )
                surf.blit(tmp, (0, 0))

    def _draw_ring_slam(self, surf):
        """Jagged shockwave edge with debris-flecked inner echo."""
        r = int(self.ring_slam_radius)
        cx, cy = int(self.x), int(self.y)
        # life progress 0..1 for colour fade
        max_r = 480
        life = max(0.0, 1.0 - r / max_r)
        alpha = int(255 * life)
        overlay = pygame.Surface((surf.get_width(), surf.get_height()), pygame.SRCALPHA)
        # jagged outer edge - sample 32 points and push alternate in/out
        n = 40
        pts = []
        for i in range(n):
            a = (i / n) * math.tau
            jitter = 1.0 + (0.12 if i % 2 == 0 else -0.08)
            rr = r * jitter
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        if len(pts) >= 3:
            pygame.draw.polygon(overlay, (255, 200, 110, alpha), pts, 6)
        # inner echo (smooth, trailing)
        if r > 22:
            pygame.draw.circle(
                overlay, (255, 140, 70, max(0, alpha - 60)),
                (cx, cy), max(1, r - 18), 4
            )
        # radial spark rays at the leading edge
        for i in range(0, n, 5):
            a = (i / n) * math.tau
            pygame.draw.line(
                overlay, (255, 240, 180, alpha),
                (cx + math.cos(a) * (r - 4), cy + math.sin(a) * (r - 4)),
                (cx + math.cos(a) * (r + 8), cy + math.sin(a) * (r + 8)),
                2,
            )
        surf.blit(overlay, (0, 0))
