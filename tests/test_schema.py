# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

import json

from psdm.steadystate_case.case import Case as SteadystateCase
from psdm.topology.topology import Topology
from psdm.topology_case.case import Case as TopologyCase

GRID_PATH_PREFIX = "examples/grids/HV_8_Bus_"


def sorting(item):
    if isinstance(item, dict):
        return sorted((key, sorting(values)) for key, values in item.items())
    if isinstance(item, list):
        return sorted(sorting(x) for x in item)
    else:
        return item


class TestSchema:
    def test_topology_schema_import(self):
        json_file_path = GRID_PATH_PREFIX + "topology.json"

        ssc = Topology.from_file(json_file_path)
        js = ssc.json(sort_keys=True)

        with open(json_file_path, "r") as file_handle:
            data = json.loads(file_handle.read())
        js2 = json.dumps(data)

        assert sorting(js) == sorting(js2)

    def test_topologycase_schema_import(self):
        json_file_path = GRID_PATH_PREFIX + "topology_case.json"

        ssc = TopologyCase.from_file(json_file_path)
        js = ssc.json(sort_keys=True)

        with open(json_file_path, "r") as file_handle:
            data = json.loads(file_handle.read())
        js2 = json.dumps(data)

        assert sorting(js) == sorting(js2)

    def test_steadystatecase_schema_import(self):
        json_file_path = GRID_PATH_PREFIX + "steadystate_case.json"

        ssc = SteadystateCase.from_file(json_file_path)
        js = ssc.json(sort_keys=True)

        with open(json_file_path, "r") as file_handle:
            data = json.loads(file_handle.read())
        js2 = json.dumps(data)

        assert sorting(js) == sorting(js2)
