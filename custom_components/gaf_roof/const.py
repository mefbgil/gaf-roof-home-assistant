"""Constants for the GAF Roof integration."""

from datetime import timedelta

DOMAIN = "gaf_roof"
PLATFORMS = ["sensor"]

CONF_POLL_INTERVAL = "poll_interval"
DEFAULT_POLL_INTERVAL = 300
MIN_POLL_INTERVAL = 30
MAX_POLL_INTERVAL = 3600

LOGIN_URL = "https://gaf-coreservices.aurai.io/cognito/login"
DEVICE_LIST_URL = "https://gaf.keenhome.io/gaf/device/deviceList"
USER_POOL_ID = "us-east-2_F6aHzg32w"
USER_ROLE = "contractor"
REQUEST_TIMEOUT = 15


def update_interval(seconds: int) -> timedelta:
    """Return a validated coordinator interval."""
    return timedelta(
        seconds=max(MIN_POLL_INTERVAL, min(MAX_POLL_INTERVAL, seconds))
    )
