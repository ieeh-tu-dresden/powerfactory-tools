# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from contextlib import nullcontext as does_not_raise

import pydantic
import pytest

from powerfactory_tools.schema.topology.load import RatedPower


class TestRatedPower:
    @pytest.mark.parametrize(
        (
            "value",
            "value_a",
            "value_b",
            "value_c",
            "cosphi_ue",
            "cosphi_a_ue",
            "cosphi_b_ue",
            "cosphi_c_ue",
            "cosphi_oe",
            "cosphi_a_oe",
            "cosphi_b_oe",
            "cosphi_c_oe",
            "expectation",
        ),
        [
            (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, does_not_raise()),
            (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, does_not_raise()),
            (2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, does_not_raise()),
            (2, 2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, pytest.raises(pydantic.ValidationError)),
            (2, -2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, pytest.raises(pydantic.ValidationError)),
        ],
    )
    def test_init(
        self,
        value,
        value_a,
        value_b,
        value_c,
        cosphi_ue,
        cosphi_a_ue,
        cosphi_b_ue,
        cosphi_c_ue,
        cosphi_oe,
        cosphi_a_oe,
        cosphi_b_oe,
        cosphi_c_oe,
        expectation,
    ) -> None:
        with expectation:
            RatedPower(
                value=value,
                value_a=value_a,
                value_b=value_b,
                value_c=value_c,
                cosphi_ue=cosphi_ue,
                cosphi_a_ue=cosphi_a_ue,
                cosphi_b_ue=cosphi_b_ue,
                cosphi_c_ue=cosphi_c_ue,
                cosphi_oe=cosphi_oe,
                cosphi_a_oe=cosphi_a_oe,
                cosphi_b_oe=cosphi_b_oe,
                cosphi_c_oe=cosphi_c_oe,
            )
