# Traffic Management Components Architecture

**Date:** February 11, 2026  
**Status:** Design Document  
**Related:** [Technical Brief: Automated QoE Verification](./Technical%20Brief_%20Automated%20QoE%20Verification.md)

---

## 1. Overview

This document defines the Boardfarm architecture for Traffic Control (network impairment) components. The design follows existing Boardfarm patterns and adheres to the **DRY (Don't Repeat Yourself)** principle. Test cases remain portable across **Functional** (physical DUT + containerized surroundings) and **Pre-Production** (physical hardware) testbeds.

### Key Design Principles

1. **Test Portability**: Use cases depend on the `TrafficController` template interface only—they never call Linux `tc` or Spirent APIs directly.
2. **Per-Device Defaults in Env Config**: Each TrafficController device has an `impairment_profile` defined in the **environment config** (`environment_def`)—the default applied at testbed initialization. Named presets (cable_typical, satellite, etc.) are also defined in env config for BDD vocabulary.
3. **Parameter-Based API**: `set_impairment_profile(profile)` and `get_impairment_profile()` work with parameter objects, not profile names.
4. **Topology Flexibility**: The number of WAN links (1, 2, 3, or more) is driven by the testbed inventory—never hardcoded in lib.

---

## 2. Architecture Layers

| Layer           | Purpose                                              | Location                                     |
| --------------- | ---------------------------------------------------- | -------------------------------------------- |
| **Template**    | Defines the contract (abstract interface)             | `boardfarm3/templates/traffic_controller.py` |
| **Env Config**  | Per-device `impairment_profile`, named presets       | Boardfarm env JSON (`environment_def`)      |
| **Inventory**   | Device identity, connection details, `impairment_interface` | Boardfarm inventory JSON                 |
| **Lib**         | ImpairmentProfile schema, tc helpers, adapter        | `boardfarm3/lib/traffic_control.py`          |
| **Devices**     | Concrete implementations (Linux, Spirent)             | `boardfarm3/devices/`                        |
| **Use Cases**   | Test operations, `get_traffic_controller()`           | `boardfarm3/use_cases/traffic_control.py`    |

---

## 3. Template: TrafficController

**Location:** `boardfarm3/templates/traffic_controller.py`

Defines the abstract interface. Methods are parameter-based: they accept and return `ImpairmentProfile` objects.

```python
from abc import ABC, abstractmethod

class TrafficController(ABC):
    """Template for network impairment / traffic control implementations."""

    @abstractmethod
    def set_impairment_profile(self, profile: ImpairmentProfile | dict) -> None:
        """Apply impairment parameters. Used at init (from config) and at runtime.
        :param profile: ImpairmentProfile or dict with latency_ms, jitter_ms, loss_percent, bandwidth_mbps
        """
        raise NotImplementedError

    @abstractmethod
    def get_impairment_profile(self) -> ImpairmentProfile:
        """Return current impairment parameters."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Remove all impairments (set to pristine/zero)."""
        raise NotImplementedError

    @abstractmethod
    def inject_transient(
        self, event: str, duration_ms: int, **kwargs
    ) -> None:
        """Inject transient event: blackout, brownout, latency_spike, packet_storm."""
        raise NotImplementedError
```

---

## 4. Configuration: Inventory + Env Config

Per-device settings are split between **inventory** (connection/topology) and **env config** (impairment defaults and presets). Boardfarm merges them via `parse_boardfarm_config()`.

### 4.1 Inventory (Device Identity and Connection)

**Location:** Boardfarm inventory config (e.g., `boardfarm_config.json`)

```json
"wan1_impairment": {
  "type": "bf_traffic_controller",
  "name": "wan1_impairment",
  "impairment_interface": "eth1",
  "connection_type": "authenticated_ssh",
  "ipaddr": "localhost",
  "port": 4010
}
```

- **impairment_interface**: Interface to apply tc/netem on (Linux implementation).

### 4.2 Env Config (Per-Device Defaults and Named Presets)

**Location:** Boardfarm env config (e.g., `boardfarm_env.json`)

```json
{
  "environment_def": {
    "wan1_impairment": {
      "impairment_profile": {
        "latency_ms": 5,
        "jitter_ms": 1,
        "loss_percent": 0,
        "bandwidth_mbps": 1000
      }
    },
    "impairment_presets": {
      "pristine": { "latency_ms": 5, "jitter_ms": 1, "loss_percent": 0, "bandwidth_mbps": 1000 },
      "cable_typical": { "latency_ms": 15, "jitter_ms": 5, "loss_percent": 0.1, "bandwidth_mbps": 100 },
      "satellite": { "latency_ms": 600, "jitter_ms": 50, "loss_percent": 2, "bandwidth_mbps": 10 }
    }
  }
}
```

- **environment_def[device_name].impairment_profile**: Default parameters for that device. Merged into device config and applied at init.
- **environment_def.impairment_presets**: Optional named presets for BDD steps (e.g. "Given the network is set to cable_typical"). Steps resolve preset names from the merged config.

### 4.3 Initialization Flow

1. Device boots and connects.
2. Merged config (inventory + env) provides `impairment_profile` for the device.
3. `set_impairment_profile(config["impairment_profile"])` is called at init.
4. The link starts in the configured state.

### 4.4 Runtime Changes

During tests, `set_impairment_profile(profile)` can be called again with new parameters—either from a preset name (resolved via env config) or explicit dict.

---

## 5. Device Getter and BDD Steps

### 5.1 get_traffic_controller(name=None)

**Location:** `boardfarm3/use_cases/traffic_control.py` or `boardfarm3/use_cases/device_getters.py`

Consistent with `get_lan_clients`, `get_wan_clients`. Supports single-WAN (omit name) and multi-path (specify device name).

```python
from boardfarm3.exceptions import DeviceNotFound
from boardfarm3.lib.device_manager import get_device_manager
from boardfarm3.templates.traffic_controller import TrafficController

def get_traffic_controller(name: str | None = None) -> TrafficController:
    """Return TrafficController device(s).

    :param name: Device name (e.g. wan1_impairment). If None and exactly one
        TrafficController exists, return it. If None and multiple exist, raise.
    :return: TrafficController instance
    :raises DeviceNotFound: if no TrafficController available
    :raises ValueError: if name is None and more than one TrafficController exists
    """
    devs = get_device_manager().get_devices_by_type(TrafficController)
    if not devs:
        raise DeviceNotFound("No TrafficController devices available")
    if name is not None:
        if name not in devs:
            raise DeviceNotFound(f"TrafficController {name!r} not found")
        return devs[name]
    if len(devs) > 1:
        raise ValueError(
            f"Multiple TrafficController devices found ({list(devs)}). "
            "Specify name= to select one."
        )
    return next(iter(devs.values()))
```

### 5.2 BDD Steps: Single Link vs All Links

Steps can target a **single link** (by device name) or **all links**:

| Step variant | Target | Use case |
|--------------|--------|----------|
| `Given the network is set to "cable_typical"` | Single link (the only one, or first) | Single-WAN testbed |
| `Given the "wan1_impairment" network is set to "cable_typical"` | Named link | Multi-WAN: specific link |
| `Given all networks are set to "cable_typical"` | All TrafficController devices | Multi-WAN: apply to all |

### 5.3 Preset Resolution from Env Config

Presets are loaded from the merged Boardfarm config (env config's `environment_def.impairment_presets`). The BDD context or fixture provides access to the config.

```python
def _get_preset_from_config(config: BoardfarmConfig, preset_name: str) -> dict:
    """Resolve preset name from env config."""
    presets = config.env_config.get("environment_def", {}).get("impairment_presets", {})
    if preset_name not in presets:
        raise KeyError(f"Preset {preset_name!r} not in environment_def.impairment_presets")
    return presets[preset_name]
```

### 5.4 BDD Step Examples

**Single link (single-WAN or default):**

```gherkin
Given the network is set to "cable_typical"
```

```python
@given('the network is set to "{preset_name}"')
def given_network_preset(bf_context, preset_name: str):
    preset = _get_preset_from_config(bf_context.config, preset_name)
    controller = get_traffic_controller()
    set_impairment_profile(controller, preset)
```

**Named link (multi-WAN):**

```gherkin
Given the "wan1_impairment" network is set to "satellite"
```

```python
@given('the "{link_name}" network is set to "{preset_name}"')
def given_link_network_preset(bf_context, link_name: str, preset_name: str):
    preset = _get_preset_from_config(bf_context.config, preset_name)
    controller = get_traffic_controller(name=link_name)
    set_impairment_profile(controller, preset)
```

**All links:**

```gherkin
Given all networks are set to "cable_typical"
```

```python
@given('all networks are set to "{preset_name}"')
def given_all_networks_preset(bf_context, preset_name: str):
    preset = _get_preset_from_config(bf_context.config, preset_name)
    for controller in get_device_manager().get_devices_by_type(TrafficController).values():
        set_impairment_profile(controller, preset)
```

---

## 6. Lib: traffic_control.py

**Location:** `boardfarm3/lib/traffic_control.py`

Contains:
- **ImpairmentProfile schema** (dataclass)
- **Parsing** (dict → ImpairmentProfile)
- **Linux tc helper functions** (console-agnostic)
- **LinuxTrafficControlAdapter** (for internal composition)

### 6.1 ImpairmentProfile Schema

```python
from dataclasses import dataclass

@dataclass
class ImpairmentProfile:
    """Parameters for network impairment."""
    latency_ms: int
    jitter_ms: int
    loss_percent: float
    bandwidth_mbps: int | None  # None or 0 = no limit / variable

def profile_from_dict(data: dict) -> ImpairmentProfile:
    """Parse dict to ImpairmentProfile."""
    return ImpairmentProfile(
        latency_ms=data["latency_ms"],
        jitter_ms=data["jitter_ms"],
        loss_percent=data["loss_percent"],
        bandwidth_mbps=data.get("bandwidth_mbps") or 0,
    )
```

### 6.2 Linux tc Helper Functions

```python
def set_profile_via_tc(
    console: _LinuxConsole,
    interface: str,
    profile: ImpairmentProfile,
) -> None:
    """Build and execute tc qdisc/netem commands."""
    ...

def clear_tc_impairment(console: _LinuxConsole, interface: str) -> None:
    """Remove netem qdisc from interface."""
    ...
```

### 6.3 LinuxTrafficControlAdapter

Used when impairment is **internal** to another device (e.g., ISP Router runs tc on itself).

```python
class LinuxTrafficControlAdapter(TrafficController):
    def __init__(self, console: _LinuxConsole, interface: str) -> None:
        self._console = console
        self._interface = interface
        self._current: ImpairmentProfile | None = None

    def set_impairment_profile(self, profile: ImpairmentProfile | dict) -> None:
        p = profile_from_dict(profile) if isinstance(profile, dict) else profile
        set_profile_via_tc(self._console, self._interface, p)
        self._current = p

    def get_impairment_profile(self) -> ImpairmentProfile:
        return self._current or ImpairmentProfile(0, 0, 0.0, None)

    def clear(self) -> None:
        clear_tc_impairment(self._console, self._interface)
        self._current = None
    ...
```

---

## 7. Device Implementations

### 7.1 LinuxTrafficController (Standalone Device)

```python
class LinuxTrafficController(LinuxDevice, TrafficController):
    def __init__(self, config: dict, cmdline_args: Namespace) -> None:
        super().__init__(config, cmdline_args)
        self._interface = config.get("impairment_interface", "eth1")
        # Apply default from config at init
        if profile_data := config.get("impairment_profile"):
            self.set_impairment_profile(profile_data)

    def set_impairment_profile(self, profile: ImpairmentProfile | dict) -> None:
        p = profile_from_dict(profile) if isinstance(profile, dict) else profile
        set_profile_via_tc(self._console, self._interface, p)

    def get_impairment_profile(self) -> ImpairmentProfile:
        ...

    def clear(self) -> None:
        clear_tc_impairment(self._console, self._interface)
```

### 7.2 SpirentTrafficController (Hardware Appliance)

```python
class SpirentTrafficController(BoardfarmDevice, TrafficController):
    def __init__(self, config: dict, cmdline_args: Namespace) -> None:
        super().__init__(config, cmdline_args)
        if profile_data := config.get("impairment_profile"):
            self.set_impairment_profile(profile_data)

    def set_impairment_profile(self, profile: ImpairmentProfile | dict) -> None:
        p = profile_from_dict(profile) if isinstance(profile, dict) else profile
        self._api.apply_impairment(p)

    def get_impairment_profile(self) -> ImpairmentProfile:
        ...

    def clear(self) -> None:
        self._api.clear_impairment()
```

---

## 8. Composition: Internal vs External Impairment

### 8.1 Internal (Functional Testbed)

Router composes `LinuxTrafficControlAdapter` using its own console. At init, applies its `impairment_profile` from config if present.

```python
class LinuxISPGateway(LinuxDevice, WAN, ...):
    @property
    def impairment(self) -> TrafficController:
        if self._impairment_device_name:
            return get_device_manager().get_devices_by_type(
                TrafficController
            )[self._impairment_device_name]
        adapter = LinuxTrafficControlAdapter(self._console, self.iface_dut)
        if profile_data := self._config.get("impairment_profile"):
            adapter.set_impairment_profile(profile_data)
        return adapter
```

### 8.2 External (Pre-Production Testbed)

Impairment handled by a separate device. Config specifies `impairment_device`; router resolves via DeviceManager.

---

## 9. Use Cases

**Location:** `boardfarm3/use_cases/traffic_control.py`

```python
def set_impairment_profile(
    controller: TrafficController,
    profile: ImpairmentProfile | dict,
) -> None:
    """Apply impairment parameters. Profile can come from env config preset or explicit dict."""
    controller.set_impairment_profile(profile)


def get_impairment_profile(controller: TrafficController) -> ImpairmentProfile:
    """Return current impairment parameters."""
    return controller.get_impairment_profile()


def clear_impairment(controller: TrafficController) -> None:
    """Remove all impairments."""
    controller.clear()


def inject_blackout(controller: TrafficController, duration_ms: int) -> None:
    """Inject complete link failure."""
    controller.inject_transient("blackout", duration_ms)
```

---

## 10. Multi-Path Topologies

The number of WAN links is **config-driven**—never hardcoded.

- **Single WAN**: One `TrafficController` device. Use `get_traffic_controller()` (no name).
- **Dual WAN**: Two devices (e.g., `wan1_impairment`, `wan2_impairment`). Use `get_traffic_controller(name="wan1_impairment")` or target all via `get_devices_by_type(TrafficController)`.
- **Triple WAN**: Three devices (e.g., `wan1_impairment`, `wan2_impairment`, `lte_impairment`).

**BDD step targeting:**
- **Single link**: `Given the "wan1_impairment" network is set to "cable_typical"` — applies to that link only.
- **All links**: `Given all networks are set to "cable_typical"` — applies to every TrafficController.

Each device has its own `impairment_profile` default in env config (`environment_def[device_name]`).

---

## 11. Component Summary

| Component | Type | Location | Purpose |
|-----------|------|----------|---------|
| `TrafficController` | Template (ABC) | `templates/traffic_controller.py` | Abstract interface |
| `impairment_profile` | Env config | `environment_def[device_name]` | Per-device default (4 params) |
| `impairment_presets` | Env config | `environment_def.impairment_presets` | Named presets for BDD steps |
| `ImpairmentProfile`, `profile_from_dict` | Lib | `lib/traffic_control.py` | Schema and parsing |
| `set_profile_via_tc`, `clear_tc_impairment` | Lib | `lib/traffic_control.py` | tc helpers |
| `LinuxTrafficControlAdapter` | Lib | `lib/traffic_control.py` | Internal composition |
| `LinuxTrafficController` | Device | `devices/linux_traffic_controller.py` | Standalone Linux tc |
| `SpirentTrafficController` | Device | `devices/spirent_traffic_controller.py` | Hardware appliance |
| `get_traffic_controller` | Use case | `use_cases/traffic_control.py` or `device_getters.py` | Device selection (single/multi-path) |
| `set_impairment_profile`, `get_impairment_profile`, `clear_impairment` | Use cases | `use_cases/traffic_control.py` | BDD / test operations |
