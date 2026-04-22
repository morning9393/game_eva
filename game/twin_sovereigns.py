"""Level 3 - The Twin Sovereigns.

Two bosses on the field simultaneously: Solar King (gold) and Lunar King
(indigo). A 12-second day/night cycle flips which king is ACTIVE - only the
active king takes damage and attacks the player. The inactive king is
spectral (reduced-opacity sprite) and drifts passively toward the player.

When one king dies, the other locks to permanently-active (no more cycling).
"""
import math
import random
import pygame

from . import constants as C
from . import sprites
from .utils import clamp, vec_from_to, clamp_to_arena


class Sunlance:
    """Straight piercing beam fired by the Solar King.
    Telegraphs as a line for ~40 frames, then becomes a solid bright beam
    for ~60 frames that damages on contact.
    """

    def __init__(self, x, y, dx, dy):
        self.x = float(x)
        self.y = float(y)
        norm = math.hypot(dx, dy) or 1.0
        self.dx = dx / norm
        self.dy = dy / norm
        self.phase = "telegraph"
        self.timer = C.TWIN_SUNLANCE_WINDUP
        self.life = C.TWIN_SUNLANCE_WINDUP + C.TWIN_SUNLANCE_LIFE
        self.alive = True
        self.has_hit = False

    def update(self):
        self.life -= 1
        self.timer -= 1
        if self.timer <= 0:
            if self.phase == "telegraph":
                self.phase = "active"
                self.timer = C.TWIN_SUNLANCE_LIFE
            else:
                self.alive = False
        if self.life <= 0:
            self.alive = False

    def beam_length(self):
        return 900  # spans the arena

    def endpoints(self):
        L = self.beam_length()
        return (self.x, self.y), (self.x + self.dx * L, self.y + self.dy * L)

    def hits_rect(self, rect):
        """Returns True if the beam line passes through the rect (active only)."""
        if self.phase != "active":
            return False
        # simple segment-vs-rect: sample points along beam within the rect's
        # bounding span and test
        (x0, y0), (x1, y1) = self.endpoints()
        steps = 48
        for i in range(steps + 1):
            t = i / steps
            px = x0 + (x1 - x0) * t
            py = y0 + (y1 - y0) * t
            if rect.collidepoint(px, py):
                return True
        return False

    def draw(self, surf):
        (x0, y0), (x1, y1) = self.endpoints()
        if self.phase == "telegraph":
            t = 1.0 - self.timer / C.TWIN_SUNLANCE_WINDUP
            # pulsing thin line that thickens over time
            tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            alpha = int(90 + 130 * t)
            pygame.draw.line(
                tmp, (255, 200, 80, alpha),
                (int(x0), int(y0)), (int(x1), int(y1)), 2,
            )
            if t > 0.5:
                pygame.draw.line(
                    tmp, (255, 240, 160, alpha),
                    (int(x0), int(y0)), (int(x1), int(y1)), 1,
                )
            surf.blit(tmp, (0, 0))
        else:
            # active solid beam
            w = C.TWIN_SUNLANCE_WIDTH
            tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            # outer glow
            pygame.draw.line(tmp, (255, 180, 80, 180),
                             (int(x0), int(y0)), (int(x1), int(y1)), w)
            # hot core
            pygame.draw.line(tmp, (255, 240, 160, 255),
                             (int(x0), int(y0)), (int(x1), int(y1)), w // 2)
            # white-hot centerline
            pygame.draw.line(tmp, (255, 255, 255, 255),
                             (int(x0), int(y0)), (int(x1), int(y1)), 2)
            surf.blit(tmp, (0, 0))


class SolarFlare:
    """Expanding fire ring from the Solar King's position. Telegraph shows
    a bright central burst, then a ring grows outward; its edge damages
    anything it passes through.
    """

    def __init__(self, x, y):
        self.cx = float(x)
        self.cy = float(y)
        self.phase = "telegraph"
        self.timer = C.SOLAR_FLARE_TELEGRAPH
        self.life = C.SOLAR_FLARE_TELEGRAPH + C.SOLAR_FLARE_GROWTH
        self.alive = True
        self.radius = 0
        self.has_hit = False
        self.age = 0

    def update(self):
        self.age += 1
        self.life -= 1
        self.timer -= 1
        if self.phase == "telegraph":
            if self.timer <= 0:
                self.phase = "active"
                self.timer = C.SOLAR_FLARE_GROWTH
                self.has_hit = False
        else:
            # grow the ring
            frac = 1.0 - (self.timer / max(1, C.SOLAR_FLARE_GROWTH))
            self.radius = int(C.SOLAR_FLARE_MAX_RADIUS * frac)
            if self.timer <= 0:
                self.alive = False

    def hits_player(self, player):
        if self.phase != "active":
            return False
        d = math.hypot(player.x - self.cx, player.y - self.cy)
        return abs(d - self.radius) < C.SOLAR_FLARE_EDGE_WIDTH // 2 + 12

    def draw(self, surf):
        if self.phase == "telegraph":
            t = 1.0 - self.timer / C.SOLAR_FLARE_TELEGRAPH
            r = int(12 + 24 * t)
            core = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(core, (255, 170, 80, int(140 + 100 * t)),
                               (r + 4, r + 4), r)
            pygame.draw.circle(core, (255, 240, 180, 255),
                               (r + 4, r + 4), max(1, r - 6))
            surf.blit(core, core.get_rect(center=(int(self.cx), int(self.cy))))
            # pulsing warning ring
            wr = int(28 + 22 * t)
            ring = pygame.Surface((wr * 2 + 6, wr * 2 + 6), pygame.SRCALPHA)
            pygame.draw.circle(ring, (255, 180, 100, int(80 + 120 * t)),
                               (wr + 3, wr + 3), wr, 2)
            surf.blit(ring, ring.get_rect(center=(int(self.cx), int(self.cy))))
        else:
            r = self.radius
            if r < 4:
                return
            life_frac = max(0.0, self.timer / max(1, C.SOLAR_FLARE_GROWTH))
            alpha = int(240 * life_frac)
            overlay = pygame.Surface((r * 2 + 10, r * 2 + 10), pygame.SRCALPHA)
            pygame.draw.circle(overlay, (255, 180, 90, alpha),
                               (r + 5, r + 5), r, 6)
            pygame.draw.circle(overlay, (255, 230, 140, int(alpha * 0.7)),
                               (r + 5, r + 5), max(1, r - 6), 3)
            # radial sparks at every 8th of the ring
            for i in range(12):
                a = i * math.tau / 12
                sp_in = (r + 5 + math.cos(a) * (r - 3), r + 5 + math.sin(a) * (r - 3))
                sp_out = (r + 5 + math.cos(a) * (r + 8), r + 5 + math.sin(a) * (r + 8))
                pygame.draw.line(overlay, (255, 240, 180, alpha),
                                 (int(sp_in[0]), int(sp_in[1])),
                                 (int(sp_out[0]), int(sp_out[1])), 2)
            surf.blit(overlay, overlay.get_rect(center=(int(self.cx), int(self.cy))))


class StarFall:
    """Dark star-mark telegraphed on the ground; detonates after a warning
    period into an AoE circle. Spawned 3 at a time using the player's past
    positions from path history.
    """

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.phase = "warning"
        self.timer = C.STAR_FALL_TELEGRAPH
        self.alive = True
        self.has_hit = False
        self.age = 0

    def update(self):
        self.age += 1
        self.timer -= 1
        if self.phase == "warning" and self.timer <= 0:
            self.phase = "detonate"
            self.timer = 18
            self.has_hit = False
        elif self.phase == "detonate" and self.timer <= 0:
            self.alive = False

    def hits_player(self, player):
        if self.phase != "detonate":
            return False
        return math.hypot(self.x - player.x, self.y - player.y) <= C.STAR_FALL_RADIUS

    def draw(self, surf):
        cx, cy = int(self.x), int(self.y)
        if self.phase == "warning":
            t = 1.0 - self.timer / C.STAR_FALL_TELEGRAPH
            r = C.STAR_FALL_RADIUS
            alpha = int(80 + 160 * t)
            pulse = (math.sin(self.age * 0.3) + 1) * 0.5
            ring = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(ring, (60, 80, 140, alpha), (r + 4, r + 4), r, 2)
            pygame.draw.circle(
                ring, (130, 150, 210, int(alpha * 0.7)),
                (r + 4, r + 4), max(4, int(r * 0.7 + pulse * 4)), 2,
            )
            surf.blit(ring, ring.get_rect(center=(cx, cy)))
            # star insignia at center
            for a_deg in (0, 72, 144, 216, 288):
                a = math.radians(a_deg + self.age * 2)
                ex = cx + math.cos(a) * 8
                ey = cy + math.sin(a) * 8
                pygame.draw.line(surf, (200, 210, 240), (cx, cy), (int(ex), int(ey)), 1)
            pygame.draw.circle(surf, (200, 210, 240), (cx, cy), 3)
        else:
            # detonation burst
            t = self.timer / 18.0
            r = int(C.STAR_FALL_RADIUS * (1.0 - t * 0.3))
            overlay = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(overlay, (120, 130, 200, int(220 * t)),
                               (r + 4, r + 4), r)
            pygame.draw.circle(overlay, (200, 220, 250, int(240 * t)),
                               (r + 4, r + 4), max(1, r - 10))
            pygame.draw.circle(overlay, (40, 60, 120, int(200 * t)),
                               (r + 4, r + 4), r, 4)
            surf.blit(overlay, overlay.get_rect(center=(cx, cy)))


class LunarOrbit:
    """Crescent that orbits around the player and spirals inward.
    Damages on contact; one-shot (destroyed after hitting).
    """

    def __init__(self, target_x, target_y):
        self.cx = float(target_x)
        self.cy = float(target_y)
        self.angle = random.uniform(0, math.tau)
        self.radius = 160.0
        self.alive = True
        self.life = C.TWIN_LUNAR_ORBIT_LIFE
        self.speed = 0.06
        self.radius_shrink = 0.18

    def update(self, player):
        self.life -= 1
        if self.life <= 0:
            self.alive = False
            return
        # track the player slowly
        self.cx += (player.x - self.cx) * 0.02
        self.cy += (player.y - self.cy) * 0.02
        self.angle += self.speed
        self.radius = max(40, self.radius - self.radius_shrink)

    @property
    def x(self):
        return self.cx + math.cos(self.angle) * self.radius

    @property
    def y(self):
        return self.cy + math.sin(self.angle) * self.radius

    def hits_player(self, player):
        return math.hypot(self.x - player.x, self.y - player.y) < 22

    def draw(self, surf):
        # tether line from player center to crescent
        tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.line(
            tmp, (150, 170, 220, 80),
            (int(self.cx), int(self.cy)), (int(self.x), int(self.y)), 1,
        )
        surf.blit(tmp, (0, 0))
        # crescent body
        cx, cy = int(self.x), int(self.y)
        pygame.draw.circle(surf, (210, 220, 240), (cx, cy), 11)
        pygame.draw.circle(surf, (40, 50, 90), (cx + 4, cy - 1), 10)
        pygame.draw.circle(surf, (255, 255, 255), (cx - 2, cy - 2), 3)


class SovereignKing:
    """One of the Twin Sovereigns - parametrized by role ('solar' or 'lunar').
    Only damageable while active. Inactive kings drift passively toward player.
    """

    def __init__(self, x, y, role):
        self.role = role
        self.x = float(x)
        self.y = float(y)
        self.hp = C.TWIN_BOSS_HP
        self.max_hp = C.TWIN_BOSS_HP
        self.alive = True
        self.active = (role == "solar")  # solar starts active (day)
        self.locked_active = False       # when other twin dies
        self.phase = 1                    # for HUD compatibility
        self.facing = -1
        self.flash = 0
        self.intro_timer = 90
        self.enraged_anim = 0
        self.state = "idle"
        self.state_timer = 60
        self.attack_cooldown = 120
        self.bob = 0.0
        self.radius = 22
        self._sprite_cache = {}

    def _sprite(self):
        key = (self.role, self.active)
        if key not in self._sprite_cache:
            if self.role == "solar":
                self._sprite_cache[key] = sprites.make_solar_king_sprite(self.active)
            else:
                self._sprite_cache[key] = sprites.make_lunar_king_sprite(self.active)
        return self._sprite_cache[key]

    def set_active(self, active):
        if self.active != active:
            self.active = active

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 28, int(self.y) - 44, 56, 84)

    def sweep_hitbox(self):
        return None

    def receive_player_hit(self, damage):
        """Returns outcome dict. Inactive kings are intangible (no damage)."""
        if not self.active:
            return {"dealt": 0, "band": "intangible"}
        self.hp -= damage
        self.flash = 8
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
        # drift toward player slowly (both roles) so the fight never stalls
        dx, dy, dist = vec_from_to(self.x, self.y, player.x, player.y)
        speed = 1.4 if self.active else 0.6
        if dist > 150:
            self.x += dx * speed
            self.y += dy * speed
            self.facing = 1 if dx >= 0 else -1
        self.x, self.y = clamp_to_arena(self.x, self.y, pad=40)
        # cooldown tick
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

    def want_to_attack(self):
        return self.active and self.attack_cooldown <= 0 and self.intro_timer == 0

    def pick_attack(self):
        """Decide which attack to queue - primary or secondary skill."""
        if self.role == "solar":
            return random.choice(["sunlance", "solar_flare"])
        return random.choice(["lunar_orbit", "star_fall"])

    def on_attacked(self):
        # after launching an attack, cooldown
        interval = 150 if self.role == "solar" else 200
        self.attack_cooldown = interval

    def draw(self, surf):
        spr = self._sprite()
        bob_y = int(math.sin(self.bob) * 3)
        flip = self.facing == -1
        drawn = pygame.transform.flip(spr, True, False) if flip else spr
        rect = drawn.get_rect(midbottom=(int(self.x), int(self.y) + 44 + bob_y))
        if self.flash > 0:
            # Bake the flash into a sprite copy so transparent corners stay
            # transparent. BLEND_RGB_ADD brightens visible pixels; alpha
            # channel is left untouched.
            intensity = min(180, self.flash * 28)
            flashed = drawn.copy()
            overlay = pygame.Surface(flashed.get_size(), pygame.SRCALPHA)
            overlay.fill((intensity, intensity, intensity, 255))
            flashed.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            surf.blit(flashed, rect)
        else:
            surf.blit(drawn, rect)
        # a subtle halo/aura for active king
        if self.active:
            aura = pygame.Surface((80, 80), pygame.SRCALPHA)
            col = (255, 200, 120, 80) if self.role == "solar" else (140, 170, 230, 90)
            pygame.draw.circle(aura, col, (40, 40), 38, 3)
            surf.blit(aura, aura.get_rect(center=(int(self.x), int(self.y) - 20)))


