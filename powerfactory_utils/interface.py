from __future__ import annotations

import importlib.util
import itertools
import pathlib
import typing
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from powerfactory_utils import powerfactory_types as pft

if TYPE_CHECKING:
    from typing import Iterable
    from typing import Literal
    from typing import Optional
    from typing import TypeVar

    T = TypeVar("T")

POWERFACTORY_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
POWERFACTORY_VERSION = "2022 SP2"
PYTHON_VERSION = "3.9"
PATH_SEP = "/"


@dataclass
class UnitConversionSetting:
    cuserexp: str
    ufacA: float
    ufacB: float


@dataclass
class PowerfactoryInterface:
    project_name: str
    powerfactory_user_profile: Optional[str] = None
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH
    powerfactory_version: str = POWERFACTORY_VERSION
    python_version: str = PYTHON_VERSION

    def __post_init__(self) -> None:
        pf = self.start_powerfactory()
        self.app = self.connect_to_app(pf)
        self.project = self.connect_to_project(self.project_name)
        self.load_project_folders()
        self.set_unit_conversion()

    def load_project_folders(self) -> None:
        self.grid_model = self.load_grid_model()
        self.types_lib = self.load_asset_types_lib()
        self.op_lib = self.load_operational_data_lib()
        self.chars_lib = self.load_characteristics_lib()
        self.ext_data_dir = self.load_ext_data_dir()

        self.grid_data = self.load_grid_data()
        self.study_case_lib = self.load_study_case_lib()
        self.scenario_lib = self.load_scenario_lib()
        self.grid_graphs_dir = self.load_grid_graphs()

    def start_powerfactory(self) -> pft.PowerFactoryModule:
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
                pf = typing.cast(pft.PowerFactoryModule, pfm)
                return pf
        raise RuntimeError("Could not load Powerfactory module.")

    def close(self) -> bool:
        self.reset_unit_conversion()
        return True

    def connect_to_app(self, pf: pft.PowerFactoryModule) -> pft.Application:
        """Connect to PowerFactory Application.

         Arguments:
            pf {pft.PowerFactoryModule} -- the Python module contributed via the PowerFactory system installation

        Returns:
            pft.Application -- the application handle (root)
        """

        try:
            return pf.GetApplicationExt(self.powerfactory_user_profile)
        except pf.ExitError as e:
            logger.error(e)
            raise RuntimeError(e)

    def connect_to_project(self, project_name: str) -> pft.Project:
        """Connect to a PowerFactory project.

        Arguments:
            project_name {str} -- the name of the project to be connected/activated

        Returns:
            pft.Project -- the project handle
        """

        success = self.activate_project(project_name)
        if success:
            project = self.get_project()
            if project is not None:
                return project
        raise RuntimeError(f"Could not connect to Powerfactory project {project_name}.")

    def activate_project(self, name: str) -> bool:
        exit_code = self.app.ActivateProject(name + ".IntPrj")
        return not exit_code

    def activate_grid(self, grid: pft.Grid) -> bool:
        exit_code = grid.Activate()
        return not exit_code

    def deactivate_grid(self, grid: pft.Grid) -> bool:
        exit_code = grid.Deactivate()
        return not exit_code

    def deactivate_grids(self) -> bool:
        exit_codes = [self.deactivate_grid(g) for g in self.grids()]
        return all(exit_codes)

    def activate_scenario(self, scen: pft.Scenario) -> bool:
        exit_code = scen.Activate()
        return not exit_code

    def deactivate_scenario(self, scen: pft.Scenario) -> bool:
        exit_code = scen.Deactivate()
        return not exit_code

    def activate_study_case(self, stc: pft.StudyCase) -> bool:
        exit_code = stc.Activate()
        return not exit_code

    def deactivate_study_case(self, stc: pft.StudyCase) -> bool:
        exit_code = stc.Deactivate()
        return not exit_code

    def get_project(self) -> pft.Project:
        return self.app.GetActiveProject()

    def load_grid_model(self) -> pft.DataObject:
        return self.app.GetProjectFolder("netmod")

    def load_asset_types_lib(self) -> pft.DataObject:
        return self.app.GetProjectFolder("equip")

    def load_operational_data_lib(self) -> pft.DataObject:
        return self.app.GetProjectFolder("oplib")

    def load_characteristics_lib(self) -> pft.DataObject:
        return self.app.GetProjectFolder("chars")

    def load_ext_data_dir(self) -> pft.DataObject:
        project_settings = self.project.pPrjSettings
        if project_settings is not None:
            data_dir = project_settings.extDataDir
            data_dir = typing.cast(pft.DataObject, data_dir)
            return data_dir
        raise RuntimeError("Could not access data dir.")

    def load_grid_data(self) -> pft.DataObject:
        return self.app.GetProjectFolder("netdat")

    def load_study_case_lib(self) -> pft.DataObject:
        return self.app.GetProjectFolder("study")

    def load_grid_graphs(self) -> pft.DataObject:
        return self.app.GetProjectFolder("dia")

    def load_scenario_lib(self) -> pft.DataObject:
        return self.app.GetProjectFolder("scen")

    def set_unit_conversion(self) -> None:
        project_settings = self.project.pPrjSettings
        if project_settings is not None:
            self.app_cspqexp: Literal["m", " ", "k", "M", "G"] = project_settings.cspqexp
            project_settings.cspqexp = "M"
            self.app_user_unit_convs: dict[str, UnitConversionSetting] = {}
            unit_conversions = self.unit_conversion_settings()
            for uc in unit_conversions:
                ucs = UnitConversionSetting(cuserexp=uc.cuserexp, ufacA=uc.ufacA, ufacB=uc.ufacB)
                self.app_user_unit_convs[uc.loc_name + uc.digunit] = ucs
                uc.cuserexp = uc.cdigexp
        raise RuntimeError("Could not access project settings.")

    def reset_unit_conversion(self) -> None:
        project_settings = self.project.pPrjSettings
        if project_settings is not None:
            project_settings.cspqexp = self.app_cspqexp
            unit_conversions = self.unit_conversion_settings()
            for uc in unit_conversions:
                ucs = self.app_user_unit_convs[uc.loc_name + uc.digunit]
                uc.cuserexp = ucs.cuserexp
                uc.ufacA = ucs.ufacA
                uc.ufacB = ucs.ufacB
        raise RuntimeError("Could not access project settings.")

    def element_of(
        self, element: pft.DataObject, filter: str = "*", recursive: bool = True
    ) -> Optional[pft.DataObject]:
        elements = self.elements_of(element, filter=filter, recursive=recursive)
        if len(elements) == 0:
            return None
        if len(elements) > 1:
            logger.warning("Found more then one element, returning only the first one.")
        return elements[0]

    def elements_of(self, element: pft.DataObject, filter: str = "*", recursive: bool = True) -> list[pft.DataObject]:
        elements = element.GetContents(filter, recursive)
        return elements

    def subloads_of(self, load: pft.LoadLV) -> list[pft.LoadLVP]:
        es = self.elements_of(load, filter="*.ElmLodlvp")
        return [typing.cast(pft.LoadLVP, e) for e in es]

    def unit_conversion_settings(self) -> list[pft.UnitConversionSetting]:
        es = self.elements_of(self.project, filter="*.SetVariable")
        return [typing.cast(pft.UnitConversionSetting, e) for e in es]

    def study_case(self, name: str = "*") -> Optional[pft.StudyCase]:
        e = self.element_of(self.study_case_lib, name)
        return typing.cast(pft.StudyCase, e) if e is not None else None

    def study_cases(self, name: str = "*") -> list[pft.StudyCase]:
        es = self.elements_of(self.study_case_lib, name)
        return [typing.cast(pft.StudyCase, e) for e in es]

    def scenario(self, name: str = "*") -> Optional[pft.Scenario]:
        e = self.element_of(self.scenario_lib, name)
        return typing.cast(pft.Scenario, e) if e is not None else None

    def scenarios(self, name: str = "*") -> list[pft.Scenario]:
        es = self.elements_of(self.scenario_lib, name)
        return [typing.cast(pft.Scenario, e) for e in es]

    def grid_model_element(self, class_name: str, name: str = "*") -> Optional[pft.DataObject]:
        return self.element_of(self.grid_model, name + "." + class_name)

    def grid_model_elements(self, class_name: str, name: str = "*") -> list[pft.DataObject]:
        return self.elements_of(self.grid_model, name + "." + class_name)

    def line_type(self, name: str = "*") -> Optional[pft.LineType]:
        e = self.grid_model_element("TypLne", name)
        return typing.cast(pft.LineType, e) if e is not None else None

    def line_types(self, name: str = "*") -> list[pft.LineType]:
        es = self.grid_model_elements("TypLne", name)
        return [typing.cast(pft.LineType, e) for e in es]

    def load_type(self, name: str = "*") -> Optional[pft.DataObject]:
        return self.grid_model_element("TypLod", name)

    def load_types(self, name: str = "*") -> list[pft.DataObject]:
        return self.grid_model_elements("TypLod", name)

    def transformer_2w_type(self, name: str = "*") -> Optional[pft.Transformer2WType]:
        e = self.grid_model_element("TypTr2", name)
        return typing.cast(pft.Transformer2WType, e) if e is not None else None

    def transformer_2w_types(self, name: str = "*") -> list[pft.Transformer2WType]:
        es = self.grid_model_elements("TypTr2", name)
        return [typing.cast(pft.Transformer2WType, e) for e in es]

    def area(self, name: str = "*") -> Optional[pft.DataObject]:
        return self.grid_model_element("ElmArea", name)

    def areas(self, name: str = "*") -> list[pft.DataObject]:
        return self.grid_model_elements("ElmArea", name)

    def zone(self, name: str = "*") -> Optional[pft.DataObject]:
        return self.grid_model_element("ElmZone", name)

    def zones(self, name: str = "*") -> list[pft.DataObject]:
        return self.grid_model_elements("ElmZone", name)

    def grid(self, name: str = "*") -> Optional[pft.Grid]:
        e = self.grid_model_element("ElmNet", name)
        return typing.cast(pft.Grid, e) if e is not None else None

    def grids(self, name: str = "*") -> list[pft.Grid]:
        es = self.grid_model_elements("ElmNet", name)
        return [typing.cast(pft.Grid, e) for e in es]

    def grid_element(self, class_name: str, name: str = "*", grid: str = "*") -> Optional[pft.DataObject]:
        elements = self.grid_elements(class_name=class_name, name=name, grid=grid)
        if len(elements) == 0:
            return None
        if len(elements) > 1:
            logger.warning("Found more then one element, returning only the first one.")
        return elements[0]

    def grid_elements(self, class_name: str, name: str = "*", grid: str = "*") -> list[pft.DataObject]:
        rv = [self.elements_of(g, name + "." + class_name) for g in self.grids(grid)]
        return self.list_from_sequences(*rv)

    def grid_diagram(self, grid: str = "*") -> Optional[pft.GridDiagram]:
        e = self.grid_element("IntGrfnet", grid=grid)
        return typing.cast(pft.GridDiagram, e) if e is not None else None

    def grid_diagrams(self, grid: str = "*") -> list[pft.GridDiagram]:
        es = self.grid_elements("IntGrfnet", grid=grid)
        return [typing.cast(pft.GridDiagram, e) for e in es]

    def external_grid(self, name: str = "*", grid: str = "*") -> Optional[pft.ExternalGrid]:
        e = self.grid_element("ElmXNet", name, grid)
        return typing.cast(pft.ExternalGrid, e) if e is not None else None

    def external_grids(self, name: str = "*", grid: str = "*") -> list[pft.ExternalGrid]:
        es = self.grid_elements("ElmXNet", name, grid)
        return [typing.cast(pft.ExternalGrid, e) for e in es]

    def terminal(self, name: str = "*", grid: str = "*") -> Optional[pft.Terminal]:
        e = self.grid_element("ElmTerm", name, grid)
        return typing.cast(pft.Terminal, e) if e is not None else None

    def terminals(self, name: str = "*", grid: str = "*") -> list[pft.Terminal]:
        es = self.grid_elements("ElmTerm", name, grid)
        return [typing.cast(pft.Terminal, e) for e in es]

    def cubicle(self, name: str = "*", grid: str = "*") -> Optional[pft.StationCubicle]:
        e = self.grid_elements("StaCubic", name, grid)
        return typing.cast(pft.StationCubicle, e) if e is not None else None

    def cubicles(self, name: str = "*", grid: str = "*") -> list[pft.StationCubicle]:
        es = self.grid_elements("StaCubic", name, grid)
        return [typing.cast(pft.StationCubicle, e) for e in es]

    def coupler(self, name: str = "*", grid: str = "*") -> Optional[pft.Coupler]:
        e = self.grid_element("ElmCoup", name, grid)
        return typing.cast(pft.Coupler, e) if e is not None else None

    def couplers(self, name: str = "*", grid: str = "*") -> list[pft.Coupler]:
        es = self.grid_elements("ElmCoup", name, grid)
        return [typing.cast(pft.Coupler, e) for e in es]

    def switch(self, name: str = "*", grid: str = "*") -> Optional[pft.Switch]:
        e = self.grid_element("StaSwitch", name, grid)
        return typing.cast(pft.Switch, e) if e is not None else None

    def switches(self, name: str = "*", grid: str = "*") -> list[pft.Switch]:
        es = self.grid_elements("StaSwitch", name, grid)
        return [typing.cast(pft.Switch, e) for e in es]

    def fuse(self, name: str = "*", grid: str = "*") -> Optional[pft.Fuse]:
        e = self.grid_element("RelFuse", name, grid)
        return typing.cast(pft.Fuse, e) if e is not None else None

    def fuses(self, name: str = "*", grid: str = "*") -> list[pft.Fuse]:
        es = self.grid_elements("RelFuse", name, grid)
        return [typing.cast(pft.Fuse, e) for e in es]

    def line(self, name: str = "*", grid: str = "*") -> Optional[pft.Line]:
        e = self.grid_element("ElmLne", name, grid)
        return typing.cast(pft.Line, e) if e is not None else None

    def lines(self, name: str = "*", grid: str = "*") -> list[pft.Line]:
        es = self.grid_elements("ElmLne", name, grid)
        return [typing.cast(pft.Line, e) for e in es]

    def transformer_2w(self, name: str = "*", grid: str = "*") -> Optional[pft.Transformer2W]:
        e = self.grid_element("ElmTr2", name, grid)
        return typing.cast(pft.Transformer2W, e) if e is not None else None

    def transformers_2w(self, name: str = "*", grid: str = "*") -> list[pft.Transformer2W]:
        es = self.grid_elements("ElmTr2", name, grid)
        return [typing.cast(pft.Transformer2W, e) for e in es]

    def transformer_3w(self, name: str = "*", grid: str = "*") -> Optional[pft.Transformer3W]:
        e = self.grid_element("ElmTr3", name, grid)
        return typing.cast(pft.Transformer3W, e) if e is not None else None

    def transformers_3w(self, name: str = "*", grid: str = "*") -> list[pft.Transformer3W]:
        es = self.grid_elements("ElmTr3", name, grid)
        return [typing.cast(pft.Transformer3W, e) for e in es]

    def load(self, name: str = "*", grid: str = "*") -> Optional[pft.Load]:
        e = self.grid_element("ElmLod", name, grid)
        return typing.cast(pft.Load, e) if e is not None else None

    def loads(self, name: str = "*", grid: str = "*") -> list[pft.Load]:
        es = self.grid_elements("ElmLod", name, grid)
        return [typing.cast(pft.Load, e) for e in es]

    def load_lv(self, name: str = "*", grid: str = "*") -> Optional[pft.LoadLV]:
        e = self.grid_element("ElmLodLv", name, grid)
        return typing.cast(pft.LoadLV, e) if e is not None else None

    def loads_lv(self, name: str = "*", grid: str = "*") -> list[pft.LoadLV]:
        es = self.grid_elements("ElmLodLv", name, grid)
        return [typing.cast(pft.LoadLV, e) for e in es]

    def load_mv(self, name: str = "*", grid: str = "*") -> Optional[pft.LoadMV]:
        e = self.grid_element("ElmLodMv", name, grid)
        return typing.cast(pft.LoadMV, e) if e is not None else None

    def loads_mv(self, name: str = "*", grid: str = "*") -> list[pft.LoadMV]:
        es = self.grid_elements("ElmLodMv", name, grid)
        return [typing.cast(pft.LoadMV, e) for e in es]

    def generator(self, name: str = "*", grid: str = "*") -> Optional[pft.Generator]:
        e = self.grid_element("ElmGenstat", name, grid)
        return typing.cast(pft.Generator, e) if e is not None else None

    def generators(self, name: str = "*", grid: str = "*") -> list[pft.Generator]:
        es = self.grid_elements("ElmGenstat", name, grid)
        return [typing.cast(pft.Generator, e) for e in es]

    def pv_system(self, name: str = "*", grid: str = "*") -> Optional[pft.PVSystem]:
        e = self.grid_element("ElmPvsys", name, grid)
        return typing.cast(pft.PVSystem, e) if e is not None else None

    def pv_systems(self, name: str = "*", grid: str = "*") -> list[pft.PVSystem]:
        es = self.grid_elements("ElmPvsys", name, grid)
        return [typing.cast(pft.PVSystem, e) for e in es]

    @staticmethod
    def create_name(element: pft.DataObject, grid_name: str, element_name: Optional[str] = None) -> str:
        """Create a unique name of the object.

        Object type differentiation based on the input parameters. Considers optional parents of the object,
        e.g. in case of detailed template or detailed substation.

        Arguments:
            element {pft.DataObject} -- the object itself for which a unique name is going to be created
            grid_name {str} -- the name of the grid to which the object belongs (root)

        Keyword Arguments:
            element_name {Optional[str]} -- element name if needed to specify independently (default: {None})

        Returns:
            str -- the unique name of the object
        """

        if element_name is None:
            element_name = element.loc_name
        parent = element.fold_id
        if parent is not None:
            if parent.loc_name != grid_name:
                cp_substat: Optional[pft.DataObject] = getattr(element, "cpSubstat", None)
                if cp_substat is not None:
                    return cp_substat.loc_name + PATH_SEP + element_name
                return parent.loc_name + PATH_SEP + element_name
        return element_name

    @staticmethod
    def create_gen_name(generator: pft.GeneratorBase, generator_name: Optional[str] = None) -> str:
        """Creates a name for a generator object.

        Takes into account models in which the generator might be grouped in.

        Arguments:
            generator {pft.GeneratorBase} -- the generator object

        Keyword Arguments:
            generator_name {Optional[str]} -- name of generator or generator related object (e.g. external controller) if needed to specify independently (default: {None})

        Returns:
            str -- the name of the generator obejct
        """
        if generator_name is None:
            generator_name = generator.loc_name
        if generator.c_pmod is None:  # if generator is not part of higher model
            return generator_name
        else:
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
