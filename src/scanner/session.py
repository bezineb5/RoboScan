import logging
import random
import threading
from typing import Any, Callable, List, Dict

from . import scanner
from .hardware import camera

log = logging.getLogger(__name__)


class Session:
    __slots__ = ['id', '_camera', '_scanner', '_callback', '_settings', '_is_scanning', '_files_per_photo', ]

    def __init__(self, the_camera: camera.Camera, the_scanner: scanner.Scanner, settings: Dict[str, Any], callback: Callable[[str, Any], None]) -> None:
        self.id = random.randint(1, 99999)
        self._callback = callback
        self._camera = the_camera
        self._scanner = the_scanner
        self._settings = settings
        self._is_scanning = False

        self._init_handlers()

        log.info("Initializing camera")
        self._camera.connect()
        log.info("Starting scanner session")
        self._scanner.start_session()
        log.info("Session initialized")

    def _init_handlers(self):
        def on_stop():
            self._is_scanning = False
            self._callback("session", {
                "event": "stop",
                "id": self.id,
            })
            #self.stop()

        def on_photo(index: int):
            self._camera.take_photo()
            self._callback("session",
                           {
                               "event": "scanned_photo",
                               "id": self.id,
                               "data": index,
                           })

        def on_scan_finished(count: int):
            self._is_scanning = False
            self._callback("session",
                           {
                               "event": "scan_finished",
                               "id": self.id,
                               "data": count,
                           })

        self._scanner.on_next_photo = on_photo
        self._scanner.on_scan_finished = on_scan_finished
        self._scanner.on_session_start = lambda: self._callback(
            "session", {"event": "start",
                        "id": self.id,
                        })
        self._scanner.on_session_stop = on_stop

    def start_scan_async(self):
        threading.Thread(target=lambda: self._scanner.scan_roll()).start()
        self._is_scanning = True
        self._callback("session",
                {
                    "event": "scan_started",
                    "id": self.id,
                })

    def skip_holes_async(self, number_of_holes: int):
        threading.Thread(target=lambda n: self._scanner.skip_holes(
            n), args=(number_of_holes,)).start()

    def stop(self):
        if self.id in SESSIONS:
            del SESSIONS[self.id]

        self._camera.close()
        self._scanner.stop_session()

    @property
    def is_scanning(self) -> bool:
        return self._is_scanning


def get_session(id: int) -> Session:
    return SESSIONS[id]


def get_or_new_session(the_camera: camera.Camera, the_scanner: scanner.Scanner, settings: Dict[str, Any], callback: Callable[[str, Any], None]) -> Session:
    # In reality, we only support one session
    if SESSIONS:
        key = next(iter(SESSIONS))
        return SESSIONS[key]

    # No existing session, create a new one
    new_session = Session(the_camera, the_scanner, settings, callback)
    SESSIONS[new_session.id] = new_session
    return new_session


def list_session_ids() -> List[int]:
    return list(SESSIONS.keys())


SESSIONS: Dict[int, Session] = {}
