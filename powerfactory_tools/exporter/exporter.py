# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import datetime
import itertools
import math
import multiprocessing
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from powerfactory_tools.constants import DecimalDigits
from powerfactory_tools.constants import Exponents
from powerfactory_tools.exporter.load_power import LoadPower
from powerfactory_tools.interface import PowerfactoryInterface
from powerfactory_tools.powerfactory_types import CosphiChar
from powerfactory_tools.powerfactory_types import CtrlMode
from powerfactory_tools.powerfactory_types import IOpt
from powerfactory_tools.powerfactory_types import PowReactChar
from powerfactory_tools.schema.base import Meta
from powerfactory_tools.schema.base import VoltageSystemType
from powerfactory_tools.schema.steadystate_case.case import Case as SteadystateCase
from powerfactory_tools.schema.steadystate_case.controller import Controller
from powerfactory_tools.schema.steadystate_case.controller import ControllerType
from powerfactory_tools.schema.steadystate_case.controller import CosphiDir
from powerfactory_tools.schema.steadystate_case.external_grid import ExternalGrid as ExternalGridSSC
from powerfactory_tools.schema.steadystate_case.load import Load as LoadSSC
from powerfactory_tools.schema.steadystate_case.transformer import Transformer as TransformerSSC
from powerfactory_tools.schema.topology.active_power import ActivePower
from powerfactory_tools.schema.topology.branch import Branch
from powerfactory_tools.schema.topology.branch import BranchType
from powerfactory_tools.schema.topology.external_grid import ExternalGrid
from powerfactory_tools.schema.topology.external_grid import GridType
from powerfactory_tools.schema.topology.load import ConsumerPhaseConnectionType
from powerfactory_tools.schema.topology.load import ConsumerSystemType
from powerfactory_tools.schema.topology.load import Load
from powerfactory_tools.schema.topology.load import LoadType
from powerfactory_tools.schema.topology.load import ProducerPhaseConnectionType
from powerfactory_tools.schema.topology.load import ProducerSystemType
from powerfactory_tools.schema.topology.load_model import LoadModel
from powerfactory_tools.schema.topology.node import Node
from powerfactory_tools.schema.topology.reactive_power import ReactivePower
from powerfactory_tools.schema.topology.topology import Topology
from powerfactory_tools.schema.topology.transformer import TapSide
from powerfactory_tools.schema.topology.transformer import Transformer
from powerfactory_tools.schema.topology.transformer import TransformerPhaseTechnologyType
from powerfactory_tools.schema.topology.windings import Winding
from powerfactory_tools.schema.topology_case.case import Case as TopologyCase
from powerfactory_tools.schema.topology_case.element_state import ElementState

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import TracebackType
    from typing import Literal

    from powerfactory_tools.powerfactory_types import PowerFactoryTypes as PFTypes

    ElementBase = PFTypes.GeneratorBase | PFTypes.LoadBase | PFTypes.ExternalGrid


POWERFACTORY_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
POWERFACTORY_VERSION = "2022 SP2"

FULL_DYNAMIC = 100
M_TAB2015_MIN_THRESHOLD = 0.01


@dataclass
class LoadLV:
    fixed: LoadPower
    night: LoadPower
    flexible: LoadPower


@dataclass
class LoadMV:
    consumer: LoadPower
    producer: LoadPower


@dataclass
class PowerfactoryData:
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


