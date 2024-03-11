# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import datetime as dt
import logging
import pathlib
import typing as t

import loguru
import pydantic

from powerfactory_tools.base.interface import DEFAULT_POWERFACTORY_PATH
from powerfactory_tools.base.interface import PowerFactoryInterface as PowerFactoryInterfaceBase
from powerfactory_tools.base.types import PFClassId
from powerfactory_tools.versions.pf2022.data import PowerFactoryData

if t.TYPE_CHECKING:
    from collections.abc import Sequence

    from powerfactory_tools.versions.pf2022.types import PowerFactoryTypes as PFTypes


POWERFACTORY_VERSION = "PowerFactory 2022"
PYTHON_VERSIONS = t.Literal["3.6", "3.7", "3.8", "3.9", "3.10"]
DEFAULT_PYTHON_VERSION = "3.10"

config = pydantic.ConfigDict(use_enum_values=True)


@pydantic.dataclasses.dataclass
class PowerFactoryInterface(PowerFactoryInterfaceBase):
    project_name: str
    powerfactory_path: pathlib.Path = DEFAULT_POWERFACTORY_PATH
    powerfactory_service_pack: int | None = None
    powerfactory_user_profile: str | None = None
    powerfactory_user_password: str | None = None
    powerfactory_ini_name: str | None = None
    python_version: PYTHON_VERSIONS = DEFAULT_PYTHON_VERSION
    logging_level: int = logging.DEBUG
    log_file_path: pathlib.Path | None = None

    def __post_init__(self) -> None:
        try:
            self._set_logging_handler(self.log_file_path)
            loguru.logger.info("Starting PowerFactory Interface...")
            pfm = self.load_powerfactory_module_from_path(POWERFACTORY_VERSION)
            self.app = self.connect_to_app(pfm, POWERFACTORY_VERSION)
            self.project = self.connect_to_project(self.project_name)
            self.load_project_setting_folders_from_pf_db()
            self.stash_unit_conversion_settings()
            self.set_default_unit_conversion()
            self.load_project_folders_from_pf_db()
            loguru.logger.info("Starting PowerFactory Interface... Done.")
        except RuntimeError:
            loguru.logger.exception("Could not start PowerFactory Interface. Shutting down...")
            self.close()

    def compile_powerfactory_data(self, grid: PFTypes.Grid) -> PowerFactoryData:
        """Read out all relevant data from PowerFactory 2022 for a given grid and store as typed dataclass PowerFactroyData.

        Args:
            grid (PFTypes.Grid): the grid object to be read out

        Returns:
            PowerFactoryData: a dataclass containing typed lists with all relevant data from PowerFactory
        """
        grid_name = grid.loc_name
        loguru.logger.debug("Compiling data from PowerFactory for grid {grid_name}...", grid_name=grid_name)

        project_name = self.project.loc_name
        date = dt.datetime.now().astimezone().date()

        return PowerFactoryData(
            date=date,
            project_name=project_name,
            grid_name=grid_name,
            external_grids=self.external_grids(grid_name=grid_name, calc_relevant=True),
            terminals=self.terminals(grid_name=grid_name, calc_relevant=True),
            lines=self.lines(grid_name=grid_name, calc_relevant=True),
            transformers_2w=self.transformers_2w(grid_name=grid_name, calc_relevant=True),
            transformers_3w=self.transformers_3w(grid_name=grid_name, calc_relevant=True),
            loads=self.loads(grid_name=grid_name, calc_relevant=True),
            loads_lv=self.loads_lv(grid_name=grid_name, calc_relevant=True),
            loads_mv=self.loads_mv(grid_name=grid_name, calc_relevant=True),
            generators=self.generators(grid_name=grid_name, calc_relevant=True),
            pv_systems=self.pv_systems(grid_name=grid_name, calc_relevant=True),
            couplers=self.couplers(grid_name=grid_name, calc_relevant=True),
            switches=self.switches(grid_name=grid_name, calc_relevant=True),
            bfuses=self.bfuses(grid_name=grid_name, calc_relevant=True),
            efuses=self.efuses(grid_name=grid_name, calc_relevant=True),
            ac_current_sources=self.ac_current_sources(grid_name=grid_name, calc_relevant=True),
        )

    def subloads_of(
        self,
        load: PFTypes.LoadLV,
        /,
    ) -> Sequence[PFTypes.LoadLVP]:
        elements = self.elements_of(load, pattern="*." + PFClassId.LOAD_LV_PART.value)
        return [t.cast("PFTypes.LoadLVP", element) for element in elements]

    def load_lv(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.LoadLV | None:
        return self.first_of(self.loads_lv(name, grid_name=grid_name))

    def loads_lv(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
    ) -> Sequence[PFTypes.LoadLV]:
        elements = self.grid_elements(
            class_name=PFClassId.LOAD_LV.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
        )
        return [t.cast("PFTypes.LoadLV", element) for element in elements]

    def load_mv(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.LoadMV | None:
        return self.first_of(self.loads_mv(name, grid_name=grid_name))

    def loads_mv(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
    ) -> Sequence[PFTypes.LoadMV]:
        elements = self.grid_elements(
            class_name=PFClassId.LOAD_MV.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
        )
        return [t.cast("PFTypes.LoadMV", element) for element in elements]
