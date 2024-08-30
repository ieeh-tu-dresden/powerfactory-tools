# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2024.
# :license: BSD 3-Clause

from __future__ import annotations

import contextlib
import dataclasses
import datetime as dt
import enum
import importlib.util
import itertools
import logging
import pathlib
import sys
import time
import typing as t
from collections.abc import Sequence

import loguru
import pydantic
from psdm.base import AttributeData

from powerfactory_tools.powerfactory_error_codes import ErrorCode
from powerfactory_tools.utils.io import FileType
from powerfactory_tools.versions.pf2022.constants import PATH_SEPARATOR
from powerfactory_tools.versions.pf2022.constants import BaseUnits
from powerfactory_tools.versions.pf2022.data import PowerFactoryData
from powerfactory_tools.versions.pf2022.types import CalculationCommand
from powerfactory_tools.versions.pf2022.types import Currency
from powerfactory_tools.versions.pf2022.types import FolderType
from powerfactory_tools.versions.pf2022.types import MetricPrefix
from powerfactory_tools.versions.pf2022.types import NetworkExtendedCalcType
from powerfactory_tools.versions.pf2022.types import PFClassId
from powerfactory_tools.versions.pf2022.types import PowerFactoryTypes as PFTypes
from powerfactory_tools.versions.pf2022.types import ResultExportMode
from powerfactory_tools.versions.pf2022.types import TimeSimulationNetworkCalcType
from powerfactory_tools.versions.pf2022.types import TimeSimulationType
from powerfactory_tools.versions.pf2022.types import UnitSystem
from powerfactory_tools.versions.pf2022.types import ValidPFValue
from powerfactory_tools.versions.pf2022.utils.io import ExportHandler

if t.TYPE_CHECKING:
    from collections.abc import Iterable
    from types import TracebackType

    import typing_extensions as te

    T = t.TypeVar("T")


# allowed Python versions
class ValidPythonVersion(enum.Enum):
    VERSION_3_6 = "3.6"
    VERSION_3_7 = "3.7"
    VERSION_3_8 = "3.8"
    VERSION_3_9 = "3.9"
    VERSION_3_10 = "3.10"


POWERFACTORY_VERSION = "PowerFactory 2022"
DEFAULT_POWERFACTORY_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
DEFAULT_PYTHON_VERSION = ValidPythonVersion.VERSION_3_10

config = pydantic.ConfigDict(use_enum_values=True)


@pydantic.dataclasses.dataclass(config=config)
class UnitConversionSetting:
    filtclass: Sequence[str]
    filtvar: str
    digunit: str
    cdigexp: MetricPrefix
    userunit: str
    cuserexp: MetricPrefix
    ufacA: float  # noqa: N815
    ufacB: float  # noqa: N815


@pydantic.dataclasses.dataclass(config=config)
class ProjectUnitSetting:
    ilenunit: UnitSystem
    clenexp: MetricPrefix  # Lengths
    cspqexp: MetricPrefix  # Loads etc.
    cspqexpgen: MetricPrefix  # Generators etc.
    currency: Currency


DEFAULT_PROJECT_UNIT_SETTING = ProjectUnitSetting(
    ilenunit=UnitSystem.METRIC,
    clenexp=BaseUnits.LENGTH,
    cspqexp=BaseUnits.POWER,
    cspqexpgen=BaseUnits.POWER,
    currency=BaseUnits.CURRENCY,
)


