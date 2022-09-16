from __future__ import annotations

import datetime
import math
import multiprocessing
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from powerfactory_utils.interface import PATH_SEP
from powerfactory_utils.interface import PowerfactoryInterface
from powerfactory_utils.schema.base import Meta
from powerfactory_utils.schema.base import VoltageSystemType
from powerfactory_utils.schema.steadystate_case.active_power import ActivePower as ActivePowerSSC
from powerfactory_utils.schema.steadystate_case.case import Case as SteadyStateCase
from powerfactory_utils.schema.steadystate_case.controller import Controller
from powerfactory_utils.schema.steadystate_case.controller import ControllerType
from powerfactory_utils.schema.steadystate_case.controller import CosphiDir
from powerfactory_utils.schema.steadystate_case.external_grid import ExternalGrid as ExternalGridSSC
from powerfactory_utils.schema.steadystate_case.load import Load as LoadSSC
from powerfactory_utils.schema.steadystate_case.reactive_power import ReactivePower as ReactivePowerSSC
from powerfactory_utils.schema.steadystate_case.transformer import Transformer as TransformerSSC
from powerfactory_utils.schema.topology.active_power import ActivePower
from powerfactory_utils.schema.topology.branch import Branch
from powerfactory_utils.schema.topology.branch import BranchType
from powerfactory_utils.schema.topology.external_grid import ExternalGrid
from powerfactory_utils.schema.topology.external_grid import GridType
from powerfactory_utils.schema.topology.load import ConsumerPhaseConnectionType
from powerfactory_utils.schema.topology.load import Load
from powerfactory_utils.schema.topology.load import LoadType
from powerfactory_utils.schema.topology.load import ProducerPhaseConnectionType
from powerfactory_utils.schema.topology.load import ProducerSystemType
from powerfactory_utils.schema.topology.load import RatedPower
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
    from typing import Literal
    from typing import Optional
    from typing import Sequence
    from typing import Union

    from powerfactory_utils import powerfactory_types as pft

    ElementBase = Union[pft.GeneratorBase, pft.LoadBase]


POWERFACTORY_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
POWERFACTORY_VERSION = "2021 SP5"

VOLTAGE_EXPONENT = 10**3
CURRENT_EXPONENT = 10**3
RESISTANCE_EXPONENT = 1
REACTANCE_EXPONENT = 1
SUSCEPTANCE_EXPONENT = 10**-6
CONDUCTANCE_EXPONENT = 10**-6
POWER_EXPONENT = 10**6
COSPHI_DECIMAL_DIGITS = 6
VOLTAGE_DECIMAL_DIGITS = 3
PU_DECIMAL_DIGITS = 4


