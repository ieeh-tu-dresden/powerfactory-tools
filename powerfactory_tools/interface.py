# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import importlib
import logging
import pathlib

import pydantic

from powerfactory_tools.powerfactory.powerfactory import DEFAULT_PF_PATH as POWERFACTORY_PATH
from powerfactory_tools.powerfactory.powerfactory import DEFAULT_PF_VERSION
from powerfactory_tools.powerfactory.powerfactory import PF_VERSIONS
from powerfactory_tools.powerfactory.powerfactory import SUPPORTED_VERSIONS


@pydantic.dataclasses.dataclass
class PowerFactoryInterface:
    project_name: str
    powerfactory_version: str = DEFAULT_PF_VERSION

    @pydantic.field_validator("powerfactory_version")
    def check_unit(cls, v: str) -> str:
        if v is not SUPPORTED_VERSIONS:
            msg = f"Version {v} is not supported. Supported versions are {SUPPORTED_VERSIONS}"
            raise ValueError(msg)

        return v

    powerfactory_user_profile: str = ""
    powerfactory_user_password: str | None = None
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH
    powerfactory_ini_name: str | None = None
    logging_level: int = logging.DEBUG
    log_file_path: pathlib.Path | None = None

    def __post_init__(self) -> None:
        exporter_import_path = PF_VERSIONS[self.powerfactory_version]["exporter"]
        pfm = importlib.import_module(exporter_import_path)
        pfi = pfm.Interface(
            project_name=self.project_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_user_password=self.powerfactory_user_password,
            powerfactory_path=self.powerfactory_path,
            powerfactory_ini_name=self.powerfactory_ini_name,
            logging_level=self.logging_level,
            log_file_path=self.log_file_path,
        )
        self.__dict__.update(pfi.__dict__)


def export_powerfactory_data(  # noqa: PLR0913
    *,
    export_path: pathlib.Path,
    project_name: str,
    powerfactory_user_profile: str = "",
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH,
    powerfactory_version: str = DEFAULT_PF_VERSION,
    logging_level: int = logging.DEBUG,
    log_file_path: pathlib.Path | None = None,
    topology_name: str | None = None,
    topology_case_name: str | None = None,
    steadystate_case_name: str | None = None,
    study_case_names: list[str] | None = None,
) -> None:
    exporter_import_path = PF_VERSIONS[powerfactory_version]["exporter"]
    pfm = importlib.import_module(exporter_import_path)
    pfm.export_powerfactory_data(
        export_path=export_path,
        project_name=project_name,
        powerfactory_user_profile=powerfactory_user_profile,
        powerfactory_path=powerfactory_path,
        logging_level=logging_level,
        log_file_path=log_file_path,
        topology_name=topology_name,
        topology_case_name=topology_case_name,
        steadystate_case_name=steadystate_case_name,
        study_case_names=study_case_names,
    )
