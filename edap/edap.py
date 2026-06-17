import logging
from contextlib import suppress
from typing import NamedTuple, TypedDict, Any
from datetime import datetime, timezone, timedelta
from copy import deepcopy
from abc import ABC

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

class _SampleValue(NamedTuple):
    exists: bool
    value: _MeasurementValue

class EdapDevice(ABC):
    """
    Base EdapDevice class. Holds main logic that includes trigger calculations.
    """
    def __init__(self, triggers: list[Trigger] | None = None) -> None:
        self._triggers: list[Trigger] = []
        self._last_sample: EdapSample | None = None
        self.set_triggers(triggers)

    def get_triggers(self) -> list[Trigger]:
        return self._triggers

    def set_triggers(self, triggers: list[Trigger] | None) -> None:
        if triggers is None:
            self._triggers = []
        else:
            self._triggers = triggers

    @staticmethod
    def _delta_triggered(current_sample_value: _MeasurementValue, trigger: Trigger) -> bool:
        if "delta" not in trigger:
            return False
        if "value" not in trigger:
            return True
        if not isinstance(current_sample_value, float | int | bool):
            return False
        trigger_value = trigger["value"]
        if not isinstance(trigger_value, float | int | bool):
            return False
        delta = trigger["delta"]
        if delta is None or delta == 0:
            return current_sample_value != trigger_value
        return abs(current_sample_value - trigger_value) > delta

    @staticmethod
    def _get_sample_value(sample: EdapSample | None, key: str | None) -> _SampleValue:
        if sample is None or key is None:
            return _SampleValue(False, None)
        if key not in sample:
            sensors = sample.get('sensors', {})
            if key not in sensors:
                return _SampleValue(False, None)
            value = sensors[key]
        else:
            value = sample.get(key)
        if not isinstance(value, _MeasurementValue):
            return _SampleValue(False, None)
        return _SampleValue(True, value)

    @staticmethod
    def _level_triggered(sample_value: _MeasurementValue, trigger: Trigger) -> bool:
        if "levels" not in trigger:
            return False
        if not isinstance(sample_value, float | int):
            return False
        levels: list[float] = trigger["levels"] or []
        if "value" not in trigger:
            return sample_value not in levels
        trigger_value = trigger["value"]
        if not isinstance(trigger_value, float | int):
            return False
        for level in levels:
            if trigger_value > level > sample_value or trigger_value < level < sample_value:
                return True
        return False

    @staticmethod
    def _tolerance_triggered(current_sample_value: _SampleValue, trigger: Trigger) -> bool:
        if "tolerance" not in trigger or trigger.get("tolerance") is None:
            return False
        trigger_value = trigger.get("value", trigger.get("tolerance"))
        has_value = current_sample_value.exists and current_sample_value.value is not None
        if (trigger_value is None and has_value) or (trigger_value is not None and not has_value):
            return True
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

    @staticmethod
    def _single_trigger_activated(
        current_sample: EdapSample,
        trigger: Trigger,
        conditions: dict[str, Trigger],
    ) -> bool:
        trigger_property: str | None = trigger.get('property')
        if trigger_property is None:
            return False
        try:
            if "conditions" in trigger:
                for condition in trigger.get("conditions") or []:
                    if condition in conditions and not EdapDevice._single_trigger_activated(
                        current_sample, conditions.get(condition, {}), conditions
                    ):
                        return False

            if trigger_property == "time":
                return EdapDevice._is_time_triggered(current_sample.get('time'), trigger)
            current_sample_value = EdapDevice._get_sample_value(current_sample, trigger_property)

            # A missing or None sample value must not activate any trigger other than the
            # tolerance trigger, which deliberately fires on value<->no-value transitions
            # (and only when it has been given a value different from None).
            if not (current_sample_value.exists and current_sample_value.value is not None):
                return EdapDevice._tolerance_triggered(current_sample_value, trigger)

            if "condition" in trigger and EdapDevice._condition_triggered(current_sample_value.value, trigger):
                return True

            return (
                EdapDevice._tolerance_triggered(current_sample_value, trigger)
                or EdapDevice._level_triggered(current_sample_value.value, trigger)
                or EdapDevice._delta_triggered(current_sample_value.value, trigger)
            )
        except Exception as e:
            logging.error("EdapDevice error: Error processing trigger %s: %s", trigger, e, exc_info=True)

        return False

    @staticmethod
    def apply_trigger(sample: EdapSample, triggers: list[Trigger]) -> EdapSample | None:
        """Check if a sample activates any triggers. Returns a triggered EdapSample with activated trigger IDs, or None if no triggers fired.
        To be noted is the input "triggers" object will be updated with the values of the activated triggers and their conditions,
        but the returned EdapSample will have the trigger IDs in the "triggers" list and not the full trigger objects.
        This is to avoid confusion about what properties are part of the triggered sample and what are part of the trigger definition."""
        conditions: dict[str, Trigger] = {}
        for t in triggers:
            condition = t.get("condition")
            if condition is not None:
                conditions[condition] = t

        full_activated_triggers: list[Trigger] = []
        for trigger in triggers:
            if "id" in trigger and EdapDevice._single_trigger_activated(sample, trigger, conditions):
                full_activated_triggers.append(trigger)

        if not full_activated_triggers:
            return None

        result = EdapDevice.generate_sample(sample)
        sensors: dict = sample.get('sensors') or {}

        for trigger in full_activated_triggers:
            trigger_property = trigger.get('property')

            trigger_value = EdapDevice._get_sample_value(sample, trigger_property)
            if trigger_value.exists:
                trigger['value'] = trigger_value.value
            for condition in trigger.get("conditions") or []:
                condition_property = conditions.get(condition, {}).get('property', None)
                if condition_property:
                    condition_value = EdapDevice._get_sample_value(sample, condition_property)
                    if condition_value.exists:
                        conditions[condition]['value'] = condition_value.value

            trigger_id = trigger.get("id")
            if trigger.get('discard_sample', False):
                trigger_id = f"#{trigger_id}"

            if trigger_id:
                result['triggers'].append(trigger_id)

            if len(result['sensors']) == len(sensors):
                continue

            trigger_sensors: list[str] | None = trigger.get('sensors')
            if trigger_sensors is None:
                result['sensors'] = deepcopy(sensors)
            else:
                for trigger_sensor in trigger_sensors:
                    sensor_value = sensors.get(trigger_sensor)
                    if sensor_value is not None:
                        result['sensors'][trigger_sensor] = sensor_value

        return deepcopy(result)

    def trigger(self, sample: EdapSample) -> EdapSample | None:
        """If some triggers were activated, return modified sample with trigger list inside, otherwise, return None"""
        result = self.apply_trigger(sample, self._triggers)
        if result is not None:
            self._last_sample = result
        return result

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
