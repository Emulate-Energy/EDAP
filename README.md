<img src="https://github.com/Emulate-Energy/EDAP/blob/main/EDAP_logo.svg?raw=true" alt="EDAP" width="400"/>
<hr/>
EDAP (Energy Device Aggregation Protocol) is a standard developed by Emulate Energy to efficiently control and access energy devices over the cloud with low-latency.

## Usage
The primary way to use this is to implement a concrete subclass of the `EdapDevice` class, which means to implement the logic for generating an EDAP sample; as well as other required methods for logic that is specific to the particular device you want to represent.
This library should give you all the logic regarding triggers that EDAP requires.

In the `examples/basic-edap-gateway` there is a minimal implementation of a EDAP gateway, which can be useful to get an idea of how this can be used in practice.

## Installation
Can be installed as a python package with `pip` via
```bash
pip install git+https://github.com/Emulate-Energy/EDAP@main
```
and can be added as a dependency by adding
```
edap @ git+https://github.com/Emulate-Energy/EDAP@main
```
to a `requirements.txt` file.
