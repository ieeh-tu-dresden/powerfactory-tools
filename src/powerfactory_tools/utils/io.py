# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2025.
# :license: BSD 3-Clause


from __future__ import annotations

import ast
import datetime as dt
import enum
import json
import pathlib
import typing as t

import loguru

from powerfactory_tools.str_constants import NAME_SEPARATOR

if t.TYPE_CHECKING:
    import collections.abc as cabc

    PrimitiveType = (
        str | bool | int | float | None | cabc.Sequence["PrimitiveType"] | cabc.Mapping[str, "PrimitiveType"]
    )


class FileType(enum.Enum):
    CSV = ".csv"
    DAT = ".dat"  # e.g. for COMTRADE
    FEATHER = ".arrow"  # exchange format for dataframes using pyarrow (Feather (V2) is a full set of the Arrow IPC file format)
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


def _format_dict(data: dict[str, PrimitiveType]) -> dict[str, cabc.Sequence[PrimitiveType]]:
    """Convert dict with heterogenous lengths of value to dict with where all values are lists of the same length."""
    max_length = max(len(v) if isinstance(v, list) else 1 for v in data.values())
    # Convert (non-list) values to lists with uniform length and fill (if necessary) shorter lists with None
    return {
        key: (v + [None] * (max_length - len(v))) if isinstance(v, list) else ([v] + [None] * (max_length - 1))
        for key, v in data.items()
    }


class BaseIoHandler:
    @staticmethod
    def create_file_path(
        *,
        root_path: pathlib.Path,
        file_type: FileType,
        file_name: str | None = None,
        study_case_name: str | None = None,
    ) -> pathlib.Path:
        timestamp = dt.datetime.now().astimezone()
        timestamp_string = timestamp.isoformat(sep="T", timespec="seconds").replace(":", "")
        study_case_name = f"{study_case_name}{NAME_SEPARATOR}" if study_case_name is not None else ""
        filename = (
            f"{study_case_name}{timestamp_string}{file_type.value}"
            if file_name is None
            else f"{study_case_name}{file_name}{file_type.value}"
        )
        file_path = root_path / filename
        # Formal validation of path
        try:
            file_path.resolve()
        except OSError as e:
            msg = f"File path {file_path} is not a valid path."
            raise FileNotFoundError(msg) from e

        # Create (sub)directories if not existing
        file_path.parent.mkdir(parents=True, exist_ok=True)

        return file_path


