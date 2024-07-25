# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import csv
import enum
import importlib
import json
import pathlib
import pickle

import loguru
import pydantic


class FileType(enum.Enum):
    FEATHER = ".feather"  # exchange format for dataframes using pyarrow internally
    DAT = ".dat"  # e.g. for COMTRADE
    CSV = ".csv"
    JSON = ".json"
    PICKLE = ".pkl"
    RAW = ".raw"  # e.g. for PSSPLT_VERSION_2
    TXT = ".txt"


@pydantic.dataclasses.dataclass
class CustomEncoder:
    data: dict
    parent_path: str | pathlib.Path

    def __post_init__(self) -> None:
        parent_path = pathlib.Path(self.parent_path)
        parent_path.mkdir(parents=True, exist_ok=True)

    def to_json(self, file_path: str | pathlib.Path, /, indent: int = 2) -> bool:
        try:
            with pathlib.Path(file_path).open("w+", encoding="utf-8") as file_handle:
                json.dump(self.data, file_handle, indent=indent, sort_keys=True)
        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to JSON failed at {file_path!s} with error {e}")
            return False

        return True

    def to_csv(self, file_path: str | pathlib.Path, /) -> bool:
        try:
            with pathlib.Path(file_path).open("w+", encoding="utf-8", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.data.keys())
                writer.writeheader()
                writer.writerow(self.data)
        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to CSV failed at {file_path!s} with error {e}")
            return False

        return True

    def to_feather(self, file_path: str | pathlib.Path, /) -> bool:
        try:
            pd = importlib.import_module("pandas")
        except ModuleNotFoundError:
            loguru.logger.error("Missing optional dependency 'pandas'. Use pip or conda to install pandas.")
            return False

        dataframe = pd.DataFrame.from_dict(self.data)

        try:
            with pathlib.Path(file_path).open("wb+", encoding="utf-8") as file_handle:
                dataframe.to_feather(file_handle)
        except ImportError:
            loguru.logger.error("Missing optional dependency 'pyarrow'. Use pip or conda to install pyarrow.")
            return False
        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to FEATHER failed at {file_path!s} with error {e}")
            return False

        return True

    def to_pickle(self, file_path: str | pathlib.Path, /) -> bool:
        try:
            with pathlib.Path(file_path).open("wb+") as file_handle:
                pickle.dump(self.data, file_handle)
        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to PICKLE failed at {file_path!s} with error {e}")
            return False

        return True
