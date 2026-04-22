# Crown of Hollow

A 2D pixel-art boss-fight game built with Pygame. Western fantasy. Five bosses, each built around its own creative mechanic. Pick your trial from the title screen.

> The Hollow King wore the Crown of Seven Gems when the realms united.
> Then the Shard Plague came. The gems corrupted. The king hollowed.
> You remember his true name. Shatter the crown. Free him.

---

## The five trials

The trials are presented in the following order from the title screen. Each
fight stresses a different skill: pattern discipline, timing commitment,
spatial awareness, tempo management, and rhythm.

### Level 1 — The Echo Lord *(theatre of past selves)*

The corrupted bard who plays back your own moves against you.

- **Echo Spawn.** Every ~2s he captures a **snapshot** from your movement history — a red-tinted silhouette at a past `(x, y, facing)`. Up to 5 on field at once.
- **Echo Slash.** Each snapshot pulses a red warning ring for ~1s, then fires a straight 160-px sword-slash line along the facing the player had at that moment. Damage on contact.
- **Cascade Echo.** Spawns 4 snapshots at evenly-spaced points along your recent path, with warnings staggered by ~18 frames so they detonate in sequence, chasing you through your own route.
- **Memory Surge.** After a ~34-frame red-vignette telegraph, every echo currently in the warning state *instantly* transitions to slash — a mass-fire punishment for ignoring warnings.
- **Phase 2 (below 45% HP):** spawn interval shortens; echoes arrive in bursts of 1–2.

**Core skill:** break your own movement patterns. Circling the same routes means walking straight into your past-self's slashes.

### Level 2 — The Twin Sovereigns *(hall of diurnal flux)*

Two minor kings sharing one throne, alternating power with day and night.

- **Diurnal Flux (passive).** Every 12 seconds, day and night swap. Only the *active* king can be damaged and only he attacks; the inactive king becomes spectral (dim aura, 50% alpha) and drifts slowly toward the player.
- **Sunlance (Solar, DAY).** A 40-frame line telegraph → solid piercing beam across the arena for ~60 frames. Pierces.
- **Solar Flare (Solar, DAY).** Expanding fire ring from his position; the edge deals damage, so dodge inward or outward.
- **Lunar Orbit (Lunar, NIGHT).** A silver crescent orbits the player at a shrinking radius, tethered by a faint thread. Contact damage.
- **Star Fall (Lunar, NIGHT).** Three dark star-marks drop at the player's *past* positions; each detonates as a small AoE after a ~1s warning.
- **Last Stand Lock.** When one king dies, the survivor locks to permanent-active (no more flipping).

**Core skill:** spatial awareness of *both* enemies. The king you're chasing will soon become intangible while the ghost at your back ignites.

### Level 3 — The Fate-Weaver *(loom of severed threads)*

The seamstress of destiny, spinning her web from your own aggression.

- **Thread Weaving (passive on-hit).** Every sword hit weaves a new **fate-thread** between her and the nearest stone anchor (one of four pillars at arena midpoints). Up to 4 live threads at once.
- **Thread Defense.** Each live thread reduces the damage she takes by 18% (capped at 85%). Each thread has 20 HP — slash them individually to strip defense.
- **Pull Along Thread.** A ~40-frame red-line telegraph → she dashes at speed 12 along a live thread, damaging anyone the line passes through.
- **Fated Strike.** Marks the player's current position with a violet foresight glyph; 115 frames later a crashing AoE impact lands there.
- **Weft Pulse.** Snapshots all thread endpoints at cast time, flashes them for ~40f, then detonates every captured line as a damaging pulse — forces you off the web.
- **Phase 2 (below 50% HP):** 50% of new threads anchor to *you* instead of stone, creating moving barriers that constrain your dodging.

**Core skill:** manage your own aggression. Every hit *helps her* unless you invest effort into snapping threads. Optimal pacing: break → strike → break.

### Level 4 — The Mirrorwright *(chamber of quicksilver)*

The royal mirror-maker, corrupted into a silver prism of reflection.

