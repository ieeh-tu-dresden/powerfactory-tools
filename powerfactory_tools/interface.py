# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import contextlib
import dataclasses
import datetime
import importlib.util
import itertools
import pathlib
import typing as t
from collections.abc import Sequence

import pydantic
from loguru import logger

from powerfactory_tools.constants import BaseUnits
from powerfactory_tools.powerfactory_types import Currency
from powerfactory_tools.powerfactory_types import MetricPrefix
from powerfactory_tools.powerfactory_types import UnitSystem

if t.TYPE_CHECKING:
    from collections.abc import Iterable
    from types import TracebackType

    from powerfactory_tools.powerfactory_types import PowerFactoryTypes as PFTypes

    T = t.TypeVar("T")

POWERFACTORY_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
POWERFACTORY_VERSION = "2022 SP2"
PYTHON_VERSION = "3.10"
PATH_SEP = "/"


class Config:
    use_enum_values = True


@pydantic.dataclasses.dataclass(config=Config)
class UnitConversionSetting:
    filtclass: Sequence[str]
    filtvar: str
    digunit: str
    cdigexp: MetricPrefix
    userunit: str
    cuserexp: MetricPrefix
    ufacA: float  # noqa: N815
    ufacB: float  # noqa: N815


@pydantic.dataclasses.dataclass(config=Config)
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
    name: str
    date: datetime.date
    project: str
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
    fuses: Sequence[PFTypes.Fuse]
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

    def __post_init__(self) -> None:
        try:
            logger.info("Starting PowerFactory Interface...")
            pf = self.load_powerfactory_module_from_path()
            self.app = self.connect_to_app(pf)
            self.project = self.connect_to_project(self.project_name)
            self.load_project_setting_folders_from_pf_db()
            self.stash_unit_conversion_settings()
            self.set_default_unit_conversion()
            self.load_project_folders_from_pf_db()
            logger.info("Starting PowerFactory Interface... Done.")
        except RuntimeError:
            logger.exception("Could not start PowerFactory Interface. Shutting down...")
            self.close()

    def __enter__(self) -> PowerFactoryInterface:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self.close()

    def load_project_setting_folders_from_pf_db(self) -> None:
        self.project_settings = self.load_project_settings_dir_from_pf()
        self.settings_dir = self.load_settings_dir_from_pf()
        self.unit_settings_dir = self.load_unit_settings_dir_from_pf()

    def load_project_folders_from_pf_db(self) -> None:
        self.load_project_setting_folders_from_pf_db()

        self.grid_model = self.app.GetProjectFolder("netmod")
        self.types_dir = self.app.GetProjectFolder("equip")
        self.op_dir = self.app.GetProjectFolder("oplib")
        self.chars_dir = self.app.GetProjectFolder("chars")

        self.grid_data = self.app.GetProjectFolder("netdat")
        self.study_case_dir = self.app.GetProjectFolder("study")
        self.scenario_dir = self.app.GetProjectFolder("scen")
        self.grid_graphs_dir = self.app.GetProjectFolder("dia")

        self.ext_data_dir = self.project_settings.extDataDir

    def load_powerfactory_module_from_path(self) -> PFTypes.PowerFactoryModule:
        logger.debug("Loading PowerFactory Python module...")
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
        logger.debug("Loading settings from PowerFactory...")
        _settings_dirs = self.elements_of(element=self.project, pattern="*.SetFold", recursive=False)
        settings_dir = self.first_of(elements=_settings_dirs)
        if settings_dir is None:
            msg = "Could not access settings."
            raise RuntimeError(msg)

        logger.debug("Loading settings from PowerFactory... Done.")
        return t.cast("PFTypes.DataDir", settings_dir)

    def load_unit_settings_dir_from_pf(self) -> PFTypes.DataDir | None:
        logger.debug("Loading unit settings from PowerFactory...")
        _unit_settings_dirs = self.elements_of(element=self.settings_dir, pattern="*.IntUnit", recursive=False)
        unit_settings_dir = self.first_of(elements=_unit_settings_dirs)
        if unit_settings_dir is None:
            return None

        logger.debug("Loading unit settings from PowerFactory... Done.")
        return t.cast("PFTypes.DataDir", unit_settings_dir)

    def close(self) -> None:
        logger.info("Closing PowerFactory Interface...")
        with contextlib.suppress(AttributeError):
            self.pop_unit_conversion_settings_stash()

        with contextlib.suppress(AttributeError):
            self.app.PostCommand("exit")

        logger.info("Closing PowerFactory Interface... Done.")

    def connect_to_app(self, pf: PFTypes.PowerFactoryModule) -> PFTypes.Application:
        """Connect to PowerFactory Application.

        Arguments:
            pf {PFTypes.PowerFactoryModule} -- the Python module contributed via the PowerFactory system installation

        Returns:
            PFTypes.Application -- the application handle (root)
        """

        logger.debug("Connecting to PowerFactory application...")
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

        logger.debug(
            "Activating project {project_name} application...",
            project_name=project_name,
        )
        self.activate_project(project_name)

        project = self.app.GetActiveProject()
        if project is None:
            msg = "Could not access project."
            raise RuntimeError(msg)

        logger.debug(
            "Activating project {project_name} application... Done.",
            project_name=project_name,
        )
        return project

    def switch_study_case(self, sc: str) -> None:
        study_case = self.study_case(name=sc)
        if study_case is not None:
            self.activate_study_case(study_case)
        else:
            msg = f"Study case {sc} does not exist."
            raise RuntimeError(msg)

    def switch_scenario(self, scen: str) -> None:
        scenario = self.scenario(name=scen)
        if scenario is not None:
            self.activate_scenario(scenario)
        else:
            msg = f"Scenario {scen} does not exist."
            raise RuntimeError(msg)

    def compile_powerfactory_data(self, grid_name: str) -> PowerFactoryData:
        logger.debug("Compiling data from PowerFactory...")
        if grid_name == "*":
            name = self.project_name
        else:
            grids = self.grids()
            try:
                grid = [e for e in grids if e.loc_name == grid_name][0]
                name = grid.loc_name
            except IndexError as e:
                msg = f"Grid {grid_name} does not exist."
                raise RuntimeError(msg) from e

        project_name = self.project.loc_name
        date = datetime.datetime.now().astimezone().date()  # noqa: DTZ005

        return PowerFactoryData(
            name=name,
            date=date,
            project=project_name,
            external_grids=self.external_grids(grid=grid_name),
            terminals=self.terminals(grid=grid_name),
            lines=self.lines(grid=grid_name),
            transformers_2w=self.transformers_2w(grid=grid_name),
            transformers_3w=self.transformers_3w(grid=grid_name),
            loads=self.loads(grid=grid_name),
            loads_lv=self.loads_lv(grid=grid_name),
            loads_mv=self.loads_mv(grid=grid_name),
            generators=self.generators(grid=grid_name),
            pv_systems=self.pv_systems(grid=grid_name),
            couplers=self.couplers(grid=grid_name),
            switches=self.switches(grid=grid_name),
            fuses=self.fuses(grid=grid_name),
            ac_current_sources=self.ac_current_sources(grid=grid_name),
        )

    def set_result_variables(
        self,
        *,
        result: PFTypes.Result,
        elements: Sequence[PFTypes.DataObject],
        variables: Sequence[str],
    ) -> None:
        logger.debug("Set Variables for result object {result_name} ...", result_name=result.loc_name)
        for elm in elements:
            for variable in variables:
                result.AddVariable(elm, variable)

    def activate_grid(self, grid: PFTypes.Grid) -> None:
        logger.debug("Activating grid {grid_name} application...", grid_name=grid.loc_name)
        if grid.Activate():
            msg = "Could not activate grid."
            raise RuntimeError(msg)

    def deactivate_grids(self) -> None:
        for grid in self.grids():
            self.deactivate_grid(grid)

    def deactivate_grid(self, grid: PFTypes.Grid) -> None:
        logger.debug("Deactivating grid {grid_name} application...", grid_name=grid.loc_name)
        if grid.Deactivate():
            msg = "Could not deactivate grid."
            raise RuntimeError(msg)

    def activate_scenario(self, scen: PFTypes.Scenario) -> None:
        logger.debug(
            "Activating scenario {scenario_name} application...",
            scenario_name=scen.loc_name,
        )
        active_scen = self.app.GetActiveScenario()
        if active_scen != scen and scen.Activate():
            msg = "Could not activate scenario."
            raise RuntimeError(msg)

    def deactivate_scenario(self, scen: PFTypes.Scenario) -> None:
        logger.debug(
            "Deactivating scenario {scenario_name} application...",
            scenario_name=scen.loc_name,
        )
        if scen.Deactivate():
            msg = "Could not deactivate scenario."
            raise RuntimeError(msg)

    def activate_study_case(self, stc: PFTypes.StudyCase) -> None:
        logger.debug(
            "Activating study_case {study_case_name} application...",
            study_case_name=stc.loc_name,
        )
        if stc.Activate():
            msg = "Could not activate case study."
            raise RuntimeError(msg)

    def deactivate_study_case(self, stc: PFTypes.StudyCase) -> None:
        logger.debug(
            "Deactivating study_case {study_case_name} application...",
            study_case_name=stc.loc_name,
        )
        if stc.Deactivate():
            msg = "Could not deactivate case study."
            raise RuntimeError(msg)

    def set_default_unit_conversion(self) -> None:
        logger.debug("Applying exporter default unit conversion settings...")
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
        logger.debug("Applying exporter default unit conversion settings... Done.")

    def stash_unit_conversion_settings(self) -> None:
        logger.debug("Stashing PowerFactory default unit conversion settings...")
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
        logger.debug("Stashing PowerFactory default unit conversion settings... Done.")

    def pop_unit_conversion_settings_stash(self) -> None:
        logger.debug("Applying PowerFactory default unit conversion settings...")
        self.project_settings.ilenunit = self.project_unit_setting.ilenunit
        self.project_settings.clenexp = self.project_unit_setting.clenexp
        self.project_settings.cspqexp = self.project_unit_setting.cspqexp
        self.project_settings.cspqexpgen = self.project_unit_setting.cspqexpgen
        self.project_settings.currency = self.project_unit_setting.currency
        self.delete_unit_conversion_settings()
        for name, uc in self.unit_conv_settings.items():
            self.create_unit_conversion_setting(name, uc)

        self.reset_project()
        logger.debug("Applying PowerFactory default unit conversion settings... Done.")

    def load_project_settings_dir_from_pf(self) -> PFTypes.ProjectSettings:
        logger.debug("Loading project settings dir...")
        project_settings = self.project.pPrjSettings
        if project_settings is None:
            msg = "Could not access project settings."
            raise RuntimeError(msg)

        logger.debug("Loading project settings dir... Done.")
        return project_settings

    def reset_project(self) -> None:
        logger.debug("Resetting current project...")
        self.deactivate_project()
        self.activate_project(self.project_name)
        logger.debug("Resetting current project... Done.")

    def activate_project(self, name: str) -> None:
        logger.debug("Activating project {name}...", name=name)
        if self.app.ActivateProject(name + ".IntPrj"):
            msg = "Could not activate project."
            raise RuntimeError(msg)

    def deactivate_project(self) -> None:
        logger.debug("Deactivating current project {name}...")
        if self.project.Deactivate():
            msg = "Could not deactivate project."
            raise RuntimeError(msg)

    def subloads_of(self, load: PFTypes.LoadLV) -> Sequence[PFTypes.LoadLVP]:
        elements = self.elements_of(element=load, pattern="*.ElmLodlvp")
        return [t.cast("PFTypes.LoadLVP", element) for element in elements]

    def result(self, name: str = "*", study_case_name: str = "*") -> PFTypes.Result | None:
        return self.first_of(elements=self.results(name=name, study_case_name=study_case_name))

    def results(self, name: str = "*", study_case_name: str = "*") -> Sequence[PFTypes.Result]:
        elements = self.study_case_elements(class_name="ElmRes", name=name, study_case_name=study_case_name)
        return [t.cast("PFTypes.Result", element) for element in elements]

    def study_case(self, name: str = "*") -> PFTypes.StudyCase | None:
        return self.first_of(elements=self.study_cases(name=name))

    def study_cases(self, name: str = "*") -> Sequence[PFTypes.StudyCase]:
        elements = self.elements_of(element=self.study_case_dir, pattern=name + ".IntCase")
        return [t.cast("PFTypes.StudyCase", element) for element in elements]

    def scenario(self, name: str = "*") -> PFTypes.Scenario | None:
        return self.first_of(elements=self.scenarios(name=name))

    def scenarios(self, name: str = "*") -> Sequence[PFTypes.Scenario]:
        elements = self.elements_of(element=self.scenario_dir, pattern=name)
        return [t.cast("PFTypes.Scenario", element) for element in elements]

    def line_type(self, name: str = "*") -> PFTypes.LineType | None:
        return self.first_of(elements=self.line_types(name=name))

    def line_types(self, name: str = "*") -> Sequence[PFTypes.LineType]:
        elements = self.equipment_type_elements("TypLne", name)
        return [t.cast("PFTypes.LineType", element) for element in elements]

    def load_type(self, name: str = "*") -> PFTypes.DataObject | None:
        return self.first_of(elements=self.load_types(name=name))

    def load_types(self, name: str = "*") -> Sequence[PFTypes.DataObject]:
        elements = self.equipment_type_elements("TypLod", name)
        return [t.cast("PFTypes.LoadType", element) for element in elements]

    def transformer_2w_type(self, name: str = "*") -> PFTypes.Transformer2WType | None:
        return self.first_of(elements=self.transformer_2w_types(name=name))

    def transformer_2w_types(self, name: str = "*") -> Sequence[PFTypes.Transformer2WType]:
        elements = self.equipment_type_elements("TypTr2", name)
        return [t.cast("PFTypes.Transformer2WType", element) for element in elements]

    def harmonic_source_type(self, name: str = "*") -> PFTypes.HarmonicSourceType | None:
        return self.first_of(elements=self.harmonic_source_types(name=name))

    def harmonic_source_types(self, name: str = "*") -> Sequence[PFTypes.HarmonicSourceType]:
        elements = self.equipment_type_elements("TypHmccur", name)
        return [t.cast("PFTypes.HarmonicSourceType", element) for element in elements]

    def area(self, name: str = "*") -> PFTypes.DataObject | None:
        return self.first_of(elements=self.areas(name=name))

    def areas(self, name: str = "*") -> Sequence[PFTypes.DataObject]:
        return self.grid_model_elements("ElmArea", name)

    def zone(self, name: str = "*") -> PFTypes.DataObject | None:
        return self.first_of(elements=self.zones(name=name))

    def zones(self, name: str = "*") -> Sequence[PFTypes.DataObject]:
        return self.grid_model_elements("ElmZone", name)

    def grid_diagram(self, grid: str = "*") -> PFTypes.GridDiagram | None:
        return self.first_of(elements=self.grid_diagrams(grid=grid))

    def grid_diagrams(self, grid: str = "*") -> Sequence[PFTypes.GridDiagram]:
        elements = self.grid_elements("IntGrfnet", grid=grid)
        return [t.cast("PFTypes.GridDiagram", element) for element in elements]

    def external_grid(self, name: str = "*", grid: str = "*") -> PFTypes.ExternalGrid | None:
        return self.first_of(elements=self.external_grids(name=name, grid=grid))

    def external_grids(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.ExternalGrid]:
        elements = self.grid_elements("ElmXNet", name, grid)
        return [t.cast("PFTypes.ExternalGrid", element) for element in elements]

    def terminal(self, name: str = "*", grid: str = "*") -> PFTypes.Terminal | None:
        return self.first_of(elements=self.terminals(name=name, grid=grid))

    def terminals(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Terminal]:
        elements = self.grid_elements("ElmTerm", name, grid)
        return [t.cast("PFTypes.Terminal", element) for element in elements]

    def cubicle(self, name: str = "*", grid: str = "*") -> PFTypes.StationCubicle | None:
        return self.first_of(elements=self.cubicles(name=name, grid=grid))

    def cubicles(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.StationCubicle]:
        elements = self.grid_elements("StaCubic", name, grid)
        return [t.cast("PFTypes.StationCubicle", element) for element in elements]

    def coupler(self, name: str = "*", grid: str = "*") -> PFTypes.Coupler | None:
        return self.first_of(elements=self.couplers(name=name, grid=grid))

    def couplers(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Coupler]:
        elements = self.grid_elements("ElmCoup", name, grid)
        return [t.cast("PFTypes.Coupler", element) for element in elements]

    def switch(self, name: str = "*", grid: str = "*") -> PFTypes.Switch | None:
        return self.first_of(elements=self.switches(name=name, grid=grid))

    def switches(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Switch]:
        elements = self.grid_elements("StaSwitch", name, grid)
        return [t.cast("PFTypes.Switch", element) for element in elements]

    def fuse(self, name: str = "*", grid: str = "*") -> PFTypes.Fuse | None:
        return self.first_of(elements=self.fuses(name=name, grid=grid))

    def fuses(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Fuse]:
        elements = self.grid_elements("RelFuse", name, grid)
        return [t.cast("PFTypes.Fuse", element) for element in elements]

    def line(self, name: str = "*", grid: str = "*") -> PFTypes.Line | None:
        return self.first_of(elements=self.lines(name=name, grid=grid))

    def lines(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Line]:
        elements = self.grid_elements("ElmLne", name, grid)
        return [t.cast("PFTypes.Line", element) for element in elements]

    def transformer_2w(self, name: str = "*", grid: str = "*") -> PFTypes.Transformer2W | None:
        return self.first_of(elements=self.transformers_2w(name=name, grid=grid))

    def transformers_2w(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Transformer2W]:
        elements = self.grid_elements("ElmTr2", name, grid)
        return [t.cast("PFTypes.Transformer2W", element) for element in elements]

    def transformer_3w(self, name: str = "*", grid: str = "*") -> PFTypes.Transformer3W | None:
        return self.first_of(elements=self.transformers_3w(name=name, grid=grid))

    def transformers_3w(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Transformer3W]:
        elements = self.grid_elements("ElmTr3", name, grid)
        return [t.cast("PFTypes.Transformer3W", element) for element in elements]

    def load(self, name: str = "*", grid: str = "*") -> PFTypes.Load | None:
        return self.first_of(elements=self.loads(name=name, grid=grid))

    def loads(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Load]:
        elements = self.grid_elements("ElmLod", name, grid)
        return [t.cast("PFTypes.Load", element) for element in elements]

    def load_lv(self, name: str = "*", grid: str = "*") -> PFTypes.LoadLV | None:
        return self.first_of(elements=self.loads_lv(name=name, grid=grid))

    def loads_lv(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.LoadLV]:
        elements = self.grid_elements("ElmLodLv", name, grid)
        return [t.cast("PFTypes.LoadLV", element) for element in elements]

    def load_mv(self, name: str = "*", grid: str = "*") -> PFTypes.LoadMV | None:
        return self.first_of(elements=self.loads_mv(name=name, grid=grid))

    def loads_mv(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.LoadMV]:
        elements = self.grid_elements("ElmLodMv", name, grid)
        return [t.cast("PFTypes.LoadMV", element) for element in elements]

    def generator(self, name: str = "*", grid: str = "*") -> PFTypes.Generator | None:
        return self.first_of(elements=self.generators(name=name, grid=grid))

    def generators(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Generator]:
        elements = self.grid_elements("ElmGenstat", name, grid)
        return [t.cast("PFTypes.Generator", element) for element in elements]

    def pv_system(self, name: str = "*", grid: str = "*") -> PFTypes.PVSystem | None:
        return self.first_of(elements=self.pv_systems(name=name, grid=grid))

    def pv_systems(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.PVSystem]:
        elements = self.grid_elements("ElmPvsys", name, grid)
        return [t.cast("PFTypes.PVSystem", element) for element in elements]

    def ac_current_source(self, name: str = "*", grid: str = "*") -> PFTypes.AcCurrentSource | None:
        return self.first_of(elements=self.ac_current_sources(name=name, grid=grid))

    def ac_current_sources(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.AcCurrentSource]:
        elements = self.grid_elements("ElmIac", name, grid)
        return [t.cast("PFTypes.AcCurrentSource", element) for element in elements]

    def grid(self, name: str = "*") -> PFTypes.Grid | None:
        return self.first_of(elements=self.grids(name=name))

    def grids(self, name: str = "*") -> Sequence[PFTypes.Grid]:
        elements = self.grid_model_elements("ElmNet", name)
        return [t.cast("PFTypes.Grid", element) for element in elements]

    def grid_elements(self, class_name: str, name: str = "*", grid: str = "*") -> Sequence[PFTypes.DataObject]:
        rv = [self.elements_of(element=g, pattern=name + "." + class_name) for g in self.grids(grid)]
        return self.list_from_sequences(*rv)

    def grid_model_elements(self, class_name: str, name: str = "*") -> Sequence[PFTypes.DataObject]:
        return self.elements_of(element=self.grid_model, pattern=name + "." + class_name)

    def equipment_type_elements(self, class_name: str, name: str = "*") -> Sequence[PFTypes.DataObject]:
        return self.elements_of(element=self.types_dir, pattern=name + "." + class_name)

    def study_case_element(
        self,
        class_name: str,
        name: str = "*",
        study_case_name: str = "*",
    ) -> PFTypes.DataObject | None:
        elements = self.study_case_elements(class_name=class_name, name=name, study_case_name=study_case_name)
        if len(elements) == 0:
            return None

        if len(elements) > 1:
            logger.warning("Found more then one element, returning only the first one.")

        return elements[0]

    def study_case_elements(
        self,
        class_name: str,
        name: str = "*",
        study_case_name: str = "*",
    ) -> Sequence[PFTypes.DataObject]:
        rv = [self.elements_of(element=sc, pattern=name + "." + class_name) for sc in self.study_cases(study_case_name)]
        return self.list_from_sequences(*rv)

    def first_of(self, *, elements: Sequence[T]) -> T | None:
        if len(elements) == 0:
            return None

        if len(elements) > 1:
            logger.warning("Found more then one element, returning only the first one.")

        return elements[0]

    def elements_of(
        self,
        *,
        element: PFTypes.DataObject,
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
                class_name="SetVariable",
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
            elements = self.elements_of(element=self.unit_settings_dir, pattern="*.SetVariable")
            return [t.cast("PFTypes.UnitConversionSetting", element) for element in elements]

        return []

    def create_result(
        self,
        *,
        name: str,
        study_case: PFTypes.StudyCase,
        data: dict | None = None,
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.Result | None:
        logger.debug("Create result object {name} ...", name=name)
        if data is None:
            data = {}
        element = self.create_object(
            name=name,
            class_name="ElmRes",
            location=study_case,
            data=data,
            force=force,
            update=update,
        )
        return t.cast("PFTypes.Result", element) if element is not None else None

    def create_object(
        self,
        *,
        name: str,
        class_name: str,
        location: PFTypes.DataDir | PFTypes.StudyCase,
        data: dict[str, t.Any],
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.DataObject | None:
        _elements = self.elements_of(element=location, pattern=f"{name}.{class_name}")
        element = self.first_of(elements=_elements)
        if element is not None and force is False:
            if update is False:
                logger.warning(
                    "{object_name}.{class_name} already exists. Use force=True to create it anyway or update=True to update it.",
                    object_name=name,
                    class_name=class_name,
                )
        else:
            element = location.CreateObject(class_name, name)
            update = True

        if element is not None and update is True:
            return self.update_object(element, data)

        return element

    @staticmethod
    def update_object(element: PFTypes.DataObject, data: dict[str, t.Any]) -> PFTypes.DataObject:
        for key, value in data.items():
            if getattr(element, key, None) is not None:
                setattr(element, key, value)

        return element

    @staticmethod
    def delete_object(element: PFTypes.DataObject) -> None:
        if element.Delete():
            msg = f"Could not delete element {element}."
            raise RuntimeError(msg)

    @staticmethod
    def create_name(element: PFTypes.DataObject, grid_name: str, element_name: str | None = None) -> str:
        """Create a unique name of the object.

        Object type differentiation based on the input parameters. Considers optional parents of the object,
        element.g. in case of detailed template or detailed substation.

        Arguments:
            element {PFTypes.DataObject} -- the object itself for which a unique name is going to be created
            grid_name {str} -- the name of the grid to which the object belongs (root)

        Keyword Arguments:
            element_name {str | None} -- element name if needed to specify independently (default: {None})

        Returns:
            str -- the unique name of the object
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
    def create_generator_name(generator: PFTypes.GeneratorBase, generator_name: str | None = None) -> str:
        """Create a name for a generator object.

        Takes into account models in which the generator might be grouped in.

        Arguments:
            generator {PFTypes.GeneratorBase} -- the generator object

        Keyword Arguments:
            generator_name {str | None} -- name of generator or generator related object (e.g. external controller)
            if needed to specify independently (default: {None})

        Returns:
            str -- the name of the generator object
        """
        if generator_name is None:
            generator_name = generator.loc_name

        if generator.c_pmod is None:  # if generator is not part of higher model
            return generator_name

        return generator.c_pmod.loc_name + PATH_SEP + generator_name

    @staticmethod
    def is_within_substation(terminal: PFTypes.Terminal) -> bool:
        """Check if requested terminal is part of substation (parent).

        Arguments:
            terminal {PFTypes.Terminal} -- the terminal for which the check is requested

        Returns:
            bool -- result of check
        """

        return terminal.cpSubstat is not None

    @staticmethod
    def list_from_sequences(*sequences: Iterable[T]) -> Sequence[T]:
        """Combine iterable sequences with the same base type into one list.

        Arguments:
            sequences {Iterable[T]} -- enumeration of sequences (all the same base type T)

        Returns:
            list -- list of elements of base type T
        """
        return list(itertools.chain.from_iterable([*sequences]))

    @staticmethod
    def filter_none(data: Sequence[T | None]) -> Sequence[T]:
        return [e for e in data if e is not None]
