from datetime import datetime, timezone, timedelta
from tests.utils import MockEdapDevice


def test_get_set_triggers():
    edap_device = MockEdapDevice()
    assert len(edap_device.get_triggers()) == 0
    edap_device.set_triggers(None)
    assert len(edap_device.get_triggers()) == 1

def test_single_trigger():
    edap_device = MockEdapDevice()
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

def test_multiple_triggers():
    edap_device = MockEdapDevice()
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
    edap_device = MockEdapDevice()
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
    edap_device = MockEdapDevice()
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
    edap_device = MockEdapDevice()
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
    # number of failures for power is 1
    assert triggered_sample is None

    triggered_sample = edap_device.trigger({"power": None})
    # number of failures for power is 2, tolerance reached, trigger activated
    assert triggered_sample is not None

    triggered_sample = edap_device.trigger({"power": None})
    # number of failures for power is 3, but the value is still None, trigger not activated
    assert triggered_sample is None

    triggered_sample = edap_device.trigger({"power": 21})
    # number of failures for power was 3, but the value is present, trigger activated and count is reset
    assert triggered_sample is not None


def test_level_triggered():
    edap_device = MockEdapDevice()
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
    }
    ])

    # no trigger since we assumt to start at 0
    assert edap_device.trigger({"power": 9}) is None

    # level 10 activated
    assert edap_device.trigger({"power": 11}) is not None

    # no level passed
    assert edap_device.trigger({"power": 14}) is None

    # level 15 passed
    assert edap_device.trigger({"power": 18}) is not None

def test_default_generate_sample():
    edap_device = MockEdapDevice()
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
    assert triggered_sample.get("duration") == 0
    assert triggered_sample.get("sample_energy") == 0
    triggered_sample = edap_device.trigger({"time": sample_time + timedelta(minutes=2), "power": 30, "energy": 25})
    assert triggered_sample.get("duration") == 120.0
    assert triggered_sample.get("sample_energy") == 20
    triggered_sample = edap_device.trigger({"time": None, "power": 40, "energy": None})
    assert triggered_sample.get("duration") is None
    assert triggered_sample.get("sample_energy") is None
    triggered_sample = edap_device.trigger({"time": sample_time + timedelta(minutes=4), "power": 50, "energy": 40})
    assert triggered_sample.get("duration") is None
    assert triggered_sample.get("sample_energy") is None
    triggered_sample = edap_device.trigger({"time": sample_time + timedelta(minutes=5), "power": 60, "energy": 60})
    assert triggered_sample.get("duration") == 60
    assert triggered_sample.get("sample_energy") == 20.0
    triggered_sample = edap_device.trigger({"time": sample_time + timedelta(minutes=6), "power": 40, "energy": 70, "sample_energy": 3.5, "duration": 4})
    assert triggered_sample.get("duration") == 4
    assert triggered_sample.get("sample_energy") == 3.5
