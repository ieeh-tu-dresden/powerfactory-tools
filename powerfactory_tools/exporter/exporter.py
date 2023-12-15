# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import datetime as dt
import itertools
import logging
import math
import multiprocessing
import pathlib
import textwrap
import typing as t

import loguru
import pydantic
from psdm.base import UniqueTuple
from psdm.base import VoltageSystemType
from psdm.meta import Meta
from psdm.meta import SignConvention
from psdm.quantities.multi_phase import Phase
from psdm.quantities.multi_phase import PowerFactorDirection
from psdm.quantities.single_phase import AdmittanceNat
from psdm.quantities.single_phase import AdmittancePosSeq
from psdm.quantities.single_phase import AdmittanceZerSeq
from psdm.quantities.single_phase import Angle as AngleSP
from psdm.quantities.single_phase import ImpedanceNat
from psdm.quantities.single_phase import ImpedancePosSeq
from psdm.quantities.single_phase import ImpedanceZerSeq
from psdm.quantities.single_phase import PhaseAngleClock
from psdm.quantities.single_phase import Voltage as VoltageSP
from psdm.steadystate_case.active_power import ActivePower as ActivePowerSSC
from psdm.steadystate_case.case import Case as SteadystateCase
from psdm.steadystate_case.controller import ControlledVoltageRef
from psdm.steadystate_case.controller import ControlQP
from psdm.steadystate_case.controller import PController
from psdm.steadystate_case.controller import QController
from psdm.steadystate_case.controller import QControlStrategy
from psdm.steadystate_case.external_grid import ExternalGrid as ExternalGridSSC
from psdm.steadystate_case.load import Load as LoadSSC
from psdm.steadystate_case.reactive_power import ReactivePower as ReactivePowerSSC
from psdm.steadystate_case.transformer import Transformer as TransformerSSC
from psdm.topology.branch import Branch
from psdm.topology.branch import BranchType
from psdm.topology.external_grid import ExternalGrid
from psdm.topology.external_grid import GridType
from psdm.topology.load import Load
from psdm.topology.load import LoadType
from psdm.topology.load import PhaseConnections
from psdm.topology.load import SystemType
from psdm.topology.load_model import LoadModel
from psdm.topology.node import Node
from psdm.topology.topology import Topology
from psdm.topology.transformer import TapSide
from psdm.topology.transformer import Transformer
from psdm.topology.transformer import TransformerPhaseTechnologyType
from psdm.topology.transformer import VectorGroup as TVectorGroup
from psdm.topology.windings import VectorGroup as WVectorGroup
from psdm.topology.windings import Winding
from psdm.topology_case.case import Case as TopologyCase
from psdm.topology_case.element_state import ElementState

from powerfactory_tools.constants import DEFAULT_PHASE_QUANTITY
from powerfactory_tools.constants import DecimalDigits
from powerfactory_tools.constants import Exponents
from powerfactory_tools.exporter.load_power import ConsolidatedLoadPhaseConnectionType
from powerfactory_tools.exporter.load_power import ControlTypeFactory
from powerfactory_tools.exporter.load_power import LoadPower
from powerfactory_tools.interface import PowerFactoryData
from powerfactory_tools.interface import PowerFactoryInterface
from powerfactory_tools.powerfactory_types import CosPhiChar
from powerfactory_tools.powerfactory_types import CtrlMode
from powerfactory_tools.powerfactory_types import CtrlVoltageRef
from powerfactory_tools.powerfactory_types import GeneratorPhaseConnectionType
from powerfactory_tools.powerfactory_types import GeneratorSystemType
from powerfactory_tools.powerfactory_types import IOpt
from powerfactory_tools.powerfactory_types import LoadLVPhaseConnectionType
from powerfactory_tools.powerfactory_types import LoadPhaseConnectionType
from powerfactory_tools.powerfactory_types import LocalQCtrlMode
from powerfactory_tools.powerfactory_types import PFClassId
from powerfactory_tools.powerfactory_types import Phase1PH as PFPhase1PH
from powerfactory_tools.powerfactory_types import Phase2PH as PFPhase2PH
from powerfactory_tools.powerfactory_types import Phase3PH as PFPhase3PH
from powerfactory_tools.powerfactory_types import PowerFactoryTypes as PFTypes
from powerfactory_tools.powerfactory_types import QChar
from powerfactory_tools.powerfactory_types import TerminalPhaseConnectionType
from powerfactory_tools.powerfactory_types import TerminalVoltageSystemType
from powerfactory_tools.powerfactory_types import TrfNeutralConnectionType
from powerfactory_tools.powerfactory_types import TrfNeutralPointState
from powerfactory_tools.powerfactory_types import TrfPhaseTechnology
from powerfactory_tools.powerfactory_types import TrfTapSide
from powerfactory_tools.powerfactory_types import Vector
from powerfactory_tools.powerfactory_types import VectorGroup
from powerfactory_tools.powerfactory_types import VoltageSystemType as ElementVoltageSystemType
from powerfactory_tools.quantities import QuantityConverter as Qc

if t.TYPE_CHECKING:
    from collections.abc import Sequence
    from types import TracebackType

    import typing_extensions as te

    ElementBase = PFTypes.GeneratorBase | PFTypes.LoadBase | PFTypes.ExternalGrid


POWERFACTORY_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
POWERFACTORY_VERSION = "2022 SP2"
PYTHON_VERSION = "3.10"

FULL_DYNAMIC = 100
M_TAB2015_MIN_THRESHOLD = 0.01
STRING_SEPARATOR = "; "

LOAD_CLASSES = [PFClassId.LOAD.value, PFClassId.LOAD_LV.value, PFClassId.LOAD_MV.value]


@pydantic.dataclasses.dataclass
class LoadLV:
    fixed: LoadPower
    night: LoadPower
    flexible: LoadPower
    flexible_avg: LoadPower


@pydantic.dataclasses.dataclass
class LoadMV:
    consumer: LoadPower
    producer: LoadPower


