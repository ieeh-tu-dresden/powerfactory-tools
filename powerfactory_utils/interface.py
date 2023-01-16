# -*- coding: utf-8 -*-

from __future__ import annotations

import dataclasses as dcs
import importlib.util
import itertools
import pathlib
import typing
from typing import TYPE_CHECKING

from loguru import logger

from powerfactory_utils import exceptions
from powerfactory_utils.constants import BaseUnits

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any
    from typing import Literal
    from typing import Optional
    from typing import TypeVar

    from powerfactory_utils import powerfactory_types as pft

    T = TypeVar("T")

POWERFACTORY_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
POWERFACTORY_VERSION = "2022 SP2"
PYTHON_VERSION = "3.9"
PATH_SEP = "/"


@dcs.dataclass
class UnitConversionSetting:
    filtclass: list[str]
    filtvar: str
    digunit: str
    cdigexp: pft.MetricPrefix
    userunit: str
    cuserexp: pft.MetricPrefix
    ufacA: float  # noqa: N815
    ufacB: float  # noqa: N815


@dcs.dataclass
class ProjectUnitSetting:
    ilenunit: Literal[0, 1, 2]
    clenexp: pft.MetricPrefix  # Lengths
    cspqexp: pft.MetricPrefix  # Loads etc.
    cspqexpgen: pft.MetricPrefix  # Generators etc.
    currency: pft.Currency


