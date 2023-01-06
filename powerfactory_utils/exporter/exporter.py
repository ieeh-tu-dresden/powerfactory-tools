from __future__ import annotations

import datetime
import itertools
import math
import multiprocessing
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from powerfactory_utils.constants import DecimalDigits
from powerfactory_utils.constants import Exponents
from powerfactory_utils.exporter.load_power import LoadPower
from powerfactory_utils.interface import PowerfactoryInterface
from powerfactory_utils.schema.base import Meta
from powerfactory_utils.schema.base import VoltageSystemType
from powerfactory_utils.schema.steadystate_case.case import Case as SteadyStateCase
from powerfactory_utils.schema.steadystate_case.controller import Controller
from powerfactory_utils.schema.steadystate_case.controller import ControllerType
from powerfactory_utils.schema.steadystate_case.controller import CosphiDir
from powerfactory_utils.schema.steadystate_case.external_grid import ExternalGrid as ExternalGridSSC
from powerfactory_utils.schema.steadystate_case.load import Load as LoadSSC
from powerfactory_utils.schema.steadystate_case.transformer import Transformer as TransformerSSC
from powerfactory_utils.schema.topology.active_power import ActivePower
from powerfactory_utils.schema.topology.branch import Branch
from powerfactory_utils.schema.topology.branch import BranchType
from powerfactory_utils.schema.topology.external_grid import ExternalGrid
from powerfactory_utils.schema.topology.external_grid import GridType
from powerfactory_utils.schema.topology.load import ConsumerPhaseConnectionType
from powerfactory_utils.schema.topology.load import ConsumerSystemType
from powerfactory_utils.schema.topology.load import Load
from powerfactory_utils.schema.topology.load import LoadType
from powerfactory_utils.schema.topology.load import ProducerPhaseConnectionType
from powerfactory_utils.schema.topology.load import ProducerSystemType
from powerfactory_utils.schema.topology.load_model import LoadModel
from powerfactory_utils.schema.topology.node import Node
from powerfactory_utils.schema.topology.reactive_power import ReactivePower
from powerfactory_utils.schema.topology.topology import Topology
from powerfactory_utils.schema.topology.transformer import TapSide
from powerfactory_utils.schema.topology.transformer import Transformer
from powerfactory_utils.schema.topology.transformer import TransformerPhaseTechnologyType
from powerfactory_utils.schema.topology.windings import Winding
from powerfactory_utils.schema.topology_case.case import Case as TopologyCase
from powerfactory_utils.schema.topology_case.element_state import ElementState

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Literal
    from typing import Optional
    from typing import Sequence
    from typing import Union

    from powerfactory_utils import powerfactory_types as pft

    ElementBase = Union[pft.GeneratorBase, pft.LoadBase, pft.ExternalGrid]


POWERFACTORY_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
POWERFACTORY_VERSION = "2022 SP2"


@dataclass
class LoadLV:
    fixed: LoadPower
    night: LoadPower
    variable: LoadPower


@dataclass
class LoadMV:
    consumer: LoadPower
    producer: LoadPower


@dataclass
class PowerfactoryData:
    name: str
    date: datetime.date
    project: str
    external_grids: Sequence[pft.ExternalGrid]
    terminals: Sequence[pft.Terminal]
    lines: Sequence[pft.Line]
    transformers_2w: Sequence[pft.Transformer2W]
    transformers_3w: Sequence[pft.Transformer3W]
    loads: Sequence[pft.Load]
    loads_lv: Sequence[pft.LoadLV]
    loads_mv: Sequence[pft.LoadMV]
    generators: Sequence[pft.Generator]
    pv_systems: Sequence[pft.PVSystem]
    couplers: Sequence[pft.Coupler]
    switches: Sequence[pft.Switch]
    fuses: Sequence[pft.Fuse]


