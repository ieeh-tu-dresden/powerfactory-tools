# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from contextlib import nullcontext as does_not_raise

import pydantic
import pytest

from powerfactory_tools.schema.steadystate_case.controller import ControlCosphiConst
from powerfactory_tools.schema.steadystate_case.controller import ControlCosphiP
from powerfactory_tools.schema.steadystate_case.controller import ControlCosphiU
from powerfactory_tools.schema.steadystate_case.controller import ControlledVoltageRef
from powerfactory_tools.schema.steadystate_case.controller import ControlQConst
from powerfactory_tools.schema.steadystate_case.controller import ControlQP
from powerfactory_tools.schema.steadystate_case.controller import ControlQU
from powerfactory_tools.schema.steadystate_case.controller import ControlStrategy
from powerfactory_tools.schema.steadystate_case.controller import ControlTanphiConst
from powerfactory_tools.schema.steadystate_case.controller import ControlUConst
from powerfactory_tools.schema.topology.load import CosphiDir


class TestControlQConst:
    @pytest.mark.parametrize(
        (
            "control_strategy",
            "q_set",
            "expectation",
        ),
        [
            (ControlStrategy.Q_CONST, -1500, does_not_raise()),
            (ControlStrategy.Q_CONST, 1500, does_not_raise()),
            (ControlStrategy.Q_CONST, 0, does_not_raise()),
            (ControlStrategy.Q_CONST, None, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.U_CONST, 0, pytest.raises(pydantic.ValidationError)),
        ],
    )
    def test_init(
        self,
        control_strategy,
        q_set,
        expectation,
    ) -> None:
        with expectation:
            ControlQConst(
                control_strategy=control_strategy,
                q_set=q_set,
            )


class TestControlUConst:
    @pytest.mark.parametrize(
        (
            "control_strategy",
            "u_set",
            "u_meas_tref",
            "expectation",
        ),
        [
            (ControlStrategy.U_CONST, 110000, ControlledVoltageRef.POS_SEQUENCE, does_not_raise()),
            (ControlStrategy.U_CONST, 100000, ControlledVoltageRef.AVERAGE, does_not_raise()),
            (ControlStrategy.U_CONST, 110000, None, pytest.raises(pydantic.ValidationError)),
            (
                ControlStrategy.U_CONST,
                -110000,
                ControlledVoltageRef.POS_SEQUENCE,
                pytest.raises(pydantic.ValidationError),
            ),
            (ControlStrategy.U_CONST, None, ControlledVoltageRef.POS_SEQUENCE, pytest.raises(pydantic.ValidationError)),
            (
                ControlStrategy.Q_CONST,
                110000,
                ControlledVoltageRef.POS_SEQUENCE,
                pytest.raises(pydantic.ValidationError),
            ),
        ],
    )
    def test_init(
        self,
        control_strategy,
        u_set,
        u_meas_tref,
        expectation,
    ) -> None:
        with expectation:
            ControlUConst(
                control_strategy=control_strategy,
                u_set=u_set,
                u_meas_tref=u_meas_tref,
            )


class TestControlTanphiConst:
    @pytest.mark.parametrize(
        (
            "control_strategy",
            "cosphi_dir",
            "cosphi",
            "expectation",
        ),
        [
            (ControlStrategy.TANPHI_CONST, CosphiDir.UE, 1, does_not_raise()),
            (ControlStrategy.TANPHI_CONST, CosphiDir.UE, 0, does_not_raise()),
            (ControlStrategy.TANPHI_CONST, CosphiDir.OE, 0.9, does_not_raise()),
            (ControlStrategy.TANPHI_CONST, None, 0.9, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.TANPHI_CONST, CosphiDir.OE, -0.9, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.TANPHI_CONST, CosphiDir.OE, 2, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.TANPHI_CONST, CosphiDir.OE, None, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_CONST, CosphiDir.UE, 0.9, pytest.raises(pydantic.ValidationError)),
        ],
    )
    def test_init(
        self,
        control_strategy,
        cosphi_dir,
        cosphi,
        expectation,
    ) -> None:
        with expectation:
            ControlTanphiConst(
                control_strategy=control_strategy,
                cosphi_dir=cosphi_dir,
                cosphi=cosphi,
            )


class TestControlCosphiConst:
    @pytest.mark.parametrize(
        (
            "control_strategy",
            "cosphi_dir",
            "cosphi",
            "expectation",
        ),
        [
            (ControlStrategy.COSPHI_CONST, CosphiDir.UE, 1, does_not_raise()),
            (ControlStrategy.COSPHI_CONST, CosphiDir.UE, 0, does_not_raise()),
            (ControlStrategy.COSPHI_CONST, CosphiDir.OE, 0.9, does_not_raise()),
            (ControlStrategy.COSPHI_CONST, None, 0.9, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.COSPHI_CONST, CosphiDir.OE, -0.9, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.COSPHI_CONST, CosphiDir.OE, 2, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.COSPHI_CONST, CosphiDir.OE, None, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_CONST, CosphiDir.UE, 0.9, pytest.raises(pydantic.ValidationError)),
        ],
    )
    def test_init(
        self,
        control_strategy,
        cosphi_dir,
        cosphi,
        expectation,
    ) -> None:
        with expectation:
            ControlCosphiConst(
                control_strategy=control_strategy,
                cosphi_dir=cosphi_dir,
                cosphi=cosphi,
            )


