"""DoorBird integration utils."""

from .const import DOMAIN, DOOR_STATION


def get_mac_address_from_doorstation_info(doorstation_info):
    """Get the mac address depending on the device type."""
    if "PRIMARY_MAC_ADDR" in doorstation_info:
        return doorstation_info["PRIMARY_MAC_ADDR"]
    return doorstation_info["WIFI_MAC_ADDR"]


def get_all_doorstations(hass):
    """Get all doorstations."""
    return [
        entry[DOOR_STATION]
        for entry in hass.data[DOMAIN].values()
        if DOOR_STATION in entry
    ]
