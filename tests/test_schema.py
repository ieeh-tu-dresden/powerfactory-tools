# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

import json
import pathlib

import pytest
from psdm.steadystate_case.case import Case as SteadystateCase
from psdm.topology.topology import Topology
from psdm.topology_case.case import Case as TopologyCase

GRID_PATH_PREFIX = "examples/grids/HV_9_Bus_"


def round_floats(o):
    if isinstance(o, float):
        return round(o, 10)
    if isinstance(o, dict):
        return {k: round_floats(v) for k, v in o.items()}
    if isinstance(o, list | tuple):
        return [round_floats(x) for x in o]
    return o


@pytest.mark.parametrize(
    (
        "schema_class",
        "json_file_name",
    ),
    [
        (Topology, "topology.json"),
        (TopologyCase, "topology_case.json"),
        (SteadystateCase, "steadystate_case.json"),
    ],
)
def test_schema_import(schema_class, json_file_name) -> None:
    json_file_path = pathlib.Path(GRID_PATH_PREFIX + json_file_name)

    data = schema_class.from_file(json_file_path)
    _json_str1 = data.model_dump()
    json_str1 = json.dumps(round_floats(_json_str1), sort_keys=True, default=str)

    with json_file_path.open(encoding="utf-8") as file_handle:
        data = json.load(file_handle)
    json_str2 = json.dumps(round_floats(data), sort_keys=True)

    assert json_str1 == json_str2
