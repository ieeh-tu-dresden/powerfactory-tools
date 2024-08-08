# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2024.
# :license: BSD 3-Clause

from __future__ import annotations

import csv
import datetime as dt
import enum
import importlib
import json
import pathlib
import pickle
import typing as t

import loguru
import pydantic

if t.TYPE_CHECKING:
    from powerfactory_tools.versions.pf2022.types import PowerFactoryTypes as PFTypes


class FileType(enum.Enum):
    FEATHER = ".feather"  # exchange format for dataframes using pyarrow internally
    DAT = ".dat"  # e.g. for COMTRADE
    CSV = ".csv"
    JSON = ".json"
    PICKLE = ".pkl"
    RAW = ".raw"  # e.g. for PSSPLT_VERSION_2
    TXT = ".txt"


def create_external_file_path(
    *,
    file_type: FileType,
    path: pathlib.Path,
    active_study_case: PFTypes.StudyCase | None = None,
    file_name: str | None = None,
) -> pathlib.Path:
    timestamp = dt.datetime.now().astimezone()
    timestamp_string = timestamp.isoformat(sep="T", timespec="seconds").replace(":", "")
    study_case_name = active_study_case.loc_name if active_study_case is not None else ""
    filename = (
        f"{study_case_name}__{timestamp_string}{file_type.value}"
        if file_name is None
        else f"{file_name}{file_type.value}"
    )
    file_path = path / filename
    # Formal validation of path
    try:
        file_path.resolve()
    except OSError as e:
        msg = f"File path {file_path} is not a valid path."
        raise FileNotFoundError(msg) from e
    # Create (sub)direcotries if not existing
    file_path.parent.mkdir(parents=True, exist_ok=True)

    return file_path


def export_user_data(
    data: dict,
    export_path: pathlib.Path,
    file_type: FileType,
    file_name: str | None = None,
) -> None:
    """Export user defined data to different file types.

    Arguments:
        data {dict} -- data to export
        export_path {pathlib.Path} -- the directory where the exported json file is saved
        file_type {FileType} -- the chosen file type for data export
        file_name {str | None} -- the chosen file name for data export. (default: {None})
    """
    loguru.logger.debug(
        "Export data to {export_path} as {file_type} ...",
        file_type=file_type,
        export_path=str(export_path),
    )
    if file_type not in [FileType.CSV, FileType.FEATHER, FileType.JSON, FileType.PICKLE]:
        msg = f"File type {file_type} is not supported."
        raise ValueError(msg)
    full_file_path = create_external_file_path(
        file_type=file_type,
        path=export_path,
        file_name=file_name,
    )

    ce = CustomEncoder(data=data, parent_path=full_file_path.parent)
    if file_type is FileType.CSV:
        ce.to_csv(full_file_path)
    elif file_type is FileType.FEATHER:
        ce.to_feather(full_file_path)
    elif file_type is FileType.JSON:
        ce.to_json(full_file_path)
    elif file_type is FileType.PICKLE:
        ce.to_pickle(full_file_path)


def import_user_data(
    full_file_path: pathlib.Path,
    file_type: FileType,
) -> dict | None:
    """Import different file types as raw data.

    Arguments:
        full_file_path {pathlib.Path} -- the directory where the file (to be imported) is saved
        file_type {FileType} -- the chosen file type for data export

    Returns:
        {dict} -- the imported data as a dict
    """

    loguru.logger.debug(
        "Import data from {file_path} as {file_type} ...",
        file_type=file_type,
        file_path=str(full_file_path),
    )
    if file_type not in [FileType.CSV, FileType.FEATHER, FileType.JSON]:
        msg = f"File type {file_type} is not supported."
        raise ValueError(msg)

    cd = CustomDecoder()
    if file_type is FileType.CSV:
        return cd.from_csv(full_file_path)
    if file_type is FileType.FEATHER:
        return cd.from_feather(full_file_path)
    if file_type is FileType.JSON:
        return cd.from_json(full_file_path)
    return None


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
        # Convert dictionary to list of dictionaries
        list_of_dicts = [dict(zip(self.data, t, strict=False)) for t in zip(*self.data.values(), strict=False)]
        try:
            with pathlib.Path(file_path).open("w+", encoding="utf-8", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.data.keys())
                writer.writeheader()
                writer.writerows(list_of_dicts)
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
            with pathlib.Path(file_path).open("wb+") as file_handle:
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


class CustomDecoder:
    def from_csv(self, file_path: str | pathlib.Path, /) -> dict | None:
        try:
            pd = importlib.import_module("pandas")
        except ModuleNotFoundError:
            loguru.logger.error("Missing optional dependency 'pandas'. Use pip or conda to install pandas.")
            return None

        try:
            with pathlib.Path(file_path).open("rb") as file_handle:
                dataframe = pd.read_csv(file_handle)
                return dataframe.to_dict(orient="list")
        except ImportError:
            loguru.logger.error("Missing optional dependency 'pyarrow'. Use pip or conda to install pyarrow.")
            return None
        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Import from CSV failed at {file_path!s} with error {e}")
            return None

    def from_json(self, file_path: str | pathlib.Path, /) -> dict | None:
        try:
            pd = importlib.import_module("pandas")
        except ModuleNotFoundError:
            loguru.logger.error("Missing optional dependency 'pandas'. Use pip or conda to install pandas.")
            return None

        try:
            with pathlib.Path(file_path).open("r+", encoding="utf-8") as file_handle:
                dataframe = pd.read_json(file_handle)
                return dataframe.to_dict(orient="list")
        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Import from JSON failed at {file_path!s} with error {e}")
            return None

    def from_feather(self, file_path: str | pathlib.Path, /) -> dict | None:
        try:
            pd = importlib.import_module("pandas")
        except ModuleNotFoundError:
            loguru.logger.error("Missing optional dependency 'pandas'. Use pip or conda to install pandas.")
            return None

        try:
            with pathlib.Path(file_path).open("rb") as file_handle:
                dataframe = pd.read_feather(file_handle)
                return dataframe.to_dict(orient="list")
        except ImportError:
            loguru.logger.error("Missing optional dependency 'pyarrow'. Use pip or conda to install pyarrow.")
            return None
        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Import from FEATHER failed at {file_path!s} with error {e}")
            return None