class TestControlCosphiP:
    @pytest.mark.parametrize(
        (
            "control_strategy",
            "cosphi_ue",
            "cosphi_oe",
            "p_threshold_ue",
            "p_threshold_oe",
            "expectation",
        ),
        [
            (ControlStrategy.COSPHI_P, 0.9, 0.9, -1, -2, does_not_raise()),
            (ControlStrategy.COSPHI_P, 1, 0, -2, -1, does_not_raise()),
            (ControlStrategy.COSPHI_P, 0.9, 1.1, -2, -1, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.COSPHI_P, 1.1, 0.9, -2, -1, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.COSPHI_P, -0.9, 0.9, -2, -1, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.COSPHI_P, 0.9, -0.9, -2, -1, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.COSPHI_P, 0.9, 0.9, 2, -1, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.COSPHI_P, 0.9, 0.9, -2, 1, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_CONST, 0.9, 0.9, -2, -1, pytest.raises(pydantic.ValidationError)),
        ],
    )
    def test_init(  # noqa: PLR0913
        self,
        control_strategy,
        cosphi_ue,
        cosphi_oe,
        p_threshold_ue,
        p_threshold_oe,
        expectation,
    ) -> None:
        with expectation:
            ControlCosphiP(
                control_strategy=control_strategy,
                cosphi_ue=cosphi_ue,
                cosphi_oe=cosphi_oe,
                p_threshold_ue=p_threshold_ue,
                p_threshold_oe=p_threshold_oe,
            )


class TestControlCosphiU:
    @pytest.mark.parametrize(
        (
            "control_strategy",
            "cosphi_ue",
            "cosphi_oe",
            "u_threshold_ue",
            "u_threshold_oe",
            "expectation",
        ),
        [
            (ControlStrategy.COSPHI_U, 0.9, 0.9, 20000, 24000, does_not_raise()),
            (ControlStrategy.COSPHI_U, 1, 0, 24000, 20000, does_not_raise()),
            (ControlStrategy.COSPHI_U, 0.9, 1.1, 24000, 20000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.COSPHI_U, 1.1, 0.9, 24000, 20000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.COSPHI_U, -0.9, 0.9, 24000, 20000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.COSPHI_U, 0.9, -0.9, 24000, 20000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.COSPHI_U, 0.9, 0.9, -24000, 20000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.COSPHI_U, 0.9, 0.9, 20000, -20000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_CONST, 0.9, 0.9, 20000, 24000, pytest.raises(pydantic.ValidationError)),
        ],
    )
    def test_init(  # noqa: PLR0913
        self,
        control_strategy,
        cosphi_ue,
        cosphi_oe,
        u_threshold_ue,
        u_threshold_oe,
        expectation,
    ) -> None:
        with expectation:
            ControlCosphiU(
                control_strategy=control_strategy,
                cosphi_ue=cosphi_ue,
                cosphi_oe=cosphi_oe,
                u_threshold_ue=u_threshold_ue,
                u_threshold_oe=u_threshold_oe,
            )


class TestControlQU:
    @pytest.mark.parametrize(
        (
            "control_strategy",
            "m_tg_2015",
            "m_tg_2018",
            "u_q0",
            "u_deadband_up",
            "u_deadband_low",
            "q_max_ue",
            "q_max_oe",
            "expectation",
        ),
        [
            (ControlStrategy.Q_U, 5, 6, 110000, 1000, 1000, 10000, 10000, does_not_raise()),
            (ControlStrategy.Q_U, 5, 6, 110000, 1000, 2000, 20000, 10000, does_not_raise()),
            (ControlStrategy.Q_U, -5, 6, 110000, 1000, 2000, 20000, 10000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_U, 5, -6, 110000, 1000, 2000, 20000, 10000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_U, 5, 6, -110000, 1000, 2000, 20000, 10000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_U, 5, 6, 110000, -1000, 2000, 20000, 10000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_U, 5, 6, 110000, 1000, -2000, 20000, 10000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_U, 5, 6, 110000, 1000, 2000, -20000, 10000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_U, 5, 6, 110000, 1000, 2000, 20000, -10000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_CONST, 5, 6, 110000, 1000, 2000, 20000, 10000, pytest.raises(pydantic.ValidationError)),
        ],
    )
    def test_init(  # noqa: PLR0913
        self,
        control_strategy,
        m_tg_2015,
        m_tg_2018,
        u_q0,
        u_deadband_up,
        u_deadband_low,
        q_max_ue,
        q_max_oe,
        expectation,
    ) -> None:
        with expectation:
            ControlQU(
                control_strategy=control_strategy,
                m_tg_2015=m_tg_2015,
                m_tg_2018=m_tg_2018,
                u_q0=u_q0,
                u_deadband_up=u_deadband_up,
                u_deadband_low=u_deadband_low,
                q_max_ue=q_max_ue,
                q_max_oe=q_max_oe,
            )


class TestControlQP:
    @pytest.mark.parametrize(
        (
            "control_strategy",
            "q_p_characteristic_name",
            "q_max_ue",
            "q_max_oe",
            "expectation",
        ),
        [
            (ControlStrategy.Q_P, "Q(P)-char", 10000, 10000, does_not_raise()),
            (ControlStrategy.Q_P, "Q(P)-char", 10000, 20000, does_not_raise()),
            (ControlStrategy.Q_P, None, 10000, 10000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_P, "Q(P)-char", -10000, 10000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_P, "Q(P)-char", 10000, -10000, pytest.raises(pydantic.ValidationError)),
            (ControlStrategy.Q_CONST, "Q(P)-char", 10000, 10000, pytest.raises(pydantic.ValidationError)),
        ],
    )
    def test_init(  # noqa: PLR0913
        self,
        control_strategy,
        q_p_characteristic_name,
        q_max_ue,
        q_max_oe,
        expectation,
    ) -> None:
        with expectation:
            ControlQP(
                control_strategy=control_strategy,
                q_p_characteristic_name=q_p_characteristic_name,
                q_max_ue=q_max_ue,
                q_max_oe=q_max_oe,
            )
