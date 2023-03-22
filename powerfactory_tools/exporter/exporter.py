# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import dataclasses
import datetime
import itertools
import math
import multiprocessing
import pathlib
import textwrap
from typing import TYPE_CHECKING

from loguru import logger

from powerfactory_tools.constants import DecimalDigits
from powerfactory_tools.constants import Exponents
from powerfactory_tools.exporter.load_power import LoadPower
from powerfactory_tools.interface import PowerFactoryInterface
from powerfactory_tools.powerfactory_types import CosphiChar
from powerfactory_tools.powerfactory_types import CtrlMode
from powerfactory_tools.powerfactory_types import CtrlVoltageRef
from powerfactory_tools.powerfactory_types import GeneratorPhaseConnectionType
from powerfactory_tools.powerfactory_types import GeneratorSystemType
from powerfactory_tools.powerfactory_types import IOpt
from powerfactory_tools.powerfactory_types import LoadPhaseConnectionType
from powerfactory_tools.powerfactory_types import LocalQCtrlMode
from powerfactory_tools.powerfactory_types import Phase as PFPhase
from powerfactory_tools.powerfactory_types import QChar
from powerfactory_tools.powerfactory_types import TerminalVoltageSystemType
from powerfactory_tools.powerfactory_types import Vector
from powerfactory_tools.powerfactory_types import VectorGroup
from powerfactory_tools.powerfactory_types import VoltageSystemType as ElementVoltageSystemType
from powerfactory_tools.schema.base import CosphiDir
from powerfactory_tools.schema.base import Meta
from powerfactory_tools.schema.base import VoltageSystemType
from powerfactory_tools.schema.steadystate_case.case import Case as SteadystateCase
from powerfactory_tools.schema.steadystate_case.controller import ControlCosphiConst
from powerfactory_tools.schema.steadystate_case.controller import ControlCosphiP
from powerfactory_tools.schema.steadystate_case.controller import ControlCosphiU
from powerfactory_tools.schema.steadystate_case.controller import ControlledVoltageRef
from powerfactory_tools.schema.steadystate_case.controller import Controller
from powerfactory_tools.schema.steadystate_case.controller import ControlQConst
from powerfactory_tools.schema.steadystate_case.controller import ControlQP
from powerfactory_tools.schema.steadystate_case.controller import ControlQU
from powerfactory_tools.schema.steadystate_case.controller import ControlTanphiConst
from powerfactory_tools.schema.steadystate_case.controller import ControlUConst
from powerfactory_tools.schema.steadystate_case.external_grid import ExternalGrid as ExternalGridSSC
from powerfactory_tools.schema.steadystate_case.load import Load as LoadSSC
from powerfactory_tools.schema.steadystate_case.transformer import Transformer as TransformerSSC
from powerfactory_tools.schema.topology.active_power import ActivePower
from powerfactory_tools.schema.topology.branch import Branch
from powerfactory_tools.schema.topology.branch import BranchType
from powerfactory_tools.schema.topology.external_grid import ExternalGrid
from powerfactory_tools.schema.topology.external_grid import GridType
from powerfactory_tools.schema.topology.load import Load
from powerfactory_tools.schema.topology.load import LoadType
from powerfactory_tools.schema.topology.load import Phase
from powerfactory_tools.schema.topology.load import PhaseConnectionType
from powerfactory_tools.schema.topology.load import SystemType
from powerfactory_tools.schema.topology.load_model import LoadModel
from powerfactory_tools.schema.topology.node import Node
from powerfactory_tools.schema.topology.reactive_power import ReactivePower
from powerfactory_tools.schema.topology.topology import Topology
from powerfactory_tools.schema.topology.transformer import TapSide
from powerfactory_tools.schema.topology.transformer import Transformer
from powerfactory_tools.schema.topology.transformer import TransformerPhaseTechnologyType
from powerfactory_tools.schema.topology.transformer import VectorGroup as TVectorGroup
from powerfactory_tools.schema.topology.windings import VectorGroup as WVectorGroup
from powerfactory_tools.schema.topology.windings import Winding
from powerfactory_tools.schema.topology_case.case import Case as TopologyCase
from powerfactory_tools.schema.topology_case.element_state import ElementState

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import TracebackType
    from typing import Literal

    from powerfactory_tools.powerfactory_types import PowerFactoryTypes as PFTypes
    from powerfactory_tools.schema.steadystate_case.controller import ControlType

    ElementBase = PFTypes.GeneratorBase | PFTypes.LoadBase | PFTypes.ExternalGrid


POWERFACTORY_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
POWERFACTORY_VERSION = "2022 SP2"
PYTHON_VERSION = "3.10"

FULL_DYNAMIC = 100
M_TAB2015_MIN_THRESHOLD = 0.01


@dataclasses.dataclass
class LoadLV:
    fixed: LoadPower
    night: LoadPower
    flexible: LoadPower


@dataclasses.dataclass
class LoadMV:
    consumer: LoadPower
    producer: LoadPower


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


class PowerFactoryExporterProcess(multiprocessing.Process):
    def __init__(
        self,
        *,
        export_path: pathlib.Path,
        project_name: str,
        grid_name: str,
        powerfactory_user_profile: str = "",
        powerfactory_path: pathlib.Path = POWERFACTORY_PATH,
        powerfactory_version: str = POWERFACTORY_VERSION,
        python_version: str = PYTHON_VERSION,
        topology_name: str | None = None,
        topology_case_name: str | None = None,
        steadystate_case_name: str | None = None,
    ) -> None:
        super().__init__()
        self.export_path = export_path
        self.project_name = project_name
        self.grid_name = grid_name
        self.powerfactory_user_profile = powerfactory_user_profile
        self.powerfactory_path = powerfactory_path
        self.powerfactory_version = powerfactory_version
        self.python_version = python_version
        if topology_name is not None:
            self.topology_name = topology_name
        else:
            self.topology_name = grid_name

        if topology_case_name is not None:
            self.topology_case_name = topology_case_name
        else:
            self.topology_case_name = grid_name

        if steadystate_case_name is not None:
            self.steadystate_case_name = steadystate_case_name
        else:
            self.steadystate_case_name = grid_name

    def run(self) -> None:
        pfe = PowerFactoryExporter(
            project_name=self.project_name,
            grid_name=self.grid_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_path=self.powerfactory_path,
            powerfactory_version=self.powerfactory_version,
            python_version=self.python_version,
        )
        pfe.export(self.export_path, self.topology_name, self.topology_case_name, self.steadystate_case_name)


