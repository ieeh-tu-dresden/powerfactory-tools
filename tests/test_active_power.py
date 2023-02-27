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
            "value",
            "value_a",
            "value_b",
            "value_c",
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
    def test_init(  # noqa: PLR0913
        self,
        value,
        value_a,
        value_b,
        value_c,
        is_symmetrical,
        expectation,
    ) -> None:
        with expectation:
            ActivePower(
                value=value,
                value_a=value_a,
                value_b=value_b,
                value_c=value_c,
                is_symmetrical=is_symmetrical,
            )
