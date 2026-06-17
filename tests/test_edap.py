from datetime import datetime, timezone, timedelta
from edap.edap import EdapDevice

import pytest


def test_get_set_triggers():
    edap_device = EdapDevice()
    assert len(edap_device.get_triggers()) == 0
    edap_device.set_triggers([
        {
            "id": "power_1",
            "property": "power",
            "value": 25,
            "delta": 2
        }
    ])
    assert len(edap_device.get_triggers()) == 1
    edap_device.set_triggers([])
    assert len(edap_device.get_triggers()) == 0
    edap_device.set_triggers([
        {
            "id": "power_1",
            "property": "power",
            "value": 25,
            "delta": 2
        }
    ])
    assert len(edap_device.get_triggers()) == 1
    edap_device.set_triggers(None)
    assert len(edap_device.get_triggers()) == 0

def test_single_trigger():
    edap_device = EdapDevice()
    edap_device.set_triggers([
    {
        "property": "power",
        "delta": 2,
        "value": 20,
        "id": "power_id"
    }
    ])

    # this sample should not trigger the trigger, no changes to trigger spec
    triggered_sample = edap_device.trigger({"power": 21})
    assert triggered_sample is None
    assert edap_device.get_triggers()[0]['value'] == 20


    # this one should
    triggered_sample = edap_device.trigger({"power": 23})
    assert triggered_sample is not None
    assert triggered_sample.get("triggers")[0] == "power_id"
    assert edap_device.get_triggers()[0]['value'] == 23

def test_delta_trigger_on_non_exiting_property():
    first_sample_time = datetime.now(timezone.utc)
    edap_device = EdapDevice()
    edap_device.set_triggers([
    {
        "property": "current_max",
        "delta": 1,
        "value": 20,
        "id": "current_max_id"
    }
    ])

    # this sample should not trigger since the ttriigger propert is not exisitng in the sample
    triggered_sample = edap_device.trigger({"energy": 100, "time": first_sample_time, "sensors": {"temp": 21}})
    assert triggered_sample is None
    triggered_sample = edap_device.trigger({"energy": 100, "sensors": {"temp": 21, "current_max": None}})
    assert triggered_sample is None
    triggered_sample = edap_device.trigger({"energy": 100, "sensors": {"temp": 21, "current_max": 7}})
    assert triggered_sample is not None

def test_multiple_triggers():
    edap_device = EdapDevice()
    edap_device.set_triggers([
        {
            "id": "power_1",
            "property": "power",
            "value": 25,
            "delta": 2
        },
        {
            "id": "temperature_1",
            "property": "temp",
            "value": 20,
            "delta": 0.5
        }
    ])

    triggered_sample = edap_device.trigger({"power": 22, "sensors": {"temp": 21}})
    assert triggered_sample is not None
    assert triggered_sample.get('triggers') == ["power_1", "temperature_1"]

def test_time_trigger():
    edap_device = EdapDevice()
    first_sample_time = datetime.now(timezone.utc)
    edap_device.set_triggers([
    {
        "property": "time",
        "delta": 60,
        "value": first_sample_time,
        "id": "time_id"
    },
    {
        "property": "power",
        "delta": 2,
        "value": 20,
        "id": "power_id"
    }
    ])
    # this sample triggers the power_id trigger and the time of the last sample is set to the time of this sample
    triggered_sample = edap_device.trigger({"time": first_sample_time, "power": 23})
    assert triggered_sample is not None
    assert triggered_sample.get("triggers")[0] == "power_id"

    # since time of the last sample was 2 minutes ago, and delta of the time trigger is defined as 60 seconds,
    # this sample should trigger the time_id trigger
    triggered_sample = edap_device.trigger({"time": first_sample_time + timedelta(minutes=2), "power": 20})
    assert triggered_sample is not None
    assert triggered_sample.get("triggers")[0] == "time_id"
    assert triggered_sample.get("triggers")[1] == "power_id"

def test_time_trigger__value_is_none():
    edap_device = EdapDevice()
    edap_device.set_triggers([
    {
        "property": "time",
        "delta": 60,
        "value": None,
        "id": "time_id"
    }])
    sample_time = datetime.now(timezone.utc)

    triggered_sample = edap_device.trigger({"time": sample_time, "power": 20})
    assert triggered_sample is not None
    assert triggered_sample.get("triggers")[0] == "time_id"
    assert edap_device.get_triggers()[0].get('value') == sample_time


