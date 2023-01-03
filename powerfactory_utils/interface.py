# -*- coding: utf-8 -*-

from __future__ import annotations

import importlib.util
import itertools
import pathlib
import typing
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from powerfactory_utils import exceptions
from powerfactory_utils import powerfactory_types as pft

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import TypeVar

    T = TypeVar("T")

POWERFACTORY_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
POWERFACTORY_VERSION = "2022 SP2"
PYTHON_VERSION = "3.9"
PATH_SEP = "/"


@dataclass
class PowerfactoryInterface:
    project_name: str
    powerfactory_user_profile: str | None = None
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH
    powerfactory_version: str = POWERFACTORY_VERSION
    python_version: str = PYTHON_VERSION

    def __post_init__(self) -> None:
        try:
            pfm = self.load_powerfactory_module_from_path()
            self.app = self.connect_to_app(pfm)
            self.project = self.connect_to_project(self.project_name)
            self.load_project_folders_from_pf()
        except RuntimeError:
            logger.exception("Could not start PowerFactoryInterface.")
            raise

    def load_project_folders_from_pf(self) -> None:
        self.grid_model = self.load_grid_model_from_pf()
        self.types_lib = self.load_asset_types_lib_from_pf()
        self.op_lib = self.load_operational_data_lib_from_pf()
        self.chars_lib = self.load_characteristics_lib_from_pf()
        self.ext_data_dir = self.load_ext_data_dir_from_pf()

        self.grid_data = self.load_grid_data_from_pf()
        self.study_case_lib = self.load_study_case_lib_from_pf()
        self.scenario_lib = self.load_scenario_lib_from_pf()
        self.grid_graphs_dir = self.load_grid_graphs_from_pf()

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

        success = self.activate_project(project_name)
        if success:
            project = self.fetch_active_project()
            if project is not None:
                return project

        raise RuntimeError(f"Could not connect to Powerfactory project {project_name}.")

    def activate_project(self, name: str) -> None:
        if self.app.ActivateProject(name + ".IntPrj"):
            raise exceptions.ProjectActivationError

    def activate_grid(self, grid: pft.Grid) -> None:
        if grid.Activate():
            raise exceptions.GridActivationError

    def deactivate_grids(self) -> None:
        [self.deactivate_grid(g) for g in self.grids()]

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

    def fetch_active_project(self) -> pft.Project:
        return self.app.GetActiveProject()

    def load_grid_model_from_pf(self) -> pft.DataObject:
        return self.app.GetProjectFolder("netmod")

    def load_asset_types_lib_from_pf(self) -> pft.DataObject:
        return self.app.GetProjectFolder("equip")

    def load_operational_data_lib_from_pf(self) -> pft.DataObject:
        return self.app.GetProjectFolder("oplib")

    def load_characteristics_lib_from_pf(self) -> pft.DataObject:
        return self.app.GetProjectFolder("chars")

    def load_ext_data_dir_from_pf(self) -> pft.DataObject:
        project_settings = self.project.pPrjSettings
        if project_settings is not None:
            data_dir = project_settings.extDataDir
            return typing.cast("pft.DataObject", data_dir)

        raise exceptions.DataDirAccessError

    def load_grid_data_from_pf(self) -> pft.DataObject:
        return self.app.GetProjectFolder("netdat")

    def load_study_case_lib_from_pf(self) -> pft.DataObject:
        return self.app.GetProjectFolder("study")

    def load_grid_graphs_from_pf(self) -> pft.DataObject:
        return self.app.GetProjectFolder("dia")

    def load_scenario_lib_from_pf(self) -> pft.DataObject:
        return self.app.GetProjectFolder("scen")

    def subloads_of(self, load: pft.LoadLV) -> list[pft.LoadLVP]:
        elements = self.elements_of(load, pattern="*.ElmLodlvp")
        return [typing.cast("pft.LoadLVP", element) for element in elements]

    def study_case(self, name: str = "*") -> pft.StudyCase | None:
        element = self.element_of(self.study_case_lib, name)
        return typing.cast("pft.StudyCase", element) if element is not None else None

    def study_cases(self, name: str = "*") -> list[pft.StudyCase]:
        elements = self.elements_of(self.study_case_lib, name)
        return [typing.cast("pft.StudyCase", element) for element in elements]

    def scenario(self, name: str = "*") -> pft.Scenario | None:
        element = self.element_of(self.scenario_lib, name)
        return typing.cast("pft.Scenario", element) if element is not None else None

    def scenarios(self, name: str = "*") -> list[pft.Scenario]:
        elements = self.elements_of(self.scenario_lib, name)
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

    def element_of(
        self,
        element: pft.DataObject,
        pattern: str = "*",
        recursive: bool = True,
    ) -> pft.DataObject | None:
        elements = self.elements_of(element, pattern=pattern, recursive=recursive)
        if len(elements) == 0:
            return None

        if len(elements) > 1:
            logger.warning("Found more then one element, returning only the first one.")

        return elements[0]

    def elements_of(
        self,
        element: pft.DataObject,
        pattern: str = "*",
        recursive: bool = True,
    ) -> list[pft.DataObject]:
        return element.GetContents(pattern, recursive)

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
            str -- the name of the generator obejct
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
