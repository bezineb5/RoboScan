from __future__ import annotations
import dataclasses
from typing import Optional, Tuple

from dataclasses_json import dataclass_json

from scanner.frame_counter import FrameCounter


@dataclass_json
@dataclasses.dataclass(frozen=True)
class MetaData:
    exposure_number: Optional[int]
    lens_serial_number: str
    roll_id: str
    film_maker: str
    film: str
    film_alias: str
    film_grain: int
    film_type: str
    developer: str
    develop_process: str
    developer_maker: str
    developer_dilution: str
    develop_time: str
    lab: str
    lab_address: str
    filter: str
    crop: Optional[Tuple[float, float, float, float]] = None

    def with_frame_count(self, frame_count: Optional[FrameCounter]) -> MetaData:
        if frame_count is None:
            return self
        return dataclasses.replace(self, exposure_number=frame_count.current_frame_index)

    def with_crop(self, crop: Optional[Tuple[float, float, float, float]]) -> MetaData:
        return dataclasses.replace(self, crop=crop)
