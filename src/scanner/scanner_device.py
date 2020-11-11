import abc
from dataclasses import dataclass
import threading
from typing import Callable, Optional, Tuple

from .hardware import led


@dataclass
class PhotoInfo:
    index: int
    crop: Optional[Tuple[float, float, float, float]] = None # (x1, y1, x2, y2)


class Scanner(abc.ABC):
    def __init__(self) -> None:
        # Threading locks
        self.is_in_use = threading.Lock()
        self.session_started = threading.Event()
        self.must_stop = threading.Event()

        # Callbacks
        self._on_session_start: Optional[Callable] = None
        self._on_session_stop: Optional[Callable] = None
        self._on_next_photo: Optional[Callable] = None
        self._on_scan_finished: Optional[Callable] = None

    def start_session(self) -> bool:
        if self.session_started.is_set():
            return False

        self.session_started.set()
        self.must_stop.clear()

        if self._on_session_start:
            self._on_session_start()

        return True

    def stop_session(self) -> bool:
        if self.session_started.is_set():
            self.must_stop.set()
            if self._on_session_stop:
                self._on_session_stop()
            self.session_started.clear()
            return True
        return False

    @abc.abstractmethod
    def scan_roll(self) -> int:
        raise NotImplementedError

    @property
    def on_session_start(self) -> Optional[Callable[[], None]]:
        return self._on_session_start

    @on_session_start.setter
    def on_session_start(self, callback: Optional[Callable[[], None]]) -> None:
        self._on_session_start = callback

    @property
    def on_session_stop(self) -> Optional[Callable[[], None]]:
        return self._on_session_stop

    @on_session_stop.setter
    def on_session_stop(self, callback: Optional[Callable[[], None]]) -> None:
        self._on_session_stop = callback

    @property
    def on_next_photo(self) -> Optional[Callable[[PhotoInfo], None]]:
        return self._on_next_photo

    @on_next_photo.setter
    def on_next_photo(self, callback: Optional[Callable[[PhotoInfo], None]]) -> None:
        self._on_next_photo = callback

    @property
    def on_scan_finished(self) -> Optional[Callable[[int], None]]:
        return self._on_scan_finished

    @on_scan_finished.setter
    def on_scan_finished(self, callback: Optional[Callable[[int], None]]) -> None:
        self._on_scan_finished = callback

    @property
    def is_session_started(self) -> bool:
        return self.session_started.is_set()


class BacklightedScanner(Scanner):
    def __init__(self, backlight_pin: int) -> None:
        super().__init__()
        self.backlight_device = led.Led(
            backlight_pin, active_high=False, initial_value=False)

    def start_session(self) -> bool:
        started = super().start_session()
        if started:
            self.backlight_device.on()

        return started

    def stop_session(self) -> bool:
        stopped = super().stop_session()
        if stopped:
            self.backlight_device.off()

        return stopped


class CanSkipHoles(abc.ABC):
    @abc.abstractmethod
    def skip_holes(self, number_of_holes: int) -> None:
        raise NotImplementedError
