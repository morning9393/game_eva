"""Central tuning knobs and palette for Crown of Hollow."""

SCREEN_W, SCREEN_H = 960, 600
FPS = 60

ARENA_W, ARENA_H = 880, 500
ARENA_X = (SCREEN_W - ARENA_W) // 2
ARENA_Y = (SCREEN_H - ARENA_H) // 2 + 20

TITLE = "Crown of Hollow"

# Palette - a muted fantasy set
BLACK = (12, 10, 18)
DEEP = (22, 20, 34)
STONE = (58, 54, 74)
STONE_LIGHT = (92, 88, 112)
BONE = (214, 204, 180)
BLOOD = (178, 40, 52)
EMBER = (240, 140, 60)
GOLD = (236, 196, 104)
AZURE = (100, 168, 220)
VIOLET = (148, 96, 210)
MOSS = (96, 142, 78)
WHITE = (240, 240, 240)

# Player
PLAYER_SPEED = 3.1
PLAYER_MAX_HP = 5
PLAYER_IFRAMES = 45             # frames
PLAYER_ATTACK_DAMAGE = 10
PLAYER_ATTACK_WINDUP = 6
PLAYER_ATTACK_ACTIVE = 10
PLAYER_ATTACK_RECOVER = 10
PLAYER_ATTACK_REACH = 78
PLAYER_ATTACK_HEIGHT = 52
PLAYER_DASH_FRAMES = 14
PLAYER_DASH_SPEED = 7.2
PLAYER_DASH_COOLDOWN = 55

# Boss
BOSS_MAX_HP = 320
BOSS_MAX_RESONANCE = 100.0
BOSS_RESONANCE_PER_HIT = 18.0
BOSS_RESONANCE_DECAY = 0.05     # per frame passive decay
BOSS_SPEED = 1.3
BOSS_CONTACT_DAMAGE = 1
BOSS_ENRAGE_HP_PCT = 0.5

# Resonance reaction thresholds
RES_SAFE = 40.0                 # full damage below this
RES_WARN = 70.0                 # damage scales down between safe and warn
RES_DANGER = 90.0               # reflect + heal above this

# Shards
SHARD_MAX_HP = 30
SHARD_RESONANCE_DRAIN = 28.0
SHARD_PULSE_INTERVAL = 150      # frames
SHARD_PULSE_RADIUS = 68
SHARD_SPAWN_INTERVAL_P1 = 360
SHARD_SPAWN_INTERVAL_P2 = 220
SHARD_MAX_ON_FIELD = 5

# Projectiles
CROWN_BOLT_SPEED = 3.6
CROWN_BOLT_DAMAGE = 1

# UI
HUD_MARGIN = 16

# ---- Level 2: The Mirrorwright ----
MIRROR_BOSS_MAX_HP = 280
MIRROR_ORB_MAX = 80.0
MIRROR_ORB_SHATTER_P1 = 80.0    # phase 1 auto-shatter threshold
MIRROR_ORB_SHATTER_P2 = 60.0    # phase 2 shatters sooner
MIRROR_ORB_DECAY = 0.0          # no passive decay - must be shattered
MIRROR_AUTO_SHATTER_DAMAGE = 2  # cap damage dealt to player on auto-shatter
MIRROR_DASH_SHATTER_RADIUS = 62 # dash within this of boss chest to trigger
MIRROR_DASH_DAMAGE_MULT = 1.5   # queued damage multiplied on dash-shatter
MIRROR_BOSS_ENRAGE_HP_PCT = 0.4

PHANTOM_SPEED = 3.4
PHANTOM_DAMAGE = 1
PLAYER_PATH_HISTORY = 140       # frames of history to record for phantom retrace
