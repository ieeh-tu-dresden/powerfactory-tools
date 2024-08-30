# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2024.
# :license: BSD 3-Clause

from __future__ import annotations

import abc
import csv
import enum
import json
import pathlib
import pickle
import typing as t

import loguru
import pydantic

try:
    import pandas as pd
except ModuleNotFoundError:
    loguru.logger.error("Missing optional dependency 'pandas'. Use pip or conda to install pandas.")

if t.TYPE_CHECKING:
    import collections.abc as cabc

    PrimitiveType = (
        str | bool | int | float | None | cabc.Sequence["PrimitiveType"] | cabc.Mapping[str, "PrimitiveType"]
    )


class FileType(enum.Enum):
    FEATHER = ".feather"  # exchange format for dataframes using pyarrow internally
    DAT = ".dat"  # e.g. for COMTRADE
    CSV = ".csv"
    JSON = ".json"
    PICKLE = ".pkl"
    RAW = ".raw"  # e.g. for PSSPLT_VERSION_2
    TXT = ".txt"

    @classmethod
    def values(cls) -> list[str]:
        return [_.value for _ in list(cls)]

    @classmethod
    def has(cls, value: str) -> bool:
        return value in cls.values()


@pydantic.dataclasses.dataclass
class ExportHandler(abc.ABC):
    directory_path: pathlib.Path

    def export_user_data(
        self,
        data: dict[str, PrimitiveType],
        /,
        *,
        file_type: FileType,
        file_name: str | None = None,
    ) -> None:
        """Export user defined data to different file types.

        Arguments:
            data {dict[str, PrimitiveType]]} -- data to export
            export_path {pathlib.Path} -- the directory where the exported json file is saved
            file_type {FileType} -- the chosen file type for data export
            file_name {str | None} -- the chosen file name for data export. (default: {None})
        """
        loguru.logger.debug(
            "Export data to {export_path} as {file_type} ...",
            file_type=file_type,
            export_path=str(self.directory_path),
        )
        if not FileType.has(file_type.value):
            msg = f"File type {file_type} is not supported."
            raise ValueError(msg)

        file_path = self.create_file_path(
            file_type=file_type,
            file_name=file_name,
        )

        if file_type is FileType.CSV:
            self.to_csv(file_path, data=data)
        elif file_type is FileType.FEATHER:
            self.to_feather(file_path, data=data)
        elif file_type is FileType.JSON:
            self.to_json(file_path, data=data)
        elif file_type is FileType.PICKLE:
            self.to_pickle(file_path, data=data)

    @abc.abstractmethod
    def create_file_path(
        self,
        *,
        file_type: FileType,
        file_name: str | None = None,
        active_study_case: PFTypes.StudyCase | None = None,  # type: ignore # noqa: F821 , PGH003
    ) -> pathlib.Path:
        msg = "This method should be implemented in a subclass"
        raise NotImplementedError(msg)

    @staticmethod
    def _format_dict(data: dict[str, PrimitiveType]) -> dict[str, PrimitiveType]:
        # Convert dictionary to list of dictionaries
        max_length = max(len(v) if isinstance(v, list) else 1 for v in data.values())
        # Convert non-list values to lists with repeated values and pad shorter lists with None
        return {
            key: (v + [None] * (max_length - len(v))) if isinstance(v, list) else ([v] + [None] * (max_length - 1))
            for key, v in data.items()
        }

    def to_json(self, file_path: pathlib.Path, /, *, data: dict[str, PrimitiveType], indent: int = 2) -> bool:
        padded_data = self._format_dict(data)
        try:
            with pathlib.Path(file_path).open("w+", encoding="utf-8") as file_handle:
                json.dump(padded_data, file_handle, indent=indent, sort_keys=True)

        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to JSON failed at {file_path!s} with error {e}")
            return False

        return True

    def to_csv(self, file_path: pathlib.Path, /, *, data: dict[str, PrimitiveType]) -> bool:
        padded_data = self._format_dict(data)
        list_of_dicts = [dict(zip(padded_data, t, strict=False)) for t in zip(*padded_data.values(), strict=False)]

        try:
            with pathlib.Path(file_path).open("w+", encoding="utf-8", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=data.keys())
                writer.writeheader()
                writer.writerows(list_of_dicts)

        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to CSV failed at {file_path!s} with error {e}")
            return False

        return True

    def to_feather(self, file_path: pathlib.Path, /, *, data: dict[str, PrimitiveType]) -> bool:
        padded_data = self._format_dict(data)
        dataframe = pd.DataFrame.from_dict(padded_data)

        try:
            with pathlib.Path(file_path).open("wb+") as file_handle:
                dataframe.to_feather(file_handle)

        except ImportError:
            loguru.logger.error("Missing optional dependency 'pyarrow'. Use pip or conda to install pyarrow.")
            return False
        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to FEATHER failed at {file_path!s} with error {e}")
            return False

        return True

    def to_pickle(self, file_path: pathlib.Path, /, *, data: dict[str, PrimitiveType]) -> bool:
        padded_data = self._format_dict(data)
        try:
            with pathlib.Path(file_path).open("wb+") as file_handle:
                pickle.dump(padded_data, file_handle)

        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to PICKLE failed at {file_path!s} with error {e}")
            return False

        return True