def test_tolerance_trigger():
    edap_device = EdapDevice()
    edap_device.set_triggers([
    {
        "property": "power",
        "value": 20,
        "delta": 2,
        "tolerance": 2,
        "id": "power_id"
    }
    ])

    triggered_sample = edap_device.trigger({"power": None})
    # last known value was 20 (not None), now None — value disappeared, trigger activated
    assert triggered_sample is not None

    triggered_sample = edap_device.trigger({"power": None})
    # last known value is now None, still None — no transition, trigger not activated
    assert triggered_sample is None

    triggered_sample = edap_device.trigger({"power": 21})
    # last known value was None, now 21 — value appeared, trigger activated
    assert triggered_sample is not None

def test_tolerance_trigger_none(): 
    edap_device = EdapDevice()
    edap_device.set_triggers([
    {
        "property": "power",
        "value": 15,
        "delta": 2,
        "tolerance": None,
        "id": "power_id"
    }
    ])

    triggered_sample = edap_device.trigger({"power": 20})
    # last known value was None, now 20 — value appeared, trigger activated
    assert triggered_sample is not None

    triggered_sample = edap_device.trigger({"power": 20})
    # last known value is now 20, still 20 — no transition, trigger not activated
    assert triggered_sample is None

    triggered_sample = edap_device.trigger({"power": None})
    # last known value was 20, now None — value disappeared, trigger not activated because tolerance is None
    assert triggered_sample is None

def test_missing_or_none_value_does_not_activate_non_tolerance_triggers():
    # A missing or None sample value must not activate delta/level/condition triggers,
    # not even on the first sample (where no previous trigger value is stored yet).
    edap_device = EdapDevice()
    edap_device.set_triggers([
        {"id": "delta_id", "property": "power", "delta": 2},
        {"id": "levels_id", "property": "power", "levels": [10, 20]},
        {"id": "cond_id", "property": "power", "condition": "c", "greater": 0},
    ])

    # None value on the first sample — previously the delta trigger fired here
    assert edap_device.trigger({"power": None}) is None
    # missing property entirely
    assert edap_device.trigger({}) is None
    # a real value still triggers as normal
    assert edap_device.trigger({"power": 25}) is not None


def test_none_value_only_activates_tolerance_trigger():
    # When a value disappears, only the tolerance trigger should fire even though a
    # delta is also configured on the same property.
    edap_device = EdapDevice()
    edap_device.set_triggers([
        {"id": "power_id", "property": "power", "value": 20, "delta": 2, "tolerance": 2},
    ])

    result = edap_device.trigger({"power": None})
    assert result is not None
    assert result["triggers"] == ["power_id"]


def test_level_triggered():
    edap_device = EdapDevice()
    edap_device.set_triggers([
    {
        "id": "levels_1",
        "property": "power",
        "levels": [10, 15, 30]
    },
    {
        "id": "levels_2",
        "property": "power",
        "levels": [19, 30]
    },
    {
        "id": "tolerance_2",
        "property": "power",
        "tolerance": None
    }
    ])

    assert edap_device.trigger({"power": 9}) is not None

    # level 10 activated
    assert edap_device.trigger({"power": 11}) is not None

    # no level passed
    assert edap_device.trigger({"power": 14}) is None

    # level 15 passed
    assert edap_device.trigger({"power": 18}) is not None

def test_condition_special_triggers():
    edap_device = EdapDevice()
    edap_device.set_triggers([
        {
            "id": "delta_1",
            "property": "power",
            "delta": 2,
            "conditions": ["c1", "c2", "c3"]
        },
        {
            "id": "levels_2",
            "property": "power",
            "levels": [19, 30]
        },
        {
            "condition": "c1",
            "property": "power",
            "greater": 12,
            "less": 22
        },
        {
            "condition": "c2",
            "property": "power",
            "in": [5,10,11,12,13,14,15,20,21,25]
        },
    ])
    assert edap_device.trigger({"power": 7}).get("triggers") == ["levels_2"]
    assert edap_device.trigger({"power": 11}) is None
    assert edap_device.trigger({"power": 14}).get("triggers") == ['delta_1'] # both c1 and c2 satisfied and initial delta
    assert edap_device.trigger({"power": 15}) is None
    assert edap_device.trigger({"power": 18}) is None
    assert edap_device.trigger({"power": 20}).get("triggers") == ['delta_1','levels_2'] # both c1 and c2 satisfied
    assert edap_device.trigger({"power": 21}) is None #c1 and c2 satisfied but not delta
    assert edap_device.trigger({"power": 25}) is None
    assert edap_device.trigger({"power": 35}).get("triggers") == ['levels_2']

