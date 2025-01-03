from collections import defaultdict
import logging
import socket
import concurrent.futures

LOGGER = logging.getLogger("zonetouch3")


class zonetouch3_device:
    def __init__(self, address: str, port: int, zone: str) -> None:
        """Initialize and craft zone entity ."""
        # Set instance variables
        self._initialisation_data = "555555aa90b0071f0002fff0ad8c"
        self._address = address
        self._port = port
        self._zone = zone
        self._state = {"state": False, "percentage": 0}

    @property
    def state(self):
        """Return current state."""
        return self._state

    @state.setter
    def state(self, state):
        """Set zone state (in hex) based on state provided."""
        if state["state"] is None:
            hex_state = "80"  # Hex for percentage
        elif state["state"]:
            hex_state = "03"  # Hex for on
        else:
            hex_state = "02"  # Hex for off

        if state["percentage"] is None:
            state["percentage"] = 00

        if state["percentage"] <= 15:
            hex_percentage = "0" + hex(state["percentage"])[2:]
        else:
            hex_percentage = hex(state["percentage"])[2:]

        # Craft and send Hex data
        self.send_zone_information(hex_state, hex_percentage)

    def get_state(self):
        """Get current state of ZT3 zone."""
        state = self.connect_ZT3()
        # Set instance variables from output
        self._state["state"] = bool(state[0])
        self._state["percentage"] = int(state[1])

    def initial_zone_states(self, tcpDump):
        """Craft payload for reviving Zone State."""
        bytePairs = [
            tcpDump[i : i + 2] for i in range(0, len(tcpDump), 2)
        ]  # splitting the hex data into byte pairs as this is how it should be treated.
        zoneStates = defaultdict(list)

        # Find the starting pair
        # zoneStartingPair = bytePairs.index(str(40 + int(self._zone)))
        # another option
        zoneStartingPair = 123 + (22 * (int(self._zone)))
        if int(self._zone) >= 8:
            zoneStartingPair += 1

        zoneStates[self._zone].append(bytePairs[zoneStartingPair][0] == "4")
        zoneStates[self._zone].append(int(bytePairs[zoneStartingPair + 1], 16))
        zoneStates[self._zone].append(int(bytePairs[zoneStartingPair + 2], 16))
        return zoneStates

    def crc16_modbus(self, data_hex: str) -> str:
        """CRC16 checksum required to be appended to set commands with ZT3."""

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
        """Hex to string."""
        hex_string = ""
        for i in hex_data:
            hex_string += i
        return hex_string

    def send_hex_data(self, hex_data: str) -> str:
        """Send hex payload data."""
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
        """Send payload and receive zone data."""
        # Send payload and retrieve state data
        # Initialization data is what the ZT3 app sends to the ZT3 when opening communication.
        initialQueryData = self.send_hex_data(self._initialisation_data)
        # Filter that data to find zone state
        zone_state = self.initial_zone_states(initialQueryData)[self._zone]
        return zone_state

    def send_zone_information(self, state, percentage):
        """Craft payload send zone state."""
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

        # if int(self._zone) <= 15:
        hex_data[18] = "0" + hex(int(self._zone))[2:]
        # else:
        #     hex_data[18] = hex(int(self._zone))[2:]
        hex_data[19] = state
        hex_data[20] = percentage

        data = self.hex_string(hex_data[4:22])
        checksum = self.hex_string(self.crc16_modbus(data))
        hex_data[22] = checksum[0:2]
        hex_data[23] = checksum[2:4]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.send_hex_data, self.hex_string(hex_data))
            response_hex = future.result()
        return response_hex
