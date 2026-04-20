"""Main application / game loop for Crown of Hollow."""
import math
import random
import sys

import pygame

from . import constants as C
from . import sprites
from .boss import Boss
from .mirrorwright import Mirrorwright, Phantom
from .particles import ParticleSystem
from .player import Player
from .projectile import CrownBolt
from .shard import Shard
from .ui import HUD
from .utils import circle_rect_collide, clamp, clamp_to_arena, inside_arena, random_point_in_arena

LEVELS = [
    {
        "id": 1,
        "title": "The Hollow King",
        "subtitle": "a crownbreaker's vigil",
        "blurb": "Resonance builds with every strike. Break shards to drain it.",
    },
    {
        "id": 2,
        "title": "The Mirrorwright",
        "subtitle": "chamber of quicksilver",
        "blurb": "Hits queue in his mirror orb. Dash-shatter to unload, or explode.",
    },
]

TEST_CODE = "114514"
TEST_CODE_MAX_LEN = 6

DIGIT_KEYS = {
    pygame.K_0: "0", pygame.K_1: "1", pygame.K_2: "2", pygame.K_3: "3",
    pygame.K_4: "4", pygame.K_5: "5", pygame.K_6: "6", pygame.K_7: "7",
    pygame.K_8: "8", pygame.K_9: "9",
    pygame.K_KP0: "0", pygame.K_KP1: "1", pygame.K_KP2: "2", pygame.K_KP3: "3",
    pygame.K_KP4: "4", pygame.K_KP5: "5", pygame.K_KP6: "6", pygame.K_KP7: "7",
    pygame.K_KP8: "8", pygame.K_KP9: "9",
}