class PowerfactoryExporterProcess(multiprocessing.Process):
    def __init__(
        self,
        *,
        export_path: pathlib.Path,
        project_name: str,
        grid_name: str,
        powerfactory_user_profile: str = "",
        powerfactory_path: pathlib.Path = POWERFACTORY_PATH,
        powerfactory_version: str = POWERFACTORY_VERSION,
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
        pfe = PowerfactoryExporter(
            project_name=self.project_name,
            grid_name=self.grid_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_path=self.powerfactory_path,
            powerfactory_version=self.powerfactory_version,
        )
        pfe.export(self.export_path, self.topology_name, self.topology_case_name, self.steadystate_case_name)


@dataclass
class PowerfactoryExporter:
    project_name: str
    grid_name: str
    powerfactory_user_profile: str = ""
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH
    powerfactory_version: str = POWERFACTORY_VERSION

    def __post_init__(self) -> None:
        self.pfi = PowerfactoryInterface(
            project_name=self.project_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_path=self.powerfactory_path,
            powerfactory_version=self.powerfactory_version,
        )

    def __enter__(self) -> PowerfactoryExporter:
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

    def compile_powerfactory_data(self) -> PowerfactoryData:
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

        return PowerfactoryData(
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
    def create_meta_data(data: PowerfactoryData) -> Meta:
        grid_name = data.name.replace(" ", "-")
        project = data.project.replace(" ", "-")
        date = data.date

        return Meta(name=grid_name, date=date, project=project)

    def create_topology(self, meta: Meta, data: PowerfactoryData) -> Topology:
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

    def create_external_grids(self, ext_grids: Sequence[PFTypes.ExternalGrid], grid_name: str) -> set[ExternalGrid]:
        grids: set[ExternalGrid] = set()
        for grid in ext_grids:
            name = self.pfi.create_name(grid, grid_name)
            export, description = self.get_description(grid)
            if not export:
                logger.warning(
                    "External grid {ext_grid_name} not set for export. Skipping.",
                    ext_grid_name=name,
                )
                continue

            if grid.bus1 is None:
                logger.warning(
                    "External grid {ext_grid_name} not connected to any bus. Skipping.",
                    ext_grid_name=name,
                )
                continue

            node_name = self.pfi.create_name(grid.bus1.cterm, grid_name)

            ext_grid = ExternalGrid(
                name=name,
                description=description,
                node=node_name,
                type=GridType(grid.bustp),
                short_circuit_power_max=grid.snss,
                short_circuit_power_min=grid.snssmin,
            )
            logger.debug(
                "Created external grid {ext_grid}.",
                ext_grid=ext_grid,
            )
            grids.add(ext_grid)

        return grids

    def create_nodes(self, terminals: Sequence[PFTypes.Terminal], grid_name: str) -> Sequence[Node]:
        nodes = [self.create_node(terminal, grid_name) for terminal in terminals]
        return [e for e in nodes if e is not None]

    def create_node(self, terminal: PFTypes.Terminal, grid_name: str) -> Node | None:
        export, description = self.get_description(terminal)
        name = self.pfi.create_name(terminal, grid_name)
        if not export:
            logger.warning(
                "Node {node_name} not set for export. Skipping.",
                node_name=name,
            )
            return None

        u_n = round(terminal.uknom, DecimalDigits.VOLTAGE) * Exponents.VOLTAGE  # voltage in V

        if self.pfi.is_within_substation(terminal):
            description = "substation internal" if description == "" else "substation internal; " + description

        node = Node(name=name, u_n=u_n, description=description)
        logger.debug(
            "Created node {node}.",
            node=node,
        )
        return node

    def create_branches(
        self,
        lines: Sequence[PFTypes.Line],
        couplers: Sequence[PFTypes.Coupler],
        grid_name: str,
    ) -> Sequence[Branch]:
        blines = [self.create_line(line, grid_name) for line in lines]
        bcouplers = [self.create_coupler(coupler, grid_name) for coupler in couplers]

        return [e for sublist in [blines, bcouplers] for e in sublist if e is not None]

    def create_line(self, line: PFTypes.Line, grid_name: str) -> Branch | None:
        name = self.pfi.create_name(line, grid_name)
        export, description = self.get_description(line)
        if not export:
            logger.warning(
                "Line {line_name} not set for export. Skipping.",
                line_name=name,
            )
            return None

        if line.bus1 is None or line.bus2 is None:
            logger.warning(
                "Line {line_name} not connected to buses on both sides. Skipping.",
                line_name=name,
            )
            return None

        t1 = line.bus1.cterm
        t2 = line.bus2.cterm

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

        u_system_type = VoltageSystemType.DC if l_type.systp else VoltageSystemType.AC  # AC or DC

        branch = Branch(
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
        logger.debug("Created line {branch}.", branch=branch)
        return branch

    @staticmethod
    def determine_line_voltage(u_nom_1: float, u_nom_2: float, l_type: PFTypes.LineType) -> float:
        if round(u_nom_1, 2) == round(u_nom_2, 2):
            return u_nom_1 * Exponents.VOLTAGE  # nominal voltage (V)

        return l_type.uline * Exponents.VOLTAGE  # nominal voltage (V)

    def create_coupler(self, coupler: PFTypes.Coupler, grid_name: str) -> Branch | None:
        name = self.pfi.create_name(coupler, grid_name)
        export, description = self.get_description(coupler)
        if not export:
            logger.warning(
                "Coupler {coupler_name} not set for export. Skipping.",
                coupler_name=name,
            )
            return None

        if coupler.bus1 is None or coupler.bus2 is None:
            logger.warning(
                "Coupler {coupler} not connected to buses on both sides. Skipping.",
                coupler=coupler,
            )
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

        t1 = coupler.bus1.cterm
        t2 = coupler.bus2.cterm

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

        branch = Branch(
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
        )
        logger.debug(
            "Created coupler {branch}.",
            branch=branch,
        )
        return branch

    def get_coupler_description(
        self,
        terminal1: PFTypes.Terminal,
        terminal2: PFTypes.Terminal,
        description: str,
    ) -> str:
        if self.pfi.is_within_substation(terminal1) and self.pfi.is_within_substation(terminal2):
            if description == "":
                return "substation internal"

            return "substation internal; " + description

        return description

    def create_loads(  # noqa: PLR0913 # fix
        self,
        consumers: Sequence[PFTypes.Load],
        consumers_lv: Sequence[PFTypes.LoadLV],
        consumers_mv: Sequence[PFTypes.LoadMV],
        generators: Sequence[PFTypes.Generator],
        pv_systems: Sequence[PFTypes.PVSystem],
        grid_name: str,
    ) -> Sequence[Load]:
        normal_consumers = self.create_consumers_normal(consumers, grid_name)
        lv_consumers = self.create_consumers_lv(consumers_lv, grid_name)
        load_mvs = self.create_loads_mv(consumers_mv, grid_name)
        gen_producers = self.create_producers_normal(generators, grid_name)
        pv_producers = self.create_producers_pv(pv_systems, grid_name)
        return self.pfi.list_from_sequences(normal_consumers, lv_consumers, load_mvs, gen_producers, pv_producers)

    def create_consumers_normal(self, loads: Sequence[PFTypes.Load], grid_name: str) -> set[Load]:
        consumers: set[Load] = set()
        for load in loads:
            power = self.calc_normal_load_power(load)
            if power is not None:
                consumer = self.create_consumer(load, power, grid_name)
                if consumer is not None:
                    consumers.add(consumer)

        return consumers

    def create_consumers_lv(self, loads: Sequence[PFTypes.LoadLV], grid_name: str) -> set[Load]:
        consumers_lv_parts = [self.create_consumers_lv_parts(load, grid_name) for load in loads]
        return self.pfi.set_from_sequences(*consumers_lv_parts)

    def create_consumers_lv_parts(self, load: PFTypes.LoadLV, grid_name: str) -> set[Load]:
        powers = self.calc_load_lv_powers(load)
        sfx_pre = "" if len(powers) == 1 else "_({})"

        consumer_lv_parts = [
            self.create_consumer_lv_parts(load=load, grid_name=grid_name, power=power, sfx_pre=sfx_pre, index=i)
            for i, power in enumerate(powers)
        ]
        return self.pfi.set_from_sequences(*consumer_lv_parts)

    def create_consumer_lv_parts(  # noqa: PLR0913 # fix
        self,
        load: PFTypes.LoadLV,
        grid_name: str,
        power: LoadLV,
        sfx_pre: str,
        index: int,
    ) -> Sequence[Load]:
        consumer_fixed = (
            self.create_consumer(
                load,
                power.fixed,
                grid_name,
                system_type=ConsumerSystemType.FIXED,
                name_suffix=sfx_pre.format(index) + "_" + ConsumerSystemType.FIXED.value,
            )
            if power.fixed.pow_app_abs != 0
            else None
        )
        consumer_night = (
            self.create_consumer(
                load,
                power.night,
                grid_name,
                system_type=ConsumerSystemType.NIGHT_STORAGE,
                name_suffix=sfx_pre.format(index) + "_" + ConsumerSystemType.NIGHT_STORAGE.value,
            )
            if power.night.pow_app_abs != 0
            else None
        )
        consumer_flex = (
            self.create_consumer(
                load,
                power.flexible,
                grid_name,
                system_type=ConsumerSystemType.VARIABLE,
                name_suffix=sfx_pre.format(index) + "_" + ConsumerSystemType.VARIABLE.value,
            )
            if power.flexible.pow_app_abs != 0
            else None
        )
        return [e for e in [consumer_fixed, consumer_night, consumer_flex] if e is not None]

    def create_loads_mv(self, loads: Sequence[PFTypes.LoadMV], grid_name: str) -> set[Load]:
        _loads: set[Load] = set()
        for load in loads:
            power = self.calc_load_mv_power(load)
            consumer = self.create_consumer(
                load=load,
                power=power.consumer,
                grid_name=grid_name,
                name_suffix="_CONSUMER",
            )
            if consumer is not None:
                _loads.add(consumer)

            producer = self.create_producer(
                gen=load,
                power=power.producer,
                gen_name=load.loc_name,
                grid_name=grid_name,
                name_suffix="_PRODUCER",
            )
            if producer is not None:
                _loads.add(producer)

        return _loads

    def create_consumer(  # noqa: PLR0913 # fix
        self,
        load: PFTypes.LoadBase,
        power: LoadPower,
        grid_name: str,
        system_type: ConsumerSystemType | None = None,
        name_suffix: str = "",
    ) -> Load | None:
        export, description = self.get_description(load)
        if not export:
            logger.warning(
                "Load {load_name} not set for export. Skipping.",
                load_name=load.loc_name,
            )
            return None

        bus = load.bus1
        if bus is None:
            logger.debug(
                "Load {load_name} not connected to any bus. Skipping.",
                load_name=load.loc_name,
            )
            return None

        terminal = bus.cterm
        l_name = self.pfi.create_name(load, grid_name) + name_suffix
        t_name = self.pfi.create_name(terminal, grid_name)

        u_n = round(terminal.uknom, DecimalDigits.VOLTAGE) * Exponents.VOLTAGE  # voltage in V

        rated_power = power.as_rated_power()
        logger.debug(
            " {load_name}: there is no real rated, but 's' is calculated on basis of actual power.",
            load_name=load.loc_name,
        )

        load_model_p = self.load_model_of(load, specifier="p")
        active_power = ActivePower(load_model=load_model_p)

        load_model_q = self.load_model_of(load, specifier="q")
        reactive_power = ReactivePower(load_model=load_model_q)

        u_system_type, ph_con = self.consumer_technology_of(load)

        consumer = Load(
            name=l_name,
            node=t_name,
            description=description,
            u_n=u_n,
            rated_power=rated_power,
            active_power=active_power,
            reactive_power=reactive_power,
            type=LoadType.CONSUMER,
            system_type=system_type,
            voltage_system_type=u_system_type,
            phase_connection_type=ph_con,
        )
        logger.debug(
            "Created consumer {consumer}.",
            consumer=consumer,
        )
        return consumer

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

    @staticmethod
    def consumer_technology_of(
        load: PFTypes.LoadBase,
    ) -> tuple[VoltageSystemType | None, ConsumerPhaseConnectionType | None]:
        phase_con_dict = {
            0: ConsumerPhaseConnectionType.THREE_PH_D,
            2: ConsumerPhaseConnectionType.THREE_PH_PH_E,
            3: ConsumerPhaseConnectionType.THREE_PH_YN,
            4: ConsumerPhaseConnectionType.TWO_PH_PH_E,
            5: ConsumerPhaseConnectionType.TWO_PH_YN,
            7: ConsumerPhaseConnectionType.ONE_PH_PH_PH,
            8: ConsumerPhaseConnectionType.ONE_PH_PH_E,
            9: ConsumerPhaseConnectionType.ONE_PH_PH_N,
        }
        load_type = load.typ_id
        if load_type is not None:
            system_type = VoltageSystemType.DC if load_type.systp else VoltageSystemType.AC  # AC or DC
            phase_con = None
            try:
                phase_con = phase_con_dict[load_type.phtech]
            except KeyError:
                logger.warning(
                    "Wrong phase connection identifier {load_phtech!r} for consumer {consumer_name}. Skipping.",
                    load_phtech=load_type.phtech,
                    consumer_name=load.loc_name,
                )

            return system_type, phase_con

        logger.debug("No load model defined for load {load_name}. Skipping.", load_name=load.loc_name)

        return None, None

    def create_producers_normal(
        self,
        generators: Sequence[PFTypes.Generator],
        grid_name: str,
    ) -> set[Load]:
        producers: set[Load] = set()
        for gen in generators:
            producer_system_type = self.producer_system_type_of(gen)
            producer_phase_connection_type = self.producer_technology_of(gen)
            external_controller_name = self.get_external_controller_name(gen)
            power = self.calc_normal_gen_power(gen)
            gen_name = self.pfi.create_generator_name(gen)
            producer = self.create_producer(
                gen=gen,
                power=power,
                gen_name=gen_name,
                grid_name=grid_name,
                producer_system_type=producer_system_type,
                producer_phase_connection_type=producer_phase_connection_type,
                external_controller_name=external_controller_name,
            )
            if producer is not None:
                producers.add(producer)

        return producers

    @staticmethod
    def producer_system_type_of(load: PFTypes.Generator) -> ProducerSystemType | None:
        # dict of plant categories, consisting of english and german key words
        system_type_dict = {
            **dict.fromkeys(["Coal", "Kohle"], ProducerSystemType.COAL),
            **dict.fromkeys(["Oil", "Öl"], ProducerSystemType.OIL),
            **dict.fromkeys(["Diesel", "Diesel"], ProducerSystemType.DIESEL),
            **dict.fromkeys(["Nuclear", "Nuklear"], ProducerSystemType.NUCLEAR),
            **dict.fromkeys(["Hydro", "Wasser"], ProducerSystemType.HYDRO),
            **dict.fromkeys(["Pump storage", "Pumpspeicher"], ProducerSystemType.PUMP_STORAGE),
            **dict.fromkeys(["Wind", "Wind"], ProducerSystemType.WIND),
            **dict.fromkeys(["Biogas", "Biogas"], ProducerSystemType.BIOGAS),
            **dict.fromkeys(["Solar", "Solar"], ProducerSystemType.SOLAR),
            **dict.fromkeys(["Others", "Sonstige"], ProducerSystemType.OTHERS),
            **dict.fromkeys(["Photovoltaic", "Fotovoltaik"], ProducerSystemType.PV),
            **dict.fromkeys(["Renewable Generation", "Erneuerbare Erzeugung"], ProducerSystemType.RENEWABLE_ENERGY),
            **dict.fromkeys(["Fuel Cell", "Brennstoffzelle"], ProducerSystemType.FUELCELL),
            **dict.fromkeys(["Peat", "Torf"], ProducerSystemType.PEAT),
            **dict.fromkeys(["Other Static Generator", "Statischer Generator"], ProducerSystemType.STAT_GEN),
            **dict.fromkeys(["HVDC Terminal", "HGÜ-Anschluss"], ProducerSystemType.HVDC),
            **dict.fromkeys(
                ["Reactive Power Compensation", "Blindleistungskompensation"],
                ProducerSystemType.REACTIVE_POWER_COMPENSATOR,
            ),
            **dict.fromkeys(["Storage", "Batterie"], ProducerSystemType.BATTERY_STORAGE),
            **dict.fromkeys(["External Grids", "Externe Netze"], ProducerSystemType.EXTERNAL_GRID_EQUIVALENT),
        }

        try:
            system_type = system_type_dict[load.cCategory]
        except KeyError:
            system_type = None
            logger.warning(
                "Wrong system type identifier {load_category!r} for producer {consumer_name}. Skipping.",
                load_category=load.cCategory,
                consumer_name=load.loc_name,
            )

        return system_type

    def create_producers_pv(
        self,
        generators: Sequence[PFTypes.PVSystem],
        grid_name: str,
    ) -> set[Load]:
        producers: set[Load] = set()
        for gen in generators:
            producer_system_type = ProducerSystemType.PV
            producer_phase_connection_type = self.producer_technology_of(gen)
            external_controller_name = self.get_external_controller_name(gen)
            power = self.calc_normal_gen_power(gen)
            gen_name = self.pfi.create_generator_name(gen)
            producer = self.create_producer(
                gen=gen,
                power=power,
                gen_name=gen_name,
                grid_name=grid_name,
                producer_system_type=producer_system_type,
                producer_phase_connection_type=producer_phase_connection_type,
                external_controller_name=external_controller_name,
            )
            if producer is not None:
                producers.add(producer)

        return producers

    @staticmethod
    def producer_technology_of(load: PFTypes.GeneratorBase) -> ProducerPhaseConnectionType | None:
        phase_con_dict = {
            0: ProducerPhaseConnectionType.THREE_PH,
            1: ProducerPhaseConnectionType.THREE_PH_E,
            2: ProducerPhaseConnectionType.ONE_PH_PH_E,
            3: ProducerPhaseConnectionType.ONE_PH_PH_N,
            4: ProducerPhaseConnectionType.ONE_PH_PH_PH,
        }
        phase_con = None
        try:
            phase_con = phase_con_dict[load.phtech]
        except KeyError:
            logger.warning(
                "Wrong phase connection identifier {load_phtech!r} for producer {producer_name}. Skipping.",
                load_phtech=load.phtech,
                producer_name=load.loc_name,
            )

        return phase_con

    def get_external_controller_name(self, gen: PFTypes.Generator | PFTypes.PVSystem) -> str | None:
        ext_ctrl = gen.c_pstac
        if ext_ctrl is None:
            return None

        return self.pfi.create_generator_name(gen, generator_name=ext_ctrl.loc_name)

    def calc_normal_gen_power(self, gen: PFTypes.Generator | PFTypes.PVSystem) -> LoadPower:
        pow_app = gen.sgn * gen.ngnum
        cosphi = gen.cosn
        return LoadPower.from_sc_sym(pow_app=pow_app, cosphi=cosphi, scaling=gen.scale0)

    def create_producer(  # noqa: PLR0913 # fix
        self,
        gen: PFTypes.GeneratorBase | PFTypes.LoadMV,
        gen_name: str,
        power: LoadPower,
        grid_name: str,
        producer_system_type: ProducerSystemType | None = None,
        producer_phase_connection_type: ProducerPhaseConnectionType | None = None,
        external_controller_name: str | None = None,
        name_suffix: str = "",
    ) -> Load | None:
        gen_name = self.pfi.create_name(gen, grid_name, element_name=gen_name) + name_suffix

        export, description = self.get_description(gen)
        if not export:
            logger.warning(
                "Generator {gen_name} not set for export. Skipping.",
                gen_name=gen_name,
            )
            return None

        bus = gen.bus1
        if bus is None:
            logger.warning("Generator {gen_name} not connected to any bus. Skipping.", gen_name=gen_name)
            return None

        terminal = bus.cterm
        t_name = self.pfi.create_name(terminal, grid_name)
        u_n = round(terminal.uknom, DecimalDigits.VOLTAGE) * Exponents.VOLTAGE

        # Rated Values of single unit
        rated_power = power.as_rated_power()
        reactive_power = ReactivePower(external_controller_name=external_controller_name)

        producer = Load(
            name=gen_name,
            node=t_name,
            description=description,
            u_n=u_n,
            rated_power=rated_power,
            active_power=ActivePower(),
            reactive_power=reactive_power,
            type=LoadType.PRODUCER,
            system_type=producer_system_type,
            phase_connection_type=producer_phase_connection_type,
        )
        logger.debug("Created producer {producer}.", producer=producer)
        return producer

    def create_topology_case(self, meta: Meta, data: PowerfactoryData) -> TopologyCase:
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
        power_on_states = self.pfi.set_from_sequences(
            switch_states,
            coupler_states,
            node_power_on_states,
            line_power_on_states,
            transformer_2w_power_on_states,
            element_power_on_states,
        )
        power_on_states = self.merge_power_on_states(power_on_states)

        return TopologyCase(meta=meta, elements=power_on_states)

    def merge_power_on_states(self, power_on_states: set[ElementState]) -> set[ElementState]:
        merged_states: set[ElementState] = set()
        entry_names = [entry.name for entry in power_on_states]
        for entry_name in entry_names:
            entries = {entry for entry in power_on_states if entry.name == entry_name}
            merged_states.add(self.merge_entries(entry_name, entries))

        return set(merged_states)

    def merge_entries(self, entry_name: str, entries: set[ElementState]) -> ElementState:
        disabled = any(entry.disabled for entry in entries)
        open_switches = tuple(itertools.chain.from_iterable([entry.open_switches for entry in entries]))
        return ElementState(name=entry_name, disabled=disabled, open_switches=open_switches)

    def create_switch_states(self, switches: Sequence[PFTypes.Switch]) -> set[ElementState]:
        """Create element states for all type of elements based on if the switch is open.

        The element states contain a node reference.

        Arguments:
            switches {Sequence[PFTypes.Switch]} -- sequence of PowerFactory objects of type Switch

        Returns:
            set[ElementState] -- set of element states
        """

        relevancies: set[ElementState] = set()
        for sw in switches:
            if not sw.isclosed:
                cub = sw.fold_id
                element = cub.obj_id
                if element is not None:
                    terminal = cub.cterm
                    node_name = self.pfi.create_name(terminal, self.grid_name)
                    element_name = self.pfi.create_name(element, self.grid_name)
                    element_state = ElementState(name=element_name, open_switches=(node_name,))
                    relevancies.add(element_state)

        return relevancies

    def create_coupler_states(self, couplers: Sequence[PFTypes.Coupler]) -> set[ElementState]:
        """Create element states for all type of elements based on if the coupler is open.

        The element states contain a node reference.

        Arguments:
            swtiches {Sequence[PFTypes.Coupler]} -- sequence of PowerFactory objects of type Coupler

        Returns:
            set[ElementState] -- set of element states
        """

        relevancies: set[ElementState] = set()
        for coupler in couplers:
            if not coupler.isclosed:
                element_name = self.pfi.create_name(coupler, self.grid_name)
                element_state = ElementState(name=element_name, disabled=True)
                relevancies.add(element_state)

        return relevancies

    def create_node_power_on_states(self, terminals: Sequence[PFTypes.Terminal]) -> set[ElementState]:
        """Create element states based on if the connected nodes are out of service.

        The element states contain a node reference.

        Arguments:
            terminals {Sequence[PFTypes.Terminal]} -- sequence of PowerFactory objects of type Terminal

        Returns:
            set[ElementState] -- set of element states
        """

        relevancies: set[ElementState] = set()
        for terminal in terminals:
            if terminal.outserv:
                node_name = self.pfi.create_name(terminal, self.grid_name)
                element_state = ElementState(name=node_name, disabled=True)
                relevancies.add(element_state)

        return relevancies

    def create_element_power_on_states(
        self,
        elements: Sequence[ElementBase | PFTypes.Line | PFTypes.Transformer2W],
    ) -> set[ElementState]:
        """Create element states for one-sided connected elements based on if the elements are out of service.

        The element states contain no node reference.

        Arguments:
            elements {Sequence[ElementBase} -- sequence of one-sided connected PowerFactory objects

        Returns:
            set[ElementState] -- set of element states
        """

        relevancies: set[ElementState] = set()
        for element in elements:
            if element.outserv:
                element_name = self.pfi.create_name(element, self.grid_name)
                element_state = ElementState(name=element_name, disabled=True)
                relevancies.add(element_state)

        return relevancies

    def create_steadystate_case(self, meta: Meta, data: PowerfactoryData) -> SteadystateCase:
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
        transformers_2w = self.create_transformer_2w_ssc(pf_transformers_2w, grid_name)
        return self.pfi.list_from_sequences(transformers_2w)

    def create_transformer_2w_ssc(
        self,
        pf_transformers_2w: Sequence[PFTypes.Transformer2W],
        grid_name: str,
    ) -> set[TransformerSSC]:
        transformers_2w: set[TransformerSSC] = set()
        for transformer in pf_transformers_2w:
            name = self.pfi.create_name(transformer, grid_name)
            export, _ = self.get_description(transformer)
            if not export:
                logger.warning("Transformer {transformer_name} not set for export. Skipping.", transformer_name=name)
                continue

            # Transformer Tap Changer
            t_type = transformer.typ_id
            tap_pos = None if t_type is None else transformer.nntap

            transformer_ssc = TransformerSSC(name=name, tap_pos=tap_pos)
            logger.debug("Created steadystate for transformer_2w {transformer_ssc}.", transformer_ssc=transformer_ssc)
            transformers_2w.add(transformer_ssc)

        return transformers_2w

    def create_external_grid_ssc(
        self,
        ext_grids: Sequence[PFTypes.ExternalGrid],
        grid_name: str,
    ) -> Sequence[ExternalGridSSC]:
        ext_grid_sscs = [self.create_external_grid_ssc_state(grid, grid_name) for grid in ext_grids]
        return [e for e in ext_grid_sscs if e is not None]

    def create_external_grid_ssc_state(
        self,
        ext_grid: PFTypes.ExternalGrid,
        grid_name: str,
    ) -> ExternalGridSSC | None:
        name = self.pfi.create_name(ext_grid, grid_name)
        export, _ = self.get_description(ext_grid)
        if not export:
            logger.warning("External grid {ext_grid_name} not set for export. Skipping.", ext_grid_name=name)
            return None

        if ext_grid.bus1 is None:
            logger.warning("External grid {ext_grid_name} not connected to any bus. Skipping.", ext_grid_name=name)
            return None

        g_type = GridType(ext_grid.bustp)
        if g_type == GridType.SL:
            ext_grid_ssc = ExternalGridSSC(
                name=name,
                u_0=round(ext_grid.usetp * ext_grid.bus1.cterm.uknom * Exponents.VOLTAGE, DecimalDigits.VOLTAGE),
                phi_0=ext_grid.phiini,
            )
        elif g_type == GridType.PV:
            ext_grid_ssc = ExternalGridSSC(
                name=name,
                u_0=round(ext_grid.usetp * ext_grid.bus1.cterm.uknom * Exponents.VOLTAGE, DecimalDigits.VOLTAGE),
                p_0=round(ext_grid.pgini * Exponents.POWER, DecimalDigits.POWER),
            )
        elif g_type == GridType.PQ:
            ext_grid_ssc = ExternalGridSSC(
                name=name,
                p_0=round(ext_grid.pgini * Exponents.POWER, DecimalDigits.POWER),
                q_0=round(ext_grid.qgini * Exponents.POWER, DecimalDigits.POWER),
            )

        ext_grid_ssc = ExternalGridSSC(name=name)
        logger.debug("Created steadystate for external grid {ext_grid_ssc}.", ext_grid_ssc=ext_grid_ssc)
        return ext_grid_ssc

    def create_loads_ssc(  # noqa: PLR0913 # fix
        self,
        consumers: Sequence[PFTypes.Load],
        consumers_lv: Sequence[PFTypes.LoadLV],
        consumers_mv: Sequence[PFTypes.LoadMV],
        generators: Sequence[PFTypes.Generator],
        pv_systems: Sequence[PFTypes.PVSystem],
        grid_name: str,
    ) -> Sequence[LoadSSC]:
        normal_consumers = self.create_consumers_ssc_normal(consumers, grid_name)
        lv_consumers = self.create_consumers_ssc_lv(consumers_lv, grid_name)
        mv_consumers = self.create_loads_ssc_mv(consumers_mv, grid_name)
        gen_producers = self.create_producers_ssc(generators)
        pv_producers = self.create_producers_ssc(pv_systems)
        return self.pfi.list_from_sequences(normal_consumers, lv_consumers, mv_consumers, gen_producers, pv_producers)

    def create_consumers_ssc_normal(
        self,
        loads: Sequence[PFTypes.Load],
        grid_name: str,
    ) -> Sequence[LoadSSC]:
        consumers_ssc = [self.create_consumer_ssc_normal(load, grid_name) for load in loads]
        return [e for e in consumers_ssc if e is not None]

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
        power = self.calc_normal_load_power_sym(load) if not load.i_sym else self.calc_normal_load_power_asym(load)

        if power is not None:  # noqa: SIM102
            if not power.is_empty:
                return power

        logger.warning("Power is not set for load {load_name}. Skipping.", load_name=load.loc_name)
        return None

    def calc_normal_load_power_sym(self, load: PFTypes.Load) -> LoadPower | None:  # noqa: PLR0911
        load_type = load.mode_inp
        scaling = load.scale0
        if load_type == "DEF" or load_type == "PQ":
            return LoadPower.from_pq_sym(pow_act=load.plini, pow_react=load.qlini, scaling=scaling)

        if load_type == "PC":
            return LoadPower.from_pc_sym(pow_act=load.plini, cosphi=load.coslini, scaling=scaling)

        if load_type == "IC":
            return LoadPower.from_ic_sym(voltage=load.u0, current=load.ilini, cosphi=load.coslini, scaling=scaling)

        if load_type == "SC":
            return LoadPower.from_sc_sym(pow_app=load.slini, cosphi=load.coslini, scaling=scaling)

        if load_type == "QC":
            return LoadPower.from_qc_sym(pow_react=load.qlini, cosphi=load.coslini, scaling=scaling)

        if load_type == "IP":
            return LoadPower.from_ip_sym(voltage=load.u0, current=load.ilini, pow_act=load.plini, scaling=scaling)

        if load_type == "SP":
            return LoadPower.from_sp_sym(pow_app=load.slini, pow_act=load.plini, scaling=scaling)

        if load_type == "SQ":
            return LoadPower.from_sq_sym(pow_app=load.slini, pow_react=load.qlini, scaling=scaling)

        msg = "unreachable"
        raise RuntimeError(msg)

    def calc_normal_load_power_asym(self, load: PFTypes.Load) -> LoadPower | None:  # noqa: PLR0911
        load_type = load.mode_inp
        scaling = load.scale0
        if load_type == "DEF" or load_type == "PQ":
            return LoadPower.from_pq_asym(
                pow_act_r=load.plinir,
                pow_act_s=load.plinis,
                pow_act_t=load.plinit,
                pow_react_r=load.qlinir,
                pow_react_s=load.qlinis,
                pow_react_t=load.qlinit,
                scaling=scaling,
            )

        if load_type == "PC":
            return LoadPower.from_pc_asym(
                pow_act_r=load.plinir,
                pow_act_s=load.plinis,
                pow_act_t=load.plinit,
                cosphi_r=load.coslinir,
                cosphi_s=load.coslinis,
                cosphi_t=load.coslinit,
                scaling=scaling,
            )

        if load_type == "IC":
            return LoadPower.from_ic_asym(
                voltage=load.u0,
                current_r=load.ilinir,
                current_s=load.ilinis,
                current_t=load.ilinit,
                cosphi_r=load.coslinir,
                cosphi_s=load.coslinis,
                cosphi_t=load.coslinit,
                scaling=scaling,
            )

        if load_type == "SC":
            return LoadPower.from_sc_asym(
                pow_app_r=load.slinir,
                pow_app_s=load.slinis,
                pow_app_t=load.slinit,
                cosphi_r=load.coslinir,
                cosphi_s=load.coslinis,
                cosphi_t=load.coslinit,
                scaling=scaling,
            )

        if load_type == "QC":
            return LoadPower.from_qc_asym(
                pow_react_r=load.qlinir,
                pow_react_s=load.qlinis,
                pow_react_t=load.qlinit,
                cosphi_r=load.coslinir,
                cosphi_s=load.coslinis,
                cosphi_t=load.coslinit,
                scaling=scaling,
            )

        if load_type == "IP":
            return LoadPower.from_ip_asym(
                voltage=load.u0,
                current_r=load.ilinir,
                current_s=load.ilinis,
                current_t=load.ilinit,
                pow_act_r=load.plinir,
                pow_act_s=load.plinis,
                pow_act_t=load.plinit,
                scaling=scaling,
            )

        if load_type == "SP":
            return LoadPower.from_sp_asym(
                pow_app_r=load.slinir,
                pow_app_s=load.slinis,
                pow_app_t=load.slinit,
                pow_act_r=load.plinir,
                pow_act_s=load.plinis,
                pow_act_t=load.plinit,
                scaling=scaling,
            )

        if load_type == "SQ":
            return LoadPower.from_sq_asym(
                pow_app_r=load.slinir,
                pow_app_s=load.slinis,
                pow_app_t=load.slinit,
                pow_react_r=load.qlinir,
                pow_react_s=load.qlinis,
                pow_react_t=load.qlinit,
                scaling=scaling,
            )

        msg = "unreachable"
        raise RuntimeError(msg)

    def create_consumers_ssc_lv(self, loads: Sequence[PFTypes.LoadLV], grid_name: str) -> Sequence[LoadSSC]:
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
                name_suffix=sfx_pre.format(index) + "_" + ConsumerSystemType.FIXED.value,
            )
            if power.fixed.pow_app_abs != 0
            else None
        )
        consumer_night_ssc = (
            self.create_consumer_ssc(
                load,
                power.night,
                grid_name,
                name_suffix=sfx_pre.format(index) + "_" + ConsumerSystemType.NIGHT_STORAGE.value,
            )
            if power.night.pow_app_abs != 0
            else None
        )
        consumer_flexible_ssc = (
            self.create_consumer_ssc(
                load,
                power.flexible,
                grid_name,
                name_suffix=sfx_pre.format(index) + "_" + ConsumerSystemType.VARIABLE.value,
            )
            if power.flexible.pow_app_abs != 0
            else None
        )
        return [e for e in [consumer_fixed_ssc, consumer_night_ssc, consumer_flexible_ssc] if e is not None]

    def calc_load_lv_powers(self, load: PFTypes.LoadLV) -> Sequence[LoadLV]:
        subloads = self.pfi.subloads_of(load)
        if not subloads:
            return [self.calc_load_lv_power(load)]

        return [self.calc_load_lv_power_sym(sl) for sl in subloads]

    def calc_load_lv_power(self, load: PFTypes.LoadLV) -> LoadLV:
        load_type = load.iopt_inp
        scaling = load.scale0
        if not load.i_sym:
            power_fixed = self.calc_load_lv_power_fixed_sym(load, scaling)
        else:
            if load_type == IOpt.SCosphi:
                power_fixed = LoadPower.from_sc_asym(
                    pow_app_r=load.slinir,
                    pow_app_s=load.slinis,
                    pow_app_t=load.slinit,
                    cosphi_r=load.coslinir,
                    cosphi_s=load.coslinis,
                    cosphi_t=load.coslinit,
                    scaling=scaling,
                )
            elif load_type == IOpt.PCosphi:
                power_fixed = LoadPower.from_pc_asym(
                    pow_act_r=load.plinir,
                    pow_act_s=load.plinis,
                    pow_act_t=load.plinit,
                    cosphi_r=load.coslinir,
                    cosphi_s=load.coslinis,
                    cosphi_t=load.coslinit,
                    scaling=scaling,
                )
            elif load_type == IOpt.UICosphi:
                power_fixed = LoadPower.from_ic_asym(
                    voltage=load.ulini,
                    current_r=load.ilinir,
                    current_s=load.ilinis,
                    current_t=load.ilinit,
                    cosphi_r=load.coslinir,
                    cosphi_s=load.coslinis,
                    cosphi_t=load.coslinit,
                    scaling=scaling,
                )
            else:
                msg = "unreachable"
                raise RuntimeError(msg)

        power_night = LoadPower.from_pq_sym(
            pow_act=load.pnight,
            pow_react=0,
            scaling=1,
        )
        power_flexible = LoadPower.from_sc_sym(
            pow_app=load.cSav,
            cosphi=load.ccosphi,
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
        power_flexible = LoadPower.from_sc_sym(
            pow_app=load.cSav,
            cosphi=load.ccosphi,
            scaling=1,
        )
        return LoadLV(fixed=power_fixed, night=power_night, flexible=power_flexible)

    def calc_load_lv_power_fixed_sym(
        self,
        load: PFTypes.LoadLV | PFTypes.LoadLVP,
        scaling: float,
    ) -> LoadPower:
        load_type = load.iopt_inp
        if load_type == IOpt.SCosphi:
            return LoadPower.from_sc_sym(
                pow_app=load.slini,
                cosphi=load.coslini,
                scaling=scaling,
            )

        if load_type == IOpt.PCosphi:
            return LoadPower.from_pc_sym(
                pow_act=load.plini,
                cosphi=load.coslini,
                scaling=scaling,
            )

        if load_type == IOpt.UICosphi:
            return LoadPower.from_ic_sym(
                voltage=load.ulini,
                current=load.ilini,
                cosphi=load.coslini,
                scaling=scaling,
            )

        if load_type == IOpt.ECosphi:
            return LoadPower.from_pc_sym(
                pow_act=load.cplinia,
                cosphi=load.coslini,
                scaling=scaling,
            )

        msg = "unreachable"
        raise RuntimeError(msg)

    def create_loads_ssc_mv(
        self,
        loads: Sequence[PFTypes.LoadMV],
        grid_name: str,
    ) -> set[LoadSSC]:
        loads_ssc: set[LoadSSC] = set()
        for load in loads:
            power = self.calc_load_mv_power(load)
            consumer = self.create_consumer_ssc(load, power.consumer, grid_name, name_suffix="_CONSUMER")
            if consumer is not None:
                loads_ssc.add(consumer)

            producer = self.create_consumer_ssc(load, power.producer, grid_name, name_suffix="_PRODUCER")
            if producer is not None:
                loads_ssc.add(producer)

        return loads_ssc

    def calc_load_mv_power(self, load: PFTypes.LoadMV) -> LoadMV:
        if not load.ci_sym:
            return self.calc_load_mv_power_sym(load)

        return self.calc_load_mv_power_asym(load)

    def calc_load_mv_power_sym(self, load: PFTypes.LoadMV) -> LoadMV:
        load_type = load.mode_inp
        scaling_cons = load.scale0
        scaling_prod = load.gscale
        if load_type == "PC":
            power_consumer = LoadPower.from_pc_sym(
                pow_act=load.plini,
                cosphi=load.coslini,
                scaling=scaling_cons,
            )
            power_producer = LoadPower.from_pc_sym(
                pow_act=load.plini,
                cosphi=load.cosgini,
                scaling=scaling_prod,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        if load_type == "SC":
            power_consumer = LoadPower.from_sc_sym(
                pow_app=load.slini,
                cosphi=load.coslini,
                scaling=scaling_cons,
            )
            power_producer = LoadPower.from_sc_sym(
                pow_app=load.sgini,
                cosphi=load.cosgini,
                scaling=scaling_prod,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        if load_type == "EC":
            logger.warning("Power from yearly demand is not implemented yet. Skipping.")
            power_consumer = LoadPower.from_pc_sym(
                pow_act=load.cplinia,
                cosphi=load.coslini,
                scaling=scaling_cons,
            )
            power_producer = LoadPower.from_pc_sym(
                pow_act=load.pgini,
                cosphi=load.cosgini,
                scaling=scaling_prod,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        msg = "unreachable"
        raise RuntimeError(msg)

    def calc_load_mv_power_asym(self, load: PFTypes.LoadMV) -> LoadMV:
        load_type = load.mode_inp
        scaling_cons = load.scale0
        scaling_prod = load.gscale
        if load_type == "PC":
            power_consumer = LoadPower.from_pc_asym(
                pow_act_r=load.plinir,
                pow_act_s=load.plinis,
                pow_act_t=load.plinit,
                cosphi_r=load.coslinir,
                cosphi_s=load.coslinis,
                cosphi_t=load.coslinit,
                scaling=scaling_cons,
            )
            power_producer = LoadPower.from_pc_asym(
                pow_act_r=load.pginir,
                pow_act_s=load.pginis,
                pow_act_t=load.pginit,
                cosphi_r=load.cosginir,
                cosphi_s=load.cosginis,
                cosphi_t=load.cosginit,
                scaling=scaling_prod,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        if load_type == "SC":
            power_consumer = LoadPower.from_sc_asym(
                pow_app_r=load.slinir,
                pow_app_s=load.slinis,
                pow_app_t=load.slinit,
                cosphi_r=load.coslinir,
                cosphi_s=load.coslinis,
                cosphi_t=load.coslinit,
                scaling=scaling_cons,
            )
            power_producer = LoadPower.from_sc_asym(
                pow_app_r=load.sginir,
                pow_app_s=load.sginis,
                pow_app_t=load.sginit,
                cosphi_r=load.cosginir,
                cosphi_s=load.cosginis,
                cosphi_t=load.cosginit,
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
        export, _ = self.get_description(load)
        if not export:
            logger.warning("External grid {consumer_ssc_name} not set for export. Skipping.", consumer_ssc_name=name)
            return None

        active_power = power.as_active_power_ssc()
        reactive_power = power.as_reactive_power_ssc()

        load_ssc = LoadSSC(
            name=name,
            active_power=active_power,
            reactive_power=reactive_power,
        )
        logger.debug("Created steadystate for consumer {load_ssc}.", load_ssc=load_ssc)
        return load_ssc

    def create_producers_ssc(
        self,
        generators: Sequence[PFTypes.GeneratorBase],
    ) -> set[LoadSSC]:
        producers_ssc: set[LoadSSC] = set()
        for gen in generators:
            gen_name = self.pfi.create_generator_name(gen)

            export, _ = self.get_description(gen)
            if not export:
                logger.warning("Generator {gen_name} not set for export. Skipping.", gen_name=gen_name)
                continue

            bus = gen.bus1
            if bus is None:
                logger.warning("Generator {gen_name} not connected to any bus. Skipping.", gen_name=gen_name)
                continue

            terminal = bus.cterm
            u_n = round(terminal.uknom, DecimalDigits.VOLTAGE) * Exponents.VOLTAGE

            power = LoadPower.from_pq_sym(
                pow_act=gen.pgini_a * gen.ngnum,
                pow_react=gen.qgini_a * gen.ngnum,
                scaling=gen.scale0_a,
            )

            active_power = power.as_active_power_ssc()

            # External Controller
            ext_ctrl = gen.c_pstac
            # Q-Controller
            controller = self.create_q_controller(gen, gen_name, u_n, ext_ctrl=ext_ctrl)
            reactive_power = power.as_reactive_power_ssc(controller=controller)

            producer = LoadSSC(
                name=gen_name,
                active_power=active_power,
                reactive_power=reactive_power,
            )
            logger.debug("Created steadystate for producer {producer}.", producer=producer)
            producers_ssc.add(producer)

        return producers_ssc

    def create_producers_ssc_state(
        self,
        generator: PFTypes.GeneratorBase,
    ) -> LoadSSC | None:
        gen_name = self.pfi.create_generator_name(generator)

        export, _ = self.get_description(generator)
        if not export:
            logger.warning("Generator {gen_name} not set for export. Skipping.", gen_name=gen_name)
            return None

        bus = generator.bus1
        if bus is None:
            logger.warning("Generator {gen_name} not connected to any bus. Skipping.", gen_name=gen_name)
            return None

        terminal = bus.cterm
        u_n = round(terminal.uknom, DecimalDigits.VOLTAGE) * Exponents.VOLTAGE

        power = LoadPower.from_pq_sym(
            pow_act=generator.pgini_a * generator.ngnum,
            pow_react=generator.qgini_a * generator.ngnum,
            scaling=generator.scale0_a,
        )

        active_power = power.as_active_power_ssc()

        # External Controller
        ext_ctrl = generator.c_pstac
        # Q-Controller
        controller = self.create_q_controller(generator, gen_name, u_n, ext_ctrl=ext_ctrl)
        reactive_power = power.as_reactive_power_ssc(controller=controller)

        load_ssc = LoadSSC(
            name=gen_name,
            active_power=active_power,
            reactive_power=reactive_power,
        )
        logger.debug("Created steadystate for producer {load_ssc}.", load_ssc=load_ssc)
        return load_ssc

    def create_q_controller(  # noqa: PLR0912, PLR0915
        self,
        gen: PFTypes.GeneratorBase,
        gen_name: str,
        u_n: float,
        ext_ctrl: PFTypes.StationController | None,
    ) -> Controller:
        controller_type_dict_default = {
            "constv": ControllerType.U_CONST,
            "constc": ControllerType.COSPHI_CONST,
            "constq": ControllerType.Q_CONST,
            "qvchar": ControllerType.Q_U,
            "qpchar": ControllerType.Q_P,
            "cpchar": ControllerType.COSPHI_P,
        }
        s_r = gen.sgn
        cosphi_r = gen.cosn
        q_r = s_r * math.sin(math.acos(cosphi_r))

        cosphi_type = None
        cosphi = None
        q_set = None
        m_tab2015 = None  # Q(U) droop/slope related to VDE-AR-N 4120:2015
        m_tar2018 = None  # Q(U) droop/slope related to VDE-AR-N 4120:2018
        qmax_ue = q_r
        qmax_oe = q_r
        u_q0 = None
        udeadband_low = None
        udeadband_up = None

        if ext_ctrl is None:
            ext_ctrl_name = None
            controller_type = controller_type_dict_default[gen.av_mode]
            if controller_type == ControllerType.COSPHI_CONST:
                cosphi = gen.cosgini
                cosphi_type = CosphiDir.UE if gen.pf_recap == 1 else CosphiDir.OE
            elif controller_type == ControllerType.Q_CONST:
                q_set = gen.qgini
            elif controller_type == ControllerType.Q_U:
                qmax_ue = abs(gen.Qfu_min)  # absolute value
                qmax_oe = abs(gen.Qfu_max)  # absolute value
                u_q0 = gen.udeadbup - (gen.udeadbup - gen.udeadblow) / 2  # p.u.
                udeadband_low = abs(u_q0 - gen.udeadblow)  # delta in p.u.
                udeadband_up = abs(u_q0 - gen.udeadbup)  # delta in p.u.
                m_tab2015 = 100 / abs(gen.ddroop) * 100 / u_n / cosphi_r  # (% von Pr) / kV
                m_tar2018 = self.transform_qu_slope(slope=m_tab2015, given_format="2015", target_format="2018", u_n=u_n)
            elif controller_type == ControllerType.Q_P:
                logger.warning("Generator {gen_name} Q(P) control is not implemented yet. Skipping.", gen_name=gen_name)
            elif controller_type == ControllerType.COSPHI_P:
                logger.warning(
                    "Generator {gen_name} cosphi(P) control is not implemented yet. Skipping.",
                    gen_name=gen_name,
                )
            elif controller_type == ControllerType.U_CONST:
                logger.warning(
                    "Generator {gen_name} Const. U control is not implemented yet. Skipping.",
                    gen_name=gen_name,
                )
            else:
                msg = "unreachable"
                raise RuntimeError(msg)

        else:
            ext_ctrl_name = self.pfi.create_generator_name(gen, generator_name=ext_ctrl.loc_name)

            ctrl_mode = ext_ctrl.i_ctrl
            if ctrl_mode == CtrlMode.PowAct:  # voltage control mode
                controller_type = ControllerType.U_CONST
            elif ctrl_mode == CtrlMode.PowReact:  # reactive power control mode
                controller_type_dict_pow_react = {
                    PowReactChar.const: ControllerType.Q_CONST,
                    PowReactChar.U: ControllerType.Q_U,
                    PowReactChar.P: ControllerType.Q_P,
                }
                controller_type = controller_type_dict_pow_react[ext_ctrl.qu_char]

                if controller_type == ControllerType.Q_CONST:
                    q_dir = -1 if ext_ctrl.iQorient else 1  # negative counting --> under excited
                    q_set = ext_ctrl.qsetp * q_dir
                elif controller_type == ControllerType.Q_U:
                    u_nom = round(ext_ctrl.refbar.uknom, DecimalDigits.VOLTAGE) * Exponents.VOLTAGE  # voltage in V

                    qmax_ue = abs(ext_ctrl.Qmin)
                    qmax_oe = abs(ext_ctrl.Qmax)
                    u_q0 = ext_ctrl.udeadbup - (ext_ctrl.udeadbup - ext_ctrl.udeadblow) / 2  # per unit
                    udeadband_low = abs(u_q0 - ext_ctrl.udeadblow)  # delta in per unit
                    udeadband_up = abs(u_q0 - ext_ctrl.udeadbup)  # delta in per unit

                    q_rated = ext_ctrl.Srated
                    try:
                        if abs((abs(q_rated) - abs(s_r)) / abs(s_r)) < M_TAB2015_MIN_THRESHOLD:  # q_rated == s_r
                            m_tab2015 = 100 / ext_ctrl.ddroop * 100 * Exponents.VOLTAGE / u_nom / cosphi_r
                        else:
                            m_tab2015 = (
                                100
                                / abs(ext_ctrl.ddroop)
                                * 100
                                * Exponents.VOLTAGE
                                / u_nom
                                * math.tan(math.acos(cosphi_r))
                            )

                        # in default there should q_rated=s_r, but user could enter incorrectly
                        m_tab2015 = m_tab2015 * q_rated / s_r
                        m_tar2018 = self.transform_qu_slope(
                            slope=m_tab2015,
                            given_format="2015",
                            target_format="2018",
                            u_n=u_nom,
                        )
                    except ZeroDivisionError:
                        m_tab2015 = float("inf")
                        m_tar2018 = float("inf")

                elif controller_type == ControllerType.Q_P:
                    logger.warning(
                        "Generator {gen_name}: Q(P) control is not implemented yet. Skipping.",
                        gen_name=gen_name,
                    )
                else:
                    msg = "unreachable"
                    raise RuntimeError(msg)

            elif ctrl_mode == CtrlMode.Cosphi:  # cosphi control mode
                controller_type_dict_cosphi = {
                    CosphiChar.const: ControllerType.COSPHI_CONST,
                    CosphiChar.U: ControllerType.COSPHI_P,
                    CosphiChar.P: ControllerType.COSPHI_U,
                }
                controller_type = controller_type_dict_cosphi[ext_ctrl.cosphi_char]

                if controller_type == ControllerType.COSPHI_CONST:
                    cosphi = ext_ctrl.pfsetp
                    ue = ext_ctrl.pf_recap ^ ext_ctrl.iQorient  # OE/UE XOR +Q/-Q
                    cosphi_type = CosphiDir.UE if ue else CosphiDir.OE
                elif controller_type == ControllerType.COSPHI_P:
                    logger.warning(
                        "Generator {gen_name}: cosphi(P) control is not implemented yet. Skipping.",
                        gen_name=gen_name,
                    )
                elif controller_type == ControllerType.COSPHI_U:
                    logger.warning(
                        "Generator {gen_name}: cosphi(U) control is not implemented yet. Skipping.",
                        gen_name=gen_name,
                    )
                else:
                    msg = "unreachable"
                    raise RuntimeError(msg)

            elif ctrl_mode == CtrlMode.Tanphi:  # tanphi control mode
                controller_type = ControllerType.TANPHI_CONST
                cosphi = math.cos(math.atan(ext_ctrl.tansetp))
                cosphi_type = CosphiDir.UE if ext_ctrl.iQorient else CosphiDir.OE
            else:
                msg = "unreachable"
                raise RuntimeError(msg)

        # final scaling and rounding
        if cosphi:
            cosphi = round(cosphi, DecimalDigits.COSPHI)

        if q_set:
            q_set = round(q_set * Exponents.POWER * gen.ngnum, DecimalDigits.POWER)

        if m_tab2015:
            m_tab2015 = round(m_tab2015, DecimalDigits.PU)

        if m_tar2018:
            m_tar2018 = round(m_tar2018, DecimalDigits.PU)

        if u_q0:
            u_q0 = round(u_q0, DecimalDigits.VOLTAGE)

        if udeadband_up:
            udeadband_up = round(udeadband_up, DecimalDigits.VOLTAGE)

        if udeadband_low:
            udeadband_low = round(udeadband_low, DecimalDigits.VOLTAGE)

        return Controller(
            controller_type=controller_type,
            external_controller_name=ext_ctrl_name,
            cosphi_type=cosphi_type,
            cosphi=cosphi,
            q_set=q_set,
            m_tab2015=m_tab2015,
            m_tar2018=m_tar2018,
            qmax_ue=round(qmax_ue * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
            qmax_oe=round(qmax_oe * Exponents.POWER * gen.ngnum, DecimalDigits.POWER),
            u_q0=u_q0,
            udeadband_up=udeadband_up,
            udeadband_low=udeadband_low,
        )

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

    def create_transformers(
        self,
        pf_transformers_2w: Sequence[PFTypes.Transformer2W],
        grid_name: str,
    ) -> Sequence[Transformer]:
        transformers_2w = self.create_transformers_2w(pf_transformers_2w, grid_name)

        return self.pfi.list_from_sequences(transformers_2w)

    def create_transformers_2w(
        self,
        transformers_2w: Sequence[PFTypes.Transformer2W],
        grid_name: str,
    ) -> set[Transformer]:
        transformers: set[Transformer] = set()
        for transformer_2w in transformers_2w:
            name = self.pfi.create_name(element=transformer_2w, grid_name=grid_name)
            export, description = self.get_description(transformer_2w)
            if not export:
                logger.warning("Transformer {transformer_name} not set for export. Skipping.", transformer_name=name)
                continue

            if transformer_2w.buslv is None or transformer_2w.bushv is None:
                logger.warning(
                    "Transformer {transformer_name} not connected to buses on both sides. Skipping.",
                    transformer_name=name,
                )
                continue

            t_high = transformer_2w.bushv.cterm
            t_low = transformer_2w.buslv.cterm

            t_high_name = self.pfi.create_name(element=t_high, grid_name=grid_name)
            t_low_name = self.pfi.create_name(element=t_low, grid_name=grid_name)

            t_type = transformer_2w.typ_id

            if t_type is not None:
                t_number = transformer_2w.ntnum
                vector_group = t_type.vecgrp

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
                        "Transformer {transformer_name} has second tap changer. Not supported so far. Skipping.",
                        transformer_name=name,
                    )
                    continue

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
                vector_h = t_type.tr2cn_h  # Wiring HV
                vector_l = t_type.tr2cn_l  # Wiring LV
                vector_phase_angle_clock = t_type.nt2ag

                wh = Winding(
                    node=t_high_name,
                    s_r=round(s_r * Exponents.POWER, DecimalDigits.POWER),
                    u_r=round(u_ref_h * Exponents.VOLTAGE, DecimalDigits.VOLTAGE),
                    u_n=round(u_nom_h * Exponents.VOLTAGE, DecimalDigits.VOLTAGE),
                    r1=r_1,
                    r0=r_0,
                    x1=x_1,
                    x0=x_0,
                    vector_group=vector_h,
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
                    vector_group=vector_l,
                    phase_angle_clock=int(vector_phase_angle_clock),
                )

                transformer = Transformer(
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
                    windings={wh, wl},
                )
                logger.debug("Created transformer {transformer}", transformer=transformer)
                transformers.add(transformer)
            else:
                logger.warning("Type not set for transformer {transformer_name}. Skipping.", transformer_name=name)

        return transformers

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


def export_powerfactory_data(  # noqa: PLR0913 # fix
    export_path: pathlib.Path,
    project_name: str,
    grid_name: str,
    powerfactory_user_profile: str = "",
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH,
    powerfactory_version: str = POWERFACTORY_VERSION,
    topology_name: str | None = None,
    topology_case_name: str | None = None,
    steadystate_case_name: str | None = None,
) -> None:
    """Export powerfactory data to json files using PowerfactoryExporter running in process.

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

    process = PowerfactoryExporterProcess(
        project_name=project_name,
        export_path=export_path,
        grid_name=grid_name,
        powerfactory_user_profile=powerfactory_user_profile,
        powerfactory_path=powerfactory_path,
        powerfactory_version=powerfactory_version,
        topology_name=topology_name,
        topology_case_name=topology_case_name,
        steadystate_case_name=steadystate_case_name,
    )
    process.start()
    process.join()