class TwinSovereigns:
    """Holds both kings + shared cycle logic. Acts as the 'boss' in app.py."""

    def __init__(self, cx, cy):
        self.solar = SovereignKing(cx + 180, cy - 40, "solar")
        self.lunar = SovereignKing(cx - 180, cy + 40, "lunar")
        self.solar.active = True
        self.lunar.active = False
        self.cycle_timer = C.TWIN_CYCLE_FRAMES
        self.day_phase = "day"   # "day" or "night"
        self.pending_flash = 0   # brief overlay on phase flip
        self.intro_timer = 90
        self.enraged_anim = 0
        self.sunlance_request = None   # (x, y, dx, dy) queued for app
        self.lunar_orbit_request = False
        self.solar_flare_request = None    # (x, y) for Solar Flare origin
        self.star_fall_request = None      # list of (x, y) for Star Fall targets
        self.phase = 1
        # HUD compatibility
        self.max_hp = C.TWIN_BOSS_HP
        self.state = "idle"

    # ---- compatibility with single-boss HUD code ----

    @property
    def hp(self):
        # show whichever is currently active in the "main" HP slot
        return self.active.hp

    @property
    def alive(self):
        return self.solar.alive or self.lunar.alive

    @property
    def active(self):
        return self.solar if self.day_phase == "day" else self.lunar

    @property
    def inactive(self):
        return self.lunar if self.day_phase == "day" else self.solar

    @property
    def rect(self):
        return self.active.rect

    @property
    def x(self):
        return self.active.x

    @property
    def y(self):
        return self.active.y

    @property
    def facing(self):
        return self.active.facing

    def sweep_hitbox(self):
        return None

    def receive_player_hit(self, damage):
        return self.active.receive_player_hit(damage)

    def update(self, player):
        if self.intro_timer > 0:
            self.intro_timer -= 1
        if self.pending_flash > 0:
            self.pending_flash -= 1
        # day/night cycle (disabled after one king dies)
        both_alive = self.solar.alive and self.lunar.alive
        if both_alive:
            self.cycle_timer -= 1
            if self.cycle_timer <= 0:
                self._flip_cycle()
                self.cycle_timer = C.TWIN_CYCLE_FRAMES
        else:
            # survivor locks to active
            if self.solar.alive:
                self.solar.active = True
                self.solar.locked_active = True
                self.lunar.active = False
                self.day_phase = "day"
            elif self.lunar.alive:
                self.lunar.active = True
                self.lunar.locked_active = True
                self.solar.active = False
                self.day_phase = "night"
        # both kings think each frame
        self.solar.update(player)
        self.lunar.update(player)
        # active king decides which attack to launch
        if self.active.want_to_attack():
            choice = self.active.pick_attack()
            if choice == "sunlance":
                dx, dy, _ = vec_from_to(self.active.x, self.active.y, player.x, player.y)
                self.sunlance_request = (self.active.x, self.active.y - 20, dx, dy)
            elif choice == "solar_flare":
                self.solar_flare_request = (self.active.x, self.active.y - 20)
            elif choice == "lunar_orbit":
                self.lunar_orbit_request = True
            elif choice == "star_fall":
                # pick 3 past player positions spread across path history
                hist = [(p[0], p[1]) for p in player.path_history]
                targets = []
                if hist:
                    step = max(1, len(hist) // C.STAR_FALL_COUNT)
                    for i in range(C.STAR_FALL_COUNT):
                        idx = min(len(hist) - 1, i * step)
                        targets.append(hist[idx])
                if not targets:
                    # fallback: scatter around player
                    for _ in range(C.STAR_FALL_COUNT):
                        targets.append((
                            player.x + random.randint(-60, 60),
                            player.y + random.randint(-60, 60),
                        ))
                self.star_fall_request = targets
            self.active.on_attacked()

    def _flip_cycle(self):
        self.day_phase = "night" if self.day_phase == "day" else "day"
        self.solar.set_active(self.day_phase == "day")
        self.lunar.set_active(self.day_phase == "night")
        self.pending_flash = 30

    def draw(self, surf):
        # draw inactive first (back), then active (front)
        if self.inactive.alive:
            self.inactive.draw(surf)
        if self.active.alive:
            self.active.draw(surf)
        # cycle-flip flash overlay
        if self.pending_flash > 0:
            t = self.pending_flash / 30.0
            col = (255, 220, 160, int(100 * t)) if self.day_phase == "day" else (150, 170, 230, int(110 * t))
            overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            overlay.fill(col)
            surf.blit(overlay, (0, 0))
