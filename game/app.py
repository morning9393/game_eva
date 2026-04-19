"""Main application / game loop for Crown of Hollow."""
import math
import random
import sys

import pygame

from . import constants as C
from . import sprites
from .boss import Boss
from .particles import ParticleSystem
from .player import Player
from .projectile import CrownBolt
from .shard import Shard
from .ui import HUD
from .utils import circle_rect_collide, clamp, clamp_to_arena, inside_arena, random_point_in_arena


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(C.TITLE)
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("menlo", 22, bold=True)
        self.font_big = pygame.font.SysFont("menlo", 44, bold=True)
        self.font_small = pygame.font.SysFont("menlo", 14)
        self.floor_tile = sprites.make_floor_tile()
        self.state = "title"
        self.shake = 0
        self._init_fight()

    # ---------- setup ----------

    def _init_fight(self):
        cx = C.ARENA_X + C.ARENA_W // 2
        cy = C.ARENA_Y + C.ARENA_H // 2
        self.player = Player(cx - 200, cy + 80)
        self.boss = Boss(cx + 160, cy - 40)
        self.shards = []
        self.bolts = []
        self.particles = ParticleSystem()
        self.hud = HUD()
        self.shard_spawn_timer = 180
        self.hits_landed = 0
        self.result_timer = 0
        self._showed_danger_hint = False

    # ---------- input helpers ----------

    def _handle_event(self, ev):
        if ev.type == pygame.QUIT:
            pygame.quit()
            sys.exit(0)
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit(0)
            if self.state == "title" and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_j):
                self.state = "fight"
                self._init_fight()
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

    def _update_fight(self):
        keys = pygame.key.get_pressed()
        self.player.update(keys)
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

        # boss side-effects
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
            self.particles.spawn_burst(self.boss.x + self.boss.facing * 28, self.boss.y - 20, C.EMBER, count=14, speed=3.5)

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
                # damage player if in radius
                if math.hypot(self.player.x - s.x, self.player.y - s.y) <= C.SHARD_PULSE_RADIUS:
                    if self.player.take_hit(1):
                        self.hud.toast("Shard pulse!", C.EMBER, 45)
        self.shards = [s for s in self.shards if s.alive]

        # player sword collisions
        arect = self.player.attack_rect()
        if arect is not None:
            # vs boss
            if id(self.boss) not in self.player.attack_hit_set and arect.colliderect(self.boss.rect):
                result = self.boss.receive_player_hit(C.PLAYER_ATTACK_DAMAGE)
                self.player.attack_hit_set.add(id(self.boss))
                self.hits_landed += 1
                if result["band"] == "danger":
                    self.hud.toast("REJECTED - crown reflects!", C.BLOOD, 70)
                    self.particles.spawn_burst(self.boss.x, self.boss.y - 20, C.BLOOD, count=18, speed=4.0)
                    # reflect: damage player
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
            # vs shards
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

        # boss sweep hitbox vs player
        sweep = self.boss.sweep_hitbox()
        if sweep and not self.boss.attack_hit_player_this_state and sweep.colliderect(self.player.rect):
            if self.player.take_hit(1):
                self.boss.attack_hit_player_this_state = True
                self.shake = max(self.shake, 9)
                self.particles.spawn_burst(self.player.x, self.player.y, C.BLOOD, count=14, speed=3.2)

        # boss body contact no longer damages the player - only his active
        # attack hitboxes (sweep, bolt, ring slam) and shard pulses can hurt

        # bolts
        for b in self.bolts:
            b.update()
            if b.alive and math.hypot(b.x - self.player.x, b.y - self.player.y) < 16 + b.radius and self.player.iframes == 0:
                if self.player.take_hit(C.CROWN_BOLT_DAMAGE):
                    b.alive = False
                    self.particles.spawn_burst(b.x, b.y, C.EMBER, count=10, speed=2.6)
                    self.shake = max(self.shake, 5)
        self.bolts = [b for b in self.bolts if b.alive]

        # ring slam advance
        ring = self.boss.ring_slam_tick()
        if ring and not self.boss.ring_slam_hit:
            d = math.hypot(self.player.x - ring["cx"], self.player.y - ring["cy"])
            if abs(d - ring["radius"]) < 18:
                if self.player.take_hit(1):
                    self.boss.ring_slam_hit = True
                    self.shake = max(self.shake, 12)
                    self.hud.toast("Ring slam!", C.BLOOD, 45)

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
        # floor on world surf so shake covers everything
        tile = self.floor_tile
        tw, th = tile.get_size()
        for ty in range(C.ARENA_Y, C.ARENA_Y + C.ARENA_H, th):
            for tx in range(C.ARENA_X, C.ARENA_X + C.ARENA_W, tw):
                world.blit(tile, (tx, ty))
        pygame.draw.rect(world, C.STONE_LIGHT, (C.ARENA_X - 4, C.ARENA_Y - 4, C.ARENA_W + 8, C.ARENA_H + 8), 4)
        pygame.draw.rect(world, C.STONE, (C.ARENA_X - 2, C.ARENA_Y - 2, C.ARENA_W + 4, C.ARENA_H + 4), 2)

        # shadows
        for ent in (*self.shards, self.boss, self.player):
            pygame.draw.ellipse(world, (0, 0, 0, 80), (int(ent.x) - 18, int(ent.y) + 16, 36, 10))

        # entities sorted by y for fake depth
        drawables = [*self.shards, self.boss, self.player]
        drawables.sort(key=lambda e: e.y)
        for e in drawables:
            e.draw(world)

        # bolts above
        for b in self.bolts:
            b.draw(world)

        # particles
        self.particles.draw(world)

        self.screen.blit(world, offset)

        # HUD - fixed (no shake)
        self.hud.draw_player(self.screen, self.player)
        self.hud.draw_boss(self.screen, self.boss)
        self.hud.draw_controls_hint(self.screen)
        self.hud.draw_toasts(self.screen)

        # phase transition banner
        if self.boss.enraged_anim > 0:
            t = self.boss.enraged_anim / 60.0
            alpha = int(255 * (1 - abs(0.5 - t) * 2))
            banner = self.font_big.render("THE CROWN IGNITES", True, C.EMBER)
            banner.set_alpha(alpha)
            self.screen.blit(banner, banner.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 - 40)))

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
        self.screen.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 150)))
        subtitle = self.font.render("a crownbreaker's vigil", True, C.BONE)
        self.screen.blit(subtitle, subtitle.get_rect(center=(C.SCREEN_W // 2, 200)))

        lore = [
            "The Hollow King wore the Crown of Seven Gems when the realms united.",
            "Then the Shard Plague came. The gems corrupted. The king hollowed.",
            "You remember his true name.  Shatter the crown.  Free him.",
        ]
        for i, line in enumerate(lore):
            img = self.font_small.render(line, True, (180, 170, 150))
            self.screen.blit(img, img.get_rect(center=(C.SCREEN_W // 2, 260 + i * 20)))

        rules = [
            "- Hits on the king raise his RESONANCE.",
            "- When Resonance burns red, your blows reflect and heal him.",
            "- Break Crown Shards that rise from the floor to drain Resonance.",
            "- Shards pulse - dodge with your dash (K / Shift).",
        ]
        for i, line in enumerate(rules):
            img = self.font_small.render(line, True, C.BONE)
            self.screen.blit(img, (C.SCREEN_W // 2 - 240, 340 + i * 20))

        prompt = self.font.render("press SPACE to begin", True, C.EMBER)
        t = (pygame.time.get_ticks() // 500) % 2
        if t == 0:
            self.screen.blit(prompt, prompt.get_rect(center=(C.SCREEN_W // 2, 500)))

    def _draw_end(self):
        self._draw_fight()
        overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        if self.state == "win":
            title = self.font_big.render("THE CROWN SHATTERS", True, C.GOLD)
            sub = self.font.render("his soul is free.  press R to fight again.", True, C.BONE)
        else:
            title = self.font_big.render("YOU FALL BEFORE THE KING", True, C.BLOOD)
            sub = self.font.render("press R to try again", True, C.BONE)
        self.screen.blit(title, title.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 - 20)))
        self.screen.blit(sub, sub.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H // 2 + 30)))

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
