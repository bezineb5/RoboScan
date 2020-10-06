import dataclasses
import logging
import os
from pathlib import Path
import queue
import threading
from typing import Callable, List

import exiftool

from . import exif, metadata

log = logging.getLogger(__name__)

_ANALOG_EXIF_CONFIG = str(exif.get_analogexif_config())

TAG_MAPPING = {
    "exposure_number": "ExposureNumber",
    "lens_serial_number": "LensSerialNumber",
    "roll_id": "RollId",
    "film_maker": "FilmMaker",
    "film": "Film",
    "film_alias": "FilmAlias",
    "film_grain": "FilmGrain",
    "film_type": "FilmType",
    "developer": "Developer",
    "develop_process": "DevelopProcess",
    "developer_maker": "DeveloperMaker",
    "developer_dilution": "DeveloperDilution",
    "develop_time": "DevelopTime",
    "lab": "Lab",
    "lab_address": "LabAddress",
    "filter": "Filter",
}


def async_tagger() -> Callable[[Path, metadata.MetaData, Callable[[Path], None]], None]:
    sync_queue: queue.SimpleQueue = queue.SimpleQueue()

    threading.Thread(target=_tagger_thread, args=(sync_queue, ), daemon=True).start()

    def tag_file(filename: Path, mdata: metadata.MetaData, post_action: Callable[[Path], None]):
        sync_queue.put((filename, mdata, post_action))

    return tag_file


def _tagger_thread_test(sync_queue: queue.SimpleQueue):

    while True:
        filename, metadata, post_action = sync_queue.get()
        log.info("Tagging file %s using Metadata: %s", filename, metadata)
        params = _build_command_line(filename, metadata)

        full_cmd_line = " ".join(['exiftool'] + params)
        log.info("ExifTool command line: %s", full_cmd_line)

        result = os.system(full_cmd_line)

        log.info("ExifTool result: %s", result)

        if post_action is not None:
            post_action(filename)


def _tagger_thread(sync_queue: queue.SimpleQueue):
    log.info("Starting ExifTool")

    with exiftool.ExifTool() as et:
        while True:
            filename, metadata, post_action = sync_queue.get()
            params = _build_command_line(filename, metadata)

            # Do the tagging! It seems that execute_json fails in that case.
            encoded_params = map(os.fsencode, params)
            result = et.execute(*encoded_params)
            log.info("ExifTool result: %s", result.decode("utf-8"))

            if post_action is not None:
                post_action(filename)


def _build_command_line(filename: Path, mdata: metadata.MetaData) -> List[str]:
    params = []
    # exiftool -config ./analogexif.config -FilmMaker="Kodak"  -FilmType="APS" -Film="Kodak Advantix 200" -overwrite_original  *.RW2
    
    # Configuration file for the custom AnalogExif tags is not necessary - it's easier to configure the Dockerfile for that

    # Append all defined metadata
    data_dict = dataclasses.asdict(mdata)
    for key, v in data_dict.items():
        tag = TAG_MAPPING.get(key)
        content = str(v) if v is not None else None
        if content and v != "" and tag:
            params.append('-{tag}="{content}"'.format(tag=tag, content=content))

    params.append("-overwrite_original")
    params.append(str(filename))

    log.info("ExifTool parameters: %s", params)

    return params
