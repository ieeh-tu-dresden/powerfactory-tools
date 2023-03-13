# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from powerfactory_tools.schema.base import VoltageSystemType
from powerfactory_tools.schema.topology.branch import Branch
from powerfactory_tools.schema.topology.branch import BranchType


class TestBranch:
    def test_init(self) -> None:
        Branch(
            node_1="asd",
            node_2="fgh",
            name="wqertasd",
            u_n=1,
            i_r=1,
            b1=1,
            g1=1,
            x1=1,
            r1=1,
            type=BranchType.LINE,
            voltage_system_type=VoltageSystemType.AC,
        )
