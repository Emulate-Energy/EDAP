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
    edap_device.set_triggers([
    {
        "property": "time",
        "delta": 60,
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
    triggered_sample = edap_device.trigger({"time": datetime.now(timezone.utc) - timedelta(minutes=2), "power": 23})
    assert triggered_sample is not None
    assert triggered_sample.get("triggers")[0] == "power_id"


    # since time of the last sample was 2 minutes ago, and delta of the time trigger is defined as 60 seconds,
    # this sample should trigger the time_id trigger
    triggered_sample = edap_device.trigger({"time": datetime.now(timezone.utc), "power": 20})
    assert triggered_sample is not None
    assert triggered_sample.get("triggers")[0] == "time_id"

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
