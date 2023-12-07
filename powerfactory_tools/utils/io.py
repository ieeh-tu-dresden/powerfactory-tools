# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import enum
import json
import pathlib


class FileType(enum.Enum):
    ARROW = ".arrow"
    DAT = ".dat"  # e.g. for COMTRADE
    CSV = ".csv"
    JSON = ".json"
    PICKLE = ".pkl"
    RAW = ".raw"  # e.g. for PSSPLT_VERSION_2
    TXT = ".txt"


def to_json(data: dict, file_path: str | pathlib.Path, indent: int = 2) -> None:
    file_path = pathlib.Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w+", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, indent=indent, sort_keys=True)
