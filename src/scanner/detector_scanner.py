from datetime import datetime
import logging
import pathlib
import time
from typing import Generator, Optional, Tuple

import numpy as np

from scanner.object_detection import ObjectDetection

from .scanner_device import BacklightedScanner, PhotoInfo
from .hardware import stepper_motor, camera

log = logging.getLogger(__name__)

MODEL_PATH = "object_detection_model"
MODEL_FILE = "model.tflite"
MODEL_FILE_TPU = "model_edgetpu.tflite"
LABELS_FILE = "dict.txt"

LABEL_HOLE = "hole"
LABEL_PARTIAL_PHOTO = "partial_photo"
LABEL_SEPARATOR = "separator"
LABEL_PHOTO = "photo"

MIN_CONFIDENCE = 0.25
MIN_NUMBER_OF_HOLES = 4
MIN_COVERAGE = 0.4

MIN_X_MARGIN = 0.005
MIN_Y_MARGIN = 0.02

LEFT_SIDE = 0.10

DEBUG_PATH = pathlib.Path('/storage/share')

COUNTDOWN_TO_STOP = 3

# Stepper motor settings
SLEEP_TIME = 0.001
DIRECTION = -1
NORMAL_STEPS = 3
LARGE_STEPS = 90

def _get_model_path() -> pathlib.Path:
    base_dir = pathlib.Path(__file__).parent.absolute()
    model_path = base_dir / MODEL_PATH
    if not model_path.exists():
        raise FileNotFoundError(f"Model path does not exist: {model_path}")
    return model_path


def _get_model_files(use_edge_tpu: bool) -> Tuple[pathlib.Path, pathlib.Path]:
    model_path = _get_model_path()
    model_filename = MODEL_FILE_TPU if use_edge_tpu else MODEL_FILE

    model_file = model_path / model_filename
    labels_file = model_path / LABELS_FILE

    if not model_file.exists():
        raise FileNotFoundError(f"Model file does not exist: {model_file}")
    if not labels_file.exists():
        raise FileNotFoundError(f"Label file does not exist: {labels_file}")

    return model_file, labels_file