- **Mirror Orb (passive).** Sword hits don't reduce HP directly — damage queues inside an orb on his chest. The orb brightens from blue to red as it fills; hairline cracks appear near threshold.
  - **Dash-shatter.** Dash into the orb while it has queued damage and the full queue, multiplied ×1.5, detonates *on the boss*. Huge combo, but you're committed to the dash.
  - **Auto-shatter.** Let the orb fill to its threshold (**80 P1 / 60 P2**) and it bursts *on you*, reflecting capped damage back.
- **Mirror Sweep.** Crescent-arc telegraph → lunges with his silver scimitar.
- **Phantom Reflection.** Three-ring charge → spawns a silver ghost that retraces your last ~140 frames of movement. Stationary players get caught easily.
- **Silver Rain.** Marks 4 ground zones with pulsing silver rings; after a ~50-frame warning, each zone rains shards for ~32 frames.
- **Shard Volley.** Charges 5 shard-points around his weaving hand, then fires a spread fan of silver mirror-shards at the player.
- **Reflection Shift (P2 teleport).** Silver-mirror rift with sprite squash + flash.
- **Phase 2 (below 40% HP):** shatter threshold drops 80 → 60, idle windows shorten, teleports join the attack pool.

**Core skill:** timing commitment. Build the queue, then pick your moment — greed at 79/80 is fine, greed at 80 is fatal.

### Level 5 — The Hollow King *(a crownbreaker's vigil)*

The once-great monarch whose crown absorbed the Shard Plague.

- **Resonance (passive).** Every hit raises the king's **Resonance** from 0 → 100. As Resonance climbs, your damage scales down. In the red band, your blows are fully **reflected back at you** and they *heal him*.
- **Crown Shards.** Periodically shards rise from the arena floor. Slash shards to drain Resonance. Shards also pulse damaging shockwaves — read their charging ring and dash through.
- **Sword Sweep.** Crescent arc telegraph → lunging horizontal slash.
- **Crown Bolt Spray.** Orbiting-particle charge at the crown → fans 3 (P1) / 5 (P2) crown-bolts at the player.
- **Summon Crown Shard.** Stamps the ground; 1 (P1) / 2 (P2) shards erupt near his feet.
- **Ring Slam (P2 only).** Runic-glyph telegraph at his feet → jagged 40-vertex shockwave expanding outward.
- **Void Step (P2 only).** Violet rift teleport far from the player.
- **Phase 2 (below 50% HP):** gains Ring Slam + Void Step, hit-flashes visible, crown ignites.

**Core skill:** rhythm. Pure aggression punishes you. Bait → dodge → break a shard → burst him briefly while Resonance is low → back off.

---

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
| Navigate trials | `W` / `S` or `↑` / `↓` |
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

For playtesting without dying. On the title screen, type the 6-digit code:

```
114514
```

A green `TEST MODE ENABLED` banner confirms activation; the test-code field border stays green, and during a run a small `TEST MODE` chip shows in the top-right corner. Any wrong code flashes `INVALID CODE` and clears.

In test mode the player takes zero damage from all sources (boss attacks, shard pulses, phantom contact, orb auto-shatter, fated strikes, echo slashes, everything).

## Project layout

```
game_eva/
├── main.py                # entry point
├── requirements.txt
├── assets/                # Kenney's Tiny Dungeon CC0 pack
└── game/
    ├── app.py             # main loop, title + level selector, per-level dispatch
    ├── boss.py            # Hollow King (Resonance, shards, bolts, ring slam)
    ├── mirrorwright.py    # Mirrorwright (Mirror Orb, phantoms, silver rain, volley)
    ├── twin_sovereigns.py # Twin Sovereigns (day/night, sunlance, orbit, flare, star fall)
    ├── fate_weaver.py     # Fate-Weaver (threads, pull, fated strike, weft pulse)
    ├── echo_lord.py       # Echo Lord (snapshots, cascade, memory surge)
    ├── player.py          # movement, sword swing arc, dash, path history
    ├── shard.py           # Crown Shard entities + pulse AoE (level 5)
    ├── projectile.py      # crown bolts (level 5)
    ├── particles.py       # hit sparks, rings, dust
    ├── sprites.py         # sprite factories (Kenney-backed with fallback)
    ├── assets.py          # tilemap loader + named tile constants
    ├── ui.py              # HUD, chip-styled labels, toast panels
    ├── utils.py           # math / arena helpers
    └── constants.py       # all tuning knobs
```

