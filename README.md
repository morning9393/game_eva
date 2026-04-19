# Crown of Hollow

A 2D pixel-art boss-fight prototype built with Pygame. Western fantasy. Single arena, single boss, one creative mechanic at its center.

> The Hollow King wore the Crown of Seven Gems when the realms united.
> Then the Shard Plague came. The gems corrupted. The king hollowed.
> You remember his true name. Shatter the crown. Free him.

## The hook: Resonance

Most boss fights reward aggression. This one punishes it.

- The king has two bars: **HP** and **Resonance** (0–100).
- Every hit you land raises Resonance. As it climbs, your damage scales down.
- At full Resonance your blows **reflect back at you** and **heal the king**.
- **Crown Shards** rise from the arena floor. Slash shards to drain Resonance.
- Shards also pulse damaging shockwaves — read the telegraph, dash through.

The rhythm: bait an attack → dodge → break a shard or two → burst the king while Resonance is low → back off. Phase 2 (below 50% HP) adds wider bolt spreads and an expanding ring slam.

## Install

Requires conda (Anaconda / Miniconda). A dedicated env is used so pygame stays isolated.

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

| Action | Keys |
|--------|------|
| Move | `W A S D` or arrows |
| Attack (sword) | `J` or `Space` |
| Dash (i-frames, ~1s cd) | `K` or `Shift` |
| Restart after win/loss | `R` |
| Quit | `Esc` |

## Project layout

```
game_eva/
├── main.py                # entry point
├── requirements.txt
└── game/
    ├── app.py             # main loop, state machine, collisions
    ├── boss.py            # Hollow King AI, phases, Resonance rules
    ├── player.py          # movement, sword FSM, dash
    ├── shard.py           # Crown Shard entities and pulse AoE
    ├── projectile.py      # crown bolts
    ├── particles.py       # hit sparks, rings, dust
    ├── sprites.py         # procedural pixel-art sprites (scaled x3)
    ├── ui.py              # HUD: hearts, HP bar, Resonance meter, toasts
    ├── utils.py           # math / arena helpers
    └── constants.py       # tuning knobs (one place to rebalance)
```

Pixel-art sprites come from Kenney's **Tiny Dungeon** pack (CC0 public domain) at `assets/kenney_tiny-dungeon/`. Each sprite factory in `game/sprites.py` tries the loaded tile first and falls back to a procedurally drawn version if the pack is missing, so the game runs either way.

## Credits

- Sprite pack: **Tiny Dungeon** by [Kenney](https://kenney.nl/assets/tiny-dungeon) — Creative Commons Zero (CC0).

## Tuning

Every gameplay number lives in `game/constants.py`:

- Player: `PLAYER_SPEED`, `PLAYER_MAX_HP`, dash frames, sword timing.
- Boss: `BOSS_MAX_HP`, `BOSS_RESONANCE_PER_HIT`, `BOSS_RESONANCE_DECAY`.
- Resonance bands: `RES_SAFE` / `RES_WARN` / `RES_DANGER` (damage scaling cutoffs).
- Shards: HP, pulse interval, pulse radius, spawn cadence per phase.

Change numbers, re-run — no other code touches needed for rebalance.

## Roadmap

This is a prototype. Planned expansion:

- Tile-based overworld with room transitions.
- Dialogue and quest log driven by data files.
- Sprite-sheet loader and drop-in pixel-art packs.
- More bosses, each with a distinct creative mechanic in the Resonance spirit.
- Inventory, persistent save, audio.

## License

Personal project. No license declared yet.