@dataclasses.dataclass
class PowerFactoryExporter:
    project_name: str
    grid_name: str
    powerfactory_user_profile: str = ""
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH
    powerfactory_version: str = POWERFACTORY_VERSION
    python_version: str = PYTHON_VERSION

    def __post_init__(self) -> None:
        self.pfi = PowerFactoryInterface(
            project_name=self.project_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_path=self.powerfactory_path,
            powerfactory_version=self.powerfactory_version,
            python_version=self.python_version,
        )

    def __enter__(self) -> PowerFactoryExporter:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self.pfi.close()

    def export(
        self,
        export_path: pathlib.Path,
        topology_name: str | None = None,
        topology_case_name: str | None = None,
        steadystate_case_name: str | None = None,
    ) -> None:
        """Export grid topology, topology_case and steadystate_case to json files.

        Based on the class arguments of PowerFactoryExporter a grid, given in DIgSILENT PowerFactory, is exported to
        three json files with given schema. The whole grid data is separated into topology (raw assets), topology_case
        (binary switching info and out of service info) and steadystate_case (operation points).

        Arguments:
            export_path {pathlib.Path} -- the directory where the exported json files are saved
            topology_name {str} -- the chosen file name for 'topology' data
            topology_case_name {str} -- the chosen file name for related 'topology_case' data
            steadystate_case_name {str} -- the chosen file name for related 'steadystate_case' data
        """

        logger.debug("Exporting {project_name}...", project_name=self.project_name)
        data = self.compile_powerfactory_data()
        meta = self.create_meta_data(data=data)

        topology = self.create_topology(meta=meta, data=data)
        topology_case = self.create_topology_case(meta=meta, data=data)
        steadystate_case = self.create_steadystate_case(meta=meta, data=data)

        if steadystate_case.is_valid_topology(topology) is False:
            msg = "Steadystate case does not match specified topology."
            raise ValueError(msg)

        self.export_topology(topology=topology, topology_name=topology_name, export_path=export_path)
        self.export_topology_case(
            topology_case=topology_case,
            topology_case_name=topology_case_name,
            export_path=export_path,
        )
        self.export_steadystate_case(
            steadystate_case=steadystate_case,
            steadystate_case_name=steadystate_case_name,
            export_path=export_path,
        )

    def export_scenario(
        self,
        *,
        export_path: pathlib.Path,
        scenario_name: str | None,
        topology_case_name: str | None = None,
        steadystate_case_name: str | None = None,
        verify_steadystate_case: bool = False,
    ) -> None:
        """Export grid topology_case and steadystate_case for a given scenario to json files.

        Based on the class arguments of PowerFactoryExporter a grid, given in DIgSILENT PowerFactory, is exported to
        two json files with given schema. Only grid data related to topology_case (binary switching info and out of
        service info) and steadystate_case (operation points) is exported.

        Arguments:
            export_path {pathlib.Path} -- the directory where the exported json files are saved
            scenario_name {str | None} -- the scenario name
            topology_case_name {str} -- the chosen file name for related 'topology_case' data
            steadystate_case_name {str} -- the chosen file name for related 'steadystate_case' data
            verify_steadystate_case {bool} -- if True, associated topology is created to be checked against
        """

        logger.debug("Exporting scenario {scenario_name}...", scenario_name=scenario_name)
        if scenario_name is not None:
            self.switch_scenario(scenario_name)

        data = self.compile_powerfactory_data()
        meta = self.create_meta_data(data=data)

        topology_case = self.create_topology_case(meta=meta, data=data)
        steadystate_case = self.create_steadystate_case(meta=meta, data=data)
        if verify_steadystate_case is True:
            topology = self.create_topology(meta=meta, data=data)
            if steadystate_case.is_valid_topology(topology) is False:
                msg = "Steadystate case does not match specified topology."
                raise ValueError(msg)

        self.export_topology_case(
            topology_case=topology_case,
            topology_case_name=topology_case_name,
            export_path=export_path,
        )
        self.export_steadystate_case(
            steadystate_case=steadystate_case,
            steadystate_case_name=steadystate_case_name,
            export_path=export_path,
        )

    def export_topology(self, topology: Topology, topology_name: str | None, export_path: pathlib.Path) -> None:
        logger.debug("Exporting topology {topology_name}...", topology_name=topology_name)
        self.export_data(
            data=topology,
            data_name=topology_name,
            data_type="topology",
            export_path=export_path,
        )

    def export_topology_case(
        self,
        topology_case: TopologyCase,
        topology_case_name: str | None,
        export_path: pathlib.Path,
    ) -> None:
        logger.debug("Exporting topology case {topology_case_name}...", topology_case_name=topology_case_name)
        self.export_data(
            data=topology_case,
            data_name=topology_case_name,
            data_type="topology_case",
            export_path=export_path,
        )

    def export_steadystate_case(
        self,
        steadystate_case: SteadystateCase,
        steadystate_case_name: str | None,
        export_path: pathlib.Path,
    ) -> None:
        logger.debug(
            "Exporting steadystate case {steadystate_case_name}...",
            steadystate_case_name=steadystate_case_name,
        )
        self.export_data(
            data=steadystate_case,
            data_name=steadystate_case_name,
            data_type="steadystate_case",
            export_path=export_path,
        )

    def export_data(
        self,
        data: Topology | TopologyCase | SteadystateCase,
        data_name: str | None,
        data_type: Literal["topology", "topology_case", "steadystate_case"],
        export_path: pathlib.Path,
    ) -> None:
        """Export data to json file.

        Arguments:
            data {Topology | TopologyCase | SteadystateCase} -- data to export
            data_name {str | None} -- the chosen file name for data
            data_type {Literal['topology', 'topology_case', 'steadystate_case']} -- the data type
            export_path {pathlib.Path} -- the directory where the exported json file is saved
        """
        timestamp = datetime.datetime.now().astimezone()  # noqa: DTZ005
        timestamp_string = timestamp.isoformat(sep="T", timespec="seconds").replace(":", "")
        if data_name is None:
            filename = f"{self.grid_name}_{timestamp_string}_{data_type}.json"
        else:
            filename = f"{data_name}_{data_type}.json"

        file_path = export_path / filename
        try:
            file_path.resolve()
        except OSError as e:
            msg = f"File path {file_path} is not a valid path."
            raise FileNotFoundError(msg) from e

        data.to_json(file_path)

    def switch_study_case(self, sc: str) -> None:
        study_case = self.pfi.study_case(name=sc)
        if study_case is not None:
            self.pfi.activate_study_case(study_case)
        else:
            msg = f"Study case {sc} does not exist."
            raise RuntimeError(msg)

    def switch_scenario(self, scen: str) -> None:
        scenario = self.pfi.scenario(name=scen)
        if scenario is not None:
            self.pfi.activate_scenario(scenario)
        else:
            msg = f"Scenario {scen} does not exist."
            raise RuntimeError(msg)

    def compile_powerfactory_data(self) -> PowerFactoryData:
        logger.debug("Compiling data from PowerFactory...")
        if self.grid_name == "*":
            name = self.project_name
        else:
            grids = self.pfi.grids()
            try:
                grid = [e for e in grids if e.loc_name == self.grid_name][0]
                name = grid.loc_name
            except IndexError as e:
                msg = f"Grid {self.grid_name} does not exist."
                raise RuntimeError(msg) from e

        project = self.pfi.project.loc_name
        date = datetime.datetime.now().astimezone().date()  # noqa: DTZ005

        return PowerFactoryData(
            name=name,
            date=date,
            project=project,
            external_grids=self.pfi.external_grids(grid=self.grid_name),
            terminals=self.pfi.terminals(grid=self.grid_name),
            lines=self.pfi.lines(grid=self.grid_name),
            transformers_2w=self.pfi.transformers_2w(grid=self.grid_name),
            transformers_3w=self.pfi.transformers_3w(grid=self.grid_name),
            loads=self.pfi.loads(grid=self.grid_name),
            loads_lv=self.pfi.loads_lv(grid=self.grid_name),
            loads_mv=self.pfi.loads_mv(grid=self.grid_name),
            generators=self.pfi.generators(grid=self.grid_name),
            pv_systems=self.pfi.pv_systems(grid=self.grid_name),
            couplers=self.pfi.couplers(grid=self.grid_name),
            switches=self.pfi.switches(grid=self.grid_name),
            fuses=self.pfi.fuses(grid=self.grid_name),
        )

    @staticmethod
    def create_meta_data(data: PowerFactoryData) -> Meta:
        logger.debug("Creating meta data...")
        grid_name = data.name.replace(" ", "-")
        project = data.project.replace(" ", "-")
        date = data.date

        return Meta(name=grid_name, date=date, project=project)

    def create_topology(self, meta: Meta, data: PowerFactoryData) -> Topology:
        logger.debug("Creating topology...")
        external_grids = self.create_external_grids(
            ext_grids=data.external_grids,
            grid_name=data.name,
        )
        nodes = self.create_nodes(terminals=data.terminals, grid_name=data.name)
        branches = self.create_branches(lines=data.lines, couplers=data.couplers, grid_name=data.name)
        loads = self.create_loads(
            consumers=data.loads,
            consumers_lv=data.loads_lv,
            consumers_mv=data.loads_mv,
            generators=data.generators,
            pv_systems=data.pv_systems,
            grid_name=data.name,
        )
        transformers = self.create_transformers(
            pf_transformers_2w=data.transformers_2w,
            grid_name=data.name,
        )

        return Topology(
            meta=meta,
            nodes=nodes,
            branches=branches,
            loads=loads,
            transformers=transformers,
            external_grids=external_grids,
        )

    def create_external_grids(
        self,
        ext_grids: Sequence[PFTypes.ExternalGrid],
        grid_name: str,
    ) -> Sequence[ExternalGrid]:
        logger.info("Creating external grids...")
        external_grids = [self.create_external_grid(ext_grid, grid_name) for ext_grid in ext_grids]
        return self.pfi.filter_none(external_grids)

    def create_external_grid(
        self,
        ext_grid: PFTypes.ExternalGrid,
        grid_name: str,
    ) -> ExternalGrid | None:
        name = self.pfi.create_name(ext_grid, grid_name)
        logger.debug("Creating external_grid {ext_grid_name}...", ext_grid_name=name)
        export, description = self.get_description(ext_grid)
        if not export:
            logger.warning("External grid {ext_grid_name} not set for export. Skipping.", ext_grid_name=name)
            return None

        if ext_grid.bus1 is None:
            logger.warning("External grid {ext_grid_name} not connected to any bus. Skipping.", ext_grid_name=name)
            return None

        node_name = self.pfi.create_name(ext_grid.bus1.cterm, grid_name)

        return ExternalGrid(
            name=name,
            description=description,
            node=node_name,
            type=GridType(ext_grid.bustp),
            short_circuit_power_max=ext_grid.snss,
            short_circuit_power_min=ext_grid.snssmin,
        )

    def create_nodes(self, terminals: Sequence[PFTypes.Terminal], grid_name: str) -> Sequence[Node]:
        logger.info("Creating nodes...")
        nodes = [self.create_node(terminal, grid_name) for terminal in terminals]
        return self.pfi.filter_none(nodes)

    def create_node(self, terminal: PFTypes.Terminal, grid_name: str) -> Node | None:
        export, description = self.get_description(terminal)
        name = self.pfi.create_name(terminal, grid_name)
        logger.debug("Creating node {node_name}...", node_name=name)
        if not export:
            logger.warning("Node {node_name} not set for export. Skipping.", node_name=name)
            return None

        u_n = round(terminal.uknom * Exponents.VOLTAGE, DecimalDigits.VOLTAGE)  # voltage in V

        if self.pfi.is_within_substation(terminal):
            description = "substation internal" if description else "substation internal; " + description

        return Node(name=name, u_n=u_n, description=description)

    def create_branches(
        self,
        lines: Sequence[PFTypes.Line],
        couplers: Sequence[PFTypes.Coupler],
        grid_name: str,
    ) -> Sequence[Branch]:
        logger.info("Creating branches...")
        blines = [self.create_line(line, grid_name) for line in lines]
        bcouplers = [self.create_coupler(coupler, grid_name) for coupler in couplers]

        return self.pfi.list_from_sequences(self.pfi.filter_none(blines), self.pfi.filter_none(bcouplers))

    def create_line(self, line: PFTypes.Line, grid_name: str) -> Branch | None:
        name = self.pfi.create_name(line, grid_name)
        logger.debug("Creating line {line_name}...", line_name=name)
        export, description = self.get_description(line)
        if not export:
            logger.warning("Line {line_name} not set for export. Skipping.", line_name=name)
            return None

        if line.bus1 is None or line.bus2 is None:
            logger.warning("Line {line_name} not connected to buses on both sides. Skipping.", line_name=name)
            return None

        t1 = line.bus1.cterm
        t2 = line.bus2.cterm

        if t1.systype != t2.systype:
            logger.warning("Line {line_name} connected to DC and AC bus. Skipping.", line_name=name)
            return None

        t1_name = self.pfi.create_name(t1, grid_name)
        t2_name = self.pfi.create_name(t2, grid_name)

        u_nom_1 = t1.uknom
        u_nom_2 = t2.uknom

        l_type = line.typ_id
        if l_type is None:
            logger.warning(
                "Type not set for line {line_name}. Skipping.",
                line_name=name,
            )
            return None

        u_nom = self.determine_line_voltage(u_nom_1=u_nom_1, u_nom_2=u_nom_2, l_type=l_type)

        i = l_type.InomAir if line.inAir else l_type.sline
        i_r = line.nlnum * line.fline * i * Exponents.CURRENT  # rated current (A)

        r1 = l_type.rline * line.dline / line.nlnum * Exponents.RESISTANCE
        x1 = l_type.xline * line.dline / line.nlnum * Exponents.REACTANCE
        r0 = l_type.rline0 * line.dline / line.nlnum * Exponents.RESISTANCE
        x0 = l_type.xline0 * line.dline / line.nlnum * Exponents.REACTANCE
        g1 = l_type.gline * line.dline * line.nlnum * Exponents.CONDUCTANCE
        b1 = l_type.bline * line.dline * line.nlnum * Exponents.SUSCEPTANCE
        g0 = l_type.gline0 * line.dline * line.nlnum * Exponents.CONDUCTANCE
        b0 = l_type.bline0 * line.dline * line.nlnum * Exponents.SUSCEPTANCE

        f_nom = l_type.frnom  # usually 50 Hertz
        u_system_type = VoltageSystemType[ElementVoltageSystemType(l_type.systp).name]

        return Branch(
            name=name,
            node_1=t1_name,
            node_2=t2_name,
            r1=r1,
            x1=x1,
            r0=r0,
            x0=x0,
            g1=g1,
            b1=b1,
            g0=g0,
            b0=b0,
            i_r=i_r,
            description=description,
            u_n=u_nom,
            f_n=f_nom,
            type=BranchType.LINE,
            voltage_system_type=u_system_type,
        )

    @staticmethod
    def determine_line_voltage(u_nom_1: float, u_nom_2: float, l_type: PFTypes.LineType) -> float:
        if round(u_nom_1, 2) == round(u_nom_2, 2):
            return u_nom_1 * Exponents.VOLTAGE  # nominal voltage (V)

        return l_type.uline * Exponents.VOLTAGE  # nominal voltage (V)

    def create_coupler(self, coupler: PFTypes.Coupler, grid_name: str) -> Branch | None:
        name = self.pfi.create_name(coupler, grid_name)
        logger.debug("Creating coupler {coupler_name}...", coupler_name=name)
        export, description = self.get_description(coupler)
        if not export:
            logger.warning("Coupler {coupler_name} not set for export. Skipping.", coupler_name=name)
            return None

        if coupler.bus1 is None or coupler.bus2 is None:
            logger.warning("Coupler {coupler} not connected to buses on both sides. Skipping.", coupler=coupler)
            return None

        t1 = coupler.bus1.cterm
        t2 = coupler.bus2.cterm

        if t1.systype != t2.systype:
            logger.warning("Coupler {coupler} connected to DC and AC bus. Skipping.", coupler=coupler)
            return None

        if coupler.typ_id is not None:
            r1 = coupler.typ_id.R_on
            x1 = coupler.typ_id.X_on
            i_r = coupler.typ_id.Inom
        else:
            r1 = 0
            x1 = 0
            i_r = math.inf

        b1 = 0
        g1 = 0

        u_nom_1 = t1.uknom
        u_nom_2 = t2.uknom

        if round(u_nom_1, 2) == round(u_nom_2, 2):
            u_nom = u_nom_1 * Exponents.VOLTAGE  # nominal voltage (V)
        else:
            logger.warning(
                "Coupler {coupler_name} couples busbars with different voltage levels. Skipping.",
                coupler_name=name,
            )
            return None

        description = self.get_coupler_description(terminal1=t1, terminal2=t2, description=description)

        t1_name = self.pfi.create_name(t1, grid_name)
        t2_name = self.pfi.create_name(t2, grid_name)

        voltage_system_type = VoltageSystemType[TerminalVoltageSystemType(t1.systype).name]

        return Branch(
            name=name,
            node_1=t1_name,
            node_2=t2_name,
            r1=r1,
            x1=x1,
            g1=g1,
            b1=b1,
            i_r=i_r,
            description=description,
            u_n=u_nom,
            type=BranchType.COUPLER,
            voltage_system_type=voltage_system_type,
        )

    def get_coupler_description(
        self,
        terminal1: PFTypes.Terminal,
        terminal2: PFTypes.Terminal,
        description: str,
    ) -> str:
        if self.pfi.is_within_substation(terminal1) and self.pfi.is_within_substation(terminal2):
            if description:
                return "substation internal"

            return "substation internal; " + description

        return description

    def create_transformers(
        self,
        pf_transformers_2w: Sequence[PFTypes.Transformer2W],
        grid_name: str,
    ) -> Sequence[Transformer]:
        logger.info("Creating transformers...")
        return self.create_transformers_2w(pf_transformers_2w, grid_name)

    def create_transformers_2w(
        self,
        transformers_2w: Sequence[PFTypes.Transformer2W],
        grid_name: str,
    ) -> Sequence[Transformer]:
        logger.info("Creating 2-winding transformers...")
        transformers = [self.create_transformer_2w(transformer_2w, grid_name) for transformer_2w in transformers_2w]
        return self.pfi.filter_none(transformers)

    def create_transformer_2w(self, transformer_2w: PFTypes.Transformer2W, grid_name: str) -> Transformer | None:
        name = self.pfi.create_name(element=transformer_2w, grid_name=grid_name)
        logger.debug("Creating 2-winding transformer {transformer_name}...", transformer_name=name)
        export, description = self.get_description(transformer_2w)
        if not export:
            logger.warning(
                "2-winding transformer {transformer_name} not set for export. Skipping.",
                transformer_name=name,
            )
            return None

        if transformer_2w.buslv is None or transformer_2w.bushv is None:
            logger.warning(
                "2-winding transformer {transformer_name} not connected to buses on both sides. Skipping.",
                transformer_name=name,
            )
            return None

        t_high = transformer_2w.bushv.cterm
        t_low = transformer_2w.buslv.cterm

        t_high_name = self.pfi.create_name(element=t_high, grid_name=grid_name)
        t_low_name = self.pfi.create_name(element=t_low, grid_name=grid_name)

        t_type = transformer_2w.typ_id

        if t_type is not None:
            t_number = transformer_2w.ntnum
            vector_group = TVectorGroup[VectorGroup(t_type.vecgrp).name]

            ph_technology = self.transformer_phase_technology(t_type)

            # Transformer Tap Changer
            tap_u_abs = t_type.dutap
            tap_u_phi = t_type.phitr
            tap_min = t_type.ntpmn
            tap_max = t_type.ntpmx
            tap_neutral = t_type.nntap0
            tap_side = self.transformer_tap_side(t_type)

            if bool(t_type.itapch2) is True:
                logger.warning(
                    "2-winding transformer {transformer_name} has second tap changer. Not supported so far. Skipping.",
                    transformer_name=name,
                )
                return None

            # Rated Voltage of the transformer_2w windings itself (CIM: ratedU)
            u_ref_h = t_type.utrn_h
            u_ref_l = t_type.utrn_l

            # Nominal Voltage of connected nodes (CIM: BaseVoltage)
            u_nom_h = transformer_2w.bushv.cterm.uknom
            u_nom_l = transformer_2w.buslv.cterm.uknom

            # Rated values
            p_fe = t_type.pfe  # kW
            i_0 = t_type.curmg  # %
            s_r = t_type.strn  # MVA

            # Create Winding Objects
            # Resulting impedance
            pu2abs = u_ref_h**2 / s_r
            r_1 = t_type.r1pu * pu2abs
            r_0 = t_type.r0pu * pu2abs
            x_1 = t_type.x1pu * pu2abs
            x_0 = t_type.x0pu * pu2abs

            # Wiring group
            vector_phase_angle_clock = t_type.nt2ag
            vector_group_h = WVectorGroup[Vector(t_type.tr2cn_h).name]
            vector_group_l = WVectorGroup[Vector(t_type.tr2cn_l).name]

            wh = Winding(
                node=t_high_name,
                s_r=round(s_r * Exponents.POWER, DecimalDigits.POWER),
                u_r=round(u_ref_h * Exponents.VOLTAGE, DecimalDigits.VOLTAGE),
                u_n=round(u_nom_h * Exponents.VOLTAGE, DecimalDigits.VOLTAGE),
                r1=r_1,
                r0=r_0,
                x1=x_1,
                x0=x_0,
                vector_group=vector_group_h,
                phase_angle_clock=0,
            )

            wl = Winding(
                node=t_low_name,
                s_r=round(s_r * Exponents.POWER, DecimalDigits.POWER),
                u_r=round(u_ref_l * Exponents.VOLTAGE, DecimalDigits.VOLTAGE),
                u_n=round(u_nom_l * Exponents.VOLTAGE, DecimalDigits.VOLTAGE),
                r1=float(0),
                r0=float(0),
                x1=float(0),
                x0=float(0),
                vector_group=vector_group_l,
                phase_angle_clock=int(vector_phase_angle_clock),
            )

            return Transformer(
                node_1=t_high_name,
                node_2=t_low_name,
                name=name,
                number=t_number,
                i_0=i_0,
                p_fe=round(p_fe * 1e3, DecimalDigits.POWER),
                vector_group=vector_group,
                tap_u_abs=tap_u_abs,
                tap_u_phi=tap_u_phi,
                tap_min=tap_min,
                tap_max=tap_max,
                tap_neutral=tap_neutral,
                tap_side=tap_side,
                description=description,
                phase_technology_type=ph_technology,
                windings=[wh, wl],
            )

        logger.warning("Type not set for 2-winding transformer {transformer_name}. Skipping.", transformer_name=name)
        return None

    @staticmethod
    def get_description(
        element: PFTypes.Terminal | PFTypes.LineBase | PFTypes.Element | PFTypes.Coupler | PFTypes.ExternalGrid,
    ) -> tuple[bool, str]:
        desc = element.desc
        if desc:
            if desc[0] == "do_not_export":
                return False, ""

            return True, desc[0]

        return True, ""

    @staticmethod
    def transformer_phase_technology(t_type: PFTypes.Transformer2WType) -> TransformerPhaseTechnologyType | None:
        tech_mapping = {
            1: TransformerPhaseTechnologyType.SINGLE_PH_E,
            2: TransformerPhaseTechnologyType.SINGLE_PH,
            3: TransformerPhaseTechnologyType.THREE_PH,
        }
        return tech_mapping[t_type.nt2ph]

    @staticmethod
    def transformer_tap_side(t_type: PFTypes.Transformer2WType) -> TapSide | None:
        side_mapping_2w = {
            0: TapSide.HV,
            1: TapSide.LV,
        }
        if t_type.itapch:
            return side_mapping_2w.get(t_type.tap_side)

        return None

    def create_loads(  # noqa: PLR0913 # fix
        self,
        consumers: Sequence[PFTypes.Load],
        consumers_lv: Sequence[PFTypes.LoadLV],
        consumers_mv: Sequence[PFTypes.LoadMV],
        generators: Sequence[PFTypes.Generator],
        pv_systems: Sequence[PFTypes.PVSystem],
        grid_name: str,
    ) -> Sequence[Load]:
        logger.info("Creating loads...")
        normal_consumers = self.create_consumers_normal(consumers, grid_name)
        lv_consumers = self.create_consumers_lv(consumers_lv, grid_name)
        load_mvs = self.create_loads_mv(consumers_mv, grid_name)
        gen_producers = self.create_producers_normal(generators, grid_name)
        pv_producers = self.create_producers_pv(pv_systems, grid_name)
        return self.pfi.list_from_sequences(normal_consumers, lv_consumers, load_mvs, gen_producers, pv_producers)

    def create_consumers_normal(self, loads: Sequence[PFTypes.Load], grid_name: str) -> Sequence[Load]:
        logger.info("Creating normal consumers...")
        consumers = [self.create_consumer_normal(load=load, grid_name=grid_name) for load in loads]
        return self.pfi.filter_none(consumers)

    def create_consumer_normal(self, load: PFTypes.Load, grid_name: str) -> Load | None:
        power = self.calc_normal_load_power(load)
        phase_connection_type = (
            LoadPhaseConnectionType(load.typ_id.phtech)
            if load.typ_id is not None
            else LoadPhaseConnectionType.THREE_PH_D
        )
        if power is not None:
            return self.create_consumer(
                load,
                power,
                grid_name,
                system_type=SystemType.FIXED_CONSUMPTION,
                phase_connection_type=phase_connection_type,
            )

        return None

    def create_consumers_lv(self, loads: Sequence[PFTypes.LoadLV], grid_name: str) -> Sequence[Load]:
        logger.info("Creating low voltage consumers...")
        consumers_lv_parts = [self.create_consumers_lv_parts(load, grid_name) for load in loads]
        return self.pfi.list_from_sequences(*consumers_lv_parts)

    def create_consumers_lv_parts(self, load: PFTypes.LoadLV, grid_name: str) -> Sequence[Load]:
        logger.debug("Creating subconsumers for low voltage consumer {name}...", name=load.loc_name)
        powers = self.calc_load_lv_powers(load)
        sfx_pre = "" if len(powers) == 1 else "_({})"

        consumer_lv_parts = [
            self.create_consumer_lv_parts(load=load, grid_name=grid_name, power=power, sfx_pre=sfx_pre, index=i)
            for i, power in enumerate(powers)
        ]
        return self.pfi.list_from_sequences(*consumer_lv_parts)

    def create_consumer_lv_parts(  # noqa: PLR0913 # fix
        self,
        load: PFTypes.LoadLV,
        grid_name: str,
        power: LoadLV,
        sfx_pre: str,
        index: int,
    ) -> Sequence[Load]:
        logger.debug(
            "Creating partial consumers for subconsumer {index} of low voltage consumer {name}...",
            index=index,
            name=load.loc_name,
        )
        phase_connection_type = LoadPhaseConnectionType(load.phtech)
        consumer_fixed = (
            self.create_consumer(
                load,
                power.fixed,
                grid_name,
                system_type=SystemType.FIXED_CONSUMPTION,
                phase_connection_type=phase_connection_type,
                name_suffix=sfx_pre.format(index) + "_" + SystemType.FIXED_CONSUMPTION.name,
            )
            if power.fixed.pow_app_abs != 0
            else None
        )
        consumer_night = (
            self.create_consumer(
                load,
                power.night,
                grid_name,
                system_type=SystemType.NIGHT_STORAGE,
                phase_connection_type=phase_connection_type,
                name_suffix=sfx_pre.format(index) + "_" + SystemType.NIGHT_STORAGE.name,
            )
            if power.night.pow_app_abs != 0
            else None
        )
        consumer_flex = (
            self.create_consumer(
                load,
                power.flexible,
                grid_name,
                system_type=SystemType.VARIABLE_CONSUMPTION,
                phase_connection_type=phase_connection_type,
                name_suffix=sfx_pre.format(index) + "_" + SystemType.VARIABLE_CONSUMPTION.name,
            )
            if power.flexible.pow_app_abs != 0
            else None
        )
        return self.pfi.filter_none([consumer_fixed, consumer_night, consumer_flex])

    def create_loads_mv(self, loads: Sequence[PFTypes.LoadMV], grid_name: str) -> Sequence[Load]:
        logger.info("Creating medium voltage loads...")
        loads_mv_ = [self.create_load_mv(load=load, grid_name=grid_name) for load in loads]
        loads_mv = self.pfi.list_from_sequences(*loads_mv_)
        return self.pfi.filter_none(loads_mv)

    def create_load_mv(self, load: PFTypes.LoadMV, grid_name: str) -> Sequence[Load | None]:
        power = self.calc_load_mv_power(load)
        logger.debug("Creating medium voltage load {name}...", name=load.loc_name)
        phase_connection_type = (
            LoadPhaseConnectionType(load.typ_id.phtech)
            if load.typ_id is not None
            else LoadPhaseConnectionType.THREE_PH_D
        )
        consumer = self.create_consumer(
            load=load,
            power=power.consumer,
            grid_name=grid_name,
            phase_connection_type=phase_connection_type,
            system_type=SystemType.FIXED_CONSUMPTION,
            name_suffix="_CONSUMER",
        )
        producer = self.create_producer(
            generator=load,
            power=power.producer,
            gen_name=load.loc_name,
            grid_name=grid_name,
            phase_connection_type=phase_connection_type,
            system_type=SystemType.OTHER,
            name_suffix="_PRODUCER",
        )

        return [consumer, producer]

    def create_consumer(  # noqa: PLR0913 # fix
        self,
        load: PFTypes.LoadBase,
        power: LoadPower,
        grid_name: str,
        system_type: SystemType,
        phase_connection_type: LoadPhaseConnectionType,
        name_suffix: str = "",
    ) -> Load | None:
        l_name = self.pfi.create_name(load, grid_name) + name_suffix
        logger.debug("Creating consumer {load_name}...", load_name=l_name)
        export, description = self.get_description(load)
        if not export:
            logger.warning("Consumer {load_name} not set for export. Skipping.", load_name=l_name)
            return None

        bus = load.bus1
        if bus is None:
            logger.warning("Consumer {load_name} not connected to any bus. Skipping.", load_name=l_name)
            return None

        phase_id = bus.cPhInfo
        if phase_id == "SPN":
            logger.warning(
                "Load {load_name} is a 1-phase load which is currently not supported. Skipping.",
                load_name=load.loc_name,
            )
            return None

        terminal = bus.cterm
        t_name = self.pfi.create_name(terminal, grid_name)

        u_n = round(terminal.uknom * Exponents.VOLTAGE, DecimalDigits.VOLTAGE)  # voltage in V

        rated_power = power.as_rated_power()
        logger.debug(
            "{load_name}: there is no real rated power, it is calculated based on actual power.",
            load_name=l_name,
        )

        load_model_p = self.load_model_of(load, specifier="p")
        active_power = ActivePower(load_model=load_model_p)

        load_model_q = self.load_model_of(load, specifier="q")
        reactive_power = ReactivePower(load_model=load_model_q)

        phase_connection_type_ = PhaseConnectionType[phase_connection_type.name]
        connected_phases = [Phase[PFPhase(phase).name] for phase in textwrap.wrap(bus.cPhInfo, 2)]
        voltage_system_type = (
            VoltageSystemType[ElementVoltageSystemType(load.typ_id.systp).name]
            if load.typ_id is not None
            else VoltageSystemType[TerminalVoltageSystemType(terminal.systype).name]
        )

        return Load(
            name=l_name,
            node=t_name,
            description=description,
            u_n=u_n,
            rated_power=rated_power,
            active_power=active_power,
            reactive_power=reactive_power,
            type=LoadType.CONSUMER,
            connected_phases=connected_phases,
            system_type=system_type,
            phase_connection_type=phase_connection_type_,
            voltage_system_type=voltage_system_type,
        )

    @staticmethod
    def load_model_of(load: PFTypes.LoadBase, specifier: Literal["p", "q"]) -> LoadModel:
        load_type = load.typ_id
        if load_type is not None:
            if load_type.loddy != FULL_DYNAMIC:
                logger.warning(
                    "Please check load model setting of {load_name} for RMS simulation.",
                    load_name=load.loc_name,
                )
                logger.info(
                    "Consider to set 100% dynamic mode, but with time constants =0 (=same static model for RMS).",
                )

            name = load_type.loc_name

            if specifier == "p":
                return LoadModel(
                    name=name,
                    c_p=load_type.aP,
                    c_i=load_type.bP,
                    exp_p=load_type.kpu0,
                    exp_i=load_type.kpu1,
                    exp_z=load_type.kpu,
                )

            if specifier == "q":
                return LoadModel(
                    name=name,
                    c_p=load_type.aQ,
                    c_i=load_type.bQ,
                    exp_p=load_type.kqu0,
                    exp_i=load_type.kqu1,
                    exp_z=load_type.kqu,
                )

            msg = "unreachable"
            raise RuntimeError(msg)

        return LoadModel()  # default: 100% power-const. load

    def create_producers_normal(
        self,
        generators: Sequence[PFTypes.Generator],
        grid_name: str,
    ) -> Sequence[Load]:
        logger.info("Creating normal producers...")
        producers = [self.create_producer_normal(generator=generator, grid_name=grid_name) for generator in generators]
        return self.pfi.filter_none(producers)

    def create_producer_normal(
        self,
        generator: PFTypes.Generator,
        grid_name: str,
    ) -> Load | None:
        power = self.calc_normal_gen_power(generator)
        gen_name = self.pfi.create_generator_name(generator)
        system_type = SystemType[GeneratorSystemType(generator.aCategory).name]
        phase_connection_type = GeneratorPhaseConnectionType(generator.phtech)
        external_controller_name = self.get_external_controller_name(generator)
        return self.create_producer(
            generator=generator,
            power=power,
            gen_name=gen_name,
            grid_name=grid_name,
            phase_connection_type=phase_connection_type,
            system_type=system_type,
            external_controller_name=external_controller_name,
        )

    def create_producers_pv(
        self,
        generators: Sequence[PFTypes.PVSystem],
        grid_name: str,
    ) -> Sequence[Load]:
        logger.info("Creating PV producers...")
        producers = [self.create_producer_pv(generator=generator, grid_name=grid_name) for generator in generators]
        return self.pfi.filter_none(producers)

    def create_producer_pv(
        self,
        generator: PFTypes.PVSystem,
        grid_name: str,
    ) -> Load | None:
        power = self.calc_normal_gen_power(generator)
        gen_name = self.pfi.create_generator_name(generator)
        phase_connection_type = GeneratorPhaseConnectionType(generator.phtech)
        system_type = SystemType.PV
        return self.create_producer(
            generator=generator,
            power=power,
            gen_name=gen_name,
            grid_name=grid_name,
            phase_connection_type=phase_connection_type,
            system_type=system_type,
        )

    def get_external_controller_name(self, gen: PFTypes.Generator | PFTypes.PVSystem) -> str | None:
        controller = gen.c_pstac
        if controller is None:
            return None

        return self.pfi.create_generator_name(gen, generator_name=controller.loc_name)

    def calc_normal_gen_power(self, gen: PFTypes.Generator | PFTypes.PVSystem) -> LoadPower:
        pow_app = gen.sgn * gen.ngnum
        cosphi = gen.cosn
        # in PF for producer: ind. cosphi = over excited; cap. cosphi = under excited
        cosphi_dir = CosphiDir.UE if gen.pf_recap == 1 else CosphiDir.OE
        return LoadPower.from_sc_sym(pow_app=pow_app, cosphi=cosphi, cosphi_dir=cosphi_dir, scaling=gen.scale0)

    def create_producer(  # noqa: PLR0913 # fix
        self,
        generator: PFTypes.GeneratorBase | PFTypes.LoadMV,
        gen_name: str,
        power: LoadPower,
        grid_name: str,
        system_type: SystemType,
        phase_connection_type: GeneratorPhaseConnectionType | LoadPhaseConnectionType,
        external_controller_name: str | None = None,
        name_suffix: str = "",
    ) -> Load | None:
        gen_name = self.pfi.create_name(generator, grid_name, element_name=gen_name) + name_suffix
        logger.debug("Creating producer {gen_name}...", gen_name=gen_name)
        export, description = self.get_description(generator)
        if not export:
            logger.warning(
                "Generator {gen_name} not set for export. Skipping.",
                gen_name=gen_name,
            )
            return None

        bus = generator.bus1
        if bus is None:
            logger.warning("Generator {gen_name} not connected to any bus. Skipping.", gen_name=gen_name)
            return None

        terminal = bus.cterm
        t_name = self.pfi.create_name(terminal, grid_name)
        u_n = round(terminal.uknom * Exponents.VOLTAGE, DecimalDigits.VOLTAGE)  # voltage in V

        # Rated Values of single unit
        rated_power = power.as_rated_power()
        reactive_power = ReactivePower(external_controller_name=external_controller_name)

        phase_connection_type_ = PhaseConnectionType[phase_connection_type.name]
        connected_phases = [Phase[PFPhase(phase).name] for phase in textwrap.wrap(bus.cPhInfo, 2)]

        return Load(
            name=gen_name,
            node=t_name,
            description=description,
            u_n=u_n,
            rated_power=rated_power,
            active_power=ActivePower(),
            reactive_power=reactive_power,
            type=LoadType.PRODUCER,
            connected_phases=connected_phases,
            system_type=system_type,
            phase_connection_type=phase_connection_type_,
            voltage_system_type=VoltageSystemType.AC,
        )

    def create_topology_case(self, meta: Meta, data: PowerFactoryData) -> TopologyCase:
        logger.debug("Creating topology case...")
        switch_states = self.create_switch_states(data.switches)
        coupler_states = self.create_coupler_states(data.couplers)
        elements: Sequence[ElementBase] = self.pfi.list_from_sequences(
            data.loads,
            data.loads_lv,
            data.loads_mv,
            data.generators,
            data.pv_systems,
            data.external_grids,
        )
        node_power_on_states = self.create_node_power_on_states(data.terminals)
        line_power_on_states = self.create_element_power_on_states(data.lines)
        transformer_2w_power_on_states = self.create_element_power_on_states(data.transformers_2w)
        element_power_on_states = self.create_element_power_on_states(elements)
        power_on_states = self.pfi.list_from_sequences(
            switch_states,
            coupler_states,
            node_power_on_states,
            line_power_on_states,
            transformer_2w_power_on_states,
            element_power_on_states,
        )
        power_on_states = self.merge_power_on_states(power_on_states)
        return TopologyCase(meta=meta, elements=power_on_states)

    def merge_power_on_states(self, power_on_states: Sequence[ElementState]) -> Sequence[ElementState]:
        entry_names = {entry.name for entry in power_on_states}
        return [
            self.merge_entries(entry_name=entry_name, power_on_states=power_on_states) for entry_name in entry_names
        ]

    def merge_entries(self, entry_name: str, power_on_states: Sequence[ElementState]) -> ElementState:
        entries = {entry for entry in power_on_states if entry.name == entry_name}
        disabled = any(entry.disabled for entry in entries)
        open_switches = tuple(itertools.chain.from_iterable([entry.open_switches for entry in entries]))
        return ElementState(name=entry_name, disabled=disabled, open_switches=open_switches)

    def create_switch_states(self, switches: Sequence[PFTypes.Switch]) -> Sequence[ElementState]:
        """Create element states for all type of elements based on if the switch is open.

        The element states contain a node reference.

        Arguments:
            switches {Sequence[PFTypes.Switch]} -- sequence of PowerFactory objects of type Switch

        Returns:
            Sequence[ElementState] -- set of element states
        """

        logger.info("Creating switch states...")
        states = [self.create_switch_state(switch=switch) for switch in switches]
        return self.pfi.filter_none(states)

    def create_switch_state(self, switch: PFTypes.Switch) -> ElementState | None:
        if not switch.isclosed:
            cub = switch.fold_id
            element = cub.obj_id
            if element is not None:
                terminal = cub.cterm
                node_name = self.pfi.create_name(terminal, self.grid_name)
                element_name = self.pfi.create_name(element, self.grid_name)
                logger.debug(
                    "Creating switch state {node_name}-{element_name}...",
                    node_name=node_name,
                    element_name=element_name,
                )
                return ElementState(name=element_name, open_switches=(node_name,))

        return None

    def create_coupler_states(self, couplers: Sequence[PFTypes.Coupler]) -> Sequence[ElementState]:
        """Create element states for all type of elements based on if the coupler is open.

        The element states contain a node reference.

        Arguments:
            swtiches {Sequence[PFTypes.Coupler]} -- sequence of PowerFactory objects of type Coupler

        Returns:
            Sequence[ElementState] -- set of element states
        """
        logger.info("Creating coupler states...")
        states = [self.create_coupler_state(coupler=coupler) for coupler in couplers]
        return self.pfi.filter_none(states)

    def create_coupler_state(self, coupler: PFTypes.Coupler) -> ElementState | None:
        if not coupler.isclosed:
            element_name = self.pfi.create_name(coupler, self.grid_name)
            logger.debug(
                "Creating switch state {element_name}...",
                element_name=element_name,
            )
            return ElementState(name=element_name, disabled=True)

        return None

    def create_node_power_on_states(self, terminals: Sequence[PFTypes.Terminal]) -> Sequence[ElementState]:
        """Create element states based on if the connected nodes are out of service.

        The element states contain a node reference.

        Arguments:
            terminals {Sequence[PFTypes.Terminal]} -- sequence of PowerFactory objects of type Terminal

        Returns:
            Sequence[ElementState] -- set of element states
        """

        logger.info("Creating node power on states...")
        states = [self.create_node_power_on_state(terminal=terminal) for terminal in terminals]
        return self.pfi.filter_none(states)

    def create_node_power_on_state(self, terminal: PFTypes.Terminal) -> ElementState | None:
        if terminal.outserv:
            node_name = self.pfi.create_name(terminal, self.grid_name)
            logger.debug(
                "Creating node power on state {node_name}...",
                node_name=node_name,
            )
            return ElementState(name=node_name, disabled=True)

        return None

    def create_element_power_on_states(
        self,
        elements: Sequence[ElementBase | PFTypes.Line | PFTypes.Transformer2W],
    ) -> Sequence[ElementState]:
        """Create element states for one-sided connected elements based on if the elements are out of service.

        The element states contain no node reference.

        Arguments:
            elements {Sequence[ElementBase} -- sequence of one-sided connected PowerFactory objects

        Returns:
            Sequence[ElementState] -- set of element states
        """
        logger.info("Creating element power on states...")
        states = [self.create_element_power_on_state(element=element) for element in elements]
        return self.pfi.filter_none(states)

    def create_element_power_on_state(
        self,
        element: ElementBase | PFTypes.Line | PFTypes.Transformer2W,
    ) -> ElementState | None:
        if element.outserv:
            element_name = self.pfi.create_name(element, self.grid_name)
            logger.debug(
                "Creating element power on state {element_name}...",
                element_name=element_name,
            )
            return ElementState(name=element_name, disabled=True)

        return None

    def create_steadystate_case(self, meta: Meta, data: PowerFactoryData) -> SteadystateCase:
        logger.info("Creating steadystate case...")
        loads = self.create_loads_ssc(
            consumers=data.loads,
            consumers_lv=data.loads_lv,
            consumers_mv=data.loads_mv,
            generators=data.generators,
            pv_systems=data.pv_systems,
            grid_name=data.name,
        )
        transformers = self.create_transformers_ssc(
            pf_transformers_2w=data.transformers_2w,
            grid_name=data.name,
        )
        external_grids = self.create_external_grid_ssc(
            ext_grids=data.external_grids,
            grid_name=data.name,
        )

        return SteadystateCase(
            meta=meta,
            loads=loads,
            transformers=transformers,
            external_grids=external_grids,
        )

    def create_transformers_ssc(
        self,
        pf_transformers_2w: Sequence[PFTypes.Transformer2W],
        grid_name: str,
    ) -> Sequence[TransformerSSC]:
        logger.info("Creating transformers steadystate case...")
        transformers_2w_sscs = self.create_transformers_2w_ssc(pf_transformers_2w, grid_name)
        return self.pfi.list_from_sequences(transformers_2w_sscs)

    def create_transformers_2w_ssc(
        self,
        pf_transformers_2w: Sequence[PFTypes.Transformer2W],
        grid_name: str,
    ) -> Sequence[TransformerSSC]:
        logger.info("Creating 2-winding transformers steadystate cases...")
        transformers_2w_sscs = [
            self.create_transformer_2w_ssc(pf_transformer_2w=pf_transformer_2w, grid_name=grid_name)
            for pf_transformer_2w in pf_transformers_2w
        ]
        return self.pfi.filter_none(transformers_2w_sscs)

    def create_transformer_2w_ssc(
        self,
        pf_transformer_2w: PFTypes.Transformer2W,
        grid_name: str,
    ) -> TransformerSSC | None:
        name = self.pfi.create_name(pf_transformer_2w, grid_name)
        logger.debug("Creating 2-winding transformer {transformer_name} steadystate case...", transformer_name=name)
        export, _ = self.get_description(pf_transformer_2w)
        if not export:
            logger.warning("Transformer {transformer_name} not set for export. Skipping.", transformer_name=name)
            return None

        # Transformer Tap Changer
        t_type = pf_transformer_2w.typ_id
        tap_pos = None if t_type is None else pf_transformer_2w.nntap

        return TransformerSSC(name=name, tap_pos=tap_pos)

    def create_external_grid_ssc(
        self,
        ext_grids: Sequence[PFTypes.ExternalGrid],
        grid_name: str,
    ) -> Sequence[ExternalGridSSC]:
        logger.info("Creating external grids steadystate case...")
        ext_grid_sscs = [self.create_external_grid_ssc_state(grid, grid_name) for grid in ext_grids]
        return self.pfi.filter_none(ext_grid_sscs)

    def create_external_grid_ssc_state(
        self,
        ext_grid: PFTypes.ExternalGrid,
        grid_name: str,
    ) -> ExternalGridSSC | None:
        name = self.pfi.create_name(ext_grid, grid_name)
        logger.debug("Creating external grid {ext_grid_name} steadystate case...", ext_grid_name=name)
        export, _ = self.get_description(ext_grid)
        if not export:
            logger.warning("External grid {ext_grid_name} not set for export. Skipping.", ext_grid_name=name)
            return None

        if ext_grid.bus1 is None:
            logger.warning("External grid {ext_grid_name} not connected to any bus. Skipping.", ext_grid_name=name)
            return None

        g_type = GridType(ext_grid.bustp)
        if g_type == GridType.SL:
            return ExternalGridSSC(
                name=name,
                u_0=round(ext_grid.usetp * ext_grid.bus1.cterm.uknom * Exponents.VOLTAGE, DecimalDigits.VOLTAGE),
                phi_0=ext_grid.phiini,
            )

        if g_type == GridType.PV:
            return ExternalGridSSC(
                name=name,
                u_0=round(ext_grid.usetp * ext_grid.bus1.cterm.uknom * Exponents.VOLTAGE, DecimalDigits.VOLTAGE),
                p_0=round(ext_grid.pgini * Exponents.POWER, DecimalDigits.POWER),
            )

        if g_type == GridType.PQ:
            return ExternalGridSSC(
                name=name,
                p_0=round(ext_grid.pgini * Exponents.POWER, DecimalDigits.POWER),
                q_0=round(ext_grid.qgini * Exponents.POWER, DecimalDigits.POWER),
            )

        return ExternalGridSSC(name=name)

    def create_loads_ssc(  # noqa: PLR0913
        self,
        consumers: Sequence[PFTypes.Load],
        consumers_lv: Sequence[PFTypes.LoadLV],
        consumers_mv: Sequence[PFTypes.LoadMV],
        generators: Sequence[PFTypes.Generator],
        pv_systems: Sequence[PFTypes.PVSystem],
        grid_name: str,
    ) -> Sequence[LoadSSC]:
        logger.info("Creating loads steadystate case...")
        normal_consumers = self.create_consumers_ssc_normal(loads=consumers, grid_name=grid_name)
        lv_consumers = self.create_consumers_ssc_lv(loads=consumers_lv, grid_name=grid_name)
        mv_consumers = self.create_loads_ssc_mv(loads=consumers_mv, grid_name=grid_name)
        gen_producers = self.create_producers_ssc(loads=generators, grid_name=grid_name)
        pv_producers = self.create_producers_ssc(loads=pv_systems, grid_name=grid_name)
        return self.pfi.list_from_sequences(normal_consumers, lv_consumers, mv_consumers, gen_producers, pv_producers)

    def create_consumers_ssc_normal(
        self,
        loads: Sequence[PFTypes.Load],
        grid_name: str,
    ) -> Sequence[LoadSSC]:
        logger.info("Creating normal consumers steadystate case...")
        consumers_ssc = [self.create_consumer_ssc_normal(load, grid_name) for load in loads]
        return self.pfi.filter_none(consumers_ssc)

    def create_consumer_ssc_normal(
        self,
        load: PFTypes.Load,
        grid_name: str,
    ) -> LoadSSC | None:
        power = self.calc_normal_load_power(load)
        if power is not None:
            return self.create_consumer_ssc(load, power, grid_name)

        return None

    def calc_normal_load_power(self, load: PFTypes.Load) -> LoadPower | None:
        logger.debug("Calculating power for normal load {load_name}...", load_name=load.loc_name)
        power = self.calc_normal_load_power_sym(load) if not load.i_sym else self.calc_normal_load_power_asym(load)

        if power:
            return power

        logger.warning("Power is not set for load {load_name}. Skipping.", load_name=load.loc_name)
        return None

    def calc_normal_load_power_sym(self, load: PFTypes.Load) -> LoadPower | None:  # noqa: PLR0911
        load_type = load.mode_inp
        scaling = load.scale0
        u_nom = None if load.bus1 is None else load.bus1.cterm.uknom
        cosphi_dir = CosphiDir.UE if load.pf_recap == 0 else CosphiDir.OE
        if load_type == "DEF" or load_type == "PQ":
            return LoadPower.from_pq_sym(pow_act=load.plini, pow_react=load.qlini, scaling=scaling)

        if load_type == "PC":
            return LoadPower.from_pc_sym(
                pow_act=load.plini,
                cosphi=load.coslini,
                cosphi_dir=cosphi_dir,
                scaling=scaling,
            )

        if load_type == "IC":
            if u_nom is not None:
                return LoadPower.from_ic_sym(
                    voltage=load.u0 * u_nom,
                    current=load.ilini,
                    cosphi=load.coslini,
                    cosphi_dir=cosphi_dir,
                    scaling=scaling,
                )

            logger.warning(
                "Load {load_name} is not connected to grid. Can not calculate power based on current and cosphi as voltage is missing. Skipping.",
                load_name=load.loc_name,
            )
            return None

        if load_type == "SC":
            return LoadPower.from_sc_sym(
                pow_app=load.slini,
                cosphi=load.coslini,
                cosphi_dir=cosphi_dir,
                scaling=scaling,
            )

        if load_type == "QC":
            return LoadPower.from_qc_sym(pow_react=load.qlini, cosphi=load.coslini, scaling=scaling)

        if load_type == "IP":
            if u_nom is not None:
                return LoadPower.from_ip_sym(
                    voltage=load.u0 * u_nom,
                    current=load.ilini,
                    pow_act=load.plini,
                    cosphi_dir=cosphi_dir,
                    scaling=scaling,
                )
            logger.warning(
                "Load {load_name} is not connected to grid. Can not calculate power based on current and active power as voltage is missing. Skipping.",
                load_name=load.loc_name,
            )
            return None

        if load_type == "SP":
            return LoadPower.from_sp_sym(pow_app=load.slini, pow_act=load.plini, cosphi_dir=cosphi_dir, scaling=scaling)

        if load_type == "SQ":
            return LoadPower.from_sq_sym(pow_app=load.slini, pow_react=load.qlini, scaling=scaling)

        msg = "unreachable"
        raise RuntimeError(msg)

    def calc_normal_load_power_asym(self, load: PFTypes.Load) -> LoadPower | None:  # noqa: PLR0911
        load_type = load.mode_inp
        scaling = load.scale0
        u_nom = None if load.bus1 is None else load.bus1.cterm.uknom
        cosphi_dir = CosphiDir.UE if load.pf_recap == 0 else CosphiDir.OE
        if load_type == "DEF" or load_type == "PQ":
            return LoadPower.from_pq_asym(
                pow_act_a=load.plinir,
                pow_act_b=load.plinis,
                pow_act_c=load.plinit,
                pow_react_a=load.qlinir,
                pow_react_b=load.qlinis,
                pow_react_c=load.qlinit,
                scaling=scaling,
            )

        if load_type == "PC":
            return LoadPower.from_pc_asym(
                pow_act_a=load.plinir,
                pow_act_b=load.plinis,
                pow_act_c=load.plinit,
                cosphi_a=load.coslinir,
                cosphi_b=load.coslinis,
                cosphi_c=load.coslinit,
                cosphi_dir=cosphi_dir,
                scaling=scaling,
            )

        if load_type == "IC":
            if u_nom is not None:
                return LoadPower.from_ic_asym(
                    voltage=load.u0 * u_nom,
                    current_a=load.ilinir,
                    current_b=load.ilinis,
                    current_c=load.ilinit,
                    cosphi_a=load.coslinir,
                    cosphi_b=load.coslinis,
                    cosphi_c=load.coslinit,
                    cosphi_dir=cosphi_dir,
                    scaling=scaling,
                )
            logger.warning(
                "Load {load_name} is not connected to grid. Can not calculate power based on current and cosphi as voltage is missing. Skipping.",
                load_name=load.loc_name,
            )
            return None

        if load_type == "SC":
            return LoadPower.from_sc_asym(
                pow_app_a=load.slinir,
                pow_app_b=load.slinis,
                pow_app_c=load.slinit,
                cosphi_a=load.coslinir,
                cosphi_b=load.coslinis,
                cosphi_c=load.coslinit,
                cosphi_dir=cosphi_dir,
                scaling=scaling,
            )

        if load_type == "QC":
            return LoadPower.from_qc_asym(
                pow_react_a=load.qlinir,
                pow_react_b=load.qlinis,
                pow_react_c=load.qlinit,
                cosphi_a=load.coslinir,
                cosphi_b=load.coslinis,
                cosphi_c=load.coslinit,
                scaling=scaling,
            )

        if load_type == "IP":
            if u_nom is not None:
                return LoadPower.from_ip_asym(
                    voltage=load.u0 * u_nom,
                    current_a=load.ilinir,
                    current_b=load.ilinis,
                    current_c=load.ilinit,
                    pow_act_a=load.plinir,
                    pow_act_b=load.plinis,
                    pow_act_c=load.plinit,
                    cosphi_dir=cosphi_dir,
                    scaling=scaling,
                )
            logger.warning(
                "Load {load_name} is not connected to grid. Can not calculate power based on current and active power as voltage is missing. Skipping.",
                load_name=load.loc_name,
            )
            return None

        if load_type == "SP":
            return LoadPower.from_sp_asym(
                pow_app_a=load.slinir,
                pow_app_b=load.slinis,
                pow_app_c=load.slinit,
                pow_act_a=load.plinir,
                pow_act_b=load.plinis,
                pow_act_c=load.plinit,
                cosphi_dir=cosphi_dir,
                scaling=scaling,
            )

        if load_type == "SQ":
            return LoadPower.from_sq_asym(
                pow_app_a=load.slinir,
                pow_app_b=load.slinis,
                pow_app_c=load.slinit,
                pow_react_a=load.qlinir,
                pow_react_b=load.qlinis,
                pow_react_c=load.qlinit,
                scaling=scaling,
            )

        msg = "unreachable"
        raise RuntimeError(msg)

    def create_consumers_ssc_lv(self, loads: Sequence[PFTypes.LoadLV], grid_name: str) -> Sequence[LoadSSC]:
        logger.info("Creating low voltage consumers steadystate case...")
        consumers_ssc_lv_parts = [self.create_consumers_ssc_lv_parts(load, grid_name) for load in loads]
        return list(itertools.chain.from_iterable(consumers_ssc_lv_parts))

    def create_consumers_ssc_lv_parts(self, load: PFTypes.LoadLV, grid_name: str) -> Sequence[LoadSSC]:
        powers = self.calc_load_lv_powers(load)
        sfx_pre = "" if len(powers) == 1 else "_({})"

        consumer_ssc_lv_parts = [
            self.create_consumer_ssc_lv_parts(load=load, grid_name=grid_name, power=power, sfx_pre=sfx_pre, index=i)
            for i, power in enumerate(powers)
        ]
        return list(itertools.chain.from_iterable(consumer_ssc_lv_parts))

    def create_consumer_ssc_lv_parts(  # noqa: PLR0913 # fix
        self,
        load: PFTypes.LoadLV,
        grid_name: str,
        power: LoadLV,
        sfx_pre: str,
        index: int,
    ) -> Sequence[LoadSSC]:
        consumer_fixed_ssc = (
            self.create_consumer_ssc(
                load,
                power.fixed,
                grid_name,
                name_suffix=sfx_pre.format(index) + "_" + SystemType.FIXED_CONSUMPTION.name,
            )
            if power.fixed.pow_app_abs != 0
            else None
        )
        consumer_night_ssc = (
            self.create_consumer_ssc(
                load,
                power.night,
                grid_name,
                name_suffix=sfx_pre.format(index) + "_" + SystemType.NIGHT_STORAGE.name,
            )
            if power.night.pow_app_abs != 0
            else None
        )
        consumer_flexible_ssc = (
            self.create_consumer_ssc(
                load,
                power.flexible,
                grid_name,
                name_suffix=sfx_pre.format(index) + "_" + SystemType.VARIABLE_CONSUMPTION.name,
            )
            if power.flexible.pow_app_abs != 0
            else None
        )
        return self.pfi.filter_none([consumer_fixed_ssc, consumer_night_ssc, consumer_flexible_ssc])

    def calc_load_lv_powers(self, load: PFTypes.LoadLV) -> Sequence[LoadLV]:
        subloads = self.pfi.subloads_of(load)
        if not subloads:
            return [self.calc_load_lv_power(load)]

        return [self.calc_load_lv_power_sym(sl) for sl in subloads]

    def calc_load_lv_power(self, load: PFTypes.LoadLV) -> LoadLV:
        logger.debug("Calculating power for low voltage load {load_name}...", load_name=load.loc_name)
        scaling = load.scale0
        cosphi_dir = CosphiDir.UE if load.pf_recap == 0 else CosphiDir.OE
        if not load.i_sym:
            power_fixed = self.calc_load_lv_power_fixed_sym(load=load, scaling=scaling)
        else:
            power_fixed = self.calc_load_lv_power_fixed_asym(load=load, scaling=scaling)

        power_night = LoadPower.from_pq_sym(
            pow_act=load.pnight,
            pow_react=0,
            scaling=1,
        )
        power_flexible = LoadPower.from_sc_sym(
            pow_app=load.cSav,
            cosphi=load.ccosphi,
            cosphi_dir=cosphi_dir,
            scaling=1,
        )
        return LoadLV(fixed=power_fixed, night=power_night, flexible=power_flexible)

    def calc_load_lv_power_sym(self, load: PFTypes.LoadLVP) -> LoadLV:
        power_fixed = self.calc_load_lv_power_fixed_sym(load, scaling=1)
        power_night = LoadPower.from_pq_sym(
            pow_act=load.pnight,
            pow_react=0,
            scaling=1,
        )
        cosphi_dir = CosphiDir.UE if load.pf_recap == 0 else CosphiDir.OE
        power_flexible = LoadPower.from_sc_sym(
            pow_app=load.cSav,
            cosphi=load.ccosphi,
            cosphi_dir=cosphi_dir,
            scaling=1,
        )
        return LoadLV(fixed=power_fixed, night=power_night, flexible=power_flexible)

    def calc_load_lv_power_fixed_sym(
        self,
        load: PFTypes.LoadLV | PFTypes.LoadLVP,
        scaling: float,
    ) -> LoadPower:
        load_type = load.iopt_inp
        cosphi_dir = CosphiDir.UE if load.pf_recap == 0 else CosphiDir.OE
        if load_type == IOpt.S_COSPHI:
            return LoadPower.from_sc_sym(
                pow_app=load.slini,
                cosphi=load.coslini,
                cosphi_dir=cosphi_dir,
                scaling=scaling,
            )

        if load_type == IOpt.P_COSPHI:
            return LoadPower.from_pc_sym(
                pow_act=load.plini,
                cosphi=load.coslini,
                cosphi_dir=cosphi_dir,
                scaling=scaling,
            )

        if load_type == IOpt.U_I_COSPHI:
            return LoadPower.from_ic_sym(
                voltage=load.ulini,
                current=load.ilini,
                cosphi=load.coslini,
                cosphi_dir=cosphi_dir,
                scaling=scaling,
            )

        if load_type == IOpt.E_COSPHI:
            return LoadPower.from_pc_sym(
                pow_act=load.cplinia,
                cosphi=load.coslini,
                cosphi_dir=cosphi_dir,
                scaling=scaling,
            )

        msg = "unreachable"
        raise RuntimeError(msg)

    def calc_load_lv_power_fixed_asym(
        self,
        load: PFTypes.LoadLV,
        scaling: float,
    ) -> LoadPower:
        load_type = load.iopt_inp
        cosphi_dir = CosphiDir.UE if load.pf_recap == 0 else CosphiDir.OE
        if load_type == IOpt.S_COSPHI:
            return LoadPower.from_sc_asym(
                pow_app_a=load.slinir,
                pow_app_b=load.slinis,
                pow_app_c=load.slinit,
                cosphi_a=load.coslinir,
                cosphi_b=load.coslinis,
                cosphi_c=load.coslinit,
                cosphi_dir=cosphi_dir,
                scaling=scaling,
            )
        if load_type == IOpt.P_COSPHI:
            return LoadPower.from_pc_asym(
                pow_act_a=load.plinir,
                pow_act_b=load.plinis,
                pow_act_c=load.plinit,
                cosphi_a=load.coslinir,
                cosphi_b=load.coslinis,
                cosphi_c=load.coslinit,
                cosphi_dir=cosphi_dir,
                scaling=scaling,
            )
        if load_type == IOpt.U_I_COSPHI:
            return LoadPower.from_ic_asym(
                voltage=load.ulini,
                current_a=load.ilinir,
                current_b=load.ilinis,
                current_c=load.ilinit,
                cosphi_a=load.coslinir,
                cosphi_b=load.coslinis,
                cosphi_c=load.coslinit,
                cosphi_dir=cosphi_dir,
                scaling=scaling,
            )

        msg = "unreachable"
        raise RuntimeError(msg)

    def create_loads_ssc_mv(
        self,
        loads: Sequence[PFTypes.LoadMV],
        grid_name: str,
    ) -> Sequence[LoadSSC]:
        logger.info("Creating medium voltage loads steadystate case...")
        loads_ssc_mv_ = [self.create_load_ssc_mv(load=load, grid_name=grid_name) for load in loads]
        loads_ssc_mv = self.pfi.list_from_sequences(*loads_ssc_mv_)
        return self.pfi.filter_none(loads_ssc_mv)

    def create_load_ssc_mv(
        self,
        load: PFTypes.LoadMV,
        grid_name: str,
    ) -> Sequence[LoadSSC | None]:
        power = self.calc_load_mv_power(load)
        consumer_ssc = self.create_consumer_ssc(load, power.consumer, grid_name, name_suffix="_CONSUMER")
        producer_ssc = self.create_consumer_ssc(load, power.producer, grid_name, name_suffix="_PRODUCER")
        return [consumer_ssc, producer_ssc]

    def calc_load_mv_power(self, load: PFTypes.LoadMV) -> LoadMV:
        logger.debug("Calculating power for medium voltage load {load_name}...", load_name=load.loc_name)
        if not load.ci_sym:
            return self.calc_load_mv_power_sym(load)

        return self.calc_load_mv_power_asym(load)

    def calc_load_mv_power_sym(self, load: PFTypes.LoadMV) -> LoadMV:
        load_type = load.mode_inp
        scaling_cons = load.scale0
        scaling_prod = load.gscale * -1  # to be in line with demand based counting system
        # in PF for consumer: ind. cosphi = under excited; cap. cosphi = over excited
        cosphi_dir_cons = CosphiDir.UE if load.pf_recap == 0 else CosphiDir.OE
        # in PF for producer: ind. cosphi = over excited; cap. cosphi = under excited
        cosphi_dir_prod = CosphiDir.OE if load.pfg_recap == 0 else CosphiDir.UE
        if load_type == "PC":
            power_consumer = LoadPower.from_pc_sym(
                pow_act=load.plini,
                cosphi=load.coslini,
                cosphi_dir=cosphi_dir_cons,
                scaling=scaling_cons,
            )
            power_producer = LoadPower.from_pc_sym(
                pow_act=load.plini,
                cosphi=load.cosgini,
                cosphi_dir=cosphi_dir_prod,
                scaling=scaling_prod,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        if load_type == "SC":
            power_consumer = LoadPower.from_sc_sym(
                pow_app=load.slini,
                cosphi=load.coslini,
                cosphi_dir=cosphi_dir_cons,
                scaling=scaling_cons,
            )
            power_producer = LoadPower.from_sc_sym(
                pow_app=load.sgini,
                cosphi=load.cosgini,
                cosphi_dir=cosphi_dir_prod,
                scaling=scaling_prod,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        if load_type == "EC":
            logger.warning("Power from yearly demand is not implemented yet. Skipping.")
            power_consumer = LoadPower.from_pc_sym(
                pow_act=load.cplinia,
                cosphi=load.coslini,
                cosphi_dir=cosphi_dir_cons,
                scaling=scaling_cons,
            )
            power_producer = LoadPower.from_pc_sym(
                pow_act=load.pgini,
                cosphi=load.cosgini,
                cosphi_dir=cosphi_dir_prod,
                scaling=scaling_prod,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        msg = "unreachable"
        raise RuntimeError(msg)

    def calc_load_mv_power_asym(self, load: PFTypes.LoadMV) -> LoadMV:
        load_type = load.mode_inp
        scaling_cons = load.scale0
        scaling_prod = load.gscale * -1  # to be in line with demand based counting system
        # in PF for consumer: ind. cosphi = under excited; cap. cosphi = over excited
        cosphi_dir_cons = CosphiDir.UE if load.pf_recap == 0 else CosphiDir.OE
        # in PF for producer: ind. cosphi = over excited; cap. cosphi = under excited
        cosphi_dir_prod = CosphiDir.OE if load.pfg_recap == 0 else CosphiDir.UE
        if load_type == "PC":
            power_consumer = LoadPower.from_pc_asym(
                pow_act_a=load.plinir,
                pow_act_b=load.plinis,
                pow_act_c=load.plinit,
                cosphi_a=load.coslinir,
                cosphi_b=load.coslinis,
                cosphi_c=load.coslinit,
                cosphi_dir=cosphi_dir_cons,
                scaling=scaling_cons,
            )
            power_producer = LoadPower.from_pc_asym(
                pow_act_a=load.pginir,
                pow_act_b=load.pginis,
                pow_act_c=load.pginit,
                cosphi_a=load.cosginir,
                cosphi_b=load.cosginis,
                cosphi_c=load.cosginit,
                cosphi_dir=cosphi_dir_prod,
                scaling=scaling_prod,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        if load_type == "SC":
            power_consumer = LoadPower.from_sc_asym(
                pow_app_a=load.slinir,
                pow_app_b=load.slinis,
                pow_app_c=load.slinit,
                cosphi_a=load.coslinir,
                cosphi_b=load.coslinis,
                cosphi_c=load.coslinit,
                cosphi_dir=cosphi_dir_cons,
                scaling=scaling_cons,
            )
            power_producer = LoadPower.from_sc_asym(
                pow_app_a=load.sginir,
                pow_app_b=load.sginis,
                pow_app_c=load.sginit,
                cosphi_a=load.cosginir,
                cosphi_b=load.cosginis,
                cosphi_c=load.cosginit,
                cosphi_dir=cosphi_dir_prod,
                scaling=scaling_prod,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        msg = "unreachable"
        raise RuntimeError(msg)

    def create_consumer_ssc(
        self,
        load: PFTypes.LoadBase,
        power: LoadPower,
        grid_name: str,
        name_suffix: str = "",
    ) -> LoadSSC | None:
        name = self.pfi.create_name(load, grid_name) + name_suffix
        logger.debug("Creating consumer {consumer_name} steadystate case...", consumer_name=name)
        export, _ = self.get_description(load)
        if not export:
            logger.warning("External grid {consumer_ssc_name} not set for export. Skipping.", consumer_ssc_name=name)
            return None

        active_power = power.as_active_power_ssc()
        reactive_power = power.as_reactive_power_ssc()

        return LoadSSC(
            name=name,
            active_power=active_power,
            reactive_power=reactive_power,
        )

    def create_producers_ssc(
        self,
        loads: Sequence[PFTypes.GeneratorBase],
        grid_name: str,
    ) -> Sequence[LoadSSC]:
        logger.info("Creating producers steadystate case...")
        producers_ssc = [self.create_producer_ssc(generator=load, grid_name=grid_name) for load in loads]
        return self.pfi.filter_none(producers_ssc)

    def create_producer_ssc(
        self,
        generator: PFTypes.GeneratorBase,
        grid_name: str,
    ) -> LoadSSC | None:
        gen_name = self.pfi.create_generator_name(generator)
        producer_name = self.pfi.create_name(generator, grid_name, element_name=gen_name)
        logger.debug("Creating producer {producer_name} steadystate case...", producer_name=producer_name)
        export, _ = self.get_description(generator)
        if not export:
            logger.warning("Generator {producer_name} not set for export. Skipping.", producer_name=producer_name)
            return None

        bus = generator.bus1
        if bus is None:
            logger.warning("Generator {producer_name} not connected to any bus. Skipping.", producer_name=producer_name)
            return None

        terminal = bus.cterm
        u_n = round(terminal.uknom * Exponents.VOLTAGE, DecimalDigits.VOLTAGE)  # voltage in V

        power = LoadPower.from_pq_sym(
            pow_act=generator.pgini_a * generator.ngnum * -1,  # has to be negative as power is counted demand based
            pow_react=generator.qgini_a * generator.ngnum * -1,  # has to be negative as power is counted demand based
            scaling=generator.scale0_a,
        )

        active_power = power.as_active_power_ssc()

        # Q-Controller
        external_controller = generator.c_pstac
        if external_controller is None:
            controller = self.create_q_controller_builtin(gen=generator, u_n=u_n)
        else:
            controller = self.create_q_controller_external(
                gen=generator,
                u_n=u_n,
                controller=external_controller,
                grid_name=grid_name,
            )

        reactive_power = power.as_reactive_power_ssc(controller=controller)

        return LoadSSC(
            name=producer_name,
            active_power=active_power,
            reactive_power=reactive_power,
        )

    def create_q_controller_builtin(  # noqa: PLR0911
        self,
        gen: PFTypes.GeneratorBase,
        u_n: float,
    ) -> Controller | None:
        logger.debug("Creating producer {gen_name} internal Q controller...", gen_name=gen.loc_name)
        if gen.bus1 is not None:
            node_target = self.pfi.create_name(gen.bus1.cterm, self.grid_name)
        else:
            return None

        av_mode = LocalQCtrlMode(gen.av_mode)

        if av_mode == LocalQCtrlMode.COSPHI_CONST:
            cosphi = gen.cosgini
            cosphi_dir = CosphiDir.UE if gen.pf_recap == 1 else CosphiDir.UE
            q_controller: ControlType = ControlCosphiConst(
                node_target=node_target,
                cosphi=round(cosphi, DecimalDigits.COSPHI),
                cosphi_dir=cosphi_dir,
            )
            return Controller(control_type=q_controller)

        if av_mode == LocalQCtrlMode.Q_CONST:
            q_set = gen.qgini * -1  # has to be negative as power is now counted demand based
            q_controller = ControlQConst(
                node_target=node_target,
                q_set=round(q_set * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
            )
            return Controller(control_type=q_controller)

        if av_mode == LocalQCtrlMode.Q_U:
            cosphi_a = gen.cosn
            q_max_ue = abs(gen.Qfu_min)  # absolute value
            q_max_oe = abs(gen.Qfu_max)  # absolute value
            u_q0 = gen.udeadbup - (gen.udeadbup - gen.udeadblow) / 2  # p.u.
            u_deadband_low = abs(u_q0 - gen.udeadblow)  # delta in p.u.
            u_deadband_up = abs(u_q0 - gen.udeadbup)  # delta in p.u.
            m_tg_2015 = 100 / abs(gen.ddroop) * 100 / u_n / cosphi_a * Exponents.VOLTAGE  # (% von Pr) / kV
            m_tg_2018 = self.transform_qu_slope(slope=m_tg_2015, given_format="2015", target_format="2018", u_n=u_n)
            q_controller = ControlQU(
                node_target=node_target,
                m_tg_2015=round(m_tg_2015, DecimalDigits.PU),
                m_tg_2018=round(m_tg_2018, DecimalDigits.PU),
                u_q0=round(u_q0 * u_n, DecimalDigits.VOLTAGE),
                u_deadband_up=round(u_deadband_up * u_n, DecimalDigits.VOLTAGE),
                u_deadband_low=round(u_deadband_low * u_n, DecimalDigits.VOLTAGE),
                q_max_ue=round(q_max_ue * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
                q_max_oe=round(q_max_oe * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
            )
            q_controller.control_strategy
            return Controller(control_type=q_controller)

        if av_mode == LocalQCtrlMode.Q_P:
            if gen.pQPcurve is None:
                return None

            q_controller = ControlQP(node_target=node_target, q_p_characteristic_name=gen.pQPcurve.loc_name)
            return Controller(control_type=q_controller)

        if av_mode == LocalQCtrlMode.COSPHI_P:
            cosphi_ue = gen.pf_under
            cosphi_oe = gen.pf_over
            p_threshold_ue = gen.p_under * -1  # P-threshold for cosphi_ue
            p_threshold_oe = gen.p_over * -1  # P-threshold for cosphi_oe
            q_controller = ControlCosphiP(
                node_target=node_target,
                cosphi_ue=round(cosphi_ue, DecimalDigits.COSPHI),
                cosphi_oe=round(cosphi_oe, DecimalDigits.COSPHI),
                p_threshold_ue=round(p_threshold_ue * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
                p_threshold_oe=round(p_threshold_oe * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
            )
            return Controller(control_type=q_controller)

        if av_mode == LocalQCtrlMode.U_CONST:
            u_set = gen.usetp
            q_controller = ControlUConst(node_target=node_target, u_set=round(u_set * u_n, DecimalDigits.VOLTAGE))
            return Controller(control_type=q_controller)

        if av_mode == LocalQCtrlMode.U_Q_DROOP:
            logger.warning(
                "Generator {gen_name}: Voltage control with Q-droop is not implemented yet. Skipping.",
                gen_name=gen.loc_name,
            )
            return None

        if av_mode == LocalQCtrlMode.U_I_DROOP:
            logger.warning(
                "Generator {gen_name}: Voltage control with I-droop is not implemented yet. Skipping.",
                gen_name=gen.loc_name,
            )
            return None

        msg = "unreachable"
        raise RuntimeError(msg)

    def create_q_controller_external(  # noqa: PLR0911, PLR0912, PLR0915
        self,
        gen: PFTypes.GeneratorBase,
        u_n: float,
        controller: PFTypes.StationController,
        grid_name: str,
    ) -> Controller | None:
        controller_name = self.pfi.create_generator_name(gen, generator_name=controller.loc_name)
        logger.debug(
            "Creating producer {gen_name} external Q controller {controller_name}...",
            gen_name=gen.loc_name,
            controller_name=controller_name,
        )

        # Controlled node
        node_target_cub = controller.p_cub
        if node_target_cub is None:
            logger.warning(
                "Generator {gen_name}: external controller has no target node. Skipping.",
                gen_name=gen.loc_name,
            )
            return None
        node_target_name = self.pfi.create_name(element=node_target_cub.cterm, grid_name=grid_name)

        ctrl_mode = controller.i_ctrl
        if ctrl_mode == CtrlMode.U:  # voltage control mode -> const. U
            u_set = controller.usetp
            u_meas_ref = ControlledVoltageRef[CtrlVoltageRef(controller.i_phase).name]
            q_controller: ControlType = ControlUConst(
                u_set=round(u_set * u_n, DecimalDigits.VOLTAGE),
                u_meas_ref=u_meas_ref,
                node_target=node_target_name,
            )
            return Controller(control_type=q_controller, external_controller_name=controller_name)

        if ctrl_mode == CtrlMode.Q:  # reactive power control mode
            if controller.qu_char == QChar.CONST:  # const. Q
                q_dir = -1 if controller.iQorient else 1
                q_set = controller.qsetp * q_dir * -1  # has to be negative as power is now counted demand based
                q_controller = ControlQConst(
                    q_set=round(q_set * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
                    node_target=node_target_name,
                )
                return Controller(control_type=q_controller, external_controller_name=controller_name)

            if controller.qu_char == QChar.U:  # Q(U)
                s_r = gen.sgn
                cosphi_a = gen.cosn
                u_nom = round(controller.refbar.uknom * Exponents.VOLTAGE, DecimalDigits.VOLTAGE)  # voltage in V

                q_max_ue = abs(controller.Qmin)
                q_max_oe = abs(controller.Qmax)
                u_q0 = controller.udeadbup - (controller.udeadbup - controller.udeadblow) / 2  # per unit
                u_deadband_low = abs(u_q0 - controller.udeadblow)  # delta in per unit
                u_deadband_up = abs(u_q0 - controller.udeadbup)  # delta in per unit

                q_rated = controller.Srated
                try:
                    if abs((abs(q_rated) - abs(s_r)) / abs(s_r)) < M_TAB2015_MIN_THRESHOLD:  # q_rated == s_r
                        m_tg_2015 = 100 / controller.ddroop * 100 / u_nom / cosphi_a * Exponents.VOLTAGE
                    else:
                        m_tg_2015 = (
                            100
                            / abs(controller.ddroop)
                            * 100
                            / u_nom
                            * math.tan(math.acos(cosphi_a))
                            * Exponents.VOLTAGE
                        )

                    # in default there should q_rated=s_r, but user could enter incorrectly
                    m_tg_2015 = m_tg_2015 * q_rated / s_r
                    m_tg_2018 = self.transform_qu_slope(
                        slope=m_tg_2015,
                        given_format="2015",
                        target_format="2018",
                        u_n=u_nom,
                    )
                except ZeroDivisionError:
                    m_tg_2015 = float("inf")
                    m_tg_2018 = float("inf")

                q_controller = ControlQU(
                    m_tg_2015=round(m_tg_2015, DecimalDigits.PU),
                    m_tg_2018=round(m_tg_2018, DecimalDigits.PU),
                    u_q0=round(u_q0 * u_n, DecimalDigits.VOLTAGE),
                    u_deadband_up=round(u_deadband_up * u_n, DecimalDigits.VOLTAGE),
                    u_deadband_low=round(u_deadband_low * u_n, DecimalDigits.VOLTAGE),
                    q_max_ue=round(q_max_ue * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
                    q_max_oe=round(q_max_oe * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
                    node_target=node_target_name,
                )
                return Controller(control_type=q_controller, external_controller_name=controller_name)

            if controller.qu_char == QChar.P:  # Q(P)
                q_p_char_name = controller.pQPcurve.loc_name
                q_max_ue = abs(controller.Qmin)
                q_max_oe = abs(controller.Qmax)
                q_dir = q_dir = -1 if controller.iQorient else 1
                q_controller = ControlQP(
                    q_p_characteristic_name=q_p_char_name,
                    q_max_ue=round(q_max_ue * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
                    q_max_oe=round(q_max_oe * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
                    node_target=node_target_name,
                )
                return Controller(control_type=q_controller, external_controller_name=controller_name)

            msg = "unreachable"
            raise RuntimeError(msg)

        if ctrl_mode == CtrlMode.COSPHI:  # cosphi control mode
            if controller.cosphi_char == CosphiChar.CONST:  # const. cosphi
                cosphi = controller.pfsetp
                ue = controller.pf_recap ^ controller.iQorient  # OE/UE XOR +Q/-Q
                # in PF for producer: ind. cosphi = over excited; cap. cosphi = under excited
                q_dir = q_dir = -1 if controller.iQorient else 1
                cosphi_dir = CosphiDir.UE if ue else CosphiDir.OE
                q_controller = ControlCosphiConst(
                    cosphi=round(cosphi, DecimalDigits.COSPHI),
                    cosphi_dir=cosphi_dir,
                    node_target=node_target_name,
                )
                return Controller(control_type=q_controller, external_controller_name=controller_name)

            if controller.cosphi_char == CosphiChar.P:  # cosphi(P)
                cosphi_ue = controller.pf_under
                cosphi_oe = controller.pf_over
                p_threshold_ue = controller.p_under * -1  # P-threshold for cosphi_ue
                p_threshold_oe = controller.p_over * -1  # P-threshold for cosphi_oe
                q_controller = ControlCosphiP(
                    cosphi_ue=round(cosphi_ue, DecimalDigits.COSPHI),
                    cosphi_oe=round(cosphi_oe, DecimalDigits.COSPHI),
                    p_threshold_ue=round(p_threshold_ue * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
                    p_threshold_oe=round(p_threshold_oe * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
                    node_target=node_target_name,
                )
                return Controller(control_type=q_controller, external_controller_name=controller_name)

            if controller.cosphi_char == CosphiChar.U:  # cosphi(U)
                cosphi_ue = controller.pf_under
                cosphi_oe = controller.pf_over
                u_threshold_ue = controller.u_under  # U-threshold for cosphi_ue
                u_threshold_oe = controller.u_over  # U-threshold for cosphi_oe
                q_controller = ControlCosphiU(
                    cosphi_ue=round(cosphi_ue, DecimalDigits.COSPHI),
                    cosphi_oe=round(cosphi_oe, DecimalDigits.COSPHI),
                    u_threshold_ue=round(u_threshold_ue * u_n, DecimalDigits.VOLTAGE),
                    u_threshold_oe=round(u_threshold_oe * u_n, DecimalDigits.VOLTAGE),
                    node_target=node_target_name,
                )
                return Controller(control_type=q_controller, external_controller_name=controller_name)

            msg = "unreachable"
            raise RuntimeError(msg)

        if ctrl_mode == CtrlMode.TANPHI:  # tanphi control mode --> const. tanphi
            cosphi = math.cos(math.atan(controller.tansetp))
            cosphi_dir = CosphiDir.UE if controller.iQorient else CosphiDir.OE
            q_controller = ControlTanphiConst(
                cosphi=round(cosphi, DecimalDigits.COSPHI),
                cosphi_dir=cosphi_dir,
                node_target=node_target_name,
            )
            return Controller(control_type=q_controller, external_controller_name=controller_name)

        msg = "unreachable"
        raise RuntimeError(msg)

    @staticmethod
    def transform_qu_slope(
        slope: float,
        given_format: Literal["2015", "2018"],
        target_format: Literal["2015", "2018"],
        u_n: float,
    ) -> float:
        """Transform slope of Q(U)-characteristic from given format type to another format type.

        Arguments:
            value {float} -- slope of Q(U)-characteristic
            given_format {str} -- format specifier for related normative guideline (e.g. '2015' or '2018')
            target_format {str} -- format specifier for related normative guideline (e.g. '2015' or '2018')
            u_n {float} -- nominal voltage of the related controller, in V

        Returns:
            float -- transformed slope
        """
        if given_format == "2015" and target_format == "2018":
            return slope / (1e3 / u_n * 100)  # 2018: (% von Pr) / (p.u. von Un)

        if given_format == "2018" and target_format == "2015":
            return slope * (1e3 / u_n * 100)  # 2015: (% von Pr) / kV

        msg = "unreachable"
        raise RuntimeError(msg)


def export_powerfactory_data(  # noqa: PLR0913
    export_path: pathlib.Path,
    project_name: str,
    grid_name: str,
    powerfactory_user_profile: str = "",
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH,
    powerfactory_version: str = POWERFACTORY_VERSION,
    python_version: str = PYTHON_VERSION,
    topology_name: str | None = None,
    topology_case_name: str | None = None,
    steadystate_case_name: str | None = None,
) -> None:
    """Export powerfactory data to json files using PowerFactoryExporter running in process.

    A grid given in DIgSILENT PowerFactory is exported to three json files with given schema.
    The whole grid data is separated into topology (raw assets), topology_case (binary switching info and out of service
    info) and steadystate_case (operation points).
    When the code execution is complete, the process is terminated and the connection to PowerFactory is closed.

        Arguments:
            export_path {pathlib.Path} -- the directory where the exported json files are saved
            project_name {str} -- project name in PowerFactory to which the grid belongs
            grid_name {str} -- name of the grid to exported
            powerfactory_user_profile {str} -- user profile for login in PowerFactory
            powerfactory_path {pathlib.Path} -- installation directory of PowerFactory (hard-coded in interface.py)
            powerfactory_version {str} -- version number of PowerFactory (hard-coded in interface.py)
            topology_name {str} -- the chosen file name for 'topology' data
            topology_case_name {str} -- the chosen file name for related 'topology_case' data
            steadystate_case_name {str} -- the chosen file name for related 'steadystate_case' data

        Returns:
            None
    """

    process = PowerFactoryExporterProcess(
        project_name=project_name,
        export_path=export_path,
        grid_name=grid_name,
        powerfactory_user_profile=powerfactory_user_profile,
        powerfactory_path=powerfactory_path,
        powerfactory_version=powerfactory_version,
        python_version=python_version,
        topology_name=topology_name,
        topology_case_name=topology_case_name,
        steadystate_case_name=steadystate_case_name,
    )
    process.start()
    process.join()