class DetectorScanner(BacklightedScanner):
    __slots__ = ['_camera', '_stepper_device', '_object_detector', '_debug_count', ]

    def __init__(self, camera: camera.Camera, backlight_pin: int, stepper_pin_1: int, stepper_pin_2: int, stepper_pin_3: int, stepper_pin_4: int, use_edge_tpu: bool=False) -> None:
        super().__init__(backlight_pin)
        
        self._debug_count = 0

        # Hardware devices
        self._camera = camera
        self._stepper_device = stepper_motor.StepperMotor(
            stepper_pin_1, stepper_pin_2, stepper_pin_3, stepper_pin_4)

        # Inference model
        model_file, labels_file = _get_model_files(use_edge_tpu)
        self._object_detector = ObjectDetection(
            str(model_file), str(labels_file),
            use_edge_tpu=use_edge_tpu)

    def scan_roll(self) -> int:
        # Start chronometer
        start_time = datetime.now()
        log.info("Ready to scan")
        self.must_stop.clear()
        count = 0

        with self.is_in_use:
            for photo_info in self._scroll_through_photos():
                count += 1
                time.sleep(0.5)     # Wait 1/2s in order to stabilize
                if self._on_next_photo:
                    self._on_next_photo(photo_info)

        self.stop_session()

        # Stop chronometer
        time_elapsed = datetime.now() - start_time
        log.info("Finished scanning, %s photos taken in: %s",
                 count, time_elapsed)
        if self._on_scan_finished:
            self._on_scan_finished(count)

        return count

    def stop_session(self) -> bool:
        stopped = super().stop_session()
        if stopped:
            self._stepper_device.stop()

        return stopped

    def _scroll_through_photos(self) -> Generator[PhotoInfo, None, None]:
        current_photo = 0
        number_of_steps = 0
        has_seen_holes = False
        countdown_to_stop = COUNTDOWN_TO_STOP

        while True:
            if self.must_stop.is_set():
                return

            steps_to_do = NORMAL_STEPS

            has_holes, has_photo, bounding_box = self._interpret()

            log.info("Loop 2 [%s]: %s, %s, %s", current_photo, has_holes, has_photo, bounding_box)

            # Holes indicate there's a film
            if has_seen_holes and not has_holes:
                # We'll try multiple times before deciding it's finished
                countdown_to_stop -= 1
                # Finished
                if countdown_to_stop <= 0:
                    log.info("No more holes")
                    return
            else:
                countdown_to_stop = COUNTDOWN_TO_STOP
                has_seen_holes = has_holes

            if has_photo:
                info = PhotoInfo(index=current_photo, crop=bounding_box)
                yield info
                current_photo += 1
                steps_to_do = LARGE_STEPS

            number_of_steps += steps_to_do
            self._stepper_device.rotate(SLEEP_TIME, DIRECTION * steps_to_do)

            # Logging several data
            log.info("%s: %s, %s", number_of_steps, has_holes, has_photo)

    def _interpret(self) -> Tuple[bool, bool, Optional[Tuple[float, float, float, float]]]:
        start_time = datetime.now()
        image = self._camera.capture_preview()
        capture_time = datetime.now()

        detections = self._object_detector.infer(image)

        # Debugging: store annotated preview
        if log.isEnabledFor(logging.DEBUG): 
            annotated_image = self._object_detector.draw_detections(image, detections, MIN_CONFIDENCE)
            annotated_file = DEBUG_PATH / f'{self._debug_count}-detections.jpg'
            dest_file = DEBUG_PATH / f'{self._debug_count}.jpg'
            annotated_image.save(annotated_file, "JPEG")
            image.save(dest_file, "JPEG")
            self._debug_count += 1

        num_holes = 0
        photo_coverage = 0.0
        best_bounding_box = None
        has_left_side_separator = False

        for d in detections:
            label = d[0]
            bounding_box = d[1]
            confidence = d[2]

            y1, x1, y2, x2 = np.float_(bounding_box).tolist()
            min_x = min(x1, x2)
            max_x = max(x1, x2)
            min_y = min(y1, y2)
            max_y = max(y1, y2)

            if confidence < MIN_CONFIDENCE:
                continue

            if label == LABEL_HOLE:
                num_holes += 1
            elif label == LABEL_PHOTO or label == LABEL_PARTIAL_PHOTO:
                # Check if there's a margin
                if min_x >= MIN_X_MARGIN and max_x <= 1.0 - MIN_X_MARGIN \
                   and min_y >= MIN_Y_MARGIN and max_y <= 1.0 - MIN_Y_MARGIN \
                   and min_x <= LEFT_SIDE:

                    current_photo_coverage = (x2 - x1) * (y2 - y1)
                    if current_photo_coverage > photo_coverage:
                        photo_coverage = current_photo_coverage
                        best_bounding_box = (x1, y1, x2, y2)
                        log.info("Found photo: %s", bounding_box)
                else:
                    log.info("Excluded due to margin: %s", bounding_box)
            elif label == LABEL_SEPARATOR:
                # Check if the separator is tall and on the left sid
                if max_x <= LEFT_SIDE and min_y <=0.20 and  max_y >= 0.80 and min_y >= 0.01 and max_y <= 0.99:
                    log.info("Found left-side separator: %s", bounding_box)

        has_holes = num_holes >= MIN_NUMBER_OF_HOLES

        # Determine if there is a well-frame photo
        # Option 1: photo detected by the model, aligned on the left
        has_photo = photo_coverage >= MIN_COVERAGE
        if not has_photo:
            # Option 2: there is a tall separator on the left, with many holes
            has_photo = num_holes >= 16 and has_left_side_separator

        log.info("Detection: %s, %s, %s, %s, %s", len(detections), num_holes, photo_coverage, has_left_side_separator, has_photo)
        log.info('Total inference time (hh:mm:ss.ms): %s / capture time: %s', datetime.now() - start_time, capture_time - start_time)

        return has_holes, has_photo, best_bounding_box
