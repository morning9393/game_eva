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
        self.toasts = []  # list of (text, color, life)

    def toast(self, text, color=C.WHITE, life=70):
        self.toasts.append([text, color, life, life])

    def _blit_chip(self, surf, text, color, topleft=None, topright=None, pad_x=6, pad_y=2):
        """Render `text` with a translucent dark backdrop chip.
        Provide exactly one of `topleft` or `topright` for anchoring.
        """
        img = self.font_small.render(text, True, color)
        w = img.get_width() + pad_x * 2
        h = img.get_height() + pad_y * 2
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((10, 8, 16, 170))
        if topleft is not None:
            panel_rect = panel.get_rect(topleft=topleft)
        else:
            panel_rect = panel.get_rect(topright=topright)
        surf.blit(panel, panel_rect)
        surf.blit(img, img.get_rect(center=panel_rect.center))

    def update(self, boss):
        # smooth lerp for bars
        self.boss_hp_display += (boss.hp - self.boss_hp_display) * 0.18
        self.res_display += (boss.resonance - self.res_display) * 0.22
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
        lbl = self.font_small.render("DASH", True, C.BONE)
        surf.blit(lbl, (x + 104, bar_y - 4))

    def draw_boss(self, surf, boss):
        bar_w = 540
        bar_h = 14
        x = (C.SCREEN_W - bar_w) // 2
        y = 14

        # boss name + phase
        phase_tag = "- ENRAGED -" if boss.phase == 2 else ""
        name = self.font.render(f"THE HOLLOW KING  {phase_tag}", True, C.BONE)
        surf.blit(name, name.get_rect(midtop=(C.SCREEN_W // 2, y)))
        y += 24

        # HP bar
        pygame.draw.rect(surf, (20, 12, 18), (x - 2, y - 2, bar_w + 4, bar_h + 4))
        pygame.draw.rect(surf, (44, 24, 32), (x, y, bar_w, bar_h))
        hp_pct = max(0.0, self.boss_hp_display / C.BOSS_MAX_HP)
        pygame.draw.rect(surf, C.BLOOD, (x, y, int(bar_w * hp_pct), bar_h))
        # tick marks
        for i in range(1, 8):
            tx = x + int(bar_w * i / 8)
            pygame.draw.line(surf, (20, 12, 18), (tx, y), (tx, y + bar_h))

        # Resonance meter just below, segmented with gradient bands
        y2 = y + bar_h + 6
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

        # band dividers
        for px in (safe_end, warn_end, danger_end):
            pygame.draw.line(surf, C.BLACK, (x + px, y2), (x + px, y2 + bar_h))

        lbl_color = (210, 230, 250)
        lbl_y = y2 + bar_h + 2
        # translucent dark backdrop behind each piece of text, like the toasts
        self._blit_chip(surf, "RESONANCE", lbl_color, topleft=(x, lbl_y))
        self._blit_chip(
            surf,
            f"{int(self.res_display)}/100",
            lbl_color,
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
        lines = [
            "WASD / Arrows: move     J or Space: attack     K or Shift: dash",
        ]
        for i, line in enumerate(lines):
            img = self.font_small.render(line, True, (160, 150, 130))
            surf.blit(img, img.get_rect(midbottom=(C.SCREEN_W // 2, C.SCREEN_H - 8 + i * 14)))
