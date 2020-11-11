import collections
import logging
import time
from datetime import datetime
from typing import List, Tuple

import board
import busio

from .scanner_device import BacklightedScanner, CanSkipHoles, PhotoInfo
from .hardware import stepper_motor, lux_meter, led

log = logging.getLogger(__name__)

HOLES_PER_PHOTO = 8
MINIMUM_AMPLITUDE = 20
BUFFER_LEN = 100
SLEEP_TIME = 0.01
DIRECTION = -1


class HoleCounterScanner(BacklightedScanner, CanSkipHoles):
    def __init__(self, led_pin: int, led_use_infrared: bool, backlight_pin: int, stepper_pin_1: int, stepper_pin_2: int, stepper_pin_3: int, stepper_pin_4: int) -> None:
        super().__init__(backlight_pin)

        # Hardware devices
        self.led_device = led.Led(led_pin, initial_value=False)
        self.stepper_device = stepper_motor.StepperMotor(
            stepper_pin_1, stepper_pin_2, stepper_pin_3, stepper_pin_4)

        i2c = busio.I2C(board.SCL, board.SDA)
        self.lux_meter_device = lux_meter.LuxMeter(i2c)
        self.recent_lux: collections.deque = collections.deque(
            maxlen=BUFFER_LEN)
        self.led_use_infrared = led_use_infrared

    def _scroll_through_holes(self):
        number_of_steps = 0
        current_hole = 0
        had_a_minimum = False

        with self.led_device:
            while True:
                if self.must_stop.is_set():
                    return

                number_of_steps += 1
                self.stepper_device.rotate(SLEEP_TIME, DIRECTION * 1)
                visible_lux, ir_lux = self.lux_meter_device.measure()
                measured = ir_lux if self.led_use_infrared else visible_lux
                self.recent_lux.appendleft(measured)
                is_finished, is_new_hole, is_minimum = self._interpret_lux(
                    list(self.recent_lux), had_a_minimum)

                if is_finished:
                    log.info("No more holes")
                    self.recent_lux.clear()
                    return

                if is_minimum:
                    had_a_minimum = True

                # Logging several data
                log.info("%s: %s, %s", number_of_steps, visible_lux, ir_lux)

                if is_new_hole:
                    had_a_minimum = False
                    current_hole += 1
                    yield current_hole

    def _interpret_lux(self, measures: List[int], had_a_minimum: bool) -> Tuple[bool, bool, bool]:

        min_lux = min(measures)
        max_lux = max(measures)

        if len(measures) == BUFFER_LEN and 2*(max_lux - min_lux) < MINIMUM_AMPLITUDE:
            # Finished the roll
            return True, False, False

        if 2*len(measures) < BUFFER_LEN:
            return False, False, False

        d0 = measures[0] - measures[1]
        d1 = measures[1] - measures[2]
        d2 = measures[2] - measures[3]

        if had_a_minimum and d0 < 0 and d1 >= 0 and d2 >= 0 and measures[0] > (min_lux + MINIMUM_AMPLITUDE) and measures[0] > (max_lux - 2*MINIMUM_AMPLITUDE):
            # Local maximum reached
            return False, True, False

        if d0 > 0 and d1 <= 0 and d2 <= 0 and measures[0] < (max_lux - MINIMUM_AMPLITUDE):
            # Local maximum reached
            return False, False, True

        return False, False, False

    def start_session(self) -> bool:
        started = super().start_session()
        if started:
            self.recent_lux.clear()

        return started

    def stop_session(self) -> bool:
        stopped = super().stop_session()
        if stopped:
            self.stepper_device.stop()
            self.led_device.off()

        return stopped

    def skip_holes(self, number_of_holes: int) -> None:
        if number_of_holes <= 0:
            return

        with self.is_in_use:
            for _ in self._scroll_through_holes():
                number_of_holes -= 1
                log.info("Skipping hole, remaining: %s", number_of_holes)
                if number_of_holes <= 0:
                    return

    def scan_roll(self) -> int:
        # Start chronometer
        start_time = datetime.now()
        log.info("Ready to scan")
        self.must_stop.clear()
        count = 0

        def capture(photo_index):
            nonlocal count
            count += 1
            self.led_device.off()
            time.sleep(0.5)     # Wait 1/2s in order to stabilize
            if self._on_next_photo:
                info = PhotoInfo(index=photo_index)
                self._on_next_photo(info)
            self.led_device.on()
            time.sleep(0.25)     # Wait for light sensor to be stable

        with self.is_in_use:
            # Start with a photo
            capture(0)

            for photo_index in self._scroll_through_photos():
                capture(photo_index+1)

        self.stop_session()

        # Stop chronometer
        time_elapsed = datetime.now() - start_time
        log.info("Finished scanning, %s photos taken in: %s",
                 count, time_elapsed)
        if self._on_scan_finished:
            self._on_scan_finished(count)

        return count

    def _scroll_through_photos(self):
        current_photo = 0
        for i in self._scroll_through_holes():
            log.info("Holes remaing: %s", i % HOLES_PER_PHOTO)
            if i % HOLES_PER_PHOTO == 0:
                yield current_photo
                current_photo += 1
