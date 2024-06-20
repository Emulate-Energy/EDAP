"""Dummy implementation of an EDAP device."""
import logging
from datetime import datetime, timezone
from edap import EdapDevice, EdapSample, Trigger


class DummyEdapBattery(EdapDevice):
    """Dummy implementation of an EDAP device."""
    power_kw: float = 0.0
    soc: float = 0.50
    energy_capacity = 100.0 # kWh
    energy: float = 0.0
    last_sample_time: datetime # when the last device sample received
    last_triggered: datetime  # when the last trigger was activated

    def __init__(self, mediator):
        self.mediator = mediator
        self.last_sample_time = None
        self.last_triggered = None

        # add a default time trigger just for testing
        default_time_trigger: Trigger = Trigger(
            id="time",
            property="time",
            delta=10
        )
        super().__init__([default_time_trigger])

    def update_from_sample(self, data: dict):
        """Update the device state from a polling sample, and check if any triggers are activated,
        notifying the mediator if so."""
        logging.debug({"message": "Updating device from sample", "data": data})
        self.power_kw = data["power"]
        self.soc = data["soc"]

        now = datetime.now(tz=timezone.utc)
        if self.last_sample_time:
            since_last_sample = now - self.last_sample_time
            self.energy += self.power_kw * since_last_sample.total_seconds() / 3600

        self.last_sample_time = now

        sample = EdapSample(
            triggers = [],
            time = now,
            power = 0.0,
            energy = 0.0,
            duration = 0.0,
            sensors = {},
            sample_energy = 0.0,
        )

        maybe_sample = self.trigger(sample)
        if maybe_sample is not None:
            self.last_triggered = now
            self.mediator.notify("trigger_activated", maybe_sample)

    def generate_sample(self, sample: EdapSample) -> dict:
        sample["power"] = self.power_kw
        sample["sensors"]["soc"] = self.soc
        sample["energy"] = self.energy
        sample["sensors"]["remaining_energy"] = self.soc * self.energy_capacity

        if self.last_triggered:
            now = datetime.now(tz=timezone.utc)
            sample["duration"] = (now - self.last_triggered).total_seconds()

        return sample
