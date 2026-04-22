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

# ---- Level 3: Twin Sovereigns ----
TWIN_BOSS_HP = 180              # each king has this much HP
TWIN_CYCLE_FRAMES = 720         # 12s day/night cycle
TWIN_SUNLANCE_WINDUP = 40
TWIN_SUNLANCE_LIFE = 60
TWIN_SUNLANCE_WIDTH = 22
TWIN_LUNAR_ORBIT_LIFE = 360     # crescent chases for 6s
TWIN_CONTACT_DAMAGE = 0         # no body contact damage (matches other bosses)

# ---- Level 4: Fate-Weaver ----
WEAVER_MAX_HP = 300
WEAVER_MAX_THREADS = 4
WEAVER_THREAD_HP = 20
WEAVER_THREAD_DEFENSE = 0.18    # each live thread reduces damage taken by 18%
WEAVER_PULL_WINDUP = 40
WEAVER_PULL_SPEED = 12.0
WEAVER_PULL_WIDTH = 26
WEAVER_ENRAGE_HP_PCT = 0.5

# ---- Level 5: Echo Lord ----
ECHO_LORD_HP = 300
ECHO_WARNING_FRAMES = 52        # echo glows red for ~1s before firing
ECHO_SLASH_FRAMES = 16          # line-slash active window
ECHO_SLASH_LENGTH = 160
ECHO_SLASH_WIDTH = 16
ECHO_SPAWN_INTERVAL_P1 = 130
ECHO_SPAWN_INTERVAL_P2 = 70
ECHO_MAX_ON_FIELD = 5
ECHO_LORD_ENRAGE_HP_PCT = 0.45

# ---- New skill tuning ----
# Mirrorwright Silver Rain
SILVER_RAIN_ZONES = 4
SILVER_RAIN_TELEGRAPH = 50
SILVER_RAIN_ACTIVE = 32
SILVER_RAIN_RADIUS = 46
# Mirrorwright Shard Volley
SHARD_VOLLEY_COUNT = 5
SHARD_VOLLEY_SPREAD = 0.70       # radians total spread across the fan
MIRROR_SHARD_SPEED = 3.6
MIRROR_SHARD_DAMAGE = 1

# Twin Sovereigns
SOLAR_FLARE_TELEGRAPH = 34
SOLAR_FLARE_GROWTH = 70          # frames expanding
SOLAR_FLARE_MAX_RADIUS = 180
SOLAR_FLARE_EDGE_WIDTH = 22
STAR_FALL_COUNT = 3
STAR_FALL_TELEGRAPH = 56
STAR_FALL_RADIUS = 38

# Fate-Weaver
FATED_STRIKE_DELAY = 115         # frames between mark and impact
FATED_STRIKE_RADIUS = 52
WEFT_PULSE_TELEGRAPH = 40
WEFT_PULSE_ACTIVE = 22
WEFT_PULSE_HALF_WIDTH = 10

# Echo Lord
CASCADE_ECHO_COUNT = 4
CASCADE_ECHO_STAGGER = 18        # frames between sequential warning starts
MEMORY_SURGE_TELEGRAPH = 34
