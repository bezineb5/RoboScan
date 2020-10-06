import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import gphoto2 as gp

log = logging.getLogger(__name__)


class CameraException(Exception):
    def __init__(self, message):
        self.message = message


class Camera():
    __slots__ = ['_target_path', '_camera', '_new_file_detected',
                 '_must_stop', '_monitor_thread', '_camera_lock']

    TIMEOUT = 10.0

    def __init__(self, target_path: Path) -> None:
        self._target_path = target_path
        self._camera: gp.Camera = None

        self._new_file_detected = threading.Event()
        self._must_stop = threading.Event()
        self._camera_lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None

        gp.use_python_logging()

    def connect(self):
        try:
            # Close previously opened camera
            self.close()

            self._must_stop.clear()

            log.info("Init camera")
            self._camera = gp.Camera()
            self._camera.init()
        except Exception:
            log.exception("Unable to connect to camera")
            raise CameraException("Unable to connect to camera")

    def take_photo(self, max_files_count: int = 1,
                   delete_after_download: bool = False,
                   callback: Callable[[Path], None] = None):
        if self._camera is None:
            raise Exception("Camera not connected")

        start_time = datetime.now()
        self._new_file_detected.clear()

        with self._camera_lock:
            log.info('Capturing image')
            try:
                file_path = self._camera.capture(gp.GP_CAPTURE_IMAGE)
                if max_files_count >= 1:
                    self._download_file(
                        file_path.folder, file_path.name,
                        delete_after_download=delete_after_download,
                        callback=callback)
            except:
                log.exception("Unable to capture photo")
                return

        # Wait for more files
        if max_files_count > 1:
            # One file has already been downloaded
            monitor_args = (max_files_count-1, delete_after_download, callback)
            self._monitor_thread = threading.Thread(target=self._monitor_files,
                                                    args=monitor_args)
            self._monitor_thread.start()

        time_elapsed = datetime.now() - start_time
        log.info('Elapsed capture time (hh:mm:ss.ms): %s', time_elapsed)

    def _download_file(self, folder: str, name: str, delete_after_download: bool = False,
                       callback: Callable[[Path], None] = None):
        log.info('Camera file path: {0}/{1}'.format(folder, name))
        target_file = self._target_path / name

        log.info('Copying image to: %s', target_file)
        camera_file = self._camera.file_get(
            folder, name, gp.GP_FILE_TYPE_NORMAL)
        camera_file.save(str(target_file))

        if delete_after_download:
            log.info('Deleting file on camera: %s/%s', folder, name)
            self._camera.file_delete(folder, name)

        if callback is not None:
            callback(target_file)

    def close(self) -> None:
        self._must_stop.set()
        if self._monitor_thread is not None:
            self._monitor_thread.join(self.TIMEOUT)
            self._monitor_thread = None

        if self._camera is not None:
            self._camera.exit()
            self._camera = None

    def __enter__(self) -> "Camera":
        self.connect()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def _monitor_files(self, files_to_download: int,
                       delete_after_download: bool = False,
                       callback: Callable[[Path], None] = None):
        log.info("Starting camera monitoring")

        self._new_file_detected.clear()
        timeout = 0  # miliseconds
        should_continue = files_to_download > 0

        while should_continue and not self._must_stop.is_set():
            try:
                with self._camera_lock:
                    should_continue = False
                    log.info("Waiting for camera event")

                    event_type, event_data = self._camera.wait_for_event(
                        timeout)
                    if event_type == gp.GP_EVENT_FILE_ADDED:
                        self._download_file(
                            event_data.folder, event_data.name,
                            delete_after_download=delete_after_download,
                            callback=callback)
                        files_to_download -= 1
                        should_continue = files_to_download > 0
                    elif event_type == gp.GP_EVENT_FOLDER_ADDED:
                        should_continue = True

            except KeyboardInterrupt:
                return


class FakeCamera(Camera):
    def __init__(self, target_path: Path) -> None:
        pass

    def connect(self):
        pass

    def take_photo(self, *args):
        log.info('[Dry-run] Capturing image')

    def close(self):
        pass
