"""Constants for Meshtastic UI integration."""

DOMAIN = "meshtastic_ui"

# Storage
STORAGE_KEY = "meshtastic_ui.messages"
STORAGE_VERSION = 1
SAVE_DELAY = 30  # seconds

# Message limits
MAX_CHANNEL_MESSAGES = 500
MAX_DM_MESSAGES = 200

# Node retention
NODE_RETENTION_DAYS = 7
ACTIVE_NODE_WINDOW_SECONDS = 3600  # 1 hour

# Events from meshtastic integration
EVENT_MESHTASTIC_MESSAGE_LOG = "meshtastic_message_log"
EVENT_MESHTASTIC_EVENT = "meshtastic_event"

# Internal dispatcher signals
SIGNAL_NEW_MESSAGE = f"{DOMAIN}_new_message"

# WebSocket command prefix
WS_PREFIX = f"{DOMAIN}"

# Frontend
PANEL_URL = "meshtastic-ui"
PANEL_TITLE = "Mesh UI"
PANEL_ICON = "mdi:radio-handheld"
FRONTEND_PATH = "frontend"
