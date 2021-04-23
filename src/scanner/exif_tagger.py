import collections
import dataclasses
import logging
import os
from pathlib import Path
import queue
import threading
from typing import Callable, List

import exiftool

from . import metadata, exif

log = logging.getLogger(__name__)

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
    "crop": "DefaultUserCrop",
}


def async_tagger() -> Callable[[Path, metadata.MetaData, Callable[[Path], None]], None]:
    sync_queue: queue.SimpleQueue = queue.SimpleQueue()

    threading.Thread(target=_tagger_thread, args=(sync_queue, ), daemon=True).start()

    def tag_file(filename: Path, mdata: metadata.MetaData, post_action: Callable[[Path], None]):
        sync_queue.put((filename, mdata, post_action))

    return tag_file


def _tagger_thread(sync_queue: queue.SimpleQueue):
    log.info("Starting ExifTool")

    with exiftool.ExifTool(config_file=str(exif.get_analogexif_config())) as et:
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
        content = _format_content(v)
        if content and v != "" and tag:
            params.append(f'-{tag}="{content}"')

    params.append("-overwrite_original")
    params.append(str(filename))

    log.info("ExifTool parameters: %s", params)

    return params


def _format_content(value: str):
    if value is None:
        return None
    elif isinstance(value, collections.abc.Sequence) and not isinstance(value, str):
        # List, Tuple, ...
        list_content = [_format_content(v) for v in value]
        return " ".join(list_content)
    else:
        # str and non-iterable and not null
        return str(value)
