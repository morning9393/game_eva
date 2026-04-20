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
        self.boss_hp_display += (boss.hp - self.boss_hp_display) * 0.18
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

        is_mirror = hasattr(boss, "orb")
        # boss name + phase - wrapped in a translucent chip for legibility
        phase_tag = "- ENRAGED -" if boss.phase == 2 else ""
        if is_mirror:
            name_str = f"THE MIRRORWRIGHT  {phase_tag}"
        else:
            name_str = f"THE HOLLOW KING  {phase_tag}"
        self._blit_chip(
            surf, name_str, C.BONE,
            midtop=(C.SCREEN_W // 2, y), pad_x=14, pad_y=3, font=self.font,
        )
        y += 26

        # HP bar
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
        else:
            self._draw_resonance_bar(surf, x, y2, bar_w, bar_h)

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
