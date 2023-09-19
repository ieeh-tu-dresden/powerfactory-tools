# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import contextlib
import dataclasses
import datetime as dt
import importlib.util
import itertools
import logging
import pathlib
import sys
import typing as t
from collections.abc import Sequence

import loguru
import pydantic

from powerfactory_tools.constants import BaseUnits
from powerfactory_tools.powerfactory_types import CalculationCommand
from powerfactory_tools.powerfactory_types import Currency
from powerfactory_tools.powerfactory_types import FolderType
from powerfactory_tools.powerfactory_types import MetricPrefix
from powerfactory_tools.powerfactory_types import NetworkExtendedCalcType
from powerfactory_tools.powerfactory_types import PFClassId
from powerfactory_tools.powerfactory_types import UnitSystem
from powerfactory_tools.powerfactory_types import ValidPFValue

if t.TYPE_CHECKING:
    from collections.abc import Iterable
    from types import TracebackType

    import typing_extensions as te

    from powerfactory_tools.powerfactory_types import PowerFactoryTypes as PFTypes

    T = t.TypeVar("T")

POWERFACTORY_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
POWERFACTORY_VERSION = "2022 SP2"
PYTHON_VERSION = "3.10"
PATH_SEP = "/"


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


@dataclasses.dataclass
class PowerFactoryData:
    date: dt.date
    project_name: str
    grid_name: str
    external_grids: Sequence[PFTypes.ExternalGrid]
    terminals: Sequence[PFTypes.Terminal]
    lines: Sequence[PFTypes.Line]
    transformers_2w: Sequence[PFTypes.Transformer2W]
    transformers_3w: Sequence[PFTypes.Transformer3W]
    loads: Sequence[PFTypes.Load]
    loads_lv: Sequence[PFTypes.LoadLV]
    loads_mv: Sequence[PFTypes.LoadMV]
    generators: Sequence[PFTypes.Generator]
    pv_systems: Sequence[PFTypes.PVSystem]
    couplers: Sequence[PFTypes.Coupler]
    switches: Sequence[PFTypes.Switch]
    bfuses: Sequence[PFTypes.BFuse]
    efuses: Sequence[PFTypes.EFuse]
    ac_current_sources: Sequence[PFTypes.AcCurrentSource]


