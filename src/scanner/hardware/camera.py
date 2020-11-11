from abc import ABC, abstractmethod
import io
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Type

import gphoto2 as gp
from PIL import Image

log = logging.getLogger(__name__)


class CameraException(Exception):
    def __init__(self, message):
        self.message = message


class Camera(ABC):
    def __init__(self, target_path: Path) -> None:
        pass

    @abstractmethod
    def connect(self):
        raise NotImplementedError

    @abstractmethod
    def take_photo(self, max_files_count: int = 1,
                   delete_after_download: bool = False,
                   callback: Callable[[Path], None] = None):
        raise NotImplementedError

    @abstractmethod
    def capture_preview(self) -> Image:
        raise NotImplementedError

    @abstractmethod
    def close(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def accepted_iso(self) -> List[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def accepted_shutter_speed(self) -> List[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def accepted_aperture(self) -> List[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def accepted_exposure_compensation(self) -> List[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def iso(self) -> str:
        raise NotImplementedError

    @iso.setter
    @abstractmethod
    def iso(self, val) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def shutter_speed(self) -> str:
        raise NotImplementedError

    @shutter_speed.setter
    @abstractmethod
    def shutter_speed(self, val) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def aperture(self) -> str:
        raise NotImplementedError

    @aperture.setter
    @abstractmethod
    def aperture(self, val) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def exposure_compensation(self) -> str:
        raise NotImplementedError

    @exposure_compensation.setter
    @abstractmethod
    def exposure_compensation(self, val) -> None:
        raise NotImplementedError


class GPhoto2Camera(Camera):
    __slots__ = ['_target_path', '_camera', '_new_file_detected',
                 '_must_stop', '_monitor_thread', '_camera_lock',
                 '_initial_iso', '_initial_shutter_speed',
                 '_initial_aperture', '_initial_exposure_compensation',
                 '_choices_iso', '_choices_shutter_speed',
                 '_choices_aperture', '_choices_exposure_compensation', ]

    TIMEOUT = 10.0

    CONFIG_ISO = "iso"
    CONFIG_APERTURE = "aperture"
    CONFIG_SHUTTER_SPEED = "shutterspeed"
    CONFIG_EXPOSURE_COMPENSATION = "exposurecompensation"

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

            with self._camera_lock:
                log.info("Init camera")
                self._camera = gp.Camera()
                self._camera.init()

            self._retrieve_config()
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

    def capture_preview(self) -> Image:
        with self._camera_lock:
            capture = self._camera.capture_preview()
            file_data = capture.get_data_and_size()
        return Image.open(io.BytesIO(file_data))

    def close(self) -> None:
        self._must_stop.set()
        if self._monitor_thread is not None:
            self._monitor_thread.join(self.TIMEOUT)
            self._monitor_thread = None

        if self._camera is not None:
            # Restore back the configuration of the camera
            try:
                self._restore_config()
            except:
                log.exception("Unable to restore the configuration")

            with self._camera_lock:
                self._camera.exit()
                self._camera = None

    @property
    def accepted_iso(self) -> List[str]:
        return self._choices_iso

    @property
    def accepted_shutter_speed(self) -> List[str]:
        return self._choices_shutter_speed

    @property
    def accepted_aperture(self) -> List[str]:
        return self._choices_aperture

    @property
    def accepted_exposure_compensation(self) -> List[str]:
        return self._choices_exposure_compensation

    @property
    def iso(self) -> str:
        widget, _ = self._retrieve_radio_config(self.CONFIG_ISO)
        return widget.get_value()

    @iso.setter
    def iso(self, val) -> None:
        self._set_config_value(self.CONFIG_ISO, val, self._initial_iso)

    @property
    def shutter_speed(self) -> str:
        widget, _ = self._retrieve_radio_config(self.CONFIG_SHUTTER_SPEED)
        return widget.get_value()

    @shutter_speed.setter
    def shutter_speed(self, val) -> None:
        self._set_config_value(self.CONFIG_SHUTTER_SPEED, val, self._initial_shutter_speed)

    @property
    def aperture(self) -> str:
        widget, _ = self._retrieve_radio_config(self.CONFIG_APERTURE)
        return widget.get_value()

    @aperture.setter
    def aperture(self, val) -> None:
        self._set_config_value(self.CONFIG_APERTURE, val, self._initial_aperture)

    @property
    def exposure_compensation(self) -> str:
        widget, _ = self._retrieve_radio_config(self.CONFIG_EXPOSURE_COMPENSATION)
        return widget.get_value()

    @exposure_compensation.setter
    def exposure_compensation(self, val) -> None:
        self._set_config_value(self.CONFIG_EXPOSURE_COMPENSATION, val, self._initial_exposure_compensation)

    def __enter__(self) -> "Camera":
        self.connect()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def _download_file(self, folder: str, name: str, delete_after_download: bool = False,
                       callback: Callable[[Path], None] = None):
        log.info('Camera file path: %s/%s', folder, name)
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

    def _retrieve_config(self) -> None:
        self._initial_iso, self._choices_iso = self._retrieve_radio_config(self.CONFIG_ISO)
        self._initial_aperture, self._choices_aperture = self._retrieve_radio_config(self.CONFIG_APERTURE)
        self._initial_shutter_speed, self._choices_shutter_speed = self._retrieve_radio_config(self.CONFIG_SHUTTER_SPEED)
        self._initial_exposure_compensation, self._choices_exposure_compensation = self._retrieve_radio_config(self.CONFIG_EXPOSURE_COMPENSATION)
        log.info("Initial settings: ISO %s, Aperture %s, Shutter speed %s, Exp. comp. %s",
                 self._initial_iso.get_value(),
                 self._initial_aperture.get_value(),
                 self._initial_shutter_speed.get_value(),
                 self._initial_exposure_compensation.get_value())

    def _retrieve_radio_config(self, name: str) -> Tuple[gp.CameraWidget, List[str]]:
        with self._camera_lock:
            config = self._camera.get_single_config(name)
            if config.get_type() != gp.GP_WIDGET_RADIO:
                raise CameraException(f"{name} is not a supported option")

            choices = list(config.get_choices())

        return config, choices

    def _set_config_value(self, name: str, value: str, default: gp.CameraWidget) -> None:
        if value:
            widget, _ = self._retrieve_radio_config(name)
            widget.set_value(value)
        else:
            widget = default

        try:
            with self._camera_lock:
                self._camera.set_single_config(name, widget)
        except:
            log.exception('Unable to set parameter "%s" to value "%s"', name, widget.get_value())

    def _restore_config(self) -> None:
        # Reset all settings
        self.aperture = ''
        self.iso = ''
        self.shutter_speed = ''
        self.exposure_compensation = ''


class FakeCamera(Camera):
    def __init__(self, target_path: Path) -> None:
        pass

    def connect(self):
        pass

    def take_photo(self, *args):
        log.info('[Dry-run] Capturing image')

    def capture_preview(self) -> Image:
        raise NotImplementedError

    def close(self):
        pass

    @property
    def accepted_iso(self) -> List[str]:
        return ['100']

    @property
    def accepted_shutter_speed(self) -> List[str]:
        return ['1/500']

    @property
    def accepted_aperture(self) -> List[str]:
        return ['8.0']

    @property
    def accepted_exposure_compensation(self) -> List[str]:
        return ['0']

    @property
    def iso(self) -> str:
        return '100'

    @iso.setter
    def iso(self, val) -> None:
        pass

    @property
    def shutter_speed(self) -> str:
        return '1/500'

    @shutter_speed.setter
    def shutter_speed(self, val) -> None:
        pass

    @property
    def aperture(self) -> str:
        return '8.0'

    @aperture.setter
    def aperture(self, val) -> None:
        pass

    @property
    def exposure_compensation(self) -> str:
        return '0'

    @exposure_compensation.setter
    def exposure_compensation(self, val) -> None:
        pass


def get_camera_type(dry_run: bool) -> Type[Camera]:
    if dry_run:
        return FakeCamera
    return GPhoto2Camera
