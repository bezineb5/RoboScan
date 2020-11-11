from dataclasses import dataclass
import logging
from logging import info
from pathlib import Path
import pathlib
import random
import threading
import shutil
from typing import Any, Callable, Dict, List, Optional

from dataclasses_json import dataclass_json

from scanner.frame_counter import FrameCounter
from scanner.metadata import MetaData
from scanner.scanner_device import CanSkipHoles, PhotoInfo
from . import scanner_device
from .hardware import camera

log = logging.getLogger(__name__)


@dataclass_json
@dataclass(frozen=True)
class SessionSettings:
    metadata: Optional[MetaData]
    initial_frame: Optional[FrameCounter]
    max_number_of_files: int = 1
    delete_photo_after_download: bool = False


class SessionDoesNotExist(Exception):
    def __init__(self, message):
        self.message = message


class Session:
    __slots__ = ['id', '_camera', '_scanner', '_callback', '_settings',
                 '_is_scanning', '_files_per_photo', '_current_frame',
                 '_exif_tagger', '_destination_storage', ]

    def __init__(self,
                 the_camera: camera.Camera,
                 the_scanner: scanner_device.Scanner,
                 destination_storage: pathlib.Path,
                 settings: SessionSettings,
                 callback: Callable[[str, Any], None],
                 exif_tagger: Callable[[Path, MetaData, Callable[[Path], None]], None]) -> None:

        self.id = random.randint(1, 99999)
        self._callback = callback
        self._camera = the_camera
        self._scanner = the_scanner
        self._exif_tagger = exif_tagger
        self._destination_storage = destination_storage
        self._settings = settings
        self._current_frame = settings.initial_frame
        self._is_scanning = False

        self._init_handlers()

        log.info("Initializing camera")
        self._camera.connect()
        log.info("Starting scanner session")
        self._scanner.start_session()
        log.info("Session initialized")
        log.info("Using Metadata: %s", self._settings.metadata)

    def _init_handlers(self):
        def on_stop():
            self._is_scanning = False
            self._callback("session", {
                "event": "stop",
                "id": self.id,
            })
            # self.stop()

        def on_photo(info: PhotoInfo):
            # Closure: capture the values for later use
            frame_count = self._current_frame
            destination_path = self._destination_storage

            def move_to_destination_callback(file: Path):
                if file:
                    shutil.move(str(file), str(destination_path / file.name))

            def download_callback(file: Path):
                metadata = self._settings.metadata
                if metadata is None:
                    return
                frame_metadata = metadata.with_frame_count(frame_count)
                if info.crop:
                    frame_metadata = frame_metadata.with_crop(info.crop)

                # Notify the exif tagger to write that info into the file
                self._exif_tagger(file, frame_metadata, move_to_destination_callback)

            self._camera.take_photo(
                max_files_count=self._settings.max_number_of_files,
                delete_after_download=self._settings.delete_photo_after_download,
                callback=download_callback)

            # Increase the frame counter
            if self._current_frame is not None:
                self._current_frame = self._current_frame.next()

            # Notify as soon as the photo is taken, don't wait to download files
            self._callback("session",
                           {
                               "event": "scanned_photo",
                               "id": self.id,
                               "data": info.index,
                           })

        def on_scan_finished(count: int):
            self._is_scanning = False
            self._callback("session",
                           {
                               "event": "scan_finished",
                               "id": self.id,
                               "data": count,
                           })
            self.stop()

        self._scanner.on_next_photo = on_photo
        self._scanner.on_scan_finished = on_scan_finished
        self._scanner.on_session_start = lambda: self._callback(
            "session", {"event": "start",
                        "id": self.id,
                        })
        self._scanner.on_session_stop = on_stop

    def start_scan_async(self):
        def scan():
            try:
                self._scanner.scan_roll()
            except:
                log.exception("Unable to scan roll")
                self._scanner.stop_session()

        threading.Thread(target=scan).start()
        self._is_scanning = True
        self._callback("session",
                       {
                           "event": "scan_started",
                           "id": self.id,
                       })

    def skip_holes_async(self, number_of_holes: int):
        if isinstance(self._scanner, CanSkipHoles):
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

    @property
    def support_hole_skipping(self) -> bool:
        return isinstance(self._scanner, scanner_device.CanSkipHoles)


def get_session(id: int) -> Session:
    session = SESSIONS.get(id)
    if session is None:
        raise SessionDoesNotExist(f"Session not found: {id}")
    return session


def get_or_new_session(the_camera: camera.Camera,
                       the_scanner: scanner_device.Scanner,
                       destination_storage: pathlib.Path,
                       settings: SessionSettings,
                       callback: Callable[[str, Any], None],
                       exif_tagger: Callable[[Path, MetaData, Callable[[Path], None]], None]) -> Session:

    # In reality, we only support one session
    if SESSIONS:
        key = next(iter(SESSIONS))
        return SESSIONS[key]

    # No existing session, create a new one
    new_session = Session(the_camera, the_scanner, destination_storage,
                          settings, callback, exif_tagger)
    SESSIONS[new_session.id] = new_session
    return new_session


def list_session_ids() -> List[int]:
    return list(SESSIONS.keys())


SESSIONS: Dict[int, Session] = {}
