# Crown of Hollow

A 2D pixel-art boss-fight prototype built with Pygame. Western fantasy. Two bosses, each built around a distinct creative mechanic.

> The Hollow King wore the Crown of Seven Gems when the realms united.
> Then the Shard Plague came. The gems corrupted. The king hollowed.
> You remember his true name. Shatter the crown. Free him.

## The two trials

Each boss has a dual-stat economy, but the skill each rewards is different. Pick from the title screen.

### Level 1 — The Hollow King ("Resonance")

- The king has **HP** and **Resonance** (0–100). Every sword hit raises Resonance.
- As Resonance climbs, your damage scales down. At the red band your blows **reflect back at you** and **heal the king**.
- **Crown Shards** rise from the arena floor. Slash shards to drain Resonance. Shards also pulse damaging shockwaves — read the telegraph, dash through.
- **Phase 2 (below 50% HP)** — wider crown-bolt spreads, an expanding ring slam, and hit-flashes on the boss.

Core rhythm: bait → dodge → break a shard or two → burst the king while Resonance is low → back off.

### Level 2 — The Mirrorwright ("Mirror Orb")

- Sword hits don't reduce HP directly. Damage queues inside a **mirror orb** on his chest.
- Two outcomes for the queue:
  - **Dash-shatter** — dash *into* the orb while it has queued damage and the full queue, multiplied ×1.5, detonates *on the boss*. Huge combo, but you're committed.
  - **Auto-shatter** — let the orb fill to its threshold and it bursts *on you*, reflecting the queue back. Greed punishes.
- **Phantom Reflections** — the boss fires silver ghosts that retrace the player's last ~2 seconds of movement. Dodge by breaking your own pattern.
- **Phase 2 (below 40% HP)** — shatter threshold drops 80 → 60, idle windows shorten, teleports enter the attack pool.

Core rhythm: build queue with clean hits → time your dash through the orb at the right moment → back off, reset, feint out phantoms.

## Install

Requires conda (Anaconda / Miniconda). A dedicated env keeps pygame isolated.

```bash
conda create -n game_eva python=3.11 -y
conda activate game_eva
pip install pygame
```

Tested with **Python 3.11.13** and **pygame 2.6.1** (SDL 2.28.4) on macOS.

## Run

```bash
conda activate game_eva
cd game_eva
python main.py
```

## Controls

**Title screen**

| Action | Keys |
|--------|------|
| Navigate levels | `W` / `S` or `↑` / `↓` |
| Start fight | `Space` / `Enter` |
| Quit | `Esc` |
| Enter test code | type digits (see Test Mode below) |

**In fight**

| Action | Keys |
|--------|------|
| Move | `W A S D` or arrows |
| Attack (sword) | `J` or `Space` |
| Dash (i-frames, ~1s cd) | `K` or `Shift` |
| Back to menu | `Esc` |

**On win / loss screen**

| Action | Keys |
|--------|------|
| Restart | `R` / `Space` / `Enter` |
| Back to menu | `Esc` |

## Test mode

For playtesting the game without dying. On the title screen, type the 6-digit code:

```
114514
```

A green `TEST MODE ENABLED` banner confirms activation. The test-code field border stays green; during a run, a small `TEST MODE` chip appears in the top-right so you don't forget. Any wrong code flashes `INVALID CODE` and clears.

In test mode the player takes zero damage from all sources (boss attacks, shard pulses, phantom contact, orb auto-shatter). Normal gameplay otherwise.

## Project layout

```
game_eva/
├── main.py                # entry point
├── requirements.txt
├── assets/                # Kenney's Tiny Dungeon CC0 pack
└── game/
    ├── app.py             # main loop, title + level selector, per-level dispatch
    ├── boss.py            # Hollow King (Resonance, shards, bolts, ring slam)
    ├── mirrorwright.py    # Mirrorwright (Mirror Orb, phantom reflections)
    ├── player.py          # movement, sword swing arc, dash, path history
    ├── shard.py           # Crown Shard entities + pulse AoE
    ├── projectile.py      # crown bolts
    ├── particles.py       # hit sparks, rings, dust
    ├── sprites.py         # sprite factories (Kenney-backed with fallback)
    ├── assets.py          # tilemap loader + named tile constants
    ├── ui.py              # HUD, chip-styled labels, toast panels
    ├── utils.py           # math / arena helpers
    └── constants.py       # all tuning knobs
```

Pixel-art sprites come from Kenney's **Tiny Dungeon** pack (CC0 public domain) at `assets/kenney_tiny-dungeon/`. Each sprite factory in `game/sprites.py` tries the loaded tile first and falls back to a procedurally drawn version if the pack is missing, so the game runs either way.

## Arena & visuals

- **Decor** — each arena has themed static props: Hollow King's throne + four pillars vs. Mirrorwright's cracked standing mirror + two pillars. Both share corner braziers with flickering flame particles and ground-level debris (rubble vs. mirror shards).
- **Collision** — the player is pushed out of brazier, pillar, and throne bases with minimum-translation sliding. Ground debris is walk-through and draws below characters.
- **Boss attack visuals** — no plain expanding ellipses: sweep shows a crescent arc telegraph + glowing blade arc with afterimage; bolt charge orbits particles around the crown; ring-slam runs a 40-vertex jagged shockwave with radial sparks; teleport now plays a vertical rift/mirror-plane with sprite squash, bright flash, and themed particle bursts (violet for the King, silver for the Mirrorwright).
- **HUD** — every label (DASH, boss name, Resonance/Orb value, toasts, phase banner, win/lose) sits on translucent dark chips so text never blends with the arena.

## Credits

- Sprite pack: **Tiny Dungeon** by [Kenney](https://kenney.nl/assets/tiny-dungeon) — Creative Commons Zero (CC0).

## Tuning

Every gameplay number lives in `game/constants.py`:

- **Player** — `PLAYER_SPEED`, `PLAYER_MAX_HP`, sword/dash timings, attack reach.
- **Hollow King** — `BOSS_MAX_HP`, `BOSS_RESONANCE_PER_HIT`, `BOSS_RESONANCE_DECAY`, `RES_SAFE` / `RES_WARN` / `RES_DANGER` bands.
- **Mirrorwright** — `MIRROR_BOSS_MAX_HP`, `MIRROR_ORB_MAX`, `MIRROR_ORB_SHATTER_P1` / `_P2`, `MIRROR_DASH_DAMAGE_MULT`, `MIRROR_DASH_SHATTER_RADIUS`, `PHANTOM_SPEED`, `PLAYER_PATH_HISTORY`.
- **Shards** — HP, pulse interval, pulse radius, spawn cadence per phase.

Change numbers, re-run — no other code touches needed for rebalance.

## Roadmap

- More bosses, each with a distinct dual-stat mechanic.
- Tile-based overworld connecting the chambers.
- Dialogue and quest log driven by data files.
- Inventory, persistent save, audio.

## License

Personal project. No license declared yet.
