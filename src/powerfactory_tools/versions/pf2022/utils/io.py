# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2024.
# :license: BSD 3-Clause

from __future__ import annotations

import datetime as dt
import typing as t

import pydantic

from powerfactory_tools.utils.io import ExportHandler as BaseExportHandler
from powerfactory_tools.versions.pf2022.constants import NAME_SEPARATOR

if t.TYPE_CHECKING:
    import pathlib

    from powerfactory_tools.utils.io import FileType
    from powerfactory_tools.versions.pf2022.types import PowerFactoryTypes as PFTypes


@pydantic.dataclasses.dataclass
class ExportHandler(BaseExportHandler):
    def create_file_path(
        self,
        *,
        file_type: FileType,
        file_name: str | None = None,
        active_study_case: PFTypes.StudyCase | None = None,
    ) -> pathlib.Path:
        timestamp = dt.datetime.now().astimezone()
        timestamp_string = timestamp.isoformat(sep="T", timespec="seconds").replace(":", "")
        study_case_name = f"{active_study_case.loc_name}{NAME_SEPARATOR}" if active_study_case is not None else ""
        filename = (
            f"{study_case_name}{timestamp_string}{file_type.value}"
            if file_name is None
            else f"{study_case_name}{file_name}{file_type.value}"
        )
        file_path = self.directory_path / filename
        # Formal validation of path
        try:
            file_path.resolve()
        except OSError as e:
            msg = f"File path {file_path} is not a valid path."
            raise FileNotFoundError(msg) from e

        # Create (sub)direcotries if not existing
        file_path.parent.mkdir(parents=True, exist_ok=True)

        return file_path
