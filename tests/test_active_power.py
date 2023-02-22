# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from contextlib import nullcontext as does_not_raise

import pydantic
import pytest

from powerfactory_tools.schema.steadystate_case.active_power import ActivePower


class TestActivePower:
    @pytest.mark.parametrize(
        (
            "value_0",
            "value_a_0",
            "value_b_0",
            "value_c_0",
            "is_symmetrical",
            "expectation",
        ),
        [
            (0, 0, 0, 0, True, does_not_raise()),
            (0, 0, 0, 0, False, does_not_raise()),
            (3, 1, 1, 1, True, does_not_raise()),
            (2, 1, 1, 1, True, pytest.raises(pydantic.ValidationError)),
            (3, 1, 2, 1, False, pytest.raises(pydantic.ValidationError)),
            (4, 1, 2, 1, False, does_not_raise()),
            (4, 1, 2, 1, True, pytest.raises(pydantic.ValidationError)),
        ],
    )
    def test_init(
        self,
        value_0,
        value_a_0,
        value_b_0,
        value_c_0,
        is_symmetrical,
        expectation,
    ) -> None:
        with expectation:
            ActivePower(
                value_0=value_0,
                value_a_0=value_a_0,
                value_b_0=value_b_0,
                value_c_0=value_c_0,
                is_symmetrical=is_symmetrical,
            )