@pydantic.dataclasses.dataclass
class ImportHandler:
    file_path: pathlib.Path

    def __post_init__(self) -> None:
        self.file_type = FileType(self.file_path.suffix)
        if not self.file_path.exists():
            msg = f"File path {self.file_path} does not exist."
            raise FileNotFoundError(msg)

        if not FileType.has(self.file_type.value):
            msg = f"File type {self.file_path.suffix} is not supported."
            raise ValueError(msg)

    def import_user_data(
        self,
    ) -> dict[str, PrimitiveType] | None:
        """Import different file types as raw data.

        Returns:
            {dict[str, PrimitiveType]} -- the imported data as a dict
        """

        loguru.logger.debug(
            "Import data from {file_path} as {file_type} ...",
            file_type=self.file_type,
            file_path=str(self.file_path),
        )

        if self.file_type is FileType.CSV:
            return self.from_csv()

        if self.file_type is FileType.FEATHER:
            return self.from_feather()

        if self.file_type is FileType.JSON:
            return self.from_json()

        return None

    @staticmethod
    def _format_dataframe(dataframe: pd.DataFrame) -> dict[str, PrimitiveType]:
        # Drop NaN values from each column
        data = {col: dataframe[col].dropna().tolist() for col in dataframe.columns}
        # Unmap lists with a single value back to a single value
        for key, value in data.items():
            if all(v == value[0] for v in value):
                data[key] = value[0]

        return data

    def from_csv(self) -> dict[str, PrimitiveType] | None:
        try:
            with pathlib.Path(self.file_path).open("rb") as file_handle:
                dataframe = pd.read_csv(file_handle)
                return self._format_dataframe(dataframe)

        except ImportError:
            loguru.logger.error("Missing optional dependency 'pyarrow'. Use pip or conda to install pyarrow.")
            return None
        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Import from CSV failed at {self.file_path!s} with error {e}")
            return None

    def from_json(self) -> dict[str, PrimitiveType] | None:
        try:
            with pathlib.Path(self.file_path).open("r+", encoding="utf-8") as file_handle:
                dataframe = pd.read_json(file_handle)
                return self._format_dataframe(dataframe)

        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Import from JSON failed at {self.file_path!s} with error {e}")
            return None

    def from_feather(self) -> dict[str, PrimitiveType] | None:
        try:
            with pathlib.Path(self.file_path).open("rb") as file_handle:
                dataframe = pd.read_feather(file_handle)
                return self._format_dataframe(dataframe)

        except ImportError:
            loguru.logger.error("Missing optional dependency 'pyarrow'. Use pip or conda to install pyarrow.")
            return None
        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Import from FEATHER failed at {self.file_path!s} with error {e}")
            return None
