"""Representation of an EnOcean dongle."""
from asyncio import sleep
import glob
from os.path import basename, normpath

from enocean.communicators import SerialCommunicator
from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket
import serial

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import LOGGER, SIGNAL_RECEIVE_MESSAGE, SIGNAL_SEND_MESSAGE
from .utils import enocean_id_to_string


class EnOceanDongle:
    """Representation of an EnOcean dongle.

    The dongle is responsible for receiving the ENOcean frames,
    creating devices if needed, and dispatching messages to platforms.
    """

    def __init__(self, hass: HomeAssistant, serial_path):
        """Initialize the EnOcean dongle."""

        self._communicator = SerialCommunicator(
            port=serial_path, callback=self.enocean_packet_received_callback
        )
        self.serial_path = serial_path
        self.identifier = basename(normpath(serial_path))
        self.hass = hass
        self.dispatcher_disconnect_handle = None

    async def async_setup(self):
        """Finish the setup of the bridge and supported platforms."""
        self._communicator.start()

        # Workaround here: we have to get the base id of the dongle.
        # This is handled by the enocean lib as an asynchronous process,
        # triggered by the first read access to base_id,
        # that will always return None.
        self._communicator.base_id

        self.dispatcher_disconnect_handle = async_dispatcher_connect(
            self.hass, SIGNAL_SEND_MESSAGE, self._send_message_callback
        )

    def unload(self):
        """Disconnect callbacks established at init time."""
        if self.dispatcher_disconnect_handle:
            self.dispatcher_disconnect_handle()
            self.dispatcher_disconnect_handle = None

    def _send_message_callback(self, command):
        """Send a command through the EnOcean dongle."""
        self._communicator.send(command)

    def enocean_packet_received_callback(self, packet):
        """Handle incoming EnOcean packets.

        This is the callback function called by python-enocean whenever there
        is an incoming packet.
        """

        if packet.packet_type == PACKET.RESPONSE:
            # The packet is a response packet from the bridge for the base_id request.
            # We need to re-inject it to the receive queue of the enocean lib,
            # base_id will be available after the receive queue has processed the packet.
            self._communicator.receive.put(packet)

            async def check_dongle_base_id():
                await sleep(0.1)
                dongle_id = self._communicator.base_id
                # Once we have an ID, we can activate teach_in
                # without triggering an exception
                if dongle_id is not None:
                    LOGGER.info("Dongle ID is %s", enocean_id_to_string(dongle_id))
                    self._communicator.teach_in = True

            self.hass.add_job(check_dongle_base_id)

            return

        if isinstance(packet, RadioPacket):
            LOGGER.debug("Received radio packet: %s", packet)
            self.hass.helpers.dispatcher.dispatcher_send(SIGNAL_RECEIVE_MESSAGE, packet)


def detect():
    """Return a list of candidate paths for USB ENOcean dongles.

    This method is currently a bit simplistic, it may need to be
    improved to support more configurations and OS.
    """
    globs_to_test = ["/dev/tty*FTOA2PV*", "/dev/serial/by-id/*EnOcean*"]
    found_paths = []
    for current_glob in globs_to_test:
        found_paths.extend(glob.glob(current_glob))

    return found_paths


def validate_path(path: str):
    """Return True if the provided path points to a valid serial port, False otherwise."""
    try:
        # Creating the serial communicator will raise an exception
        # if it cannot connect
        SerialCommunicator(port=path)
        return True
    except serial.SerialException as exception:
        LOGGER.warning("Dongle path %s is invalid: %s", path, str(exception))
        return False
