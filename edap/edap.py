from typing import TypedDict, Any
from datetime import datetime, timezone, timedelta
from copy import deepcopy
from abc import abstractmethod, ABC

class EdapSample(TypedDict):
    triggers: list[str]
    time: datetime
    power: float
    energy: float | None
    sample_energy: float | None
    duration: int
    sensors: dict


class Trigger(TypedDict):
    id: str | None
    property: str | None
    sensors: list[str] | None
    delta: int | float | None
    levels: list[float] | None
    tolerance: int | None
    value: Any
    discard_sample: bool | None

class EdapDevice(ABC):
    """
    Base EdapDevice class. Holds main logic that includes trigger calculations.
    """
    def __init__(self, triggers: list[Trigger] | None = None) -> None:
        self._triggers: list[Trigger] = triggers or []
        self._last_sample: EdapSample = {
            "energy": 0,
            "power": 0,
            "time": datetime.now(timezone.utc),
            "sensors": {},
            "triggers": [],
            "duration": 0,
            "sample_energy": 0
        }
        self._property_failures: dict[str, int] = {}

    def get_triggers(self) -> list[Trigger]:
        return self._triggers

    def set_triggers(self, triggers: list[Trigger] | None) -> None:
        if triggers is None:
            self._triggers = []
        else:
            self._triggers = triggers
        if len(self._triggers) == 0:
            self._triggers.append(
                {
                    "property": "time",
                    "delta": 3600,
                    "id": "unset_time"
                })

    def _delta_triggered(self, value: Any, trigger: Trigger) -> bool:
        if "delta" not in trigger:
            return False
        delta = trigger.get('delta')
        if delta is None or delta == 0:
            return value != trigger.get('value')
        return abs(value-(trigger.get('value') or 0)) > delta

    def _level_triggered(self, value: float, trigger: Trigger) -> bool:
        levels: list[float] = trigger.get('levels') or []
        trigger_property = trigger.get('property')
        if not trigger_property:
            return False
        last_value: float = self._last_sample.get(trigger_property) or (self._last_sample.get("sensors") or {}).get(trigger_property) or 0
        for level in levels:
            if last_value > level > value or last_value < level < value:
                return True
        return False

    def _is_tolerance_triggered(self, trigger: Trigger, exact_equals: bool) -> bool:
        tolerance: int | None = trigger.get('tolerance')
        failures: int | None = self._property_failures.get(trigger.get('property'))
        if tolerance is not None and failures is not None:
            return (exact_equals and failures == tolerance) or (not exact_equals and failures >= tolerance)
        return False

    def _is_time_triggered(self, sample_time: datetime, trigger: Trigger) -> bool:
        delta_time = trigger.get('delta')
        last_trigger_time = trigger.get('value')
        if last_trigger_time is not None:
            return sample_time - last_trigger_time >= timedelta(seconds=int(delta_time))
        return True

    def _single_trigger_activated(self, sample: EdapSample, trigger: Trigger) -> bool:
        trigger_property: str = trigger.get('property')
        if trigger_property == "time":
            return self._is_time_triggered(sample.get('time'), trigger)
        value: Any = sample.get(trigger_property) or (sample.get('sensors') or {}).get(trigger_property)
        if value is not None:
            tolerance_triggered = self._is_tolerance_triggered(trigger, False)
            self._property_failures[trigger_property] = 0
            if tolerance_triggered or self._level_triggered(value, trigger) or self._delta_triggered(value, trigger):
                return True
        else:
            self._property_failures[trigger_property] = self._property_failures.get(trigger_property, 0) + 1
            if self._is_tolerance_triggered(trigger, True):
                return True
        return False

    def _round(self, number: float | None, precision: int = 6) -> float | None:
        # doesn't really belong in the class, to be moved in a util file
        return None if number is None else round(number, precision)

    def trigger(self, sample: EdapSample) -> EdapSample | None:
        """If some triggers were activated, return modified sample with trigger list inside, otherwise, return None"""
        full_activated_triggers: list[Trigger] = []

        for trigger in self._triggers:
            if self._single_trigger_activated(sample, trigger):
                full_activated_triggers.append(trigger)

        if len(full_activated_triggers) == 0:
            return None

        self._last_sample = self.generate_sample(sample)
        sensors: dict = sample.get('sensors') or {}

        for trigger in full_activated_triggers:
            trigger_property = trigger.get('property')

            # update the values of activated triggers
            trigger['value'] = sample.get(trigger_property) or sensors.get(trigger_property)

            # if the trigger tells us to discard the sample, we add a # in front of the trigger id
            trigger_id = trigger.get('id', f'unset_{trigger_property}')
            if trigger.get('discard_sample', False):
                trigger_id = f"#{trigger_id}"

            # add ids of activated triggers to EDAP sample
            self._last_sample['triggers'].append(trigger_id)

            if len(self._last_sample['sensors']) == len(sensors):
                continue

            trigger_sensors: list[str] | None = trigger.get('sensors')
            if trigger_sensors is None:
                self._last_sample['sensors'] = deepcopy(sensors)
            else:
                for trigger_sensor in trigger_sensors:
                    sensor_value = sensors.get(trigger_sensor)
                    if sensor_value is not None:
                        self._last_sample['sensors'][trigger_sensor] = sensor_value

        return deepcopy(self._last_sample)

    def _get_delta(self, sample, prop, calc_prop):
        if prop in sample or sample.get(calc_prop) is None or self._last_sample.get(calc_prop) is None:
            return sample.get(prop)
        if calc_prop == "time":
            return (sample.get("time") - self._last_sample.get("time")).total_seconds()
        return sample.get(calc_prop,0) - self._last_sample.get(calc_prop,0)

    def generate_sample(self, sample: EdapSample) -> EdapSample:
        """
        Method for generating base EDAP structure for triggered EDAP samples. The "sensors" and "triggers" properties are empty as these 
        will be filled in by the various activated triggers. Also "sample_energy" and "duration" will be calcualted if they are not provided.
        If any calculations involving values from the last sample are needed, this method needs to be overrriden. Any sensors added here will always
        be present in the triggered EDAP sample.
        """
        return {
            "time":  sample.get("time"),
            "power": sample.get("power"),
            "energy": sample.get("energy"),
            "sample_energy": self._get_delta(sample, "sample_energy", "energy"),
            "duration": self._get_delta(sample, "duration", "time"),
            "triggers": [],
            "sensors": {}
        }
