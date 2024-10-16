from __future__ import annotations

import asyncio
import dataclasses
import logging
import struct
from collections.abc import Callable
from enum import IntEnum

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak_retry_connector import establish_connection

from .bluetooth import create_adv_receiver
from .const import (
    ALIRO_CHARACTERISTIC_UUID,
    DISPLAY_UNIT_KEY,
    HW_REVISION_STRING_CHARACTERISTIC_UUID,
    IMPEDANCE_KEY,
    SW_REVISION_STRING_CHARACTERISTIC_UUID,
    UNIT_UPDATE_COMMAND,
    WEIGHT_CHARACTERISTIC_UUID_NOTIFY,
    WEIGHT_KEY,
)

_LOGGER = logging.getLogger(__name__)


class WeightUnit(IntEnum):
    """Weight units."""

    KG = 0  # Kilograms
    LB = 1  # Pounds
    ST = 2  # Stones


@dataclasses.dataclass
class ScaleData:
    """Response data with information about the scale."""

    name: str = ""
    address: str = ""
    hw_version: str = ""
    sw_version: str = ""
    display_unit: WeightUnit = WeightUnit.KG
    measurements: dict[str, str | float | None] = dataclasses.field(
        default_factory=dict
    )


def parse(payload: bytearray) -> dict[str, int | float | None]:
    print(f"Payload: \n {payload}")
    if (
       payload is not None
        and len(payload) == 12
        and payload[4] == 0x02
    ):
        data = dict[str, int | float | None]()
        # Extract weight from bytes 8-9 in big-endian format
        weight = struct.unpack(">H", payload[8:10])[0]

        # Assuming weight is in 100g units
        data[WEIGHT_KEY] = round(float(weight) / 100, 2)

        # weight = struct.unpack("<I", payload[10:13].ljust(4, b"\x00"))[0]
        # impedance = struct.unpack("<H", payload[13:15])[0]
        # data[DISPLAY_UNIT_KEY] = int(payload[21])
        # data[WEIGHT_KEY] = round(float(weight) / 1000, 2)
        # if payload[20] == 1:
        #     if impedance := struct.unpack("<H", payload[13:15])[0]:
        #         data[IMPEDANCE_KEY] = int(impedance)
        return data
    return None


class VitafitBodyFatScale:
    _client: BleakClient = None
    _hw_version: str = None
    _sw_version: str = None
    _display_unit: WeightUnit = None
    _unit_update_flag: bool = False

    def __init__(
        self,
        address: str,
        notification_callback: Callable[[ScaleData], None],
        display_unit: WeightUnit = None,
    ) -> None:
        self.address = address
        self._notification_callback = notification_callback
        self._scanner = create_adv_receiver(self._advertisement_callback)
        self._connect_lock = asyncio.Lock()
        self._unit_update_buff = bytearray.fromhex(UNIT_UPDATE_COMMAND)
        if display_unit != None:
            self.display_unit = display_unit

    @property
    def hw_version(self) -> str:
        return self._hw_version

    @property
    def sw_version(self) -> str:
        return self._sw_version

    @property
    def display_unit(self):
        return self._display_unit

    @display_unit.setter
    def display_unit(self, value):
        if value != None:
            self._display_unit = value
            self._unit_update_flag = True

    async def async_start(self) -> None:
        """Start the callbacks."""
        _LOGGER.debug(
            "Starting VitafitBodyFatScale for address: %s", self.address
        )
        await self._scanner.start()

    async def async_stop(self) -> None:
        """Stop the callbacks."""
        _LOGGER.debug(
            "Stopping VitafitBodyFatScale for address: %s", self.address
        )
        await self._scanner.stop()

    def _notification_handler(
        self, _: BleakGATTCharacteristic, payload: bytearray, name: str, address: str
    ) -> None:
        if data := parse(payload):
            _LOGGER.debug(
                "Received stable weight notification from %s (%s): %s",
                name,
                address,
                data,
            )
            device = ScaleData()
            device.name = name
            device.address = address
            device.hw_version = self.hw_version
            device.sw_version = self.sw_version
            _LOGGER.debug("%s (%s): %s", name, address, data)
            device.display_unit = WeightUnit(data.pop(DISPLAY_UNIT_KEY))

            if self._display_unit == None:
                self._display_unit = device.display_unit
                self._unit_update_flag = False
            else:
                self._unit_update_flag = device.display_unit != self._display_unit

            device.measurements = data
            self._notification_callback(device)

    def _unavailable_callback(self, _: BleakClient) -> None:
        self._client = None
        self._scanner.set_adv_callback(self._advertisement_callback)
        _LOGGER.debug("Scale disconnected")

    async def _advertisement_callback(
        self, ble_device: BLEDevice, _: AdvertisementData
    ) -> None:
        """Connects to the device through BLE and retrieves relevant data."""
        if ble_device.address != self.address or self._client:
            return
        try:
            async with self._connect_lock:
                if self._client:
                    return
                self._scanner.unset_adv_callback()
                self._client = await establish_connection(
                    BleakClient,
                    ble_device,
                    self.address,
                    self._unavailable_callback,
                )
                _LOGGER.debug("Connected to scale: %s", self.address)
            if self._unit_update_flag:
                if self._display_unit != None:
                    self._unit_update_buff[5] = 43 - self._display_unit
                    self._unit_update_buff[10] = self._display_unit
                    await self._client.write_gatt_char(
                        ALIRO_CHARACTERISTIC_UUID, self._unit_update_buff, False
                    )
                    _LOGGER.debug(
                        "Trying to update display unit to %s (buffer: %s)",
                        self._display_unit,
                        self._unit_update_buff.hex(),
                    )
            await self._client.start_notify(
                WEIGHT_CHARACTERISTIC_UUID_NOTIFY,
                lambda char, data: self._notification_handler(
                    char, data, ble_device.name, ble_device.address
                ),
            )
            if not self._hw_version:
                self._hw_version = (
                    await self._client.read_gatt_char(
                        HW_REVISION_STRING_CHARACTERISTIC_UUID
                    )
                ).decode()
            self._sw_version = (
                await self._client.read_gatt_char(
                    SW_REVISION_STRING_CHARACTERISTIC_UUID
                )
            ).decode()
            _LOGGER.debug("Scale HW version: %s", self._hw_version)
            _LOGGER.debug("Scale SW version: %s", self._sw_version)
        except Exception as ex:
            self._client = None
            self._unit_update_flag = True
            self._scanner.set_adv_callback(self._advertisement_callback)
            _LOGGER.exception("%s(%s)", type(ex), ex.args)
