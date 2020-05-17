import argparse
import collections
import csv
import json
import logging
import pathlib
import threading
import time
from datetime import datetime
from typing import Any, List, Tuple, Optional

import board
import busio
import requests
from gpiozero import Button

from hardware import stepper_motor, lux_meter, led, camera

log = logging.getLogger(__name__)

SLEEP_TIME = 0.01
HOLES_PER_PHOTO = 8
DIRECTION = -1
MINIMUM_AMPLITUDE = 20
BUFFER_LEN = 100
STEP_PER_TURN = 64 * 8 # ???

ifttt_key: Optional[str] = None
is_started = threading.Event()


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Film automatic scanner')

    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose mode')
    parser.add_argument('--dryrun', action='store_true',
                        help='Dry run without camera camera')
    #parser.add_argument('--port', default='5000', type=int, help='Server port to listen to')
    #parser.add_argument('--steps', '-s', default='128', type=int, help='Number of steps per rotation')
    parser.add_argument('--pin1', '-p1', default='5', type=int, help='BCM pin for IN1')
    parser.add_argument('--pin2', '-p2', default='6', type=int, help='BCM pin for IN2')
    parser.add_argument('--pin3', '-p3', default='13', type=int, help='BCM pin for IN3')
    parser.add_argument('--pin4', '-p4', default='19', type=int, help='BCM pin for IN4')
    parser.add_argument('--led', '-l', default='4', type=int, help='BCM pin for the LED')
    parser.add_argument('--buttonstart', '-s', default='20', type=int, help='BCM pin for the start button')
    parser.add_argument('--buttonskip', '-k', default='21', type=int, help='BCM pin for the skip button')

    parser.add_argument('--destination', '-d', default='.', type=str, help='Destination path')
    parser.add_argument('--ifttt', type=str, help='IFTTT key to call webhooks')

    return parser.parse_args()


def _notify(action: str, value1: Any=None, value2: Any=None, value3: Any=None) -> None:
    if not ifttt_key:
        return

    url = "https://maker.ifttt.com/trigger/{action}/with/key/{key}".format(action=action, key=ifttt_key)
    payload = {
        "value1" : value1,
        "value2" : value2,
        "value3" : value3,
    }

    r = requests.post(url, data=json.dumps(payload))
    r.raise_for_status()


def _scan_roll(stepper_device: stepper_motor.StepperMotor, lux_meter_device: lux_meter.LuxMeter, led_device: led.Led, skip_button: Button, camera_device: camera.Camera) -> int:
    count = 0
    for photo_index in _scroll_to_next(stepper_device, lux_meter_device, led_device, skip_button):
        time.sleep(0.5)     # Wait 1/2s in order to stabilize
        camera_device.take_photo()
        count += 1
    
    return count


def _scroll_to_next(stepper_device: stepper_motor.StepperMotor, lux_meter_device: lux_meter.LuxMeter, led_device: led.Led, skip_button: Button):
    number_of_steps = 0
    current_photo = 0
    recent_lux: collections.deque = collections.deque(maxlen=BUFFER_LEN)
    had_a_minimum = False

    with open('lux.csv', 'w', newline='') as csvfile:
        lux_writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
        
        while True:
            capturing = False

            with led_device:
                is_started.wait(0.1)
                if is_started.is_set():
                    # First photo: start immediately, otherwise, move by 8 holes
                    holes_to_go = 0 if current_photo == 0 else HOLES_PER_PHOTO
                    capturing = True
                elif skip_button.is_pressed:
                    holes_to_go = 1
                else:
                    holes_to_go = 0

                # Slight delay to give time to the lux meter to adjust
                time.sleep(0.1)

                while holes_to_go > 0:
                    number_of_steps += 1
                    stepper_device.rotate(SLEEP_TIME, DIRECTION * 1)
                    visible_lux, ir_lux = lux_meter_device.measure()
                    recent_lux.appendleft(visible_lux)
                    is_finished, is_new_hole, is_minimum = _interpret_lux(list(recent_lux), had_a_minimum)

                    if capturing and is_finished:
                        log.info("Finished")
                        # Position the motor at the same angle as it was initially
                        #steps_to_go = STEP_PER_TURN - (number_of_steps % STEP_PER_TURN)
                        #stepper_device.rotate(SLEEP_TIME, DIRECTION * steps_to_go)
                        return
                    
                    if is_minimum:
                        had_a_minimum = True

                    if is_new_hole:
                        holes_to_go -= 1
                        had_a_minimum = False
                        log.info("Found hole, remaining: %s", holes_to_go)

                    log.info("%s: %s, %s", number_of_steps, visible_lux, ir_lux)
                    should_capture = (holes_to_go == 0)
                    lux_writer.writerow([number_of_steps, visible_lux, ir_lux, should_capture])

            if capturing:
                yield current_photo
                current_photo += 1


def _interpret_lux(measures: List[int], had_a_minimum: bool) -> Tuple[bool, bool, bool]:

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


def start_scan() -> None:
    is_started.set()


def get_camera_type(dry_run: bool):
    if dry_run:
        return camera.FakeCamera
    return camera.Camera


def main() -> None:
    args = _parse_arguments()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level)

    global ifttt_key
    ifttt_key = args.ifttt
    destination_path = pathlib.Path(args.destination)

    i2c = busio.I2C(board.SCL, board.SDA)

    lux_meter_device = lux_meter.LuxMeter(i2c)
    led_device = led.Led(args.led)
    skip_button = Button(args.buttonskip)
    start_button = Button(args.buttonstart)
    start_button.when_pressed = start_scan

    with stepper_motor.StepperMotor(args.pin1, args.pin2, args.pin3, args.pin4) as stepper_device:
        with get_camera_type(args.dryrun)(destination_path) as camera_device:
            start_time = datetime.now()
            log.info("Ready to scan")

            count = _scan_roll(stepper_device, lux_meter_device, led_device, skip_button, camera_device)

            time_elapsed = datetime.now() - start_time 
            log.info("Finished scanning, %s photos taken in: %s", count, time_elapsed)

    _notify("finished_scan", count)


if __name__ == "__main__":
    main()
