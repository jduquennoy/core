"""Test EnOcean utilities."""
from enocean.protocol.constants import PACKET, RORG
from enocean.protocol.packet import RadioPacket, UTETeachIn
from pytest import raises

from homeassistant.components.enocean.utilities import (
    DiscoveredEnOceanDeviceInfo,
    EnOceanEEP,
    InvalidEnOceanId,
    enocean_id_to_string,
)


async def test_create_enocean_eep_from_valid_string(hass):
    """Test that enocean eep is correctly created from a string value."""
    eep = EnOceanEEP("A1:B2:C3")

    assert eep.rorg == 0xA1
    assert eep.func == 0xB2
    assert eep.type == 0xC3


async def test_create_enocean_eep_from_invalid_string_raises_exception(hass):
    """Test that enocean eep raises an exception when decoding an invalid string."""
    with raises(InvalidEnOceanId):
        EnOceanEEP("A1:B2")

    with raises(InvalidEnOceanId):
        EnOceanEEP("A1:invalidValue:C3")


async def test_create_enocean_eep_from_valid_list(hass):
    """Test that enocean eep is correctly created from a list of three integer values."""
    eep = EnOceanEEP([0x1A, 0x2B, 0x3C])

    assert eep.rorg == 0x1A
    assert eep.func == 0x2B
    assert eep.type == 0x3C


async def test_create_enocean_eep_from_invalid_list_raises_exception(hass):
    """Test that enocean eep is correctly created from a list of three integer values."""
    with raises(InvalidEnOceanId):
        EnOceanEEP([0x1A, "invalidValue", 0x3C])

    with raises(InvalidEnOceanId):
        EnOceanEEP([0x1A, 0x3C])


async def test_eep_equality(hass):
    """Test equality of EnOceanEEP objects."""
    assert EnOceanEEP([0x1A, 0x2B, 0x3C]) == EnOceanEEP([0x1A, 0x2B, 0x3C])
    assert EnOceanEEP([0x1A, 0x2B, 0x3C]) != EnOceanEEP([0x1A, 0x2B, 0x00])
    assert EnOceanEEP([0x1A, 0x2B, 0x3C]) != EnOceanEEP([0x1A, 0x00, 0x3D])
    assert EnOceanEEP([0x1A, 0x2B, 0x3C]) != EnOceanEEP([0x00, 0x2B, 0x3D])


async def test_enocean_eep_string_conversion_cycle(hass):
    """Test that conversion between EnOceanEEP and string preserves all information."""
    eep = EnOceanEEP([0x1A, 0x2B, 0x3C])
    eep2 = EnOceanEEP(eep.string_representation)

    assert eep == eep2


async def test_discovered_enocean_device_properties(hass):
    """Test the name and device_id properties of the discovered structure."""
    sender = [0x04, 0x05, 0x06, 0x07]
    packet = RadioPacket.create(
        rorg=RORG.BS1, rorg_func=0x02, rorg_type=0x03, sender=sender
    )

    info = DiscoveredEnOceanDeviceInfo(packet)

    assert enocean_id_to_string(sender) in info.name
    assert info.device_id == enocean_id_to_string(sender)


async def test_discovered_enocean_device_has_eep_for_teachin_packets(hass):
    """Test that discoverdEnOceanDevice reports and EEP for teachin packets."""
    packet = UTETeachIn(
        PACKET.RADIO,
        data=[0xD4, 0xA0, 0x1, 0x46, 0x0, 0xA, 0x1, 0xD2, 0x1, 0xA3, 0x19, 0xB2, 0x0],
        optional=[0x1, 0xFF, 0xFF, 0xFF, 0xFF, 0x47, 0x0],
    )

    info = DiscoveredEnOceanDeviceInfo(packet)

    assert info.eep == EnOceanEEP([RORG.VLD, 0x01, 0x0A])
