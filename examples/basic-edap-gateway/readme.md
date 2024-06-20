# Basic EDAP gateway implementation

This is meant to be a barebones implementation of an EDAP gateway.
We assume that it connects to a single device, and that we can control the power of that device, as well as read certain values from it.

The specific implementation of the connection to the device will depend on the actual hardware.
The application currenty starts with a `DummyDeviceConnection`, which just returns some dummy values, and has a `DummyEdapBattery` device, which mimics a basic battery. Both these classes needs real implementations, depending on the particular device and gateway setup.


## Running it
You can either create a virtual python environment, activate it and then run `make deps`, and then `python main.py` to start it, or you can build and run the application as a Docker container.
The application depends on a few environment variables being set, namely the URL to the Emulate Commander Proxy service, and the device id of the device as it exists in the Emulate system (an uuid).

In the makefile, the `run-linux-container-local` is an example setup for running the gateway against the local Emulate development environment.

