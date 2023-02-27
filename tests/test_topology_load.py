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
            "cosphi",
            "cosphi_a",
            "cosphi_b",
            "cosphi_c",
            "expectation",
        ),
        [
            (0, 0, 0, 0, 0, 0, 0, 0, does_not_raise()),
            (3, 1, 1, 1, 1, 1, 1, 1, does_not_raise()),
            (4, 2, 1, 1, 1, 1, 1, 1, does_not_raise()),
            (2, 2, 1, 1, 1, 1, 2, 1, pytest.raises(pydantic.ValidationError)),
            (2, -2, 1, 1, 1, 1, 1, 1, pytest.raises(pydantic.ValidationError)),
            (0, -2, 1, 1, 1, 1, 1, 1, pytest.raises(pydantic.ValidationError)),
        ],
    )
    def test_init(  # noqa: PLR0913
        self,
        value,
        value_a,
        value_b,
        value_c,
        cosphi,
        cosphi_a,
        cosphi_b,
        cosphi_c,
        expectation,
    ) -> None:
        with expectation:
            RatedPower(
                value=value,
                value_a=value_a,
                value_b=value_b,
                value_c=value_c,
                cosphi=cosphi,
                cosphi_a=cosphi_a,
                cosphi_b=cosphi_b,
                cosphi_c=cosphi_c,
            )
