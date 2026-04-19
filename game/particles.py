"""Lightweight particle system for hit sparks, dust, and pulses."""
import math
import random
import pygame


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "grav", "fade")

    def __init__(self, x, y, vx, vy, life, color, size=2, grav=0.0, fade=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.grav = grav
        self.fade = fade

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.grav
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= 1

    def alive(self):
        return self.life > 0

    def draw(self, surf):
        t = max(0.0, self.life / self.max_life)
        s = max(1, int(self.size * (t if self.fade else 1.0)))
        c = self.color
        if self.fade:
            c = (
                int(c[0] * (0.35 + 0.65 * t)),
                int(c[1] * (0.35 + 0.65 * t)),
                int(c[2] * (0.35 + 0.65 * t)),
            )
        pygame.draw.rect(surf, c, (int(self.x) - s // 2, int(self.y) - s // 2, s, s))


class ParticleSystem:
    def __init__(self):
        self.parts = []

    def spawn_burst(self, x, y, color, count=12, speed=3.5, size=3, life=26, spread=math.tau):
        for _ in range(count):
            a = random.uniform(0, spread)
            s = random.uniform(0.3, 1.0) * speed
            self.parts.append(
                Particle(x, y, math.cos(a) * s, math.sin(a) * s, life + random.randint(-5, 5), color, size)
            )

    def spawn_ring(self, x, y, color, count=22, speed=3.0, size=3, life=22):
        for i in range(count):
            a = (i / count) * math.tau
            self.parts.append(
                Particle(x, y, math.cos(a) * speed, math.sin(a) * speed, life, color, size)
            )

    def spawn_dust(self, x, y, color, count=6):
        for _ in range(count):
            self.parts.append(
                Particle(
                    x + random.uniform(-4, 4),
                    y + random.uniform(-2, 2),
                    random.uniform(-0.8, 0.8),
                    random.uniform(-1.4, -0.2),
                    random.randint(18, 30),
                    color,
                    size=2,
                    grav=0.06,
                )
            )

    def update(self):
        for p in self.parts:
            p.update()
        self.parts = [p for p in self.parts if p.alive()]

    def draw(self, surf):
        for p in self.parts:
            p.draw(surf)
