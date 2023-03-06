"""Support for DoorBird devices."""
from __future__ import annotations
import asyncio

from http import HTTPStatus
import logging

from doorbirdpy import DoorBird
import requests
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MJPEG_VIDEO,
    DOMAIN,
    DOOR_STATION,
    DOOR_STATION_EVENT_ENTITY_IDS,
    DOOR_STATION_INFO,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

RESET_DEVICE_FAVORITES = "doorbird_reset_favorites"

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PORT, default=80): cv.port,
        vol.Optional(CONF_SSL, default=False): cv.boolean,
        vol.Optional(CONF_MJPEG_VIDEO, default=False): cv.boolean,
        vol.Optional(CONF_NAME): cv.string,
    }
)

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the DoorBird component."""
    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DoorBird from a config entry."""

    doorstation_config = entry.data
    config_entry_id = entry.entry_id

    device_ip = doorstation_config[CONF_HOST]
    username = doorstation_config[CONF_USERNAME]
    password = doorstation_config[CONF_PASSWORD]
    secure = doorstation_config[CONF_SSL]
    port = doorstation_config[CONF_PORT]

    device = DoorBird(device_ip, username, password, secure=secure, port=port)
    try:
        status, info = await hass.async_add_executor_job(_init_doorbird_device, device)
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == HTTPStatus.UNAUTHORIZED:
            _LOGGER.error(
                "Authorization rejected by DoorBird for %s@%s", username, device_ip
            )
            return False
        raise ConfigEntryNotReady from err
    except OSError as oserr:
        _LOGGER.error("Failed to setup doorbird at %s: %s", device_ip, oserr)
        raise ConfigEntryNotReady from oserr

    if not status[0]:
        _LOGGER.error(
            "Could not connect to DoorBird as %s@%s: Error %s",
            username,
            device_ip,
            str(status[1]),
        )
        raise ConfigEntryNotReady

    name = doorstation_config.get(CONF_NAME)
    doorstation = ConfiguredDoorBird(device, name)

    async def async_notify_event(event):
        print("FIRING EVENT: " + event)
        event_data = doorstation.get_event_data()
        event_data[ATTR_ENTITY_ID] = hass.data[DOMAIN][
            DOOR_STATION_EVENT_ENTITY_IDS
        ].get(event)
        hass.bus.async_fire(f"{DOMAIN}_{event}", event_data)

    def handle_event(event):
        asyncio.run_coroutine_threadsafe(async_notify_event(event), hass.loop)

    async def async_handle_error(error):
        _LOGGER.error(error)
        hass.config_entries.async_reload(entry.entry_id)

    def handle_error(error):
        print("ERROR!: " + error)
        asyncio.run_coroutine_threadsafe(async_handle_error(error), hass.loop)

    # Subscribe to doorbell and motion events
    device.start_monitoring(handle_event, handle_error)

    hass.data[DOMAIN][config_entry_id] = {
        DOOR_STATION: doorstation,
        DOOR_STATION_INFO: info,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


def _init_doorbird_device(device):
    return device.ready(), device.info()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # stop monitoring device
    await hass.data[DOMAIN][entry.entry_id][DOOR_STATION].device.stop_monitoring()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class ConfiguredDoorBird:
    """Attach additional information to pass along with configured device."""

    def __init__(self, device, name):
        """Initialize configured device."""
        self._name = name
        self._device = device

    @property
    def name(self):
        """Get custom device name."""
        return self._name

    @property
    def device(self):
        """Get the configured device."""
        return self._device

    def get_event_data(self):
        """Get data to pass along with HA event."""
        return {
            "timestamp": dt_util.utcnow().isoformat(),
            "live_video_url": self._device.live_video_url,
            "live_image_url": self._device.live_image_url,
            "rtsp_live_video_url": self._device.rtsp_live_video_url,
            "html5_viewer_url": self._device.html5_viewer_url,
        }
