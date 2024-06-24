# Dummy implementations
These files do not reflect any real hardware, but just produce some mocked data.
In a real implementation the `DeviceConnection` implementation should do things like for example read values from ModBus registers, or get data from an internal api, or whatever is needed.

The real EdapDevice implementation should similarly keep whatever state variables necessary, and add the logic to construct appropriate Edap samples (i.e. a battery should fill in the state of charge (soc), while an HVAC system should fill in temperature data, and so on.).