@pydantic.dataclasses.dataclass
class PowerFactoryInterface:
    project_name: str
    powerfactory_path: pathlib.Path = DEFAULT_POWERFACTORY_PATH
    powerfactory_service_pack: int | None = None
    powerfactory_user_profile: str | None = None
    powerfactory_user_password: str | None = None
    powerfactory_ini_name: str | None = None
    python_version: ValidPythonVersion = DEFAULT_PYTHON_VERSION
    logging_level: int = logging.DEBUG
    log_file_path: pathlib.Path | None = None

    def __post_init__(self) -> None:
        try:
            self._set_logging_handler(self.log_file_path)
            loguru.logger.info("Starting PowerFactory Interface...")
            pfm = self.load_powerfactory_module_from_path()
            self.app = self.connect_to_app(pfm)
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
        if sys.version_info.major != int(self.python_version.value.split(".")[0]) or sys.version_info.minor != int(
            self.python_version.value.split(".")[1],
        ):
            msg = f"The Python version of your code environment ({sys.version_info.major}.{sys.version_info.minor}) does not match with the Python version you selected for the PowerFactory API ({self.python_version.value})."
            raise RuntimeError(msg)

        module_path = (
            self.powerfactory_path / POWERFACTORY_VERSION / "Python" / self.python_version.value
            if self.powerfactory_service_pack is None
            else self.powerfactory_path
            / (POWERFACTORY_VERSION + f" SP{self.powerfactory_service_pack}")
            / "Python"
            / self.python_version.value
        )
        spec = importlib.util.spec_from_file_location(
            "powerfactory",
            module_path / "powerfactory.pyd",
        )
        if (spec is None) or (spec.loader is None):
            msg = "Could not load PowerFactory Module."
            raise RuntimeError(msg)

        try:
            pfm = importlib.util.module_from_spec(spec)
        except ImportError as element:
            loguru.logger.exception("Could not find PowerFactory Module.")
            raise RuntimeError from element

        spec.loader.exec_module(pfm)
        return t.cast("PFTypes.PowerFactoryModule", pfm)

    def connect_to_app(self, pfm: PFTypes.PowerFactoryModule) -> PFTypes.Application:
        """Connect to PowerFactory Application.

        Arguments:
            pfm {PFTypes.PowerFactoryModule} -- the Python module contributed via the PowerFactory system installation

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
                else self.powerfactory_path
                / (POWERFACTORY_VERSION + f" SP{self.powerfactory_service_pack}")
                / (self.powerfactory_ini_name + ".ini")
            )
            command_line_arg = '/ini "' + str(ini_path) + '"'
        try:
            return pfm.GetApplicationExt(
                self.powerfactory_user_profile,
                self.powerfactory_user_password,
                command_line_arg,
            )
        except pfm.ExitError as element:
            error_code = self.resolve_pf_error_code(element)
            msg = f"Could not start application. Error code: {error_code.value} - {error_code.name}"
            loguru.logger.exception(msg)
            raise RuntimeError(msg) from element

    def load_project_setting_folders_from_pf_db(self) -> None:
        self.project_settings = self.load_project_settings_dir_from_pf()
        self.settings_dir = self.load_settings_dir_from_pf()
        self.unit_settings_dir = self.load_unit_settings_dir_from_pf()

    def load_project_folders_from_pf_db(self) -> None:
        loguru.logger.debug("Loading all project folders...")
        self.load_project_setting_folders_from_pf_db()

        self.chars_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.CHARACTERISTICS.value))
        self.grid_data_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.NETWORK_DATA.value))
        self.grid_graphs_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.DIAGRAMS.value))
        self.grid_model_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.NETWORK_MODEL.value))
        self.grid_variant_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.VARIATIONS.value))
        self.op_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.OPERATIONAL_LIBRARY.value))
        self.study_case_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.STUDY_CASES.value))
        self.scenario_dir = t.cast(
            "PFTypes.ProjectFolder",
            self.app.GetProjectFolder(FolderType.OPERATION_SCENARIOS.value),
        )
        self.templates_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.TEMPLATES.value))
        self.types_dir = t.cast(
            "PFTypes.ProjectFolder",
            self.app.GetProjectFolder(FolderType.EQUIPMENT_TYPE_LIBRARY.value),
        )

        self.ext_data_dir = self.project_settings.extDataDir
        loguru.logger.debug("Loading all project folders... Done")

    def load_settings_dir_from_pf(self) -> PFTypes.DataDir:
        loguru.logger.debug("Loading settings from PowerFactory...")
        _settings_dirs = self.elements_of(
            self.project,
            pattern="*." + PFClassId.SETTINGS_FOLDER.value,
            recursive=False,
        )
        settings_dir = self.first_of(_settings_dirs)
        if settings_dir is None:
            msg = "Could not access settings."
            raise RuntimeError(msg)

        loguru.logger.debug("Loading settings from PowerFactory... Done.")
        return settings_dir

    def load_unit_settings_dir_from_pf(self) -> PFTypes.DataDir:
        loguru.logger.debug("Loading unit settings from PowerFactory...")
        _unit_settings_dirs = self.elements_of(
            self.settings_dir,
            pattern="*." + PFClassId.SETTINGS_FOLDER_UNITS.value,
            recursive=False,
        )
        unit_settings_dir = self.first_of(_unit_settings_dirs)
        if unit_settings_dir is None:
            unit_settings_dir = self.create_object(
                name="Units",
                class_name=PFClassId.SETTINGS_FOLDER_UNITS.value,
                location=self.settings_dir,
            )
            if unit_settings_dir is None:
                msg = "Could not create unit settings directory."
                raise RuntimeError(msg)

        loguru.logger.debug("Loading unit settings from PowerFactory... Done.")
        return unit_settings_dir

    def close(self) -> None:
        loguru.logger.info("Closing PowerFactory Interface...")
        with contextlib.suppress(AttributeError):
            self.pop_unit_conversion_settings_stash()

        with contextlib.suppress(AttributeError):
            self.app.PostCommand("exit")

        loguru.logger.info("Closing PowerFactory Interface... Done.")

    def connect_to_project(self, project_name: str) -> PFTypes.Project:
        """Connect to a PowerFactory project.

        Arguments:
            project_name {str} -- the name of the project to be connected/activated

        Returns:
            PFTypes.Project -- the project handle
        """

        loguru.logger.debug(
            "Activating project {project_name} application...",
            project_name=project_name,
        )
        self.activate_project(project_name)

        project = self.app.GetActiveProject()
        if project is None:
            msg = "Could not access project."
            raise RuntimeError(msg)

        loguru.logger.debug(
            "Activating project {project_name} application... Done.",
            project_name=project_name,
        )
        return project

    @staticmethod
    def resolve_pf_error_code(error: PFTypes.PowerFactoryExitError) -> ErrorCode:
        try:
            return ErrorCode(error.code)
        except ValueError:
            return ErrorCode.UNKNOWN_ERROR_OCCURED

    def switch_study_case(self, study_case_name: str) -> PFTypes.StudyCase:
        study_case = self.study_case(study_case_name)
        if study_case is not None:
            self.activate_study_case(study_case)
        else:
            msg = f"Study case {study_case_name} does not exist."
            raise RuntimeError(msg)

        return self.study_case(study_case_name)  # type: ignore [return-value]

    def switch_scenario(self, scenario_name: str) -> None:
        scenario = self.scenario(scenario_name)
        if scenario is not None:
            self.activate_scenario(scenario)
        else:
            msg = f"Scenario {scenario_name} does not exist."
            raise RuntimeError(msg)

    def switch_grid_variant(self, grid_variant_name: str) -> None:
        # first deactivate all existing variants to prevent overriding
        for var in self.grid_variants():
            var.Deactivate()  # use the built-in function to ignore error when variant is already deactive

        variant = self.grid_variant(grid_variant_name)
        if variant is not None:
            self.activate_grid_variant(variant)
        else:
            msg = f"Grid variant {grid_variant_name} does not exist."
            raise RuntimeError(msg)

    def compile_powerfactory_data(self, grid: PFTypes.Grid) -> PowerFactoryData:
        """Read out all relevant data from PowerFactory for a given grid and store as typed dataclass PowerFactroyData.

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
            ac_voltage_sources=self.ac_voltage_sources(grid_name=grid_name, calc_relevant=True),
            shunts=self.shunts(grid_name=grid_name, calc_relevant=True),
        )

    def add_result_variables(
        self,
        *,
        result: PFTypes.Result,
        elements: Sequence[PFTypes.DataObject],
        variables: Sequence[str],
    ) -> None:
        """Adds variables to a result object for a given list of elements.

        Args:
            result (PFTypes.Result): the result object to be written to
            elements (Sequence[PFTypes.DataObject]): list of elements for which variables has to be added to the result object
            variables (Sequence[str]): list of variables (string identifiers) to be added for each element
        """
        loguru.logger.debug("Set Variables for result object {result_name} ...", result_name=result.loc_name)
        for elm in elements:
            for variable in variables:
                result.AddVariable(elm, variable)

    def write_variable_monitors_for_result(self, result: PFTypes.Result) -> None:
        """For each variable monitor in the result object, write the variable monitor as result variable.

        A result object (ElmRes) contains variable monitors (IntMon).
        In case of load flow calculation, these variable monitors can be written (kind of making visible)
        as result variables to the result itself.

        Args:
            result (PFTypes.Result): the result object to be written

        Raises:
            RuntimeError: if the writing of the variable monitors fails
        """
        loguru.logger.debug(
            f"Write all in the result object {result.loc_name} containing variable monitors (IntMon) as result variables ...",
        )
        result.InitialiseWriting()
        if result.Write():
            msg = f"Could not write result {result.loc_name}."
            raise RuntimeError(msg)
        result.FinishWriting()

        result.Flush()
        time.sleep(1)

    def activate_grid(
        self,
        grid: PFTypes.Grid,
        /,
    ) -> None:
        loguru.logger.debug("Activating grid {grid_name} application...", grid_name=grid.loc_name)
        if grid.IsCalcRelevant():
            loguru.logger.warning(
                "Grid {grid_name} is already active.",
                grid_name=grid.loc_name,
            )
        elif grid.Activate():
            msg = "Could not activate grid."
            raise RuntimeError(msg)

    def deactivate_grids(self) -> None:
        for grid in self.independent_grids(calc_relevant=True):
            self.deactivate_grid(grid)

    def deactivate_grid(
        self,
        grid: PFTypes.Grid,
        /,
    ) -> None:
        loguru.logger.debug("Deactivating grid {grid_name} application...", grid_name=grid.loc_name)
        if not grid.IsCalcRelevant():
            loguru.logger.warning(
                "Grid {grid_name} is already inactive.",
                grid_name=grid.loc_name,
            )
        elif grid.Deactivate():
            msg = "Could not deactivate grid."
            raise RuntimeError(msg)

    def activate_scenario(
        self,
        scenario: PFTypes.Scenario,
        /,
    ) -> None:
        loguru.logger.debug(
            "Activating scenario {scenario_name} application...",
            scenario_name=scenario.loc_name,
        )
        if scenario == self.app.GetActiveScenario():
            loguru.logger.warning(
                "Scenario {scenario_name} is already active.",
                scenario_name=scenario.loc_name,
            )
        elif scenario.Activate():
            msg = "Could not activate scenario."
            raise RuntimeError(msg)

    def deactivate_scenario(
        self,
        scenario: PFTypes.Scenario,
        /,
    ) -> None:
        loguru.logger.debug(
            "Deactivating scenario {scenario_name} application...",
            scenario_name=scenario.loc_name,
        )
        if scenario != self.app.GetActiveScenario():
            loguru.logger.warning(
                "Scenario {scenario_name} is already inactive.",
                scenario_name=scenario.loc_name,
            )
        elif scenario.Deactivate():
            msg = "Could not deactivate scenario."
            raise RuntimeError(msg)

    def activate_study_case(
        self,
        study_case: PFTypes.StudyCase,
        /,
    ) -> None:
        loguru.logger.debug(
            "Activating study_case {study_case_name} application...",
            study_case_name=study_case.loc_name,
        )
        if study_case == self.app.GetActiveStudyCase():
            loguru.logger.warning(
                "Study_case {study_case_name} is already inactive.",
                study_case_name=study_case.loc_name,
            )
        elif study_case.Activate():
            msg = "Could not activate case study."
            raise RuntimeError(msg)

    def deactivate_study_case(
        self,
        study_case: PFTypes.StudyCase,
        /,
    ) -> None:
        loguru.logger.debug(
            "Deactivating study_case {study_case_name} application...",
            study_case_name=study_case.loc_name,
        )
        if study_case != self.app.GetActiveStudyCase():
            loguru.logger.warning(
                "Study_case {study_case_name} is already inactive.",
                study_case_name=study_case.loc_name,
            )
        elif study_case.Deactivate():
            msg = "Could not deactivate case study."
            raise RuntimeError(msg)

    def activate_grid_variant(
        self,
        grid_variant: PFTypes.GridVariant,
        /,
    ) -> None:
        loguru.logger.debug(
            "Activating grid variant {variant_name} application...",
            variant_name=grid_variant.loc_name,
        )
        if grid_variant in self.app.GetActiveNetworkVariations():
            loguru.logger.warning(
                "Grid variant {variant_name} is already active.",
                variant_name=grid_variant.loc_name,
            )
        elif grid_variant.Activate():
            msg = "Could not activate grid variant."
            raise RuntimeError(msg)

    def deactivate_grid_variant(
        self,
        grid_variant: PFTypes.GridVariant,
        /,
    ) -> None:
        loguru.logger.debug(
            "Deactivating grid variant {variant_name} application...",
            variant_name=grid_variant.loc_name,
        )
        if grid_variant not in self.app.GetActiveNetworkVariations():
            loguru.logger.warning(
                "Grid variant {variant_name} is already inactive.",
                variant_name=grid_variant.loc_name,
            )
        elif grid_variant.Deactivate():
            msg = "Could not deactivate grid variant."
            raise RuntimeError(msg)

    def deactivate_grid_variants(self) -> None:
        active_variants = self.app.GetActiveNetworkVariations()
        for variant in active_variants:
            self.deactivate_grid_variant(variant)

    def set_default_unit_conversion(self) -> None:
        loguru.logger.debug("Applying exporter default unit conversion settings...")
        self.project_settings.ilenunit = DEFAULT_PROJECT_UNIT_SETTING.ilenunit
        self.project_settings.clenexp = DEFAULT_PROJECT_UNIT_SETTING.clenexp
        self.project_settings.cspqexp = DEFAULT_PROJECT_UNIT_SETTING.cspqexp
        self.project_settings.cspqexpgen = DEFAULT_PROJECT_UNIT_SETTING.cspqexpgen
        self.project_settings.currency = DEFAULT_PROJECT_UNIT_SETTING.currency
        for cls, data in BaseUnits.UNITCONVERSIONS.items():
            for unit, base_exp, exp in data:
                name = f"{cls}-{unit}"
                uc = UnitConversionSetting(
                    filtclass=[cls],
                    filtvar="*",
                    digunit=unit,
                    cdigexp=base_exp,
                    userunit="",
                    cuserexp=exp,
                    ufacA=1,
                    ufacB=0,
                )
                self.create_unit_conversion_setting(name, uc)

        self.reset_project()
        loguru.logger.debug("Applying exporter default unit conversion settings... Done.")

    def stash_unit_conversion_settings(self) -> None:
        loguru.logger.debug("Stashing PowerFactory default unit conversion settings...")
        self.project_unit_setting = ProjectUnitSetting(
            ilenunit=UnitSystem(self.project_settings.ilenunit),
            clenexp=MetricPrefix(self.project_settings.clenexp),
            cspqexp=MetricPrefix(self.project_settings.cspqexp),
            cspqexpgen=MetricPrefix(self.project_settings.cspqexpgen),
            currency=Currency(self.project_settings.currency),
        )
        unit_conversion_settings = self.unit_conversion_settings()
        self.unit_conv_settings: dict[str, UnitConversionSetting] = {}
        for uc in unit_conversion_settings:
            ucs = UnitConversionSetting(
                filtclass=uc.filtclass,
                filtvar=uc.filtvar,
                digunit=uc.digunit,
                cdigexp=uc.cdigexp,
                userunit=uc.userunit,
                cuserexp=uc.cuserexp,
                ufacA=uc.ufacA,
                ufacB=uc.ufacB,
            )
            self.unit_conv_settings[uc.loc_name] = ucs

        self.delete_unit_conversion_settings()
        loguru.logger.debug("Stashing PowerFactory default unit conversion settings... Done.")

    def pop_unit_conversion_settings_stash(self) -> None:
        loguru.logger.debug("Applying PowerFactory default unit conversion settings...")
        self.project_settings.ilenunit = self.project_unit_setting.ilenunit
        self.project_settings.clenexp = self.project_unit_setting.clenexp
        self.project_settings.cspqexp = self.project_unit_setting.cspqexp
        self.project_settings.cspqexpgen = self.project_unit_setting.cspqexpgen
        self.project_settings.currency = self.project_unit_setting.currency
        self.delete_unit_conversion_settings()
        for name, uc in self.unit_conv_settings.items():
            self.create_unit_conversion_setting(name, uc)

        self.reset_project()
        loguru.logger.debug("Applying PowerFactory default unit conversion settings... Done.")

    def load_project_settings_dir_from_pf(self) -> PFTypes.ProjectSettings:
        loguru.logger.debug("Loading project settings dir...")
        project_settings = self.project.pPrjSettings
        if project_settings is None:
            msg = "Could not access project settings."
            raise RuntimeError(msg)

        loguru.logger.debug("Loading project settings dir... Done.")
        return project_settings

    def reset_project(self) -> None:
        loguru.logger.debug("Resetting current project...")
        self.deactivate_project()
        self.activate_project(self.project_name)
        loguru.logger.debug("Resetting current project... Done.")

    def activate_project(self, name: str) -> None:
        loguru.logger.debug("Activating project {name}...", name=name)
        if self.app.ActivateProject(name + ".IntPrj"):
            msg = "Could not activate project."
            raise RuntimeError(msg)

    def deactivate_project(self) -> None:
        loguru.logger.debug("Deactivating current project {name}...")
        if self.project.Deactivate():
            msg = "Could not deactivate project."
            raise RuntimeError(msg)

    def variable_monitor(
        self,
        name: str = "*",
        /,
        *,
        result_name: str = "*",
    ) -> PFTypes.VariableMonitor | None:
        return self.first_of(self.variable_monitors(name, result_name=result_name))

    def variable_monitors(
        self,
        name: str = "*",
        /,
        *,
        result_name: str = "*",
    ) -> Sequence[PFTypes.VariableMonitor]:
        elements = self.result_elements(
            class_name=PFClassId.VARIABLE_MONITOR.value,
            name=name,
            result_name=result_name,
        )
        return [t.cast("PFTypes.VariableMonitor", element) for element in elements]

    def result(
        self,
        name: str = "*",
        /,
        *,
        study_case_name: str = "*",
    ) -> PFTypes.Result | None:
        return self.first_of(self.results(name, study_case_name=study_case_name))

    def results(
        self,
        name: str = "*",
        /,
        *,
        study_case_name: str = "*",
    ) -> Sequence[PFTypes.Result]:
        act_sc = self.app.GetActiveStudyCase()
        if study_case_name == "*" and act_sc is not None:
            study_case_name = act_sc.loc_name
        elements = self.study_case_elements(
            class_name=PFClassId.RESULT.value,
            name=name,
            study_case_name=study_case_name,
        )
        return [t.cast("PFTypes.Result", element) for element in elements]

    def result_export_command(
        self,
        name: str = "*",
        /,
        *,
        study_case_name: str = "*",
    ) -> PFTypes.CommandResultExport | None:
        return self.first_of(self.result_export_commands(name, study_case_name=study_case_name))

    def result_export_commands(
        self,
        name: str = "*",
        /,
        *,
        study_case_name: str = "*",
    ) -> Sequence[PFTypes.CommandResultExport]:
        elements = self.study_case_elements(
            class_name=CalculationCommand.RESULT_EXPORT.value,
            name=name,
            study_case_name=study_case_name,
        )
        return [t.cast("PFTypes.CommandResultExport", element) for element in elements]

    def study_case(
        self,
        name: str = "*",
        /,
        *,
        only_active: bool = False,
    ) -> PFTypes.StudyCase | None:
        if only_active:
            return self.app.GetActiveStudyCase()

        return self.first_of(self.study_cases(name))

    def study_cases(
        self,
        name: str = "*",
        /,
    ) -> Sequence[PFTypes.StudyCase]:
        elements = self.elements_of(self.study_case_dir, pattern=name + "." + PFClassId.STUDY_CASE.value)
        return [t.cast("PFTypes.StudyCase", element) for element in elements]

    def scenario(
        self,
        name: str = "*",
        /,
        *,
        only_active: bool = False,
    ) -> PFTypes.Scenario | None:
        if only_active:
            return self.app.GetActiveScenario()

        return self.first_of(self.scenarios(name))

    def scenarios(
        self,
        name: str = "*",
        /,
    ) -> Sequence[PFTypes.Scenario]:
        elements = self.elements_of(self.scenario_dir, pattern=name)
        return [t.cast("PFTypes.Scenario", element) for element in elements]

    def grid_variant(
        self,
        name: str = "*",
        /,
        *,
        only_active: bool = False,
    ) -> PFTypes.GridVariant | None:
        return self.first_of(self.grid_variants(name, only_active=only_active))

    def grid_variants(
        self,
        name: str = "*",
        /,
        *,
        only_active: bool = False,
    ) -> Sequence[PFTypes.GridVariant]:
        elements = self.elements_of(self.grid_variant_dir, pattern=name + "." + PFClassId.VARIANT.value)

        if only_active:
            active_variants = self.app.GetActiveNetworkVariations()
            return [variant for variant in active_variants if variant in elements]
        return [t.cast("PFTypes.GridVariant", element) for element in elements]

    def grid_variant_stage(
        self,
        name: str = "*",
        /,
        *,
        grid_variant: PFTypes.GridVariant | None = None,
        folder: PFTypes.DataObject | None = None,
        only_active: bool = False,
    ) -> PFTypes.GridVariantStage | None:
        return self.first_of(
            self.grid_variant_stages(
                name,
                grid_variant=grid_variant,
                folder=folder,
                only_active=only_active,
            ),
        )

    def grid_variant_stages(
        self,
        name: str = "*",
        /,
        *,
        grid_variant: PFTypes.GridVariant | None = None,
        folder: PFTypes.DataObject | None = None,
        only_active: bool = False,
    ) -> Sequence[PFTypes.GridVariantStage]:
        """Returns grid variant stages specified by affiliation and relenvance.

        Within the root 'grid_variant_dir', subfolders can exist.
        Thus, grid variants with the same name can be stored in different subfolders.
        Grid variant stages with the same name can be exist in different grid variants.
        Remark: If you want to get stages of this unique grid variant, just specify only grid_variant and no folder.

        Arguments:
            name {str} -- Name of requested grid variant stage (default: {"*"})

        Keyword Arguments:
            grid_variant {PFTypes.GridVariant | None} -- The parent grid variant related to (default: {None})
            folder {PFTypes.DataObject | None} -- The parent grid variant folder to search (default: {None})
            only_active {bool} -- Flag to return only currently ative grid variant stages (default: {False})

        Returns:
            {Sequence[PFTypes.GridVariantStage]} -- A List of existing grid variant stages
        """
        is_folder_none_and_variant_not_none = False
        if folder is None:
            folder = self.grid_variant_dir
            if grid_variant is not None:
                is_folder_none_and_variant_not_none = True

        if grid_variant is None:
            elements = self.elements_of(folder, pattern=name)
        elif is_folder_none_and_variant_not_none:
            # check if unique grid variant is requested be used as parent for the stages or not
            elements = self.elements_of(grid_variant, pattern=name)
        else:
            # get all variants within folder with the requested variant name
            relevant_variants = self.elements_of(folder, pattern=grid_variant.loc_name)
            # get all stages for all relevant_variants with the requested stage name
            elements = []
            for variant in relevant_variants:
                elements += self.elements_of(variant, pattern=name)

        if only_active:
            active_stages = self.app.GetActiveStages(folder)
            return [stage for stage in active_stages if stage in elements]

        return [t.cast("PFTypes.GridVariantStage", element) for element in elements]

    def template(self, name: str = "*") -> PFTypes.Template | None:
        return self.first_of(self.templates(name=name))

    def templates(self, name: str = "*") -> Sequence[PFTypes.Template]:
        elements = self.elements_of(self.templates_dir, pattern=name + "." + PFClassId.TEMPLATE.value)
        return [t.cast("PFTypes.Template", element) for element in elements]

    def dsl_model(
        self,
        name: str = "*",
        /,
        *,
        location: PFTypes.Grid | PFTypes.CompoundModel | None = None,
    ) -> PFTypes.DslModel | None:
        return self.first_of(self.dsl_models(name, location=location))

    def dsl_models(
        self,
        name: str = "*",
        /,
        *,
        location: PFTypes.Grid | PFTypes.CompoundModel | None = None,
    ) -> Sequence[PFTypes.DslModel]:
        if location is None:
            location = self.grid_data_dir
        elements = self.elements_of(location, pattern=name + "." + PFClassId.DSL_MODEL.value)
        return [t.cast("PFTypes.DslModel", element) for element in elements]

    def line_type(
        self,
        name: str = "*",
        /,
    ) -> PFTypes.LineType | None:
        return self.first_of(self.line_types(name))

    def line_types(
        self,
        name: str = "*",
        /,
    ) -> Sequence[PFTypes.LineType]:
        elements = self.equipment_type_elements(PFClassId.LINE_TYPE.value, name)
        return [t.cast("PFTypes.LineType", element) for element in elements]

    def load_type(
        self,
        name: str = "*",
        /,
    ) -> PFTypes.DataObject | None:
        return self.first_of(self.load_types(name))

    def load_types(
        self,
        name: str = "*",
        /,
    ) -> Sequence[PFTypes.DataObject]:
        elements = self.equipment_type_elements(PFClassId.LOAD_TYPE_GENERAL.value, name)
        return [t.cast("PFTypes.LoadType", element) for element in elements]

    def transformer_2w_type(
        self,
        name: str = "*",
        /,
    ) -> PFTypes.Transformer2WType | None:
        return self.first_of(self.transformer_2w_types(name))

    def transformer_2w_types(
        self,
        name: str = "*",
        /,
    ) -> Sequence[PFTypes.Transformer2WType]:
        elements = self.equipment_type_elements(PFClassId.TRANSFORMER_2W_TYPE.value, name)
        return [t.cast("PFTypes.Transformer2WType", element) for element in elements]

    def harmonic_source_type(
        self,
        name: str = "*",
        /,
    ) -> PFTypes.SourceTypeHarmonicCurrent | None:
        return self.first_of(self.harmonic_source_types(name))

    def harmonic_source_types(
        self,
        name: str = "*",
        /,
    ) -> Sequence[PFTypes.SourceTypeHarmonicCurrent]:
        elements = self.equipment_type_elements(PFClassId.SOURCE_TYPE_HARMONIC_CURRENT.value, name)
        return [t.cast("PFTypes.SourceTypeHarmonicCurrent", element) for element in elements]

    def area(
        self,
        name: str = "*",
        /,
    ) -> PFTypes.DataObject | None:
        return self.first_of(self.areas(name))

    def areas(
        self,
        name: str = "*",
        /,
    ) -> Sequence[PFTypes.DataObject]:
        return self.grid_model_elements(class_name=PFClassId.AREA.value, name=name)

    def zone(
        self,
        name: str = "*",
        /,
    ) -> PFTypes.DataObject | None:
        return self.first_of(self.zones(name))

    def zones(
        self,
        name: str = "*",
        /,
    ) -> Sequence[PFTypes.DataObject]:
        return self.grid_model_elements(class_name=PFClassId.ZONE.value, name=name)

    def grid_diagram(
        self,
        name: str = "*",
        /,
    ) -> PFTypes.GridDiagram | None:
        return self.first_of(self.grid_diagrams(name))

    def grid_diagrams(
        self,
        name: str = "*",
        /,
    ) -> Sequence[PFTypes.GridDiagram]:
        elements = self.grid_model_elements(class_name=PFClassId.GRID_GRAPHIC.value, name=name)
        return [t.cast("PFTypes.GridDiagram", element) for element in elements]

    def external_grid(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.ExternalGrid | None:
        return self.first_of(self.external_grids(name, grid_name=grid_name))

    def external_grids(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.ExternalGrid]:
        elements = self.grid_elements(
            class_name=PFClassId.EXTERNAL_GRID.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.ExternalGrid", element) for element in elements]

    def terminal(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.Terminal | None:
        return self.first_of(self.terminals(name, grid_name=grid_name))

    def terminals(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.Terminal]:
        elements = self.grid_elements(
            class_name=PFClassId.TERMINAL.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.Terminal", element) for element in elements]

    def cubicle(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.StationCubicle | None:
        return self.first_of(self.cubicles(name, grid_name=grid_name))

    def cubicles(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.StationCubicle]:
        elements = self.grid_elements(
            class_name=PFClassId.CUBICLE.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.StationCubicle", element) for element in elements]

    def coupler(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.Coupler | None:
        return self.first_of(self.couplers(name, grid_name=grid_name))

    def couplers(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.Coupler]:
        elements = self.grid_elements(
            class_name=PFClassId.COUPLER.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.Coupler", element) for element in elements]

    def switch(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.Switch | None:
        return self.first_of(self.switches(name, grid_name=grid_name))

    def switches(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.Switch]:
        elements = self.grid_elements(
            class_name=PFClassId.SWITCH.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.Switch", element) for element in elements]

    def bfuse(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.BFuse | None:
        return self.first_of(self.bfuses(name, grid_name=grid_name))

    def bfuses(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.BFuse]:
        elements = self.grid_elements(
            class_name=PFClassId.FUSE.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        fuses = [t.cast("PFTypes.Fuse", element) for element in elements]
        bfuses = [fuse for fuse in fuses if self.is_bfuse(fuse)]
        return [t.cast("PFTypes.BFuse", fuse) for fuse in bfuses]

    def efuse(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.EFuse | None:
        return self.first_of(self.efuses(name, grid_name=grid_name))

    def efuses(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.EFuse]:
        elements = self.grid_elements(
            class_name=PFClassId.FUSE.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        fuses = [t.cast("PFTypes.Fuse", element) for element in elements]
        efuses = [fuse for fuse in fuses if self.is_efuse(fuse)]
        return [t.cast("PFTypes.EFuse", fuse) for fuse in efuses]

    def line(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.Line | None:
        return self.first_of(self.lines(name, grid_name=grid_name))

    def lines(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.Line]:
        elements = self.grid_elements(
            class_name=PFClassId.LINE.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.Line", element) for element in elements]

    def shunt(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.Shunt | None:
        return self.first_of(self.shunts(name, grid_name=grid_name))

    def shunts(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.Shunt]:
        elements = self.grid_elements(
            class_name=PFClassId.SHUNT.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.Shunt", element) for element in elements]

    def transformer_2w(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.Transformer2W | None:
        return self.first_of(self.transformers_2w(name, grid_name=grid_name))

    def transformers_2w(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.Transformer2W]:
        elements = self.grid_elements(
            class_name=PFClassId.TRANSFORMER_2W.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.Transformer2W", element) for element in elements]

    def transformer_3w(
        self,
        name: str = "*",
        grid_name: str = "*",
    ) -> PFTypes.Transformer3W | None:
        return self.first_of(self.transformers_3w(name, grid_name=grid_name))

    def transformers_3w(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.Transformer3W]:
        elements = self.grid_elements(
            class_name=PFClassId.TRANSFORMER_3W.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.Transformer3W", element) for element in elements]

    def load(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.Load | None:
        return self.first_of(self.loads(name, grid_name=grid_name))

    def loads(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.Load]:
        elements = self.grid_elements(
            class_name=PFClassId.LOAD.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.Load", element) for element in elements]

    def generator(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
    ) -> PFTypes.Generator | None:
        return self.first_of(self.generators(name, grid_name=grid_name))

    def generators(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.Generator]:
        elements = self.grid_elements(
            class_name=PFClassId.GENERATOR.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.Generator", element) for element in elements]

    def pv_system(
        self,
        name: str = "*",
        grid_name: str = "*",
    ) -> PFTypes.PVSystem | None:
        return self.first_of(self.pv_systems(name, grid_name=grid_name))

    def pv_systems(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.PVSystem]:
        elements = self.grid_elements(
            class_name=PFClassId.PVSYSTEM.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.PVSystem", element) for element in elements]

    def ac_current_source(
        self,
        name: str = "*",
        grid_name: str = "*",
    ) -> PFTypes.AcCurrentSource | None:
        return self.first_of(self.ac_current_sources(name, grid_name=grid_name))

    def ac_current_sources(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.AcCurrentSource]:
        elements = self.grid_elements(
            class_name=PFClassId.CURRENT_SOURCE_AC.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.AcCurrentSource", element) for element in elements]

    def ac_voltage_source(
        self,
        name: str = "*",
        grid_name: str = "*",
    ) -> PFTypes.AcVoltageSource | None:
        return self.first_of(self.ac_voltage_sources(name, grid_name=grid_name))

    def ac_voltage_sources(
        self,
        name: str = "*",
        /,
        *,
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.AcVoltageSource]:
        elements = self.grid_elements(
            class_name=PFClassId.VOLTAGE_SOURCE_AC.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
            include_out_of_service=include_out_of_service,
        )
        return [t.cast("PFTypes.AcVoltageSource", element) for element in elements]

    def grid(
        self,
        name: str = "*",
        /,
    ) -> PFTypes.Grid | None:
        return self.first_of(self.grids(name))

    def grids(
        self,
        name: str = "*",
        /,
        *,
        calc_relevant: bool = False,
    ) -> Sequence[PFTypes.Grid]:
        elements = self.grid_model_elements(class_name=PFClassId.GRID.value, name=name, calc_relevant=calc_relevant)
        return [t.cast("PFTypes.Grid", element) for element in elements]

    def independent_grids(
        self,
        name: str = "*",
        /,
        *,
        calc_relevant: bool = False,
    ) -> Sequence[PFTypes.Grid]:
        """Gets all grid entities except the superior summary grid stored at the study case level.

        Keyword Arguments:
            name -- Name of grid to be accessed (default: {"*"})
            calc_relevant -- Flag, if only calc relevant (active) grids should be accessed (default: {False})

        Returns:
            Sequence of grids without superior summary grid entitiy.
        """
        study_case = self.study_case(only_active=True)
        if study_case is not None:
            superior_grids = self.elements_of(study_case, pattern="*." + PFClassId.GRID.value)
            return list(filter(lambda g: g not in superior_grids, self.grids(name, calc_relevant=calc_relevant)))

        return []

    def grid_elements(
        self,
        *,
        class_name: str,
        name: str = "*",
        grid_name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.DataObject]:
        if calc_relevant:
            calc_elements = self.app.GetCalcRelevantObjects(name + "." + class_name, include_out_of_service)
            grid_elements = self._grid_elements(class_name=class_name, name=name, grid_name=grid_name)
            return list(filter(lambda e: e in grid_elements, calc_elements))

        return self._grid_elements(class_name=class_name, name=name, grid_name=grid_name)

    def _grid_elements(
        self,
        *,
        class_name: str,
        name: str = "*",
        grid_name: str = "*",
    ) -> Sequence[PFTypes.DataObject]:
        rv = [self.elements_of(g, pattern=name + "." + class_name) for g in self.grids(grid_name)]
        return self.list_from_sequences(*rv)

    def grid_model_elements(
        self,
        *,
        class_name: str,
        name: str = "*",
        calc_relevant: bool = False,
        include_out_of_service: bool = True,
    ) -> Sequence[PFTypes.DataObject]:
        if calc_relevant:
            return self.app.GetCalcRelevantObjects(name + "." + class_name, include_out_of_service)

        return self.elements_of(self.grid_model_dir, pattern=name + "." + class_name)

    def equipment_type_elements(
        self,
        class_name: str,
        name: str = "*",
    ) -> Sequence[PFTypes.DataObject]:
        return self.elements_of(self.types_dir, pattern=name + "." + class_name)

    def study_case_element(
        self,
        *,
        class_name: str,
        name: str = "*",
        study_case_name: str = "*",
    ) -> PFTypes.DataObject | None:
        elements = self.study_case_elements(class_name=class_name, name=name, study_case_name=study_case_name)
        if len(elements) == 0:
            return None

        if len(elements) > 1:
            loguru.logger.warning("Found more then one element, returning only the first one.")

        return elements[0]

    def study_case_elements(
        self,
        *,
        class_name: str,
        name: str = "*",
        study_case_name: str = "*",
    ) -> Sequence[PFTypes.DataObject]:
        rv = [self.elements_of(sc, pattern=name + "." + class_name) for sc in self.study_cases(study_case_name)]
        return self.list_from_sequences(*rv)

    def result_element(
        self,
        *,
        class_name: str,
        name: str = "*",
        result_name: str = "*",
    ) -> PFTypes.DataObject | None:
        elements = self.result_elements(class_name=class_name, name=name, result_name=result_name)
        if len(elements) == 0:
            return None

        if len(elements) > 1:
            loguru.logger.warning("Found more then one element, returning only the first one.")

        return elements[0]

    def result_elements(
        self,
        *,
        class_name: str,
        name: str = "*",
        result_name: str = "*",
    ) -> Sequence[PFTypes.DataObject]:
        rv = [self.elements_of(res, pattern=name + "." + class_name) for res in self.results(result_name)]
        return self.list_from_sequences(*rv)

    def first_of(
        self,
        elements: Sequence[T],
        /,
    ) -> T | None:
        if len(elements) == 0:
            return None

        if len(elements) > 1:
            loguru.logger.warning("Found more then one element, returning only the first one.")

        return elements[0]

    def elements_of(
        self,
        element: PFTypes.DataObject,
        /,
        *,
        pattern: str = "*",
        recursive: bool = True,
    ) -> Sequence[PFTypes.DataObject]:
        return element.GetContents(pattern, recursive)

    def create_unit_conversion_setting(
        self,
        name: str,
        uc: UnitConversionSetting,
    ) -> PFTypes.UnitConversionSetting | None:
        if self.unit_settings_dir is not None:
            data = dataclasses.asdict(uc)
            element = self.create_object(
                name=name,
                class_name=PFClassId.UNIT_VARIABLE.value,
                location=self.unit_settings_dir,
                data=data,
            )
            return t.cast("PFTypes.UnitConversionSetting", element) if element is not None else None

        return None

    def delete_unit_conversion_settings(self) -> None:
        ucs = self.unit_conversion_settings()
        for uc in ucs:
            self.delete_object(uc)

    def unit_conversion_settings(self) -> Sequence[PFTypes.UnitConversionSetting]:
        if self.unit_settings_dir is not None:
            elements = self.elements_of(self.unit_settings_dir, pattern="*." + PFClassId.UNIT_VARIABLE.value)
            return [t.cast("PFTypes.UnitConversionSetting", element) for element in elements]

        return []

    def create_variable_monitor(
        self,
        *,
        element: PFTypes.DataObject,
        result: PFTypes.Result,
        variables: Sequence[str],
        data: dict[str, ValidPFValue] | None = None,
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.VariableMonitor | None:
        """Creates a variable monitoring object within a result object.

         Keyword Arguments:
            element {PFTypes.DataObject} -- the element for which variable monitors are to be created
            result {PFTypes.Result} -- the related result object the variable monitor is to be created within
            variables {Sequence[str]} -- a list of variable names to be monitored
            data {dict[str, ValidPFValue] | None} -- a dictionary with name-value-pairs of object attributes (default: {None}).
            force {bool} -- flag to force the creation, nonetheless if variant already exits (default: {False})
            update {bool} -- Flag to update object attributes if objects already exists (default: {True})

        Returns:
            {PFTypes.VariableMonitor | None -- the created variable monitoring object
        """
        loguru.logger.debug("Create variable monitor object {name} ...", name=element.loc_name)
        obj = self.create_object(
            name=element.loc_name,
            class_name=PFClassId.VARIABLE_MONITOR.value,
            location=result,
            data=data,
            force=force,
            update=update,
        )
        variable_monitor = t.cast("PFTypes.VariableMonitor", obj) if obj is not None else None

        if variable_monitor is not None:
            # specify the element to monitor
            variable_monitor.obj_id = element
            # add variables to monitor
            for var in variables:
                variable_monitor.AddVar(var)
        return variable_monitor

    def create_result(
        self,
        *,
        name: str,
        study_case: PFTypes.StudyCase,
        data: dict[str, ValidPFValue] | None = None,
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.Result | None:
        """Creates a result object within a study case.

         Keyword Arguments:
            name {str} -- the name of the result
            study_case {PFTypes.StudyCase} -- the related study case the result is to be created within (default: {None})
            data {dict[str, ValidPFValue] | None} -- a dictionary with name-value-pairs of object attributes (default: {None}).
            force {bool} -- flag to force the creation, nonetheless if variant already exits (default: {False})
            update {bool} -- Flag to update object attributes if objects already exists (default: {True})

        Returns:
            {PFTypes.Result | None -- the created result object
        """
        loguru.logger.debug("Create result object {name} ...", name=name)
        element = self.create_object(
            name=name,
            class_name=PFClassId.RESULT.value,
            location=study_case,
            data=data,
            force=force,
            update=update,
        )
        return t.cast("PFTypes.Result", element) if element is not None else None

    def create_scenario(
        self,
        *,
        name: str,
        location: PFTypes.DataObject | None = None,
        data: dict[str, ValidPFValue] | None = None,
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.Scenario | None:
        """Creates a grid scenario.

         Keyword Arguments:
            name {str} -- the name of the scenario
            location {PFTypes.DataObject | None} -- the folder within which the scenario should be created (default: {None}).
            data {dict[str, ValidPFValue] | None} -- a dictionary with name-value-pairs of object attributes (default: {None}).
            force {bool} -- flag to force the creation, nonetheless if scenario already exits (default: {False}).
            update {bool} -- flag to update object attributes if objects already exists (default: {True}).

        Returns:
            {PFTypes.Scenario | None -- the created scenario object
        """
        loguru.logger.debug("Create scenario object {name} ...", name=name)

        if location is None:
            location = self.scenario_dir
        element = self.create_object(
            name=name,
            class_name=PFClassId.SCENARIO.value,
            location=location,
            data=data,
            force=force,
            update=update,
        )
        return t.cast("PFTypes.Scenario", element) if element is not None else None

    def create_study_case(
        self,
        *,
        name: str,
        grids: Sequence[PFTypes.Grid] | None = None,
        grid_variants: Sequence[PFTypes.GridVariant] | None = None,
        scenario: PFTypes.Scenario | None = None,
        target_datetime: dt.datetime | None = None,
        location: PFTypes.DataObject | None = None,
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.StudyCase | None:
        """Create a study case with optional related grids, variants and scenarios.

        Keyword Arguments:
            name {str} -- the name of the new study case
            grids {Sequence[PFTypes.Grid] | None} -- preset of grids to be related to the study case (default: {None})
            grid_variants {Sequence[PFTypes.GridVariant] | None} -- preset of grid variants to be related to / activated in the study case (default: {None})
            scenario {PFTypes.Scenario | None} -- preset scenario to be related to the study case (default: {None})
            target_datetime {datetime | None}-- datetime basis to be related to the study case (default: {None})
            location {PFTypes.DataObject | None} -- the folder where the study case should be created in (default: {None})
            force {bool} -- flag to force the creation, nonetheless if variant already exits (default: {False})
            update {bool} -- Flag to update object attributes if objects already exists (default: {True})

        Returns:
            {PFTypes.StudyCase} -- the created study case
        """
        if location is None:
            location = self.study_case_dir

        loguru.logger.debug("Create study case {name} ...", name=name)
        study_case = self.create_object(
            name=name,
            class_name=PFClassId.STUDY_CASE.value,
            location=location,
            force=force,
            update=update,
        )
        if study_case is None:
            loguru.logger.warning(
                "{object_name}.{class_name} could not be created.",
                object_name=name,
                class_name=PFClassId.STUDY_CASE.value,
            )
            return None

        study_case = t.cast("PFTypes.StudyCase", study_case)

        if target_datetime is not None:
            target_timestamp = int(time.mktime(target_datetime.timetuple()))
            study_case.SetStudyTime(target_timestamp)
            # check if datetime was successfully set
            set_timestamp = study_case.iStudyTime
            if set_timestamp != target_timestamp:
                loguru.logger.warning("Requested study time could not be set.")
                return None

        # Switch to the newly created study case to activate grids, variants and scenarios
        current_study_case = self.app.GetActiveStudyCase()
        self.switch_study_case(study_case.loc_name)

        if grids is not None:
            for grid in grids:
                self.activate_grid(grid)

        if grid_variants is not None:
            for grid_variant in grid_variants:
                self.activate_grid_variant(grid_variant)

        if scenario is not None:
            self.activate_scenario(scenario)

        # Switch back to the previous study case
        if current_study_case is not None:
            self.switch_study_case(current_study_case.loc_name)
        else:
            self.deactivate_study_case(study_case)

        return study_case

    def create_grid_variant(
        self,
        *,
        name: str,
        stage_name: str = "initial stage",
        location: PFTypes.DataObject | None = None,
        data: dict[str, ValidPFValue] | None = None,
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.GridVariant | None:
        """Create a grid variant with related variant stage.

        Keyword Arguments:
            name {str} -- The name of the grid variant to be created.
            stage_name {str} -- The name of the variant stage related to the grid variant; at least one active stage is necessary (default: {"initial stage"}).
            location {PFTypes.DataObject | None} -- The folder within which the variant should be created (default: {None}).
            data {dict[str, ValidPFValue] | None} -- A dictionary with name-value-pairs of object attributes (default: {None}).
            force {bool} -- Flag to force the creation, nonetheless if variant already exits (default: {False}).
            update {bool} -- Flag to update object attributes if objects already exists (default: {True}).

        Returns:
            {PFTypes.GridVariant | None} -- the created grid variant
        """
        if location is None:
            location = self.grid_variant_dir

        loguru.logger.debug("Create grid variant {name} ...", name=name)
        variant = self.create_object(
            name=name,
            class_name=PFClassId.VARIANT.value,
            location=location,
            data=data,
            force=force,
            update=update,
        )
        if variant is None:
            loguru.logger.warning(
                "{object_name}.{class_name} could not be created.",
                object_name=name,
                class_name=PFClassId.VARIANT.value,
            )
            return None
        variant = t.cast("PFTypes.GridVariant", variant)

        # create initial stage
        stage = self.create_grid_variant_stage(
            name=stage_name,
            grid_variant=variant,
            data=data,
            force=force,
            update=update,
        )

        return variant if stage is not None else None

    def create_grid_variant_stage(
        self,
        *,
        name: str,
        grid_variant: PFTypes.GridVariant,
        data: dict[str, ValidPFValue] | None = None,
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.GridVariantStage | None:
        """Create a grid variant stage as child of the given grid variant.

        Keyword Arguments:
            name {str} -- The given name of the grid variant stage.
            grid_variant {PFTypes.GridVariant} -- The name of the grid variant.
            data {dict[str, ValidPFValue] | None} -- A dictionary with name-value-pairs of object attributes (default: {None}).
            force {bool} -- Flag to force the creation nonetheless if stage already exits (default: {False}).
            update {bool} -- Flag to update object attributes if objects already exists (default: {True}).

        Returns:
            {PFTypes.GridVariantStage | None} -- the created grid variant stage
        """
        # try to catch possibly existing variant stage
        stage = self.grid_variant_stage(name, grid_variant=grid_variant)

        if stage is not None:
            # if stage already exists and creation is forced, override existing stage
            elm = self.create_object(
                name=name,
                class_name=PFClassId.VARIANT_STAGE.value,
                location=grid_variant,
                data=data,
                force=force,
                update=update,
            )
        else:
            # if stage does not exist, try to create a new one
            activation_time = 0 if data is None else t.cast("int", data.get("tAcTime", 0))
            error = grid_variant.NewStage(name, activation_time, 1)
            if error:
                loguru.logger.warning(
                    "{object_name}.{class_name} could not be created.",
                    object_name=name,
                    class_name=PFClassId.VARIANT_STAGE.value,
                )
                return None
            elm = self.grid_variant_stage(name, grid_variant=grid_variant)

        return t.cast("PFTypes.GridVariantStage", elm) if elm is not None else None

    def create_folder(
        self,
        *,
        name: str,
        location: PFTypes.ProjectFolder | PFTypes.StudyCase | PFTypes.GridDiagram,
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.DataObject | None:
        """Create simple folder within given directory.

        Keyword Arguments
            name {str} -- The folder name.
            location {PFTypes.ProjectFolder | PFTypes.StudyCase | PFTypes.GridDiagram} -- The directory where the folder should be created.
            force {bool} -- Flag to force creation nonetheless if already exists (default: {False}).
            update {bool} -- Flag to update object attributes if objects already exists (default: {True}).

        Returns:
            {PFTypes.DataObject | None} - the created folder
        """
        loguru.logger.debug("Create folder {name} in {location} ...", name=name, location=location.loc_name)
        return self.create_object(
            name=name,
            class_name=PFClassId.FOLDER.value,
            location=location,
            force=force,
            update=update,
        )

    def create_object(
        self,
        *,
        name: str,
        class_name: str,
        location: PFTypes.DataObject,
        data: dict[str, ValidPFValue] | None = None,
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.DataObject | None:
        """Create an object at a given location.

        Create an object at a specified location with attributes defined in a data dictionary.
        Use the flags force and update to handle the action if an object with the choosen naem already exists.

        Keyword Arguments:
            name {str} -- The name of the grid variant to be created.
            class_name {str} -- The PowerFactory class name string for the type of object.
            location {PFTypes.DataObject} -- The directory the object should be created in.
            data {dict[str, ValidPFValue] | None} -- A dictionary with name-value-pairs of object attributes (default: {None}).
            force {bool} -- Flag to force the creation of the object nonetheless if it already exits (default: {False}).
            update {bool} -- Flag to update object attributes if objects already exists (default: {True}).

        Returns:
            {PFTypes.DataObject | None} -- the created object
        """

        _elements = self.elements_of(location, pattern=f"{name}.{class_name}")
        element = self.first_of(_elements)
        if element is not None and not force:
            if not update:
                loguru.logger.warning(
                    "{object_name}.{class_name} already exists. Use force=True to create it anyway or update=True to update it.",
                    object_name=name,
                    class_name=class_name,
                )
        else:
            element = location.CreateObject(class_name, name)
            update = True

        if element is not None and data is not None and update:
            return self.update_object(element, data=data)
        # Update project folders if (new) object is not a VARIABLE_MONITOR
        if class_name != PFClassId.VARIABLE_MONITOR.value:
            self.load_project_folders_from_pf_db()
        return element

    def update_object(
        self,
        element: PFTypes.DataObject,
        /,
        *,
        data: dict[str, ValidPFValue],
    ) -> PFTypes.DataObject:
        for key, value in data.items():
            if getattr(element, key, None) is not None:
                setattr(element, key, value)

        self.load_project_folders_from_pf_db()
        return element

    # WARNING: does not work properly for now
    def update_value(
        self,
        element: str | float | bool | enum.Enum,
        /,
        *,
        value: str | float | bool | enum.Enum,
    ) -> str | float | bool | enum.Enum:
        match value:
            case str() | int() | float() | bool():
                element = value
            case enum.Enum():
                element = value.value
            case _:
                msg = f"Value type {value.__class__} not supported."
                raise ValueError(msg)

        return element

    @staticmethod
    def is_of_type(
        element: PFTypes.DataObject,
        pf_type: PFClassId,
        /,
    ) -> bool:
        return element.GetClassName() == pf_type.value

    @staticmethod
    def is_of_types(
        element: PFTypes.DataObject,
        pf_types: Sequence[PFClassId],
        /,
    ) -> bool:
        return element.GetClassName() in [pf_type.value for pf_type in pf_types]

    def create_command(self, command_type: CalculationCommand) -> PFTypes.CommandBase:
        return t.cast("PFTypes.CommandBase", self.app.GetFromStudyCase(command_type.value))

    def create_ldf_command(
        self,
        /,
        *,
        ac: bool = True,
        symmetrical: bool = True,
        data: dict[str, ValidPFValue] | None = None,
    ) -> PFTypes.CommandLoadFlow:
        """Creates a new / collect a command object of type ComLdf.

        Args:
            ac {bool} -- flag for AC or DC load flow. (default: {True})
            symmetrical {bool} -- positive sequence based ldf (symmetrical) or 3phase natural components based (unsymmetrical). (default: {True})
            data {dict[str, ValidPFValue] | None} -- a dictionary with name-value-pairs of object attributes. (default: {None})

        Returns:
            {PFTypes.CommandLoadFlow} -- the load flow command object.
        """
        cmd = t.cast("PFTypes.CommandLoadFlow", self.create_command(CalculationCommand.LOAD_FLOW))
        if ac:
            if symmetrical:
                cmd.iopt_net = NetworkExtendedCalcType.AC_SYM_POSITIVE_SEQUENCE.value  # type: ignore[assignment]
            else:
                cmd.iopt_net = NetworkExtendedCalcType.AC_UNSYM_ABC.value  # type: ignore[assignment]
        else:
            cmd.iopt_net = NetworkExtendedCalcType.DC.value  # type: ignore[assignment]

        # update further attributes if needed
        if data is not None:
            self.update_object(cmd, data=data)

        return cmd

    def create_time_sim_start_command(
        self,
        /,
        *,
        sim_type: TimeSimulationType,
        symmetrical: bool = True,
        result: PFTypes.Result | None = None,
        data: dict[str, ValidPFValue] | None = None,
    ) -> PFTypes.CommandTimeSimulationStart:
        """Creates a new / collects a command object of type ComInc.

        Keyword Arguments:
            sim_type {TimeSimulationType} -- flag to choose between RMS and EMT.
            symmetrical {bool} -- positive sequence based ldf (symmetrical) or 3phase natural components based (unsymmetrical). (default: {True})
            result {PFTypes.Result | None} -- the result object to write simulation results to. (default: {None})
            data {dict[str, ValidPFValue] | None} -- a dictionary with name-value-pairs of object attributes. (default: {None})

        Returns:
             {PFTypes.CommandTimeSimulationStart} -- the command object.
        """
        # Set type of network representation for the load flow calculation in beforehand (Workaround as cmd.c_butldf is not accessible)
        self.create_ldf_command(symmetrical=symmetrical)
        cmd = t.cast(
            "PFTypes.CommandTimeSimulationStart",
            self.create_command(CalculationCommand.TIME_DOMAIN_SIMULATION_START),
        )
        # Set type of simulation (RMS, EMT)
        cmd.iopt_sim = sim_type.value  # type: ignore[assignment]
        # Set type of network representation (symmetrical, unsymmetrical)
        if symmetrical:
            cmd.iopt_net = TimeSimulationNetworkCalcType.AC_SYM_POSITIVE_SEQUENCE.value  # type: ignore[assignment]
        else:
            cmd.iopt_net = TimeSimulationNetworkCalcType.AC_UNSYM_ABC.value  # type: ignore[assignment]
        # Set result object to be used for simulation
        if result is not None:
            cmd.p_resvar = result

        # update further attributes if needed
        if data is not None:
            self.update_object(cmd, data=data)

        return cmd

    def create_time_sim_command(self, /, *, time: float) -> PFTypes.CommandTimeSimulation:
        """Creates a new / collects a command object of type ComSim.

        Arguments:
            time {float}: duration of time simulation in seconds.

        Returns:
            {PFTypes.CommandTimeSimulation} -- the command object.
        """
        cmd = t.cast(
            "PFTypes.CommandTimeSimulation",
            self.create_command(CalculationCommand.TIME_DOMAIN_SIMULATION),
        )
        cmd.tstop = time
        return cmd

    def create_result_export_command(
        self,
        /,
        *,
        result: PFTypes.Result,
        study_case: PFTypes.StudyCase,
        export_path: pathlib.Path,
        export_mode: ResultExportMode,
        file_name: str | None = None,
        name: str = "Result Export",
        data: dict[str, ValidPFValue] | None = None,
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.CommandResultExport | None:
        """Creates a new result export command object.

        Args:
            result {PFTypes.Result} -- the result to be exported
            study_case {PFTypes.StudyCase} -- the study case this export command is related to (resp. the loaction)
            export_path {pathlib.Path} -- relative or absolute path for export
            export_mode {ResultExportMode} -- the export mode to be used (eg. CSV or COMTRADE)
            file_name {str | None} -- name of the export file. (defaults: {None}).
            name {str} -- the name of the command itself.  (defaults: {"Result Export"}).
            data {dict[str, ValidPFValue] | None} -- A dictionary with name-value-pairs of object attributes (default: {None}).
            force {bool} -- Flag to force the creation of the object nonetheless if it already exits (default: {False}).
            update {bool} -- Flag to update object attributes if objects already exists (default: {True}).

        Returns:
            {PFTypes.CommandResultExport | None} -- The new created command object.
        """
        loguru.logger.debug("Create result export command {name} ...", name=name)
        if data is None:
            data = {}
        data["iopt_exp"] = export_mode.value

        # specify file path if export mode requires a file
        if export_mode in [
            ResultExportMode.MEASUREMENT_DATA_FILE,
            ResultExportMode.COMTRADE,
            ResultExportMode.TEXT_FILE,
            ResultExportMode.PSSPLT_VERSION_2,
            ResultExportMode.CSV,
        ]:
            if export_mode in [ResultExportMode.MEASUREMENT_DATA_FILE, ResultExportMode.TEXT_FILE]:
                file_type = FileType.TXT
            elif export_mode is ResultExportMode.COMTRADE:
                file_type = FileType.DAT
            elif export_mode is ResultExportMode.PSSPLT_VERSION_2:
                file_type = FileType.RAW
            elif export_mode is ResultExportMode.CSV:
                file_type = FileType.CSV

            export_handler = ExportHandler(directory_path=export_path)
            file_path = export_handler.create_file_path(
                file_type=file_type,
                file_name=file_name,
                active_study_case=self.app.GetActiveStudyCase(),
            )
            data["f_name"] = str(file_path.resolve())

        # create result export command within specified attribute data
        element = self.create_object(
            name=name,
            class_name=CalculationCommand.RESULT_EXPORT.value,
            location=study_case,
            data=data,
            force=force,
            update=update,
        )
        res_exp_cmd = t.cast("PFTypes.CommandResultExport", element) if element is not None else None
        # Need to explicitly set the result object of the command as not doable in create/update_object()
        if res_exp_cmd is not None and update is True:
            res_exp_cmd.pResult = result

        return res_exp_cmd

    def run_ldf(
        self,
        /,
        *,
        ac: bool = True,
        symmetrical: bool = True,
        data: dict[str, ValidPFValue] | None = None,
    ) -> PFTypes.Result | None:
        """Wrapper for load flow calculation.

        Keyword Arguments:
            ac {bool} -- the voltage system used for load flow calculation (default: {True}).
            symmetrical {bool} -- flag to indicate symmetrical (positive sequence based) or unsymmetrical load flow (3phase natural components based) (default: {True}).
            data {dict[str, ValidPFValue] | None} -- a dictionary with name-value-pairs of object attributes. (default: {None})

        Returns:
            {PFTypes.Result | None} -- The default result object of load flow.
        """
        ldf_cmd = self.create_ldf_command(ac=ac, symmetrical=symmetrical, data=data)

        if ldf_cmd.Execute():
            msg = "Load flow execution failed."
            raise ValueError(msg)

        return self.result("All*", study_case_name=self.app.GetActiveStudyCase().loc_name)  # type: ignore [union-attr]

    def run_rms_simulation(
        self,
        time: float,
        /,
        *,
        symmetrical: bool = True,
        result: PFTypes.Result | None = None,
        data: dict[str, ValidPFValue] | None = None,
    ) -> PFTypes.Result | None:
        """Wrapper to easily run RMS time simulation.

        Arguments:
            time (float): simualtion time in s
        Keyword Arguments:
            symmetrical {bool} -- positive sequence based ldf (symmetrical) or 3phase natural components based (unsymmetrical). (default: {True})
            result {PFTypes.Result | None} -- the result object to write simulation results to. (default: {None})
            data {dict[str, ValidPFValue] | None} -- a dictionary with name-value-pairs of object attributes. (default: {None})

        Returns:
            {PFTypes.Result | None} -- The result object related to the RMS simualtion.
        """
        # Setup simulation start command
        sim_start_cmd = self.create_time_sim_start_command(
            sim_type=TimeSimulationType.RMS,
            symmetrical=symmetrical,
            result=result,
            data=data,
        )
        if sim_start_cmd.Execute():
            msg = "Time domain simulation: Calculation of initial condition failed."
            raise ValueError(msg)

        # Setup RMS simulation command
        time_sim_cmd = self.create_time_sim_command(time=time)

        if time_sim_cmd.Execute():
            msg = "RMS simulation execution failed."
            raise ValueError(msg)

        return sim_start_cmd.p_resvar

    def run_emt_simulation(
        self,
        time: float,
        /,
        *,
        result: PFTypes.Result | None = None,
        data: dict[str, ValidPFValue] | None = None,
    ) -> PFTypes.Result | None:
        """Wrapper to easily run EMT time simulation.

        Arguments:
            time {float}: simualtion time in seconds
        Keyword Arguments:
            result {PFTypes.Result | None} -- the result object to write simulation results to. (default: {None})
            data {dict[str, ValidPFValue] | None} -- a dictionary with name-value-pairs of object attributes. (default: {None})

        Returns:
            {PFTypes.Result | None} -- the result object related to the EMT simualtion.
        """
        # Setup simulation start command
        # Unsymmetric is set by PowerFactory!
        sim_start_cmd = self.create_time_sim_start_command(
            sim_type=TimeSimulationType.EMT,
            symmetrical=False,
            result=result,
            data=data,
        )
        if sim_start_cmd.Execute():
            msg = "Time domain simulation: Calculation of initial condition failed."
            raise ValueError(msg)

        # Setup EMT simulation command
        time_sim_cmd = self.create_time_sim_command(time=time)

        if time_sim_cmd.Execute():
            msg = "EMT simulation execution failed."
            raise ValueError(msg)

        return sim_start_cmd.p_resvar

    @staticmethod
    def run_result_export(result_export_command: PFTypes.CommandResultExport, /) -> None:
        """Result export by executing predefined result export command.

        Arguments:
            result_export_command {PFTypes.CommandResultExport} -- predefined result export command
        """
        export_mode_name = ResultExportMode(result_export_command.iopt_exp).name
        if result_export_command.Execute():
            msg = f"Result export with export mode {export_mode_name} failed."
            raise ValueError(msg)

    @staticmethod
    def delete_object(
        element: PFTypes.DataObject,
        /,
    ) -> None:
        if element.Delete():
            msg = f"Could not delete element {element}."
            raise RuntimeError(msg)

    @staticmethod
    def create_generator_name(
        generator: PFTypes.GeneratorBase,
        /,
        *,
        generator_name: str | None = None,
    ) -> str:
        """Create a name for a generator object.

        Takes into account models in which the generator might be grouped in.

        Arguments:
            generator {PFTypes.GeneratorBase} -- The generator object for which the name should be created.

        Keyword Arguments:
            generator_name {str | None} -- The already existing name of generator or generator related object (e.g. external controller) if needed to specify independently (default: {None})

        Returns:
            {str} -- The unique name of the generator object.
        """
        if generator_name is None:
            generator_name = generator.loc_name

        if generator.c_pmod is None:  # if generator is not part of higher model
            return generator_name

        return generator.c_pmod.loc_name + PATH_SEPARATOR + generator_name

    @staticmethod
    def is_within_substation(
        terminal: PFTypes.Terminal,
        /,
    ) -> bool:
        """Check if requested terminal is part of substation (parent).

        Arguments:
            terminal {PFTypes.Terminal} -- The terminal for which the check is requested.

        Returns:
            {bool} -- The result of the check.
        """

        return terminal.cpSubstat is not None

    @staticmethod
    def list_from_sequences(*sequences: Iterable[T]) -> Sequence[T]:
        """Combine iterable sequences with the same base type into one list.

        Arguments:
            sequences {Iterable[T]} -- An enumeration of sequences (all the same base type T).

        Returns:
            {list} -- A list of elements of base type T.
        """
        return list(itertools.chain.from_iterable([*sequences]))

    @staticmethod
    def is_efuse(
        fuse: PFTypes.Fuse,
        /,
    ) -> bool:
        """Return true if element fuse."""
        return not (fuse.bus1) and not (fuse.bus2)

    @staticmethod
    def is_bfuse(
        fuse: PFTypes.Fuse,
        /,
    ) -> bool:
        """Return true if branch fuse."""
        return fuse.bus1 is not None or fuse.bus2 is not None

    @staticmethod
    def filter_none(
        data: Sequence[T | None],
        /,
    ) -> Sequence[T]:
        return [e for e in data if e is not None]

    def filter_none_attributes(
        self,
        attribute_data: Sequence[AttributeData | None],
        elment: str,
        /,
    ) -> Sequence[AttributeData]:
        """Filters out None values from a list of AttributeData."""
        filtered_attribute_data: Sequence[AttributeData] = self.filter_none(attribute_data)

        # log if some attributes have not been exported
        if len(attribute_data) > len(filtered_attribute_data):
            loguru.logger.info(
                "Only {len_filtered_attribute_data} out of {len_attribute_data} attributes exported for element {elment}.",
                len_filtered_attribute_data=len(filtered_attribute_data),
                len_attribute_data=len(attribute_data),
                elment=elment,
            )
        return filtered_attribute_data

    def pf_dataobject_to_name_string(self, obj: PFTypes.DataObject, /, *, grid_name: str | None = None) -> str:
        """Converts a PowerFactory DataObject into a string based on its (full) name."""
        class_name = obj.GetClassName() if grid_name is not None else ""
        object_name = self.create_name(obj, grid_name=grid_name) if grid_name is not None else obj.GetFullName()
        return object_name + "." + class_name

    def create_attribute_data_recursive(
        self,
        element: PFTypes.DataObject,
        attribute: str | dict[str, str | dict],
        /,
        *,
        grid_name: str | None = None,
    ) -> AttributeData | None:
        """Create an instance of AttributeData for the given element.

        In case that the given attribute is a dictionary, the function is called recursively to get nested attributes.
        In case of the occurence of DataObject as value (return type) of a requesetd attribute: If the grid_name is given, the DataObject is converted to its unique_name + class_name , otherwise the full name is used.

        Args:
            element (PFTypes.DataObject): the element of interest
            elm_type(PFClassId): the type of the element
            attribute (str): key of the attribute
            grid_name (str | None, optional): the name of the grid related to the element, relevant if converting a PFTypes.DataObject. Defaults to None.

        Returns:
            AttributeData | None: instance of AttributeData or None if attribute does not exist within the element
        """
        # if given attribute is just a simple string key
        if not isinstance(attribute, dict):
            attr_value = getattr(element, attribute, None)
            if attr_value is None:
                loguru.logger.debug(
                    "Attribute {attr_key} does not exist for element {element_name}.",
                    attr_key=attribute,
                    element_name=element.loc_name,
                )
                return None

            # if attr_value is DataObject: convert to its (full) name as DataObject is not hashable, else if attr_value is vector: convert into tuple
            if element.GetAttributeType(attribute).name == PFTypes.AttributeType.OBJECT.value:
                attr_value = self.pf_dataobject_to_name_string(attr_value, grid_name=grid_name)
            elif element.GetAttributeType(attribute).name == PFTypes.AttributeType.OBJECT_VEC.value:
                attr_value = tuple(
                    [self.pf_dataobject_to_name_string(obj, grid_name=grid_name) for obj in attr_value],
                )
            elif element.GetAttributeType(attribute).name in [
                PFTypes.AttributeType.INTEGER_VEC.value,
                PFTypes.AttributeType.DOUBLE_VEC.value,
                PFTypes.AttributeType.INTEGER64_VEC.value,
            ]:
                attr_value = tuple(attr_value)
            return AttributeData(
                name=attribute,
                value=attr_value,
                description=element.GetAttributeDescription(attribute),
            )

        # otherwise if the given attribute is not a str but a dictionary, recursively get nested attributes
        obj: PFTypes.DataObject | None = getattr(element, next(iter(attribute)), None)
        if obj is None:
            loguru.logger.debug(
                "Attribute {attr_key} does not exist for element {element_name}.",
                attr_key=next(iter(attribute)),
                element_name=element.loc_name,
            )
            return None

        nested_value = tuple(
            self.create_attribute_data_recursive(
                obj,
                nested_value,
                grid_name=grid_name,
            )
            for nested_value in sorted(
                attribute[next(iter(attribute))],
                key=lambda x: x.lower() if isinstance(x, str) else next(iter(x)).lower(),
            )
        )

        return AttributeData(
            name=next(iter(attribute)),
            description=element.GetAttributeDescription(next(iter(attribute))),
            value=self.filter_none_attributes(
                nested_value,
                self.pf_dataobject_to_name_string(obj, grid_name=grid_name),
            ),
        )

    def create_name(
        self,
        element: PFTypes.DataObject,
        /,
        *,
        grid_name: str,
        element_name: str | None = None,
    ) -> str:
        """Create a unique name of the object.

        Object type differentiation based on the input parameters. Considers optional parents of the object,
        element.g. in case of detailed template or detailed substation.

        Arguments:
            element {PFTypes.DataObject} -- The object itself for which a unique name is going to be created.
            grid_name {str} -- The name of the grid to which the object belongs (root).

        Keyword Arguments:
            element_name {str | None} -- The element name if needed to specify independently (default: {None}).

        Returns:
            {str} -- The unique name of the object.
        """

        if element_name is None:
            element_name = element.loc_name

        parent = element.fold_id
        if (parent is not None) and (parent.loc_name != grid_name):
            cp_substat: PFTypes.Substation | None = getattr(element, "cpSubstat", None)
            if cp_substat is not None:
                if PowerFactoryInterface.is_of_type(parent, PFClassId.SUBSTATION_FIELD):
                    return cp_substat.loc_name + PATH_SEPARATOR + parent.loc_name + PATH_SEPARATOR + element_name

                return cp_substat.loc_name + PATH_SEPARATOR + element_name

            return parent.loc_name + PATH_SEPARATOR + element_name

        return element_name

    ## !
    ## The following may be part of version inconsistent behavior
    ## !
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
