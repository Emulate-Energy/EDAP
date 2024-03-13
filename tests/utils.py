from datetime import datetime, timezone
from edap import EdapDevice, EdapSample


class MockEdapDevice(EdapDevice):
    def generate_sample(self, sample: EdapSample) -> EdapSample:
        time = sample.get('time') or datetime.now(timezone.utc)
        last_time = self._last_sample.get('time')
        last_energy = self._last_sample.get('energy') or 0
        sample_energy = sample.get('energy')

        return {
            "time": time,
            "power": sample.get("power"),
            "energy": sample.get("energy"),
            "sample_energy": None if sample_energy is None else sample_energy - last_energy,
            "duration": (time - last_time).total_seconds(),
            "triggers": [],
            "sensors": {}
        }