class PowerfactoryExporterProcess(multiprocessing.Process):
    def __init__(
        self,
        export_path: pathlib.Path,
        project_name: str,
        grid_name: str,
        powerfactory_user_profile: str = "",
        powerfactory_path: pathlib.Path = POWERFACTORY_PATH,
        powerfactory_version: str = POWERFACTORY_VERSION,
        topology_name: Optional[str] = None,
        topology_case_name: Optional[str] = None,
        steadystate_case_name: Optional[str] = None,
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
        with PowerfactoryExporter(
            project_name=self.project_name,
            grid_name=self.grid_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_path=self.powerfactory_path,
            powerfactory_version=self.powerfactory_version,
        ) as pfe:
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
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.pfi.close()

    def export(
        self,
        export_path: pathlib.Path,
        topology_name: Optional[str] = None,
        topology_case_name: Optional[str] = None,
        steadystate_case_name: Optional[str] = None,
    ) -> bool:
        """Export grid topology, topology_case and steadystate_case to json files.

        Based on the class arguments of PowerFactoryExporter a grid, given in DIgSILENT PowerFactory, is exported to
        three json files with given schema. The whole grid data is separated into topology (raw assets), topology_case
        (binary switching info and out of service info) and steadystate_case (operation points).

        Arguments:
            export_path {pathlib.Path} -- the directory where the exported json files are saved
            topology_name {str} -- the chosen file name for 'topology' data
            topology_case_name {str} -- the chosen file name for related 'topology_case' data
            steadystate_case_name {str} -- the chosen file name for related 'steadystate_case' data

        Returns:
            bool -- success of export
        """

        data = self.compile_powerfactory_data()
        meta = self.create_meta_data(data=data)

        topology = self.create_topology(meta=meta, data=data)
        topology_case = self.create_topology_case(meta=meta, data=data)
        steadystate_case = self.create_steadystate_case(meta=meta, data=data)

        if steadystate_case.verify_against_topology(topology) is False:
            logger.error("Steadystate case is not valid.")
            return False

        if (
            self.export_data(
                data=topology,
                data_name=topology_name,
                data_type="topology",
                export_path=export_path,
            )
            is False
        ):
            logger.error("Topology export failed.")
            return False

        if (
            self.export_data(
                data=topology_case,
                data_name=topology_case_name,
                data_type="topology_case",
                export_path=export_path,
            )
            is False
        ):
            logger.error("Topology Case export failed.")
            return False

        if (
            self.export_data(
                data=steadystate_case,
                data_name=steadystate_case_name,
                data_type="steadystate_case",
                export_path=export_path,
            )
            is False
        ):
            logger.error("Steadystate Case export failed.")
            return False

        return True

    def export_scenario(
        self,
        export_path: pathlib.Path,
        scenario_name: str,
        topology_case_name: Optional[str] = None,
        steadystate_case_name: Optional[str] = None,
        verify_steadystate_case: bool = False,
    ) -> bool:
        """Export grid topology_case and steadystate_case for a given scenario to json files.

        Based on the class arguments of PowerFactoryExporter a grid, given in DIgSILENT PowerFactory, is exported to
        two json files with given schema. Only grid data related to topology_case (binary switching info and out of
        service info) and steadystate_case (operation points) is exported.

        Arguments:
            export_path {pathlib.Path} -- the directory where the exported json files are saved
            scenario_name {str} -- the scenario name
            topology_case_name {str} -- the chosen file name for related 'topology_case' data
            steadystate_case_name {str} -- the chosen file name for related 'steadystate_case' data
            verify_steadystate_case {bool} -- if True, associated topology is created to be checked against

        Returns:
            bool -- success of export
        """

        if self.switch_scenario(scenario_name) is False:
            logger.error("Switching scenario failed.")
            return False

        data = self.compile_powerfactory_data()
        meta = self.create_meta_data(data=data)

        topology_case = self.create_topology_case(meta=meta, data=data)
        steadystate_case = self.create_steadystate_case(meta=meta, data=data)
        if verify_steadystate_case is True:
            topology = self.create_topology(meta=meta, data=data)
            if steadystate_case.verify_against_topology(topology) is False:
                logger.error("Steadystate case is not valid.")
                return False

        if (
            self.export_data(
                data=topology_case,
                data_name=topology_case_name,
                data_type="topology_case",
                export_path=export_path,
            )
            is False
        ):
            logger.error("Topology Case export failed.")
            return False

        if (
            self.export_data(
                data=steadystate_case,
                data_name=steadystate_case_name,
                data_type="steadystate_case",
                export_path=export_path,
            )
            is False
        ):
            logger.error("Steadystate Case export failed.")
            return False

        return True

    def export_data(
        self,
        data: Union[Topology, TopologyCase, SteadyStateCase],
        data_name: Optional[str],
        data_type: Literal["topology", "topology_case", "steadystate_case"],
        export_path: pathlib.Path,
    ) -> bool:
        """Export data to json file.

        Arguments:
            data {Union[Topology, TopologyCase, SteadyStateCase]} -- data to export
            data_name {Optional[str]} -- the chosen file name for data
            data_type {Literal['topology', 'topology_case', 'steadystate_case']} -- the data type
            export_path {pathlib.Path} -- the directory where the exported json file is saved

        Returns:
            bool -- success of export
        """
        time = datetime.datetime.now().isoformat(sep="T", timespec="seconds").replace(":", "")
        if data_name is None:
            filename = f"{self.grid_name}_{time}_{data_type}.json"
        else:
            filename = f"{data_name}_{data_type}.json"
        file_path = export_path / filename
        try:
            file_path.resolve()
        except OSError:
            logger.error(f"File path {file_path} is not a valid path. Please provide a valid file path.")
            return False
        return data.to_json(file_path)

    def switch_study_case(self, sc: str) -> bool:
        study_case = self.pfi.study_case(name=sc)
        if study_case is not None:
            success = self.pfi.activate_study_case(study_case)
        else:
            logger.error(f"Study case {sc} does not exist. Cancel switch of study case.")
            success = False
        return success

    def switch_scenario(self, scen: str) -> bool:
        scenario = self.pfi.scenario(name=scen)
        if scenario is not None:
            success = self.pfi.activate_scenario(scenario)
        else:
            logger.error(f"Scenario {scen} does not exist. Cancel switch of scenario.")
            success = False
        return success

    def compile_powerfactory_data(self) -> PowerfactoryData:
        if self.grid_name == "*":
            name = self.project_name
        else:
            grids = self.pfi.grids()
            try:
                g = [e for e in grids if e.loc_name == self.grid_name][0]
                name = g.loc_name
            except IndexError:
                raise RuntimeError(f"Grid {self.grid_name} does not exist.")
        project = self.pfi.project.loc_name
        date = datetime.date.today()

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
            pf_transformers_2w=data.transformers_2w, pf_transformers_3w=data.transformers_3w, grid_name=data.name
        )

        return Topology(
            meta=meta,
            nodes=nodes,
            branches=branches,
            loads=loads,
            transformers=transformers,
            external_grids=external_grids,
        )

    def create_external_grids(self, ext_grids: Sequence[pft.ExternalGrid], grid_name: str) -> Sequence[ExternalGrid]:
        grids: list[ExternalGrid] = []
        for g in ext_grids:
            name = self.pfi.create_name(g, grid_name)
            export, description = self.get_description(g)
            if not export:
                logger.warning(f"External grid {name} not set for export. Skipping.")
                continue

            if g.bus1 is None:
                logger.warning(f"External grid {name} not connected to any bus. Skipping.")
                continue

            node_name = self.pfi.create_name(g.bus1.cterm, grid_name)

            grid = ExternalGrid(
                name=name,
                description=description,
                node=node_name,
                type=GridType(g.bustp),
                short_circuit_power_max=g.snss,
                short_circuit_power_min=g.snssmin,
            )
            grids.append(grid)

        return grids

    @staticmethod
    def get_description(
        element: Union[pft.Terminal, pft.LineBase, pft.Element, pft.Coupler, pft.ExternalGrid]
    ) -> tuple[bool, str]:
        desc = element.desc
        if desc:
            if (
                desc[0] == "do_not_export"
            ):  # if description explicitly contains "do_not_export", element does not have to be considered
                return False, ""
            else:
                description = desc[0]
        else:
            description = ""
        return True, description

    def create_nodes(self, terminals: Sequence[pft.Terminal], grid_name: str) -> Sequence[Node]:
        nodes: list[Node] = []
        for t in terminals:
            export, description = self.get_description(t)
            name = self.pfi.create_name(t, grid_name)
            if not export:
                logger.warning(f"Node {name} not set for export. Skipping.")
                continue

            u_n = round(t.uknom, DecimalDigits.VOLTAGE) * Exponents.VOLTAGE  # voltage in V

            if self.pfi.is_within_substation(t):
                if description == "":
                    description = "substation internal"
                else:
                    description = "substation internal; " + description

            node = Node(name=name, u_n=u_n, description=description)
            logger.debug(f"Created node {node}")
            nodes.append(node)
        return nodes

    def create_branches(
        self, lines: Sequence[pft.Line], couplers: Sequence[pft.Coupler], grid_name: str
    ) -> Sequence[Branch]:

        branches: list[Branch] = []
        for line in lines:
            name = self.pfi.create_name(line, grid_name)
            export, description = self.get_description(line)
            if not export:
                logger.warning(f"Line {name} not set for export. Skipping.")
                continue

            if line.bus1 is None or line.bus2 is None:
                logger.warning(f"Line {name} not connected to buses on both sides. Skipping.")
                continue

            t1 = line.bus1.cterm
            t2 = line.bus2.cterm

            t1_name = self.pfi.create_name(t1, grid_name)
            t2_name = self.pfi.create_name(t2, grid_name)

            u_nom_1 = t1.uknom
            u_nom_2 = t2.uknom

            l_type = line.typ_id
            if l_type is not None:
                if round(u_nom_1, 2) == round(u_nom_2, 2):
                    u_nom = u_nom_1 * Exponents.VOLTAGE  # nominal voltage (V)
                else:
                    u_nom = l_type.uline * Exponents.VOLTAGE  # nominal voltage (V)

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
                logger.debug(f"Created line {branch}.")
                branches.append(branch)
            else:
                logger.warning(f"Type not set for line {name}. Skipping.")

        for coupler in couplers:
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

            bus1 = coupler.bus1
            bus2 = coupler.bus2
            if bus1 is None or bus2 is None:
                continue

            t1 = bus1.cterm
            t2 = bus2.cterm

            name = self.pfi.create_name(coupler, grid_name)
            export, description = self.get_description(coupler)
            if not export:
                logger.warning(f"Coupler {name} not set for export. Skipping.")
                continue
            if self.pfi.is_within_substation(t1) and self.pfi.is_within_substation(t2):
                if description == "":
                    description = "substation internal"
                else:
                    description = "substation internal; " + description

            t1_name = self.pfi.create_name(t1, grid_name)
            t2_name = self.pfi.create_name(t2, grid_name)

            u_nom_1 = t1.uknom
            u_nom_2 = t2.uknom

            if round(u_nom_1, 2) == round(u_nom_2, 2):
                u_nom = u_nom_1 * Exponents.VOLTAGE  # nominal voltage (V)
            else:
                logger.warning(f"Coupler {name} couples busbars with different voltage levels. Skipping.")
                continue

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
            logger.debug(f"Created line {branch}.")
            branches.append(branch)

        return branches

    def create_loads(
        self,
        consumers: Sequence[pft.Load],
        consumers_lv: Sequence[pft.LoadLV],
        consumers_mv: Sequence[pft.LoadMV],
        generators: Sequence[pft.Generator],
        pv_systems: Sequence[pft.PVSystem],
        grid_name: str,
    ) -> Sequence[Load]:

        normal_consumers = self.create_consumers_normal(consumers, grid_name)
        lv_consumers = self.create_consumers_lv(consumers_lv, grid_name)
        load_mvs = self.create_loads_mv(consumers_mv, grid_name)
        gen_producers = self.create_producers_normal(generators, grid_name)
        pv_producers = self.create_producers_pv(pv_systems, grid_name)
        return self.pfi.list_from_sequences(normal_consumers, lv_consumers, load_mvs, gen_producers, pv_producers)

    def create_consumers_normal(self, loads: Sequence[pft.Load], grid_name: str) -> Sequence[Load]:
        consumers: list[Load] = []
        for load in loads:
            power = self.calc_normal_load_power(load)
            if power is not None:
                consumer = self.create_consumer(load, power, grid_name)
                if consumer is not None:
                    consumers.append(consumer)
        return consumers

    def create_consumers_lv(self, loads: Sequence[pft.LoadLV], grid_name: str) -> Sequence[Load]:
        consumers: list[Load] = []
        for load in loads:
            powers = self.calc_load_lv_powers(load)
            if len(powers) == 1:
                sfx_pre = ""
            else:
                sfx_pre = "_({})"
            for i, p in enumerate(powers):
                consumer = (
                    self.create_consumer(
                        load,
                        p.fixed,
                        grid_name,
                        system_type=ConsumerSystemType.FIXED,
                        name_suffix=sfx_pre.format(i) + "_" + ConsumerSystemType.FIXED.value,
                    )
                    if p.fixed.s_abs != 0
                    else None
                )
                if consumer is not None:
                    consumers.append(consumer)
                consumer = (
                    self.create_consumer(
                        load,
                        p.night,
                        grid_name,
                        system_type=ConsumerSystemType.NIGHT_STORAGE,
                        name_suffix=sfx_pre.format(i) + "_" + ConsumerSystemType.NIGHT_STORAGE.value,
                    )
                    if p.night.s_abs != 0
                    else None
                )
                if consumer is not None:
                    consumers.append(consumer)
                consumer = (
                    self.create_consumer(
                        load,
                        p.variable,
                        grid_name,
                        system_type=ConsumerSystemType.VARIABLE,
                        name_suffix=sfx_pre.format(i) + "_" + ConsumerSystemType.VARIABLE.value,
                    )
                    if p.variable.s_abs != 0
                    else None
                )
                if consumer is not None:
                    consumers.append(consumer)
        return consumers

    def create_loads_mv(self, loads: Sequence[pft.LoadMV], grid_name: str) -> Sequence[Load]:
        _loads: list[Load] = []
        for load in loads:
            power = self.calc_load_mv_power(load)
            consumer = self.create_consumer(
                load=load, power=power.consumer, grid_name=grid_name, name_suffix="_CONSUMER"
            )
            if consumer is not None:
                _loads.append(consumer)
            producer = self.create_producer(
                gen=load, power=power.producer, gen_name=load.loc_name, grid_name=grid_name, name_suffix="_PRODUCER"
            )
            if producer is not None:
                _loads.append(producer)
        return _loads

    def calc_normal_load_power(self, load: pft.Load) -> Optional[LoadPower]:
        load_type = load.mode_inp
        scaling = load.scale0
        if not load.i_sym:
            if load_type == "DEF" or load_type == "PQ":
                power = LoadPower.from_pq_sym(p=load.plini, q=load.qlini, scaling=scaling)
            elif load_type == "PC":
                power = LoadPower.from_pc_sym(p=load.plini, cosphi=load.coslini, scaling=scaling)
            elif load_type == "IC":
                power = LoadPower.from_ic_sym(u=load.u0, i=load.ilini, cosphi=load.coslini, scaling=scaling)
            elif load_type == "SC":
                power = LoadPower.from_sc_sym(s=load.slini, cosphi=load.coslini, scaling=scaling)
            elif load_type == "QC":
                power = LoadPower.from_qc_sym(q=load.qlini, cosphi=load.coslini, scaling=scaling)
            elif load_type == "IP":
                power = LoadPower.from_ip_sym(u=load.u0, i=load.ilini, p=load.plini, scaling=scaling)
            elif load_type == "SP":
                power = LoadPower.from_sp_sym(s=load.slini, p=load.plini, scaling=scaling)
            elif load_type == "SQ":
                power = LoadPower.from_sq_sym(s=load.slini, q=load.qlini, scaling=scaling)
            else:
                raise RuntimeError("Unreachable")
        else:
            if load_type == "DEF" or load_type == "PQ":
                power = LoadPower.from_pq_asym(
                    p_r=load.plinir,
                    p_s=load.plinis,
                    p_t=load.plinit,
                    q_r=load.qlinir,
                    q_s=load.qlinis,
                    q_t=load.qlinit,
                    scaling=scaling,
                )
            elif load_type == "PC":
                power = LoadPower.from_pc_asym(
                    p_r=load.plinir,
                    p_s=load.plinis,
                    p_t=load.plinit,
                    cosphi_r=load.coslinir,
                    cosphi_s=load.coslinis,
                    cosphi_t=load.coslinit,
                    scaling=scaling,
                )
            elif load_type == "IC":
                power = LoadPower.from_ic_asym(
                    u=load.u0,
                    i_r=load.ilinir,
                    i_s=load.ilinis,
                    i_t=load.ilinit,
                    cosphi_r=load.coslinir,
                    cosphi_s=load.coslinis,
                    cosphi_t=load.coslinit,
                    scaling=scaling,
                )
            elif load_type == "SC":
                power = LoadPower.from_sc_asym(
                    s_r=load.slinir,
                    s_s=load.slinis,
                    s_t=load.slinit,
                    cosphi_r=load.coslinir,
                    cosphi_s=load.coslinis,
                    cosphi_t=load.coslinit,
                    scaling=scaling,
                )
            elif load_type == "QC":
                power = LoadPower.from_qc_asym(
                    q_r=load.qlinir,
                    q_s=load.qlinis,
                    q_t=load.qlinit,
                    cosphi_r=load.coslinir,
                    cosphi_s=load.coslinis,
                    cosphi_t=load.coslinit,
                    scaling=scaling,
                )
            elif load_type == "IP":
                power = LoadPower.from_ip_asym(
                    u=load.u0,
                    i_r=load.ilinir,
                    i_s=load.ilinis,
                    i_t=load.ilinit,
                    p_r=load.plinir,
                    p_s=load.plinis,
                    p_t=load.plinit,
                    scaling=scaling,
                )
            elif load_type == "SP":
                power = LoadPower.from_sp_asym(
                    s_r=load.slinir,
                    s_s=load.slinis,
                    s_t=load.slinit,
                    p_r=load.plinir,
                    p_s=load.plinis,
                    p_t=load.plinit,
                    scaling=scaling,
                )
            elif load_type == "SQ":
                power = LoadPower.from_sq_asym(
                    s_r=load.slinir,
                    s_s=load.slinis,
                    s_t=load.slinit,
                    q_r=load.qlinir,
                    q_s=load.qlinis,
                    q_t=load.qlinit,
                    scaling=scaling,
                )
            else:
                raise RuntimeError("Unreachable")
        if power.isempty:
            logger.warning(f"Power is not set for load {load.loc_name}. Skipping.")
            return None
        return power

    def calc_load_lv_powers(self, load: pft.LoadLV) -> Sequence[LoadLV]:
        subloads = self.pfi.subloads_of(load)
        if not subloads:
            return [self.calc_load_lv_power(load)]
        return [self.calc_load_lv_power_sym(sl) for sl in subloads]

    def calc_load_lv_power_fixed_sym(self, load: Union[pft.LoadLV, pft.LoadLVP], scaling: float) -> LoadPower:
        load_type = load.iopt_inp
        if load_type == 0:
            power_fixed = LoadPower.from_sc_sym(
                s=load.slini,
                cosphi=load.coslini,
                scaling=scaling,
            )
        elif load_type == 1:
            power_fixed = LoadPower.from_pc_sym(
                p=load.plini,
                cosphi=load.coslini,
                scaling=scaling,
            )
        elif load_type == 2:
            power_fixed = LoadPower.from_ic_sym(
                u=load.ulini,
                i=load.ilini,
                cosphi=load.coslini,
                scaling=scaling,
            )
        elif load_type == 3:
            power_fixed = LoadPower.from_pc_sym(
                p=load.cplinia,
                cosphi=load.coslini,
                scaling=scaling,
            )
        else:
            raise RuntimeError("Unreachable")
        return power_fixed

    def calc_load_lv_power_sym(self, load: pft.LoadLVP) -> LoadLV:
        power_fixed = self.calc_load_lv_power_fixed_sym(load, scaling=1)
        power_night = LoadPower.from_pq_sym(
            p=load.pnight,
            q=0,
            scaling=1,
        )
        power_variable = LoadPower.from_sc_sym(
            s=load.cSav,
            cosphi=load.ccosphi,
            scaling=1,
        )
        return LoadLV(fixed=power_fixed, night=power_night, variable=power_variable)

    def calc_load_lv_power(self, load: pft.LoadLV) -> LoadLV:
        load_type = load.iopt_inp
        scaling = load.scale0
        if not load.i_sym:
            power_fixed = self.calc_load_lv_power_fixed_sym(load, scaling)
        else:
            if load_type == 0:
                power_fixed = LoadPower.from_sc_asym(
                    s_r=load.slinir,
                    s_s=load.slinis,
                    s_t=load.slinit,
                    cosphi_r=load.coslinir,
                    cosphi_s=load.coslinis,
                    cosphi_t=load.coslinit,
                    scaling=scaling,
                )
            elif load_type == 1:
                power_fixed = LoadPower.from_pc_asym(
                    p_r=load.plinir,
                    p_s=load.plinis,
                    p_t=load.plinit,
                    cosphi_r=load.coslinir,
                    cosphi_s=load.coslinis,
                    cosphi_t=load.coslinit,
                    scaling=scaling,
                )
            elif load_type == 2:
                power_fixed = LoadPower.from_ic_asym(
                    u=load.ulini,
                    i_r=load.ilinir,
                    i_s=load.ilinis,
                    i_t=load.ilinit,
                    cosphi_r=load.coslinir,
                    cosphi_s=load.coslinis,
                    cosphi_t=load.coslinit,
                    scaling=scaling,
                )
            else:
                raise RuntimeError("Unreachable")
        power_night = LoadPower.from_pq_sym(
            p=load.pnight,
            q=0,
            scaling=1,
        )
        power_variable = LoadPower.from_sc_sym(
            s=load.cSav,
            cosphi=load.ccosphi,
            scaling=1,
        )
        return LoadLV(fixed=power_fixed, night=power_night, variable=power_variable)

    def calc_load_mv_power(self, load: pft.LoadMV) -> LoadMV:
        load_type = load.mode_inp
        scaling_cons = load.scale0
        scaling_prod = load.gscale
        if not load.ci_sym:
            if load_type == "PC":
                power_consumer = LoadPower.from_pc_sym(
                    p=load.plini,
                    cosphi=load.coslini,
                    scaling=scaling_cons,
                )
                power_producer = LoadPower.from_pc_sym(
                    p=load.pgini,
                    cosphi=load.cosgini,
                    scaling=scaling_prod,
                )
            elif load_type == "SC":
                power_consumer = LoadPower.from_sc_sym(
                    s=load.slini,
                    cosphi=load.coslini,
                    scaling=scaling_cons,
                )
                power_producer = LoadPower.from_sc_sym(
                    s=load.sgini,
                    cosphi=load.cosgini,
                    scaling=scaling_prod,
                )
            elif load_type == "EC":
                logger.warning("Power from yearly demand is not implemented yet. Skipping.")
                power_consumer = LoadPower.from_pc_sym(
                    p=load.cplinia,
                    cosphi=load.coslini,
                    scaling=scaling_cons,
                )
                power_producer = LoadPower.from_pc_sym(
                    p=load.pgini,
                    cosphi=load.cosgini,
                    scaling=scaling_prod,
                )
            else:
                raise RuntimeError("Unreachable.")
        else:
            if load_type == "PC":
                power_consumer = LoadPower.from_pc_asym(
                    p_r=load.plinir,
                    p_s=load.plinis,
                    p_t=load.plinit,
                    cosphi_r=load.coslinir,
                    cosphi_s=load.coslinis,
                    cosphi_t=load.coslinit,
                    scaling=scaling_cons,
                )
                power_producer = LoadPower.from_pc_asym(
                    p_r=load.pginir,
                    p_s=load.pginis,
                    p_t=load.pginit,
                    cosphi_r=load.cosginir,
                    cosphi_s=load.cosginis,
                    cosphi_t=load.cosginit,
                    scaling=scaling_prod,
                )
            elif load_type == "SC":
                power_consumer = LoadPower.from_sc_asym(
                    s_r=load.slinir,
                    s_s=load.slinis,
                    s_t=load.slinit,
                    cosphi_r=load.coslinir,
                    cosphi_s=load.coslinis,
                    cosphi_t=load.coslinit,
                    scaling=scaling_cons,
                )
                power_producer = LoadPower.from_sc_asym(
                    s_r=load.sginir,
                    s_s=load.sginis,
                    s_t=load.sginit,
                    cosphi_r=load.cosginir,
                    cosphi_s=load.cosginis,
                    cosphi_t=load.cosginit,
                    scaling=scaling_prod,
                )
            else:
                raise RuntimeError("Unreachable.")
        return LoadMV(consumer=power_consumer, producer=power_producer)

    @staticmethod
    def load_model_of(load: pft.LoadBase, specifier: Literal["p", "q"]) -> LoadModel:
        load_type = load.typ_id
        if load_type is not None:
            if load_type.loddy != 100:
                logger.warning(f"Please check load model setting of {load.loc_name} for RMS simulation.")
                logger.info(
                    "Consider to set 100% dynamic mode, but with time constants equal zero (=same static model for RMS)."
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
            elif specifier == "q":
                return LoadModel(
                    name=name,
                    c_p=load_type.aQ,
                    c_i=load_type.bQ,
                    exp_p=load_type.kqu0,
                    exp_i=load_type.kqu1,
                    exp_z=load_type.kqu,
                )
            else:
                raise RuntimeError("unreachable")
        else:
            return LoadModel()  # default: 100% power-const. load

    @staticmethod
    def consumer_technology_of(
        load: pft.LoadBase,
    ) -> tuple[Optional[VoltageSystemType], Optional[ConsumerPhaseConnectionType]]:

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
                    f"Wrong phase connection identifier '{load_type.phtech}'for consumer {load.loc_name}. Skipping."
                )
            return system_type, phase_con
        else:
            logger.debug(f"No load model defined for load {load.loc_name}. Skipping.")

        return None, None

    @staticmethod
    def producer_technology_of(load: pft.GeneratorBase) -> Optional[ProducerPhaseConnectionType]:

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
            logger.warning(f"Wrong phase connection identifier '{load.phtech}'for producer {load.loc_name}. Skipping.")
        return phase_con

    @staticmethod
    def producer_system_type_of(load: pft.Generator) -> Optional[ProducerSystemType]:
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
            logger.warning(f"Wrong system type identifier '{load.cCategory}'for producer {load.loc_name}. Skipping.")

        return system_type

    def create_consumer(
        self,
        load: pft.LoadBase,
        power: LoadPower,
        grid_name: str,
        system_type: Optional[ConsumerSystemType] = None,
        name_suffix: str = "",
    ) -> Optional[Load]:

        export, description = self.get_description(load)
        if not export:
            logger.warning(f"Load {load.loc_name} not set for export. Skipping.")
            return None

        bus = load.bus1
        if bus is None:
            logger.debug(f"Load {load.loc_name} not connected to any bus. Skipping.")
            return None
        t = bus.cterm
        l_name = self.pfi.create_name(load, grid_name) + name_suffix
        t_name = self.pfi.create_name(t, grid_name)

        u_n = round(t.uknom, DecimalDigits.VOLTAGE) * Exponents.VOLTAGE  # voltage in V

        rated_power = power.as_rated_power()
        logger.debug(f"{load.loc_name}: there is no real rated, but 's' is calculated on basis of actual power.")

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
        logger.debug(f"Created consumer {consumer}.")
        return consumer

    def create_producer(
        self,
        gen: Union[pft.GeneratorBase, pft.LoadMV],
        gen_name: str,
        power: LoadPower,
        grid_name: str,
        producer_system_type: Optional[ProducerSystemType] = None,
        producer_phase_connection_type: Optional[ProducerPhaseConnectionType] = None,
        external_controller_name: Optional[str] = None,
        name_suffix: str = "",
    ) -> Optional[Load]:

        # get unique name
        gen_name = self.pfi.create_name(gen, grid_name, element_name=gen_name) + name_suffix

        export, description = self.get_description(gen)
        if not export:
            logger.warning(f"Generator {gen_name} not set for export. Skipping.")
            return None

        bus = gen.bus1
        if bus is None:
            logger.warning(f"Generator {gen_name} not connected to any bus. Skipping.")
            return None
        else:
            t = bus.cterm
        t_name = self.pfi.create_name(t, grid_name)

        u_n = round(t.uknom, DecimalDigits.VOLTAGE) * Exponents.VOLTAGE

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
        logger.debug(f"Created producer {producer}.")
        return producer

    def calc_normal_gen_power(self, gen: Union[pft.Generator, pft.PVSystem]) -> LoadPower:
        s = gen.sgn * gen.ngnum
        cosphi = gen.cosn
        return LoadPower.from_sc_sym(s=s, cosphi=cosphi, scaling=gen.scale0)

    def get_external_controller_name(self, gen: Union[pft.Generator, pft.PVSystem]) -> Optional[str]:
        ext_ctrl = gen.c_pstac
        if ext_ctrl is None:
            return None
        else:
            return self.pfi.create_gen_name(gen, generator_name=ext_ctrl.loc_name)

    def create_producers_normal(
        self,
        generators: Sequence[pft.Generator],
        grid_name: str,
    ) -> Sequence[Load]:

        producers: list[Load] = []
        for gen in generators:
            gen_name = gen.loc_name
            producer_system_type = self.producer_system_type_of(gen)
            producer_phase_connection_type = self.producer_technology_of(gen)
            external_controller_name = self.get_external_controller_name(gen)
            power = self.calc_normal_gen_power(gen)
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
                producers.append(producer)
        return producers

    def create_producers_pv(
        self,
        generators: Sequence[pft.PVSystem],
        grid_name: str,
    ) -> Sequence[Load]:

        producers: list[Load] = []
        for gen in generators:
            gen_name = gen.loc_name
            producer_system_type = ProducerSystemType.PV
            producer_phase_connection_type = self.producer_technology_of(gen)
            external_controller_name = self.get_external_controller_name(gen)
            power = self.calc_normal_gen_power(gen)
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
                producers.append(producer)
        return producers

    def create_q_controller(
        self,
        gen: pft.GeneratorBase,
        gen_name: str,
        u_n: float,
        ext_ctrl: Optional[pft.StationController],
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
        m_tab2015 = None  # Q(U) droop related to VDE-AR-N 4120:2015
        m_tar2018 = None  # Q(U) droop related to VDE-AR-N 4120:2018
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
                qmax_ue = abs(gen.Qfu_min)
                qmax_oe = abs(gen.Qfu_max)
                u_q0 = gen.udeadbup - (gen.udeadbup - gen.udeadblow) / 2  # p.u.
                udeadband_low = abs(u_q0 - gen.udeadblow)  # delta in p.u.
                udeadband_up = abs(u_q0 - gen.udeadbup)  # delta in p.u.
                m_tab2015 = 100 / abs(gen.ddroop) * 100 / u_n / cosphi_r  # (% von Pr) / kV
                m_tar2018 = self.transform_qu_slope(slope=m_tab2015, given_format="2015", target_format="2018", u_n=u_n)
            elif controller_type == ControllerType.Q_P:
                logger.warning(f"Generator {gen_name}: Q(P) control is not implemented yet. Skipping.")
                # TODO: implement Q(P) control
            elif controller_type == ControllerType.COSPHI_P:
                logger.warning(f"Generator {gen_name}: cosphi(P) control is not implemented yet. Skipping.")
                # TODO: implement cosphi(P) control
                # calculation below is only brief estimation
                # qmax_ue = math.tan(math.acos(gen.pf_under)) * gen.p_under
                # qmax_oe = math.tan(math.acos(gen.pf_over)) * gen.p_over
            elif controller_type == ControllerType.U_CONST:
                logger.warning(f"Generator {gen_name}: Const. U control is not implemented yet. Skipping.")
                # TODO: implement U_CONST control
            else:
                raise RuntimeError("Unreachable")

        else:
            ext_ctrl_name = self.pfi.create_gen_name(gen, generator_name=ext_ctrl.loc_name)

            ctrl_mode = ext_ctrl.i_ctrl
            if ctrl_mode == 0:  # voltage control mode
                controller_type = ControllerType.U_CONST
            elif ctrl_mode == 1:  # reactive power control mode
                controller_type_dict_ext = {
                    0: ControllerType.Q_CONST,
                    1: ControllerType.Q_U,
                    2: ControllerType.Q_P,
                }
                controller_type = controller_type_dict_ext[ext_ctrl.qu_char]

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
                        if abs(abs(q_rated) - abs(s_r) / abs(s_r)) < 0.01:  # q_rated == s_r
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
                            # PF droop = 100%/m_tab2015 * 100*Exponents.VOLTAGE/u_nom * tan(phi)
                            # PF droop = 100%/m_tar2018 * tan(phi)

                        # in default there should q_rated=s_r, but user could enter incorrectly
                        m_tab2015 = m_tab2015 * q_rated / s_r
                        m_tar2018 = self.transform_qu_slope(
                            slope=m_tab2015, given_format="2015", target_format="2018", u_n=u_nom
                        )
                    except ZeroDivisionError:
                        m_tab2015 = float("inf")
                        m_tar2018 = float("inf")

                elif controller_type == ControllerType.Q_P:
                    logger.warning(f"Generator {gen_name}: Q(P) control is not implemented yet. Skipping.")
                    # TODO: implement Q(P) control
                    # calculation below is only brief estimation
                    # qmax_ue = abs(ctrl_ext.Qmin)
                    # qmax_oe = abs(ctrl_ext.Qmax)
                else:
                    raise RuntimeError("Unreachable")
            elif ctrl_mode == 2:  # cosphi control mode
                controller_type_dict_ext = {
                    0: ControllerType.COSPHI_CONST,
                    1: ControllerType.COSPHI_P,
                    2: ControllerType.COSPHI_U,
                }
                controller_type = controller_type_dict_ext[ext_ctrl.cosphi_char]

                if controller_type == ControllerType.COSPHI_CONST:
                    cosphi = ext_ctrl.pfsetp
                    ue = ext_ctrl.pf_recap ^ ext_ctrl.iQorient  # OE/UE XOR +Q/-Q
                    cosphi_type = CosphiDir.UE if ue else CosphiDir.OE
                elif controller_type == ControllerType.COSPHI_P:
                    logger.warning(f"Generator {gen_name}: cosphi(P) control is not implemented yet. Skipping.")
                    # TODO: implement Cosphi(P) control
                    # calculation below is only brief estimation
                    # qmax_ue = math.tan(math.acos(ctrl_ext.pf_under)) * ctrl_ext.p_under
                    # qmax_oe = math.tan(math.acos(ctrl_ext.pf_over)) * ctrl_ext.p_over
                elif controller_type == ControllerType.COSPHI_U:
                    logger.warning(f"Generator {gen_name}: cosphi(U) control is not implemented yet. Skipping.")
                    # TODO: implement Cosphi(U) control
                    # calculation below is only brief estimation
                    # qmax_ue = math.tan(math.acos(ctrl_ext.pf_under)) # todo
                    # qmax_oe = math.tan(math.acos(ctrl_ext.pf_over))  # todo
                else:
                    raise RuntimeError("Unreachable")

            elif ctrl_mode == 3:  # tanphi control mode
                controller_type = ControllerType.TANPHI_CONST
                cosphi = math.cos(math.atan(ext_ctrl.tansetp))
                cosphi_type = CosphiDir.UE if ext_ctrl.iQorient else CosphiDir.OE
            else:
                raise RuntimeError("Unreachable")

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

        controller = Controller(
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
        return controller

    @staticmethod
    def transform_qu_slope(
        slope: float, given_format: Literal["2015", "2018"], target_format: Literal["2015", "2018"], u_n: float
    ) -> float:
        """Transform slope of Q(U)-characteristic from given format type to another format type.

        Arguments:
            slope {float} -- slope of Q(U)-characteristic
            given_format {str} -- format specifier for related normative guideline (e.g. '2015' or '2018')
            target_format {str} -- format specifier for related normative guideline (e.g. '2015' or '2018')
            u_n {float} -- nominal voltage of the related controller, in V

        Returns:
            float -- transformed slope
        """
        if given_format == "2015" and target_format == "2018":
            transformed_slope = slope / (1e3 / u_n * 100)  # 2018: (% von Pr) / (p.u. von Un)
        elif given_format == "2018" and target_format == "2015":
            transformed_slope = slope * (1e3 / u_n * 100)  # 2015: (% von Pr) / kV
        else:
            raise ValueError("Wrong format as input. Valid input is '2015' and '2018'.")

        # Conversion: gen.ddroop = PF droop = 100%/m_tab2015 * 100*Exponents.VOLTAGE/u_n * 1/cosphi_r
        # Conversion: gen.ddroop = PF droop = 100%/m_tar2018 * 1/cosphi_r

        return transformed_slope

    def create_transformers(
        self,
        pf_transformers_2w: Sequence[pft.Transformer2W],
        pf_transformers_3w: Sequence[pft.Transformer3W],
        grid_name: str,
    ) -> Sequence[Transformer]:

        transformers_2w = self.create_transformers_2w(pf_transformers_2w, grid_name)
        transformers_3w = self.create_transformers_3w(pf_transformers_3w, grid_name)

        return self.pfi.list_from_sequences(transformers_2w, transformers_3w)

    @staticmethod
    def transformer_phase_technology(t_type: pft.Transformer2WType) -> Optional[TransformerPhaseTechnologyType]:
        ph_technology = None

        if t_type.nt2ph == 1:
            ph_technology = TransformerPhaseTechnologyType.SINGLE_PH_E
        elif t_type.nt2ph == 2:
            ph_technology = TransformerPhaseTechnologyType.SINGLE_PH
        elif t_type.nt2ph == 3:
            ph_technology = TransformerPhaseTechnologyType.THREE_PH

        return ph_technology

    @staticmethod
    def transformer_tap_side(t_type: pft.Transformer2WType) -> Optional[TapSide]:
        tap_side = None
        # TODO Adapt for Three Phase Trf
        if bool(t_type.itapch) is True:
            if t_type.tap_side == 0:
                tap_side = TapSide.HV
            elif t_type.tap_side == 1:
                tap_side = TapSide.LV

        return tap_side

    def create_transformers_2w(
        self,
        pf_transformers: Sequence[pft.Transformer2W],
        grid_name: str,
    ) -> Sequence[Transformer]:

        transformers: list[Transformer] = []
        for transformer in pf_transformers:
            name = self.pfi.create_name(element=transformer, grid_name=grid_name)
            export, description = self.get_description(transformer)
            if not export:
                logger.warning(f"Transformer {name} not set for export. Skipping.")
                continue

            if transformer.buslv is None or transformer.bushv is None:
                logger.warning(f"Transformer {name} not connected to buses on both sides. Skipping.")
                continue

            t_high = transformer.bushv.cterm
            t_low = transformer.buslv.cterm

            t_high_name = self.pfi.create_name(element=t_high, grid_name=grid_name)
            t_low_name = self.pfi.create_name(element=t_low, grid_name=grid_name)

            t_type = transformer.typ_id

            if t_type is not None:
                t_number = transformer.ntnum
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
                    logger.warning(f"Transformer {name} has second tap changer. Not supported so far. Skipping.")

                # Rated Voltage of the transformer windings itself (CIM: ratedU)
                u_ref_h = t_type.utrn_h
                u_ref_l = t_type.utrn_l

                # Nominal Voltage of connected nodes (CIM: BaseVoltage)
                u_nom_h = transformer.bushv.cterm.uknom
                u_nom_l = transformer.buslv.cterm.uknom

                # Rated values
                p_fe = t_type.pfe  # kW
                i_0 = t_type.curmg  # %
                s_r = t_type.strn  # MVA
                # p_cu = t_type.pcutr  # kW
                # u_k = t_type.uktr  # %

                # Create Winding Objects
                # Resulting impedance
                pu2abs = u_ref_h**2 / s_r
                r_1 = t_type.r1pu * pu2abs
                r_0 = t_type.r0pu * pu2abs
                x_1 = t_type.x1pu * pu2abs
                x_0 = t_type.x0pu * pu2abs

                # Optional
                # z_0_uk = t_type.zx0hl_n  # Magnetic: Impedance / uk0;  uk0= x_0_pu
                # r_x_0 = t_type.rtox0_n  # Magnetic: R/X
                # z_sc = u_k / 100
                # g_1 = 1 / ((u_ref_h * 1e3) ** 2 / (p_fe * 1000))
                # y_1 = i_0 / 100 * s_r / u_ref_h**2
                # b_1 = -g_1 * y_1 * math.sqrt(1 / g_1**2 - 1 / y_1**2)

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

                t = Transformer(
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
                logger.debug(f"Created transformer {t}")
                transformers.append(t)
            else:
                logger.warning(f"Type not set for transformer {name}. Skipping.")

        return transformers

    def create_transformers_3w(
        self,
        pf_transformers: Sequence[pft.Transformer3W],
        grid_name: str,
    ) -> Sequence[Transformer]:

        transformers: list[Transformer] = []
        for _ in pf_transformers:  # TODO implement
            # name = self.pfi.create_name(element=transformer, grid_name=grid_name)
            # export, description = self.get_description(transformer)
            # if not export:
            #     logger.warning(f"Transformer {name} not set for export. Skipping.")
            #     continue
            #
            # buslv = transformer.buslv
            # busmv = transformer.busmv
            # bushv = transformer.bushv
            # if any([buslv, busmv, bushv]):
            #     logger.warning(f"Transformer {name} not connected to buses on all three sides. Skipping.)
            #     continue
            pass
        return transformers

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
        # TODO: transformer_3w_power_on_states = self.create_transformer_3w_power_on_states(data.transformers_3w)
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

    def merge_power_on_states(self, power_on_states: list[ElementState]) -> list[ElementState]:
        merged_states = []
        entry_names = [entry.name for entry in power_on_states]
        for entry_name in entry_names:
            entries = [entry for entry in power_on_states if entry.name == entry_name]
            merged_states.append(self.merge_entries(entry_name, entries))

        return merged_states

    def merge_entries(self, entry_name: str, entries: list[ElementState]) -> ElementState:
        disabled = any([entry.disabled for entry in entries])
        open_switches = tuple(itertools.chain.from_iterable([entry.open_switches for entry in entries]))
        return ElementState(name=entry_name, disabled=disabled, open_switches=open_switches)

    def create_switch_states(self, switches: Sequence[pft.Switch]) -> Sequence[ElementState]:
        """Create element states for all type of elements based on if the switch is open.

        The element states contain a node reference.

        Arguments:
            switches {Sequence[pft.Switch]} -- list of PowerFactory objects of type Switch

        Returns:
            Sequence[ElementState] -- list of element states
        """

        relevancies: list[ElementState] = []
        for sw in switches:
            if not sw.isclosed:
                cub = sw.fold_id
                element = cub.obj_id
                if element is not None:
                    terminal = cub.cterm
                    node_name = self.pfi.create_name(terminal, self.grid_name)
                    element_name = self.pfi.create_name(element, self.grid_name)
                    element_state = ElementState(name=element_name, open_switches=(node_name,))
                    relevancies.append(element_state)

        return relevancies

    def create_coupler_states(self, couplers: Sequence[pft.Coupler]) -> Sequence[ElementState]:
        """Create element states for all type of elements based on if the coupler is open.

        The element states contain a node reference.

        Arguments:
            swtiches {Sequence[pft.Coupler]} -- list of PowerFactory objects of type Coupler

        Returns:
            Sequence[ElementState] -- list of element states
        """

        relevancies: list[ElementState] = []
        for c in couplers:
            if not c.isclosed:
                element_name = self.pfi.create_name(c, self.grid_name)
                element_state = ElementState(name=element_name, disabled=True)
                relevancies.append(element_state)

        return relevancies

    def create_node_power_on_states(self, terminals: Sequence[pft.Terminal]) -> Sequence[ElementState]:
        """Create element states based on if the connected nodes are out of service.

        The element states contain a node reference.

        Arguments:
            terminals {Sequence[pft.Terminal]} -- list of PowerFactory objects of type Terminal

        Returns:
            Sequence[ElementState] -- list of element states
        """

        relevancies: list[ElementState] = []
        for t in terminals:
            if t.outserv:
                node_name = self.pfi.create_name(t, self.grid_name)
                element_state = ElementState(name=node_name, disabled=True)
                relevancies.append(element_state)

        return relevancies

    def create_element_power_on_states(
        self, elements: Sequence[ElementBase | pft.Line | pft.Transformer2W]
    ) -> Sequence[ElementState]:
        """Create element states for one-sided connected elements based on if the elements are out of service.

        The element states contain no node reference.

        Arguments:
            elements {Sequence[ElementBase} -- list of one-sided connected PowerFactory objects

        Returns:
            Sequence[ElementState] -- list of element states
        """

        relevancies: list[ElementState] = []
        for e in elements:
            if e.outserv:
                e_name = self.pfi.create_name(e, self.grid_name)
                element_state = ElementState(name=e_name, disabled=True)
                relevancies.append(element_state)

        return relevancies

    def create_steadystate_case(self, meta: Meta, data: PowerfactoryData) -> SteadyStateCase:
        loads = self.create_loads_ssc_states(
            consumers=data.loads,
            consumers_lv=data.loads_lv,
            consumers_mv=data.loads_mv,
            generators=data.generators,
            pv_systems=data.pv_systems,
            grid_name=data.name,
        )
        transformers = self.create_transformers_ssc_states(
            pf_transformers_2w=data.transformers_2w,
            pf_transformers_3w=data.transformers_3w,
            grid_name=data.name,
        )
        external_grids = self.create_external_grids_ssc_states(
            ext_grids=data.external_grids,
            grid_name=data.name,
        )

        return SteadyStateCase(
            meta=meta,
            loads=loads,
            transformers=transformers,
            external_grids=external_grids,
        )

    def create_transformers_ssc_states(
        self,
        pf_transformers_2w: Sequence[pft.Transformer2W],
        pf_transformers_3w: Sequence[pft.Transformer3W],
        grid_name: str,
    ) -> Sequence[TransformerSSC]:

        transformers_2w = self.create_transformer_2w_ssc_states(pf_transformers_2w, grid_name)
        transformers_3w = self.create_transformer_3w_ssc_states(pf_transformers_3w, grid_name)

        return self.pfi.list_from_sequences(transformers_2w, transformers_3w)

    def create_transformer_2w_ssc_states(
        self,
        pf_transformers_2w: Sequence[pft.Transformer2W],
        grid_name: str,
    ) -> Sequence[TransformerSSC]:

        transformers_2w: list[TransformerSSC] = []
        for t in pf_transformers_2w:
            name = self.pfi.create_name(t, grid_name)
            export, description = self.get_description(t)
            if not export:
                logger.warning(f"Transformer {name} not set for export. Skipping.")
                continue

            # Transformer Tap Changer
            t_type = t.typ_id
            if t_type is None:
                tap_pos = None
            else:
                tap_pos = t.nntap
            transformer = TransformerSSC(name=name, tap_pos=tap_pos)
            logger.debug(f"Created steadystate for transformer_2w {transformer}.")
            transformers_2w.append(transformer)

        return transformers_2w

    def create_transformer_3w_ssc_states(
        self,
        pf_transformers_3w: Sequence[pft.Transformer3W],
        grid_name: str,
    ) -> Sequence[TransformerSSC]:

        transformers_3w: list[TransformerSSC] = []
        for _ in pf_transformers_3w:  # TODO implement
            pass
        return transformers_3w

    def create_external_grids_ssc_states(
        self,
        ext_grids: Sequence[pft.ExternalGrid],
        grid_name: str,
    ) -> Sequence[ExternalGridSSC]:

        grids: list[ExternalGridSSC] = []
        for g in ext_grids:
            name = self.pfi.create_name(g, grid_name)
            export, description = self.get_description(g)
            if not export:
                logger.warning(f"External grid {name} not set for export. Skipping.")
                continue

            if g.bus1 is None:
                logger.warning(f"External grid {name} not connected to any bus. Skipping.")
                continue

            g_type = GridType(g.bustp)
            if g_type == GridType.SL:
                grid = ExternalGridSSC(
                    name=name,
                    u_0=round(g.usetp * g.bus1.cterm.uknom * Exponents.VOLTAGE, DecimalDigits.VOLTAGE),
                    phi_0=g.phiini,
                )
            elif g_type == GridType.PV:
                grid = ExternalGridSSC(
                    name=name,
                    u_0=round(g.usetp * g.bus1.cterm.uknom * Exponents.VOLTAGE, DecimalDigits.VOLTAGE),
                    p_0=round(g.pgini * Exponents.POWER, DecimalDigits.POWER),
                )
            elif g_type == GridType.PQ:
                grid = ExternalGridSSC(
                    name=name,
                    p_0=round(g.pgini * Exponents.POWER, DecimalDigits.POWER),
                    q_0=round(g.qgini * Exponents.POWER, DecimalDigits.POWER),
                )
            else:
                grid = ExternalGridSSC(name=name)

            logger.debug(f"Created steadystate for external grid {grid}.")
            grids.append(grid)

        return grids

    def create_loads_ssc_states(
        self,
        consumers: Sequence[pft.Load],
        consumers_lv: Sequence[pft.LoadLV],
        consumers_mv: Sequence[pft.LoadMV],
        generators: Sequence[pft.Generator],
        pv_systems: Sequence[pft.PVSystem],
        grid_name: str,
    ) -> Sequence[LoadSSC]:

        normal_consumers = self.create_consumer_ssc_states_normal(consumers, grid_name)
        lv_consumers = self.create_consumer_ssc_states_lv(consumers_lv, grid_name)
        mv_consumers = self.create_load_ssc_states_mv(consumers_mv, grid_name)
        gen_producers = self.create_producers_ssc_states(generators)
        pv_producers = self.create_producers_ssc_states(pv_systems)
        return self.pfi.list_from_sequences(normal_consumers, lv_consumers, mv_consumers, gen_producers, pv_producers)

    def create_consumer_ssc_states_normal(
        self,
        loads: Sequence[pft.Load],
        grid_name: str,
    ) -> Sequence[LoadSSC]:

        consumers_ssc: list[LoadSSC] = []
        for load in loads:
            power = self.calc_normal_load_power(load)
            if power is not None:
                consumer = self.create_consumer_ssc_state(load, power, grid_name)
                if consumer is not None:
                    consumers_ssc.append(consumer)
        return consumers_ssc

    def create_consumer_ssc_states_lv(
        self,
        loads: Sequence[pft.LoadLV],
        grid_name: str,
    ) -> Sequence[LoadSSC]:

        consumers_ssc: list[LoadSSC] = []
        for load in loads:
            powers = self.calc_load_lv_powers(load)
            if len(powers) == 1:
                sfx_pre = ""
            else:
                sfx_pre = "_({})"
            for i, p in enumerate(powers):
                consumer = (
                    self.create_consumer_ssc_state(
                        load,
                        p.fixed,
                        grid_name,
                        name_suffix=sfx_pre.format(i) + "_" + ConsumerSystemType.FIXED.value,
                    )
                    if p.fixed.s_abs != 0
                    else None
                )
                if consumer is not None:
                    consumers_ssc.append(consumer)
                consumer = (
                    self.create_consumer_ssc_state(
                        load,
                        p.night,
                        grid_name,
                        name_suffix=sfx_pre.format(i) + "_" + ConsumerSystemType.NIGHT_STORAGE.value,
                    )
                    if p.night.s_abs != 0
                    else None
                )
                if consumer is not None:
                    consumers_ssc.append(consumer)
                consumer = (
                    self.create_consumer_ssc_state(
                        load,
                        p.variable,
                        grid_name,
                        name_suffix=sfx_pre.format(i) + "_" + ConsumerSystemType.VARIABLE.value,
                    )
                    if p.variable.s_abs != 0
                    else None
                )
                if consumer is not None:
                    consumers_ssc.append(consumer)
        return consumers_ssc

    def create_load_ssc_states_mv(
        self,
        loads: Sequence[pft.LoadMV],
        grid_name: str,
    ) -> Sequence[LoadSSC]:

        loads_ssc: list[LoadSSC] = []
        for load in loads:
            power = self.calc_load_mv_power(load)
            consumer = self.create_consumer_ssc_state(load, power.consumer, grid_name, name_suffix="_CONSUMER")
            if consumer is not None:
                loads_ssc.append(consumer)
            producer = self.create_consumer_ssc_state(load, power.producer, grid_name, name_suffix="_PRODUCER")
            if producer is not None:
                loads_ssc.append(producer)
        return loads_ssc

    def create_consumer_ssc_state(
        self,
        load: pft.LoadBase,
        power: LoadPower,
        grid_name: str,
        name_suffix: str = "",
    ) -> Optional[LoadSSC]:

        name = self.pfi.create_name(load, grid_name) + name_suffix
        export, _ = self.get_description(load)
        if not export:
            logger.warning(f"External grid {name} not set for export. Skipping.")
            return None

        active_power = power.as_active_power_ssc()
        reactive_power = power.as_reactive_power_ssc()

        consumer = LoadSSC(
            name=name,
            active_power=active_power,
            reactive_power=reactive_power,
        )
        logger.debug(f"Created steadystate for consumer {consumer}.")
        return consumer

    def create_producers_ssc_states(
        self,
        generators: Sequence[pft.GeneratorBase],
    ) -> Sequence[LoadSSC]:

        producers_ssc: list[LoadSSC] = []
        for gen in generators:

            gen_name = self.pfi.create_gen_name(gen)

            export, _ = self.get_description(gen)
            if not export:
                logger.warning(f"Generator {gen_name} not set for export. Skipping.")
                continue

            bus = gen.bus1
            if bus is None:
                logger.warning(f"Generator {gen_name} not connected to any bus. Skipping.")
                continue
            else:
                t = bus.cterm
            u_n = round(t.uknom, DecimalDigits.VOLTAGE) * Exponents.VOLTAGE

            power = LoadPower.from_pq_sym(p=gen.pgini_a * gen.ngnum, q=gen.qgini_a * gen.ngnum, scaling=gen.scale0_a)

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
            logger.debug(f"Created steadystate for producer {producer}.")
            producers_ssc.append(producer)

        return producers_ssc


def export_powerfactory_data(
    export_path: pathlib.Path,
    project_name: str,
    grid_name: str,
    powerfactory_user_profile: str = "",
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH,
    powerfactory_version: str = POWERFACTORY_VERSION,
    topology_name: Optional[str] = None,
    topology_case_name: Optional[str] = None,
    steadystate_case_name: Optional[str] = None,
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
