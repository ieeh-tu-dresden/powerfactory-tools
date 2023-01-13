from __future__ import annotations

import dataclasses as dcs
import importlib.util
import itertools
import pathlib
import typing
from typing import TYPE_CHECKING

from loguru import logger

from powerfactory_utils.constants import BaseUnits

if TYPE_CHECKING:
    from typing import Any
    from typing import Iterable
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
    ufacA: float
    ufacB: float


@dcs.dataclass
class ProjectUnitSetting:
    ilenunit: Literal[0, 1, 2]
    clenexp: pft.MetricPrefix  # Lengths
    cspqexp: pft.MetricPrefix  # Loads etc.
    cspqexpgen: pft.MetricPrefix  # Generators etc.
    currency: pft.Currency


@dcs.dataclass
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
        if self.project is None:
            raise RuntimeError("Could not access project.")
        self.load_project_folders()
        self.set_default_unit_conversion()

    def load_project_folders(self) -> None:
        self.grid_model = self.app.GetProjectFolder("netmod")
        self.types_dir = self.app.GetProjectFolder("equip")
        self.op_dir = self.app.GetProjectFolder("oplib")
        self.chars_dir = self.app.GetProjectFolder("chars")

        project_settings_dir = self.load_project_settings_dir()
        if project_settings_dir is None:
            raise RuntimeError("Could not access project settings dir.")
        self.project_settings_dir = typing.cast("pft.ProjectSettings", project_settings_dir)

        self.ext_data_dir = self.project_settings_dir.extDataDir

        self.grid_data = self.app.GetProjectFolder("netdat")
        self.study_case_dir = self.app.GetProjectFolder("study")
        self.scenario_dir = self.app.GetProjectFolder("scen")
        self.grid_graphs_dir = self.app.GetProjectFolder("dia")

        settings_dir = self.element_of(self.project, filter="*.SetFold", recursive=False)
        if settings_dir is None:
            raise RuntimeError("Could not access settings dir.")
        self.settings_dir = typing.cast("pft.DataDir", settings_dir)

        unit_settings_dir = self.element_of(self.settings_dir, filter="*.IntUnit", recursive=False)
        if unit_settings_dir is None:
            raise RuntimeError("Could not access unit settings dir.")
        self.unit_settings_dir = typing.cast("pft.DataDir", unit_settings_dir)

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
                pf = typing.cast("pft.PowerFactoryModule", pfm)
                return pf
        raise RuntimeError("Could not load Powerfactory module.")

    def close(self) -> bool:
        self.reset_unit_conversion_settings()
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
        if success is False:
            raise RuntimeError(f"Could not activate Powerfactory project {project_name}.")

        project = self.app.GetActiveProject()
        if project is None:
            raise RuntimeError("Could not access Powerfactory project.")

        return project

    def activate_project(self, name: str) -> bool:
        exit_code = self.app.ActivateProject(name + ".IntPrj")
        return not exit_code

    def deactivate_project(self) -> bool:
        exit_code = self.project.Deactivate()
        return not exit_code

    def reset_project(self) -> bool:
        success = self.deactivate_project()
        return False if not success else self.activate_project(self.project_name)

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

    def load_project_settings_dir(self) -> pft.DataObject:
        project_settings = self.project.pPrjSettings
        if project_settings is None:
            raise RuntimeError("Could not access project settings dir.")
        return project_settings

    def save_unit_conversion_settings(self) -> None:
        project_settings = self.project.pPrjSettings
        if project_settings is not None:
            self.project_unit_setting = ProjectUnitSetting(
                ilenunit=project_settings.ilenunit,
                clenexp=project_settings.clenexp,
                cspqexp=project_settings.cspqexp,
                cspqexpgen=project_settings.cspqexpgen,
                currency=project_settings.currency,
            )
        else:
            raise RuntimeError("Could not access project settings.")
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

    def set_default_unit_conversion(self) -> None:
        self.save_unit_conversion_settings()

        project_settings = self.project.pPrjSettings
        if project_settings is not None:
            project_settings.ilenunit = 0
            project_settings.clenexp = BaseUnits.LENGTH
            project_settings.cspqexp = BaseUnits.POWER
            project_settings.cspqexpgen = BaseUnits.POWER
            project_settings.currency = BaseUnits.CURRENCY
        else:
            raise RuntimeError("Could not access project settings.")
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

    def reset_unit_conversion_settings(self) -> None:
        project_settings = self.project.pPrjSettings
        if project_settings is not None:
            project_settings.ilenunit = self.project_unit_setting.ilenunit
            project_settings.clenexp = self.project_unit_setting.clenexp
            project_settings.cspqexp = self.project_unit_setting.cspqexp
            project_settings.cspqexpgen = self.project_unit_setting.cspqexpgen
            project_settings.currency = self.project_unit_setting.currency
        else:
            raise RuntimeError("Could not access project settings.")
        self.delete_unit_conversion_settings()
        for name, uc in self.unit_conv_settings.items():
            self.create_unit_conversion_setting(name, uc)

        self.reset_project()

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
        return [typing.cast("pft.LoadLVP", e) for e in es]

    def unit_conversion_settings(self) -> list[pft.UnitConversionSetting]:
        es = self.elements_of(self.unit_settings_dir, filter="*.SetVariable")
        return [typing.cast("pft.UnitConversionSetting", e) for e in es]

    def study_case(self, name: str = "*") -> Optional[pft.StudyCase]:
        e = self.element_of(self.study_case_dir, name)
        return typing.cast("pft.StudyCase", e) if e is not None else None

    def study_cases(self, name: str = "*") -> list[pft.StudyCase]:
        es = self.elements_of(self.study_case_dir, name)
        return [typing.cast("pft.StudyCase", e) for e in es]

    def scenario(self, name: str = "*") -> Optional[pft.Scenario]:
        e = self.element_of(self.scenario_dir, name)
        return typing.cast("pft.Scenario", e) if e is not None else None

    def scenarios(self, name: str = "*") -> list[pft.Scenario]:
        es = self.elements_of(self.scenario_dir, name)
        return [typing.cast("pft.Scenario", e) for e in es]

    def grid_model_element(self, class_name: str, name: str = "*") -> Optional[pft.DataObject]:
        return self.element_of(self.grid_model, name + "." + class_name)

    def grid_model_elements(self, class_name: str, name: str = "*") -> list[pft.DataObject]:
        return self.elements_of(self.grid_model, name + "." + class_name)

    def line_type(self, name: str = "*") -> Optional[pft.LineType]:
        e = self.grid_model_element("TypLne", name)
        return typing.cast("pft.LineType", e) if e is not None else None

    def line_types(self, name: str = "*") -> list[pft.LineType]:
        es = self.grid_model_elements("TypLne", name)
        return [typing.cast("pft.LineType", e) for e in es]

    def load_type(self, name: str = "*") -> Optional[pft.DataObject]:
        return self.grid_model_element("TypLod", name)

    def load_types(self, name: str = "*") -> list[pft.DataObject]:
        return self.grid_model_elements("TypLod", name)

    def transformer_2w_type(self, name: str = "*") -> Optional[pft.Transformer2WType]:
        e = self.grid_model_element("TypTr2", name)
        return typing.cast("pft.Transformer2WType", e) if e is not None else None

    def transformer_2w_types(self, name: str = "*") -> list[pft.Transformer2WType]:
        es = self.grid_model_elements("TypTr2", name)
        return [typing.cast("pft.Transformer2WType", e) for e in es]

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
        return typing.cast("pft.Grid", e) if e is not None else None

    def grids(self, name: str = "*") -> list[pft.Grid]:
        es = self.grid_model_elements("ElmNet", name)
        return [typing.cast("pft.Grid", e) for e in es]

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
        return typing.cast("pft.GridDiagram", e) if e is not None else None

    def grid_diagrams(self, grid: str = "*") -> list[pft.GridDiagram]:
        es = self.grid_elements("IntGrfnet", grid=grid)
        return [typing.cast("pft.GridDiagram", e) for e in es]

    def external_grid(self, name: str = "*", grid: str = "*") -> Optional[pft.ExternalGrid]:
        e = self.grid_element("ElmXNet", name, grid)
        return typing.cast("pft.ExternalGrid", e) if e is not None else None

    def external_grids(self, name: str = "*", grid: str = "*") -> list[pft.ExternalGrid]:
        es = self.grid_elements("ElmXNet", name, grid)
        return [typing.cast("pft.ExternalGrid", e) for e in es]

    def terminal(self, name: str = "*", grid: str = "*") -> Optional[pft.Terminal]:
        e = self.grid_element("ElmTerm", name, grid)
        return typing.cast("pft.Terminal", e) if e is not None else None

    def terminals(self, name: str = "*", grid: str = "*") -> list[pft.Terminal]:
        es = self.grid_elements("ElmTerm", name, grid)
        return [typing.cast("pft.Terminal", e) for e in es]

    def cubicle(self, name: str = "*", grid: str = "*") -> Optional[pft.StationCubicle]:
        e = self.grid_elements("StaCubic", name, grid)
        return typing.cast("pft.StationCubicle", e) if e is not None else None

    def cubicles(self, name: str = "*", grid: str = "*") -> list[pft.StationCubicle]:
        es = self.grid_elements("StaCubic", name, grid)
        return [typing.cast("pft.StationCubicle", e) for e in es]

    def coupler(self, name: str = "*", grid: str = "*") -> Optional[pft.Coupler]:
        e = self.grid_element("ElmCoup", name, grid)
        return typing.cast("pft.Coupler", e) if e is not None else None

    def couplers(self, name: str = "*", grid: str = "*") -> list[pft.Coupler]:
        es = self.grid_elements("ElmCoup", name, grid)
        return [typing.cast("pft.Coupler", e) for e in es]

    def switch(self, name: str = "*", grid: str = "*") -> Optional[pft.Switch]:
        e = self.grid_element("StaSwitch", name, grid)
        return typing.cast("pft.Switch", e) if e is not None else None

    def switches(self, name: str = "*", grid: str = "*") -> list[pft.Switch]:
        es = self.grid_elements("StaSwitch", name, grid)
        return [typing.cast("pft.Switch", e) for e in es]

    def fuse(self, name: str = "*", grid: str = "*") -> Optional[pft.Fuse]:
        e = self.grid_element("RelFuse", name, grid)
        return typing.cast("pft.Fuse", e) if e is not None else None

    def fuses(self, name: str = "*", grid: str = "*") -> list[pft.Fuse]:
        es = self.grid_elements("RelFuse", name, grid)
        return [typing.cast("pft.Fuse", e) for e in es]

    def line(self, name: str = "*", grid: str = "*") -> Optional[pft.Line]:
        e = self.grid_element("ElmLne", name, grid)
        return typing.cast("pft.Line", e) if e is not None else None

    def lines(self, name: str = "*", grid: str = "*") -> list[pft.Line]:
        es = self.grid_elements("ElmLne", name, grid)
        return [typing.cast("pft.Line", e) for e in es]

    def transformer_2w(self, name: str = "*", grid: str = "*") -> Optional[pft.Transformer2W]:
        e = self.grid_element("ElmTr2", name, grid)
        return typing.cast("pft.Transformer2W", e) if e is not None else None

    def transformers_2w(self, name: str = "*", grid: str = "*") -> list[pft.Transformer2W]:
        es = self.grid_elements("ElmTr2", name, grid)
        return [typing.cast("pft.Transformer2W", e) for e in es]

    def transformer_3w(self, name: str = "*", grid: str = "*") -> Optional[pft.Transformer3W]:
        e = self.grid_element("ElmTr3", name, grid)
        return typing.cast("pft.Transformer3W", e) if e is not None else None

    def transformers_3w(self, name: str = "*", grid: str = "*") -> list[pft.Transformer3W]:
        es = self.grid_elements("ElmTr3", name, grid)
        return [typing.cast("pft.Transformer3W", e) for e in es]

    def load(self, name: str = "*", grid: str = "*") -> Optional[pft.Load]:
        e = self.grid_element("ElmLod", name, grid)
        return typing.cast("pft.Load", e) if e is not None else None

    def loads(self, name: str = "*", grid: str = "*") -> list[pft.Load]:
        es = self.grid_elements("ElmLod", name, grid)
        return [typing.cast("pft.Load", e) for e in es]

    def load_lv(self, name: str = "*", grid: str = "*") -> Optional[pft.LoadLV]:
        e = self.grid_element("ElmLodLv", name, grid)
        return typing.cast("pft.LoadLV", e) if e is not None else None

    def loads_lv(self, name: str = "*", grid: str = "*") -> list[pft.LoadLV]:
        es = self.grid_elements("ElmLodLv", name, grid)
        return [typing.cast("pft.LoadLV", e) for e in es]

    def load_mv(self, name: str = "*", grid: str = "*") -> Optional[pft.LoadMV]:
        e = self.grid_element("ElmLodMv", name, grid)
        return typing.cast("pft.LoadMV", e) if e is not None else None

    def loads_mv(self, name: str = "*", grid: str = "*") -> list[pft.LoadMV]:
        es = self.grid_elements("ElmLodMv", name, grid)
        return [typing.cast("pft.LoadMV", e) for e in es]

    def generator(self, name: str = "*", grid: str = "*") -> Optional[pft.Generator]:
        e = self.grid_element("ElmGenstat", name, grid)
        return typing.cast("pft.Generator", e) if e is not None else None

    def generators(self, name: str = "*", grid: str = "*") -> list[pft.Generator]:
        es = self.grid_elements("ElmGenstat", name, grid)
        return [typing.cast("pft.Generator", e) for e in es]

    def pv_system(self, name: str = "*", grid: str = "*") -> Optional[pft.PVSystem]:
        e = self.grid_element("ElmPvsys", name, grid)
        return typing.cast("pft.PVSystem", e) if e is not None else None

    def pv_systems(self, name: str = "*", grid: str = "*") -> list[pft.PVSystem]:
        es = self.grid_elements("ElmPvsys", name, grid)
        return [typing.cast("pft.PVSystem", e) for e in es]

    def create_unit_conversion_setting(
        self, name: str, uc: UnitConversionSetting
    ) -> Optional[pft.UnitConversionSetting]:
        data = dcs.asdict(uc)
        e = self.create_object(name=name, class_name="SetVariable", location=self.unit_settings_dir, data=data)
        return typing.cast("pft.UnitConversionSetting", e) if e is not None else None

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
    ) -> Optional[pft.DataObject]:
        element = self.element_of(location, filter=f"{name}.{class_name}")
        if element is not None and force is False:
            if update is False:
                logger.warning(
                    f"{name}.{class_name} already exists. Use force=True to create it anyway or update=True to update it."
                )
        else:
            element = location.CreateObject(class_name, name)
            update = True

        if element is not None and update is True:
            element = self.update_object(element, data)

        return element

    @staticmethod
    def update_object(element: pft.DataObject, data: dict[str, Any]) -> pft.DataObject:
        for k, v in data.items():
            if getattr(element, k, None) is not None:
                setattr(element, k, v)
        return element

    @staticmethod
    def delete_object(element: pft.DataObject) -> bool:
        return element.Delete() == 0

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
            str -- the name of the generator object
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
