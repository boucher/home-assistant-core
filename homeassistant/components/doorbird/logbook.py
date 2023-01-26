"""Describe logbook events."""
from __future__ import annotations

from homeassistant.components.logbook import (
    LOGBOOK_ENTRY_ENTITY_ID,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import callback

from .const import DOMAIN, DOOR_STATION_EVENT_ENTITY_IDS


@callback
def async_describe_events(hass, async_describe_event):
    """Describe logbook events."""

    @callback
    def async_describe_logbook_event(event):
        """Describe a logbook event."""
        doorbird_event = event.event_type.split("_", 1)[1]

        return {
            LOGBOOK_ENTRY_NAME: "Doorbird",
            LOGBOOK_ENTRY_MESSAGE: f"Event {event.event_type} was fired",
            LOGBOOK_ENTRY_ENTITY_ID: hass.data[DOMAIN][
                DOOR_STATION_EVENT_ENTITY_IDS
            ].get(doorbird_event, event.data.get(ATTR_ENTITY_ID)),
        }

    for doorbird_event in ("doorbell", "motionsensor"):
        async_describe_event(
            DOMAIN, f"{DOMAIN}_{doorbird_event}", async_describe_logbook_event
        )
