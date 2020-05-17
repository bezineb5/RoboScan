from typing import Tuple

import adafruit_tsl2561
import busio


class LuxMeter:
    def __init__(self, i2c: busio.I2C, gain: int=0, integration_time: int=1):
        self._sensor = adafruit_tsl2561.TSL2561(i2c)
        self._sensor.gain = gain
        self._sensor.integration_time = integration_time

    def measure(self) -> Tuple[int, int]:
        return self._sensor.luminosity
