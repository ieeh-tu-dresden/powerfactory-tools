# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import importlib
import logging
import pathlib

import pydantic

from powerfactory_tools.versions.powerfactory import DEFAULT_PF_PATH as POWERFACTORY_PATH
from powerfactory_tools.versions.powerfactory import DEFAULT_PF_VERSION
from powerfactory_tools.versions.powerfactory import PF_VERSIONS
from powerfactory_tools.versions.powerfactory import SUPPORTED_VERSIONS


@pydantic.dataclasses.dataclass
class PowerFactoryExporter:
    project_name: str
    powerfactory_version: str = DEFAULT_PF_VERSION

    @pydantic.field_validator("powerfactory_version")
    def check_unit(cls, v: str) -> str:
        if v is not SUPPORTED_VERSIONS:
            msg = f"Version {v} is not supported. Supported versions are {SUPPORTED_VERSIONS}"
            raise ValueError(msg)

        return v

    powerfactory_user_profile: str = ""
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH
    powerfactory_service_pack: int | None = None
    logging_level: int = logging.DEBUG
    log_file_path: pathlib.Path | None = None

    def __post_init__(self) -> None:
        exporter_import_path = PF_VERSIONS[self.powerfactory_version]["exporter"]
        pfm = importlib.import_module(exporter_import_path)
        pfe = pfm.PowerFactoryExporter(
            project_name=self.project_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_path=self.powerfactory_path,
            powerfactory_service_pack=self.powerfactory_service_pack,
            logging_level=self.logging_level,
            log_file_path=self.log_file_path,
        )
        method_names = [method_name for method_name in dir(pfe) if callable(getattr(pfe, method_name))]
        self.__dict__.update(pfe.__dict__)
        for method_name in method_names:
            setattr(self, method_name, getattr(pfe, method_name))


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
