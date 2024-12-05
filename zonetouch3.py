import argparse
from collections import defaultdict
import logging
import socket

LOGGER = logging.getLogger(__name__)


class zonetouch3_device:
    def __init__(self, address: str, port: int, zone: str) -> None:
        """Initialize and craft zone entity ."""
        # Set instance variables
        self._initialisation_data = "555555aa90b0071f0002fff0ad8c"
        self._address = address
        self._port = port
        self._zone = zone
        self._state = {"state": False, "percentage": 0}

        if not port:
            port = 7030

    @property
    def state(self):
        """Return current state.."""
        return self._state

    @state.setter
    def state(self, state):
        """Set zone state based on state provided."""
        if state["state"] is None:
            hex_state = "80"  # Hex for percentage
        elif state["state"]:
            hex_state = "03"
        else:
            hex_state = "02"

        percentage = hex(state["percentage"])[2:]  # add parentheses after lower
        # Craft and send Hex data
        self.send_zone_information(hex_state, percentage)

    def get_state(self):
        """Get current state of ZT3 device, filter out particular zone."""
        states = self.connect_ZT3()
        state = states[self._zone]
        # Set instance variables from output
        self._state["state"] = bool(state[0])
        self._state["percentage"] = int(state[1])


    # initial_zone_states, continuous_update_zone_states, and update_zone_states are all information processors.
    # they do the same thing but just interpret the data slightly differently, the setup for all 3 is fairly similar.
    def initial_zone_states(self, tcpDump):
        """
        At the moment the zones are hard coded in, without re-configuring my ZT3 I can't verify
        which hexpair denotes the number of zones, my suspicion is pair 117 based on it being
        the only value in the header that is 7 when converted to ASCII. I'm sure ASCII is
        the correct choice as hexpairs 19-26 spell Polyaire and I could pull the name of each
        zone from the initialisation response as it lists the state, percentage and name for each zone.
        """

        bytePairs = [
            tcpDump[i : i + 2] for i in range(0, len(tcpDump), 2)
        ]  # splitting the hex data into byte pairs as this is how it should be treated.
        zoneStates = defaultdict(list)
        # Each of the below statement checks the state of the zones:
        zoneStates["0"].append(
            bytePairs[123][0] == "4"
        )  # If a zone is on the hexpair is 4?, if off it is 0? where ? is the zone number
        zoneStates["0"].append(
            int(bytePairs[124], 16)
        )  # Check to get zone set percentage
        zoneStates["0"].append(
            int(bytePairs[126], 16)
        )  # Check to get zone actual percentage

        zoneStates["1"].append(bytePairs[145][0] == "4")
        zoneStates["1"].append(int(bytePairs[146], 16))
        zoneStates["1"].append(int(bytePairs[148], 16))

        zoneStates["2"].append(bytePairs[167][0] == "4")
        zoneStates["2"].append(int(bytePairs[168], 16))
        zoneStates["2"].append(int(bytePairs[170], 16))

        zoneStates["3"].append(bytePairs[189][0] == "4")
        zoneStates["3"].append(int(bytePairs[190], 16))
        zoneStates["3"].append(int(bytePairs[192], 16))

        zoneStates["4"].append(bytePairs[211][0] == "4")
        zoneStates["4"].append(int(bytePairs[212], 16))
        zoneStates["4"].append(int(bytePairs[214], 16))

        zoneStates["5"].append(bytePairs[233][0] == "4")
        zoneStates["5"].append(int(bytePairs[234], 16))
        zoneStates["5"].append(int(bytePairs[236], 16))

        zoneStates["6"].append(bytePairs[255][0] == "4")
        zoneStates["6"].append(int(bytePairs[256], 16))
        zoneStates["6"].append(int(bytePairs[258], 16))

        return zoneStates

    def continuous_update_zone_states(self, returnString: str):
        """This is used when the program is connected to the ZT3 and another client modifies zone settings."""

        bytePairs = [returnString[i : i + 2] for i in range(0, len(returnString), 2)]
        zoneStates = defaultdict(list)

        zoneStates["0"].append(
            bytePairs[18][0] == "4"
        )  # Same as initial zone states, this is the on/off determiner
        zoneStates["0"].append(
            int(bytePairs[19], 16)
        )  # This is the set percentage, not actual percentage

        zoneStates["1"].append(bytePairs[26][0] == "4")
        zoneStates["1"].append(int(bytePairs[27], 16))

        zoneStates["2"].append(bytePairs[34][0] == "4")
        zoneStates["2"].append(int(bytePairs[35], 16))

        zoneStates["3"].append(bytePairs[42][0] == "4")
        zoneStates["3"].append(int(bytePairs[43], 16))

        zoneStates["4"].append(bytePairs[50][0] == "4")
        zoneStates["4"].append(int(bytePairs[51], 16))

        zoneStates["5"].append(bytePairs[58][0] == "4")
        zoneStates["5"].append(int(bytePairs[59], 16))

        zoneStates["6"].append(bytePairs[66][0] == "4")
        zoneStates["6"].append(int(bytePairs[67], 16))

        return zoneStates

    def update_zone_states(self, returnString: str):
        """Update zone states."""

        bytePairs = [returnString[i : i + 2] for i in range(0, len(returnString), 2)]
        zoneStates = defaultdict(list)
        # Same as continuous but data is located in different places

        zoneStates["0"].append(
            bytePairs[18][0] == "4"
        )  # Same as initial zone states, this is the on/off determiner
        zoneStates["0"].append(
            int(bytePairs[21], 16)
        )  # This is the set percentage, not actual percentage

        zoneStates["1"].append(bytePairs[26][0] == "4")
        zoneStates["1"].append(int(bytePairs[29], 16))

        zoneStates["2"].append(bytePairs[34][0] == "4")
        zoneStates["2"].append(int(bytePairs[37], 16))

        zoneStates["3"].append(bytePairs[42][0] == "4")
        zoneStates["3"].append(int(bytePairs[45], 16))

        zoneStates["4"].append(bytePairs[50][0] == "4")
        zoneStates["4"].append(int(bytePairs[53], 16))

        zoneStates["5"].append(bytePairs[58][0] == "4")
        zoneStates["5"].append(int(bytePairs[61], 16))

        zoneStates["6"].append(bytePairs[66][0] == "4")
        zoneStates["6"].append(int(bytePairs[69], 16))

        return zoneStates

    def crc16_modbus(self, data_hex: str) -> str:
        import struct

        # CRC16 checksum required to be appended to set commands with ZT3
        def calc_crc16(data: bytes, poly: int = 0xA001) -> int:
            crc = 0xFFFF
            for b in data:
                crc ^= b
                for _ in range(8):
                    if crc & 0x0001:
                        crc = (crc >> 1) ^ poly
                    else:
                        crc >>= 1
            return crc

        # Convert hex string to byte array
        data_bytes = bytes.fromhex(data_hex)

        # Calculate CRC16 checksum
        crc = calc_crc16(data_bytes)

        # Convert CRC to a hex string
        crc_hex = format(crc, "04x").upper()
        return crc_hex

    def hex_string(self, hex_data: list) -> str:
        hex_string = ""
        for i in hex_data:
            hex_string += i
        return hex_string

    def send_hex_data(self, hex_data: str) -> str:
        # Convert hex data to bytes
        data_bytes = bytes.fromhex(hex_data)
        # print(hex_data)

        # Create a socket object
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Connect to the server
            s.connect((self._address, self._port))

            # Send the data
            s.sendall(data_bytes)

            # Receive and print the response
            response_bytes = s.recv(1024)
            response_hex = response_bytes.hex().upper()
            return response_hex

    def connect_ZT3(self):
        initialQueryData = self.send_hex_data(self._initialisation_data)
        # Initialisation data is what the ZT3 app sends to the ZT3 when opening communication, I just sniffed it and use it here.
        zone_states = self.initial_zone_states(initialQueryData)
        return zone_states

    def send_zone_information(self, state, percentage):
        hex_data = [
            "55",
            "55",
            "55",
            "aa",
            "80",
            "b0",
            "12",
            "c0",
            "00",
            "0c",
            "20",
            "00",
            "00",
            "00",
            "00",
            "04",
            "00",
            "01",
            "00",
            "03",
            "00",
            "00",
            "65",
            "79",
        ]
        hex_data[18] = "0" + self._zone
        hex_data[19] = state
        hex_data[20] = percentage

        data = self.hex_string(hex_data[4:22])
        checksum = self.hex_string(self.crc16_modbus(data))
        hex_data[22] = checksum[0:2]
        hex_data[23] = checksum[2:4]
        response_hex = self.send_hex_data(self.hex_string(hex_data))
        return response_hex
