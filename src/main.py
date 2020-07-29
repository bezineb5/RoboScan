import logging
import pathlib
import threading

from gpiozero import Button

from scanner import scanner, utils

log = logging.getLogger(__name__)


def main() -> None:
    args = utils.parse_arguments()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level)

    destination_path = pathlib.Path(args.destination)

    end_event = threading.Event()

    the_scanner = scanner.Scanner(args.led, args.backlight, args.pin1, args.pin2, args.pin3, args.pin4)
    the_scanner.on_session_stop = lambda: end_event.set()
    the_scanner.on_scan_finished = lambda count: utils.notify_ifttt(args.ifttt, "finished_scan", count)

    skip_button = Button(args.buttonskip)
    skip_button.when_pressed = lambda: the_scanner.skip_holes(1)
    start_button = Button(args.buttonstart)
    start_button.when_pressed = lambda: the_scanner.scan_roll()


    with utils.get_camera_type(args.dryrun)(destination_path) as camera_device:
        the_scanner.on_next_photo = lambda _: camera_device.take_photo()
        the_scanner.start_session()
        end_event.wait()


if __name__ == "__main__":
    main()
