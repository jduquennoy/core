"""Support for EnOcean switches."""
import logging
from typing import List

from utilities import DiscoveredEnOceanDeviceInfo, EnOceanEEP, string_to_enocean_id
import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.const import CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.helpers.entity_registry import async_entries_for_config_entry

from .device import EnOceanEntity

_LOGGER = logging.getLogger(__name__)

CONF_CHANNEL = "channel"
DEFAULT_NAME = "EnOcean Switch"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_CHANNEL, default=0): cv.positive_int,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the EnOcean switch platform."""
    channel = config.get(CONF_CHANNEL)
    dev_id = config.get(CONF_ID)
    dev_name = config.get(CONF_NAME)

    add_entities([EnOceanSwitch(dev_id=dev_id, dev_name=dev_name, channel=channel)])


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up binary sensors for the ENOcean component."""

    entities_to_add = []

    # Load entities from registry
    entities_registry = await entity_registry.async_get_registry(hass)
    entities_from_config = async_entries_for_config_entry(
        entities_registry, config_entry.entry_id
    )

    for entry in entities_from_config:
        entities_to_add.append(
            EnOceanSwitch(
                string_to_enocean_id(entry.unique_id), entry.name, entry.device_class,
            )
        )

    def entity_already_exists(input_id: str):
        for entity in entities_to_add:
            if entity.unique_id == input_id:
                return True
        return False

    async_add_entities(entities_to_add, True)


def entities_for_discovered_device(
    hass, discovery_info: DiscoveredEnOceanDeviceInfo
) -> List[EnOceanEntity]:
    """Return a list of entities for a discovered device."""

    entities = []
    eep = discovery_info.eep

    # D2-01-* Electronic switches and dimmers
    if eep.rorg == 0xD2 and eep.func == 0x01:
        entities.append(
            EnOceanSwitch(dev_id=discovery_info.device_id, eep=eep, channel=1)
        )
        if eep.type in [0x10, 0x11]:
            entities.append(
                EnOceanSwitch(dev_id=discovery_info.device_id, eep=eep, channel=2),
            )


class EnOceanSwitch(EnOceanEntity, ToggleEntity):
    """Representation of an EnOcean switch device."""

    def __init__(
        self,
        dev_id: str,
        eep: EnOceanEEP = None,
        dev_name: str = None,
        channel: int = 1,
    ):
        """Initialize the EnOcean switch device."""
        dev_name = dev_name or f"EnOcean switch {dev_id} - 1"
        super().__init__(dev_id, eep, dev_name)
        self._light = None
        self._on_state = False
        self._on_state2 = False
        self.channel = channel

    @property
    def is_on(self):
        """Return whether the switch is on or off."""
        return self._on_state

    @property
    def name(self):
        """Return the device name."""
        return self.dev_name

    def turn_on(self, **kwargs):
        """Turn on the switch."""
        optional = [0x03]
        optional.extend(self.dev_id)
        optional.extend([0xFF, 0x00])
        self.send_command(
            data=[0xD2, 0x01, self.channel & 0xFF, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00],
            optional=optional,
            packet_type=0x01,
        )
        self._on_state = True

    def turn_off(self, **kwargs):
        """Turn off the switch."""
        optional = [0x03]
        optional.extend(self.dev_id)
        optional.extend([0xFF, 0x00])
        self.send_command(
            data=[0xD2, 0x01, self.channel & 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
            optional=optional,
            packet_type=0x01,
        )
        self._on_state = False

    def value_changed(self, packet):
        """Update the internal state of the switch."""
        if packet.data[0] == 0xA5:
            # power meter telegram, turn on if > 10 watts
            packet.parse_eep(0x12, 0x01)
            if packet.parsed["DT"]["raw_value"] == 1:
                raw_val = packet.parsed["MR"]["raw_value"]
                divisor = packet.parsed["DIV"]["raw_value"]
                watts = raw_val / (10 ** divisor)
                if watts > 1:
                    self._on_state = True
                    self.schedule_update_ha_state()
        elif packet.data[0] == 0xD2:
            # actuator status telegram
            packet.parse_eep(0x01, 0x01)
            if packet.parsed["CMD"]["raw_value"] == 4:
                channel = packet.parsed["IO"]["raw_value"]
                output = packet.parsed["OV"]["raw_value"]
                if channel == self.channel:
                    self._on_state = output > 0
                    self.schedule_update_ha_state()
