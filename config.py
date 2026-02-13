"""
NOVA Global Configuration

Central configuration for runtime behavior.
"""

# Debug Mode Control
# Set to False for production - suppresses internal logs
DEBUG = False

# Memory Configuration
MIN_TOPIC_LENGTH = 3
MEMORY_BLACKLIST_TERMS = {"memory", "recall", "remember", "note"}

# Execution Configuration
MAX_CORRECTION_ATTEMPTS = 2
CONFIRMATION_TIMEOUT = 60  # seconds

# Telemetry Configuration
TELEMETRY_RETENTION_DAYS = 30
