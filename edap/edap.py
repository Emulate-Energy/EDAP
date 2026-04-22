import logging
from contextlib import suppress
from typing import TypedDict, Any
from datetime import datetime, timezone, timedelta
from copy import deepcopy
from abc import abstractmethod, ABC

class EdapSample(TypedDict):
    triggers: list[str]
    time: datetime | None
    power: float | None
    energy: float | None
    sensors: dict


Trigger = TypedDict("Trigger", {
    "id": str | None,
    "condition": str | None,
    "property": str | None,
    "sensors": list[str] | None,
    "delta": int | float | None,
    "levels": list[float] | None,
    "tolerance": int | None,
    "value": Any,
    "discard_sample": bool | None,
    "in": list[int] | list[float] | list[str] | list[bool] | None,
    "greater": int | float | None,
    "less": int | float | None,
    "conditions": list[str] | None
}, total=False)

_MeasurementValue = int | float | str | bool | datetime | None

class EdapDevice(ABC):
    """
    Base EdapDevice class. Holds main logic that includes trigger calculations.
    """
    def __init__(self, triggers: list[Trigger] | None = None) -> None:
        self._triggers: list[Trigger] = []
        self._last_sample: EdapSample = {
            "energy": 0,
            "power": 0,
            "time": datetime.now(timezone.utc),
            "sensors": {},
            "triggers": []
        }
        self._property_failures: dict[str, int] = {}
        self._conditions: dict[str, Trigger] = {}
        self.set_triggers(triggers)

    def get_triggers(self) -> list[Trigger]:
        return self._triggers

    def set_triggers(self, triggers: list[Trigger] | None) -> None:
        if triggers is None:
            self._triggers = []
        else:
            self._triggers = triggers
        self._conditions = {}
        for trigger in self._triggers:
            condition = trigger.get("condition")
            if condition is not None:
                self._conditions[condition] = trigger

    @staticmethod
    def _delta_triggered(current_sample_value: _MeasurementValue, trigger: Trigger) -> bool:
        if "delta" not in trigger:
            return False
        if "value" not in trigger:
            return True
        if not isinstance(current_sample_value, float | int):
            return False
        trigger_value = trigger["value"]
        if not isinstance(trigger_value, float | int):
            return False
        delta = trigger["delta"]
        if delta is None or delta == 0:
            return current_sample_value != trigger_value
        return abs(current_sample_value - trigger_value) > delta

    @staticmethod
    def _level_triggered(sample_value: _MeasurementValue, trigger: Trigger) -> bool:
        if "levels" not in trigger:
            return False
        if "value" not in trigger:
            return True
        if not isinstance(sample_value, float | int):
            return False
        trigger_value = trigger["value"]
        if not isinstance(trigger_value, float | int):
            return False
        levels: list[float] = trigger["levels"] or []
        for level in levels:
            if trigger_value > level > sample_value or trigger_value < level < sample_value:
                return True
        return False

    def _is_tolerance_triggered(self, trigger: Trigger, exact_equals: bool) -> bool:
        tolerance: int | None = trigger.get('tolerance')
        failures: int | None = self._property_failures.get(trigger.get('property'))
        if tolerance is not None and failures is not None:
            return (exact_equals and failures == tolerance) or (not exact_equals and failures >= tolerance)
        return False

    @staticmethod
    def _is_time_triggered(sample_time: datetime | None, trigger: Trigger) -> bool:
        if sample_time is None:
            return False
        delta_time = trigger.get('delta')
        last_trigger_time = trigger.get('value')

        if not isinstance(last_trigger_time, datetime):
            if isinstance(last_trigger_time, str):
                try:
                    last_trigger_time = datetime.fromisoformat(last_trigger_time)
                except ValueError:
                    last_trigger_time = None
            elif isinstance(last_trigger_time, (int, float)):
                try:
                    last_trigger_time = datetime.fromtimestamp(last_trigger_time, tz=timezone.utc)
                except (ValueError, TypeError):
                    last_trigger_time = None
        elif last_trigger_time.tzinfo is None:
            last_trigger_time = last_trigger_time.replace(tzinfo=timezone.utc)

        if isinstance(delta_time, str):
            try:
                delta_time = float(delta_time)
            except ValueError:
                delta_time = None

        delta = timedelta(seconds=float(delta_time)) if delta_time is not None else timedelta(seconds=60)

        if last_trigger_time is not None:
            with suppress(TypeError):
                return sample_time - last_trigger_time >= delta
        return True

    @staticmethod
    def _condition_triggered(current_sample_value: _MeasurementValue, trigger: Trigger) -> bool:
        if not ("greater" in trigger or "less" in trigger or "in" in trigger):
            return False
        limit_greater = trigger.get("greater")
        if limit_greater is not None and (
            not isinstance(current_sample_value, float | int)
            or current_sample_value <= limit_greater
        ):
            return False
        limit_less = trigger.get("less")
        if limit_less is not None and (
            not isinstance(current_sample_value, float | int)
            or current_sample_value >= limit_less
        ):
            return False
        values_in = trigger.get("in")
        if values_in is not None and current_sample_value not in values_in:
            return False
        return True

    def _single_trigger_activated(self, sample: EdapSample, trigger: Trigger) -> bool:
        trigger_property: str | None = trigger.get('property')
        if trigger_property is None:
            return False
        try:
            if "conditions" in trigger:
                for condition in trigger.get("conditions"):
                    if condition in self._conditions and not self._single_trigger_activated(sample, self._conditions.get(condition)):
                        return False

            if trigger_property == "time":
                return self._is_time_triggered(sample.get('time'), trigger)
            value: Any = sample.get(trigger_property) or (sample.get('sensors') or {}).get(trigger_property)
            if value is not None:
                if "condition" in trigger and self._condition_triggered(value, trigger):
                    return True
                tolerance_triggered = self._is_tolerance_triggered(trigger, False)
                self._property_failures[trigger_property] = 0
                if tolerance_triggered or self._level_triggered(value, trigger) or self._delta_triggered(value, trigger):
                    return True
            else:
                self._property_failures[trigger_property] = self._property_failures.get(trigger_property, 0) + 1
                if self._is_tolerance_triggered(trigger, True):
                    return True
        except Exception as e:
            logging.error("EdapDevice error: Error processing trigger %s: %s", trigger, e, exc_info=True)

        return False

    def trigger(self, sample: EdapSample) -> EdapSample | None:
        """If some triggers were activated, return modified sample with trigger list inside, otherwise, return None"""
        full_activated_triggers: list[Trigger] = []

        for trigger in self._triggers:
            if "id" in trigger and self._single_trigger_activated(sample, trigger):
                full_activated_triggers.append(trigger)

        if len(full_activated_triggers) == 0:
            return None

        self._last_sample = self.generate_sample(sample)
        sensors: dict = sample.get('sensors') or {}

        for trigger in full_activated_triggers:
            trigger_property = trigger.get('property')

            # update the values of activated triggers
            trigger['value'] = sample.get(trigger_property, sensors.get(trigger_property))
            if "conditions" in trigger:
                for condition in trigger.get("conditions"):
                    condition_property =  self._conditions.get(condition, {}).get('property', None)
                    if condition_property:
                        self._conditions[condition]['value'] = sample.get(condition_property) or sensors.get(condition_property)

            # if the trigger tells us to discard the sample, we add a # in front of the trigger id
            trigger_id = trigger.get("id")
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

    @staticmethod
    def generate_sample(sample: EdapSample) -> EdapSample:
        """
        Method for generating base EDAP structure for triggered EDAP samples. The "sensors" and "triggers" properties are empty as these 
        will be filled in by the various activated triggers.
        If any calculations involving values from the last sample are needed, this method needs to be overrriden. Any sensors added here will always
        be present in the triggered EDAP sample.
        """
        return {
            "time":  sample.get("time"),
            "power": sample.get("power"),
            "energy": sample.get("energy"),
            "triggers": [],
            "sensors": {}
        }
