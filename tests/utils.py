from datetime import datetime, timezone
from edap import EdapDevice, EdapSample


class MockEdapDevice(EdapDevice):
    def unused_generate_sample(self, sample: EdapSample) -> EdapSample:
        time = sample.get('time') or datetime.now(timezone.utc)

        return {
            "time": time,
            "power": sample.get("power"),
            "energy": sample.get("energy"),
            "triggers": [],
            "sensors": {}
        }
