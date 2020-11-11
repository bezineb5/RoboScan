import logging
import pathlib
import threading
from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json

from scanner.session import SessionSettings

log = logging.getLogger(__name__)

_saver_lock = threading.Lock()


@dataclass_json
@dataclass
class CameraSettings:
    iso: Optional[str] = None
    shutter_speed: Optional[str] = None
    aperture: Optional[str] = None
    exposure_compensation: Optional[str] = None


@dataclass_json
@dataclass
class ApplicationSettings:
    last_camera_settings: CameraSettings = CameraSettings()
    last_session_settings: Optional[SessionSettings] = None


_settings_file: pathlib.Path
_current_settings = ApplicationSettings()


def init_settings(settings_filename: str):
    with _saver_lock:
        global _settings_file, _current_settings

        _settings_file = pathlib.Path(settings_filename)
        try:
            with open(_settings_file, 'r') as f:
                raw_json = f.read()

            _current_settings = ApplicationSettings.from_json(raw_json)
            if _current_settings is None:
                _current_settings = ApplicationSettings()
        except FileNotFoundError:
            log.info("Settings file not found")
        except:
            log.exception("Unable to read settings file")


def get_settings():
    return _current_settings


class SettingsSaver:
    __slots__ = ['_settings', ]
        
    def __enter__(self) -> ApplicationSettings:
        # It's not possible to use multiple savers at the same time
        _saver_lock.acquire()

        # Deep copy of the settings
        if _current_settings is not None:
            self._settings = ApplicationSettings.from_json(_current_settings.to_json())
        else:
            self._settings = ApplicationSettings()

        return self._settings
    
    def __exit__(self, type, value, traceback):
        try:
            # Pretty-print the saved file
            raw_json = self._settings.to_json(indent=4)
            with open(_settings_file, 'w') as f:
                f.write(raw_json)

            # Store locally
            global _current_settings
            _current_settings = self._settings
        finally:
            _saver_lock.release()
