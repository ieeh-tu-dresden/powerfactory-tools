# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import contextlib
import importlib.util
import itertools
import pathlib
import typing
from collections.abc import Sequence  # noqa: TCH003 # bug
from typing import TYPE_CHECKING

import pydantic
from loguru import logger

from powerfactory_tools.constants import BaseUnits
from powerfactory_tools.powerfactory_types import Currency
from powerfactory_tools.powerfactory_types import MetricPrefix
from powerfactory_tools.powerfactory_types import UnitSystem
from powerfactory_tools.schema.base import Base

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any
    from typing import TypeVar

    from powerfactory_tools.powerfactory_types import PowerFactoryTypes as PFTypes

    T = TypeVar("T")

POWERFACTORY_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
POWERFACTORY_VERSION = "2022 SP2"
PYTHON_VERSION = "3.10"
PATH_SEP = "/"


class UnitConversionSetting(Base):
    filtclass: Sequence[str]
    filtvar: str
    digunit: str
    cdigexp: MetricPrefix
    userunit: str
    cuserexp: MetricPrefix
    ufacA: float  # noqa: N815
    ufacB: float  # noqa: N815


class ProjectUnitSetting(Base):
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
    powerfactory_user_profile: str | None = None
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH
    powerfactory_version: str = POWERFACTORY_VERSION
    python_version: str = PYTHON_VERSION

    def __post_init__(self) -> None:
        try:
            logger.info("Starting PowerFactory Interface...")
            pf = self.load_powerfactory_module_from_path()
            self.app = self.connect_to_app(pf)
            self.project = self.connect_to_project(self.project_name)
            self.load_project_folders_from_pf_db()
            self.stash_unit_conversion_settings()
            self.set_default_unit_conversion()
            logger.info("Starting PowerFactory Interface... Done.")
        except RuntimeError:
            logger.exception("Could not start PowerFactory Interface. Shutting down...")
            self.close()

    def load_project_folders_from_pf_db(self) -> None:
        self.grid_model = self.app.GetProjectFolder("netmod")
        self.types_dir = self.app.GetProjectFolder("equip")
        self.op_dir = self.app.GetProjectFolder("oplib")
        self.chars_dir = self.app.GetProjectFolder("chars")

        project_settings_dir = self.load_project_settings_dir_from_pf()

        self.ext_data_dir = project_settings_dir.extDataDir

        self.grid_data = self.app.GetProjectFolder("netdat")
        self.study_case_dir = self.app.GetProjectFolder("study")
        self.scenario_dir = self.app.GetProjectFolder("scen")
        self.grid_graphs_dir = self.app.GetProjectFolder("dia")
        self.settings_dir = self.load_settings_dir_from_pf()
        self.unit_settings_dir = self.load_unit_settings_dir_from_pf()

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
        return typing.cast("PFTypes.PowerFactoryModule", pfm)

    def load_settings_dir_from_pf(self) -> PFTypes.DataDir:
        logger.debug("Loading settings from PowerFactory...")
        settings_dir = self.element_of(element=self.project, pattern="*.SetFold", recursive=False)
        if settings_dir is None:
            msg = "Could not access settings."
            raise RuntimeError(msg)

        logger.debug("Loading settings from PowerFactory... Done.")
        return typing.cast("PFTypes.DataDir", settings_dir)

    def load_unit_settings_dir_from_pf(self) -> PFTypes.DataDir | None:
        logger.debug("Loading unit settings from PowerFactory...")
        unit_settings_dir = self.element_of(element=self.settings_dir, pattern="*.IntUnit", recursive=False)
        if unit_settings_dir is None:
            return None

        logger.debug("Loading unit settings from PowerFactory... Done.")
        return typing.cast("PFTypes.DataDir", unit_settings_dir)

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
        try:
            return pf.GetApplicationExt(self.powerfactory_user_profile)
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

        logger.debug("Activating project {project_name} application...", project_name=project_name)
        self.activate_project(project_name)

        project = self.app.GetActiveProject()
        if project is None:
            msg = "Could not access project."
            raise RuntimeError(msg)

        logger.debug("Activating project {project_name} application... Done.", project_name=project_name)
        return project

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
        logger.debug("Activating scenario {scenario_name} application...", scenario_name=scen.loc_name)
        active_scen = self.app.GetActiveScenario()
        if active_scen != scen and scen.Activate():
            msg = "Could not activate scenario."
            raise RuntimeError(msg)

    def deactivate_scenario(self, scen: PFTypes.Scenario) -> None:
        logger.debug("Deactivating scenario {scenario_name} application...", scenario_name=scen.loc_name)
        if scen.Deactivate():
            msg = "Could not deactivate scenario."
            raise RuntimeError(msg)

    def activate_study_case(self, stc: PFTypes.StudyCase) -> None:
        logger.debug("Activating study_case {study_case_name} application...", study_case_name=stc.loc_name)
        if stc.Activate():
            msg = "Could not activate case study."
            raise RuntimeError(msg)

    def deactivate_study_case(self, stc: PFTypes.StudyCase) -> None:
        logger.debug("Deactivating study_case {study_case_name} application...", study_case_name=stc.loc_name)
        if stc.Deactivate():
            msg = "Could not deactivate case study."
            raise RuntimeError(msg)

    def set_default_unit_conversion(self) -> None:
        logger.debug("Applying exporter default unit conversion settings...")
        project_settings = self.load_project_settings_dir_from_pf()
        project_settings.ilenunit = DEFAULT_PROJECT_UNIT_SETTING.ilenunit
        project_settings.clenexp = DEFAULT_PROJECT_UNIT_SETTING.clenexp
        project_settings.cspqexp = DEFAULT_PROJECT_UNIT_SETTING.cspqexp
        project_settings.cspqexpgen = DEFAULT_PROJECT_UNIT_SETTING.cspqexpgen
        project_settings.currency = DEFAULT_PROJECT_UNIT_SETTING.currency
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
        project_settings = self.load_project_settings_dir_from_pf()
        self.project_unit_setting = ProjectUnitSetting(
            ilenunit=UnitSystem(project_settings.ilenunit),
            clenexp=MetricPrefix(project_settings.clenexp),
            cspqexp=MetricPrefix(project_settings.cspqexp),
            cspqexpgen=MetricPrefix(project_settings.cspqexpgen),
            currency=Currency(project_settings.currency),
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
        project_settings = self.load_project_settings_dir_from_pf()
        project_settings.ilenunit = self.project_unit_setting.ilenunit
        project_settings.clenexp = self.project_unit_setting.clenexp
        project_settings.cspqexp = self.project_unit_setting.cspqexp
        project_settings.cspqexpgen = self.project_unit_setting.cspqexpgen
        project_settings.currency = self.project_unit_setting.currency
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
        return [typing.cast("PFTypes.LoadLVP", element) for element in elements]

    def study_case(self, name: str = "*") -> PFTypes.StudyCase | None:
        element = self.element_of(element=self.study_case_dir, pattern=name)
        return typing.cast("PFTypes.StudyCase", element) if element is not None else None

    def study_cases(self, name: str = "*") -> Sequence[PFTypes.StudyCase]:
        elements = self.elements_of(element=self.study_case_dir, pattern=name)
        return [typing.cast("PFTypes.StudyCase", element) for element in elements]

    def scenario(self, name: str = "*") -> PFTypes.Scenario | None:
        element = self.element_of(element=self.scenario_dir, pattern=name)
        return typing.cast("PFTypes.Scenario", element) if element is not None else None

    def scenarios(self, name: str = "*") -> Sequence[PFTypes.Scenario]:
        elements = self.elements_of(element=self.scenario_dir, pattern=name)
        return [typing.cast("PFTypes.Scenario", element) for element in elements]

    def line_type(self, name: str = "*") -> PFTypes.LineType | None:
        element = self.grid_model_element("TypLne", name)
        return typing.cast("PFTypes.LineType", element) if element is not None else None

    def line_types(self, name: str = "*") -> Sequence[PFTypes.LineType]:
        elements = self.grid_model_elements("TypLne", name)
        return [typing.cast("PFTypes.LineType", element) for element in elements]

    def load_type(self, name: str = "*") -> PFTypes.DataObject | None:
        return self.grid_model_element("TypLod", name)

    def load_types(self, name: str = "*") -> Sequence[PFTypes.DataObject]:
        return self.grid_model_elements("TypLod", name)

    def transformer_2w_type(self, name: str = "*") -> PFTypes.Transformer2WType | None:
        element = self.grid_model_element("TypTr2", name)
        return typing.cast("PFTypes.Transformer2WType", element) if element is not None else None

    def transformer_2w_types(self, name: str = "*") -> Sequence[PFTypes.Transformer2WType]:
        elements = self.grid_model_elements("TypTr2", name)
        return [typing.cast("PFTypes.Transformer2WType", element) for element in elements]

    def area(self, name: str = "*") -> PFTypes.DataObject | None:
        return self.grid_model_element("ElmArea", name)

    def areas(self, name: str = "*") -> Sequence[PFTypes.DataObject]:
        return self.grid_model_elements("ElmArea", name)

    def zone(self, name: str = "*") -> PFTypes.DataObject | None:
        return self.grid_model_element("ElmZone", name)

    def zones(self, name: str = "*") -> Sequence[PFTypes.DataObject]:
        return self.grid_model_elements("ElmZone", name)

    def grid_diagram(self, grid: str = "*") -> PFTypes.GridDiagram | None:
        element = self.grid_element("IntGrfnet", grid=grid)
        return typing.cast("PFTypes.GridDiagram", element) if element is not None else None

    def grid_diagrams(self, grid: str = "*") -> Sequence[PFTypes.GridDiagram]:
        elements = self.grid_elements("IntGrfnet", grid=grid)
        return [typing.cast("PFTypes.GridDiagram", element) for element in elements]

    def external_grid(self, name: str = "*", grid: str = "*") -> PFTypes.ExternalGrid | None:
        element = self.grid_element("ElmXNet", name, grid)
        return typing.cast("PFTypes.ExternalGrid", element) if element is not None else None

    def external_grids(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.ExternalGrid]:
        elements = self.grid_elements("ElmXNet", name, grid)
        return [typing.cast("PFTypes.ExternalGrid", element) for element in elements]

    def terminal(self, name: str = "*", grid: str = "*") -> PFTypes.Terminal | None:
        element = self.grid_element("ElmTerm", name, grid)
        return typing.cast("PFTypes.Terminal", element) if element is not None else None

    def terminals(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Terminal]:
        elements = self.grid_elements("ElmTerm", name, grid)
        return [typing.cast("PFTypes.Terminal", element) for element in elements]

    def cubicle(self, name: str = "*", grid: str = "*") -> PFTypes.StationCubicle | None:
        element = self.grid_elements("StaCubic", name, grid)
        return typing.cast("PFTypes.StationCubicle", element) if element is not None else None

    def cubicles(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.StationCubicle]:
        elements = self.grid_elements("StaCubic", name, grid)
        return [typing.cast("PFTypes.StationCubicle", element) for element in elements]

    def coupler(self, name: str = "*", grid: str = "*") -> PFTypes.Coupler | None:
        element = self.grid_element("ElmCoup", name, grid)
        return typing.cast("PFTypes.Coupler", element) if element is not None else None

    def couplers(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Coupler]:
        elements = self.grid_elements("ElmCoup", name, grid)
        return [typing.cast("PFTypes.Coupler", element) for element in elements]

    def switch(self, name: str = "*", grid: str = "*") -> PFTypes.Switch | None:
        element = self.grid_element("StaSwitch", name, grid)
        return typing.cast("PFTypes.Switch", element) if element is not None else None

    def switches(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Switch]:
        elements = self.grid_elements("StaSwitch", name, grid)
        return [typing.cast("PFTypes.Switch", element) for element in elements]

    def fuse(self, name: str = "*", grid: str = "*") -> PFTypes.Fuse | None:
        element = self.grid_element("RelFuse", name, grid)
        return typing.cast("PFTypes.Fuse", element) if element is not None else None

    def fuses(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Fuse]:
        elements = self.grid_elements("RelFuse", name, grid)
        return [typing.cast("PFTypes.Fuse", element) for element in elements]

    def line(self, name: str = "*", grid: str = "*") -> PFTypes.Line | None:
        element = self.grid_element("ElmLne", name, grid)
        return typing.cast("PFTypes.Line", element) if element is not None else None

    def lines(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Line]:
        elements = self.grid_elements("ElmLne", name, grid)
        return [typing.cast("PFTypes.Line", element) for element in elements]

    def transformer_2w(self, name: str = "*", grid: str = "*") -> PFTypes.Transformer2W | None:
        element = self.grid_element("ElmTr2", name, grid)
        return typing.cast("PFTypes.Transformer2W", element) if element is not None else None

    def transformers_2w(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Transformer2W]:
        elements = self.grid_elements("ElmTr2", name, grid)
        return [typing.cast("PFTypes.Transformer2W", element) for element in elements]

    def transformer_3w(self, name: str = "*", grid: str = "*") -> PFTypes.Transformer3W | None:
        element = self.grid_element("ElmTr3", name, grid)
        return typing.cast("PFTypes.Transformer3W", element) if element is not None else None

    def transformers_3w(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Transformer3W]:
        elements = self.grid_elements("ElmTr3", name, grid)
        return [typing.cast("PFTypes.Transformer3W", element) for element in elements]

    def load(self, name: str = "*", grid: str = "*") -> PFTypes.Load | None:
        element = self.grid_element("ElmLod", name, grid)
        return typing.cast("PFTypes.Load", element) if element is not None else None

    def loads(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Load]:
        elements = self.grid_elements("ElmLod", name, grid)
        return [typing.cast("PFTypes.Load", element) for element in elements]

    def load_lv(self, name: str = "*", grid: str = "*") -> PFTypes.LoadLV | None:
        element = self.grid_element("ElmLodLv", name, grid)
        return typing.cast("PFTypes.LoadLV", element) if element is not None else None

    def loads_lv(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.LoadLV]:
        elements = self.grid_elements("ElmLodLv", name, grid)
        return [typing.cast("PFTypes.LoadLV", element) for element in elements]

    def load_mv(self, name: str = "*", grid: str = "*") -> PFTypes.LoadMV | None:
        element = self.grid_element("ElmLodMv", name, grid)
        return typing.cast("PFTypes.LoadMV", element) if element is not None else None

    def loads_mv(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.LoadMV]:
        elements = self.grid_elements("ElmLodMv", name, grid)
        return [typing.cast("PFTypes.LoadMV", element) for element in elements]

    def generator(self, name: str = "*", grid: str = "*") -> PFTypes.Generator | None:
        element = self.grid_element("ElmGenstat", name, grid)
        return typing.cast("PFTypes.Generator", element) if element is not None else None

    def generators(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.Generator]:
        elements = self.grid_elements("ElmGenstat", name, grid)
        return [typing.cast("PFTypes.Generator", element) for element in elements]

    def pv_system(self, name: str = "*", grid: str = "*") -> PFTypes.PVSystem | None:
        element = self.grid_element("ElmPvsys", name, grid)
        return typing.cast("PFTypes.PVSystem", element) if element is not None else None

    def pv_systems(self, name: str = "*", grid: str = "*") -> Sequence[PFTypes.PVSystem]:
        elements = self.grid_elements("ElmPvsys", name, grid)
        return [typing.cast("PFTypes.PVSystem", element) for element in elements]

    def grid_element(self, class_name: str, name: str = "*", grid: str = "*") -> PFTypes.DataObject | None:
        elements = self.grid_elements(class_name=class_name, name=name, grid=grid)
        if len(elements) == 0:
            return None

        if len(elements) > 1:
            logger.warning("Found more then one element, returning only the first one.")

        return elements[0]

    def grid_elements(self, class_name: str, name: str = "*", grid: str = "*") -> Sequence[PFTypes.DataObject]:
        rv = [self.elements_of(element=g, pattern=name + "." + class_name) for g in self.grids(grid)]
        return self.list_from_sequences(*rv)

    def grid(self, name: str = "*") -> PFTypes.Grid | None:
        element = self.grid_model_element("ElmNet", name)
        return typing.cast("PFTypes.Grid", element) if element is not None else None

    def grids(self, name: str = "*") -> Sequence[PFTypes.Grid]:
        elements = self.grid_model_elements("ElmNet", name)
        return [typing.cast("PFTypes.Grid", element) for element in elements]

    def grid_model_element(self, class_name: str, name: str = "*") -> PFTypes.DataObject | None:
        return self.element_of(element=self.grid_model, pattern=name + "." + class_name)

    def grid_model_elements(self, class_name: str, name: str = "*") -> Sequence[PFTypes.DataObject]:
        return self.elements_of(element=self.grid_model, pattern=name + "." + class_name)

    def create_unit_conversion_setting(
        self,
        name: str,
        uc: UnitConversionSetting,
    ) -> PFTypes.UnitConversionSetting | None:
        if self.unit_settings_dir is not None:
            data = uc.dict()
            element = self.create_object(
                name=name,
                class_name="SetVariable",
                location=self.unit_settings_dir,
                data=data,
            )
            return typing.cast("PFTypes.UnitConversionSetting", element) if element is not None else None

        return None

    def delete_unit_conversion_settings(self) -> None:
        ucs = self.unit_conversion_settings()
        for uc in ucs:
            self.delete_object(uc)

    def unit_conversion_settings(self) -> Sequence[PFTypes.UnitConversionSetting]:
        if self.unit_settings_dir is not None:
            elements = self.elements_of(element=self.unit_settings_dir, pattern="*.SetVariable")
            return [typing.cast("PFTypes.UnitConversionSetting", element) for element in elements]

        return []

    def create_object(
        self,
        *,
        name: str,
        class_name: str,
        location: PFTypes.DataDir,
        data: dict[str, Any],
        force: bool = False,
        update: bool = True,
    ) -> PFTypes.DataObject | None:
        element = self.element_of(element=location, pattern=f"{name}.{class_name}")
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

    def element_of(
        self,
        *,
        element: PFTypes.DataObject,
        pattern: str = "*",
        recursive: bool = True,
    ) -> PFTypes.DataObject | None:
        elements = self.elements_of(element=element, pattern=pattern, recursive=recursive)
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

    @staticmethod
    def update_object(element: PFTypes.DataObject, data: dict[str, Any]) -> PFTypes.DataObject:
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