def test_condition_standard_triggers():
    edap_device = EdapDevice()
    edap_device.set_triggers([
        {
            "id": "delta_1",
            "property": "power",
            "delta": 2,
            "conditions": ["c1", "c2", "c3"]
        },
        {
            "condition": "c1",
            "property": "temp",
            "delta": 2
        },
        {
            "condition": "c2",
            "property": "connector",
            "in": ["con_1", "con_2"]
        },
        {
            "condition": "c3",
            "property": "active",
            "in": [True]
        },
    ])
    assert edap_device.trigger({"power": 7, "sensors": {"active": False, "connector": "con_3", "temp":20}}) is None
    assert edap_device.trigger({"power": 7, "sensors": {"active": True, "connector": "con_3", "temp":20}}) is None
    assert edap_device.trigger({"power": 7, "sensors": {"active": True, "connector": "con_2", "temp":20}}) is not None
    assert edap_device.trigger({"power": 10, "sensors": {"active": True, "connector": "con_2", "temp":20}}) is None # Both delta and c1 need to trigger
    assert edap_device.trigger({"power": 10, "sensors": {"active": True, "connector": "con_2", "temp":23}}) is not None
    assert edap_device.trigger({"power": 13, "sensors": {"active": False, "connector": "con_2", "temp":20}}) is None
    assert edap_device.trigger({"power": 13, "sensors": {"active": True, "connector": "con_2", "temp":20}}) is not None
    assert edap_device.trigger({"power": 16, "sensors": {"active": True, "connector": "con_3", "temp":23}}) is None
    assert edap_device.trigger({"power": 16, "sensors": {"active": True, "connector": "con_2", "temp":23}}) is not None
    assert edap_device.trigger({"power": 16, "sensors": {"active": True, "connector": "con_2", "temp":26}}) is None
    assert edap_device.trigger({"power": 13, "sensors": {"active": True, "connector": "con_2", "temp":23}}) is None
    assert edap_device.trigger({"power": 13, "sensors": {"active": True, "connector": "con_2", "temp":26}}) is not None

def test_default_generate_sample():
    edap_device = EdapDevice()
    edap_device.set_triggers([
    {
        "property": "power",
        "delta": 5,
        "id": "time_id"
    }
    ])
    sample_time = datetime.now(timezone.utc)
    triggered_sample = edap_device.trigger({"time": sample_time, "power": 10, "energy": 5})
    triggered_sample = edap_device.trigger({"time": sample_time, "power": 20, "energy": 5})
    assert triggered_sample.get("energy") == 5
    assert triggered_sample.get("power") == 20
    triggered_sample = edap_device.trigger({"time": sample_time + timedelta(minutes=2), "power": 30, "energy": 25})
    assert triggered_sample.get("power") == 30
    assert triggered_sample.get("energy") == 25
    triggered_sample = edap_device.trigger({"time": None, "power": 40, "energy": None})
    assert triggered_sample.get("time") is None
    assert triggered_sample.get("energy") is None
    triggered_sample = edap_device.trigger({"time": sample_time + timedelta(minutes=4), "power": 50, "energy": 40})
    assert triggered_sample.get("time") == sample_time + timedelta(minutes=4)
    assert triggered_sample.get("power") == 50
    triggered_sample = edap_device.trigger({"time": sample_time + timedelta(minutes=5), "power": 60, "energy": 60})
    assert triggered_sample.get("power") == 60
    assert triggered_sample.get("energy") == 60