class Decor:
    """Static decorative entity with a feet-based anchor, sorted by y like
    living entities for fake 2.5D occlusion. Optionally carries a small
    ground-level collider so the player can bump against it.
    """

    __slots__ = ("x", "y", "sprite", "emits_flame", "collider", "ground")

    def __init__(self, x, y, sprite, emits_flame=False, collider_size=None, ground=False):
        self.x = float(x)
        self.y = float(y)
        self.sprite = sprite
        self.emits_flame = emits_flame
        self.ground = ground  # ground-layer decor draws under everything
        if collider_size is not None:
            w, h = collider_size
            self.collider = pygame.Rect(int(x) - w // 2, int(y) - h, w, h)
        else:
            self.collider = None

    def draw(self, surf):
        rect = self.sprite.get_rect(midbottom=(int(self.x), int(self.y)))
        surf.blit(self.sprite, rect)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(C.TITLE)
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("menlo", 22, bold=True)
        self.font_big = pygame.font.SysFont("menlo", 44, bold=True)
        self.font_small = pygame.font.SysFont("menlo", 14)
        self.state = "title"
        self.shake = 0
        self.level_id = 1
        self.title_selection = 0     # index into LEVELS
        self.floor_tile = None       # set per-level in _init_fight
        # test-mode (tester invulnerability) toggled by code entry on title
        self.test_mode = False
        self.test_code_buffer = ""
        self.test_code_flash = 0     # frames to show confirmation/reject banner
        self.test_code_flash_text = ""
        self.test_code_flash_color = C.AZURE
        self._init_fight()

    # ---------- setup ----------

    def _init_fight(self):
        cx = C.ARENA_X + C.ARENA_W // 2
        cy = C.ARENA_Y + C.ARENA_H // 2
        self.player = Player(cx - 200, cy + 80)
        self.player.test_mode = self.test_mode
        if self.level_id == 2:
            self.boss = Mirrorwright(cx + 160, cy - 40)
            self.floor_tile = sprites.make_floor_tile_level2()
        else:
            self.boss = Boss(cx + 160, cy - 40)
            self.floor_tile = sprites.make_floor_tile()
        self.shards = []
        self.bolts = []
        self.phantoms = []
        self.particles = ParticleSystem()
        self.hud = HUD()
        self.shard_spawn_timer = 180
        self.hits_landed = 0
        self.result_timer = 0
        self._showed_danger_hint = False
        self._showed_shatter_hint = False
        self._build_arena_decor()

    def _build_arena_decor(self):
        """Generate static backgrounds (floor variants + decor props).

        Uses a fixed seed so the arena looks the same each run and doesn't
        shimmer between frames. Branches on level for a different feel.
        """
        rng = random.Random(0xC10DE if self.level_id == 1 else 0xF00D)
        ax, ay, aw, ah = C.ARENA_X, C.ARENA_Y, C.ARENA_W, C.ARENA_H
        cx = ax + aw // 2
        # --- floor layout: vary tiles per level ---
        tile = self.floor_tile
        tw, th = tile.get_size()
        if self.level_id == 2:
            alt_tile = sprites.make_floor_tile_level2_alt()
        else:
            alt_tile = sprites.make_floor_tile_alt()
        cols = (aw // tw) + 1
        rows = (ah // th) + 1
        self._floor_layout = []
        for ry in range(rows):
            row = []
            for rx in range(cols):
                row.append(alt_tile if rng.random() < 0.18 else tile)
            self._floor_layout.append(row)

        # --- decor props (feet position anchored at bottom of sprite) ---
        decor = []
        brazier_spr = sprites.make_brazier_sprite()
        pillar_spr = sprites.make_pillar_sprite()

        if self.level_id == 2:
            # Level 2: a cracked standing mirror at center-back, flanking pillars,
            # scattered mirror shards on the ground
            mirror_spr = sprites.make_vanity_sprite()
            mirror_feet_y = ay + 16 + mirror_spr.get_height()
            decor.append(Decor(cx, mirror_feet_y, mirror_spr, collider_size=(52, 16)))
            # two pillars only, further out, to emphasise the open gallery feel
            pillar_feet_y = ay + 24 + pillar_spr.get_height()
            for px in (ax + 180, ax + aw - 180):
                decor.append(Decor(px, pillar_feet_y, pillar_spr, collider_size=(28, 14)))
            # mirror shards scattered as ground decor (non-blocking)
            shard_spr = sprites.make_mirror_shard_sprite()
            edge_ys = [ay + 120, ay + ah - 60, ay + ah // 2 + 100]
            for _ in range(10):
                ry = rng.choice(edge_ys) + rng.randint(-20, 20)
                rx = rng.randint(ax + 80, ax + aw - 80)
                decor.append(Decor(rx, ry, shard_spr, ground=True))
        else:
            # Level 1: cursed throne room
            throne_spr = sprites.make_throne_sprite()
            throne_feet_y = ay + 16 + throne_spr.get_height()
            decor.append(Decor(cx, throne_feet_y, throne_spr, collider_size=(50, 16)))
            pillar_feet_y = ay + 24 + pillar_spr.get_height()
            pillar_xs = [ax + 140, ax + 300, ax + aw - 300, ax + aw - 140]
            for px in pillar_xs:
                decor.append(Decor(px, pillar_feet_y, pillar_spr, collider_size=(28, 14)))
            rubble_variants = [sprites.make_rubble_sprite(i) for i in range(3)]
            edge_ys = [ay + 120, ay + ah - 60]
            for _ in range(10):
                ry = rng.choice(edge_ys)
                rx = rng.randint(ax + 80, ax + aw - 80)
                spr = rng.choice(rubble_variants)
                decor.append(Decor(rx, ry, spr, ground=True))

        # Four corner braziers - shared across levels
        pad = 60
        brazier_positions = [
            (ax + pad, ay + pad + brazier_spr.get_height()),
            (ax + aw - pad, ay + pad + brazier_spr.get_height()),
            (ax + pad, ay + ah - pad),
            (ax + aw - pad, ay + ah - pad),
        ]
        for bx, by in brazier_positions:
            decor.append(
                Decor(bx, by, brazier_spr, emits_flame=True, collider_size=(26, 14))
            )

        self._decor = decor
        self._torches = [d for d in decor if d.emits_flame]
        self._torch_tick = 0

    # ---------- input helpers ----------

    def _validate_test_code(self):
        """Check the current test_code_buffer; toggle test_mode if it matches."""
        if self.test_code_buffer == TEST_CODE:
            self.test_mode = True
            self.test_code_flash_text = "TEST MODE ENABLED"
            self.test_code_flash_color = (140, 220, 160)
        else:
            self.test_code_flash_text = "INVALID CODE"
            self.test_code_flash_color = (220, 100, 100)
        self.test_code_flash = 140
        self.test_code_buffer = ""

    def _handle_event(self, ev):
        if ev.type == pygame.QUIT:
            pygame.quit()
            sys.exit(0)
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                if self.state in ("fight", "win", "lose"):
                    # back to title
                    self.state = "title"
                    return
                pygame.quit()
                sys.exit(0)
            if self.state == "title":
                if ev.key in DIGIT_KEYS:
                    if len(self.test_code_buffer) < TEST_CODE_MAX_LEN:
                        self.test_code_buffer += DIGIT_KEYS[ev.key]
                        if len(self.test_code_buffer) == TEST_CODE_MAX_LEN:
                            self._validate_test_code()
                elif ev.key == pygame.K_BACKSPACE:
                    self.test_code_buffer = self.test_code_buffer[:-1]
                elif ev.key in (pygame.K_UP, pygame.K_w):
                    self.title_selection = (self.title_selection - 1) % len(LEVELS)
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    self.title_selection = (self.title_selection + 1) % len(LEVELS)
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_j):
                    self.level_id = LEVELS[self.title_selection]["id"]
                    self._init_fight()
                    self.state = "fight"
            elif self.state in ("win", "lose") and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                self._init_fight()
                self.state = "fight"
            elif self.state == "fight":
                if ev.key in (pygame.K_j, pygame.K_SPACE):
                    self.player.try_attack()
                elif ev.key in (pygame.K_k, pygame.K_LSHIFT, pygame.K_RSHIFT):
                    keys = pygame.key.get_pressed()
                    self.player.try_dash(keys)

    # ---------- update ----------

    def _spawn_shard(self, origin=None):
        if len(self.shards) >= C.SHARD_MAX_ON_FIELD:
            return
        # pick a point that's neither too close to the player nor to any
        # existing shard, with a shrinking separation budget on retries so we
        # still succeed in cramped arenas
        MIN_PLAYER_DIST = 90
        MIN_SHARD_DIST = 140
        best = None
        for attempt in range(16):
            if origin:
                ox, oy = origin
                x = ox + random.randint(-140, 140)
                y = oy + random.randint(-110, 110)
                x, y = clamp_to_arena(x, y, pad=50)
            else:
                x, y = random_point_in_arena(pad=60)
            if math.hypot(x - self.player.x, y - self.player.y) < MIN_PLAYER_DIST:
                continue
            # avoid spawning on top of any solid decor (throne, pillars, braziers)
            shard_footprint = pygame.Rect(int(x) - 16, int(y) - 16, 32, 32)
            if any(
                d.collider is not None and d.collider.inflate(16, 16).colliderect(shard_footprint)
                for d in self._decor
            ):
                continue
            # separation from other shards shrinks slightly per failed attempt
            threshold = max(70, MIN_SHARD_DIST - attempt * 6)
            too_close = any(
                math.hypot(x - s.x, y - s.y) < threshold for s in self.shards
            )
            if too_close:
                best = (x, y)     # remember last candidate as fallback
                continue
            best = (x, y)
            break
        if best is None:
            return
        x, y = best
        self.shards.append(Shard(x, y))
        self.particles.spawn_burst(x, y + 14, (120, 90, 70), count=10, speed=2.0, size=3, life=22)

    def _resolve_player_decor_collision(self):
        """Push the player out of any solid decor collider using minimum
        translation along the least-overlapped axis (enables wall sliding).
        """
        rect = self.player.rect
        for d in self._decor:
            col = d.collider
            if col is None or not col.colliderect(rect):
                continue
            dx_right = col.right - rect.left
            dx_left = rect.right - col.left
            dy_down = col.bottom - rect.top
            dy_up = rect.bottom - col.top
            min_overlap = min(dx_right, dx_left, dy_down, dy_up)
            if min_overlap == dx_right:
                self.player.x += dx_right
            elif min_overlap == dx_left:
                self.player.x -= dx_left
            elif min_overlap == dy_down:
                self.player.y += dy_down
            else:
                self.player.y -= dy_up
            rect = self.player.rect
        # re-clamp to arena after pushes
        self.player.x, self.player.y = clamp_to_arena(
            self.player.x, self.player.y, pad=18
        )

    def _anim_frame_mod(self, n):
        """Helper - tick modulo for staggered particle emissions."""
        return pygame.time.get_ticks() % n == 0

    # ---------- per-level update logic ----------

    def _update_level1_specifics(self):
        """Hollow King: shards, resonance, bolts."""
        # boss requests
        if self.boss.spawn_shard_request > 0:
            for _ in range(self.boss.spawn_shard_request):
                self._spawn_shard(origin=(self.boss.x, self.boss.y))
            self.boss.spawn_shard_request = 0
        if self.boss.bolts_to_fire:
            for dx, dy in self.boss.bolts_to_fire:
                ox = self.boss.x + self.boss.facing * 28
                oy = self.boss.y - 20
                self.bolts.append(CrownBolt(ox, oy, dx, dy))
            self.boss.bolts_to_fire = []
            self.particles.spawn_burst(
                self.boss.x + self.boss.facing * 28, self.boss.y - 20,
                C.EMBER, count=14, speed=3.5
            )
        # timed shard spawns
        interval = C.SHARD_SPAWN_INTERVAL_P2 if self.boss.phase == 2 else C.SHARD_SPAWN_INTERVAL_P1
        self.shard_spawn_timer -= 1
        if self.shard_spawn_timer <= 0:
            self.shard_spawn_timer = interval
            self._spawn_shard()
        # shards
        for s in self.shards:
            evt = s.update()
            if evt == "pulse":
                self.particles.spawn_ring(s.x, s.y, C.EMBER, count=28, speed=4.5, size=3, life=24)
                self.shake = max(self.shake, 6)
                if math.hypot(self.player.x - s.x, self.player.y - s.y) <= C.SHARD_PULSE_RADIUS:
                    if self.player.take_hit(1):
                        self.hud.toast("Shard pulse!", C.EMBER, 45)
        self.shards = [s for s in self.shards if s.alive]
        # player sword -> boss/shards
        arect = self.player.attack_rect()
        if arect is not None:
            if id(self.boss) not in self.player.attack_hit_set and arect.colliderect(self.boss.rect):
                result = self.boss.receive_player_hit(C.PLAYER_ATTACK_DAMAGE)
                self.player.attack_hit_set.add(id(self.boss))
                self.hits_landed += 1
                if result["band"] == "danger":
                    self.hud.toast("REJECTED - crown reflects!", C.BLOOD, 70)
                    self.particles.spawn_burst(self.boss.x, self.boss.y - 20, C.BLOOD, count=18, speed=4.0)
                    if self.player.take_hit(result["reflected"]):
                        self.shake = max(self.shake, 10)
                    if not self._showed_danger_hint:
                        self.hud.toast("Break shards to drain Resonance.", C.GOLD, 110)
                        self._showed_danger_hint = True
                else:
                    color = C.WHITE if result["band"] == "safe" else C.GOLD
                    self.particles.spawn_burst(self.boss.x, self.boss.y - 10, color, count=14, speed=3.2)
                    self.shake = max(self.shake, 4 if result["band"] == "safe" else 2)
                    if result["band"] == "warn" and self.hits_landed % 3 == 0:
                        self.hud.toast("Resonance rising...", C.GOLD, 55)
            for s in self.shards:
                if id(s) in self.player.attack_hit_set:
                    continue
                if arect.colliderect(s.rect):
                    broken = s.take_hit(C.PLAYER_ATTACK_DAMAGE)
                    self.player.attack_hit_set.add(id(s))
                    self.particles.spawn_burst(s.x, s.y, C.GOLD, count=10, speed=2.6)
                    if broken:
                        self.boss.drain_resonance(C.SHARD_RESONANCE_DRAIN)
                        self.particles.spawn_ring(s.x, s.y, C.GOLD, count=20, speed=3.2)
                        self.shake = max(self.shake, 5)
                        self.hud.toast("Shard shattered - Resonance drained", C.GOLD, 50)

    def _update_level2_specifics(self):
        """Mirrorwright: mirror orb, dash-shatter, phantoms."""
        # boss phantom request -> spawn phantom that retraces player's path
        if self.boss.phantom_request:
            self.boss.phantom_request = False
            self.phantoms.append(Phantom(self.boss.x, self.boss.y, self.player.path_history))
            self.particles.spawn_burst(
                self.boss.x + self.boss.facing * 20, self.boss.y - 14,
                (200, 220, 240), count=16, speed=3.2, size=3, life=22
            )
            self.shake = max(self.shake, 4)
        # advance phantoms
        for p in self.phantoms:
            p.update()
            if p.alive and math.hypot(p.x - self.player.x, p.y - self.player.y) < 22 \
                    and self.player.iframes == 0:
                if self.player.take_hit(C.PHANTOM_DAMAGE):
                    p.alive = False
                    self.particles.spawn_burst(p.x, p.y, (180, 200, 230), count=14, speed=3.0)
                    self.shake = max(self.shake, 6)
        self.phantoms = [p for p in self.phantoms if p.alive]
        # player sword -> queue damage in mirror orb
        arect = self.player.attack_rect()
        if arect is not None:
            if id(self.boss) not in self.player.attack_hit_set and arect.colliderect(self.boss.rect):
                self.boss.receive_player_hit(C.PLAYER_ATTACK_DAMAGE)
                self.player.attack_hit_set.add(id(self.boss))
                self.hits_landed += 1
                self.particles.spawn_burst(
                    self.boss.x, self.boss.y - 22, (200, 220, 240),
                    count=10, speed=2.4, size=3, life=16
                )
                self.shake = max(self.shake, 2)
                if not self._showed_shatter_hint and self.boss.orb >= self.boss.shatter_threshold * 0.5:
                    self.hud.toast("Dash through the orb to unload the queue.", C.AZURE, 110)
                    self._showed_shatter_hint = True
        # dash-shatter: player currently dashing and passes through orb rect
        if self.player.dash_timer > 0 and self.boss.orb > 0:
            if self.boss.orb_rect().colliderect(self.player.rect):
                dealt = self.boss.trigger_dash_shatter()
                self.hud.toast(f"SHATTER! +{dealt} damage", C.AZURE, 70)
                self.particles.spawn_ring(
                    self.boss.x, self.boss.y - 20, (220, 240, 255),
                    count=40, speed=5.0, size=4, life=30
                )
                self.shake = max(self.shake, 14)
        # auto-shatter if orb at threshold
        if self.boss.orb >= self.boss.shatter_threshold:
            dmg = self.boss.trigger_auto_shatter()
            if self.player.take_hit(dmg):
                self.shake = max(self.shake, 12)
                self.hud.toast("Orb burst!", C.BLOOD, 60)
            self.particles.spawn_ring(
                self.boss.x, self.boss.y - 20, (220, 140, 160),
                count=30, speed=4.5, size=4, life=26
            )

    def _update_fight(self):
        keys = pygame.key.get_pressed()
        self.player.update(keys)
        self._resolve_player_decor_collision()
        self.boss.update(self.player)

        # slash trail particles at the blade tip while the swing is active
        if self.player.attack_phase == "active":
            tip = self.player.blade_tip()
            if tip is not None:
                tx, ty = tip
                self.particles.spawn_burst(
                    tx, ty, C.WHITE, count=2, speed=1.2, size=2, life=10
                )
                self.particles.spawn_burst(
                    tx, ty, C.GOLD, count=2, speed=1.6, size=3, life=14
                )

        # boss attack-state particle effects (visual richness)
        if self.boss.state == "teleport_out":
            is_mirror = hasattr(self.boss, "orb")
            mote_col = (210, 225, 250) if is_mirror else C.VIOLET
            # directional motes pulled inward
            from .particles import Particle
            for _ in range(5):
                a = random.uniform(0, math.tau)
                r = random.uniform(28, 80)
                px = self.boss.x + math.cos(a) * r
                py = self.boss.y + math.sin(a) * r - 18
                if is_mirror:
                    # Mirrorwright: silver shards fly OUTWARD (mirror shattering)
                    vx = math.cos(a) * 2.2
                    vy = math.sin(a) * 2.2 - 0.4     # slight upward drift
                    self.particles.parts.append(
                        Particle(self.boss.x + math.cos(a) * 10,
                                 self.boss.y - 18 + math.sin(a) * 10,
                                 vx, vy, 22, mote_col, size=3)
                    )
                else:
                    # Hollow King: violet void motes spiral INWARD
                    vx = -math.cos(a) * 1.8
                    vy = -math.sin(a) * 1.8 - 0.6    # upward pull (void column)
                    self.particles.parts.append(
                        Particle(px, py, vx, vy, 20, mote_col, size=3)
                    )
            # a thin vertical streak effect (every few frames)
            if self._anim_frame_mod(3):
                streak_x = self.boss.x + random.uniform(-10, 10)
                self.particles.parts.append(
                    Particle(streak_x, self.boss.y - 18, 0, -2.4, 16, mote_col, size=2)
                )
            # slight shake on the peak dissolution frame
            if self.boss.state_timer == 4:
                self.shake = max(self.shake, 6)
        elif self.boss.state == "teleport_in":
            is_mirror = hasattr(self.boss, "orb")
            mote_col = (220, 235, 255) if is_mirror else C.VIOLET
            # arrival slam + radial bursts that stagger across several frames
            if self.boss.state_timer in (21, 18, 14, 9):
                self.particles.spawn_ring(
                    self.boss.x, self.boss.y - 18, mote_col,
                    count=20, speed=3.6, size=3, life=22
                )
            # tall light column motes drifting down around the boss as he emerges
            if self._anim_frame_mod(2):
                from .particles import Particle
                a = random.uniform(0, math.tau)
                r = random.uniform(8, 36)
                px = self.boss.x + math.cos(a) * r
                py = self.boss.y + math.sin(a) * r - 70
                self.particles.parts.append(
                    Particle(px, py, 0, 1.4, 18, mote_col, size=2)
                )
            # big shake on the arrival flash frame
            if self.boss.state_timer == 20:
                self.shake = max(self.shake, 9)
        elif self.boss.state == "summon_shard":
            # dust kick at the boss's feet as he channels the shard
            if self._anim_frame_mod(4):
                self.particles.spawn_burst(
                    self.boss.x, self.boss.y + 10, (120, 90, 70),
                    count=1, speed=1.2, size=2, life=12
                )
        elif self.boss.state == "bolt_telegraph":
            # occasional ember sparks pulled toward the crown orb
            if self._anim_frame_mod(3):
                a = random.uniform(0, math.tau)
                r = random.uniform(18, 40)
                ox = self.boss.x + self.boss.facing * 20
                oy = self.boss.y - 10
                px = ox + math.cos(a) * r
                py = oy + math.sin(a) * r
                from .particles import Particle
                self.particles.parts.append(
                    Particle(px, py, -math.cos(a) * 1.5, -math.sin(a) * 1.5, 16, C.EMBER, size=2)
                )
        elif self.boss.state == "phantom_telegraph":
            # silver motes drifting toward the boss's hand as the phantom forms
            if self._anim_frame_mod(3):
                a = random.uniform(0, math.tau)
                r = random.uniform(22, 52)
                ox = self.boss.x + self.boss.facing * 20
                oy = self.boss.y - 14
                px = ox + math.cos(a) * r
                py = oy + math.sin(a) * r
                from .particles import Particle
                self.particles.parts.append(
                    Particle(px, py, -math.cos(a) * 1.3, -math.sin(a) * 1.3,
                             20, (180, 210, 240), size=2)
                )

        # level-specific boss side effects and player attack resolution
        if self.level_id == 2:
            self._update_level2_specifics()
        else:
            self._update_level1_specifics()

        # boss sweep hitbox vs player
        sweep = self.boss.sweep_hitbox()
        if sweep and not self.boss.attack_hit_player_this_state and sweep.colliderect(self.player.rect):
            if self.player.take_hit(1):
                self.boss.attack_hit_player_this_state = True
                self.shake = max(self.shake, 9)
                self.particles.spawn_burst(self.player.x, self.player.y, C.BLOOD, count=14, speed=3.2)

        # boss body contact no longer damages the player - only his active
        # attack hitboxes (sweep, bolt, ring slam) and shard pulses can hurt

        # bolts and ring slam - level 1 only
        if self.level_id == 1:
            for b in self.bolts:
                b.update()
                if b.alive and math.hypot(b.x - self.player.x, b.y - self.player.y) < 16 + b.radius and self.player.iframes == 0:
                    if self.player.take_hit(C.CROWN_BOLT_DAMAGE):
                        b.alive = False
                        self.particles.spawn_burst(b.x, b.y, C.EMBER, count=10, speed=2.6)
                        self.shake = max(self.shake, 5)
            self.bolts = [b for b in self.bolts if b.alive]

            ring = self.boss.ring_slam_tick()
            if ring and not self.boss.ring_slam_hit:
                d = math.hypot(self.player.x - ring["cx"], self.player.y - ring["cy"])
                if abs(d - ring["radius"]) < 18:
                    if self.player.take_hit(1):
                        self.boss.ring_slam_hit = True
                        self.shake = max(self.shake, 12)
                        self.hud.toast("Ring slam!", C.BLOOD, 45)

        # torch flame particles - staggered emission so they flicker
        self._torch_tick += 1
        if self._torch_tick % 4 == 0:
            for i, t in enumerate(self._torches):
                if (self._torch_tick + i * 5) % 9 == 0:
                    fx = t.x + random.uniform(-1.5, 1.5)
                    fy = t.y - t.sprite.get_height() + 6
                    self.particles.spawn_burst(
                        fx, fy, C.EMBER, count=1, speed=0.6, size=3, life=14
                    )
                    self.particles.spawn_burst(
                        fx, fy - 2, C.GOLD, count=1, speed=0.4, size=2, life=10
                    )

        # particles / hud
        self.particles.update()
        self.hud.update(self.boss)

        # shake decay
        if self.shake > 0:
            self.shake = max(0, self.shake - 1)

        # resolve end conditions
        if not self.boss.alive:
            self.state = "win"
            self.result_timer = 120
            self.particles.spawn_ring(self.boss.x, self.boss.y - 16, C.GOLD, count=40, speed=5.0, life=40)
            self.shake = 18
        elif self.player.hp <= 0:
            self.state = "lose"
            self.result_timer = 120
            self.particles.spawn_burst(self.player.x, self.player.y, C.BLOOD, count=40, speed=3.5, life=36)

    # ---------- rendering ----------

    def _draw_arena(self):
        screen = self.screen
        screen.fill(C.BLACK)
        # tiled floor inside arena
        tile = self.floor_tile
        tw, th = tile.get_size()
        for ty in range(C.ARENA_Y, C.ARENA_Y + C.ARENA_H, th):
            for tx in range(C.ARENA_X, C.ARENA_X + C.ARENA_W, tw):
                screen.blit(tile, (tx, ty))
        # arena border
        pygame.draw.rect(screen, C.STONE_LIGHT, (C.ARENA_X - 4, C.ARENA_Y - 4, C.ARENA_W + 8, C.ARENA_H + 8), 4)
        pygame.draw.rect(screen, C.STONE, (C.ARENA_X - 2, C.ARENA_Y - 2, C.ARENA_W + 4, C.ARENA_H + 4), 2)
        # corner braziers (decorative)
        for (cx, cy) in [
            (C.ARENA_X + 16, C.ARENA_Y + 16),
            (C.ARENA_X + C.ARENA_W - 16, C.ARENA_Y + 16),
            (C.ARENA_X + 16, C.ARENA_Y + C.ARENA_H - 16),
            (C.ARENA_X + C.ARENA_W - 16, C.ARENA_Y + C.ARENA_H - 16),
        ]:
            pygame.draw.circle(screen, C.STONE, (cx, cy), 10)
            flick = 3 + int(math.sin(pygame.time.get_ticks() * 0.02 + cx) * 2)
            pygame.draw.circle(screen, C.EMBER, (cx, cy - 3), flick)
            pygame.draw.circle(screen, C.GOLD, (cx, cy - 3), max(1, flick - 2))

    def _draw_fight(self):
        offset = (0, 0)
        if self.shake > 0:
            offset = (random.randint(-self.shake, self.shake), random.randint(-self.shake, self.shake))

        world = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
        world.fill(C.BLACK)
        # varied floor layout (clipped to arena bounds)
        tw, th = self.floor_tile.get_size()
        for ry, row in enumerate(self._floor_layout):
            for rx, tile in enumerate(row):
                x = C.ARENA_X + rx * tw
                y = C.ARENA_Y + ry * th
                if x >= C.ARENA_X + C.ARENA_W or y >= C.ARENA_Y + C.ARENA_H:
                    continue
                world.blit(tile, (x, y), pygame.Rect(
                    0, 0,
                    min(tw, C.ARENA_X + C.ARENA_W - x),
                    min(th, C.ARENA_Y + C.ARENA_H - y),
                ))
        pygame.draw.rect(world, C.STONE_LIGHT, (C.ARENA_X - 4, C.ARENA_Y - 4, C.ARENA_W + 8, C.ARENA_H + 8), 4)
        pygame.draw.rect(world, C.STONE, (C.ARENA_X - 2, C.ARENA_Y - 2, C.ARENA_W + 4, C.ARENA_H + 4), 2)

        # ground-layer decor (rubble etc.) draws on the floor *before* entities
        # so the player always walks on top of them
        for d in self._decor:
            if d.ground:
                d.draw(world)

        # shadows for living entities
        for ent in (*self.shards, self.boss, self.player):
            pygame.draw.ellipse(world, (0, 0, 0, 80), (int(ent.x) - 18, int(ent.y) + 16, 36, 10))
        # small shadow under each tall decor piece
        for d in self._decor:
            if d.ground:
                continue
            pygame.draw.ellipse(
                world, (0, 0, 0, 70),
                (int(d.x) - 14, int(d.y) - 3, 28, 6),
            )

        # tall decor + entities sorted by feet-y for fake depth
        drawables = [d for d in self._decor if not d.ground]
        drawables.extend([*self.shards, self.boss, self.player])
        drawables.sort(key=lambda e: e.y)
        for e in drawables:
            e.draw(world)

        # bolts above
        for b in self.bolts:
            b.draw(world)
        # phantoms (level 2) - ghostly overlay on top of entities
        for p in self.phantoms:
            p.draw(world)

        # particles
        self.particles.draw(world)

        self.screen.blit(world, offset)

        # HUD - fixed (no shake)
        self.hud.draw_player(self.screen, self.player)
        self.hud.draw_boss(self.screen, self.boss)
        self.hud.draw_controls_hint(self.screen)
        self.hud.draw_toasts(self.screen)
        # test-mode indicator in the top-right corner
        if self.test_mode:
            self.hud._blit_chip(
                self.screen, "TEST MODE", (140, 220, 160),
                topright=(C.SCREEN_W - C.HUD_MARGIN, C.HUD_MARGIN),
            )

        # phase transition banner - text differs per level; fades in/out on a
        # translucent panel so it's always legible over the arena
        if self.boss.enraged_anim > 0:
            t = self.boss.enraged_anim / 60.0
            alpha = int(255 * (1 - abs(0.5 - t) * 2))
            if self.level_id == 2:
                text = "THE MIRROR CRACKS"
                color = (230, 170, 200)
            else:
                text = "THE CROWN IGNITES"
                color = C.EMBER
            banner = self.font_big.render(text, True, color)
            panel_w = banner.get_width() + 40
            panel_h = banner.get_height() + 16
            panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel.fill((10, 8, 16, 180))
            pygame.draw.rect(panel, (*color, 200), panel.get_rect(), 2)
            panel.blit(banner, banner.get_rect(center=panel.get_rect().center))
            # uniform alpha fade that respects SRCALPHA per-pixel
            fade = pygame.Surface(panel.get_size(), pygame.SRCALPHA)
            fade.fill((255, 255, 255, alpha))
            panel.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(panel, panel.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 - 40)))

    def _draw_title(self):
        self.screen.fill(C.BLACK)
        # subtle starfield
        rng = random.Random(1)
        for _ in range(100):
            x = rng.randint(0, C.SCREEN_W)
            y = rng.randint(0, C.SCREEN_H // 2)
            c = rng.choice([(180, 180, 200), (140, 140, 170), (220, 210, 180)])
            self.screen.set_at((x, y), c)

        title = self.font_big.render("CROWN  OF  HOLLOW", True, C.GOLD)
        self.screen.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 110)))
        subtitle = self.font.render("choose your trial", True, C.BONE)
        self.screen.blit(subtitle, subtitle.get_rect(center=(C.SCREEN_W // 2, 158)))

        # level cards
        card_w = 520
        card_h = 86
        card_x = (C.SCREEN_W - card_w) // 2
        y0 = 200
        for i, lvl in enumerate(LEVELS):
            card_y = y0 + i * (card_h + 18)
            selected = (i == self.title_selection)
            panel = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            bg_col = (40, 30, 46, 220) if selected else (22, 18, 28, 180)
            panel.fill(bg_col)
            border_col = (236, 196, 104) if selected else (80, 70, 90)
            pygame.draw.rect(panel, border_col, panel.get_rect(), 2 if selected else 1)
            self.screen.blit(panel, (card_x, card_y))
            num = self.font.render(str(lvl["id"]), True,
                                   C.GOLD if selected else (150, 140, 130))
            self.screen.blit(num, (card_x + 18, card_y + 14))
            title_col = (240, 220, 160) if selected else C.BONE
            name_img = self.font.render(lvl["title"], True, title_col)
            self.screen.blit(name_img, (card_x + 54, card_y + 14))
            sub_img = self.font_small.render(lvl["subtitle"], True,
                                             (200, 180, 150) if selected else (140, 130, 120))
            self.screen.blit(sub_img, (card_x + 54, card_y + 40))
            blurb_img = self.font_small.render(lvl["blurb"], True,
                                              (220, 210, 190) if selected else (120, 110, 100))
            self.screen.blit(blurb_img, (card_x + 54, card_y + 60))
            if selected:
                # pulsing chevron on the left
                pulse = (math.sin(pygame.time.get_ticks() * 0.005) + 1) * 0.5
                cx = card_x - 10 - int(pulse * 4)
                cy = card_y + card_h // 2
                pygame.draw.polygon(
                    self.screen, C.GOLD,
                    [(cx, cy - 7), (cx + 10, cy), (cx, cy + 7)]
                )

        help_text = self.font_small.render(
            "UP / DOWN to choose   -   SPACE / ENTER to begin   -   ESC to quit",
            True, (170, 160, 150),
        )
        self.screen.blit(help_text, help_text.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H - 40)))

        # test-code input field and status banner
        self._draw_test_code_field()

    def _draw_test_code_field(self):
        """Small input-field for the tester password. Digits type in, backspace
        deletes, auto-validates at 6 chars."""
        # visible text - dots for entered digits so the code doesn't shoulder-read
        entered = "*" * len(self.test_code_buffer)
        remaining = "_" * (TEST_CODE_MAX_LEN - len(self.test_code_buffer))
        blink = (pygame.time.get_ticks() // 400) % 2 == 0
        cursor_char = "|" if blink and len(self.test_code_buffer) < TEST_CODE_MAX_LEN else " "
        value_text = f"{entered}{cursor_char}{remaining}"

        label_img = self.font_small.render("TEST CODE:", True, (170, 160, 150))
        value_img = self.font_small.render(value_text, True, (220, 230, 250))

        pad_x, pad_y = 10, 4
        gap = 8
        total_w = label_img.get_width() + gap + value_img.get_width()
        pw = total_w + pad_x * 2
        ph = max(label_img.get_height(), value_img.get_height()) + pad_y * 2
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((10, 8, 16, 170))
        # indicate test-mode-on state with a green border
        if self.test_mode:
            pygame.draw.rect(panel, (140, 220, 160, 220), panel.get_rect(), 2)
        panel_rect = panel.get_rect(midbottom=(C.SCREEN_W // 2, C.SCREEN_H - 70))
        self.screen.blit(panel, panel_rect)
        inner_y = panel_rect.y + (ph - label_img.get_height()) // 2
        lx = panel_rect.x + pad_x
        self.screen.blit(label_img, (lx, inner_y))
        self.screen.blit(value_img, (lx + label_img.get_width() + gap, inner_y))

        # flash banner on validation
        if self.test_code_flash > 0:
            self.test_code_flash -= 1
            # fade in first 20, hold, fade out last 30
            if self.test_code_flash > 110:
                alpha = int(255 * (140 - self.test_code_flash) / 30.0)
            elif self.test_code_flash < 30:
                alpha = int(255 * (self.test_code_flash / 30.0))
            else:
                alpha = 255
            alpha = max(0, min(255, alpha))
            banner_img = self.font.render(
                self.test_code_flash_text, True, self.test_code_flash_color
            )
            w = banner_img.get_width() + 28
            h = banner_img.get_height() + 10
            bp = pygame.Surface((w, h), pygame.SRCALPHA)
            bp.fill((10, 8, 16, 200))
            pygame.draw.rect(bp, (*self.test_code_flash_color, 220), bp.get_rect(), 2)
            bp.blit(banner_img, banner_img.get_rect(center=bp.get_rect().center))
            fade = pygame.Surface(bp.get_size(), pygame.SRCALPHA)
            fade.fill((255, 255, 255, alpha))
            bp.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(
                bp, bp.get_rect(midbottom=(C.SCREEN_W // 2, C.SCREEN_H - 110))
            )

    def _draw_end(self):
        self._draw_fight()
        overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        if self.state == "win":
            if self.level_id == 2:
                title_text, title_color = "THE MIRROR CLEARS", (220, 235, 250)
                sub_text = "the reflections rest.  R to fight again, ESC for menu."
            else:
                title_text, title_color = "THE CROWN SHATTERS", C.GOLD
                sub_text = "his soul is free.  R to fight again, ESC for menu."
        else:
            if self.level_id == 2:
                title_text, title_color = "THE ORB CONSUMES YOU", C.BLOOD
            else:
                title_text, title_color = "YOU FALL BEFORE THE KING", C.BLOOD
            sub_text = "R to try again, ESC for menu."
        self._blit_text_panel(
            title_text, title_color, self.font_big,
            center=(C.SCREEN_W // 2, C.SCREEN_H // 2 - 20), border=True,
        )
        self._blit_text_panel(
            sub_text, C.BONE, self.font,
            center=(C.SCREEN_W // 2, C.SCREEN_H // 2 + 30),
        )

    def _blit_text_panel(self, text, color, font, center, border=False, pad_x=18, pad_y=6):
        """Shared helper - renders text on a translucent panel so it remains
        legible over any arena contents (used for end-screen banners)."""
        img = font.render(text, True, color)
        pw = img.get_width() + pad_x * 2
        ph = img.get_height() + pad_y * 2
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((10, 8, 16, 190))
        if border:
            pygame.draw.rect(panel, (*color, 220), panel.get_rect(), 2)
        panel.blit(img, img.get_rect(center=panel.get_rect().center))
        self.screen.blit(panel, panel.get_rect(center=center))

    # ---------- main loop ----------

    def run(self):
        while True:
            for ev in pygame.event.get():
                self._handle_event(ev)
            if self.state == "fight":
                self._update_fight()
                self._draw_fight()
            elif self.state == "title":
                self._draw_title()
            elif self.state in ("win", "lose"):
                if self.result_timer > 0:
                    self.result_timer -= 1
                    self._update_fight_endish()
                self._draw_end()
            pygame.display.flip()
            self.clock.tick(C.FPS)

    def _update_fight_endish(self):
        # let particles finish playing out on end screens, no gameplay
        self.particles.update()
        if self.shake > 0:
            self.shake = max(0, self.shake - 1)


def run():
    Game().run()