class PandasIoHandler(BaseIoHandler):
    """Handler for importing and exporting data using pandas."""

    try:
        import pandas as pd  # noqa: PLC0415
    except ModuleNotFoundError:
        loguru.logger.error("Missing optional dependency 'pandas'. Use uv pip, pip or conda to install pandas.")

    SUPPORTED_FILE_TYPES_IMP: t.ClassVar[set[FileType]] = {FileType.CSV, FileType.FEATHER, FileType.JSON}
    SUPPORTED_FILE_TYPES_EXP: t.ClassVar[set[FileType]] = {
        FileType.CSV,
        FileType.FEATHER,
        FileType.JSON,
        FileType.PICKLE,
    }

    @staticmethod
    def convert_dataframe_to_dict(dataframe: pd.DataFrame) -> cabc.Mapping[str, PrimitiveType]:
        """Convert a pandas DataFrame to a dict."""
        # Drop NaN values from each column
        data = {col: dataframe[col].dropna().tolist() for col in dataframe.columns}
        # Unmap lists with a single value back to a single value
        for key, value in data.items():
            if all(v == value[0] for v in value):
                data[key] = value[0]

        return data

    @staticmethod
    def convert_dict_to_dataframe(data: dict[str, PrimitiveType] | pd.DataFrame) -> pd.DataFrame:
        """Convert dict to a pandas DataFrame."""
        if isinstance(data, dict):
            padded_data = _format_dict(data)
            return PandasIoHandler.pd.DataFrame.from_dict(padded_data)

        return data

    @staticmethod
    def convert_str_lists_to_lists(df: pd.DataFrame, columns: cabc.Sequence[str] | None = None) -> pd.DataFrame:
        """Convert string representations of lists in specified columns to actual lists."""
        for col in columns if columns is not None else df.columns:
            df[col] = df[col].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith("[") and x.endswith("]") else x,
            )
        return df

    @staticmethod
    def convert_str_dicts_to_dicts(df: pd.DataFrame, columns: cabc.Sequence[str] | None = None) -> pd.DataFrame:
        """Convert string representations of dicts in specified columns to actual dicts."""
        for col in columns if columns is not None else df.columns:
            df[col] = df[col].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith("{") and x.endswith("}") else x,
            )
        return df

    def export_user_data(
        self,
        data: dict[str, PrimitiveType] | pd.DataFrame,
        /,
        *,
        export_root_path: pathlib.Path,
        file_type: FileType,
        file_name: str | None = None,
    ) -> None:
        """Export user defined data to different file types.

        Arguments:
            data {dict[str, PrimitiveType] | pd.DataFrame} -- data to export
            file_type {FileType} -- the chosen file type for data export
            file_name {str | None} -- the chosen file name for data export. (default: {None})
        """
        loguru.logger.debug(
            "Export data to {export_root_path} as {file_type} ...",
            file_type=file_type,
            export_root_path=str(export_root_path),
        )
        if not self.SUPPORTED_FILE_TYPES_EXP.__contains__(file_type):
            msg = f"File type {file_type} is not supported."
            raise ValueError(msg)

        file_path = self.create_file_path(
            root_path=export_root_path,
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

    def to_json(
        self,
        file_path: pathlib.Path,
        /,
        *,
        data: dict[str, PrimitiveType] | pd.DataFrame,
        indent: int = 2,
    ) -> bool:
        dataframe = PandasIoHandler.convert_dict_to_dataframe(data)
        try:
            with pathlib.Path(file_path).open("w+") as file_handle:
                dataframe.to_json(file_handle, indent=indent)

        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to JSON failed at {file_path!s} with error {e}")
            return False

        return True

    @staticmethod
    def to_csv(
        file_path: pathlib.Path,
        /,
        *,
        data: dict[str, PrimitiveType] | pd.DataFrame,
        separator: str = ",",
    ) -> bool:
        dataframe = PandasIoHandler.convert_dict_to_dataframe(data)
        try:
            with pathlib.Path(file_path).open("w", encoding="utf-8", newline="") as file_handle:
                dataframe.to_csv(file_handle, sep=separator, index=False)

        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to CSV failed at {file_path!s} with error {e}")
            return False

        return True

    @staticmethod
    def to_feather(file_path: pathlib.Path, /, *, data: dict[str, PrimitiveType] | pd.DataFrame) -> bool:
        dataframe = PandasIoHandler.convert_dict_to_dataframe(data)
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

    @staticmethod
    def to_pickle(file_path: pathlib.Path, /, *, data: dict[str, PrimitiveType] | pd.DataFrame) -> bool:
        dataframe = PandasIoHandler.convert_dict_to_dataframe(data)
        try:
            with pathlib.Path(file_path).open("wb+") as file_handle:
                dataframe.to_pickle(file_handle)

        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to PICKLE failed at {file_path!s} with error {e}")
            return False

        return True

    def import_user_data(
        self,
        file_path: pathlib.Path,
    ) -> pd.DataFrame | None:
        """Import different file types as raw data.

        Arguments:
            file_path {pathlib.Path} -- the path to the file to import

        Returns:
            {pd.DataFrame} -- the imported data as a pandas DataFrame or None if import failed
        """
        # Init check for file type
        file_type = FileType(file_path.suffix)
        if not file_path.exists():
            msg = f"File path {file_path} does not exist."
            raise FileNotFoundError(msg)
        if not self.SUPPORTED_FILE_TYPES_IMP.__contains__(file_type):
            msg = f"File type {file_path.suffix} is not supported."
            raise ValueError(msg)

        loguru.logger.debug(
            "Import data from {file_path} as {file_type} ...",
            file_type=file_type,
            file_path=str(file_path),
        )

        if file_type is FileType.CSV:
            return self.from_csv(file_path)

        if file_type is FileType.FEATHER:
            return self.from_feather(file_path)

        if file_type is FileType.JSON:
            return self.from_json(file_path)

        return None

    def from_csv(self, file_path: pathlib.Path, separator: str = ",") -> pd.DataFrame | None:
        try:
            with pathlib.Path(file_path).open("r") as file_handle:
                return PandasIoHandler.pd.read_csv(file_handle, sep=separator)

        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Import from CSV failed at {file_path!s} with error {e}")
            return None

    def from_json(self, file_path: pathlib.Path) -> pd.DataFrame | None:
        try:
            with pathlib.Path(file_path).open("r+", encoding="utf-8") as file_handle:
                return PandasIoHandler.pd.read_json(file_handle)

        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Import from JSON failed at {file_path!s} with error {e}")
            return None

    def from_feather(self, file_path: pathlib.Path) -> pd.DataFrame | None:
        try:
            with pathlib.Path(file_path).open("rb") as file_handle:
                return PandasIoHandler.pd.read_feather(file_handle)

        except ImportError:
            loguru.logger.error("Missing optional dependency 'pyarrow'. Use uv pip, pip or conda to install pyarrow.")
            return None
        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Import from FEATHER failed at {file_path!s} with error {e}")
            return None


class PolarsIoHandler(BaseIoHandler):
    """Handler for importing and exporting data using polars."""

    try:
        import polars as pl  # noqa: PLC0415
    except ModuleNotFoundError:
        loguru.logger.error("Missing optional dependency 'polars'. Use uv pip, pip or conda to install polars.")

    SUPPORTED_FILE_TYPES: t.ClassVar[set[FileType]] = {FileType.CSV, FileType.FEATHER, FileType.JSON}

    @staticmethod
    def convert_dict_to_dataframe(data: dict[str, PrimitiveType] | pl.DataFrame) -> pl.DataFrame:
        """Convert dict to a polars DataFrame."""
        if isinstance(data, dict):
            padded_data = _format_dict(data)
            return PolarsIoHandler.pl.from_dict(padded_data)

        return data

    def export_user_data(
        self,
        data: dict[str, PrimitiveType] | pl.DataFrame,
        /,
        *,
        export_root_path: pathlib.Path,
        file_type: FileType,
        file_name: str | None = None,
    ) -> None:
        """Export user defined data to different file types.

        Arguments:
            data {dict[str, PrimitiveType] | pl.DataFrame} -- data to export
            export_root_path {pathlib.Path} -- the root directory where the exported file is to be saved
            file_type {FileType} -- the chosen file type for data export
            file_name {str | None} -- the chosen file name for data export. (default: {None})
        """
        loguru.logger.debug(
            "Export data to {export_root_path} as {file_type} ...",
            file_type=file_type,
            export_root_path=str(export_root_path),
        )
        if not self.SUPPORTED_FILE_TYPES.__contains__(file_type):
            msg = f"File type {file_type} is not supported."
            raise ValueError(msg)

        file_path = self.create_file_path(
            root_path=export_root_path,
            file_type=file_type,
            file_name=file_name,
        )

        if file_type is FileType.CSV:
            self.to_csv(file_path, data=data)
        elif file_type is FileType.FEATHER:
            self.to_feather(file_path, data=data)
        elif file_type is FileType.JSON:
            self.to_json(file_path, data=data)

    def to_json(
        self,
        file_path: pathlib.Path,
        /,
        *,
        data: dict[str, PrimitiveType] | pl.DataFrame,
        indent: int = 2,
    ) -> bool:
        dataframe = PolarsIoHandler.convert_dict_to_dataframe(data)
        datadict = dataframe.to_dicts()
        try:
            with pathlib.Path(file_path).open("w+", encoding="utf-8") as file_handle:
                # need to use json.dump to make use of the indent parameter
                # polars does not support indenting natively
                json.dump(datadict, file_handle, indent=indent, sort_keys=True)

        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to JSON failed at {file_path!s} with error {e}")
            return False

        return True

    @staticmethod
    def to_csv(
        file_path: pathlib.Path,
        /,
        *,
        data: dict[str, PrimitiveType] | pl.DataFrame,
        separator: str = ",",
    ) -> bool:
        dataframe = PolarsIoHandler.convert_dict_to_dataframe(data)
        try:
            with pathlib.Path(file_path).open("w", encoding="utf-8", newline="") as file_handle:
                dataframe.write_csv(file_handle, separator=separator, quote_style="non_numeric")

        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to CSV failed at {file_path!s} with error {e}")
            return False

        return True

    @staticmethod
    def to_feather(file_path: pathlib.Path, /, *, data: dict[str, PrimitiveType] | pl.DataFrame) -> bool:
        dataframe = PolarsIoHandler.convert_dict_to_dataframe(data)
        try:
            with pathlib.Path(file_path).open("wb+") as file_handle:
                dataframe.write_ipc(file_handle)

        except ImportError:
            loguru.logger.error("Missing optional dependency 'pyarrow'. Use pip or conda to install pyarrow.")
            return False
        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Export to FEATHER failed at {file_path!s} with error {e}")
            return False

        return True

    def import_user_data(
        self,
        file_path: pathlib.Path,
    ) -> pl.DataFrame | None:
        """Import different file types as raw data.

        Arguments:
            file_path {pathlib.Path} -- the path to the file to import

        Returns:
            {pl.DataFrame} -- the imported data as a polars DataFrame or None if import failed
        """
        # Init check for file type
        file_type = FileType(file_path.suffix)
        if not file_path.exists():
            msg = f"File path {file_path} does not exist."
            raise FileNotFoundError(msg)
        if not self.SUPPORTED_FILE_TYPES.__contains__(file_type):
            msg = f"File type {file_path.suffix} is not supported."
            raise ValueError(msg)

        loguru.logger.debug(
            "Import data from {file_path} as {file_type} ...",
            file_type=file_type,
            file_path=str(file_path),
        )

        if file_type is FileType.CSV:
            return self.from_csv(file_path)

        if file_type is FileType.FEATHER:
            return self.from_feather(file_path)

        if file_type is FileType.JSON:
            return self.from_json(file_path)

        return None

    def from_csv(self, file_path: pathlib.Path, separator: str = ",") -> pl.DataFrame | None:
        try:
            with pathlib.Path(file_path).open("r+", encoding="utf-8") as file_handle:
                return PolarsIoHandler.pl.read_csv(file_handle, separator=separator)

        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Import from CSV failed at {file_path!s} with error {e}")
            return None

    def from_json(self, file_path: pathlib.Path) -> pl.DataFrame | None:
        try:
            with pathlib.Path(file_path).open("r+", encoding="utf-8") as file_handle:
                return PolarsIoHandler.pl.read_json(file_handle)

        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Import from JSON failed at {file_path!s} with error {e}")
            return None

    def from_feather(self, file_path: pathlib.Path) -> pl.DataFrame | None:
        try:
            with pathlib.Path(file_path).open("rb") as file_handle:
                return PolarsIoHandler.pl.read_ipc(file_handle)

        except ImportError:
            loguru.logger.error("Missing optional dependency 'pyarrow'. Use uv pip, pip or conda to install pyarrow.")
            return None
        except Exception as e:  # noqa: BLE001
            loguru.logger.error(f"Import from FEATHER failed at {file_path!s} with error {e}")
            return None
