# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import json
import pathlib


def to_json(data: dict, file_path: str | pathlib.Path, indent: int = 2) -> None:
    file_path = pathlib.Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w+", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, indent=indent, sort_keys=True)
