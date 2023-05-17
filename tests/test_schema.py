# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

import json
import pathlib

from psdm.steadystate_case.case import Case as SteadystateCase
from psdm.topology.topology import Topology
from psdm.topology_case.case import Case as TopologyCase

GRID_PATH_PREFIX = "examples/grids/HV_8_Bus_"


def sorting(item):
    if isinstance(item, dict):
        return sorted((key, sorting(values)) for key, values in item.items())

    if isinstance(item, list):
        return sorted(sorting(x) for x in item)

    return item


class TestSchema:
    def test_topology_schema_import(self) -> None:
        json_file_path = pathlib.Path(GRID_PATH_PREFIX + "topology.json")

        ssc = Topology.from_file(json_file_path)
        json_str1 = ssc.json(sort_keys=True)

        with json_file_path.open(encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        json_str2 = json.dumps(data, sort_keys=True)

        assert json_str1 == json_str2

    def test_topologycase_schema_import(self):
        json_file_path = pathlib.Path(GRID_PATH_PREFIX + "topology_case.json")

        ssc = TopologyCase.from_file(json_file_path)
        js = ssc.json(sort_keys=True)

        with json_file_path.open(encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        js2 = json.dumps(data, sort_keys=True)

        assert sorting(js) == sorting(js2)

    def test_steadystatecase_schema_import(self):
        json_file_path = pathlib.Path(GRID_PATH_PREFIX + "steadystate_case.json")

        ssc = SteadystateCase.from_file(json_file_path)
        js = ssc.json(sort_keys=True)

        with json_file_path.open(encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        js2 = json.dumps(data, sort_keys=True)

        assert sorting(js) == sorting(js2)
