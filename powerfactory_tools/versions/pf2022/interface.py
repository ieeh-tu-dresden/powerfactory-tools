# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import datetime as dt
import importlib.util
import logging
import pathlib
import sys
import typing as t

import loguru
import pydantic

from powerfactory_tools.base.interface import DEFAULT_POWERFACTORY_PATH
from powerfactory_tools.base.interface import PowerFactoryInterface as PowerFactoryInterfaceBase
from powerfactory_tools.base.types import PFClassId
from powerfactory_tools.versions.pf2022.data import PowerFactoryData

if t.TYPE_CHECKING:
    from collections.abc import Sequence
    from types import TracebackType

    import typing_extensions as te

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
            pf = self.load_powerfactory_module_from_path()
            self.app = self.connect_to_app(pf)
            self.project = self.connect_to_project(self.project_name)
            self.load_project_setting_folders_from_pf_db()
            self.stash_unit_conversion_settings()
            self.set_default_unit_conversion()
            self.load_project_folders_from_pf_db()
            loguru.logger.info("Starting PowerFactory Interface... Done.")
        except RuntimeError:
            loguru.logger.exception("Could not start PowerFactory Interface. Shutting down...")
            self.close()

    def _set_logging_handler(self, log_file_path: pathlib.Path | None) -> None:
        loguru.logger.remove(handler_id=0)
        if log_file_path is None:
            loguru.logger.add(
                sink=sys.stdout,
                colorize=True,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{file}:{line}</level> <white>{message}</white>",
                filter="powerfactory_tools",
                level=self.logging_level,
            )
        else:
            loguru.logger.add(
                sink=log_file_path,
                format="{time:YYYY-MM-DD HH:mm:ss} {level} {file}:{line} {message}",
                filter="powerfactory_tools",
                level=self.logging_level,
                enqueue=True,
            )

    def __enter__(self) -> te.Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def load_powerfactory_module_from_path(self) -> PFTypes.PowerFactoryModule:
        loguru.logger.debug("Loading PowerFactory Python module...")
        module_path = (
            self.powerfactory_path / POWERFACTORY_VERSION / "Python" / self.python_version
            if self.powerfactory_service_pack is None
            else self.powerfactory_path / POWERFACTORY_VERSION
            + f" SP{self.powerfactory_service_pack}" / "Python" / self.python_version
        )
        spec = importlib.util.spec_from_file_location(
            "powerfactory",
            module_path / "powerfactory.pyd",
        )
        if (spec is None) or (spec.loader is None):
            msg = "Could not load PowerFactory Module."
            raise RuntimeError(msg)

        pfm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pfm)
        return t.cast("PFTypes.PowerFactoryModule", pfm)

    def connect_to_app(
        self,
        pf: PFTypes.PowerFactoryModule,
    ) -> PFTypes.Application:
        """Connect to PowerFactory Application.

        Arguments:
            pf {PFTypes.PowerFactoryModule} -- the Python module contributed via the PowerFactory system installation

        Returns:
            PFTypes.Application -- the application handle (root)
        """

        loguru.logger.debug("Connecting to PowerFactory application...")
        if self.powerfactory_ini_name is None:
            command_line_arg = None
        else:
            ini_path = (
                self.powerfactory_path / POWERFACTORY_VERSION / (self.powerfactory_ini_name + ".ini")
                if self.powerfactory_service_pack is None
                else self.powerfactory_path / POWERFACTORY_VERSION
                + f" SP{self.powerfactory_service_pack}" / (self.powerfactory_ini_name + ".ini")
            )
            command_line_arg = '/ini "' + str(ini_path) + '"'
        try:
            return pf.GetApplicationExt(
                self.powerfactory_user_profile,
                self.powerfactory_user_password,
                command_line_arg,
            )
        except pf.ExitError as element:
            msg = "Could not start application."
            raise RuntimeError(msg) from element

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
