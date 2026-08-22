"""Application-wide constants.

Organized by section. Import specific constants where needed.
Changing a value here updates it everywhere.
"""

# --- Deck ---
DECK_SIZE = 52
MAX_PLAYERS = 8
MIN_PLAYERS = 2

# --- Game Defaults ---
DEFAULT_ROUNDS_PER_SET = 8
DEFAULT_NUM_SETS = 3
DEFAULT_MODE = "expert"
DEFAULT_APPEARANCE = "standard"
DEFAULT_SCORING_FORMULA = "kachuful_standard"
DEFAULT_TIMER_SECONDS = 3
DEFAULT_MUST_LOSE = False

# --- Trump Rotation ---
TRUMP_ORDER = ["spades", "diamonds", "clubs", "hearts"]

# --- Session / Auth ---
SESSION_COOKIE_NAME = "scokeep_session"
SESSION_MAX_AGE_AUTH = 60 * 60 * 24 * 30  # 30 days (PIN auth)
SESSION_MAX_AGE_JOIN = 60 * 60 * 2  # 2 hours (share code join)
ACTIVE_GAME_TTL_MINUTES = 60 * 24  # 24 hours — game resumable for a full day

# --- Playground ---
SHARE_CODE_LENGTH = 4

# --- Rate Limiting ---
AUTH_RATE_LIMIT = "5/minute"

# --- High Roller Threshold (for awards) ---
HIGH_ROLLER_MIN_BID = 3
