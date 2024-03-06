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
class PowerFactoryInterface:
    project_name: str
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH
    powerfactory_version: str = DEFAULT_PF_VERSION

    @pydantic.field_validator("powerfactory_version")
    def check_unit(cls, v: str) -> str:
        if v is not SUPPORTED_VERSIONS:
            msg = f"Version {v} is not supported. Supported versions are {SUPPORTED_VERSIONS}"
            raise ValueError(msg)

        return v

    powerfactory_service_pack: int | None = None
    powerfactory_user_profile: str = ""
    powerfactory_user_password: str | None = None
    powerfactory_ini_name: str | None = None
    logging_level: int = logging.DEBUG
    log_file_path: pathlib.Path | None = None

    def __post_init__(self) -> None:
        interface_import_path = PF_VERSIONS[self.powerfactory_version]["interface"]
        pfm = importlib.import_module(interface_import_path)
        pfi = pfm.Interface(
            project_name=self.project_name,
            powerfactory_path=self.powerfactory_path,
            powerfactory_service_pack=self.powerfactory_service_pack,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_user_password=self.powerfactory_user_password,
            powerfactory_ini_name=self.powerfactory_ini_name,
            logging_level=self.logging_level,
            log_file_path=self.log_file_path,
        )
        self.__dict__.update(pfi.__dict__)