@pydantic.dataclasses.dataclass
class PowerFactoryInterface:
    project_name: str
    powerfactory_user_profile: str | None = None
    powerfactory_user_password: str | None = None
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH
    powerfactory_version: str = POWERFACTORY_VERSION
    powerfactory_ini_name: str | None = None
    python_version: str = PYTHON_VERSION
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

    def load_project_setting_folders_from_pf_db(self) -> None:
        self.project_settings = self.load_project_settings_dir_from_pf()
        self.settings_dir = self.load_settings_dir_from_pf()
        self.unit_settings_dir = self.load_unit_settings_dir_from_pf()

    def load_project_folders_from_pf_db(self) -> None:
        self.load_project_setting_folders_from_pf_db()

        self.grid_model_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.NETWORK_MODEL.value))
        self.types_dir = t.cast(
            "PFTypes.ProjectFolder",
            self.app.GetProjectFolder(FolderType.EQUIPMENT_TYPE_LIBRARY.value),
        )
        self.op_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.OPERATIONAL_LIBRARY.value))
        self.chars_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.CHARACTERISTICS.value))

        self.grid_data_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.NETWORK_DATA.value))
        self.grid_graphs_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.DIAGRAMS.value))

        self.study_case_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.STUDY_CASES.value))
        self.scenario_dir = t.cast(
            "PFTypes.ProjectFolder",
            self.app.GetProjectFolder(FolderType.OPERATION_SCENARIOS.value),
        )
        self.grid_variant_dir = t.cast("PFTypes.ProjectFolder", self.app.GetProjectFolder(FolderType.VARIATIONS.value))

        self.ext_data_dir = self.project_settings.extDataDir

    def load_powerfactory_module_from_path(self) -> PFTypes.PowerFactoryModule:
        loguru.logger.debug("Loading PowerFactory Python module...")
        module_path = (
            self.powerfactory_path / ("PowerFactory " + self.powerfactory_version) / "Python" / self.python_version
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
                self.powerfactory_path
                / ("PowerFactory " + self.powerfactory_version)
                / (self.powerfactory_ini_name + ".ini")
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

    def switch_study_case(self, study_case_name: str) -> None:
        study_case = self.study_case(study_case_name)
        if study_case is not None:
            self.activate_study_case(study_case)
        else:
            msg = f"Study case {study_case_name} does not exist."
            raise RuntimeError(msg)

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

    def set_result_variables(
        self,
        *,
        result: PFTypes.Result,
        elements: Sequence[PFTypes.DataObject],
        variables: Sequence[str],
    ) -> None:
        loguru.logger.debug("Set Variables for result object {result_name} ...", result_name=result.loc_name)
        for elm in elements:
            for variable in variables:
                result.AddVariable(elm, variable)

    def activate_grid(
        self,
        grid: PFTypes.Grid,
        /,
    ) -> None:
        loguru.logger.debug("Activating grid {grid_name} application...", grid_name=grid.loc_name)
        if not grid.IsCalcRelevant() and grid.Activate():
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
        if grid.IsCalcRelevant() and grid.Deactivate():
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
        active_scen = self.app.GetActiveScenario()
        if active_scen != scenario and scenario.Activate():
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
        if scenario.Deactivate():
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
        if study_case.loc_name != self.app.GetActiveStudyCase().loc_name and study_case.Activate():
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
        if study_case.Deactivate():
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
        if grid_variant.Activate():
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
        if grid_variant.Deactivate():
            msg = "Could not deactivate grid variant."
            raise RuntimeError(msg)

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

    def subloads_of(
        self,
        load: PFTypes.LoadLV,
        /,
    ) -> Sequence[PFTypes.LoadLVP]:
        elements = self.elements_of(load, pattern="*." + PFClassId.LOAD_LV_PART.value)
        return [t.cast("PFTypes.LoadLVP", element) for element in elements]

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
        elements = self.study_case_elements(
            class_name=PFClassId.RESULT.value,
            name=name,
            study_case_name=study_case_name,
        )
        return [t.cast("PFTypes.Result", element) for element in elements]

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
        elements = self.equipment_type_elements("TypLne", name)
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
        elements = self.equipment_type_elements("TypLod", name)
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
        elements = self.equipment_type_elements("TypTr2", name)
        return [t.cast("PFTypes.Transformer2WType", element) for element in elements]

    def harmonic_source_type(
        self,
        name: str = "*",
        /,
    ) -> PFTypes.HarmonicSourceType | None:
        return self.first_of(self.harmonic_source_types(name))

    def harmonic_source_types(
        self,
        name: str = "*",
        /,
    ) -> Sequence[PFTypes.HarmonicSourceType]:
        elements = self.equipment_type_elements("TypHmccur", name)
        return [t.cast("PFTypes.HarmonicSourceType", element) for element in elements]

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
    ) -> Sequence[PFTypes.ExternalGrid]:
        elements = self.grid_elements(
            class_name=PFClassId.EXTERNAL_GRID.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
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
    ) -> Sequence[PFTypes.Terminal]:
        elements = self.grid_elements(
            class_name=PFClassId.TERMINAL.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
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
    ) -> Sequence[PFTypes.StationCubicle]:
        elements = self.grid_elements(
            class_name=PFClassId.CUBICLE.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
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
    ) -> Sequence[PFTypes.Coupler]:
        elements = self.grid_elements(
            class_name=PFClassId.COUPLER.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
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
    ) -> Sequence[PFTypes.Switch]:
        elements = self.grid_elements(
            class_name=PFClassId.SWITCH.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
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
    ) -> Sequence[PFTypes.BFuse]:
        elements = self.grid_elements(
            class_name=PFClassId.FUSE.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
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
    ) -> Sequence[PFTypes.EFuse]:
        elements = self.grid_elements(
            class_name=PFClassId.FUSE.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
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
    ) -> Sequence[PFTypes.Line]:
        elements = self.grid_elements(
            class_name=PFClassId.LINE.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
        )
        return [t.cast("PFTypes.Line", element) for element in elements]

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
    ) -> Sequence[PFTypes.Transformer2W]:
        elements = self.grid_elements(
            class_name=PFClassId.TRANSFORMER_2W.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
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
    ) -> Sequence[PFTypes.Transformer3W]:
        elements = self.grid_elements(
            class_name=PFClassId.TRANSFORMER_3W.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
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
    ) -> Sequence[PFTypes.Load]:
        elements = self.grid_elements(
            class_name=PFClassId.LOAD.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
        )
        return [t.cast("PFTypes.Load", element) for element in elements]

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
    ) -> Sequence[PFTypes.Generator]:
        elements = self.grid_elements(
            class_name=PFClassId.GENERATOR.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
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
    ) -> Sequence[PFTypes.PVSystem]:
        elements = self.grid_elements(
            class_name=PFClassId.PVSYSTEM.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
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
    ) -> Sequence[PFTypes.AcCurrentSource]:
        elements = self.grid_elements(
            class_name=PFClassId.CURRENT_SOURCE_AC.value,
            name=name,
            grid_name=grid_name,
            calc_relevant=calc_relevant,
        )
        return [t.cast("PFTypes.AcCurrentSource", element) for element in elements]

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
            return self.app.GetCalcRelevantObjects(name + "." + class_name, include_out_of_service)

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

    def create_result(
        self,
        *,
        name: str,
        study_case: PFTypes.StudyCase,
        data: dict[str, ValidPFValue] | None = None,
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.Result | None:
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

    def create_study_case(
        self,
        *,
        name: str,
        grids: Sequence[PFTypes.Grid],
        grid_variants: Sequence[PFTypes.GridVariant],
        scenario: PFTypes.Scenario,
        target_datetime: dt.datetime,
        location: PFTypes.DataObject | None = None,
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.StudyCase:
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

        grid_variant_config = self.create_object(
            name=f"{name}_variants",
            class_name=PFClassId.VARIANT_CONFIG.value,
            location=study_case,
            force=force,
            update=update,
        )
        for grid_variant in grid_variants:
            self.create_object(
                name=grid_variant.loc_name,
                class_name=PFClassId.REFERENCE.value,
                data={"obj_id": grid_variant},
                location=grid_variant_config,
                force=force,
                update=update,
            )

        entire_grid = self.create_object(
            name="entire_grid",
            class_name=PFClassId.GRID.value,
            location=study_case,
            force=force,
            update=update,
        )
        for grid in grids:
            self.create_object(
                name=grid.loc_name,
                class_name=PFClassId.REFERENCE.value,
                data={"obj_id": grid},
                location=entire_grid,
                force=force,
                update=update,
            )

        self.create_object(
            name=scenario.loc_name,
            class_name=PFClassId.REFERENCE.value,
            data={"obj_id": scenario},
            location=study_case,
            force=force,
            update=update,
        )

        self.create_object(
            name="target_datetime",
            class_name=PFClassId.DATETIME.value,
            data={
                "cDate": target_datetime.date,
                "cTime": target_datetime.time,
            },
            location=study_case,
            force=force,
            update=update,
        )

        return t.cast("PFTypes.GridVariant", study_case)

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
            {PFTypes.GridVariant | None} -- The created grid variant if successful.
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
            {PFTypes.GridVariantStage | None} -- The created grid variant stage if successful.
        """
        # try to catch possibly existing variant stage
        stage = self.grid_variant_stage(
            name,
            grid_variant=grid_variant,
        )

        if stage is not None:
            # if stage already exists and creation is forced, override existing stage
            if force:
                elm = self.create_object(
                    name=name,
                    class_name=PFClassId.VARIANT_STAGE.value,
                    location=grid_variant,
                    data=data,
                    force=force,
                    update=update,
                )
                stage = t.cast("PFTypes.GridVariantStage", elm) if elm else None
            else:
                loguru.logger.warning(
                    "{object_name}.{class_name} already exists. Use force=True to create it anyway.",
                    object_name=name,
                    class_name=PFClassId.VARIANT_STAGE.value,
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

        return stage

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
            {PFTypes.DataObject | None} - The created folder if successful.
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
            {PFTypes.DataObject | None} -- The created object if successful.
        """

        _elements = self.elements_of(location, pattern=f"{name}.{class_name}")
        element = self.first_of(_elements)
        if element is not None and force is False:
            if update is False:
                loguru.logger.warning(
                    "{object_name}.{class_name} already exists. Use force=True to create it anyway or update=True to update it.",
                    object_name=name,
                    class_name=class_name,
                )
        else:
            element = location.CreateObject(class_name, name)
            update = True

        if element is not None and data is not None and update is True:
            return self.update_object(element, data=data)

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

    def calc_command(self, command_type: CalculationCommand) -> PFTypes.CommandBase:
        return t.cast("PFTypes.CommandBase", self.app.GetFromStudyCase(command_type.value))

    def ldf_command(self) -> PFTypes.CommandLoadFlow:
        cmd = self.calc_command(CalculationCommand.LOAD_FLOW)
        return t.cast("PFTypes.CommandLoadFlow", cmd)

    def run_ldf(
        self,
        /,
        *,
        ac: bool = True,
        symmetrical: bool = True,
    ) -> PFTypes.Result | None:
        """Run load flow calculation.

        Keyword Arguments:
            ac {bool} -- The voltage system used for load flow calculation (default: {True}).
            symmetrical {bool} -- Flag to indicate symmetrical (posivie sequence based) or unsymmetrical load flow (3phase natural components based) (default: {True}).

        Returns:
            {PFTypes.Result | None} -- The default result object of load flow.
        """
        ldf_cmd = self.ldf_command()
        if ac:
            if symmetrical:
                ldf_cmd.iopt_net = NetworkExtendedCalcType.AC_SYM_POSITIVE_SEQUENCE.value
            else:
                ldf_cmd.iopt_net = NetworkExtendedCalcType.AC_UNSYM_ABC.value
        else:
            ldf_cmd.iopt_net = NetworkExtendedCalcType.DC.value

        error = ldf_cmd.Execute()
        if error != 0:
            msg = "Load flow execution failed."
            raise ValueError(msg)

        return self.result("All*")

    @staticmethod
    def delete_object(
        element: PFTypes.DataObject,
        /,
    ) -> None:
        if element.Delete():
            msg = f"Could not delete element {element}."
            raise RuntimeError(msg)

    @staticmethod
    def create_name(
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
            cp_substat: PFTypes.DataObject | None = getattr(element, "cpSubstat", None)
            if cp_substat is not None:
                return cp_substat.loc_name + PATH_SEP + element_name

            return parent.loc_name + PATH_SEP + element_name

        return element_name

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

        return generator.c_pmod.loc_name + PATH_SEP + generator_name

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
    def filter_none(
        data: Sequence[T | None],
        /,
    ) -> Sequence[T]:
        return [e for e in data if e is not None]

    @staticmethod
    def is_efuse(
        fuse: PFTypes.Fuse,
        /,
    ) -> bool:
        return not (fuse.bus1) and not (fuse.bus2)

    @staticmethod
    def is_bfuse(
        fuse: PFTypes.Fuse,
        /,
    ) -> bool:
        return fuse.bus1 is not None or fuse.bus2 is not None
