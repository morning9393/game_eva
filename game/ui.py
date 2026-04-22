"""HUD: player hearts, boss HP, Resonance meter, feedback toasts."""
import pygame
from . import constants as C
from . import sprites


class HUD:
    def __init__(self):
        self.font_small = pygame.font.SysFont("menlo", 14, bold=True)
        self.font = pygame.font.SysFont("menlo", 18, bold=True)
        self.font_big = pygame.font.SysFont("menlo", 32, bold=True)
        self.heart_full = sprites.make_heart(True)
        self.heart_empty = sprites.make_heart(False)
        self.boss_hp_display = float(C.BOSS_MAX_HP)
        self.res_display = 0.0
        self.orb_display = 0.0
        self.toasts = []  # list of (text, color, life)

    def toast(self, text, color=C.WHITE, life=70):
        self.toasts.append([text, color, life, life])

    def _blit_chip(self, surf, text, color, topleft=None, topright=None,
                   midtop=None, pad_x=6, pad_y=2, font=None):
        """Render `text` with a translucent dark backdrop chip.
        Provide exactly one of `topleft` / `topright` / `midtop` for anchoring.
        """
        f = font if font is not None else self.font_small
        img = f.render(text, True, color)
        w = img.get_width() + pad_x * 2
        h = img.get_height() + pad_y * 2
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((10, 8, 16, 170))
        if topleft is not None:
            panel_rect = panel.get_rect(topleft=topleft)
        elif topright is not None:
            panel_rect = panel.get_rect(topright=topright)
        else:
            panel_rect = panel.get_rect(midtop=midtop)
        surf.blit(panel, panel_rect)
        surf.blit(img, img.get_rect(center=panel_rect.center))

    def update(self, boss):
        # smooth lerp for bars
        target_hp = boss.hp
        # for twin sovereigns, treat the aggregate HP for the lerp
        if hasattr(boss, "solar") and hasattr(boss, "lunar"):
            target_hp = boss.solar.hp + boss.lunar.hp
        self.boss_hp_display += (target_hp - self.boss_hp_display) * 0.18
        if hasattr(boss, "resonance"):
            self.res_display += (boss.resonance - self.res_display) * 0.22
        if hasattr(boss, "orb"):
            self.orb_display += (boss.orb - self.orb_display) * 0.25
        for t in self.toasts:
            t[2] -= 1
        self.toasts = [t for t in self.toasts if t[2] > 0]

    def draw_player(self, surf, player):
        x = C.HUD_MARGIN
        y = C.HUD_MARGIN
        for i in range(C.PLAYER_MAX_HP):
            spr = self.heart_full if i < player.hp else self.heart_empty
            surf.blit(spr, (x + i * (spr.get_width() + 4), y))
        # dash cooldown bar
        bar_y = y + self.heart_full.get_height() + 6
        pygame.draw.rect(surf, (40, 36, 50), (x, bar_y, 100, 6))
        if player.dash_cd > 0:
            pct = 1 - player.dash_cd / C.PLAYER_DASH_COOLDOWN
            pygame.draw.rect(surf, C.AZURE, (x, bar_y, int(100 * pct), 6))
        else:
            pygame.draw.rect(surf, C.AZURE, (x, bar_y, 100, 6))
        # DASH label on a translucent chip so it reads cleanly on any floor
        self._blit_chip(surf, "DASH", C.BONE, topleft=(x + 104, bar_y - 4))

    def draw_boss(self, surf, boss):
        bar_w = 540
        bar_h = 14
        x = (C.SCREEN_W - bar_w) // 2
        y = 14

        # detect boss kind
        is_mirror = hasattr(boss, "orb")
        is_twin = hasattr(boss, "solar") and hasattr(boss, "lunar")
        is_weaver = hasattr(boss, "threads")
        is_echo = hasattr(boss, "echo_spawn_request")

        phase_tag = "- ENRAGED -" if boss.phase == 2 else ""
        if is_twin:
            name_str = "THE TWIN SOVEREIGNS" if boss.solar.alive and boss.lunar.alive \
                else (f"{'SOLAR' if boss.solar.alive else 'LUNAR'} KING - LAST")
        elif is_weaver:
            name_str = f"THE FATE-WEAVER  {phase_tag}"
        elif is_echo:
            name_str = f"THE ECHO LORD  {phase_tag}"
        elif is_mirror:
            name_str = f"THE MIRRORWRIGHT  {phase_tag}"
        else:
            name_str = f"THE HOLLOW KING  {phase_tag}"
        self._blit_chip(
            surf, name_str, C.BONE,
            midtop=(C.SCREEN_W // 2, y), pad_x=14, pad_y=3, font=self.font,
        )
        y += 26

        if is_twin:
            # two HP bars stacked, brighter for active king
            self._draw_twin_hp_bars(surf, boss, x, y, bar_w, bar_h)
            y2 = y + bar_h * 2 + 10
            self._draw_cycle_indicator(surf, boss, x, y2, bar_w)
            return

        # single HP bar for other bosses
        max_hp = boss.max_hp if hasattr(boss, "max_hp") else C.BOSS_MAX_HP
        pygame.draw.rect(surf, (20, 12, 18), (x - 2, y - 2, bar_w + 4, bar_h + 4))
        pygame.draw.rect(surf, (44, 24, 32), (x, y, bar_w, bar_h))
        hp_pct = max(0.0, self.boss_hp_display / max_hp)
        pygame.draw.rect(surf, C.BLOOD, (x, y, int(bar_w * hp_pct), bar_h))
        for i in range(1, 8):
            tx = x + int(bar_w * i / 8)
            pygame.draw.line(surf, (20, 12, 18), (tx, y), (tx, y + bar_h))

        y2 = y + bar_h + 6
        if is_mirror:
            self._draw_orb_bar(surf, boss, x, y2, bar_w, bar_h)
        elif is_weaver:
            self._draw_weaver_threads(surf, boss, x, y2, bar_w, bar_h)
        elif is_echo:
            self._draw_echo_info(surf, boss, x, y2, bar_w, bar_h)
        else:
            self._draw_resonance_bar(surf, x, y2, bar_w, bar_h)

    def _draw_twin_hp_bars(self, surf, boss, x, y, bar_w, bar_h):
        half_w = (bar_w - 12) // 2
        # solar bar (left)
        solar_pct = max(0.0, boss.solar.hp / boss.solar.max_hp)
        lunar_pct = max(0.0, boss.lunar.hp / boss.lunar.max_hp)
        # backdrops
        for offset, (pct, col, king) in enumerate([
            (solar_pct, C.GOLD, boss.solar),
            (lunar_pct, (140, 170, 230), boss.lunar),
        ]):
            bx = x + offset * (half_w + 12)
            pygame.draw.rect(surf, (20, 12, 18), (bx - 2, y - 2, half_w + 4, bar_h + 4))
            pygame.draw.rect(surf, (40, 30, 40), (bx, y, half_w, bar_h))
            fade = 255 if king.active else 120
            fill_col = (col[0], col[1], col[2])
            pygame.draw.rect(surf, fill_col, (bx, y, int(half_w * pct), bar_h))
            if not king.active:
                # dim ghost overlay
                ghost = pygame.Surface((half_w, bar_h), pygame.SRCALPHA)
                ghost.fill((0, 0, 0, 120))
                surf.blit(ghost, (bx, y))
            # label chip above each bar
            label = "SOLAR" if king.role == "solar" else "LUNAR"
            if king.active:
                label += " *"
            self._blit_chip(
                surf, label, col if king.active else (180, 180, 180),
                topleft=(bx, y - 16),
            )
        # combined HP bar background below (for aggregate view)
        y2 = y + bar_h + 4
        # second row: full HP bar split
        full_pct = max(0.0, (boss.solar.hp + boss.lunar.hp) / (boss.solar.max_hp + boss.lunar.max_hp))
        pygame.draw.rect(surf, (20, 12, 18), (x - 2, y2 - 2, bar_w + 4, bar_h + 4))
        pygame.draw.rect(surf, (44, 24, 32), (x, y2, bar_w, bar_h))
        pygame.draw.rect(surf, C.BLOOD, (x, y2, int(bar_w * full_pct), bar_h))

    def _draw_cycle_indicator(self, surf, boss, x, y, bar_w):
        # phase label and time-to-flip bar
        phase_text = "DAY" if boss.day_phase == "day" else "NIGHT"
        col = C.GOLD if boss.day_phase == "day" else (140, 170, 230)
        self._blit_chip(surf, phase_text, col, topleft=(x, y))
        # time to flip bar
        if boss.solar.alive and boss.lunar.alive:
            frac = boss.cycle_timer / C.TWIN_CYCLE_FRAMES
            fw = int(bar_w * frac)
            bar_y = y + 6
            pygame.draw.rect(surf, (20, 20, 28), (x + 76, bar_y, bar_w - 80, 6))
            pygame.draw.rect(surf, col, (x + 76, bar_y, fw, 6))
            self._blit_chip(
                surf, f"{int(boss.cycle_timer / 60)}s to flip",
                (210, 210, 220),
                topright=(x + bar_w, y),
            )

    def _draw_weaver_threads(self, surf, boss, x, y, bar_w, bar_h):
        pygame.draw.rect(surf, (20, 20, 28), (x - 2, y - 2, bar_w + 4, bar_h + 4))
        pygame.draw.rect(surf, (30, 22, 38), (x, y, bar_w, bar_h))
        live = boss.live_thread_count
        dr_pct = min(0.85, live * C.WEAVER_THREAD_DEFENSE)
        # fill shows current defense %
        fill_w = int(bar_w * dr_pct / 0.85)
        pygame.draw.rect(surf, (200, 140, 220), (x, y, fill_w, bar_h))
        lbl_y = y + bar_h + 2
        self._blit_chip(surf, "THREADS", (220, 190, 240), topleft=(x, lbl_y))
        self._blit_chip(
            surf, f"{live} live  |  {int(dr_pct * 100)}% dmg absorbed",
            (220, 190, 240),
            topright=(x + bar_w, lbl_y),
        )

    def _draw_echo_info(self, surf, boss, x, y, bar_w, bar_h):
        pygame.draw.rect(surf, (20, 20, 28), (x - 2, y - 2, bar_w + 4, bar_h + 4))
        pygame.draw.rect(surf, (40, 22, 30), (x, y, bar_w, bar_h))
        # cadence bar - when next echo spawns
        interval = C.ECHO_SPAWN_INTERVAL_P2 if boss.phase == 2 else C.ECHO_SPAWN_INTERVAL_P1
        frac = 1.0 - (boss.spawn_timer / interval)
        fill_w = int(bar_w * max(0.0, min(1.0, frac)))
        pygame.draw.rect(surf, (240, 120, 150), (x, y, fill_w, bar_h))
        lbl_y = y + bar_h + 2
        self._blit_chip(surf, "NEXT ECHO", (240, 180, 200), topleft=(x, lbl_y))
        self._blit_chip(
            surf, f"{boss.spawn_timer // 60 + 1}s",
            (240, 180, 200),
            topright=(x + bar_w, lbl_y),
        )

    def _draw_resonance_bar(self, surf, x, y2, bar_w, bar_h):
        pygame.draw.rect(surf, (20, 20, 28), (x - 2, y2 - 2, bar_w + 4, bar_h + 4))
        pygame.draw.rect(surf, (30, 30, 40), (x, y2, bar_w, bar_h))
        res_pct = self.res_display / C.BOSS_MAX_RESONANCE
        safe_end = int(bar_w * (C.RES_SAFE / C.BOSS_MAX_RESONANCE))
        warn_end = int(bar_w * (C.RES_WARN / C.BOSS_MAX_RESONANCE))
        danger_end = int(bar_w * (C.RES_DANGER / C.BOSS_MAX_RESONANCE))
        fill_w = int(bar_w * res_pct)
        seg_w_safe = min(fill_w, safe_end)
        seg_w_warn = min(max(0, fill_w - safe_end), warn_end - safe_end)
        seg_w_danger = min(max(0, fill_w - warn_end), danger_end - warn_end)
        seg_w_reflect = max(0, fill_w - danger_end)
        if seg_w_safe:
            pygame.draw.rect(surf, C.AZURE, (x, y2, seg_w_safe, bar_h))
        if seg_w_warn:
            pygame.draw.rect(surf, C.GOLD, (x + safe_end, y2, seg_w_warn, bar_h))
        if seg_w_danger:
            pygame.draw.rect(surf, C.EMBER, (x + warn_end, y2, seg_w_danger, bar_h))
        if seg_w_reflect:
            pygame.draw.rect(surf, C.BLOOD, (x + danger_end, y2, seg_w_reflect, bar_h))
        for px in (safe_end, warn_end, danger_end):
            pygame.draw.line(surf, C.BLACK, (x + px, y2), (x + px, y2 + bar_h))
        lbl_color = (210, 230, 250)
        lbl_y = y2 + bar_h + 2
        self._blit_chip(surf, "RESONANCE", lbl_color, topleft=(x, lbl_y))
        self._blit_chip(
            surf, f"{int(self.res_display)}/100",
            lbl_color, topright=(x + bar_w, lbl_y),
        )

    def _draw_orb_bar(self, surf, boss, x, y2, bar_w, bar_h):
        """Mirror Orb meter: queued damage with a threshold marker."""
        pygame.draw.rect(surf, (20, 20, 28), (x - 2, y2 - 2, bar_w + 4, bar_h + 4))
        pygame.draw.rect(surf, (26, 30, 42), (x, y2, bar_w, bar_h))
        pct = self.orb_display / C.MIRROR_ORB_MAX
        fill_w = int(bar_w * pct)
        threshold_pct = boss.shatter_threshold / C.MIRROR_ORB_MAX
        threshold_x = int(bar_w * threshold_pct)
        # safe fill (below threshold) in silver/blue, overfill in red
        safe_w = min(fill_w, threshold_x)
        over_w = max(0, fill_w - threshold_x)
        if safe_w:
            pygame.draw.rect(surf, (150, 190, 230), (x, y2, safe_w, bar_h))
            # animated shimmer
            shimmer_w = max(2, safe_w // 4)
            shimmer_x = (pygame.time.get_ticks() // 20) % max(1, safe_w - shimmer_w)
            pygame.draw.rect(
                surf, (220, 235, 250),
                (x + shimmer_x, y2, shimmer_w, 2),
            )
        if over_w:
            pygame.draw.rect(surf, C.BLOOD, (x + threshold_x, y2, over_w, bar_h))
        # threshold marker - a bright line and a small flag
        pygame.draw.line(
            surf, (255, 200, 120),
            (x + threshold_x, y2 - 3), (x + threshold_x, y2 + bar_h + 3), 2,
        )
        # tick marks
        for i in range(1, 8):
            tx = x + int(bar_w * i / 8)
            pygame.draw.line(surf, (14, 18, 28), (tx, y2), (tx, y2 + bar_h))
        lbl_color = (210, 230, 250)
        lbl_y = y2 + bar_h + 2
        self._blit_chip(surf, "MIRROR ORB", lbl_color, topleft=(x, lbl_y))
        self._blit_chip(
            surf,
            f"{int(self.orb_display)}/{int(boss.shatter_threshold)}",
            (255, 190, 170) if self.orb_display >= boss.shatter_threshold * 0.75 else lbl_color,
            topright=(x + bar_w, lbl_y),
        )

    def draw_toasts(self, surf):
        cy = C.SCREEN_H - 130
        pad_x = 14
        pad_y = 5
        for text, color, life, maxlife in self.toasts[-4:]:
            alpha = int(255 * min(1.0, life / 20.0))
            img = self.font.render(text, True, color)
            img.set_alpha(alpha)
            w = img.get_width() + pad_x * 2
            h = img.get_height() + pad_y * 2
            panel = pygame.Surface((w, h), pygame.SRCALPHA)
            panel.fill((15, 10, 20, int(200 * alpha / 255)))
            pygame.draw.rect(
                panel, (70, 60, 80, int(230 * alpha / 255)), panel.get_rect(), 1
            )
            panel_rect = panel.get_rect(center=(C.SCREEN_W // 2, cy))
            surf.blit(panel, panel_rect)
            surf.blit(img, img.get_rect(center=(C.SCREEN_W // 2, cy)))
            cy += h + 4

    def draw_controls_hint(self, surf):
        text = "WASD / Arrows: move     J or Space: attack     K or Shift: dash"
        img = self.font_small.render(text, True, (200, 190, 170))
        w = img.get_width() + 16
        h = img.get_height() + 4
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((10, 8, 16, 170))
        panel_rect = panel.get_rect(midbottom=(C.SCREEN_W // 2, C.SCREEN_H - 4))
        surf.blit(panel, panel_rect)
        surf.blit(img, img.get_rect(center=panel_rect.center))
