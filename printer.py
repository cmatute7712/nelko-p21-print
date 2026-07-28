"""Serial protocol support for the Nelko P21 label printer."""

import os
import struct
from dataclasses import dataclass
from enum import IntEnum

import serial
from PIL import Image
from packaging.version import Version
from serial.tools import list_ports


LABEL_WIDTH = 96
LABEL_HEIGHT = 284
BAUD_RATE = 115200
DEFAULT_DEVICE = None if os.name == "nt" else "/dev/rfcomm0"


class TimeoutSetting(IntEnum):
    NEVER = 0
    MINUTES_15 = 1
    MINUTES_30 = 2
    MINUTES_60 = 3

    def __str__(self):
        return {0: "Never", 1: "15 minutes", 2: "30 minutes", 3: "60 minutes"}.get(
            int(self), "Unknown"
        )


class BeepSetting(IntEnum):
    OFF = 0
    ON = 1

    def __str__(self):
        return "On" if self == BeepSetting.ON else "Off"


class PaperType(IntEnum):
    CONTINUOUS = 0
    GAPPED = 1
    BLACKMARK = 2

    def __str__(self):
        return {0: "Continuous", 1: "Gapped", 2: "Blackmark"}.get(
            int(self), "Unknown"
        )


class Readiness(IntEnum):
    READY = 0
    LID_OPEN = 1
    OUT_OF_PAPER = 4
    BUSY = 32

    def __str__(self):
        return {0: "Ready", 1: "Lid open", 4: "Paper not loaded", 32: "Busy"}.get(
            int(self), "Unknown"
        )


@dataclass
class DeviceConfig:
    dpi_resolution: int
    hardware_version: Version
    firmware_version: Version
    timeout: TimeoutSetting
    beep: BeepSetting

    def __str__(self):
        return (
            f"DPI resolution: {self.dpi_resolution}\n"
            f"Hardware version: {self.hardware_version}\n"
            f"Firmware version: {self.firmware_version}\n"
            f"Timeout: {self.timeout}\nBeep: {self.beep}"
        )


@dataclass
class PrinterStatus:
    readiness: Readiness
    label_color: int
    paper_type: PaperType
    label_length: int
    maximum_label_width: int
    label_width: int

    def __str__(self):
        if not self.label_width and not self.label_length:
            label = "No readable label RFID tag"
        else:
            label = f"Label: {self.label_width} x {self.label_length} mm ({self.paper_type})"
        return f"{self.readiness}\n{label}"


def crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc.to_bytes(2, byteorder="big")


def available_ports():
    """Return available serial ports as (device, description) pairs."""
    return sorted(
        [(port.device, port.description or "No description") for port in list_ports.comports()],
        key=lambda item: item[0],
    )


def image_to_bytes(image):
    """Convert an already composed label image to the P21 bitmap format."""
    from PIL import ImageOps

    prepared = ImageOps.grayscale(image).resize((LABEL_WIDTH, LABEL_HEIGHT))
    prepared = prepared.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    data = prepared.tobytes()
    return data.ljust(3408, b"\xff")


def build_print_command(image_data, density=15, copies=1):
    if density not in range(1, 16):
        raise ValueError("Density must be between 1 and 15")
    if copies < 1:
        raise ValueError("Copies must be at least 1")
    return b"".join(
        [
            b"\x1b!o\r\n",
            b"SIZE 14.0 mm,40.0 mm\r\n",
            b"GAP 5.0 mm,0 mm\r\n",
            b"DIRECTION 1,1\r\n",
            f"DENSITY {density}\r\n".encode(),
            b"CLS\r\nBITMAP 0,0,12,284,1,",
            image_data,
            f"\r\nPRINT {copies}\r\n".encode(),
        ]
    )


class NelkoPrinter:
    """A short-lived serial connection to a Nelko P21."""

    def __init__(self, device, timeout=2):
        if not device:
            raise ValueError("A serial device is required")
        self.device = device
        self.timeout = timeout

    def _send(self, command, encode=True):
        payload = f"{command}\r\n".encode() if encode else command
        try:
            with serial.Serial(self.device, BAUD_RATE, timeout=self.timeout) as connection:
                connection.write(payload)
                response = connection.readline()
        except serial.SerialException as exc:
            raise ConnectionError(f"Could not communicate with {self.device}: {exc}") from exc
        if not response:
            raise TimeoutError(f"The printer on {self.device} did not respond")
        return response

    @staticmethod
    def _clean_response(response, prefix, expected_length):
        prefix_bytes = prefix.encode()
        cleaned = response[len(prefix_bytes) : -2]
        if not response.startswith(prefix_bytes) or len(cleaned) != expected_length:
            raise ValueError(f"Unexpected printer response: {response.hex()}")
        return cleaned

    def status(self):
        response = self._send("\x1b!o")
        if len(response) != 16:
            raise ValueError(f"Unexpected status response: {response.hex()}")
        if response[-2:] != crc16(response[:-2]):
            raise ValueError("Printer status checksum is invalid")
        data = struct.unpack(">16B", response)
        return PrinterStatus(
            Readiness(data[0]), data[4], PaperType(data[7]), data[11], data[12], data[13]
        )

    def config(self):
        data = self._clean_response(self._send("CONFIG?"), "CONFIG ", 10)
        values = struct.unpack(">hBBBBBBB?", data)
        return DeviceConfig(
            values[0],
            Version(f"{values[1]}.{values[2]}.{values[3]}"),
            Version(f"{values[4]}.{values[5]}.{values[6]}"),
            TimeoutSetting(values[7]),
            BeepSetting(values[8]),
        )

    def battery(self):
        data = self._clean_response(self._send("BATTERY?"), "BATTERY ", 2)
        level = ((data[0] >> 4) & 0x0F) * 10 + (data[0] & 0x0F)
        return level, bool(data[1])

    def set_timeout(self, minutes):
        values = {0: 0, 15: 1, 30: 2, 60: 3}
        if minutes not in values:
            raise ValueError("Timeout must be 0, 15, 30, or 60 minutes")
        self._send(f"TIMEOUT {chr(values[minutes])}")

    def set_beep(self, enabled):
        self._send(f"BEEP {chr(int(bool(enabled)))}")

    def self_test(self):
        self._send("SELFTEST")

    def print_image(self, image, density=15, copies=1):
        response = self._send(
            build_print_command(image_to_bytes(image), density, copies), encode=False
        )
        if len(response) != 16:
            raise ValueError(f"Unexpected print response: {response.hex()}")
        return response
