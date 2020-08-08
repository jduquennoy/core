"""Utility methods and classes for ENOcean operation."""
from typing import List

from enocean.protocol.packet import RadioPacket, UTETeachIn

from homeassistant.exceptions import HomeAssistantError


class InvalidEnOceanId(HomeAssistantError):
    """When an EnOcean device ID does not match the expected format."""

    def __init__(self, invalid_value) -> None:
        """Init the error."""
        super().__init__(f"Invalid enocean id: {invalid_value}")


class InvalidEnOceanEEP(HomeAssistantError):
    """When an EnOcean device EEP does not match the expected format."""

    def __init__(self, invalid_value) -> None:
        """Init the error."""
        super().__init__(f"Invalid enocean EEP: {invalid_value}")


def enocean_id_to_string(identifier: List[int]) -> str:
    """Return a decodable string representation of an ENOcean identifier."""
    return ":".join([f"{val:02X}" for val in identifier])


def string_to_enocean_id(identifier: str) -> List[int]:
    """Return an EnOcean identifier as a list of ints from a string.

    Raises InvalidEnOceanId if the input is invalid.
    """
    try:
        id_elements = [int(element, 16) for element in identifier.split(":")]
    except ValueError:
        raise InvalidEnOceanId(identifier)

    if len(id_elements) != 4 or not all(isinstance(x, int) for x in id_elements):
        raise InvalidEnOceanId(id_elements)

    return id_elements


class EnOceanEEP:
    """Represent an Enocean Equipment profile.

    This profile is what defines a device capabilities. It is a three levels
    hierarchical identifier composed of RORG, func and type.
    """

    def __init__(self, input_eep):
        """Create an EEP either from a string or an array of 3 integer values.

        Raises InvalidEnOceanEEP if the input is invalid.
        """
        if isinstance(input_eep, str):
            try:
                eep_elements = [int(element, 16) for element in input_eep.split(":")]
            except ValueError:
                raise InvalidEnOceanEEP(input_eep)
        elif isinstance(input_eep, list):
            eep_elements = input_eep

        if len(eep_elements) != 3 or not all(isinstance(x, int) for x in eep_elements):
            raise InvalidEnOceanEEP(eep_elements)

        self.rorg = eep_elements[0]
        self.func = eep_elements[1]
        self.type = eep_elements[2]

    def __str__(self):
        """Return a string representation."""
        return f"{self.rorg:02X}:{self.func:02X}:{self.type:02X}"

    def __eq__(self, other):
        """Return true if the argument is equal to self."""
        if not isinstance(other, EnOceanEEP):
            return False
        return (
            self.rorg == other.rorg
            and self.func == other.func
            and self.type == other.type
        )

    @property
    def string_representation(self):
        """Return a string representation of the EEP, that can be used to re-create it."""
        return self.__str__()


class DiscoveredEnOceanDeviceInfo:
    """A class that contains infos of a newly discovered EnOcean device."""

    def __init__(self, packet: RadioPacket):
        """Init."""
        self.packet = packet

    @property
    def name(self) -> str:
        """Return the name that should be usef to identify the device."""
        return "ENOcean device " + enocean_id_to_string(self.packet.sender)

    @property
    def device_id(self) -> str:
        """Return the id to use for the device."""
        return enocean_id_to_string(self.packet.sender)

    @property
    def eep(self) -> EnOceanEEP:
        """Return the EEP of the packet if available, None otherwise."""
        if self.packet.rorg_type is None or self.packet.rorg_func is None:
            return None

        rorg = self.packet.rorg
        if isinstance(self.packet, UTETeachIn):
            rorg = self.packet.rorg_of_eep

        return EnOceanEEP([rorg, self.packet.rorg_func, self.packet.rorg_type])