def test_one_level_trigger_triggering_does_not_reset_other_level_triggers() -> None:
    # Arrange
    edap_device = EdapDevice(
        [
            {"property": "power", "delta": 1.0, "id": "delta_1"},
            {"property": "power", "delta": 2.0, "id": "delta_2"},
        ]
    )
    edap_device.trigger({"power": 0.0, "triggers": [], "time": None, "sensors": {}, "energy": None})

    # Act
    sample_1 = edap_device.trigger({"power": 1.1, "triggers": [], "time": None, "sensors": {}, "energy": None})
    sample_2 = edap_device.trigger({"power": 2.2, "triggers": [], "time": None, "sensors": {}, "energy": None})

    # Assert
    assert sample_1 is not None
    assert sample_2 is not None
    assert sample_1["triggers"] == ["delta_1"]
    assert sample_2["triggers"] == ["delta_1", "delta_2"]

def test_level_trigger_is_not_reset_by_other_triggers_triggering() -> None:
    # Arrange
    edap_device = EdapDevice(
        [
            {"property": "power", "delta": 1.0, "id": "delta_1"},
            {"property": "power", "levels": [10.0], "id": "levels_1"},
        ]
    )
    edap_device.trigger({"power": 0.0, "triggers": [], "time": None, "sensors": {}, "energy": None})

    # Act
    sample_1 = edap_device.trigger({"power": 10.0, "triggers": [], "time": None, "sensors": {}, "energy": None})
    sample_2 = edap_device.trigger({"power": 10.1, "triggers": [], "time": None, "sensors": {}, "energy": None})

    # Assert
    assert sample_1 is not None
    assert sample_2 is not None
    assert sample_1["triggers"] == ["delta_1"]
    assert sample_2["triggers"] == ["levels_1"]

def test_level_trigger_triggers_after_initial_value_on_level() -> None:
    # Arrange
    edap_device = EdapDevice(
        [{"property": "power", "levels": [10.0], "id": "levels_1"}]
    )

    # Act
    sample_1 = edap_device.trigger({"power": 10.0, "triggers": [], "time": None, "sensors": {}, "energy": None})
    sample_2 = edap_device.trigger({"power": 11.0, "triggers": [], "time": None, "sensors": {}, "energy": None})
    sample_3 = edap_device.trigger({"power": 9.0, "triggers": [], "time": None, "sensors": {}, "energy": None})

    # Assert
    assert sample_1 is None
    assert sample_2 is not None
    assert sample_3 is not None

def test_apply_trigger_no_instance_needed() -> None:
    # apply_trigger is a static method — callable without an EdapDevice instance
    triggers = [{"property": "power", "delta": 2, "value": 20, "id": "power_id"}]
    result = EdapDevice.apply_trigger({"power": 23}, triggers)
    assert result is not None
    assert result["triggers"] == ["power_id"]


def test_apply_trigger_returns_none_when_no_triggers_fire() -> None:
    triggers = [{"property": "power", "delta": 2, "value": 20, "id": "power_id"}]
    assert EdapDevice.apply_trigger({"power": 21}, triggers) is None


def test_apply_trigger_returns_none_for_empty_triggers() -> None:
    assert EdapDevice.apply_trigger({"power": 100}, []) is None


def test_apply_trigger_result_contains_sample_fields() -> None:
    sample_time = datetime.now(timezone.utc)
    triggers = [{"property": "power", "delta": 2, "value": 20, "id": "power_id"}]
    result = EdapDevice.apply_trigger({"time": sample_time, "power": 25, "energy": 10}, triggers)
    assert result is not None
    assert result["time"] == sample_time
    assert result["power"] == 25
    assert result["energy"] == 10


def test_apply_trigger_is_stateless_between_calls() -> None:
    # apply_trigger builds its own conditions state per call — two calls with
    # identical fresh trigger copies produce identical results
    from copy import deepcopy
    triggers = [{"property": "power", "delta": 2, "value": 20, "id": "power_id"}]
    sample = {"power": 25}
    result_1 = EdapDevice.apply_trigger(sample, deepcopy(triggers))
    result_2 = EdapDevice.apply_trigger(sample, deepcopy(triggers))
    assert result_1 is not None
    assert result_2 is not None
    assert result_1["triggers"] == result_2["triggers"]


def test_apply_trigger_updates_trigger_value_on_activation() -> None:
    triggers = [{"property": "power", "delta": 2, "value": 20, "id": "power_id"}]
    EdapDevice.apply_trigger({"power": 25}, triggers)
    assert triggers[0]["value"] == 25