@dataclass
class LoadPower:
    s_r: float
    p: float
    q: float
    cosphi: float

    def __add__(self, other: "LoadPower") -> "LoadPower":
        p = self.p + other.p
        q = self.q + other.q
        return PowerfactoryExporter.calc_pq(p=p, q=q, scaling=1)

    def __sub__(self, other: "LoadPower") -> "LoadPower":
        p = self.p - other.p
        q = self.q - other.q
        return PowerfactoryExporter.calc_pq(p=p, q=q, scaling=1)

    @property
    def isempty(self) -> bool:
        return self.s_r == 0


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
        grid_name: str = "*",
        powerfactory_user_profile: str = "*",
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
    grid_name: str = "*"
    powerfactory_user_profile: str = "*"
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH
    powerfactory_version: str = POWERFACTORY_VERSION

    def __post_init__(self) -> None:
        self.pfi = PowerfactoryInterface(
            project_name=self.project_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_path=self.powerfactory_path,
            powerfactory_version=self.powerfactory_version,
        )

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

        t_success = self.export_topology(meta=meta, data=data, filepath=export_path, topology_name=topology_name)
        tc_success = self.export_topology_case(
            meta=meta, data=data, filepath=export_path, topology_case_name=topology_case_name
        )
        ssc_success = self.export_steadystate_case(
            meta=meta, data=data, filepath=export_path, steadystate_case_name=steadystate_case_name
        )

        if not all((t_success, tc_success, ssc_success)):
            return False
        return True

    def export_scenario(
        self,
        export_path: pathlib.Path,
        scenario_name: str,
        topology_case_name: Optional[str] = None,
        steadystate_case_name: Optional[str] = None,
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

        Returns:
            bool -- success of export
        """

        s_success = self.switch_scenario(scenario_name)

        data = self.compile_powerfactory_data()
        meta = self.create_meta_data(data=data)

        tc_success = self.export_topology_case(
            meta=meta, data=data, filepath=export_path, topology_case_name=topology_case_name
        )
        ssc_success = self.export_steadystate_case(
            meta=meta, data=data, filepath=export_path, steadystate_case_name=steadystate_case_name
        )

        if not all((s_success, tc_success, ssc_success)):
            return False
        return True

    def export_topology(
        self,
        meta: Meta,
        data: PowerfactoryData,
        filepath: pathlib.Path,
        topology_name: Optional[str] = None,
    ) -> bool:
        """Export grid topology to json files.

        Based on the class arguments of PowerFactoryExporter a grid, given in DIgSILENT PowerFactory, is exported to
        json file with given schema. From the whole grid data only topology (raw assets) is exported.

        Arguments:
            meta {Meta} -- metadata which uniquely identifies the grid
            data {PowerfactoryData} -- raw data complied from PowerFactory
            filepath {pathlib.Path} -- the directory where the exported json files are saved
            topology_name {str} -- the chosen file name for 'topology' data

        Returns:
        bool -- success of export
        """

        topology = self.create_topology(meta=meta, data=data)

        time = datetime.datetime.now().isoformat(sep="T", timespec="seconds").replace(":", "")
        if topology_name is None:
            topo_name = f"{self.grid_name}_{time}_topology.json"
        else:
            topo_name = f"{topology_name}_topology.json"
        success = topology.to_json(filepath / topo_name)
        if not success:
            return False
        return True

    def export_topology_case(
        self,
        meta: Meta,
        data: PowerfactoryData,
        filepath: pathlib.Path,
        topology_case_name: Optional[str] = None,
    ) -> bool:
        """Export grid topology_case to json files.

        Based on the class arguments of PowerFactoryExporter a grid, given in DIgSILENT PowerFactory, is exported to
        json file with given schema. From the whole grid data only topology_case (binary switching info and out of
        service info) is exported.

        Arguments:
            meta {Meta} -- metadata which uniquely identifies the grid
            data {PowerfactoryData} -- raw data complied from PowerFactory
            filepath {pathlib.Path} -- the directory where the exported json files are saved
            topology_case_name {str} -- the chosen file name for 'topology_case' data

        Returns:
            bool -- success of export
        """
        topology_case = self.create_topology_case(meta=meta, data=data)

        time = datetime.datetime.now().isoformat(sep="T", timespec="seconds").replace(":", "")
        if topology_case_name is None:
            topo_case_name = f"{self.grid_name}_{time}_topology_case.json"
        else:
            topo_case_name = f"{topology_case_name}_topology_case.json"
        success = topology_case.to_json(filepath / topo_case_name)
        if not success:
            return False
        return True

    def export_steadystate_case(
        self,
        meta: Meta,
        data: PowerfactoryData,
        filepath: pathlib.Path,
        steadystate_case_name: Optional[str] = None,
    ) -> bool:
        """Export grid steadystate_case to json files.

        Based on the class arguments of PowerFactoryExporter a grid, given in DIgSILENT PowerFactory, is exported to
        json file with given schema. From the whole grid data only steadystate_case (operation points) is exported.

        Arguments:
            meta {Meta} -- metadata which uniquely identifies the grid
            data {PowerfactoryData} -- raw data complied from PowerFactory
            filepath {pathlib.Path} -- the directory where the exported json files are saved
            steadystate_case_name {str} -- the chosen file name for 'steadystate_case' data

        Returns:
            bool -- success of export
        """

        steadystate_case = self.create_steadystate_case(meta=meta, data=data)

        time = datetime.datetime.now().isoformat(sep="T", timespec="seconds").replace(":", "")
        if steadystate_case_name is None:
            ssc_name = f"{self.grid_name}_{time}_steadystate_case.json"
        else:
            ssc_name = f"{steadystate_case_name}_steadystate_case.json"
        success = steadystate_case.to_json(filepath / ssc_name)
        if not success:
            return False
        return True

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

            u_n = round(t.uknom, VOLTAGE_DECIMAL_DIGITS) * VOLTAGE_EXPONENT  # voltage in V

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
                    u_nom = u_nom_1 * VOLTAGE_EXPONENT  # nominal voltage (V)
                else:
                    u_nom = l_type.uline * VOLTAGE_EXPONENT  # nominal voltage (V)

                i = l_type.InomAir if line.inAir else l_type.sline
                i_r = line.nlnum * line.fline * i  # rated current (A)

                r1 = l_type.rline * line.dline * RESISTANCE_EXPONENT
                x1 = l_type.xline * line.dline * REACTANCE_EXPONENT
                r0 = l_type.rline0 * line.dline * RESISTANCE_EXPONENT
                x0 = l_type.xline0 * line.dline * REACTANCE_EXPONENT
                g1 = l_type.gline * line.dline * CONDUCTANCE_EXPONENT
                b1 = l_type.bline * line.dline * SUSCEPTANCE_EXPONENT
                g0 = l_type.gline0 * line.dline * CONDUCTANCE_EXPONENT
                b0 = l_type.bline0 * line.dline * SUSCEPTANCE_EXPONENT

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

            # it is assumed that only Coupler have connected buses in any case
            t1 = coupler.bus1.cterm
            t2 = coupler.bus2.cterm

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
                u_nom = u_nom_1 * VOLTAGE_EXPONENT  # nominal voltage (V)
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
        mv_consumers = self.create_consumers_mv(consumers_mv, grid_name)
        gen_producers = self.create_producers_normal(generators, grid_name)
        pv_producers = self.create_producers_pv(pv_systems, grid_name)
        return self.pfi.list_from_sequences(normal_consumers, lv_consumers, mv_consumers, gen_producers, pv_producers)

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
            power = self.calc_lv_load_power(load)
            if power is not None:
                consumer = self.create_consumer(load, power, grid_name)
                if consumer is not None:
                    consumers.append(consumer)
        return consumers

    def create_consumers_mv(self, loads: Sequence[pft.LoadMV], grid_name: str) -> Sequence[Load]:
        consumers: list[Load] = []
        for load in loads:
            power = self.calc_mv_load_power(load)
            if power is not None:
                consumer = self.create_consumer(load, power, grid_name)
                if consumer is not None:
                    consumers.append(consumer)
        return consumers

    def calc_normal_load_power(self, load: pft.Load) -> Optional[LoadPower]:
        load_type = load.mode_inp
        scaling = load.scale0
        if not load.i_sym:
            if load_type == "DEF" or load_type == "PQ":
                power = self.calc_pq(p=load.plini, q=load.qlini, scaling=scaling)
            elif load_type == "PC":
                power = self.calc_pc(p=load.plini, cosphi=load.coslini, scaling=scaling)
            elif load_type == "IC":
                power = self.calc_ic(u=load.u0, i=load.ilini, cosphi=load.coslini, scaling=scaling)
            elif load_type == "SC":
                power = self.calc_sc(s_r=load.slini, cosphi=load.coslini, scaling=scaling)
            elif load_type == "QC":
                power = self.calc_qc(q=load.qlini, cosphi=load.coslini, scaling=scaling)
            elif load_type == "IP":
                power = self.calc_ip(u=load.u0, i=load.ilini, p=load.plini, scaling=scaling)
            elif load_type == "SP":
                power = self.calc_sp(s_r=load.slini, p=load.plini, scaling=scaling)
            elif load_type == "SQ":
                power = self.calc_sq(s_r=load.slini, q=load.qlini, scaling=scaling)
            else:
                raise RuntimeError("Unreachable")
        else:
            # TODO asymmetrische Lasten
            logger.warning(f"Load {load.loc_name}: Asymmetric loads are not implemented yet. Skipping.")
            return None
        if power.isempty:
            logger.warning(f"Power is not set for load {load.loc_name}. Skipping.")
            return None
        return power

    def calc_lv_load_power(self, load: pft.LoadLV) -> Optional[LoadPower]:
        load_type = load.iopt_inp
        scaling = load.scale0
        if not load.i_sym:
            if load_type == 0:
                power = self.calc_sc(s_r=load.slini, cosphi=load.coslini, scaling=scaling)
            elif load_type == 1:
                power = self.calc_pc(p=load.plini, cosphi=load.coslini, scaling=scaling)
            elif load_type == 2:
                power = self.calc_ic(u=load.ulini, i=load.ilini, cosphi=load.coslini, scaling=scaling)
            elif load_type == 3:
                logger.warning(f"Load {load.loc_name}: Power from yearly demand is not implemented yet. Skipping.")
                # TODO: Leistung nach Jahresverbrauch
                return None
            else:
                raise RuntimeError("Unreachable")
        else:
            # TODO asymmetrische Lasten
            logger.warning(f"Load {load.loc_name}: Asymmetric loads are not implemented yet. Skipping.")
            return None
        power_night = self.calc_pq(p=load.pnight, q=0, scaling=scaling)
        # TODO: Vielleicht zwei separate Load erzeugen?
        power = power + power_night  # TODO: Variable Last (Wohneinheiten etc.)
        if power.isempty:
            logger.warning(f"Power is not set for load {load.loc_name}. Skipping.")
            return None
        return power

    def calc_mv_load_power(self, load: pft.LoadMV) -> Optional[LoadPower]:
        load_type = load.mode_inp
        scaling_load = load.scale0
        scaling_gen = load.gscale
        if not load.ci_sym:
            if load_type == "PC":
                power_load = self.calc_pc(p=load.plini, cosphi=load.coslini, scaling=scaling_load)
                power_gen = self.calc_pc(p=load.pgini, cosphi=load.cosgini, scaling=scaling_gen)
            elif load_type == "SC":
                power_load = self.calc_sc(s_r=load.slini, cosphi=load.coslini, scaling=scaling_load)
                power_gen = self.calc_sc(s_r=load.sgini, cosphi=load.cosgini, scaling=scaling_gen)
            elif load_type == "EC":
                logger.warning("Power from yearly demand is not implemented yet. Skipping.")
                return None  # TODO: Leistung nach Jahresverbrauch
            else:
                raise RuntimeError("Unreachable.")
        else:
            # TODO: asymmetrische Lasten
            logger.warning(f"Load {load.loc_name}: Asymmetric loads are not implemented yet. Skipping.")
            return None
        # TODO: Vielleicht zwei separate Load erzeugen?
        power = power_load - power_gen
        if power.isempty:
            logger.warning(f"Power is not set for load {load.loc_name}. Skipping.")
            return None
        return power

    @staticmethod
    def calc_pq(p: float, q: float, scaling: float) -> LoadPower:
        p = p * scaling * POWER_EXPONENT
        q = q * scaling * POWER_EXPONENT
        s_r = math.sqrt(p**2 + q**2)
        cosphi = p / s_r
        return LoadPower(s_r=s_r, p=p, q=q, cosphi=cosphi)

    @staticmethod
    def calc_pc(p: float, cosphi: float, scaling: float) -> LoadPower:
        p = p * scaling * POWER_EXPONENT
        cosphi = cosphi
        s_r = p / cosphi
        q = math.sqrt(s_r**2 - p**2)
        return LoadPower(s_r=s_r, p=p, q=q, cosphi=cosphi)

    @staticmethod
    def calc_ic(u: float, i: float, cosphi: float, scaling: float) -> LoadPower:
        s_r = u * i * scaling * POWER_EXPONENT
        p = s_r * cosphi
        q = math.sqrt(s_r**2 - p**2)
        return LoadPower(s_r=s_r, p=p, q=q, cosphi=cosphi)

    @staticmethod
    def calc_sc(s_r: float, cosphi: float, scaling: float) -> LoadPower:
        s_r = s_r * scaling * POWER_EXPONENT
        p = s_r * cosphi
        q = math.sqrt(s_r**2 - p**2)
        return LoadPower(s_r=s_r, p=p, q=q, cosphi=cosphi)

    @staticmethod
    def calc_qc(q: float, cosphi: float, scaling: float) -> LoadPower:
        q = q * scaling * POWER_EXPONENT
        s_r = q / math.sin(math.acos(cosphi))
        p = s_r * cosphi
        return LoadPower(s_r=s_r, p=p, q=q, cosphi=cosphi)

    @staticmethod
    def calc_ip(u: float, i: float, p: float, scaling: float) -> LoadPower:
        p = p * scaling * POWER_EXPONENT
        s_r = u * i * scaling * POWER_EXPONENT
        cosphi = s_r / p
        q = math.sqrt(s_r**2 - p**2)
        return LoadPower(s_r=s_r, p=p, q=q, cosphi=cosphi)

    @staticmethod
    def calc_sp(s_r: float, p: float, scaling: float) -> LoadPower:
        s_r = s_r * scaling * POWER_EXPONENT
        p = p * scaling * POWER_EXPONENT
        cosphi = s_r / p
        q = math.sqrt(s_r**2 - p**2)
        return LoadPower(s_r=s_r, p=p, q=q, cosphi=cosphi)

    @staticmethod
    def calc_sq(s_r: float, q: float, scaling: float) -> LoadPower:
        s_r = s_r * scaling * POWER_EXPONENT
        q = q * scaling * POWER_EXPONENT
        p = math.sqrt(s_r**2 - q**2)
        cosphi = s_r / p
        return LoadPower(s_r=s_r, p=p, q=q, cosphi=cosphi)

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
        l_name = self.pfi.create_name(load, grid_name)
        t_name = self.pfi.create_name(t, grid_name)

        u_n = round(t.uknom, VOLTAGE_DECIMAL_DIGITS) * VOLTAGE_EXPONENT  # voltage in V

        rated_power = RatedPower(s_r=power.s_r, cosphi_r=None)
        logger.debug(f"{load.loc_name}: there is no real rated, but s_r is calculated on basis of actual power.")

        load_model_p = self.load_model_of(load, specifier="p")
        active_power = ActivePower(load_model=load_model_p)

        load_model_q = self.load_model_of(load, specifier="q")
        reactive_power = ReactivePower(load_model=load_model_q)

        u_sys_type, ph_con = self.consumer_technology_of(load)

        consumer = Load(
            name=l_name,
            node=t_name,
            description=description,
            u_n=u_n,
            rated_power=rated_power,
            active_power=active_power,
            reactive_power=reactive_power,
            type=LoadType.CONSUMER,
            voltage_system_type=u_sys_type,
            phase_connection_type=ph_con,
        )
        logger.debug(f"Created consumer {consumer}.")
        return consumer

    def create_producer(
        self,
        gen: pft.GeneratorBase,
        grid_name: str,
        producer_system_type: Optional[ProducerSystemType] = None,
    ) -> Optional[Load]:

        if gen.c_pmod is None:  # if generator is not part of higher model
            gen_name = gen.loc_name
        else:
            gen_name = gen.c_pmod.loc_name + PATH_SEP + gen.loc_name

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

        u_n = round(t.uknom, VOLTAGE_DECIMAL_DIGITS) * VOLTAGE_EXPONENT
        gen_num = gen.ngnum
        scaling = gen.scale0

        # Rated Values of single unit
        s_r = gen.sgn
        cosphi_r = gen.cosn
        rated_power = RatedPower(
            s_r=round(s_r * POWER_EXPONENT * gen_num * scaling),
            cosphi_r=round(cosphi_r, COSPHI_DECIMAL_DIGITS),
        )

        # External Controller
        ext_ctrl = gen.c_pstac
        if ext_ctrl is None:
            ext_ctrl_name = None
        else:
            # if gen.c_pmod is not None then external controller is part of compound model
            ext_ctrl_name = (
                ext_ctrl.loc_name if gen.c_pmod is None else gen.c_pmod.loc_name + PATH_SEP + ext_ctrl.loc_name
            )
        reactive_power = ReactivePower(external_controller_name=ext_ctrl_name)

        ph_con = self.producer_technology_of(gen)

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
            phase_connection_type=ph_con,
        )
        logger.debug(f"Created producer {producer}.")
        return producer

    def create_producers_normal(
        self,
        generators: Sequence[pft.Generator],
        grid_name: str,
    ) -> Sequence[Load]:

        producers: list[Load] = []
        for gen in generators:
            producer_system_type = self.producer_system_type_of(gen)
            producer = self.create_producer(gen, grid_name, producer_system_type=producer_system_type)
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
            producer_system_type = ProducerSystemType.PV
            producer = self.create_producer(gen, grid_name, producer_system_type=producer_system_type)
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
        p_r = s_r * cosphi_r
        # q_r = s_r * math.sin(math.acos(cosphi_r))

        cosphi_type = None
        cosphi = None
        q_set = None
        m_tab2015 = None  # Q(U) droop related to VDE-AR-N 4120:2015
        m_tar2018 = None  # Q(U) droop related to VDE-AR-N 4120:2018
        qmax_ue = math.tan(math.acos(cosphi_r))  # q_r / p_r  default
        qmax_oe = qmax_ue
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
                qmax_ue = abs(gen.Qfu_min / p_r)  # p.u.
                qmax_oe = abs(gen.Qfu_max / p_r)  # p.u.
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
                # qmax_ue = math.tan(math.acos(gen.pf_under)) * gen.p_under / s_r  # p.u.
                # qmax_oe = math.tan(math.acos(gen.pf_over)) * gen.p_over / s_r    # p.u.
            elif controller_type == ControllerType.U_CONST:
                logger.warning(f"Generator {gen_name}: Const. U control is not implemented yet. Skipping.")
                # TODO: implement U_CONST control
            else:
                raise RuntimeError("Unreachable")

        else:
            # if gen.c_pmod is not None then external controller is part of compound model
            ext_ctrl_name = (
                ext_ctrl.loc_name if gen.c_pmod is None else gen.c_pmod.loc_name + PATH_SEP + ext_ctrl.loc_name
            )

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
                    u_nom = round(ext_ctrl.refbar.uknom, VOLTAGE_DECIMAL_DIGITS) * VOLTAGE_EXPONENT  # voltage in V

                    qmax_ue = abs(ext_ctrl.Qmin / p_r)  # per unit
                    qmax_oe = abs(ext_ctrl.Qmax / p_r)  # per unit
                    u_q0 = ext_ctrl.udeadbup - (ext_ctrl.udeadbup - ext_ctrl.udeadblow) / 2  # per unit
                    udeadband_low = abs(u_q0 - ext_ctrl.udeadblow)  # delta in per unit
                    udeadband_up = abs(u_q0 - ext_ctrl.udeadbup)  # delta in per unit

                    q_rated = ext_ctrl.Srated
                    try:
                        if abs(abs(q_rated) - abs(s_r) / abs(s_r)) < 0.01:  # q_rated == s_r
                            m_tab2015 = 100 / ext_ctrl.ddroop * 100 * VOLTAGE_EXPONENT / u_nom / cosphi_r
                        else:
                            m_tab2015 = (
                                100
                                / abs(ext_ctrl.ddroop)
                                * 100
                                * VOLTAGE_EXPONENT
                                / u_nom
                                * math.tan(math.acos(cosphi_r))
                            )
                            # PF droop = 100%/m_tab2015 * 100*VOLTAGE_EXPONENT/u_nom * tan(phi)
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
                    # qmax_ue = ctrl_ext.Qmin / p_r  # per unit
                    # qmax_oe = ctrl_ext.Qmax / p_r  # per unit
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
                    # qmax_ue = math.tan(math.acos(ctrl_ext.pf_under)) * ctrl_ext.p_under / s_r  # per unit
                    # qmax_oe = math.tan(math.acos(ctrl_ext.pf_over)) * ctrl_ext.p_over / s_r    # per unit
                elif controller_type == ControllerType.COSPHI_U:
                    logger.warning(f"Generator {gen_name}: cosphi(U) control is not implemented yet. Skipping.")
                    # TODO: implement Cosphi(U) control
                    # calculation below is only brief estimation
                    # qmax_ue = math.tan(math.acos(ctrl_ext.pf_under))  # per unit
                    # qmax_oe = math.tan(math.acos(ctrl_ext.pf_over))  # per unit
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
            cosphi = round(cosphi, COSPHI_DECIMAL_DIGITS)
        if q_set:
            q_set = round(q_set * POWER_EXPONENT * gen.ngnum)
        if m_tab2015:
            m_tab2015 = round(m_tab2015, PU_DECIMAL_DIGITS)
        if m_tar2018:
            m_tar2018 = round(m_tar2018, PU_DECIMAL_DIGITS)
        if u_q0:
            u_q0 = round(u_q0, VOLTAGE_DECIMAL_DIGITS)
        if udeadband_up:
            udeadband_up = round(udeadband_up, VOLTAGE_DECIMAL_DIGITS)
        if udeadband_low:
            udeadband_low = round(udeadband_low, VOLTAGE_DECIMAL_DIGITS)

        controller = Controller(
            controller_type=controller_type,
            external_controller_name=ext_ctrl_name,
            cosphi_type=cosphi_type,
            cosphi=cosphi,
            q_set=q_set,
            m_tab2015=m_tab2015,
            m_tar2018=m_tar2018,
            qmax_ue=round(qmax_ue, PU_DECIMAL_DIGITS),
            qmax_oe=round(qmax_oe, PU_DECIMAL_DIGITS),
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

        # Conversion: gen.ddroop = PF droop = 100%/m_tab2015 * 100*VOLTAGE_EXPONENT/u_n * 1/cosphi_r
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

            t_low = transformer.buslv.cterm
            t_high = transformer.bushv.cterm

            t_low_name = self.pfi.create_name(element=t_low, grid_name=grid_name)
            t_high_name = self.pfi.create_name(element=t_high, grid_name=grid_name)

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
                u_ref_l = t_type.utrn_l
                u_ref_h = t_type.utrn_h

                # Nominal Voltage of connected nodes (CIM: BaseVoltage)
                u_nom_l = transformer.buslv.cterm.uknom
                u_nom_h = transformer.bushv.cterm.uknom

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
                vector_l = t_type.tr2cn_l  # Wiring LV
                vector_h = t_type.tr2cn_h  # Wiring HV
                vector_phase_angle_clock = t_type.nt2ag

                wh = Winding(
                    node=t_high_name,
                    s_r=s_r * POWER_EXPONENT,
                    u_r=u_ref_h * VOLTAGE_EXPONENT,
                    u_n=u_nom_h * VOLTAGE_EXPONENT,
                    r1=r_1,
                    r0=r_0,
                    x1=x_1,
                    x0=x_0,
                    vector_group=vector_h,
                    phase_angle_clock=0,
                )

                wl = Winding(
                    node=t_low_name,
                    s_r=s_r * POWER_EXPONENT,
                    u_r=u_ref_l * VOLTAGE_EXPONENT,
                    u_n=u_nom_l * VOLTAGE_EXPONENT,
                    r1=float(0),
                    r0=float(0),
                    x1=float(0),
                    x0=float(0),
                    vector_group=vector_l,
                    phase_angle_clock=int(vector_phase_angle_clock),
                )

                t = Transformer(
                    node_1=t_low_name,
                    node_2=t_high_name,
                    name=name,
                    number=t_number,
                    i_0=i_0,
                    p_fe=p_fe * 1e3,
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
        )
        node_power_on_states = self.create_node_power_on_states(
            data.terminals,
            data.lines,
            data.transformers_2w,
            elements,
        )
        line_power_on_states = self.create_line_power_on_states(data.lines)
        transformer_2w_power_on_states = self.create_transformer_2w_power_on_states(data.transformers_2w)
        # TODO: transformer_3w_power_on_states = self.create_transformer_3w_power_on_states(data.transformers_3w)
        element_power_on_states = self.create_element_power_on_states(elements)

        return TopologyCase(
            meta=meta,
            elements=self.pfi.list_from_sequences(
                switch_states,
                coupler_states,
                node_power_on_states,
                line_power_on_states,
                transformer_2w_power_on_states,
                element_power_on_states,
            ),
        )

    def create_switch_states(self, switches: Sequence[pft.Switch]) -> Sequence[ElementState]:

        relevancies: list[ElementState] = []
        for sw in switches:
            if not sw.isclosed:
                cub = sw.fold_id
                element = cub.obj_id
                if element is not None:
                    terminal = cub.cterm
                    node_name = self.pfi.create_name(terminal, self.grid_name)
                    element_name = self.pfi.create_name(element, self.grid_name)
                    element_state = ElementState(name=element_name, node=node_name, active=False)
                    relevancies.append(element_state)

        return relevancies

    def create_coupler_states(self, couplers: Sequence[pft.Coupler]) -> Sequence[ElementState]:

        relevancies: list[ElementState] = []
        for c in couplers:
            if not c.isclosed:
                element_name = self.pfi.create_name(c, self.grid_name)
                element_state = ElementState(name=element_name, active=False)
                relevancies.append(element_state)

        return relevancies

    def create_node_power_on_states(
        self,
        terminals: Sequence[pft.Terminal],
        lines: Sequence[pft.Line],
        transformer_2w: Sequence[pft.Transformer2W],
        elements: Sequence[ElementBase],
        # TODO: transformer_3w: Sequence[pft.Transformer3W],
    ) -> Sequence[ElementState]:

        relevancies: list[ElementState] = []
        for t in terminals:
            if t.outserv:
                connected_lines = []
                for line in lines:
                    if line.bus1 is not None and line.bus2 is not None:
                        if any([line.bus1.cterm == t, line.bus2.cterm == t]):
                            connected_lines.append(line)

                connected_transformers_2w = []
                for trafo in transformer_2w:
                    if trafo.bushv is not None and trafo.buslv is not None:
                        if any([trafo.bushv.cterm == t, trafo.buslv.cterm == t]):
                            connected_transformers_2w.append(trafo)

                connected_elements = [e for e in elements if e.bus1 is not None and e.bus1.cterm == t]

                # TODO: connected_transformer_3w = [e for e in transformer_3w if e.bushv.cterm == t or e.buslv.cterm == t or e.busmv.cterm == t]
                node_name = self.pfi.create_name(t, self.grid_name)
                for cl in connected_lines:
                    element_name = self.pfi.create_name(cl, self.grid_name)
                    element_state = ElementState(name=element_name, node=node_name, active=False)
                    relevancies.append(element_state)
                for ct2 in connected_transformers_2w:
                    element_name = self.pfi.create_name(ct2, self.grid_name)
                    element_state = ElementState(name=element_name, node=node_name, active=False)
                    relevancies.append(element_state)
                for ce in connected_elements:
                    element_name = self.pfi.create_name(ce, self.grid_name)
                    element_state = ElementState(name=element_name, node=node_name, active=False)
                    relevancies.append(element_state)

        return relevancies

    def create_line_power_on_states(self, lines: Sequence[pft.Line]) -> Sequence[ElementState]:

        relevancies: list[ElementState] = []
        for line in lines:
            if line.outserv:
                line_name = self.pfi.create_name(line, self.grid_name)
                element_state = ElementState(name=line_name, active=False)
                relevancies.append(element_state)

        return relevancies

    def create_transformer_2w_power_on_states(
        self, transformers_2w: Sequence[pft.Transformer2W]
    ) -> Sequence[ElementState]:

        relevancies: list[ElementState] = []
        for t in transformers_2w:
            if t.outserv:
                t_name = self.pfi.create_name(t, self.grid_name)
                element_state = ElementState(name=t_name, active=False)
                relevancies.append(element_state)

        return relevancies

    def create_element_power_on_states(self, elements: Sequence[ElementBase]) -> Sequence[ElementState]:

        relevancies: list[ElementState] = []
        for e in elements:
            if e.outserv:
                e_name = self.pfi.create_name(e, self.grid_name)
                element_state = ElementState(name=e_name, active=False)
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

            g_type = GridType(g.bustp)
            if g_type == GridType.SL:
                grid = ExternalGridSSC(
                    name=name,
                    u_0=g.usetp,
                    phi_0=g.phiini,
                )
            elif g_type == GridType.PV:
                grid = ExternalGridSSC(
                    name=name,
                    u_0=g.usetp,
                    p_0=g.pgini,
                )
            elif g_type == GridType.PQ:
                grid = ExternalGridSSC(
                    name=name,
                    p_0=g.pgini,
                    q_0=g.qgini,
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
        mv_consumers = self.create_consumer_ssc_states_mv(consumers_mv, grid_name)
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
            power = self.calc_lv_load_power(load)
            if power is not None:
                consumer = self.create_consumer_ssc_state(load, power, grid_name)
                if consumer is not None:
                    consumers_ssc.append(consumer)
        return consumers_ssc

    def create_consumer_ssc_states_mv(
        self,
        loads: Sequence[pft.LoadMV],
        grid_name: str,
    ) -> Sequence[LoadSSC]:

        consumers_ssc: list[LoadSSC] = []
        for load in loads:
            power = self.calc_mv_load_power(load)
            if power is not None:
                consumer = self.create_consumer_ssc_state(load, power, grid_name)
                if consumer is not None:
                    consumers_ssc.append(consumer)
        return consumers_ssc

    def create_consumer_ssc_state(
        self,
        load: pft.LoadBase,
        power: LoadPower,
        grid_name: str,
    ) -> Optional[LoadSSC]:

        name = self.pfi.create_name(load, grid_name)
        export, _ = self.get_description(load)
        if not export:
            logger.warning(f"External grid {name} not set for export. Skipping.")
            return None

        active_power = ActivePowerSSC(p_0=power.p)
        cosphi_type = CosphiDir.OE if load.pf_recap else CosphiDir.UE  # inverse declaration compared to producers
        controller = Controller(
            cosphi=round(power.cosphi, COSPHI_DECIMAL_DIGITS),
            cosphi_type=cosphi_type,
            controller_type=ControllerType.COSPHI_CONST,
        )
        reactive_power = ReactivePowerSSC(q_0=power.q, controller=controller)

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
            if gen.c_pmod is None:  # if generator is not part of higher model
                gen_name = gen.loc_name
            else:
                gen_name = gen.c_pmod.loc_name + PATH_SEP + gen.loc_name

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
            u_n = round(t.uknom, VOLTAGE_DECIMAL_DIGITS) * VOLTAGE_EXPONENT
            gen_num = gen.ngnum

            # Actual Values of single unit
            p = gen.pgini_a
            active_power = ActivePowerSSC(p_0=round(p * POWER_EXPONENT * gen_num))

            # External Controller
            ext_ctrl = gen.c_pstac
            # Q-Controller
            controller = self.create_q_controller(gen, gen_name, u_n, ext_ctrl=ext_ctrl)
            q = gen.qgini_a
            reactive_power = ReactivePowerSSC(
                q_0=round(q * POWER_EXPONENT * gen_num),
                controller=controller,
            )

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
    grid_name: str = "*",
    powerfactory_user_profile: str = "*",
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