class PowerFactoryExporterProcess(multiprocessing.Process):
    def __init__(  # noqa: PLR0913
        self,
        *,
        export_path: pathlib.Path,
        project_name: str,
        powerfactory_user_profile: str = "",
        powerfactory_path: pathlib.Path = POWERFACTORY_PATH,
        powerfactory_version: str = POWERFACTORY_VERSION,
        python_version: str = PYTHON_VERSION,
        logging_level: int = logging.DEBUG,
        log_file_path: pathlib.Path | None = None,
        topology_name: str | None = None,
        topology_case_name: str | None = None,
        steadystate_case_name: str | None = None,
        study_case_names: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.export_path = export_path
        self.project_name = project_name
        self.powerfactory_user_profile = powerfactory_user_profile
        self.powerfactory_path = powerfactory_path
        self.powerfactory_version = powerfactory_version
        self.python_version = python_version
        self.logging_level = logging_level
        self.log_file_path = log_file_path
        self.topology_name = topology_name
        self.topology_case_name = topology_case_name
        self.steadystate_case_name = steadystate_case_name
        self.study_case_names = study_case_names

    def run(self) -> None:
        pfe = PowerFactoryExporter(
            project_name=self.project_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_path=self.powerfactory_path,
            powerfactory_version=self.powerfactory_version,
            python_version=self.python_version,
            logging_level=self.logging_level,
            log_file_path=self.log_file_path,
        )
        pfe.export(
            export_path=self.export_path,
            topology_name=self.topology_name,
            topology_case_name=self.topology_case_name,
            steadystate_case_name=self.steadystate_case_name,
            study_case_names=self.study_case_names,
        )


@pydantic.dataclasses.dataclass
class PowerFactoryExporter:
    project_name: str
    powerfactory_user_profile: str = ""
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH
    powerfactory_version: str = POWERFACTORY_VERSION
    python_version: str = PYTHON_VERSION
    logging_level: int = logging.DEBUG
    log_file_path: pathlib.Path | None = None

    def __post_init__(self) -> None:
        self.pfi = PowerFactoryInterface(
            project_name=self.project_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_path=self.powerfactory_path,
            powerfactory_version=self.powerfactory_version,
            python_version=self.python_version,
            logging_level=self.logging_level,
            log_file_path=self.log_file_path,
        )

    def __enter__(self) -> te.Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.pfi.close()

    def export(
        self,
        *,
        export_path: pathlib.Path,
        topology_name: str | None = None,
        topology_case_name: str | None = None,
        steadystate_case_name: str | None = None,
        study_case_names: list[str] | None = None,
    ) -> None:
        """Export grid topology, topology_case and steadystate_case to json files.

        Based on the class arguments of PowerFactoryExporter a grid, given in DIgSILENT PowerFactory, is exported to
        three json files with given schema. The whole grid data is separated into topology (raw assets), topology_case
        (binary switching info and out of service info) and steadystate_case (operation points).

        Keyword Arguments:
            export_path {pathlib.Path} -- the directory where the exported json files are saved
            topology_name {str} -- the chosen file name for 'topology' data (default: {None})
            topology_case_name {str} -- the chosen file name for related 'topology_case' data (default: {None})
            steadystate_case_name {str} -- the chosen file name for related 'steadystate_case' data (default: {None})
            study_case_names {list[str]} -- a list of study cases to export (default: {None})
        """
        if study_case_names is not None:
            self.export_study_cases(
                export_path=export_path,
                study_case_names=study_case_names,
                topology_name=topology_name,
                topology_case_name=topology_case_name,
                steadystate_case_name=steadystate_case_name,
            )
        else:
            act_sc = self.pfi.app.GetActiveStudyCase()
            if act_sc is not None:
                self.export_active_study_case(
                    export_path=export_path,
                    study_case_name=act_sc.loc_name,
                    topology_name=topology_name,
                    topology_case_name=topology_case_name,
                    steadystate_case_name=steadystate_case_name,
                )
            else:
                msg = "Could not export. There is neither a study case defined nor is one activated"
                raise ValueError(msg)

    def export_study_cases(
        self,
        *,
        export_path: pathlib.Path,
        study_case_names: list[str],
        topology_name: str | None,
        topology_case_name: str | None,
        steadystate_case_name: str | None,
    ) -> None:
        for study_case_name in study_case_names:
            study_case = self.pfi.study_case(study_case_name)
            if study_case is not None:
                self.pfi.activate_study_case(study_case)
                self.export_active_study_case(
                    export_path=export_path,
                    study_case_name=study_case_name,
                    topology_name=topology_name,
                    topology_case_name=topology_case_name,
                    steadystate_case_name=steadystate_case_name,
                )
            else:
                loguru.logger.warning(
                    "Study case {study_case_name} not found. Skipping.",
                    study_case_name=study_case_name,
                )

    def export_active_study_case(
        self,
        *,
        export_path: pathlib.Path,
        study_case_name: str,
        topology_name: str | None,
        topology_case_name: str | None,
        steadystate_case_name: str | None,
    ) -> None:
        grids = self.pfi.independent_grids(calc_relevant=True)

        for grid in grids:
            grid_name = grid.loc_name
            loguru.logger.info(
                "Exporting {project_name} - study case '{study_case_name}' - grid {grid_name}...",
                project_name=self.project_name,
                study_case_name=study_case_name,
                grid_name=grid_name,
            )
            data = self.pfi.compile_powerfactory_data(grid)
            meta = self.create_meta_data(data=data, case_name=study_case_name)

            topology = self.create_topology(meta=meta, data=data)
            topology_case = self.create_topology_case(meta=meta, data=data)
            steadystate_case = self.create_steadystate_case(meta=meta, data=data)

            if steadystate_case.is_valid_topology(topology) is False:
                msg = "Steadystate case does not match specified topology."
                raise ValueError(msg)

            self.export_topology(
                topology=topology,
                topology_name=topology_name,
                export_path=export_path,
                grid_name=grid_name,
            )
            self.export_topology_case(
                topology_case=topology_case,
                topology_case_name=topology_case_name,
                export_path=export_path,
                grid_name=grid_name,
            )
            self.export_steadystate_case(
                steadystate_case=steadystate_case,
                steadystate_case_name=steadystate_case_name,
                export_path=export_path,
                grid_name=grid_name,
            )

    def export_topology(
        self,
        *,
        topology: Topology,
        topology_name: str | None,
        export_path: pathlib.Path,
        grid_name: str,
    ) -> None:
        loguru.logger.debug("Exporting topology {topology_name}...", topology_name=topology_name)
        self.export_data(
            data=topology,
            data_name=topology_name,
            data_type="topology",
            export_path=export_path,
            grid_name=grid_name,
        )

    def export_topology_case(
        self,
        *,
        topology_case: TopologyCase,
        topology_case_name: str | None,
        export_path: pathlib.Path,
        grid_name: str,
    ) -> None:
        loguru.logger.debug("Exporting topology case {topology_case_name}...", topology_case_name=topology_case_name)
        self.export_data(
            data=topology_case,
            data_name=topology_case_name,
            data_type="topology_case",
            export_path=export_path,
            grid_name=grid_name,
        )

    def export_steadystate_case(
        self,
        *,
        steadystate_case: SteadystateCase,
        steadystate_case_name: str | None,
        grid_name: str,
        export_path: pathlib.Path,
    ) -> None:
        loguru.logger.debug(
            "Exporting steadystate case {steadystate_case_name}...",
            steadystate_case_name=steadystate_case_name,
        )
        self.export_data(
            data=steadystate_case,
            data_name=steadystate_case_name,
            data_type="steadystate_case",
            export_path=export_path,
            grid_name=grid_name,
        )

    def export_data(
        self,
        *,
        data: Topology | TopologyCase | SteadystateCase,
        data_name: str | None,
        data_type: t.Literal["topology", "topology_case", "steadystate_case"],
        export_path: pathlib.Path,
        grid_name: str,
    ) -> None:
        """Export data to json file.

        Keyword Arguments:
            data {Topology | TopologyCase | SteadystateCase} -- data to export
            data_name {str | None} -- the chosen file name for data
            data_type {t.Literal['topology', 'topology_case', 'steadystate_case']} -- the data type
            export_path {pathlib.Path} -- the directory where the exported json file is saved
            grid_name: {str} -- the exported grids name
        """
        timestamp = dt.datetime.now().astimezone()
        timestamp_string = timestamp.isoformat(sep="T", timespec="seconds").replace(":", "")
        if data_name is None:
            if data.meta.case is not None:
                filename = f"{data.meta.case}_{grid_name}_{data_type}.json"
            else:
                filename = f"{data.meta.case}_{grid_name}_{data_type}_{timestamp_string}.json"
        else:
            filename = f"{data_name}_{grid_name}_{data_type}.json"

        file_path = export_path / filename
        try:
            file_path.resolve()
        except OSError as e:
            msg = f"File path {file_path} is not a valid path."
            raise FileNotFoundError(msg) from e

        data.to_json(file_path)

    @staticmethod
    def create_meta_data(
        *,
        data: PowerFactoryData,
        case_name: str,
    ) -> Meta:
        loguru.logger.debug("Creating meta data...")
        grid_name = data.grid_name.replace(" ", "-")
        project_name = data.project_name.replace(" ", "-")
        date = data.date

        return Meta(
            case=case_name,
            date=date,
            grid=grid_name,
            project=project_name,
            sign_convention=SignConvention.PASSIVE,
        )

    def create_topology(
        self,
        *,
        meta: Meta,
        data: PowerFactoryData,
    ) -> Topology:
        loguru.logger.debug("Creating topology...")
        external_grids = self.create_external_grids(
            data.external_grids,
            grid_name=data.grid_name,
        )
        nodes = self.create_nodes(data.terminals, grid_name=data.grid_name)
        branches = self.create_branches(
            lines=data.lines,
            couplers=data.couplers,
            fuses=data.bfuses,
            grid_name=data.grid_name,
        )
        loads = self.create_loads(
            consumers=data.loads,
            consumers_lv=data.loads_lv,
            consumers_mv=data.loads_mv,
            generators=data.generators,
            pv_systems=data.pv_systems,
            grid_name=data.grid_name,
        )
        transformers = self.create_transformers(
            data.transformers_2w,
            grid_name=data.grid_name,
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
        /,
        *,
        grid_name: str,
    ) -> Sequence[ExternalGrid]:
        loguru.logger.info("Creating external grids...")
        external_grids = [self.create_external_grid(ext_grid, grid_name=grid_name) for ext_grid in ext_grids]
        return self.pfi.filter_none(external_grids)

    def create_external_grid(
        self,
        ext_grid: PFTypes.ExternalGrid,
        /,
        *,
        grid_name: str,
    ) -> ExternalGrid | None:
        name = self.pfi.create_name(ext_grid, grid_name=grid_name)
        loguru.logger.debug("Creating external_grid {ext_grid_name}...", ext_grid_name=name)
        export, description = self.get_description(ext_grid)
        if not export:
            loguru.logger.warning("External grid {ext_grid_name} not set for export. Skipping.", ext_grid_name=name)
            return None

        if ext_grid.bus1 is None:
            loguru.logger.warning(
                "External grid {ext_grid_name} not connected to any bus. Skipping.",
                ext_grid_name=name,
            )
            return None

        node_name = self.pfi.create_name(ext_grid.bus1.cterm, grid_name=grid_name)
        phase_connection_type = TerminalPhaseConnectionType(ext_grid.bus1.cterm.phtech)
        phases = self.get_external_grid_phases(
            phase_connection_type=phase_connection_type,  # default
            bus=ext_grid.bus1,
        )

        return ExternalGrid(
            name=name,
            description=description,
            node=node_name,
            phases=phases,
            type=GridType(ext_grid.bustp),
            short_circuit_power_max=Qc.single_phase_apparent_power(ext_grid.snss * Exponents.POWER),
            short_circuit_power_min=Qc.single_phase_apparent_power(ext_grid.snssmin * Exponents.POWER),
        )

    def create_nodes(
        self,
        terminals: Sequence[PFTypes.Terminal],
        /,
        *,
        grid_name: str,
    ) -> Sequence[Node]:
        loguru.logger.info("Creating nodes...")
        nodes = [self.create_node(terminal, grid_name=grid_name) for terminal in terminals]
        return self.pfi.filter_none(nodes)

    def create_node(
        self,
        terminal: PFTypes.Terminal,
        /,
        *,
        grid_name: str,
    ) -> Node | None:
        export, description = self.get_description(terminal)
        name = self.pfi.create_name(terminal, grid_name=grid_name)
        loguru.logger.debug("Creating node {node_name}...", node_name=name)
        if not export:
            loguru.logger.warning("Node {node_name} not set for export. Skipping.", node_name=name)
            return None

        u_n = Qc.single_phase_voltage(terminal.uknom * Exponents.VOLTAGE)  # phase-phase voltage

        if self.pfi.is_within_substation(terminal):
            description = (
                "substation internal" if not description else "substation internal" + STRING_SEPARATOR + description
            )

        phases = self.get_terminal_phases(TerminalPhaseConnectionType(terminal.phtech))

        return Node(
            name=name,
            u_n=u_n,
            phases=phases,
            description=description,
        )

    def create_branches(
        self,
        *,
        lines: Sequence[PFTypes.Line],
        couplers: Sequence[PFTypes.Coupler],
        fuses: Sequence[PFTypes.BFuse],
        grid_name: str,
    ) -> Sequence[Branch]:
        loguru.logger.info("Creating branches...")
        blines = [self.create_line(line, grid_name=grid_name) for line in lines]
        bcouplers = [self.create_coupler(coupler, grid_name=grid_name) for coupler in couplers]
        bfuses = [self.create_fuse(fuse, grid_name=grid_name) for fuse in fuses]

        return self.pfi.list_from_sequences(
            self.pfi.filter_none(blines),
            self.pfi.filter_none(bcouplers),
            self.pfi.filter_none(bfuses),
        )

    def create_line(  # noqa: PLR0915
        self,
        line: PFTypes.Line,
        /,
        *,
        grid_name: str,
    ) -> Branch | None:
        name = self.pfi.create_name(line, grid_name=grid_name)
        loguru.logger.debug("Creating line {line_name}...", line_name=name)
        export, description = self.get_description(line)
        if not export:
            loguru.logger.warning("Line {line_name} not set for export. Skipping.", line_name=name)
            return None

        if line.bus1 is None or line.bus2 is None:
            loguru.logger.warning("Line {line_name} not connected to buses on both sides. Skipping.", line_name=name)
            return None

        t1 = line.bus1.cterm
        t2 = line.bus2.cterm

        if t1.systype != t2.systype:
            loguru.logger.warning("Line {line_name} connected to DC and AC bus. Skipping.", line_name=name)
            return None

        t1_name = self.pfi.create_name(t1, grid_name=grid_name)
        t2_name = self.pfi.create_name(t2, grid_name=grid_name)

        u_nom_1 = t1.uknom
        u_nom_2 = t2.uknom

        l_type = line.typ_id
        if l_type is None:
            loguru.logger.warning(
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
        if l_type.nneutral:
            l_type = t.cast("PFTypes.LineNType", l_type)
            rn = l_type.rnline * line.dline / line.nlnum * Exponents.RESISTANCE
            xn = l_type.xnline * line.dline / line.nlnum * Exponents.REACTANCE
            rpn = l_type.rpnline * line.dline / line.nlnum * Exponents.RESISTANCE
            xpn = l_type.xpnline * line.dline / line.nlnum * Exponents.REACTANCE
            gn = 0  # as attribute 'gnline' does not exist in PF model type
            bn = l_type.bnline * line.dline * line.nlnum * Exponents.SUSCEPTANCE
            gpn = 0  # as attribute 'gpnline' does not exist in PF model type
            bpn = l_type.bpnline * line.dline * line.nlnum * Exponents.SUSCEPTANCE
        else:
            rn = None
            xn = None
            rpn = None
            xpn = None
            gn = None
            bn = None
            gpn = None
            bpn = None

        f_nom = l_type.frnom  # usually 50 Hertz
        u_system_type = VoltageSystemType[ElementVoltageSystemType(l_type.systp).name]

        phases_1 = self.get_branch_phases(
            l_type=l_type,
            phase_connection_type=TerminalPhaseConnectionType(t1.phtech),
            bus=line.bus1,
            grid_name=grid_name,
        )
        phases_2 = self.get_branch_phases(
            l_type=l_type,
            phase_connection_type=TerminalPhaseConnectionType(t2.phtech),
            bus=line.bus2,
            grid_name=grid_name,
        )

        return Branch(
            name=name,
            node_1=t1_name,
            node_2=t2_name,
            phases_1=phases_1,
            phases_2=phases_2,
            r1=ImpedancePosSeq(value=r1),
            x1=ImpedancePosSeq(value=x1),
            r0=ImpedanceZerSeq(value=r0),
            x0=ImpedanceZerSeq(value=x0),
            g1=AdmittancePosSeq(value=g1),
            b1=AdmittancePosSeq(value=b1),
            g0=AdmittanceZerSeq(value=g0),
            b0=AdmittanceZerSeq(value=b0),
            rn=ImpedanceNat(value=rn) if rn is not None else None,
            xn=ImpedanceNat(value=xn) if xn is not None else None,
            rpn=ImpedanceNat(value=rpn) if rpn is not None else None,
            xpn=ImpedanceNat(value=xpn) if xpn is not None else None,
            gn=AdmittanceNat(value=gn) if gn is not None else None,
            bn=AdmittanceNat(value=bn) if bn is not None else None,
            gpn=AdmittanceNat(value=gpn) if gpn is not None else None,
            bpn=AdmittanceNat(value=bpn) if bpn is not None else None,
            i_r=Qc.single_phase_current(i_r),
            description=description,
            u_n=Qc.single_phase_voltage(u_nom),
            f_n=Qc.single_phase_frequency(f_nom),
            type=BranchType.LINE,
            voltage_system_type=u_system_type,
        )

    @staticmethod
    def determine_line_voltage(
        *,
        u_nom_1: float,
        u_nom_2: float,
        l_type: PFTypes.LineType,
    ) -> float:
        """Returns the nominal voltage in SI unit (V)."""
        v = u_nom_1 if round(u_nom_1, DecimalDigits.VOLTAGE) == round(u_nom_2, DecimalDigits.VOLTAGE) else l_type.uline

        return round(v * Exponents.VOLTAGE, 0)

    def create_coupler(
        self,
        coupler: PFTypes.Coupler,
        /,
        *,
        grid_name: str,
    ) -> Branch | None:
        name = self.pfi.create_name(coupler, grid_name=grid_name)
        loguru.logger.debug("Creating coupler {coupler_name}...", coupler_name=name)
        export, description = self.get_description(coupler)
        if not export:
            loguru.logger.warning("Coupler {coupler_name} not set for export. Skipping.", coupler_name=name)
            return None

        if coupler.bus1 is None or coupler.bus2 is None:
            loguru.logger.warning("Coupler {coupler} not connected to buses on both sides. Skipping.", coupler=coupler)
            return None

        t1 = coupler.bus1.cterm
        t2 = coupler.bus2.cterm

        if t1.systype != t2.systype:
            loguru.logger.warning("Coupler {coupler} connected to DC and AC bus. Skipping.", coupler=coupler)
            return None

        if coupler.typ_id is not None:
            r1 = coupler.typ_id.R_on
            x1 = coupler.typ_id.X_on
            i_r = coupler.typ_id.Inom * Exponents.CURRENT
        else:
            r1 = 0
            x1 = 0
            i_r = None

        b1 = 0
        g1 = 0

        u_nom_1 = t1.uknom
        u_nom_2 = t2.uknom

        if round(u_nom_1, 2) == round(u_nom_2, 2):
            u_nom = round(u_nom_1 * Exponents.VOLTAGE, 0)  # nominal voltage (V)
        else:
            loguru.logger.warning(
                "Coupler {coupler_name} couples busbars with different voltage levels. Skipping.",
                coupler_name=name,
            )
            return None

        description = self.get_element_description(terminal1=t1, terminal2=t2, description=description)

        t1_name = self.pfi.create_name(t1, grid_name=grid_name)
        t2_name = self.pfi.create_name(t2, grid_name=grid_name)

        voltage_system_type = VoltageSystemType[TerminalVoltageSystemType(t1.systype).name]

        phases_1 = self.get_terminal_phases(phase_connection_type=TerminalPhaseConnectionType(t1.phtech))
        phases_2 = self.get_terminal_phases(phase_connection_type=TerminalPhaseConnectionType(t2.phtech))

        return Branch(
            name=name,
            node_1=t1_name,
            node_2=t2_name,
            phases_1=phases_1,
            phases_2=phases_2,
            r1=ImpedancePosSeq(value=r1),
            x1=ImpedancePosSeq(value=x1),
            g1=AdmittancePosSeq(value=g1),
            b1=AdmittancePosSeq(value=b1),
            i_r=Qc.single_phase_current(i_r) if i_r is not None else None,
            description=description,
            u_n=Qc.single_phase_voltage(u_nom),
            type=BranchType.COUPLER,
            voltage_system_type=voltage_system_type,
        )

    def create_fuse(
        self,
        fuse: PFTypes.BFuse,
        /,
        *,
        grid_name: str,
    ) -> Branch | None:
        name = self.pfi.create_name(fuse, grid_name=grid_name)
        loguru.logger.debug("Creating fuse {fuse_name}...", fuse_name=name)
        export, description = self.get_description(fuse)
        if not export:
            loguru.logger.warning("Fuse {fuse_name} not set for export. Skipping.", fuse_name=name)
            return None

        if fuse.bus1 is None or fuse.bus2 is None:
            loguru.logger.warning("Fuse {fuse} not connected to buses on both sides. Skipping.", fuse=fuse)
            return None

        t1 = fuse.bus1.cterm
        t2 = fuse.bus2.cterm

        if t1.systype != t2.systype:
            loguru.logger.warning("Fuse {fuse} connected to DC and AC bus. Skipping.", fuse=fuse)
            return None

        if fuse.typ_id is not None:
            i_r = fuse.typ_id.irat
            # save fuse typ in description tag
            description = (
                "Type: " + fuse.typ_id.loc_name
                if not description
                else description + STRING_SEPARATOR + "Type: " + fuse.typ_id.loc_name
            )
        else:
            i_r = None

        r1 = 0
        x1 = 0
        b1 = 0
        g1 = 0

        u_nom_1 = t1.uknom
        u_nom_2 = t2.uknom

        if round(u_nom_1, 2) == round(u_nom_2, 2):
            u_nom = round(u_nom_1 * Exponents.VOLTAGE, 0)  # nominal voltage (V)
        else:
            loguru.logger.warning(
                "Fuse {fuse_name} couples busbars with different voltage levels. Skipping.",
                fuse_name=name,
            )
            return None

        description = self.get_element_description(terminal1=t1, terminal2=t2, description=description)

        t1_name = self.pfi.create_name(t1, grid_name=grid_name)
        t2_name = self.pfi.create_name(t2, grid_name=grid_name)

        voltage_system_type = VoltageSystemType[TerminalVoltageSystemType(t1.systype).name]

        phases_1 = self.get_terminal_phases(phase_connection_type=TerminalPhaseConnectionType(t1.phtech))
        phases_2 = self.get_terminal_phases(phase_connection_type=TerminalPhaseConnectionType(t2.phtech))

        return Branch(
            name=name,
            node_1=t1_name,
            node_2=t2_name,
            phases_1=phases_1,
            phases_2=phases_2,
            r1=ImpedancePosSeq(value=r1),
            x1=ImpedancePosSeq(value=x1),
            g1=AdmittancePosSeq(value=g1),
            b1=AdmittancePosSeq(value=b1),
            i_r=Qc.single_phase_current(i_r) if i_r is not None else None,
            description=description,
            u_n=Qc.single_phase_voltage(u_nom),
            type=BranchType.FUSE,
            voltage_system_type=voltage_system_type,
        )

    def get_element_description(
        self,
        *,
        terminal1: PFTypes.Terminal,
        terminal2: PFTypes.Terminal,
        description: str,
    ) -> str:
        if self.pfi.is_within_substation(terminal1) and self.pfi.is_within_substation(terminal2):
            if not description:
                return "substation internal"

            return "substation internal" + STRING_SEPARATOR + description

        return description

    def create_transformers(
        self,
        pf_transformers_2w: Sequence[PFTypes.Transformer2W],
        /,
        *,
        grid_name: str,
    ) -> Sequence[Transformer]:
        loguru.logger.info("Creating transformers...")
        return self.create_transformers_2w(pf_transformers_2w, grid_name=grid_name)

    def create_transformers_2w(
        self,
        transformers_2w: Sequence[PFTypes.Transformer2W],
        /,
        *,
        grid_name: str,
    ) -> Sequence[Transformer]:
        loguru.logger.info("Creating 2-winding transformers...")
        transformers = [
            self.create_transformer_2w(transformer_2w, grid_name=grid_name) for transformer_2w in transformers_2w
        ]
        return self.pfi.filter_none(transformers)

    def create_transformer_2w(
        self,
        transformer_2w: PFTypes.Transformer2W,
        /,
        *,
        grid_name: str,
    ) -> Transformer | None:
        """Create a symmetrical 2-windung transformer.

        The assignment of zero sequence quantities is depended from the wiring group as follows:
        wiring group    |   Dy(n)   |   Y(N)d   |   Y(N)y(n)
        __________________________Transformer________________
        r_fe1           |   yes     |   yes     |   yes
        x_h1            |   yes     |   yes     |   yes
        r_fe0           |   none    |   none    |   yes
        x_h0            |   none    |   none    |   yes
        __________________________Winding HV_________________
        r1              |   yes     |   yes     |   yes
        x1              |   yes     |   yes     |   yes
        r0              |   none    |   yes*    |   yes
        x0              |   none    |   yes*    |   yes
        __________________________Winding LV_________________
        r1              |   yes     |   yes     |   yes
        x1              |   yes     |   yes     |   yes
        r0              |   yes*    |   none    |   yes
        x0              |   yes*    |   none    |   yes

        * Results from uk0 resp. Zk0 instead of Zm0 as magnetising impedance can not be separated from Zk0 due to delta wiring group.

        Arguments:
            transformer_2w  {PFTypes.Transformer2W} -- the powerfactory transformer data object
            grid_name {str} -- the name of the grid the transformer is located

        Returns:
            a PSDM transformer object
        """
        name = self.pfi.create_name(transformer_2w, grid_name=grid_name)
        loguru.logger.debug("Creating 2-winding transformer {transformer_name}...", transformer_name=name)
        export, description = self.get_description(transformer_2w)
        if not export:
            loguru.logger.warning(
                "2-winding transformer {transformer_name} not set for export. Skipping.",
                transformer_name=name,
            )
            return None

        if transformer_2w.buslv is None or transformer_2w.bushv is None:
            loguru.logger.warning(
                "2-winding transformer {transformer_name} not connected to buses on both sides. Skipping.",
                transformer_name=name,
            )
            return None

        t_high = transformer_2w.bushv.cterm
        t_low = transformer_2w.buslv.cterm

        t_high_name = self.pfi.create_name(t_high, grid_name=grid_name)
        t_low_name = self.pfi.create_name(t_low, grid_name=grid_name)

        t_type = transformer_2w.typ_id

        if t_type is not None:
            t_number = transformer_2w.ntnum

            ph_technology = TransformerPhaseTechnologyType[TrfPhaseTechnology(t_type.nt2ph).name]

            # Rated Voltage of the transformer_2w windings itself (CIM: ratedU)
            u_ref_h = t_type.utrn_h * Exponents.VOLTAGE  # V
            u_ref_l = t_type.utrn_l * Exponents.VOLTAGE

            # Nominal Voltage of connected nodes (CIM: BaseVoltage)
            u_nom_h = transformer_2w.bushv.cterm.uknom * Exponents.VOLTAGE  # V
            u_nom_l = transformer_2w.buslv.cterm.uknom * Exponents.VOLTAGE

            # Transformer Tap Changer
            tap_side, tap_u_mag, tap_u_phi, tap_min, tap_max, tap_neutral = self.get_transformer_tap_changer(
                t_type=t_type,
                voltage_ref_hv=u_ref_h,
                voltage_ref_lv=u_ref_l,
                voltage_ref_ter=None,
                name=name,
            )

            # Wiring group
            try:
                vector_group = TVectorGroup[VectorGroup(t_type.vecgrp).name]
            except KeyError as e:
                msg = f"Vector group {t_type.vecgrp} of transformer {name} is technically impossible. Aborting."
                loguru.logger.error(msg)
                raise RuntimeError from e

            vector_group_h = WVectorGroup[Vector(t_type.tr2cn_h).name]
            vector_group_l = WVectorGroup[Vector(t_type.tr2cn_l).name]
            vector_phase_angle_clock = t_type.nt2ag

            phases_1 = self.get_transformer2w_3ph_phases(winding_vector_group=vector_group_h, bus=transformer_2w.bushv)
            phases_2 = self.get_transformer2w_3ph_phases(winding_vector_group=vector_group_l, bus=transformer_2w.buslv)

            # Rated values
            s_r = round(t_type.strn * Exponents.POWER, DecimalDigits.POWER)  # VA
            pu2abs = u_ref_h**2 / s_r  # do only compute with rounded values to prevent float uncertainty errors

            r_fe_1, x_h_1, r_fe_0, x_h_0 = self.get_transformer2w_magnetising_impedance(
                t_type=t_type,
                vector_group_h=vector_group_h,
                vector_group_l=vector_group_l,
                voltage_ref=u_ref_h,
                pu2abs=pu2abs,
            )

            # Create Winding Objects
            # Leakage impedance
            r_1_h, x_1_h, r_1_l, x_1_l, r_0_h, x_0_h, r_0_l, x_0_l = self.get_transformer2w_leakage_impedance(
                t_type=t_type,
                vector_group_h=vector_group_h,
                vector_group_l=vector_group_l,
                pu2abs=pu2abs,
            )

            # Neutral point phase connection
            neutral_connected_h, neutral_connected_l = self.transformer_neutral_connection_hvlv(
                transformer=transformer_2w,
                vector_group=vector_group,
            )

            # Neutral point earthing
            re_h, xe_h, re_l, xe_l = self.get_transformer2w_neutral_earthing_impedance(
                transformer=transformer_2w,
                vector_group_h=vector_group_h,
                vector_group_l=vector_group_l,
            )

            # winding of high-voltage side
            wh = Winding(
                node=t_high_name,
                s_r=Qc.single_phase_apparent_power(s_r),
                u_r=Qc.single_phase_voltage(u_ref_h),
                u_n=Qc.single_phase_voltage(u_nom_h),
                r1=ImpedancePosSeq(value=r_1_h),
                r0=ImpedanceZerSeq(value=r_0_h) if r_0_h is not None else None,
                x1=ImpedancePosSeq(value=x_1_h),
                x0=ImpedanceZerSeq(value=x_0_h) if x_0_h is not None else None,
                re=ImpedanceNat(value=re_h) if re_h is not None else None,
                xe=ImpedanceNat(value=xe_h) if xe_h is not None else None,
                vector_group=vector_group_h,
                phase_angle_clock=PhaseAngleClock(value=0),
                neutral_connected=neutral_connected_h,
            )

            # winding of low-voltage side
            wl = Winding(
                node=t_low_name,
                s_r=Qc.single_phase_apparent_power(s_r),
                u_r=Qc.single_phase_voltage(u_ref_l),
                u_n=Qc.single_phase_voltage(u_nom_l),
                r1=ImpedancePosSeq(value=r_1_l),
                r0=ImpedanceZerSeq(value=r_0_l) if r_0_l is not None else None,
                x1=ImpedancePosSeq(value=x_1_l),
                x0=ImpedanceZerSeq(value=x_0_l) if x_0_l is not None else None,
                re=ImpedanceNat(value=re_l) if re_l is not None else None,
                xe=ImpedanceNat(value=xe_l) if xe_l is not None else None,
                vector_group=vector_group_l,
                phase_angle_clock=PhaseAngleClock(value=int(vector_phase_angle_clock)),
                neutral_connected=neutral_connected_l,
            )

            return Transformer(
                node_1=t_high_name,
                node_2=t_low_name,
                phases_1=phases_1,
                phases_2=phases_2,
                name=name,
                number=t_number,
                r_fe1=ImpedancePosSeq(value=r_fe_1),
                x_h1=ImpedancePosSeq(value=x_h_1),
                r_fe0=ImpedanceZerSeq(value=r_fe_0) if r_fe_0 is not None else None,
                x_h0=ImpedanceZerSeq(value=x_h_0) if x_h_0 is not None else None,
                vector_group=vector_group,
                tap_u_mag=Qc.single_phase_voltage(tap_u_mag) if tap_u_mag is not None else None,
                tap_u_phi=Qc.single_phase_angle(tap_u_phi) if tap_u_phi is not None else None,
                tap_min=tap_min,
                tap_max=tap_max,
                tap_neutral=tap_neutral,
                tap_side=tap_side,
                description=description,
                phase_technology_type=ph_technology,
                windings=[wh, wl],
            )

        loguru.logger.warning(
            "Type not set for 2-winding transformer {transformer_name}. Skipping.",
            transformer_name=name,
        )
        return None

    @staticmethod
    def get_transformer_tap_changer(
        *,
        t_type: PFTypes.Transformer2WType,
        voltage_ref_hv: float,
        voltage_ref_lv: float,
        voltage_ref_ter: float | None,  # tertiary reference voltage (only for 3w transformers)
        name: str,
    ) -> tuple[TapSide | None, VoltageSP | None, AngleSP | None, float | None, float | None, float | None]:
        voltage_ref_hv = round(voltage_ref_hv, DecimalDigits.VOLTAGE)
        voltage_ref_lv = round(voltage_ref_lv, DecimalDigits.VOLTAGE)

        tap_side = TapSide[TrfTapSide(t_type.tap_side).name] if t_type.itapch else None
        tap_u_mag_perc = t_type.dutap
        if tap_side is TapSide.HV:
            tap_u_mag = tap_u_mag_perc / 100 * voltage_ref_hv
            tap_u_phi = t_type.phitr
        elif tap_side is TapSide.LV:
            tap_u_mag = tap_u_mag_perc / 100 * voltage_ref_lv
            tap_u_phi = t_type.phitr
        elif tap_side is TapSide.MV and voltage_ref_ter is not None:
            tap_u_mag = tap_u_mag_perc / 100 * voltage_ref_ter
            tap_u_phi = t_type.phitr
        elif tap_side is None:
            tap_u_mag = None
            tap_u_phi = None
        else:
            msg = "unreachable"
            raise RuntimeError(msg)
        tap_min = t_type.ntpmn
        tap_max = t_type.ntpmx
        tap_neutral = t_type.nntap0

        if bool(t_type.itapch2) is True:
            loguru.logger.warning(
                "2-winding transformer {transformer_name} has second tap changer. Not supported so far. Skipping.",
                transformer_name=name,
            )
        return (tap_side, tap_u_mag, tap_u_phi, tap_min, tap_max, tap_neutral)

    @staticmethod
    def get_transformer2w_leakage_impedance(
        *,
        t_type: PFTypes.Transformer2WType,
        vector_group_h: WVectorGroup,
        vector_group_l: WVectorGroup,
        pu2abs: float,
    ) -> tuple[float, float, float, float, float | None, float | None, float | None, float | None]:
        r_1 = t_type.r1pu * pu2abs
        r_1_h = r_1 * t_type.itrdr
        r_1_l = r_1 * t_type.itrdr_lv
        x_1 = t_type.x1pu * pu2abs
        x_1_h = x_1 * t_type.itrdl
        x_1_l = x_1 * t_type.itrdl_lv

        z_k_0 = t_type.uk0tr / 100 * pu2abs  # Ohm
        if vector_group_h is WVectorGroup.D and vector_group_l in [WVectorGroup.Y, WVectorGroup.YN]:  # Dy(n)
            r_0_h = None
            x_0_h = None
            if t_type.ur0tr > 0:
                r_0_l = t_type.ur0tr / 100 * pu2abs  # Ohm
                x_0_l = math.sqrt(z_k_0**2 - r_0_l**2)
            else:
                r_0_l = None
                x_0_l = z_k_0
        elif vector_group_l is WVectorGroup.D and vector_group_h in [WVectorGroup.Y, WVectorGroup.YN]:  # Y(N)d
            r_0_l = None
            x_0_l = None
            if t_type.ur0tr > 0:
                r_0_h = t_type.ur0tr / 100 * pu2abs  # Ohm
                x_0_h = math.sqrt(z_k_0**2 - r_0_h**2)
            else:
                r_0_h = None
                x_0_h = z_k_0
        elif vector_group_l and vector_group_h in [WVectorGroup.Y, WVectorGroup.YN]:
            r_0 = t_type.r0pu * pu2abs
            r_0_h = r_0 * t_type.zx0hl_h
            r_0_l = r_0 * t_type.zx0hl_l
            x_0 = t_type.x0pu * pu2abs
            x_0_h = x_0 * t_type.zx0hl_h
            x_0_l = x_0 * t_type.zx0hl_l
        else:
            loguru.logger.warning(
                "Zero sequence leakage impedance for transformer with vector group 'Z' is not supported yet. Skipping.",
            )

        return (r_1_h, x_1_h, r_1_l, x_1_l, r_0_h, x_0_h, r_0_l, x_0_l)

    @staticmethod
    def get_transformer2w_neutral_earthing_impedance(
        *,
        transformer: PFTypes.Transformer2W,
        vector_group_h: WVectorGroup,
        vector_group_l: WVectorGroup,
    ) -> tuple[float | None, float | None, float | None, float | None]:
        if "N" in vector_group_h.value and transformer.cgnd_h == TrfNeutralPointState.EARTHED:
            re_h = transformer.re0tr_h
            xe_h = transformer.xe0tr_h
        else:
            re_h = None
            xe_h = None
        if "N" in vector_group_l.value and transformer.cgnd_l == TrfNeutralPointState.EARTHED:
            re_l = transformer.re0tr_l
            xe_l = transformer.xe0tr_l
        else:
            re_l = None
            xe_l = None

        return (re_h, xe_h, re_l, xe_l)

    @staticmethod
    def get_transformer2w_magnetising_impedance(
        *,
        t_type: PFTypes.Transformer2WType,
        vector_group_l: WVectorGroup,
        vector_group_h: WVectorGroup,
        voltage_ref: float,
        pu2abs: float,
    ) -> tuple[float, float, float | None, float | None]:
        # Magnetising impedance - positive sequence
        # compute with rounded values to prevent float uncertainty errors
        p_fe_1 = round(t_type.pfe * 1e3, DecimalDigits.POWER)  # W
        r_fe_1 = voltage_ref**2 / p_fe_1
        i_0_pu = t_type.curmg  # %
        z_m_1 = 100 / i_0_pu * pu2abs  # Ohm
        x_h_1 = (z_m_1 * r_fe_1) / math.sqrt(r_fe_1**2 - z_m_1**2)

        # Magnetising impedance - zero sequence
        # -> only available as separate quantity if wiring group is Y(N)y(n)
        if vector_group_l and vector_group_h in [WVectorGroup.Y, WVectorGroup.YN]:
            z_k_0 = t_type.uk0tr / 100 * pu2abs  # Ohm
            z_m_0 = z_k_0 * t_type.zx0hl_n  # Ohm

            r2x = t_type.rtox0_n
            # the dedicated resistance in parallel to the reactance
            if r2x > 0:
                r_fe_0 = z_m_0 * math.sqrt(1 + r2x**2)
                x_h_0 = (z_m_0 * r_fe_0) / math.sqrt(r_fe_0**2 - z_m_0**2)
            else:
                r_fe_0 = None
                x_h_0 = z_m_0
        else:
            r_fe_0 = None
            x_h_0 = None

        # Excursus
        # the real part of the complex magnetising impedance
        # r_m_0 = z_m_0 / math.sqrt(1 + 1/r2x**2)  # noqa: ERA001

        # i_00_pu = 100 / z_m_0 * pu2abs  # % # noqa: ERA001
        # p_fe0 = u_ref_h**2 / r_m_0  # W # noqa: ERA001
        return (r_fe_1, x_h_1, r_fe_0, x_h_0)

    @staticmethod
    def transformer_neutral_connection_hvlv(
        *,
        transformer: PFTypes.Transformer2W,
        vector_group: VectorGroup,
    ) -> tuple[bool, bool]:
        if "n" in vector_group.name.lower():
            if transformer.cneutcon == TrfNeutralConnectionType.ABC_N:
                return True, True
            if transformer.cneutcon == TrfNeutralConnectionType.HV:
                return True, False
            if transformer.cneutcon == TrfNeutralConnectionType.LV:
                return False, True
            if transformer.cneutcon == TrfNeutralConnectionType.HV_LV:
                return True, True
        return False, False  # corresponds to TrfNeutralConnectionType.NO

    @staticmethod
    def get_description(
        element: PFTypes.Terminal
        | PFTypes.LineBase
        | PFTypes.Element
        | PFTypes.Coupler
        | PFTypes.ExternalGrid
        | PFTypes.Fuse,
    ) -> tuple[bool, str]:
        desc = element.desc
        if desc:
            if desc[0] == "do_not_export":
                return False, ""

            return True, desc[0]

        return True, ""

    def create_loads(
        self,
        *,
        consumers: Sequence[PFTypes.Load],
        consumers_lv: Sequence[PFTypes.LoadLV],
        consumers_mv: Sequence[PFTypes.LoadMV],
        generators: Sequence[PFTypes.Generator],
        pv_systems: Sequence[PFTypes.PVSystem],
        grid_name: str,
    ) -> Sequence[Load]:
        loguru.logger.info("Creating loads...")
        normal_consumers = self.create_consumers_normal(consumers, grid_name=grid_name)
        lv_consumers = self.create_consumers_lv(consumers_lv, grid_name=grid_name)
        load_mvs = self.create_loads_mv(consumers_mv, grid_name=grid_name)
        gen_producers = self.create_producers_normal(generators, grid_name=grid_name)
        pv_producers = self.create_producers_pv(pv_systems, grid_name=grid_name)
        return self.pfi.list_from_sequences(
            normal_consumers,
            lv_consumers,
            load_mvs,
            gen_producers,
            pv_producers,
        )

    def create_consumers_normal(
        self,
        loads: Sequence[PFTypes.Load],
        /,
        *,
        grid_name: str,
    ) -> Sequence[Load]:
        loguru.logger.info("Creating normal consumers...")
        consumers = [self.create_consumer_normal(load, grid_name=grid_name) for load in loads]
        return self.pfi.filter_none(consumers)

    def create_consumer_normal(
        self,
        load: PFTypes.Load,
        /,
        *,
        grid_name: str,
    ) -> Load | None:
        power = self.calc_normal_load_power(load)
        phase_connection_type = (
            ConsolidatedLoadPhaseConnectionType[LoadPhaseConnectionType(load.phtech).name]
            if load.typ_id is not None
            else ConsolidatedLoadPhaseConnectionType.THREE_PH_D
        )
        if power is not None:
            return self.create_consumer(
                load,
                power=power,
                grid_name=grid_name,
                system_type=SystemType.FIXED_CONSUMPTION,
                phase_connection_type=phase_connection_type,
            )

        return None

    def create_consumers_lv(
        self,
        loads: Sequence[PFTypes.LoadLV],
        /,
        *,
        grid_name: str,
    ) -> Sequence[Load]:
        loguru.logger.info("Creating low voltage consumers...")
        consumers_lv_parts = [self.create_consumers_lv_parts(load, grid_name=grid_name) for load in loads]
        return self.pfi.list_from_sequences(*consumers_lv_parts)

    def create_consumers_lv_parts(
        self,
        load: PFTypes.LoadLV,
        /,
        *,
        grid_name: str,
    ) -> Sequence[Load]:
        loguru.logger.debug("Creating subconsumers for low voltage consumer {name}...", name=load.loc_name)
        powers = self.calc_load_lv_powers(load)
        sfx_pre = "" if len(powers) == 1 else "_({})"

        consumer_lv_parts = [
            self.create_consumer_lv_parts(load, grid_name=grid_name, power=power, sfx_pre=sfx_pre, index=i)
            for i, power in enumerate(powers)
        ]
        return self.pfi.list_from_sequences(*consumer_lv_parts)

    def create_consumer_lv_parts(
        self,
        load: PFTypes.LoadLV,
        /,
        *,
        grid_name: str,
        power: LoadLV,
        sfx_pre: str,
        index: int,
    ) -> Sequence[Load]:
        loguru.logger.debug(
            "Creating partial consumers for subconsumer {index} of low voltage consumer {name}...",
            index=index,
            name=load.loc_name,
        )
        phase_connection_type = ConsolidatedLoadPhaseConnectionType[LoadLVPhaseConnectionType(load.phtech).name]
        consumer_fixed = (
            self.create_consumer(
                load,
                power=power.fixed,
                grid_name=grid_name,
                system_type=SystemType.FIXED_CONSUMPTION,
                phase_connection_type=phase_connection_type,
                name_suffix=sfx_pre.format(index) + "_" + SystemType.FIXED_CONSUMPTION.name,
                load_model_default="Z",
            )
            if power.fixed.pow_app_abs != 0
            else None
        )
        consumer_night = (
            self.create_consumer(
                load,
                power=power.night,
                grid_name=grid_name,
                system_type=SystemType.NIGHT_STORAGE,
                phase_connection_type=phase_connection_type,
                name_suffix=sfx_pre.format(index) + "_" + SystemType.NIGHT_STORAGE.name,
                load_model_default="Z",
            )
            if power.night.pow_app_abs != 0
            else None
        )
        consumer_flex = (
            self.create_consumer(
                load,
                power=power.flexible,
                grid_name=grid_name,
                system_type=SystemType.VARIABLE_CONSUMPTION,
                phase_connection_type=phase_connection_type,
                name_suffix=sfx_pre.format(index) + "_" + SystemType.VARIABLE_CONSUMPTION.name,
                load_model_default="Z",
            )
            if power.flexible.pow_app_abs != 0
            else None
        )
        return self.pfi.filter_none([consumer_fixed, consumer_night, consumer_flex])

    def create_loads_mv(
        self,
        loads: Sequence[PFTypes.LoadMV],
        /,
        *,
        grid_name: str,
    ) -> Sequence[Load]:
        loguru.logger.info("Creating medium voltage loads...")
        loads_mv_ = [self.create_load_mv(load, grid_name=grid_name) for load in loads]
        loads_mv = self.pfi.list_from_sequences(*loads_mv_)
        return self.pfi.filter_none(loads_mv)

    def create_load_mv(
        self,
        load: PFTypes.LoadMV,
        /,
        *,
        grid_name: str,
    ) -> Sequence[Load | None]:
        power = self.calc_load_mv_power(load)
        loguru.logger.debug("Creating medium voltage load {name}...", name=load.loc_name)
        phase_connection_type = (
            ConsolidatedLoadPhaseConnectionType[LoadPhaseConnectionType(load.phtech).name]
            if load.typ_id is not None
            else ConsolidatedLoadPhaseConnectionType.THREE_PH_D
        )
        consumer = self.create_consumer(
            load,
            power=power.consumer,
            grid_name=grid_name,
            phase_connection_type=phase_connection_type,
            system_type=SystemType.FIXED_CONSUMPTION,
            name_suffix="_CONSUMER",
        )
        producer = self.create_producer(
            load,
            power=power.producer,
            gen_name=load.loc_name,
            grid_name=grid_name,
            phase_connection_type=phase_connection_type,
            system_type=SystemType.OTHER,
            name_suffix="_PRODUCER",
        )

        return [consumer, producer]

    def create_consumer(
        self,
        load: PFTypes.LoadBase,
        /,
        *,
        power: LoadPower,
        grid_name: str,
        system_type: SystemType,
        phase_connection_type: ConsolidatedLoadPhaseConnectionType,
        name_suffix: str = "",
        load_model_default: t.Literal["Z", "I", "P"] = "P",
    ) -> Load | None:
        l_name = self.pfi.create_name(load, grid_name=grid_name) + name_suffix
        loguru.logger.debug("Creating consumer {load_name}...", load_name=l_name)
        export, description = self.get_description(load)
        if not export:
            loguru.logger.warning("Consumer {load_name} not set for export. Skipping.", load_name=l_name)
            return None

        # get connected terminal
        bus = load.bus1
        if bus is None:
            loguru.logger.warning("Consumer {load_name} not connected to any bus. Skipping.", load_name=l_name)
            return None

        phase_id = bus.cPhInfo
        if phase_id == "SPN":
            loguru.logger.warning(
                "Load {load_name} is a 1-phase load which is currently not supported. Skipping.",
                load_name=load.loc_name,
            )
            return None

        terminal = bus.cterm
        t_name = self.pfi.create_name(terminal, grid_name=grid_name)

        phase_connections = self.get_load_phase_connections(
            phase_connection_type=phase_connection_type,
            bus=bus,
            grid_name=grid_name,
        )
        voltage_system_type = (
            VoltageSystemType[ElementVoltageSystemType(load.typ_id.systp).name]
            if load.typ_id is not None
            else VoltageSystemType[TerminalVoltageSystemType(terminal.systype).name]
        )

        # Rated power and load models for active and reactive power
        power = power.limit_phases(n_phases=phase_connections.n_phases)
        rated_power = power.as_rated_power()
        loguru.logger.debug(
            "{load_name}: there is no real rated power, it is calculated based on current power.",
            load_name=l_name,
        )

        u_0 = self.reference_voltage_for_load_model_of(load, u_nom=terminal.uknom * Exponents.VOLTAGE)
        load_model_p = self.load_model_of(load, specifier="p", default=load_model_default, u_0=u_0)
        load_model_q = self.load_model_of(load, specifier="q", default=load_model_default, u_0=u_0)

        return Load(
            name=l_name,
            node=t_name,
            description=description,
            rated_power=rated_power,
            active_power_model=load_model_p,
            reactive_power_model=load_model_q,
            phase_connections=phase_connections,
            type=LoadType.CONSUMER,
            system_type=system_type,
            voltage_system_type=voltage_system_type,
        )

    @staticmethod
    def reference_voltage_for_load_model_of(
        load: PFTypes.LoadBase | PFTypes.LoadLVP | PFTypes.GeneratorBase,
        /,
        *,
        u_nom: pydantic.confloat(ge=0),  # type: ignore[valid-type]
    ) -> pydantic.confloat(ge=0):  # type: ignore[valid-type]
        if load.GetClassName() == PFClassId.LOAD_LV.value:
            load = t.cast("PFTypes.LoadLV", load)
            return load.ulini * Exponents.VOLTAGE
        if load.GetClassName() == PFClassId.LOAD_LV_PART.value:
            load = t.cast("PFTypes.LoadLVP", load)
            return load.ulini * Exponents.VOLTAGE
        if load.GetClassName() == PFClassId.LOAD.value:
            load = t.cast("PFTypes.Load", load)
            return load.u0 * u_nom
        return u_nom

    @staticmethod
    def load_model_of(
        load: PFTypes.LoadBase | PFTypes.GeneratorBase,
        /,
        *,
        u_0: pydantic.confloat(ge=0),  # type: ignore[valid-type]
        specifier: t.Literal["p", "q"],
        default: t.Literal["Z", "I", "P"] = "P",
    ) -> LoadModel:
        u_0 = Qc.sym_three_phase_voltage(u_0)
        load_type = t.cast("PFTypes.LoadBase", load).typ_id if load.GetClassName() in LOAD_CLASSES else None
        if load_type is not None:
            if load_type.loddy != FULL_DYNAMIC:
                loguru.logger.warning(
                    "Please check load model setting of {load_name} for RMS simulation.",
                    load_name=load.loc_name,
                )
                loguru.logger.info(
                    r"Consider to set 100% dynamic mode, but with time constants =0 (=same static model for RMS).",
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
                    u_0=u_0,
                )

            if specifier == "q":
                return LoadModel(
                    name=name,
                    c_p=load_type.aQ,
                    c_i=load_type.bQ,
                    exp_p=load_type.kqu0,
                    exp_i=load_type.kqu1,
                    exp_z=load_type.kqu,
                    u_0=u_0,
                )

            msg = "unreachable"
            raise RuntimeError(msg)

        if default == "I":
            return LoadModel(c_i=1, c_p=0, u_0=u_0)

        if default == "P":
            return LoadModel(c_i=0, c_p=1, u_0=u_0)

        return LoadModel(c_i=0, c_p=0, u_0=u_0)

    def create_producers_normal(
        self,
        generators: Sequence[PFTypes.Generator],
        /,
        *,
        grid_name: str,
    ) -> Sequence[Load]:
        loguru.logger.info("Creating normal producers...")
        producers = [self.create_producer_normal(generator, grid_name=grid_name) for generator in generators]
        return self.pfi.filter_none(producers)

    def create_producer_normal(
        self,
        generator: PFTypes.Generator,
        /,
        *,
        grid_name: str,
    ) -> Load | None:
        power = self.calc_normal_gen_power(generator)
        gen_name = self.pfi.create_generator_name(generator)
        system_type = SystemType[GeneratorSystemType(generator.aCategory).name]
        phase_connection_type = ConsolidatedLoadPhaseConnectionType[GeneratorPhaseConnectionType(generator.phtech).name]

        return self.create_producer(
            generator,
            power=power,
            gen_name=gen_name,
            grid_name=grid_name,
            phase_connection_type=phase_connection_type,
            system_type=system_type,
            load_model_default="P",
        )

    def create_producers_pv(
        self,
        generators: Sequence[PFTypes.PVSystem],
        /,
        *,
        grid_name: str,
    ) -> Sequence[Load]:
        loguru.logger.info("Creating PV producers...")
        producers = [self.create_producer_pv(generator, grid_name=grid_name) for generator in generators]
        return self.pfi.filter_none(producers)

    def create_producer_pv(
        self,
        generator: PFTypes.PVSystem,
        /,
        *,
        grid_name: str,
    ) -> Load | None:
        power = self.calc_normal_gen_power(generator)
        gen_name = self.pfi.create_generator_name(generator)
        phase_connection_type = ConsolidatedLoadPhaseConnectionType[GeneratorPhaseConnectionType(generator.phtech).name]
        system_type = SystemType.PV
        return self.create_producer(
            generator,
            power=power,
            gen_name=gen_name,
            grid_name=grid_name,
            phase_connection_type=phase_connection_type,
            system_type=system_type,
            load_model_default="P",
        )

    def get_external_controller_name(
        self,
        gen: PFTypes.Generator | PFTypes.PVSystem,
        /,
    ) -> str | None:
        controller = gen.c_pstac
        if controller is None:
            return None

        return self.pfi.create_generator_name(gen, generator_name=controller.loc_name)

    def calc_normal_gen_power(
        self,
        gen: PFTypes.Generator | PFTypes.PVSystem,
        /,
    ) -> LoadPower:
        pow_app = gen.sgn * gen.ngnum
        cos_phi = gen.cosn
        # in PF for producer: ind. cos_phi = over excited; cap. cos_phi = under excited
        pow_fac_dir = PowerFactorDirection.UE if gen.pf_recap else PowerFactorDirection.OE
        phase_connection_type = ConsolidatedLoadPhaseConnectionType[GeneratorPhaseConnectionType(gen.phtech).name]
        return LoadPower.from_sc_sym(
            pow_app=pow_app,
            cos_phi=cos_phi,
            pow_fac_dir=pow_fac_dir,
            scaling=gen.scale0,
            phase_connection_type=phase_connection_type,
        )

    def create_producer(
        self,
        generator: PFTypes.GeneratorBase | PFTypes.LoadMV,
        /,
        *,
        gen_name: str,
        power: LoadPower,
        grid_name: str,
        system_type: SystemType,
        phase_connection_type: ConsolidatedLoadPhaseConnectionType,
        name_suffix: str = "",
        load_model_default: t.Literal["Z", "I", "P"] = "P",
    ) -> Load | None:
        gen_name = self.pfi.create_name(generator, grid_name=grid_name, element_name=gen_name) + name_suffix
        loguru.logger.debug("Creating producer {gen_name}...", gen_name=gen_name)
        export, description = self.get_description(generator)
        if not export:
            loguru.logger.warning(
                "Generator {gen_name} not set for export. Skipping.",
                gen_name=gen_name,
            )
            return None

        # get connected terminal
        bus = generator.bus1
        if bus is None:
            loguru.logger.warning("Generator {gen_name} not connected to any bus. Skipping.", gen_name=gen_name)
            return None

        terminal = bus.cterm
        t_name = self.pfi.create_name(terminal, grid_name=grid_name)

        # Rated power and load models for active and reactive power
        rated_power = power.as_rated_power()

        u_0 = self.reference_voltage_for_load_model_of(generator, u_nom=terminal.uknom * Exponents.VOLTAGE)
        load_model_p = self.load_model_of(generator, specifier="p", default=load_model_default, u_0=u_0)
        load_model_q = self.load_model_of(generator, specifier="q", default=load_model_default, u_0=u_0)

        phase_connections = self.get_load_phase_connections(
            phase_connection_type=phase_connection_type,
            bus=bus,
            grid_name=grid_name,
        )

        return Load(
            name=gen_name,
            node=t_name,
            description=description,
            rated_power=rated_power,
            active_power_model=load_model_p,
            reactive_power_model=load_model_q,
            phase_connections=phase_connections,
            type=LoadType.PRODUCER,
            system_type=system_type,
            voltage_system_type=VoltageSystemType.AC,
        )

    def create_topology_case(
        self,
        *,
        meta: Meta,
        data: PowerFactoryData,
    ) -> TopologyCase:
        loguru.logger.debug("Creating topology case...")
        switch_states = self.create_switch_states(data.switches, grid_name=data.grid_name)
        coupler_states = self.create_coupler_states(data.couplers, grid_name=data.grid_name)
        bfuse_states = self.create_bfuse_states(data.bfuses, grid_name=data.grid_name)
        efuse_states = self.create_efuse_states(data.efuses, grid_name=data.grid_name)
        elements: Sequence[ElementBase] = self.pfi.list_from_sequences(
            data.loads,
            data.loads_lv,
            data.loads_mv,
            data.generators,
            data.pv_systems,
            data.external_grids,
        )
        node_power_on_states = self.create_node_power_on_states(data.terminals, grid_name=data.grid_name)
        line_power_on_states = self.create_element_power_on_states(data.lines, grid_name=data.grid_name)
        transformer_2w_power_on_states = self.create_element_power_on_states(
            data.transformers_2w,
            grid_name=data.grid_name,
        )
        element_power_on_states = self.create_element_power_on_states(elements, grid_name=data.grid_name)
        power_on_states = self.pfi.list_from_sequences(
            switch_states,
            coupler_states,
            bfuse_states,
            efuse_states,
            node_power_on_states,
            line_power_on_states,
            transformer_2w_power_on_states,
            element_power_on_states,
        )
        power_on_states = self.merge_power_on_states(power_on_states)

        return TopologyCase(meta=meta, elements=power_on_states)

    def merge_power_on_states(
        self,
        power_on_states: Sequence[ElementState],
        /,
    ) -> Sequence[ElementState]:
        entry_names = {entry.name for entry in power_on_states}
        return [self.merge_entries(entry_name, power_on_states=power_on_states) for entry_name in entry_names]

    def merge_entries(
        self,
        entry_name: str,
        /,
        *,
        power_on_states: Sequence[ElementState],
    ) -> ElementState:
        entries = {entry for entry in power_on_states if entry.name == entry_name}
        disabled = any(entry.disabled for entry in entries)
        open_switches = tuple(itertools.chain.from_iterable([entry.open_switches for entry in entries]))
        return ElementState(name=entry_name, disabled=disabled, open_switches=open_switches)

    def create_switch_states(
        self,
        switches: Sequence[PFTypes.Switch],
        /,
        *,
        grid_name: str,
    ) -> Sequence[ElementState]:
        """Create element states for all type of elements based on if the switch is open.

        The element states contain a node reference.

        Arguments:
            switches {Sequence[PFTypes.Switch]} -- sequence of PowerFactory objects of type Switch

        Keyword Arguments:
            grid_name {str} -- the name of the related grid
        Returns:
            Sequence[ElementState] -- set of element states
        """

        loguru.logger.info("Creating switch states...")
        states = [self.create_switch_state(switch, grid_name=grid_name) for switch in switches]
        return self.pfi.filter_none(states)

    def create_switch_state(
        self,
        switch: PFTypes.Switch,
        /,
        *,
        grid_name: str,
    ) -> ElementState | None:
        if not switch.isclosed:
            cub = switch.fold_id
            element = cub.obj_id
            if element is not None:
                terminal = cub.cterm
                node_name = self.pfi.create_name(terminal, grid_name=grid_name)
                element_name = self.pfi.create_name(element, grid_name=grid_name)
                loguru.logger.debug(
                    "Creating switch state {node_name}-{element_name}...",
                    node_name=node_name,
                    element_name=element_name,
                )
                return ElementState(name=element_name, open_switches=(node_name,))

        return None

    def create_coupler_states(
        self,
        couplers: Sequence[PFTypes.Coupler],
        /,
        *,
        grid_name: str,
    ) -> Sequence[ElementState]:
        """Create element states for all type of elements based on if the coupler is open.

        The element states contain a node reference.

        Arguments:
            couplers {Sequence[PFTypes.Coupler]} -- sequence of PowerFactory objects of type Coupler

        Keyword Arguments:
            grid_name {str} -- the name of the related grid

        Returns:
            Sequence[ElementState] -- set of element states
        """
        loguru.logger.info("Creating coupler states...")
        states = [self.create_coupler_state(coupler, grid_name=grid_name) for coupler in couplers]
        return self.pfi.filter_none(states)

    def create_coupler_state(
        self,
        coupler: PFTypes.Coupler,
        /,
        *,
        grid_name: str,
    ) -> ElementState | None:
        if not coupler.isclosed:
            element_name = self.pfi.create_name(coupler, grid_name=grid_name)
            loguru.logger.debug(
                "Creating coupler state {element_name}...",
                element_name=element_name,
            )
            return ElementState(name=element_name, disabled=True)

        return None

    def create_node_power_on_states(
        self,
        terminals: Sequence[PFTypes.Terminal],
        /,
        *,
        grid_name: str,
    ) -> Sequence[ElementState]:
        """Create element states based on if the connected nodes are out of service.

        The element states contain a node reference.

        Arguments:
            terminals {Sequence[PFTypes.Terminal]} -- sequence of PowerFactory objects of type Terminal

        Keyword Arguments:
            grid_name {str} -- the name of the related grid

        Returns:
            Sequence[ElementState] -- set of element states
        """

        loguru.logger.info("Creating node power on states...")
        states = [self.create_node_power_on_state(terminal, grid_name=grid_name) for terminal in terminals]
        return self.pfi.filter_none(states)

    def create_node_power_on_state(
        self,
        terminal: PFTypes.Terminal,
        /,
        *,
        grid_name: str,
    ) -> ElementState | None:
        if terminal.outserv:
            node_name = self.pfi.create_name(terminal, grid_name=grid_name)
            loguru.logger.debug(
                "Creating node power on state {node_name}...",
                node_name=node_name,
            )
            return ElementState(name=node_name, disabled=True)

        return None

    def create_element_power_on_states(
        self,
        elements: Sequence[ElementBase | PFTypes.Line | PFTypes.Transformer2W],
        /,
        *,
        grid_name: str,
    ) -> Sequence[ElementState]:
        """Create element states for one-sided connected elements based on if the elements are out of service.

        The element states contain no node reference.

        Arguments:
            elements {Sequence[ElementBase} -- sequence of one-sided connected PowerFactory objects

        Keyword Arguments:
            grid_name {str} -- the name of the related grid

        Returns:
            Sequence[ElementState] -- set of element states
        """
        loguru.logger.info("Creating element power on states...")
        states = [self.create_element_power_on_state(element, grid_name=grid_name) for element in elements]
        return self.pfi.filter_none(states)

    def create_element_power_on_state(
        self,
        element: ElementBase | PFTypes.Line | PFTypes.Transformer2W,
        /,
        *,
        grid_name: str,
    ) -> ElementState | None:
        if element.outserv:
            element_name = self.pfi.create_name(element, grid_name=grid_name)
            loguru.logger.debug(
                "Creating element power on state {element_name}...",
                element_name=element_name,
            )
            return ElementState(name=element_name, disabled=True)

        return None

    def create_bfuse_states(
        self,
        fuses: Sequence[PFTypes.BFuse],
        /,
        *,
        grid_name: str,
    ) -> Sequence[ElementState]:
        """Create element states for all type of elements based on if the fuse is open.

        The element states contain a node reference.

        Arguments:
            fuses {Sequence[PFTypes.BFuse]} -- sequence of PowerFactory objects of type Fuse

        Keyword Arguments:
            grid_name {str} -- the name of the related grid

        Returns:
            Sequence[ElementState] -- set of element states
        """
        loguru.logger.info("Creating fuse states...")
        states = [self.create_bfuse_state(fuse, grid_name=grid_name) for fuse in fuses]
        return self.pfi.filter_none(states)

    def create_bfuse_state(
        self,
        fuse: PFTypes.BFuse,
        /,
        *,
        grid_name: str,
    ) -> ElementState | None:
        if not fuse.on_off or fuse.outserv:
            element_name = self.pfi.create_name(fuse, grid_name=grid_name)
            loguru.logger.debug(
                "Creating fuse state {element_name}...",
                element_name=element_name,
            )
            return ElementState(name=element_name, disabled=True)

        return None

    def create_efuse_states(
        self,
        fuses: Sequence[PFTypes.EFuse],
        /,
        *,
        grid_name: str,
    ) -> Sequence[ElementState]:
        """Create element states for all type of elements based on if the fuse is open.

        The element states contain a node reference.

        Arguments:
            fuses {Sequence[PFTypes.EFuse]} -- sequence of PowerFactory objects of type Fuse

        Keyword Arguments:
            grid_name {str} -- the name of the related grid

        Returns:
            Sequence[ElementState] -- set of element states
        """

        loguru.logger.info("Creating fuse states...")
        states = [self.create_efuse_state(fuse, grid_name=grid_name) for fuse in fuses]
        return self.pfi.filter_none(states)

    def create_efuse_state(
        self,
        fuse: PFTypes.EFuse,
        /,
        *,
        grid_name: str,
    ) -> ElementState | None:
        if not fuse.on_off or fuse.outserv:
            cub = fuse.fold_id
            element = cub.obj_id  # also accessible via 'fuse.cbranch'
            if element is not None:
                terminal = cub.cterm  # also accessible via 'fuse.cn_bus'
                node_name = self.pfi.create_name(terminal, grid_name=grid_name)
                element_name = self.pfi.create_name(element, grid_name=grid_name)
                loguru.logger.debug(
                    "Creating fuse state {node_name}-{element_name}...",
                    node_name=node_name,
                    element_name=element_name,
                )
                loguru.logger.warning(
                    "Element fuse at {node_name}-{element_name}: Exporter considers element as disconnected due to open fuse, but in PowerFactory element will still be handled as connected.",
                    node_name=node_name,
                    element_name=element_name,
                )
                return ElementState(name=element_name, open_switches=(node_name,))

        return None

    def create_steadystate_case(
        self,
        *,
        meta: Meta,
        data: PowerFactoryData,
    ) -> SteadystateCase:
        loguru.logger.info("Creating steadystate case...")
        loads = self.create_loads_ssc(
            consumers=data.loads,
            consumers_lv=data.loads_lv,
            consumers_mv=data.loads_mv,
            generators=data.generators,
            pv_systems=data.pv_systems,
            grid_name=data.grid_name,
        )
        transformers = self.create_transformers_ssc(
            data.transformers_2w,
            grid_name=data.grid_name,
        )
        external_grids = self.create_external_grid_ssc(
            data.external_grids,
            grid_name=data.grid_name,
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
        /,
        *,
        grid_name: str,
    ) -> Sequence[TransformerSSC]:
        loguru.logger.info("Creating transformers steadystate case...")
        transformers_2w_sscs = self.create_transformers_2w_ssc(pf_transformers_2w, grid_name=grid_name)
        return self.pfi.list_from_sequences(transformers_2w_sscs)

    def create_transformers_2w_ssc(
        self,
        pf_transformers_2w: Sequence[PFTypes.Transformer2W],
        /,
        *,
        grid_name: str,
    ) -> Sequence[TransformerSSC]:
        loguru.logger.info("Creating 2-winding transformers steadystate cases...")
        transformers_2w_sscs = [
            self.create_transformer_2w_ssc(pf_transformer_2w, grid_name=grid_name)
            for pf_transformer_2w in pf_transformers_2w
        ]
        return self.pfi.filter_none(transformers_2w_sscs)

    def create_transformer_2w_ssc(
        self,
        pf_transformer_2w: PFTypes.Transformer2W,
        /,
        *,
        grid_name: str,
    ) -> TransformerSSC | None:
        name = self.pfi.create_name(pf_transformer_2w, grid_name=grid_name)
        loguru.logger.debug(
            "Creating 2-winding transformer {transformer_name} steadystate case...",
            transformer_name=name,
        )
        export, _ = self.get_description(pf_transformer_2w)
        if not export:
            loguru.logger.warning("Transformer {transformer_name} not set for export. Skipping.", transformer_name=name)
            return None

        # Transformer Tap Changer
        t_type = pf_transformer_2w.typ_id
        tap_pos = None if t_type is None else pf_transformer_2w.nntap

        return TransformerSSC(name=name, tap_pos=tap_pos)

    def create_external_grid_ssc(
        self,
        ext_grids: Sequence[PFTypes.ExternalGrid],
        /,
        *,
        grid_name: str,
    ) -> Sequence[ExternalGridSSC]:
        loguru.logger.info("Creating external grids steadystate case...")
        ext_grid_sscs = [self.create_external_grid_ssc_state(grid, grid_name=grid_name) for grid in ext_grids]
        return self.pfi.filter_none(ext_grid_sscs)

    def create_external_grid_ssc_state(
        self,
        ext_grid: PFTypes.ExternalGrid,
        /,
        *,
        grid_name: str,
    ) -> ExternalGridSSC | None:
        name = self.pfi.create_name(ext_grid, grid_name=grid_name)
        loguru.logger.debug("Creating external grid {ext_grid_name} steadystate case...", ext_grid_name=name)
        export, _ = self.get_description(ext_grid)
        if not export:
            loguru.logger.warning("External grid {ext_grid_name} not set for export. Skipping.", ext_grid_name=name)
            return None

        if ext_grid.bus1 is None:
            loguru.logger.warning(
                "External grid {ext_grid_name} not connected to any bus. Skipping.",
                ext_grid_name=name,
            )
            return None

        g_type = GridType(ext_grid.bustp)
        if g_type == GridType.SL:
            u_0 = ext_grid.usetp * ext_grid.bus1.cterm.uknom * Exponents.VOLTAGE  # sym line-to-line voltage
            return ExternalGridSSC(
                name=name,
                u_0=Qc.sym_three_phase_voltage(u_0),
                phi_0=Qc.sym_three_phase_angle(ext_grid.phiini),
            )

        if g_type == GridType.PV:
            u_0 = ext_grid.usetp * ext_grid.bus1.cterm.uknom * Exponents.VOLTAGE  # sym line-to-line voltage
            p_0 = ext_grid.pgini * Exponents.POWER
            return ExternalGridSSC(
                name=name,
                u_0=Qc.sym_three_phase_voltage(u_0),
                p_0=Qc.sym_three_phase_active_power(p_0),
            )

        if g_type == GridType.PQ:
            p_0 = ext_grid.pgini * Exponents.POWER
            q_0 = ext_grid.qgini * Exponents.POWER
            return ExternalGridSSC(
                name=name,
                p_0=Qc.sym_three_phase_active_power(p_0),
                q_0=Qc.sym_three_phase_reactive_power(q_0),
            )

        return ExternalGridSSC(name=name)

    def create_loads_ssc(
        self,
        *,
        consumers: Sequence[PFTypes.Load],
        consumers_lv: Sequence[PFTypes.LoadLV],
        consumers_mv: Sequence[PFTypes.LoadMV],
        generators: Sequence[PFTypes.Generator],
        pv_systems: Sequence[PFTypes.PVSystem],
        grid_name: str,
    ) -> Sequence[LoadSSC]:
        loguru.logger.info("Creating loads steadystate case...")
        normal_consumers = self.create_consumers_ssc_normal(consumers, grid_name=grid_name)
        lv_consumers = self.create_consumers_ssc_lv(consumers_lv, grid_name=grid_name)
        mv_consumers = self.create_loads_ssc_mv(consumers_mv, grid_name=grid_name)
        gen_producers = self.create_producers_ssc(generators, grid_name=grid_name)
        pv_producers = self.create_producers_ssc(pv_systems, grid_name=grid_name)
        return self.pfi.list_from_sequences(normal_consumers, lv_consumers, mv_consumers, gen_producers, pv_producers)

    def create_consumers_ssc_normal(
        self,
        loads: Sequence[PFTypes.Load],
        /,
        *,
        grid_name: str,
    ) -> Sequence[LoadSSC]:
        loguru.logger.info("Creating normal consumers steadystate case...")
        consumers_ssc = [self.create_consumer_ssc_normal(load, grid_name=grid_name) for load in loads]
        return self.pfi.filter_none(consumers_ssc)

    def create_consumer_ssc_normal(
        self,
        load: PFTypes.Load,
        /,
        *,
        grid_name: str,
    ) -> LoadSSC | None:
        phase_connection_type = ConsolidatedLoadPhaseConnectionType[LoadPhaseConnectionType(load.phtech).name]
        power = self.calc_normal_load_power(load)
        if power is not None:
            return self.create_consumer_ssc(
                load,
                power=power,
                grid_name=grid_name,
                phase_connection_type=phase_connection_type,
            )

        return None

    def calc_normal_load_power(
        self,
        load: PFTypes.Load,
        /,
    ) -> LoadPower | None:
        loguru.logger.debug("Calculating power for normal load {load_name}...", load_name=load.loc_name)
        power = self.calc_normal_load_power_sym(load) if not load.i_sym else self.calc_normal_load_power_asym(load)

        if power:
            return power

        loguru.logger.warning("Power is not set for load {load_name}. Skipping.", load_name=load.loc_name)
        return None

    def calc_normal_load_power_sym(  # noqa: PLR0911
        self,
        load: PFTypes.Load,
        /,
    ) -> LoadPower | None:
        load_type = load.mode_inp
        scaling = load.scale0
        u_nom = None if load.bus1 is None else load.bus1.cterm.uknom
        pow_fac_dir = PowerFactorDirection.OE if load.pf_recap else PowerFactorDirection.UE
        phase_connection_type = ConsolidatedLoadPhaseConnectionType[LoadPhaseConnectionType(load.phtech).name]
        if load_type in ("DEF", "PQ"):
            return LoadPower.from_pq_sym(
                pow_act=load.plini,
                pow_react=load.qlini,
                scaling=scaling,
                phase_connection_type=phase_connection_type,
            )

        if load_type == "PC":
            return LoadPower.from_pc_sym(
                pow_act=load.plini,
                cos_phi=load.coslini,
                pow_fac_dir=pow_fac_dir,
                scaling=scaling,
                phase_connection_type=phase_connection_type,
            )

        if load_type == "IC":
            if u_nom is not None:
                return LoadPower.from_ic_sym(
                    voltage=load.u0 * u_nom,
                    current=load.ilini,
                    cos_phi=load.coslini,
                    pow_fac_dir=pow_fac_dir,
                    scaling=scaling,
                    phase_connection_type=phase_connection_type,
                )

            loguru.logger.warning(
                "Load {load_name} is not connected to grid. Can not calculate power based on current and cos_phi as voltage is missing. Skipping.",
                load_name=load.loc_name,
            )
            return None

        if load_type == "SC":
            return LoadPower.from_sc_sym(
                pow_app=load.slini,
                cos_phi=load.coslini,
                pow_fac_dir=pow_fac_dir,
                scaling=scaling,
                phase_connection_type=phase_connection_type,
            )

        if load_type == "QC":
            return LoadPower.from_qc_sym(
                pow_react=load.qlini,
                cos_phi=load.coslini,
                scaling=scaling,
                phase_connection_type=phase_connection_type,
            )

        if load_type == "IP":
            if u_nom is not None:
                return LoadPower.from_ip_sym(
                    voltage=load.u0 * u_nom,
                    current=load.ilini,
                    pow_act=load.plini,
                    pow_fac_dir=pow_fac_dir,
                    scaling=scaling,
                    phase_connection_type=phase_connection_type,
                )
            loguru.logger.warning(
                "Load {load_name} is not connected to grid. Can not calculate power based on current and active power as voltage is missing. Skipping.",
                load_name=load.loc_name,
            )
            return None

        if load_type == "SP":
            return LoadPower.from_sp_sym(
                pow_app=load.slini,
                pow_act=load.plini,
                pow_fac_dir=pow_fac_dir,
                scaling=scaling,
                phase_connection_type=phase_connection_type,
            )

        if load_type == "SQ":
            return LoadPower.from_sq_sym(
                pow_app=load.slini,
                pow_react=load.qlini,
                scaling=scaling,
                phase_connection_type=phase_connection_type,
            )

        msg = "unreachable"
        raise RuntimeError(msg)

    def calc_normal_load_power_asym(  # noqa: PLR0911
        self,
        load: PFTypes.Load,
        /,
    ) -> LoadPower | None:
        load_type = load.mode_inp
        scaling = load.scale0
        u_nom = None if load.bus1 is None else load.bus1.cterm.uknom
        pow_fac_dir = PowerFactorDirection.OE if load.pf_recap else PowerFactorDirection.UE
        if load_type in ("DEF", "PQ"):
            return LoadPower.from_pq_asym(
                pow_acts=(load.plinir, load.plinis, load.plinit),
                pow_reacts=(load.qlinir, load.qlinis, load.qlinit),
                scaling=scaling,
            )

        if load_type == "PC":
            return LoadPower.from_pc_asym(
                pow_acts=(load.plinir, load.plinis, load.plinit),
                cos_phis=(load.coslinir, load.coslinis, load.coslinit),
                pow_fac_dir=pow_fac_dir,
                scaling=scaling,
            )

        if load_type == "IC":
            if u_nom is not None:
                return LoadPower.from_ic_asym(
                    voltage=load.u0 * u_nom,
                    currents=(load.ilinir, load.ilinis, load.ilinit),
                    cos_phis=(load.coslinir, load.coslinis, load.coslinit),
                    pow_fac_dir=pow_fac_dir,
                    scaling=scaling,
                )
            loguru.logger.warning(
                "Load {load_name} is not connected to grid. Can not calculate power based on current and cos_phi as voltage is missing. Skipping.",
                load_name=load.loc_name,
            )
            return None

        if load_type == "SC":
            return LoadPower.from_sc_asym(
                pow_apps=(load.slinir, load.slinis, load.slinit),
                cos_phis=(load.coslinir, load.coslinis, load.coslinit),
                pow_fac_dir=pow_fac_dir,
                scaling=scaling,
            )

        if load_type == "QC":
            return LoadPower.from_qc_asym(
                pow_reacts=(load.qlinir, load.qlinis, load.qlinit),
                cos_phis=(load.coslinir, load.coslinis, load.coslinit),
                scaling=scaling,
            )

        if load_type == "IP":
            if u_nom is not None:
                return LoadPower.from_ip_asym(
                    voltage=load.u0 * u_nom,
                    currents=(load.ilinir, load.ilinis, load.ilinit),
                    pow_acts=(load.plinir, load.plinis, load.plinit),
                    pow_fac_dir=pow_fac_dir,
                    scaling=scaling,
                )
            loguru.logger.warning(
                "Load {load_name} is not connected to grid. Can not calculate power based on current and active power as voltage is missing. Skipping.",
                load_name=load.loc_name,
            )
            return None

        if load_type == "SP":
            return LoadPower.from_sp_asym(
                pow_apps=(load.slinir, load.slinis, load.slinit),
                pow_acts=(load.plinir, load.plinis, load.plinit),
                pow_fac_dir=pow_fac_dir,
                scaling=scaling,
            )

        if load_type == "SQ":
            return LoadPower.from_sq_asym(
                pow_apps=(load.slinir, load.slinis, load.slinit),
                pow_reacts=(load.qlinir, load.qlinis, load.qlinit),
                scaling=scaling,
            )

        msg = "unreachable"
        raise RuntimeError(msg)

    def create_consumers_ssc_lv(
        self,
        loads: Sequence[PFTypes.LoadLV],
        /,
        *,
        grid_name: str,
    ) -> Sequence[LoadSSC]:
        loguru.logger.info("Creating low voltage consumers steadystate case...")
        consumers_ssc_lv_parts = [self.create_consumers_ssc_lv_parts(load, grid_name=grid_name) for load in loads]
        return list(itertools.chain.from_iterable(consumers_ssc_lv_parts))

    def create_consumers_ssc_lv_parts(
        self,
        load: PFTypes.LoadLV,
        /,
        *,
        grid_name: str,
    ) -> Sequence[LoadSSC]:
        powers = self.calc_load_lv_powers(load)
        sfx_pre = "" if len(powers) == 1 else "_({})"

        consumer_ssc_lv_parts = [
            self.create_consumer_ssc_lv_parts(load, grid_name=grid_name, power=power, sfx_pre=sfx_pre, index=i)
            for i, power in enumerate(powers)
        ]
        return list(itertools.chain.from_iterable(consumer_ssc_lv_parts))

    def create_consumer_ssc_lv_parts(
        self,
        load: PFTypes.LoadLV,
        /,
        *,
        grid_name: str,
        power: LoadLV,
        sfx_pre: str,
        index: int,
    ) -> Sequence[LoadSSC]:
        phase_connection_type = ConsolidatedLoadPhaseConnectionType[LoadLVPhaseConnectionType(load.phtech).name]
        consumer_fixed_ssc = (
            self.create_consumer_ssc(
                load,
                power=power.fixed,
                grid_name=grid_name,
                phase_connection_type=phase_connection_type,
                name_suffix=sfx_pre.format(index) + "_" + SystemType.FIXED_CONSUMPTION.name,
            )
            if power.fixed.pow_app_abs != 0
            else None
        )
        consumer_night_ssc = (
            self.create_consumer_ssc(
                load,
                power=power.night,
                grid_name=grid_name,
                phase_connection_type=phase_connection_type,
                name_suffix=sfx_pre.format(index) + "_" + SystemType.NIGHT_STORAGE.name,
            )
            if power.night.pow_app_abs != 0
            else None
        )
        consumer_flexible_ssc = (
            self.create_consumer_ssc(
                load,
                power=power.flexible_avg,
                grid_name=grid_name,
                phase_connection_type=phase_connection_type,
                name_suffix=sfx_pre.format(index) + "_" + SystemType.VARIABLE_CONSUMPTION.name,
            )
            if power.flexible.pow_app_abs != 0
            else None
        )
        return self.pfi.filter_none([consumer_fixed_ssc, consumer_night_ssc, consumer_flexible_ssc])

    def calc_load_lv_powers(
        self,
        load: PFTypes.LoadLV,
        /,
    ) -> Sequence[LoadLV]:
        subloads = self.pfi.subloads_of(load)
        if not subloads:
            return [self.calc_load_lv_power(load)]

        return [self.calc_load_lv_power_sym(sl) for sl in subloads]

    def calc_load_lv_power(
        self,
        load: PFTypes.LoadLV,
        /,
    ) -> LoadLV:
        loguru.logger.debug("Calculating power for low voltage load {load_name}...", load_name=load.loc_name)
        scaling = load.scale0
        pow_fac_dir = PowerFactorDirection.OE if load.pf_recap else PowerFactorDirection.UE
        if not load.i_sym:
            power_fixed = self.calc_load_lv_power_fixed_sym(load, scaling=scaling)
        else:
            power_fixed = self.calc_load_lv_power_fixed_asym(load, scaling=scaling)

        phase_connection_type = ConsolidatedLoadPhaseConnectionType[LoadLVPhaseConnectionType(load.phtech).name]

        power_night = LoadPower.from_pq_sym(
            pow_act=load.pnight,
            pow_react=0,
            scaling=1,
            phase_connection_type=phase_connection_type,
        )
        power_flexible = LoadPower.from_sc_sym(
            pow_app=load.cSmax,
            cos_phi=load.ccosphi,
            pow_fac_dir=pow_fac_dir,
            scaling=1,
            phase_connection_type=phase_connection_type,
        )
        power_flexible_avg = LoadPower.from_sc_sym(
            pow_app=load.cSav,
            cos_phi=load.ccosphi,
            pow_fac_dir=pow_fac_dir,
            scaling=1,
            phase_connection_type=phase_connection_type,
        )
        return LoadLV(fixed=power_fixed, night=power_night, flexible=power_flexible, flexible_avg=power_flexible_avg)

    def calc_load_lv_power_sym(
        self,
        load: PFTypes.LoadLVP,
        /,
    ) -> LoadLV:
        phase_connection_type = ConsolidatedLoadPhaseConnectionType[LoadLVPhaseConnectionType(load.phtech).name]
        power_fixed = self.calc_load_lv_power_fixed_sym(load, scaling=1)
        power_night = LoadPower.from_pq_sym(
            pow_act=load.pnight,
            pow_react=0,
            scaling=1,
            phase_connection_type=phase_connection_type,
        )
        pow_fac_dir = PowerFactorDirection.OE if load.pf_recap else PowerFactorDirection.UE
        power_flexible = LoadPower.from_sc_sym(
            pow_app=load.cSmax,
            cos_phi=load.ccosphi,
            pow_fac_dir=pow_fac_dir,
            scaling=1,
            phase_connection_type=phase_connection_type,
        )
        power_flexible_avg = LoadPower.from_sc_sym(
            pow_app=load.cSav,
            cos_phi=load.ccosphi,
            pow_fac_dir=pow_fac_dir,
            scaling=1,
            phase_connection_type=phase_connection_type,
        )
        return LoadLV(fixed=power_fixed, night=power_night, flexible=power_flexible, flexible_avg=power_flexible_avg)

    def calc_load_lv_power_fixed_sym(
        self,
        load: PFTypes.LoadLV | PFTypes.LoadLVP,
        /,
        *,
        scaling: float,
    ) -> LoadPower:
        load_type = load.iopt_inp
        pow_fac_dir = PowerFactorDirection.OE if load.pf_recap else PowerFactorDirection.UE
        phase_connection_type = ConsolidatedLoadPhaseConnectionType[LoadLVPhaseConnectionType(load.phtech).name]
        if load_type == IOpt.S_COSPHI:
            return LoadPower.from_sc_sym(
                pow_app=load.slini,
                cos_phi=load.coslini,
                pow_fac_dir=pow_fac_dir,
                scaling=scaling,
                phase_connection_type=phase_connection_type,
            )

        if load_type == IOpt.P_COSPHI:
            return LoadPower.from_pc_sym(
                pow_act=load.plini,
                cos_phi=load.coslini,
                pow_fac_dir=pow_fac_dir,
                scaling=scaling,
                phase_connection_type=phase_connection_type,
            )

        if load_type == IOpt.U_I_COSPHI:
            return LoadPower.from_ic_sym(
                voltage=load.ulini,
                current=load.ilini,
                cos_phi=load.coslini,
                pow_fac_dir=pow_fac_dir,
                scaling=scaling,
                phase_connection_type=phase_connection_type,
            )

        if load_type == IOpt.E_COSPHI:
            return LoadPower.from_pc_sym(
                pow_act=load.cplinia,
                cos_phi=load.coslini,
                pow_fac_dir=pow_fac_dir,
                scaling=scaling,
                phase_connection_type=phase_connection_type,
            )

        msg = "unreachable"
        raise RuntimeError(msg)

    def calc_load_lv_power_fixed_asym(
        self,
        load: PFTypes.LoadLV,
        /,
        *,
        scaling: float,
    ) -> LoadPower:
        load_type = load.iopt_inp
        pow_fac_dir = PowerFactorDirection.OE if load.pf_recap else PowerFactorDirection.UE
        if load_type == IOpt.S_COSPHI:
            return LoadPower.from_sc_asym(
                pow_apps=(load.slinir, load.slinis, load.slinit),
                cos_phis=(load.coslinir, load.coslinis, load.coslinit),
                pow_fac_dir=pow_fac_dir,
                scaling=scaling,
            )
        if load_type == IOpt.P_COSPHI:
            return LoadPower.from_pc_asym(
                pow_acts=(load.plinir, load.plinis, load.plinit),
                cos_phis=(load.coslinir, load.coslinis, load.coslinit),
                pow_fac_dir=pow_fac_dir,
                scaling=scaling,
            )
        if load_type == IOpt.U_I_COSPHI:
            return LoadPower.from_ic_asym(
                voltage=load.ulini,
                currents=(load.ilinir, load.ilinis, load.ilinit),
                cos_phis=(load.coslinir, load.coslinis, load.coslinit),
                pow_fac_dir=pow_fac_dir,
                scaling=scaling,
            )

        msg = "unreachable"
        raise RuntimeError(msg)

    def create_loads_ssc_mv(
        self,
        loads: Sequence[PFTypes.LoadMV],
        /,
        *,
        grid_name: str,
    ) -> Sequence[LoadSSC]:
        loguru.logger.info("Creating medium voltage loads steadystate case...")
        loads_ssc_mv_ = [self.create_load_ssc_mv(load, grid_name=grid_name) for load in loads]
        loads_ssc_mv = self.pfi.list_from_sequences(*loads_ssc_mv_)
        return self.pfi.filter_none(loads_ssc_mv)

    def create_load_ssc_mv(
        self,
        load: PFTypes.LoadMV,
        /,
        *,
        grid_name: str,
    ) -> Sequence[LoadSSC | None]:
        phase_connection_type = ConsolidatedLoadPhaseConnectionType[LoadPhaseConnectionType(load.phtech).name]
        power = self.calc_load_mv_power(load)
        consumer_ssc = self.create_consumer_ssc(
            load,
            power=power.consumer,
            grid_name=grid_name,
            phase_connection_type=phase_connection_type,
            name_suffix="_CONSUMER",
        )
        producer_ssc = self.create_consumer_ssc(
            load,
            power=power.producer,
            grid_name=grid_name,
            phase_connection_type=phase_connection_type,
            name_suffix="_PRODUCER",
        )
        return [consumer_ssc, producer_ssc]

    def calc_load_mv_power(
        self,
        load: PFTypes.LoadMV,
        /,
    ) -> LoadMV:
        loguru.logger.debug("Calculating power for medium voltage load {load_name}...", load_name=load.loc_name)
        if not load.ci_sym:
            return self.calc_load_mv_power_sym(load)

        return self.calc_load_mv_power_asym(load)

    def calc_load_mv_power_sym(
        self,
        load: PFTypes.LoadMV,
        /,
    ) -> LoadMV:
        load_type = load.mode_inp
        scaling_cons = load.scale0
        scaling_prod = load.gscale * -1  # to be in line with demand based counting system
        # in PF for consumer: ind. cos_phi = under excited; cap. cos_phi = over excited
        pow_fac_dir_cons = PowerFactorDirection.OE if load.pf_recap else PowerFactorDirection.UE
        # in PF for producer: ind. cos_phi = over excited; cap. cos_phi = under excited
        pow_fac_dir_prod = PowerFactorDirection.UE if load.pfg_recap else PowerFactorDirection.OE
        phase_connection_type = ConsolidatedLoadPhaseConnectionType[LoadPhaseConnectionType(load.phtech).name]
        if load_type == "PC":
            power_consumer = LoadPower.from_pc_sym(
                pow_act=load.plini,
                cos_phi=load.coslini,
                pow_fac_dir=pow_fac_dir_cons,
                scaling=scaling_cons,
                phase_connection_type=phase_connection_type,
            )
            power_producer = LoadPower.from_pc_sym(
                pow_act=load.plini,
                cos_phi=load.cosgini,
                pow_fac_dir=pow_fac_dir_prod,
                scaling=scaling_prod,
                phase_connection_type=phase_connection_type,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        if load_type == "SC":
            power_consumer = LoadPower.from_sc_sym(
                pow_app=load.slini,
                cos_phi=load.coslini,
                pow_fac_dir=pow_fac_dir_cons,
                scaling=scaling_cons,
                phase_connection_type=phase_connection_type,
            )
            power_producer = LoadPower.from_sc_sym(
                pow_app=load.sgini,
                cos_phi=load.cosgini,
                pow_fac_dir=pow_fac_dir_prod,
                scaling=scaling_prod,
                phase_connection_type=phase_connection_type,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        if load_type == "EC":
            loguru.logger.warning("Power from yearly demand is not implemented yet. Skipping.")
            power_consumer = LoadPower.from_pc_sym(
                pow_act=load.cplinia,
                cos_phi=load.coslini,
                pow_fac_dir=pow_fac_dir_cons,
                scaling=scaling_cons,
                phase_connection_type=phase_connection_type,
            )
            power_producer = LoadPower.from_pc_sym(
                pow_act=load.pgini,
                cos_phi=load.cosgini,
                pow_fac_dir=pow_fac_dir_prod,
                scaling=scaling_prod,
                phase_connection_type=phase_connection_type,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        msg = "unreachable"
        raise RuntimeError(msg)

    def calc_load_mv_power_asym(
        self,
        load: PFTypes.LoadMV,
        /,
    ) -> LoadMV:
        load_type = load.mode_inp
        scaling_cons = load.scale0
        scaling_prod = load.gscale * -1  # to be in line with demand based counting system
        # in PF for consumer: ind. cos_phi = under excited; cap. cos_phi = over excited
        pow_fac_dir_cons = PowerFactorDirection.OE if load.pf_recap else PowerFactorDirection.UE
        # in PF for producer: ind. cos_phi = over excited; cap. cos_phi = under excited
        pow_fac_dir_prod = PowerFactorDirection.UE if load.pfg_recap else PowerFactorDirection.OE
        if load_type == "PC":
            power_consumer = LoadPower.from_pc_asym(
                pow_acts=(load.plinir, load.plinis, load.plinit),
                cos_phis=(load.coslinir, load.coslinis, load.coslinit),
                pow_fac_dir=pow_fac_dir_cons,
                scaling=scaling_cons,
            )
            power_producer = LoadPower.from_pc_asym(
                pow_acts=(load.pginir, load.pginis, load.pginit),
                cos_phis=(load.cosginir, load.cosginis, load.cosginit),
                pow_fac_dir=pow_fac_dir_prod,
                scaling=scaling_prod,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        if load_type == "SC":
            power_consumer = LoadPower.from_sc_asym(
                pow_apps=(load.slinir, load.slinis, load.slinit),
                cos_phis=(load.coslinir, load.coslinis, load.coslinit),
                pow_fac_dir=pow_fac_dir_cons,
                scaling=scaling_cons,
            )
            power_producer = LoadPower.from_sc_asym(
                pow_apps=(load.sginir, load.sginis, load.sginit),
                cos_phis=(load.cosginir, load.cosginis, load.cosginit),
                pow_fac_dir=pow_fac_dir_prod,
                scaling=scaling_prod,
            )
            return LoadMV(consumer=power_consumer, producer=power_producer)

        msg = "unreachable"
        raise RuntimeError(msg)

    def create_consumer_ssc(
        self,
        load: PFTypes.LoadBase,
        /,
        *,
        power: LoadPower,
        grid_name: str,
        phase_connection_type: ConsolidatedLoadPhaseConnectionType,
        name_suffix: str = "",
    ) -> LoadSSC | None:
        consumer_name = self.pfi.create_name(load, grid_name=grid_name) + name_suffix
        loguru.logger.debug("Creating consumer {consumer_name} steadystate case...", consumer_name=consumer_name)
        export, _ = self.get_description(load)
        if not export:
            loguru.logger.warning(
                "External grid {consumer_name} not set for export. Skipping.",
                consumer_name=consumer_name,
            )
            return None

        bus = load.bus1
        if bus is None:
            loguru.logger.warning(
                "Consumer {consumer_name} not connected to any bus. Skipping.",
                consumer_name=consumer_name,
            )
            return None

        # limit entries in case of non 3-phase load
        phase_connections = self.get_load_phase_connections(
            phase_connection_type=phase_connection_type,
            bus=bus,
            grid_name=grid_name,
        )
        power = power.limit_phases(n_phases=phase_connections.n_phases)

        # P-Controller
        p_controller = self.create_p_controller_builtin(
            load,
            grid_name=grid_name,
            power=power,
        )
        active_power = ActivePowerSSC(controller=p_controller)

        # Q-Controller
        q_controller = self.create_consumer_q_controller_builtin(
            load,
            grid_name=grid_name,
            power=power,
        )

        reactive_power = ReactivePowerSSC(controller=q_controller)

        return LoadSSC(
            name=consumer_name,
            active_power=active_power,
            reactive_power=reactive_power,
        )

    def create_producers_ssc(
        self,
        loads: Sequence[PFTypes.GeneratorBase],
        /,
        *,
        grid_name: str,
    ) -> Sequence[LoadSSC]:
        loguru.logger.info("Creating producers steadystate case...")
        producers_ssc = [self.create_producer_ssc(load, grid_name=grid_name) for load in loads]
        return self.pfi.filter_none(producers_ssc)

    def create_producer_ssc(
        self,
        generator: PFTypes.GeneratorBase,
        /,
        *,
        grid_name: str,
    ) -> LoadSSC | None:
        gen_name = self.pfi.create_generator_name(generator)
        producer_name = self.pfi.create_name(generator, grid_name=grid_name, element_name=gen_name)
        loguru.logger.debug("Creating producer {producer_name} steadystate case...", producer_name=producer_name)
        export, _ = self.get_description(generator)
        if not export:
            loguru.logger.warning(
                "Generator {producer_name} not set for export. Skipping.",
                producer_name=producer_name,
            )
            return None

        bus = generator.bus1
        if bus is None:
            loguru.logger.warning(
                "Generator {producer_name} not connected to any bus. Skipping.",
                producer_name=producer_name,
            )
            return None

        phase_connection_type = ConsolidatedLoadPhaseConnectionType[GeneratorPhaseConnectionType(generator.phtech).name]
        phase_connections = self.get_load_phase_connections(
            phase_connection_type=phase_connection_type,
            bus=bus,
            grid_name=grid_name,
        )

        power = LoadPower.from_pq_sym(
            pow_act=generator.pgini_a * generator.ngnum * -1,  # has to be negative as power is counted demand based
            pow_react=generator.qgini_a * generator.ngnum * -1,  # has to be negative as power is counted demand based
            scaling=generator.scale0_a,
            phase_connection_type=phase_connection_type,
        )
        # limit entries in case of non 3-phase load
        power = power.limit_phases(n_phases=phase_connections.n_phases)

        # P-Controller
        p_controller = self.create_p_controller_builtin(
            generator,
            grid_name=grid_name,
            power=power,
        )
        active_power = ActivePowerSSC(controller=p_controller)

        # Q-Controller
        external_controller = generator.c_pstac
        if external_controller is None:
            q_controller = self.create_q_controller_builtin(
                generator,
                grid_name=grid_name,
            )
        else:
            q_controller = self.create_q_controller_external(
                generator,
                grid_name=grid_name,
                controller=external_controller,
            )

        reactive_power = ReactivePowerSSC(controller=q_controller)

        return LoadSSC(
            name=producer_name,
            active_power=active_power,
            reactive_power=reactive_power,
        )

    def create_p_controller_builtin(
        self,
        load: PFTypes.GeneratorBase | PFTypes.LoadBase,
        /,
        *,
        grid_name: str,
        power: LoadPower,
    ) -> PController | None:
        loguru.logger.debug("Creating consumer {load_name} internal P controller...", load_name=load.loc_name)
        if load.bus1 is not None:
            node_target_name = self.pfi.create_name(load.bus1.cterm, grid_name=grid_name)
        else:
            return None

        # at the moment there is only controller of type PConst
        p_control_type = ControlTypeFactory.create_p_const(power)
        return PController(node_target=node_target_name, control_type=p_control_type)

    def create_consumer_q_controller_builtin(
        self,
        load: PFTypes.LoadBase,
        /,
        *,
        grid_name: str,
        power: LoadPower,
    ) -> QController | None:
        loguru.logger.debug("Creating consumer {load_name} internal Q controller...", load_name=load.loc_name)
        bus = load.bus1
        if bus is None:
            loguru.logger.warning(
                "Consumer {load_name}: controller has no connected node. Skipping.",
                load_name=load.loc_name,
            )
            return None

        terminal = bus.cterm
        node_target_name = self.pfi.create_name(terminal, grid_name=grid_name)

        if power.pow_react_control_type == QControlStrategy.Q_CONST:
            control_type = ControlTypeFactory.create_q_const(power)
            return QController(node_target=node_target_name, control_type=control_type)

        if power.pow_react_control_type == QControlStrategy.COSPHI_CONST:
            control_type = ControlTypeFactory.create_cos_phi_const(power)
            return QController(node_target=node_target_name, control_type=control_type)

        msg = "unreachable"
        raise RuntimeError(msg)

    def create_q_controller_builtin(  # noqa: PLR0911
        self,
        gen: PFTypes.GeneratorBase,
        /,
        *,
        grid_name: str,
    ) -> QController | None:
        loguru.logger.debug("Creating Producer {gen_name} internal Q controller...", gen_name=gen.loc_name)
        scaling = gen.scale0

        # Controlled node
        bus = gen.bus1
        if bus is None:
            loguru.logger.warning(
                "Producer {gen_name}: controller has no connected node. Skipping.",
                gen_name=gen.loc_name,
            )
            return None
        terminal = bus.cterm
        node_target_name = self.pfi.create_name(terminal, grid_name=grid_name)
        u_n = terminal.uknom * Exponents.VOLTAGE  # voltage in V

        phase_connection_type = ConsolidatedLoadPhaseConnectionType[GeneratorPhaseConnectionType(gen.phtech).name]
        phase_connections = self.get_load_phase_connections(
            phase_connection_type=phase_connection_type,
            bus=bus,
            grid_name=grid_name,
        )
        if phase_connections.n_phases != DEFAULT_PHASE_QUANTITY:
            loguru.logger.warning(
                "Generator {gen_name}: Q-Controller is not connected to 3-phase terminal. Phase mismatch possible.",
                gen_name=gen.loc_name,
            )

        # Control mode
        av_mode = LocalQCtrlMode(gen.av_mode)
        if av_mode == LocalQCtrlMode.COSPHI_CONST:
            power = LoadPower.from_pc_sym(
                pow_act=0,
                cos_phi=gen.cosgini,
                pow_fac_dir=PowerFactorDirection.UE if gen.pf_recap else PowerFactorDirection.OE,
                scaling=scaling,
                phase_connection_type=phase_connection_type,
            )
            power = power.limit_phases(n_phases=phase_connections.n_phases)
            q_control_type = ControlTypeFactory.create_cos_phi_const(power)
            return QController(node_target=node_target_name, control_type=q_control_type)

        if av_mode == LocalQCtrlMode.Q_CONST:
            q_set = gen.qgini * -1  # has to be negative as power is now counted demand based
            power = LoadPower.from_pq_sym(
                pow_act=1,
                pow_react=q_set * gen.ngnum,  # has to be negative as power is counted demand based
                scaling=scaling,
                phase_connection_type=phase_connection_type,
            )
            power = power.limit_phases(n_phases=phase_connections.n_phases)
            q_control_type = ControlTypeFactory.create_q_const(power)
            return QController(node_target=node_target_name, control_type=q_control_type)

        if av_mode == LocalQCtrlMode.Q_U:
            u_q0 = gen.udeadbup - (gen.udeadbup - gen.udeadblow) / 2  # p.u.
            u_deadband_low = abs(u_q0 - gen.udeadblow)  # delta in p.u.
            u_deadband_up = abs(u_q0 - gen.udeadbup)  # delta in p.u.
            m_tg_2015 = 100 / abs(gen.ddroop) * 100 / u_n / gen.cosn * Exponents.VOLTAGE  # (% von Pr) / kV
            m_tg_2018 = ControlTypeFactory.transform_qu_slope(
                value=m_tg_2015,
                given_format="2015",
                target_format="2018",
                u_n=u_n,
            )

            q_control_type = ControlTypeFactory.create_q_u_sym(
                q_max_ue=abs(gen.Qfu_min) * Exponents.POWER * gen.ngnum,
                q_max_oe=abs(gen.Qfu_max) * Exponents.POWER * gen.ngnum,
                u_q0=u_q0 * u_n,
                u_deadband_low=u_deadband_low * u_n,
                u_deadband_up=u_deadband_up * u_n,
                droop_up=m_tg_2018,
                droop_low=m_tg_2018,
            )
            return QController(node_target=node_target_name, control_type=q_control_type)

        if av_mode == LocalQCtrlMode.Q_P:
            if gen.pQPcurve is None:
                return None

            q_control_type = ControlQP(q_p_characteristic_name=gen.pQPcurve.loc_name)
            return QController(node_target=node_target_name, control_type=q_control_type)

        if av_mode == LocalQCtrlMode.COSPHI_P:
            q_control_type = ControlTypeFactory.create_cos_phi_p_sym(
                cos_phi_ue=gen.pf_under,
                cos_phi_oe=gen.pf_over,
                p_threshold_ue=gen.p_under * -1 * Exponents.POWER * gen.ngnum,  # P-threshold for cosphi_ue
                p_threshold_oe=gen.p_over * -1 * Exponents.POWER * gen.ngnum,  # P-threshold for cosphi_oe
            )
            return QController(node_target=node_target_name, control_type=q_control_type)

        if av_mode == LocalQCtrlMode.U_CONST:
            q_control_type = ControlTypeFactory.create_u_const_sym(u_set=gen.usetp * u_n)
            return QController(node_target=node_target_name, control_type=q_control_type)

        if av_mode == LocalQCtrlMode.U_Q_DROOP:
            loguru.logger.warning(
                "Generator {gen_name}: Voltage control with Q-droop is not implemented yet. Skipping.",
                gen_name=gen.loc_name,
            )
            return None

        if av_mode == LocalQCtrlMode.U_I_DROOP:
            loguru.logger.warning(
                "Generator {gen_name}: Voltage control with I-droop is not implemented yet. Skipping.",
                gen_name=gen.loc_name,
            )
            return None

        msg = "unreachable"
        raise RuntimeError(msg)

    def create_q_controller_external(  # noqa: PLR0911, PLR0912, PLR0915
        self,
        gen: PFTypes.GeneratorBase,
        /,
        *,
        grid_name: str,
        controller: PFTypes.StationController,
    ) -> QController | None:
        controller_name = self.pfi.create_generator_name(gen, generator_name=controller.loc_name)
        loguru.logger.debug(
            "Creating producer {gen_name} external Q controller {controller_name}...",
            gen_name=gen.loc_name,
            controller_name=controller_name,
        )

        # Controlled node
        bus = controller.p_cub  # target node
        if bus is None:
            loguru.logger.warning(
                "Generator {gen_name}: external controller has no target node. Skipping.",
                gen_name=gen.loc_name,
            )
            return None
        terminal = bus.cterm
        node_target_name = self.pfi.create_name(terminal, grid_name=grid_name)
        u_n = terminal.uknom * Exponents.VOLTAGE  # voltage in V

        phase_connection_type = ConsolidatedLoadPhaseConnectionType[GeneratorPhaseConnectionType(gen.phtech).name]
        phase_connections = self.get_load_phase_connections(
            phase_connection_type=phase_connection_type,
            bus=bus,
            grid_name=grid_name,
        )
        if phase_connections.n_phases != DEFAULT_PHASE_QUANTITY:
            loguru.logger.warning(
                "Generator {gen_name}: Q-Controller is not connected to 3-phase terminal. Phase mismatch possible.",
                gen_name=gen.loc_name,
            )

        # Control mode
        ctrl_mode = controller.i_ctrl
        if ctrl_mode == CtrlMode.U:  # voltage control mode -> const. U
            q_control_type = ControlTypeFactory.create_u_const_sym(
                u_set=controller.usetp * u_n,
                u_meas_ref=ControlledVoltageRef[CtrlVoltageRef(controller.i_phase).name],
            )
            return QController(
                node_target=node_target_name,
                control_type=q_control_type,
                external_controller_name=controller_name,
            )

        if ctrl_mode == CtrlMode.Q:  # reactive power control mode
            if controller.qu_char == QChar.CONST:  # const. Q
                q_dir = -1 if controller.iQorient else 1
                q_set = controller.qsetp * q_dir * -1  # has to be negative as power is now counted demand based
                power = LoadPower.from_pq_sym(
                    pow_act=0,
                    pow_react=q_set
                    * Exponents.POWER
                    * gen.ngnum,  # has to be negative as power is counted demand based
                    scaling=1,
                    phase_connection_type=phase_connection_type,
                )
                power = power.limit_phases(n_phases=phase_connections.n_phases)
                q_control_type = ControlTypeFactory.create_q_const(power)
                return QController(
                    node_target=node_target_name,
                    control_type=q_control_type,
                    external_controller_name=controller_name,
                )

            if controller.qu_char == QChar.U:  # Q(U)
                u_q0 = controller.udeadbup - (controller.udeadbup - controller.udeadblow) / 2  # per unit
                u_deadband_low = abs(u_q0 - controller.udeadblow)  # delta in per unit
                u_deadband_up = abs(u_q0 - controller.udeadbup)  # delta in per unit

                q_rated = controller.Srated
                try:
                    if abs((abs(q_rated) - abs(gen.sgn)) / abs(gen.sgn)) < M_TAB2015_MIN_THRESHOLD:  # q_rated == s_r
                        m_tg_2015 = 100 / controller.ddroop * 100 / u_n / gen.cosn * Exponents.VOLTAGE
                    else:
                        m_tg_2015 = (
                            100 / abs(controller.ddroop) * 100 / u_n * math.tan(math.acos(gen.cosn)) * Exponents.VOLTAGE
                        )

                    # in default there should q_rated=s_r, but user could enter incorrectly
                    m_tg_2015 = m_tg_2015 * q_rated / gen.sgn
                    m_tg_2018 = ControlTypeFactory.transform_qu_slope(
                        value=m_tg_2015,
                        given_format="2015",
                        target_format="2018",
                        u_n=u_n,
                    )
                except ZeroDivisionError:
                    m_tg_2015 = float("inf")
                    m_tg_2018 = float("inf")

                q_control_type = ControlTypeFactory.create_q_u_sym(
                    q_max_ue=abs(controller.Qmin) * Exponents.POWER * gen.ngnum,
                    q_max_oe=abs(controller.Qmax) * Exponents.POWER * gen.ngnum,
                    u_q0=u_q0 * u_n,
                    u_deadband_low=u_deadband_low * u_n,
                    u_deadband_up=u_deadband_up * u_n,
                    droop_up=m_tg_2018,
                    droop_low=m_tg_2018,
                )
                return QController(
                    node_target=node_target_name,
                    control_type=q_control_type,
                    external_controller_name=controller_name,
                )

            if controller.qu_char == QChar.P:  # Q(P)
                q_dir = -1 if controller.iQorient else 1
                q_control_type = ControlTypeFactory.create_q_p_sym(
                    q_p_characteristic_name=controller.pQPcurve.loc_name,
                    q_max_ue=abs(controller.Qmin) * Exponents.POWER * gen.ngnum,
                    q_max_oe=abs(controller.Qmax) * Exponents.POWER * gen.ngnum,
                )
                return QController(
                    node_target=node_target_name,
                    control_type=q_control_type,
                    external_controller_name=controller_name,
                )

            msg = "unreachable"
            raise RuntimeError(msg)

        if ctrl_mode == CtrlMode.COSPHI:  # cos_phi control mode
            if controller.cosphi_char == CosPhiChar.CONST:  # const. cos_phi
                ue = controller.pf_recap ^ controller.iQorient  # OE/UE XOR +Q/-Q
                # in PF for producer: ind. cos_phi = over excited; cap. cos_phi = under excited
                pow_fac_dir = PowerFactorDirection.UE if ue else PowerFactorDirection.OE
                power = LoadPower.from_pc_sym(
                    pow_act=0,
                    cos_phi=controller.pfsetp,
                    pow_fac_dir=pow_fac_dir,
                    scaling=1,
                    phase_connection_type=phase_connection_type,
                )
                power = power.limit_phases(n_phases=phase_connections.n_phases)
                q_control_type = ControlTypeFactory.create_cos_phi_const(power)
                return QController(
                    node_target=node_target_name,
                    control_type=q_control_type,
                    external_controller_name=controller_name,
                )

            if controller.cosphi_char == CosPhiChar.P:  # cos_phi(P)
                q_control_type = ControlTypeFactory.create_cos_phi_p_sym(
                    cos_phi_ue=controller.pf_under,
                    cos_phi_oe=controller.pf_over,
                    p_threshold_ue=controller.p_under * -1 * Exponents.POWER * gen.ngnum,  # P-threshold for cosphi_ue
                    p_threshold_oe=controller.p_over * -1 * Exponents.POWER * gen.ngnum,  # P-threshold for cosphi_oe
                )
                return QController(
                    node_target=node_target_name,
                    control_type=q_control_type,
                    external_controller_name=controller_name,
                )

            if controller.cosphi_char == CosPhiChar.U:  # cos_phi(U)
                q_control_type = ControlTypeFactory.create_cos_phi_u_sym(
                    cos_phi_ue=controller.pf_under,
                    cos_phi_oe=controller.pf_over,
                    u_threshold_ue=controller.u_under * u_n,  # U-threshold for cosphi_ue
                    u_threshold_oe=controller.u_over * u_n,  # U-threshold for cosphi_oe
                )
                return QController(
                    node_target=node_target_name,
                    control_type=q_control_type,
                    external_controller_name=controller_name,
                )

            msg = "unreachable"
            raise RuntimeError(msg)

        if ctrl_mode == CtrlMode.TANPHI:  # tanphi control mode --> const. tanphi
            cos_phi = math.cos(math.atan(controller.tansetp))
            pow_fac_dir = PowerFactorDirection.UE if controller.iQorient else PowerFactorDirection.OE
            power = LoadPower.from_pc_sym(
                pow_act=0,
                cos_phi=cos_phi,
                pow_fac_dir=pow_fac_dir,
                scaling=1,
                phase_connection_type=phase_connection_type,
            )
            power = power.limit_phases(n_phases=phase_connections.n_phases)
            q_control_type = ControlTypeFactory.create_tan_phi_const(power)
            return QController(
                node_target=node_target_name,
                control_type=q_control_type,
                external_controller_name=controller_name,
            )

        msg = "unreachable"
        raise RuntimeError(msg)

    def get_load_phase_connections(  # noqa: PLR0911, PLR0912
        self,
        *,
        phase_connection_type: ConsolidatedLoadPhaseConnectionType,
        bus: PFTypes.StationCubicle,
        grid_name: str,
    ) -> PhaseConnections:
        if not bus.cPhInfo:
            msg = f"Mismatch of node and load phase technology at {self.pfi.create_name(bus, grid_name=grid_name)}."
            raise RuntimeError(msg)
        t_phase_connection_type = TerminalPhaseConnectionType(bus.cterm.phtech)
        if t_phase_connection_type in (
            TerminalPhaseConnectionType.THREE_PH,
            TerminalPhaseConnectionType.THREE_PH_N,
            TerminalPhaseConnectionType.ONE_PH,
            TerminalPhaseConnectionType.ONE_PH_N,
        ):
            phases = textwrap.wrap(bus.cPhInfo, 2)
        elif t_phase_connection_type in (TerminalPhaseConnectionType.TWO_PH, TerminalPhaseConnectionType.TWO_PH_N):
            phases = textwrap.wrap(bus.cPhInfo, 3)
        elif t_phase_connection_type in (TerminalPhaseConnectionType.BI, TerminalPhaseConnectionType.BI_N):
            msg = "Terminal phase technology implementation unclear. Please extend exporter by your own."
            raise RuntimeError(msg)
        else:
            msg = "unreachable"
            raise RuntimeError(msg)

        if phase_connection_type == ConsolidatedLoadPhaseConnectionType.THREE_PH_D:
            return PhaseConnections(
                value=[
                    [Phase[PFPhase3PH(phases[0]).name], Phase[PFPhase3PH(phases[1]).name]],
                    [Phase[PFPhase3PH(phases[1]).name], Phase[PFPhase3PH(phases[2]).name]],
                    [Phase[PFPhase3PH(phases[2]).name], Phase[PFPhase3PH(phases[0]).name]],
                ],
            )

        if phase_connection_type == ConsolidatedLoadPhaseConnectionType.THREE_PH_PH_E:
            return PhaseConnections(
                value=[
                    [Phase[PFPhase3PH(phases[0]).name], Phase.E],
                    [Phase[PFPhase3PH(phases[1]).name], Phase.E],
                    [Phase[PFPhase3PH(phases[2]).name], Phase.E],
                ],
            )

        if phase_connection_type == ConsolidatedLoadPhaseConnectionType.THREE_PH_YN:
            return PhaseConnections(
                value=[
                    [Phase[PFPhase3PH(phases[0]).name], Phase.N],
                    [Phase[PFPhase3PH(phases[1]).name], Phase.N],
                    [Phase[PFPhase3PH(phases[2]).name], Phase.N],
                ],
            )

        if phase_connection_type == ConsolidatedLoadPhaseConnectionType.TWO_PH_PH_E:
            if t_phase_connection_type in (TerminalPhaseConnectionType.TWO_PH, TerminalPhaseConnectionType.TWO_PH_N):
                _phase_connections = [
                    [Phase[PFPhase2PH(phases[0]).name], Phase.E],
                    [Phase[PFPhase2PH(phases[1]).name], Phase.E],
                ]
            else:
                _phase_connections = [
                    [Phase[PFPhase3PH(phases[0]).name], Phase.E],
                    [Phase[PFPhase3PH(phases[1]).name], Phase.E],
                ]
            return PhaseConnections(value=_phase_connections)

        if phase_connection_type == ConsolidatedLoadPhaseConnectionType.TWO_PH_YN:
            if t_phase_connection_type in (TerminalPhaseConnectionType.TWO_PH, TerminalPhaseConnectionType.TWO_PH_N):
                _phase_connections = [
                    [Phase[PFPhase2PH(phases[0]).name], Phase.N],
                    [Phase[PFPhase2PH(phases[1]).name], Phase.N],
                ]
            else:
                _phase_connections = [
                    [Phase[PFPhase3PH(phases[0]).name], Phase.N],
                    [Phase[PFPhase3PH(phases[1]).name], Phase.N],
                ]
            return PhaseConnections(value=_phase_connections)

        if phase_connection_type == ConsolidatedLoadPhaseConnectionType.ONE_PH_PH_PH:
            if t_phase_connection_type in (TerminalPhaseConnectionType.ONE_PH, TerminalPhaseConnectionType.ONE_PH_N):
                _phase_connections = [[Phase[PFPhase1PH(phases[0]).name], Phase[PFPhase1PH(phases[1]).name]]]
            elif t_phase_connection_type in (TerminalPhaseConnectionType.TWO_PH, TerminalPhaseConnectionType.TWO_PH_N):
                _phase_connections = [[Phase[PFPhase2PH(phases[0]).name], Phase[PFPhase2PH(phases[1]).name]]]
            else:
                _phase_connections = [[Phase[PFPhase3PH(phases[0]).name], Phase[PFPhase3PH(phases[1]).name]]]
            return PhaseConnections(value=_phase_connections)

        if phase_connection_type == ConsolidatedLoadPhaseConnectionType.ONE_PH_PH_E:
            if t_phase_connection_type in (TerminalPhaseConnectionType.ONE_PH, TerminalPhaseConnectionType.ONE_PH_N):
                _phase_connections = [[Phase[PFPhase1PH(phases[0]).name], Phase.E]]
            elif t_phase_connection_type in (TerminalPhaseConnectionType.TWO_PH, TerminalPhaseConnectionType.TWO_PH_N):
                _phase_connections = [[Phase[PFPhase2PH(phases[0]).name], Phase.E]]
            else:
                _phase_connections = [[Phase[PFPhase3PH(phases[0]).name], Phase.E]]
            return PhaseConnections(value=_phase_connections)

        if phase_connection_type == ConsolidatedLoadPhaseConnectionType.ONE_PH_PH_N:
            if t_phase_connection_type in (TerminalPhaseConnectionType.ONE_PH, TerminalPhaseConnectionType.ONE_PH_N):
                _phase_connections = [[Phase[PFPhase1PH(phases[0]).name], Phase.N]]
            elif t_phase_connection_type in (TerminalPhaseConnectionType.TWO_PH, TerminalPhaseConnectionType.TWO_PH_N):
                _phase_connections = [[Phase[PFPhase2PH(phases[0]).name], Phase.N]]
            else:
                _phase_connections = [[Phase[PFPhase3PH(phases[0]).name], Phase.N]]
            return PhaseConnections(value=_phase_connections)

        msg = "unreachable"
        raise RuntimeError(msg)

    def get_branch_phases(
        self,
        *,
        l_type: PFTypes.LineType,
        phase_connection_type: TerminalPhaseConnectionType,
        bus: PFTypes.StationCubicle,
        grid_name: str,
    ) -> UniqueTuple[Phase]:
        if not bus.cPhInfo:
            msg = f"Mismatch of node and branch phase technology at {self.pfi.create_name(bus, grid_name=grid_name)}."
            raise RuntimeError(msg)
        if phase_connection_type in (TerminalPhaseConnectionType.BI, TerminalPhaseConnectionType.BI_N):
            msg = "Terminal phase technology implementation unclear. Please extend exporter by your own."
            raise RuntimeError(msg)

        if l_type.nlnph == 3:  # 3 phase conductors  # noqa: PLR2004
            phases = textwrap.wrap(bus.cPhInfo, 2)
            phases_tuple = [
                Phase[PFPhase3PH(phases[0]).name],
                Phase[PFPhase3PH(phases[1]).name],
                Phase[PFPhase3PH(phases[2]).name],
            ]
        elif l_type.nlnph == 2:  # 2 phase conductors  # noqa: PLR2004
            if phase_connection_type in (TerminalPhaseConnectionType.THREE_PH, TerminalPhaseConnectionType.THREE_PH_N):
                phases = textwrap.wrap(bus.cPhInfo, 2)
                phases_tuple = [
                    Phase[PFPhase3PH(phases[0]).name],
                    Phase[PFPhase3PH(phases[1]).name],
                ]
            if phase_connection_type in (TerminalPhaseConnectionType.TWO_PH, TerminalPhaseConnectionType.TWO_PH_N):
                phases = textwrap.wrap(bus.cPhInfo, 3)
                phases_tuple = [
                    Phase[PFPhase2PH(phases[0]).name],
                    Phase[PFPhase2PH(phases[1]).name],
                ]
        elif l_type.nlnph == 1:  # 1 phase conductors
            if phase_connection_type in (TerminalPhaseConnectionType.THREE_PH, TerminalPhaseConnectionType.THREE_PH_N):
                phases = textwrap.wrap(bus.cPhInfo, 2)
                phases_tuple = [
                    Phase[PFPhase3PH(phases[0]).name],
                ]
            if phase_connection_type in (TerminalPhaseConnectionType.TWO_PH, TerminalPhaseConnectionType.TWO_PH_N):
                phases = textwrap.wrap(bus.cPhInfo, 3)
                phases_tuple = [
                    Phase[PFPhase2PH(phases[0]).name],
                ]
            elif phase_connection_type in (TerminalPhaseConnectionType.ONE_PH, TerminalPhaseConnectionType.ONE_PH_N):
                phases = textwrap.wrap(bus.cPhInfo, 2)
                phases_tuple = [
                    Phase[PFPhase1PH(phases[0]).name],
                ]
        else:
            msg = "unreachable"
            raise RuntimeError(msg)

        if l_type.nneutral == 1:
            phases_tuple = [*phases_tuple, Phase.N]
        return phases_tuple

    def get_terminal_phases(
        self,
        phase_connection_type: TerminalPhaseConnectionType,
    ) -> UniqueTuple[Phase]:
        if phase_connection_type is TerminalPhaseConnectionType.THREE_PH:
            return [
                Phase[PFPhase3PH.A.name],
                Phase[PFPhase3PH.B.name],
                Phase[PFPhase3PH.C.name],
            ]
        if phase_connection_type is TerminalPhaseConnectionType.THREE_PH_N:
            return [
                Phase[PFPhase3PH.A.name],
                Phase[PFPhase3PH.B.name],
                Phase[PFPhase3PH.C.name],
                Phase[PFPhase3PH.N.name],
            ]
        if phase_connection_type is TerminalPhaseConnectionType.TWO_PH:
            return [
                Phase[PFPhase2PH.A.name],
                Phase[PFPhase2PH.B.name],
            ]
        if phase_connection_type is TerminalPhaseConnectionType.TWO_PH_N:
            return [
                Phase[PFPhase2PH.A.name],
                Phase[PFPhase2PH.B.name],
                Phase[PFPhase2PH.N.name],
            ]
        if phase_connection_type is TerminalPhaseConnectionType.ONE_PH:
            return [Phase[PFPhase1PH.A.name]]
        if phase_connection_type is TerminalPhaseConnectionType.ONE_PH_N:
            return [
                Phase[PFPhase1PH.A.name],
                Phase[PFPhase1PH.N.name],
            ]
        if phase_connection_type in (TerminalPhaseConnectionType.BI, TerminalPhaseConnectionType.BI_N):
            msg = "Implementation unclear. Please extend exporter by your own."
            raise RuntimeError(msg)
        msg = "unreachable"
        raise RuntimeError(msg)

    def get_external_grid_phases(
        self,
        *,
        phase_connection_type: TerminalPhaseConnectionType,
        bus: PFTypes.StationCubicle,
    ) -> UniqueTuple[Phase]:
        if phase_connection_type in (TerminalPhaseConnectionType.THREE_PH, TerminalPhaseConnectionType.THREE_PH_N):
            phases = textwrap.wrap(bus.cPhInfo, 2)
            return [
                Phase[PFPhase3PH(phases[0]).name],
                Phase[PFPhase3PH(phases[1]).name],
                Phase[PFPhase3PH(phases[2]).name],
            ]

        if phase_connection_type in (TerminalPhaseConnectionType.TWO_PH, TerminalPhaseConnectionType.TWO_PH_N):
            phases = textwrap.wrap(bus.cPhInfo, 3)
            return [
                Phase[PFPhase2PH(phases[0]).name],
                Phase[PFPhase2PH(phases[1]).name],
            ]
        if phase_connection_type in (TerminalPhaseConnectionType.ONE_PH, TerminalPhaseConnectionType.ONE_PH_N):
            phases = textwrap.wrap(bus.cPhInfo, 2)
            return [Phase[PFPhase1PH(phases[0]).name]]
        if phase_connection_type in (TerminalPhaseConnectionType.BI, TerminalPhaseConnectionType.BI_N):
            msg = "Implementation unclear. Please extend exporter by your own."
            raise RuntimeError(msg)
        msg = "unreachable"
        raise RuntimeError(msg)

    def get_transformer2w_3ph_phases(  # may adapt in future
        self,
        *,
        winding_vector_group: WVectorGroup,
        bus: PFTypes.StationCubicle,  # noqa: ARG002
    ) -> UniqueTuple[Phase]:
        phases = [
            Phase[PFPhase3PH.A.name],
            Phase[PFPhase3PH.B.name],
            Phase[PFPhase3PH.C.name],
        ]
        if winding_vector_group in (WVectorGroup.YN, WVectorGroup.ZN):
            phases = [*phases, Phase.N]

        return phases


def export_powerfactory_data(  # noqa: PLR0913
    *,
    export_path: pathlib.Path,
    project_name: str,
    powerfactory_user_profile: str = "",
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH,
    powerfactory_version: str = POWERFACTORY_VERSION,
    python_version: str = PYTHON_VERSION,
    logging_level: int = logging.DEBUG,
    log_file_path: pathlib.Path | None = None,
    topology_name: str | None = None,
    topology_case_name: str | None = None,
    steadystate_case_name: str | None = None,
    study_case_names: list[str] | None = None,
) -> None:
    """Export powerfactory data to json files using PowerFactoryExporter running in process.

    A grid given in DIgSILENT PowerFactory is exported to three json files with given schema.
    The whole grid data is separated into topology (raw assets), topology_case (binary switching info and out of service
    info) and steadystate_case (operation points).
    When the code execution is complete, the process is terminated and the connection to PowerFactory is closed.

        Arguments:
            export_path {pathlib.Path} -- the directory where the exported json files are saved
            project_name {str} -- project name in PowerFactory to which the grid belongs
            powerfactory_user_profile {str} -- user profile for login in PowerFactory  (default: {""})
            powerfactory_path {pathlib.Path} -- installation directory of PowerFactory (hard-coded in interface.py)
            powerfactory_version {str} -- version number of PowerFactory (hard-coded in interface.py)
            python_version {str} -- version number of Python (hard-coded in interface.py)
            logging_level {int} -- flag for the level of logging criticality (default: {DEBUG})
            log_file_path {pathlib.Path} -- the file path of an external log file (default: {None})
            topology_name {str} -- the chosen file name for 'topology' data (default: {None})
            topology_case_name {str} -- the chosen file name for related 'topology_case' data (default: {None})
            steadystate_case_name {str} -- the chosen file name for related 'steadystate_case' data (default: {None})
            study_case_names {list[str]} -- a list of study cases to export (default: {None})

        Returns:
            None
    """

    process = PowerFactoryExporterProcess(
        project_name=project_name,
        export_path=export_path,
        powerfactory_user_profile=powerfactory_user_profile,
        powerfactory_path=powerfactory_path,
        powerfactory_version=powerfactory_version,
        python_version=python_version,
        logging_level=logging_level,
        log_file_path=log_file_path,
        topology_name=topology_name,
        topology_case_name=topology_case_name,
        steadystate_case_name=steadystate_case_name,
        study_case_names=study_case_names,
    )
    process.start()
    process.join()