def test_apply_trigger_does_not_mutate_trigger_value_when_not_activated() -> None:
    triggers = [{"property": "power", "delta": 2, "value": 20, "id": "power_id"}]
    EdapDevice.apply_trigger({"power": 21}, triggers)
    assert triggers[0]["value"] == 20


def test_apply_trigger_discard_sample_prefixes_trigger_id() -> None:
    triggers = [{"property": "power", "delta": 2, "value": 20, "id": "power_id", "discard_sample": True}]
    result = EdapDevice.apply_trigger({"power": 25}, triggers)
    assert result is not None
    assert result["triggers"] == ["#power_id"]


def test_apply_trigger_sensors_populated_by_trigger_without_sensors_list() -> None:
    # A trigger with no 'sensors' key copies all sensors into the result
    triggers = [{"property": "power", "delta": 2, "value": 20, "id": "power_id"}]
    sample = {"power": 25, "sensors": {"temp": 30, "voltage": 400}}
    result = EdapDevice.apply_trigger(sample, triggers)
    assert result is not None
    assert result["sensors"] == {"temp": 30, "voltage": 400}


def test_apply_trigger_sensors_filtered_by_trigger_sensors_list() -> None:
    # A trigger with a 'sensors' list copies only the listed sensors into the result
    triggers = [{"property": "power", "delta": 2, "value": 20, "id": "power_id", "sensors": ["temp"]}]
    sample = {"power": 25, "sensors": {"temp": 30, "voltage": 400}}
    result = EdapDevice.apply_trigger(sample, triggers)
    assert result is not None
    assert result["sensors"] == {"temp": 30}
    assert "voltage" not in result["sensors"]


def test_apply_trigger_condition_triggers() -> None:
    triggers = [
        {"id": "delta_1", "property": "power", "delta": 2, "conditions": ["c1"]},
        {"condition": "c1", "property": "power", "greater": 10, "less": 30},
    ]
    # no prior value and c1 satisfied (10 < 15 < 30) → fires; trigger value updated to 15
    result = EdapDevice.apply_trigger({"power": 15}, triggers)
    assert result is not None
    assert result["triggers"] == ["delta_1"]

    # delta |17-15|=2 not > 2 → doesn't fire
    assert EdapDevice.apply_trigger({"power": 17}, triggers) is None

    # delta |18-15|=3 > 2 and c1 satisfied → fires; trigger value updated to 18
    assert EdapDevice.apply_trigger({"power": 18}, triggers) is not None

    # power=35 fails c1 (35 >= 30) → doesn't fire even though delta would be large enough
    assert EdapDevice.apply_trigger({"power": 35}, triggers) is None


def test_apply_trigger_tolerance_transition() -> None:
    # Tolerance triggers on value↔no-value transition (stateless, checked each call independently)
    triggers = [{"property": "power", "value": 20, "tolerance": 1, "id": "power_id"}]

    # had value, now None → triggers
    result = EdapDevice.apply_trigger({"power": None}, triggers)
    assert result is not None

    # trigger value was updated to None; still None → no trigger
    assert triggers[0]["value"] is None
    result = EdapDevice.apply_trigger({"power": None}, triggers)
    assert result is None

    # was None, now has value → triggers
    result = EdapDevice.apply_trigger({"power": 20}, triggers)
    assert result is not None


@pytest.mark.parametrize("delta_value", [None, 0, 0.1])
def test_delta_trigger_triggers_on_bool_change(delta_value: float | int | None) -> None:
    # Arrange
    edap_device = EdapDevice(
        [{"property": "online", "delta": delta_value, "id": "delta_1"}]
    )
    edap_device.trigger({"power": None, "triggers": [], "time": None, "sensors": {"online": False}, "energy": None})

    # Act
    sample_1 = edap_device.trigger({"power": None, "triggers": [], "time": None, "sensors": {"online": False}, "energy": None})
    sample_2 = edap_device.trigger({"power": None, "triggers": [], "time": None, "sensors": {"online": True}, "energy": None})
    sample_3 = edap_device.trigger({"power": None, "triggers": [], "time": None, "sensors": {"online": False}, "energy": None})

    # Assert
    assert sample_1 is None
    assert sample_2 is not None
    assert sample_3 is not None