@dcs.dataclass
class PowerfactoryInterface:  # noqa: H601
    project_name: str
    powerfactory_user_profile: str | None = None
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH
    powerfactory_version: str = POWERFACTORY_VERSION
    python_version: str = PYTHON_VERSION

    def __post_init__(self) -> None:
        pf = self.load_powerfactory_module_from_path()
        self.app = self.connect_to_app(pf)
        self.project = self.connect_to_project(self.project_name)
        if self.project is None:
            raise exceptions.ProjectAccessError

        self.load_project_folders_from_pf_db()
        self.set_default_unit_conversion()

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

    def load_powerfactory_module_from_path(self) -> pft.PowerFactoryModule:
        module_path = (
            self.powerfactory_path / ("Powerfactory " + self.powerfactory_version) / "Python" / self.python_version
        )
        spec = importlib.util.spec_from_file_location(
            "powerfactory",
            module_path / "powerfactory.pyd",
        )
        if spec is not None:
            pfm = importlib.util.module_from_spec(spec)
            if spec.loader is not None:
                spec.loader.exec_module(pfm)
                return typing.cast("pft.PowerFactoryModule", pfm)

        raise exceptions.LoadPFModuleError

    def load_settings_dir_from_pf(self) -> pft.DataDir:
        settings_dir = self.element_of(self.project, pattern="*.SetFold", recursive=False)
        if settings_dir is None:
            raise exceptions.SettingsAccessError

        return typing.cast("pft.DataDir", settings_dir)

    def load_unit_settings_dir_from_pf(self) -> pft.DataDir:
        unit_settings_dir = self.element_of(self.settings_dir, pattern="*.IntUnit", recursive=False)
        if unit_settings_dir is None:
            raise exceptions.UnitSettingsAccessError

        return typing.cast("pft.DataDir", unit_settings_dir)

    def close(self) -> None:
        self.reset_unit_conversion_settings()

    def connect_to_app(self, pf: pft.PowerFactoryModule) -> pft.Application:
        """Connect to PowerFactory Application.

        Arguments:
            pf {pft.PowerFactoryModule} -- the Python module contributed via the PowerFactory system installation

        Returns:
            pft.Application -- the application handle (root)
        """

        try:
            return pf.GetApplicationExt(self.powerfactory_user_profile)
        except pf.ExitError as element:
            raise exceptions.CouldNotCloseAppError from element

    def connect_to_project(self, project_name: str) -> pft.Project:
        """Connect to a PowerFactory project.

        Arguments:
            project_name {str} -- the name of the project to be connected/activated

        Returns:
            pft.Project -- the project handle
        """

        self.activate_project(project_name)

        project = self.app.GetActiveProject()
        if project is None:
            raise exceptions.ProjectAccessError

        return project

    def activate_grid(self, grid: pft.Grid) -> None:
        if grid.Activate():
            raise exceptions.GridActivationError

    def deactivate_grids(self) -> None:
        for grid in self.grids():
            self.deactivate_grid(grid)

    def deactivate_grid(self, grid: pft.Grid) -> None:
        if grid.Deactivate():
            raise exceptions.GridDeactivationError

    def activate_scenario(self, scen: pft.Scenario) -> None:
        if scen.Activate():
            raise exceptions.ScenarioActivationError

    def deactivate_scenario(self, scen: pft.Scenario) -> None:
        if scen.Deactivate():
            raise exceptions.ScenarioDeactivationError

    def activate_study_case(self, stc: pft.StudyCase) -> None:
        if stc.Activate():
            raise exceptions.StudyCaseActivationError

    def deactivate_study_case(self, stc: pft.StudyCase) -> None:
        if stc.Deactivate():
            raise exceptions.StudyCaseDeactivationError

    def set_default_unit_conversion(self) -> None:
        self.save_unit_conversion_settings_to_temp()
        project_settings = self.load_project_settings_dir_from_pf()
        project_settings.ilenunit = 0
        project_settings.clenexp = BaseUnits.LENGTH
        project_settings.cspqexp = BaseUnits.POWER
        project_settings.cspqexpgen = BaseUnits.POWER
        project_settings.currency = BaseUnits.CURRENCY
        for cls, data in BaseUnits.UNITCONVERSIONS.items():
            for (unit, base_exp, exp) in data:
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

    def save_unit_conversion_settings_to_temp(self) -> None:
        project_settings = self.load_project_settings_dir_from_pf()
        self.project_unit_setting = ProjectUnitSetting(
            ilenunit=project_settings.ilenunit,
            clenexp=project_settings.clenexp,
            cspqexp=project_settings.cspqexp,
            cspqexpgen=project_settings.cspqexpgen,
            currency=project_settings.currency,
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

    def reset_unit_conversion_settings(self) -> None:
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

    def load_project_settings_dir_from_pf(self) -> pft.ProjectSettings:
        project_settings = self.project.pPrjSettings
        if project_settings is None:
            raise exceptions.ProjectSettingsAccessError

        return project_settings

    def reset_project(self) -> None:
        self.deactivate_project()
        self.activate_project(self.project_name)

    def activate_project(self, name: str) -> None:
        if self.app.ActivateProject(name + ".IntPrj"):
            raise exceptions.ProjectActivationError

    def deactivate_project(self) -> None:
        if self.project.Deactivate():
            raise exceptions.ProjectDeactivationError

    def subloads_of(self, load: pft.LoadLV) -> list[pft.LoadLVP]:
        elements = self.elements_of(load, pattern="*.ElmLodlvp")
        return [typing.cast("pft.LoadLVP", element) for element in elements]

    def unit_conversion_settings(self) -> list[pft.UnitConversionSetting]:
        elements = self.elements_of(self.unit_settings_dir, pattern="*.SetVariable")
        return [typing.cast("pft.UnitConversionSetting", element) for element in elements]

    def study_case(self, name: str = "*") -> pft.StudyCase | None:
        element = self.element_of(self.study_case_dir, name)
        return typing.cast("pft.StudyCase", element) if element is not None else None

    def study_cases(self, name: str = "*") -> list[pft.StudyCase]:
        elements = self.elements_of(self.study_case_dir, name)
        return [typing.cast("pft.StudyCase", element) for element in elements]

    def scenario(self, name: str = "*") -> pft.Scenario | None:
        element = self.element_of(self.scenario_dir, name)
        return typing.cast("pft.Scenario", element) if element is not None else None

    def scenarios(self, name: str = "*") -> list[pft.Scenario]:
        elements = self.elements_of(self.scenario_dir, name)
        return [typing.cast("pft.Scenario", element) for element in elements]

    def line_type(self, name: str = "*") -> pft.LineType | None:
        element = self.grid_model_element("TypLne", name)
        return typing.cast("pft.LineType", element) if element is not None else None

    def line_types(self, name: str = "*") -> list[pft.LineType]:
        elements = self.grid_model_elements("TypLne", name)
        return [typing.cast("pft.LineType", element) for element in elements]

    def load_type(self, name: str = "*") -> pft.DataObject | None:  # noqa: FNE004
        return self.grid_model_element("TypLod", name)

    def load_types(self, name: str = "*") -> list[pft.DataObject]:  # noqa: FNE004
        return self.grid_model_elements("TypLod", name)

    def transformer_2w_type(self, name: str = "*") -> pft.Transformer2WType | None:
        element = self.grid_model_element("TypTr2", name)
        return typing.cast("pft.Transformer2WType", element) if element is not None else None

    def transformer_2w_types(self, name: str = "*") -> list[pft.Transformer2WType]:
        elements = self.grid_model_elements("TypTr2", name)
        return [typing.cast("pft.Transformer2WType", element) for element in elements]

    def area(self, name: str = "*") -> pft.DataObject | None:
        return self.grid_model_element("ElmArea", name)

    def areas(self, name: str = "*") -> list[pft.DataObject]:
        return self.grid_model_elements("ElmArea", name)

    def zone(self, name: str = "*") -> pft.DataObject | None:
        return self.grid_model_element("ElmZone", name)

    def zones(self, name: str = "*") -> list[pft.DataObject]:
        return self.grid_model_elements("ElmZone", name)

    def grid(self, name: str = "*") -> pft.Grid | None:
        element = self.grid_model_element("ElmNet", name)
        return typing.cast("pft.Grid", element) if element is not None else None

    def grids(self, name: str = "*") -> list[pft.Grid]:
        elements = self.grid_model_elements("ElmNet", name)
        return [typing.cast("pft.Grid", element) for element in elements]

    def grid_model_element(self, class_name: str, name: str = "*") -> pft.DataObject | None:
        return self.element_of(self.grid_model, name + "." + class_name)

    def grid_model_elements(self, class_name: str, name: str = "*") -> list[pft.DataObject]:
        return self.elements_of(self.grid_model, name + "." + class_name)

    def grid_diagram(self, grid: str = "*") -> pft.GridDiagram | None:
        element = self.grid_element("IntGrfnet", grid=grid)
        return typing.cast("pft.GridDiagram", element) if element is not None else None

    def grid_diagrams(self, grid: str = "*") -> list[pft.GridDiagram]:
        elements = self.grid_elements("IntGrfnet", grid=grid)
        return [typing.cast("pft.GridDiagram", element) for element in elements]

    def external_grid(self, name: str = "*", grid: str = "*") -> pft.ExternalGrid | None:
        element = self.grid_element("ElmXNet", name, grid)
        return typing.cast("pft.ExternalGrid", element) if element is not None else None

    def external_grids(self, name: str = "*", grid: str = "*") -> list[pft.ExternalGrid]:
        elements = self.grid_elements("ElmXNet", name, grid)
        return [typing.cast("pft.ExternalGrid", element) for element in elements]

    def terminal(self, name: str = "*", grid: str = "*") -> pft.Terminal | None:
        element = self.grid_element("ElmTerm", name, grid)
        return typing.cast("pft.Terminal", element) if element is not None else None

    def terminals(self, name: str = "*", grid: str = "*") -> list[pft.Terminal]:
        elements = self.grid_elements("ElmTerm", name, grid)
        return [typing.cast("pft.Terminal", element) for element in elements]

    def cubicle(self, name: str = "*", grid: str = "*") -> pft.StationCubicle | None:
        element = self.grid_elements("StaCubic", name, grid)
        return typing.cast("pft.StationCubicle", element) if element is not None else None

    def cubicles(self, name: str = "*", grid: str = "*") -> list[pft.StationCubicle]:
        elements = self.grid_elements("StaCubic", name, grid)
        return [typing.cast("pft.StationCubicle", element) for element in elements]

    def coupler(self, name: str = "*", grid: str = "*") -> pft.Coupler | None:
        element = self.grid_element("ElmCoup", name, grid)
        return typing.cast("pft.Coupler", element) if element is not None else None

    def couplers(self, name: str = "*", grid: str = "*") -> list[pft.Coupler]:
        elements = self.grid_elements("ElmCoup", name, grid)
        return [typing.cast("pft.Coupler", element) for element in elements]

    def switch(self, name: str = "*", grid: str = "*") -> pft.Switch | None:
        element = self.grid_element("StaSwitch", name, grid)
        return typing.cast("pft.Switch", element) if element is not None else None

    def switches(self, name: str = "*", grid: str = "*") -> list[pft.Switch]:
        elements = self.grid_elements("StaSwitch", name, grid)
        return [typing.cast("pft.Switch", element) for element in elements]

    def fuse(self, name: str = "*", grid: str = "*") -> pft.Fuse | None:
        element = self.grid_element("RelFuse", name, grid)
        return typing.cast("pft.Fuse", element) if element is not None else None

    def fuses(self, name: str = "*", grid: str = "*") -> list[pft.Fuse]:
        elements = self.grid_elements("RelFuse", name, grid)
        return [typing.cast("pft.Fuse", element) for element in elements]

    def line(self, name: str = "*", grid: str = "*") -> pft.Line | None:
        element = self.grid_element("ElmLne", name, grid)
        return typing.cast("pft.Line", element) if element is not None else None

    def lines(self, name: str = "*", grid: str = "*") -> list[pft.Line]:
        elements = self.grid_elements("ElmLne", name, grid)
        return [typing.cast("pft.Line", element) for element in elements]

    def transformer_2w(self, name: str = "*", grid: str = "*") -> pft.Transformer2W | None:
        element = self.grid_element("ElmTr2", name, grid)
        return typing.cast("pft.Transformer2W", element) if element is not None else None

    def transformers_2w(self, name: str = "*", grid: str = "*") -> list[pft.Transformer2W]:
        elements = self.grid_elements("ElmTr2", name, grid)
        return [typing.cast("pft.Transformer2W", element) for element in elements]

    def transformer_3w(self, name: str = "*", grid: str = "*") -> pft.Transformer3W | None:
        element = self.grid_element("ElmTr3", name, grid)
        return typing.cast("pft.Transformer3W", element) if element is not None else None

    def transformers_3w(self, name: str = "*", grid: str = "*") -> list[pft.Transformer3W]:
        elements = self.grid_elements("ElmTr3", name, grid)
        return [typing.cast("pft.Transformer3W", element) for element in elements]

    def load(self, name: str = "*", grid: str = "*") -> pft.Load | None:  # noqa: FNE004
        element = self.grid_element("ElmLod", name, grid)
        return typing.cast("pft.Load", element) if element is not None else None

    def loads(self, name: str = "*", grid: str = "*") -> list[pft.Load]:
        elements = self.grid_elements("ElmLod", name, grid)
        return [typing.cast("pft.Load", element) for element in elements]

    def load_lv(self, name: str = "*", grid: str = "*") -> pft.LoadLV | None:  # noqa: FNE004
        element = self.grid_element("ElmLodLv", name, grid)
        return typing.cast("pft.LoadLV", element) if element is not None else None

    def loads_lv(self, name: str = "*", grid: str = "*") -> list[pft.LoadLV]:
        elements = self.grid_elements("ElmLodLv", name, grid)
        return [typing.cast("pft.LoadLV", element) for element in elements]

    def load_mv(self, name: str = "*", grid: str = "*") -> pft.LoadMV | None:  # noqa: FNE004
        element = self.grid_element("ElmLodMv", name, grid)
        return typing.cast("pft.LoadMV", element) if element is not None else None

    def loads_mv(self, name: str = "*", grid: str = "*") -> list[pft.LoadMV]:
        elements = self.grid_elements("ElmLodMv", name, grid)
        return [typing.cast("pft.LoadMV", element) for element in elements]

    def generator(self, name: str = "*", grid: str = "*") -> pft.Generator | None:
        element = self.grid_element("ElmGenstat", name, grid)
        return typing.cast("pft.Generator", element) if element is not None else None

    def generators(self, name: str = "*", grid: str = "*") -> list[pft.Generator]:
        elements = self.grid_elements("ElmGenstat", name, grid)
        return [typing.cast("pft.Generator", element) for element in elements]

    def pv_system(self, name: str = "*", grid: str = "*") -> pft.PVSystem | None:
        element = self.grid_element("ElmPvsys", name, grid)
        return typing.cast("pft.PVSystem", element) if element is not None else None

    def pv_systems(self, name: str = "*", grid: str = "*") -> list[pft.PVSystem]:
        elements = self.grid_elements("ElmPvsys", name, grid)
        return [typing.cast("pft.PVSystem", element) for element in elements]

    def grid_element(self, class_name: str, name: str = "*", grid: str = "*") -> pft.DataObject | None:
        elements = self.grid_elements(class_name=class_name, name=name, grid=grid)
        if len(elements) == 0:
            return None

        if len(elements) > 1:
            logger.warning("Found more then one element, returning only the first one.")

        return elements[0]

    def grid_elements(self, class_name: str, name: str = "*", grid: str = "*") -> list[pft.DataObject]:
        rv = [self.elements_of(g, name + "." + class_name) for g in self.grids(grid)]
        return self.list_from_sequences(*rv)

    def create_unit_conversion_setting(self, name: str, uc: UnitConversionSetting) -> pft.UnitConversionSetting | None:
        data = dcs.asdict(uc)
        element = self.create_object(name=name, class_name="SetVariable", location=self.unit_settings_dir, data=data)
        return typing.cast("pft.UnitConversionSetting", element) if element is not None else None

    def delete_unit_conversion_settings(self) -> bool:
        ucs = self.unit_conversion_settings()
        rvs = [self.delete_object(uc) for uc in ucs]
        return all(rvs)

    def create_object(
        self,
        name: str,
        class_name: str,
        location: pft.DataDir,
        data: dict[str, Any],
        force: bool = False,
        update: bool = True,
    ) -> pft.DataObject | None:
        element = self.element_of(location, pattern=f"{name}.{class_name}")
        if element is not None and force is False:
            if update is False:
                logger.warning(
                    "%s.%s already exists. Use force=True to create it anyway or update=True to update it.",
                    name,
                    class_name,
                )
        else:
            element = location.CreateObject(class_name, name)
            update = True

        if element is not None and update is True:
            return self.update_object(element, data)

        return element

    def element_of(self, element: pft.DataObject, pattern: str = "*", recursive: bool = True) -> pft.DataObject | None:
        elements = self.elements_of(element, pattern=pattern, recursive=recursive)
        if len(elements) == 0:
            return None
        if len(elements) > 1:
            logger.warning("Found more then one element, returning only the first one.")
        return elements[0]

    def elements_of(self, element: pft.DataObject, pattern: str = "*", recursive: bool = True) -> list[pft.DataObject]:
        return element.GetContents(pattern, recursive)

    @staticmethod
    def update_object(element: pft.DataObject, data: dict[str, Any]) -> pft.DataObject:
        for k, v in data.items():
            if getattr(element, k, None) is not None:
                setattr(element, k, v)
        return element

    @staticmethod
    def delete_object(element: pft.DataObject) -> None:
        return element.Delete() == 0

    @staticmethod
    def create_name(element: pft.DataObject, grid_name: str, element_name: str | None = None) -> str:
        """Create a unique name of the object.

        Object type differentiation based on the input parameters. Considers optional parents of the object,
        element.g. in case of detailed template or detailed substation.

        Arguments:
            element {pft.DataObject} -- the object itself for which a unique name is going to be created
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
            cp_substat: pft.DataObject | None = getattr(element, "cpSubstat", None)
            if cp_substat is not None:
                return cp_substat.loc_name + PATH_SEP + element_name

            return parent.loc_name + PATH_SEP + element_name

        return element_name

    @staticmethod
    def create_generator_name(generator: pft.GeneratorBase, generator_name: str | None = None) -> str:
        """Create a name for a generator object.

        Takes into account models in which the generator might be grouped in.

        Arguments:
            generator {pft.GeneratorBase} -- the generator object

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
    def is_within_substation(terminal: pft.Terminal) -> bool:
        """Check if requested terminal is part of substation (parent).

        Arguments:
            terminal {pft.Terminal} -- the terminal for which the check is requested

        Returns:
            bool -- result of check
        """

        return terminal.cpSubstat is not None

    @staticmethod
    def list_from_sequences(*sequences: Iterable[T]) -> list[T]:
        """Combine iterable sequences with the same base type into one list.

        Arguments:
            sequences {Iterable[T]} -- enumeration of sequences (all the same base type T)

        Returns:
            list -- list of elements of base type T
        """
        return list(itertools.chain.from_iterable([*sequences]))
