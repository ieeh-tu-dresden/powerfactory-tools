# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2025.
# :license: BSD 3-Clause

from psdm.quantities.multi_phase import ActivePower
from psdm.quantities.multi_phase import Angle
from psdm.quantities.multi_phase import ApparentPower
from psdm.quantities.multi_phase import CosPhi
from psdm.quantities.multi_phase import Current
from psdm.quantities.multi_phase import Droop
from psdm.quantities.multi_phase import PowerFactor
from psdm.quantities.multi_phase import ReactivePower
from psdm.quantities.multi_phase import TanPhi
from psdm.quantities.multi_phase import Voltage
from psdm.quantities.single_phase import Angle as AngleSP
from psdm.quantities.single_phase import ApparentPower as ApparentPowerSP
from psdm.quantities.single_phase import Current as CurrentSP
from psdm.quantities.single_phase import Frequency
from psdm.quantities.single_phase import SystemType
from psdm.quantities.single_phase import Voltage as VoltageSP


class QuantityConverter:
    @staticmethod
    def _sym_three_phase_no_power(value: float) -> tuple[float, float, float]:
        return (value, value, value)

    @staticmethod
    def _sym_three_phase_power(value: float) -> tuple[float, float, float]:
        return (value / 3, value / 3, value / 3)

    @staticmethod
    def single_phase_voltage(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> VoltageSP:
        return VoltageSP(value=value, system_type=modal_system_type)

    @staticmethod
    def single_phase_current(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> CurrentSP:
        return CurrentSP(value=value, system_type=modal_system_type)

    @staticmethod
    def single_phase_angle(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> AngleSP:
        return AngleSP(value=value, system_type=modal_system_type)

    @staticmethod
    def single_phase_apparent_power(
        value: float,
        modal_system_type: SystemType = SystemType.NATURAL,
    ) -> ApparentPowerSP:
        return ApparentPowerSP(value=value, system_type=modal_system_type)

    @staticmethod
    def single_phase_frequency(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> Frequency:
        return Frequency(value=value, system_type=modal_system_type)

    @staticmethod
    def sym_three_phase_angle(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> Angle:
        values = QuantityConverter._sym_three_phase_no_power(value)
        return Angle(
            value=tuple(values),
            system_type=modal_system_type,
        )

    @staticmethod
    def sym_three_phase_active_power(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> ActivePower:
        values = QuantityConverter._sym_three_phase_power(value)
        return ActivePower(
            value=tuple(values),
            system_type=modal_system_type,
        )

    @staticmethod
    def sym_three_phase_apparent_power(
        value: float,
        modal_system_type: SystemType = SystemType.NATURAL,
    ) -> ApparentPower:
        values = QuantityConverter._sym_three_phase_power(value)
        return ApparentPower(
            value=tuple(values),
            system_type=modal_system_type,
        )

    @staticmethod
    def sym_three_phase_current(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> Current:
        values = QuantityConverter._sym_three_phase_no_power(value)
        return Current(
            value=tuple(values),
            system_type=modal_system_type,
        )

    @staticmethod
    def sym_three_phase_droop(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> Droop:
        values = QuantityConverter._sym_three_phase_no_power(value)
        return Droop(
            value=tuple(values),
            system_type=modal_system_type,
        )

    @staticmethod
    def sym_three_phase_power_factor(value: float) -> PowerFactor:
        values = QuantityConverter._sym_three_phase_no_power(value)
        return PowerFactor(
            value=tuple(values),
        )

    @staticmethod
    def sym_three_phase_cos_phi(value: float) -> CosPhi:
        values = QuantityConverter._sym_three_phase_no_power(value)
        return CosPhi(
            value=tuple(values),
        )

    @staticmethod
    def sym_three_phase_tan_phi(value: float) -> TanPhi:
        values = QuantityConverter._sym_three_phase_no_power(value)
        return TanPhi(
            value=tuple(values),
        )

    @staticmethod
    def sym_three_phase_reactive_power(
        value: float,
        modal_system_type: SystemType = SystemType.NATURAL,
    ) -> ReactivePower:
        values = QuantityConverter._sym_three_phase_power(value)
        return ReactivePower(
            value=tuple(values),
            system_type=modal_system_type,
        )

    @staticmethod
    def sym_three_phase_voltage(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> Voltage:
        values = QuantityConverter._sym_three_phase_no_power(value)
        return Voltage(
            value=tuple(values),
            system_type=modal_system_type,
        )
