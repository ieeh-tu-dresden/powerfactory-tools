from powerfactory_utils.schema.topology.branch import Branch
from powerfactory_utils.schema.topology.branch import BranchType


def test_init() -> None:
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
    )
