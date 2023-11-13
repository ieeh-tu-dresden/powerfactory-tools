# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from psdm.quantities.multi_phase import ActivePower
from psdm.quantities.multi_phase import Angle
from psdm.quantities.multi_phase import ApparentPower
from psdm.quantities.multi_phase import Current
from psdm.quantities.multi_phase import Droop
from psdm.quantities.multi_phase import PowerFactor
from psdm.quantities.multi_phase import ReactivePower
from psdm.quantities.multi_phase import Voltage
from psdm.quantities.single_phase import Angle as AngleSP
from psdm.quantities.single_phase import ApparentPower as ApparentPowerSP
from psdm.quantities.single_phase import Current as CurrentSP
from psdm.quantities.single_phase import Frequency
from psdm.quantities.single_phase import SystemType
from psdm.quantities.single_phase import Voltage as VoltageSP

from powerfactory_tools.constants import DecimalDigits


def _sym_three_phase_no_power(value: float) -> tuple[float, float, float]:
    return (value, value, value)


def _sym_three_phase_power(value: float) -> tuple[float, float, float]:
    return (value / 3, value / 3, value / 3)


def single_phase_voltage(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> VoltageSP:
    return VoltageSP(value=round(value, DecimalDigits.VOLTAGE), system_type=modal_system_type)


def single_phase_current(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> CurrentSP:
    return CurrentSP(value=round(value, DecimalDigits.CURRENT), system_type=modal_system_type)


def single_phase_angle(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> AngleSP:
    return AngleSP(value=round(value, DecimalDigits.ANGLE), system_type=modal_system_type)


def single_phase_apparent_power(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> ApparentPowerSP:
    return ApparentPowerSP(value=round(value, DecimalDigits.POWER), system_type=modal_system_type)


def single_phase_frequency(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> Frequency:
    return Frequency(value=round(value, DecimalDigits.FREQUENCY), system_type=modal_system_type)


def sym_three_phase_angle(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> Angle:
    values = _sym_three_phase_no_power(value)
    return Angle(
        value=[round(v, DecimalDigits.ANGLE) for v in values],
        system_type=modal_system_type,
    )


def sym_three_phase_active_power(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> ActivePower:
    values = _sym_three_phase_power(value)
    return ActivePower(
        value=[round(v, DecimalDigits.POWER) for v in values],
        system_type=modal_system_type,
    )


def sym_three_phase_apparent_power(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> ApparentPower:
    values = _sym_three_phase_power(value)
    return ApparentPower(
        value=[round(v, DecimalDigits.POWER) for v in values],
        system_type=modal_system_type,
    )


def sym_three_phase_current(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> Current:
    values = _sym_three_phase_no_power(value)
    return Current(
        value=[round(v, DecimalDigits.CURRENT) for v in values],
        system_type=modal_system_type,
    )


def sym_three_phase_droop(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> Droop:
    values = _sym_three_phase_no_power(value)
    return Droop(
        value=[round(v, DecimalDigits.PU) for v in values],
        system_type=modal_system_type,
    )


def sym_three_phase_power_factor(value: float) -> PowerFactor:
    values = _sym_three_phase_no_power(value)
    return PowerFactor(
        value=[round(v, DecimalDigits.POWERFACTOR) for v in values],
    )


def sym_three_phase_reactive_power(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> ReactivePower:
    values = _sym_three_phase_power(value)
    return ReactivePower(
        value=[round(v, DecimalDigits.POWER) for v in values],
        system_type=modal_system_type,
    )


def sym_three_phase_voltage(value: float, modal_system_type: SystemType = SystemType.NATURAL) -> Voltage:
    values = _sym_three_phase_no_power(value)
    return Voltage(
        value=[round(v, DecimalDigits.VOLTAGE) for v in values],
        system_type=modal_system_type,
    )