Pixel-art sprites come from Kenney's **Tiny Dungeon** pack (CC0 public domain) at `assets/kenney_tiny-dungeon/`. Each sprite factory in `game/sprites.py` tries the loaded tile first and falls back to a procedurally drawn version if the pack is missing, so the game runs either way.

## Arena & visuals

- **Decor varies per trial.** Echo Lord and Mirrorwright: dim stone gallery with flanking pillars and scattered debris. Twin Sovereigns: open sand hall with minimal obstructions. Fate-Weaver: four crystal-topped stone anchors that her threads connect to. Hollow King: full throne room with four pillars and a cursed throne. All share corner braziers with flickering flame particles.
- **Collision.** The player is pushed out of pillar, brazier, and throne bases with minimum-translation sliding. Ground debris is walk-through and always renders *below* the player.
- **Boss attack visuals.** No plain expanding ellipses: each attack has its own crescent, arc, runic sigil, or rift. Boss sweeps now render using actual pixel-art sword sprites (Bronze-ornate blade for the Hollow King, silver scimitar for the Mirrorwright) rotated through the arc with sprite ghost afterimages. Teleports are vertical rifts with sprite squash and themed particle bursts.
- **HUD.** Every label (DASH, boss name, Resonance/Orb/Thread/Echo values, toasts, phase banner, win/lose, test code) sits on translucent dark chips so text never blends with the arena.

## Credits

- Sprite pack: **Tiny Dungeon** by [Kenney](https://kenney.nl/assets/tiny-dungeon) — Creative Commons Zero (CC0).

## Tuning

Every gameplay number lives in `game/constants.py`, grouped by boss:

- **Player** — `PLAYER_SPEED`, `PLAYER_MAX_HP`, sword/dash timings, attack reach.
- **Hollow King** — `BOSS_MAX_HP`, `BOSS_RESONANCE_PER_HIT`, `BOSS_RESONANCE_DECAY`, `RES_SAFE` / `RES_WARN` / `RES_DANGER` bands.
- **Mirrorwright** — `MIRROR_BOSS_MAX_HP`, `MIRROR_ORB_MAX`, `MIRROR_ORB_SHATTER_P1/P2`, `MIRROR_DASH_DAMAGE_MULT`, `MIRROR_DASH_SHATTER_RADIUS`, `PHANTOM_SPEED`, `SILVER_RAIN_*`, `SHARD_VOLLEY_*`.
- **Twin Sovereigns** — `TWIN_BOSS_HP`, `TWIN_CYCLE_FRAMES`, `TWIN_SUNLANCE_*`, `TWIN_LUNAR_ORBIT_LIFE`, `SOLAR_FLARE_*`, `STAR_FALL_*`.
- **Fate-Weaver** — `WEAVER_MAX_HP`, `WEAVER_MAX_THREADS`, `WEAVER_THREAD_HP`, `WEAVER_THREAD_DEFENSE`, `WEAVER_PULL_*`, `FATED_STRIKE_*`, `WEFT_PULSE_*`.
- **Echo Lord** — `ECHO_LORD_HP`, `ECHO_WARNING_FRAMES`, `ECHO_SLASH_*`, `ECHO_SPAWN_INTERVAL_P1/P2`, `CASCADE_ECHO_*`, `MEMORY_SURGE_TELEGRAPH`.
- **Shards (level 5)** — HP, pulse interval, pulse radius, spawn cadence per phase.
- **Player path history** — `PLAYER_PATH_HISTORY` (140 frames by default) used by Mirrorwright phantoms, Twin Sovereigns star fall, and Echo Lord snapshots.

Change numbers, re-run — no other code touches needed for rebalance.

## Roadmap

- Tile-based overworld connecting the chambers.
- Dialogue and quest log driven by data files.
- Inventory, persistent save, audio.

## License

Personal project. No license declared yet.
