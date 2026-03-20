# Traffic Management Components Architecture

**Date:** March 2026  
**Status:** Design Document  

---

## 1. Overview

This document defines the Boardfarm architecture for Traffic Control (network impairment) components. The design follows existing Boardfarm patterns and adheres to the **DRY (Don't Repeat Yourself)** principle. Test cases remain portable across **Functional** (physical DUT + containerized surroundings) and **Pre-Production** (physical hardware) testbeds.

### Key Design Principles

1. **Test Portability**: Use cases depend on the `TrafficController` template interface only — they never call Linux `tc` or Spirent APIs directly.
2. **One Profile per Interface**: `ImpairmentProfile` describes impairment for **one kernel interface**. Asymmetry between directions is expressed by assigning *different* profiles to *different* interfaces — not by direction-specific fields within a single profile.
3. **Interfaces Dict in Env Config**: Each `LinuxTrafficController` device declares its interfaces as a named dict in `environment_def[device_name].interfaces`. Each entry maps a kernel interface name to its initial `ImpairmentProfile`. Interface names are topology-neutral (they are kernel names, not logical roles like "north" or "dut").
4. **Parameter-Based API**: All template methods accept and return `ImpairmentProfile` objects or plain dicts.
5. **Topology Flexibility**: The number of WAN links and the number of interfaces per TC are config-driven — never hardcoded.

---

## 2. Architecture Layers

| Layer           | Purpose                                              | Location                                     |
| --------------- | ---------------------------------------------------- | -------------------------------------------- |
| **Template**    | Defines the contract (abstract interface)             | `boardfarm3/templates/traffic_controller.py` |
| **Env Config**  | Per-device `interfaces` dict with initial profiles; named presets | Boardfarm env JSON (`environment_def`) |
| **Inventory**   | Device identity, connection details, topology        | Boardfarm inventory JSON                     |
| **Lib**         | ImpairmentProfile schema, per-interface tc helpers   | `boardfarm3/lib/traffic_control.py`          |
| **Devices**     | Concrete implementations (Linux, Spirent)             | `boardfarm3/devices/`                        |
| **Use Cases**   | Test operations, `get_traffic_controller()`           | `boardfarm3/use_cases/traffic_control.py`    |

---

## 3. Template: TrafficController

**Location:** `boardfarm3/templates/traffic_controller.py`

Defines the abstract interface. Methods are split into **symmetric** (all interfaces) and **per-interface** operations.

```python
from abc import ABC, abstractmethod

class TrafficController(ABC):
    """Abstract interface for network impairment / traffic control implementations.

    Multi-interface design:
    - One ImpairmentProfile per kernel interface.
    - Asymmetry across a link is expressed by different profiles on different interfaces.
    """

    # --- Symmetric operations (all interfaces at once) ---

    @abstractmethod
    def set_impairment_profile(self, profile: ImpairmentProfile | dict) -> None:
        """Apply profile to ALL configured interfaces (sustained — no auto-restore)."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Remove all impairments from ALL interfaces."""
        raise NotImplementedError

    @abstractmethod
    def inject_transient(self, event: str, duration_ms: int, **kwargs) -> None:
        """Inject a timed transient on ALL interfaces; auto-restores after duration_ms."""
        raise NotImplementedError

    # --- Per-interface operations ---

    @abstractmethod
    def set_interface_profile(self, interface: str, profile: ImpairmentProfile | dict) -> None:
        """Apply profile to a single named interface (sustained — no auto-restore)."""
        raise NotImplementedError

    @abstractmethod
    def get_interface_profile(self, interface: str) -> ImpairmentProfile:
        """Read current profile for a single interface from device/kernel (no cache)."""
        raise NotImplementedError

    @abstractmethod
    def get_interface_profiles(self) -> dict[str, ImpairmentProfile]:
        """Read current profiles for ALL configured interfaces (no cache).

        Returns {interface_name: ImpairmentProfile} for every configured interface.
        """
        raise NotImplementedError
```

---

## 4. Configuration: Inventory + Env Config

Per-device settings are split between **inventory** (connection/topology) and **env config** (impairment defaults and presets). Boardfarm merges them via `parse_boardfarm_config()`.

### 4.1 Inventory (Device Identity and Connection)

**Location:** Boardfarm inventory config (e.g., `bf_config_sdwan.json`)

```json
{
  "name": "wan1_tc",
  "type": "linux_traffic_controller",
  "connection_type": "authenticated_ssh",
  "ipaddr": "localhost",
  "port": 5001,
  "username": "root",
  "password": "boardfarm"
}
```

### 4.2 Env Config (Per-Device Interfaces and Named Presets)

**Location:** Boardfarm env config (e.g., `bf_env_sdwan.json`)

Each `LinuxTrafficController` device declares an `interfaces` dict mapping kernel interface names to their initial `ImpairmentProfile`. The interface names are what the kernel sees — they reflect the topology without encoding logical roles like "north" or "dut".

```json
{
  "environment_def": {
    "wan1_tc": {
      "interfaces": {
        "eth-north": {"latency_ms": 5, "jitter_ms": 1, "loss_percent": 0, "bandwidth_limit_mbps": 1000},
        "eth-dut":   {"latency_ms": 5, "jitter_ms": 1, "loss_percent": 0, "bandwidth_limit_mbps": 1000}
      }
    },
    "wan2_tc": {
      "interfaces": {
        "eth-north": {"latency_ms": 5, "jitter_ms": 1, "loss_percent": 0, "bandwidth_limit_mbps": 1000},
        "eth-dut":   {"latency_ms": 5, "jitter_ms": 1, "loss_percent": 0, "bandwidth_limit_mbps": 1000}
      }
    },
    "impairment_presets": {
      "pristine":      {"latency_ms": 5,   "jitter_ms": 1,  "loss_percent": 0,   "bandwidth_limit_mbps": 1000},
      "cable_typical": {"latency_ms": 15,  "jitter_ms": 5,  "loss_percent": 0.1, "bandwidth_limit_mbps": 100},
      "4g_mobile":     {"latency_ms": 80,  "jitter_ms": 30, "loss_percent": 1,   "bandwidth_limit_mbps": 20},
      "satellite":     {"latency_ms": 600, "jitter_ms": 50, "loss_percent": 2,   "bandwidth_limit_mbps": 10},
      "congested":     {"latency_ms": 25,  "jitter_ms": 40, "loss_percent": 3,   "bandwidth_limit_mbps": null}
    }
  }
}
```

**Key fields:**

- `environment_def[device_name].interfaces` — **required**. Dict mapping kernel interface name → initial `ImpairmentProfile` dict. Applied at device boot.
- `environment_def.impairment_presets` — named presets for BDD step vocabulary (e.g. `"cable_typical"`). Resolved at runtime via `_get_preset_from_config()`.

### 4.3 Initialization Flow

1. Device boots and connects via SSH.
2. Merged config (inventory + env) provides the `interfaces` dict.
3. `LinuxTrafficController` reads `config["interfaces"]`, derives `self._interfaces` (list of kernel names), and stores initial profile dicts.
4. `_apply_default_profiles()` is called: for each interface, the initial profile dict is parsed and applied via `apply_tc_profile()`.
5. All interfaces start in their configured baseline state.

### 4.4 Asymmetric Impairment

Since each interface has its own `ImpairmentProfile`, asymmetry across a link is expressed directly:

```python
# Different bandwidth upstream vs. downstream
set_interface_profile(tc, "eth-north", ImpairmentProfile(latency_ms=20, jitter_ms=5,
                                                          loss_percent=0.1, bandwidth_limit_mbps=100))
set_interface_profile(tc, "eth-dut",   ImpairmentProfile(latency_ms=20, jitter_ms=5,
                                                          loss_percent=0.1, bandwidth_limit_mbps=50))
```

`tc netem` operates on egress only. A dual-homed TC with two interfaces connected to opposite sides of a WAN link provides full asymmetric control in both directions without IFB (Intermediate Functional Block).

### 4.5 Runtime Changes

During tests, `set_impairment_profile(profile)` applies the same profile to all interfaces (symmetric), while `set_interface_profile(interface, profile)` targets a specific interface. Named presets are symmetric (applied via `set_impairment_profile`).

> **Teardown requirement:** Before calling `set_impairment_profile()` or `set_interface_profile()` in a test step, the step (or its use-case helper) should save the current profiles to `bf_context`. The `reset_sdwan_testbed_after_scenario` autouse fixture in `tests/conftest.py` reads this registry and restores all modified profiles after each scenario. See `WAN_Edge_Appliance_testing.md §3.9` for the full teardown strategy.
>
> `inject_transient()` does **not** require manual teardown — it auto-restores all interfaces to their previous kernel state after `duration_ms` via a background daemon thread (see §7.3).

---

## 5. Device Getter and BDD Steps

### 5.1 get_traffic_controller(name=None)

**Location:** `boardfarm3/use_cases/traffic_control.py`

```python
def get_traffic_controller(name: str | None = None) -> TrafficController:
    """Return TrafficController device.

    :param name: Device name (e.g. 'wan1_tc'). If None and exactly one
        TrafficController exists, return it. If None and multiple exist, raise.
    :return: TrafficController instance
    :raises DeviceNotFound: if no TrafficController available or name not found
    :raises ValueError: if name is None and more than one TrafficController exists
    """
    devs = get_device_manager().get_devices_by_type(TrafficController)
    if not devs:
        raise DeviceNotFound("No TrafficController devices available")
    if name is not None:
        if name not in devs:
            raise DeviceNotFound(f"TrafficController {name!r} not found. Available: {list(devs)}")
        return devs[name]
    if len(devs) > 1:
        raise ValueError(f"Multiple TrafficController devices ({list(devs)}). Specify name=.")
    return next(iter(devs.values()))
```

### 5.2 BDD Steps: Single Link vs All Links

| Step variant | Target | Use case |
|---|---|---|
| `Given the network is set to "cable_typical"` | Single link (only one TC) | Single-WAN testbed |
| `Given the "wan1_tc" network is set to "cable_typical"` | Named TC device | Multi-WAN: specific link |
| `Given all networks are set to "cable_typical"` | All TrafficController devices | Multi-WAN: apply to all |

### 5.3 Preset Resolution from Env Config

```python
def _get_preset_from_config(config: BoardfarmConfig, preset_name: str) -> dict:
    """Resolve preset name from environment_def.impairment_presets."""
    presets = config.env_config.get("environment_def", {}).get("impairment_presets", {})
    if preset_name not in presets:
        raise KeyError(f"Preset {preset_name!r} not in impairment_presets. Available: {list(presets)}")
    return presets[preset_name]
```

### 5.4 BDD Step Examples

**Apply preset (all interfaces of a named TC):**

```gherkin
Given the "wan1_tc" network is set to "satellite"
```

```python
@given('the "{link_name}" network is set to "{preset_name}"')
def given_link_network_preset(bf_context, link_name: str, preset_name: str):
    controller = get_traffic_controller(name=link_name)
    apply_preset(controller, preset_name, bf_context.config)
```

**Per-interface asymmetric impairment:**

```gherkin
Given "wan1_tc" has 100 Mbps upstream and 50 Mbps downstream
```

```python
@given('"{tc_name}" has {up_mbps:d} Mbps upstream and {down_mbps:d} Mbps downstream')
def given_asymmetric_bw(bf_context, tc_name, up_mbps, down_mbps):
    controller = get_traffic_controller(name=tc_name)
    set_interface_profile(controller, "eth-north",
                          ImpairmentProfile(latency_ms=5, jitter_ms=1,
                                            loss_percent=0, bandwidth_limit_mbps=up_mbps))
    set_interface_profile(controller, "eth-dut",
                          ImpairmentProfile(latency_ms=5, jitter_ms=1,
                                            loss_percent=0, bandwidth_limit_mbps=down_mbps))
```

---

## 6. Lib: traffic_control.py

**Location:** `boardfarm3/lib/traffic_control.py`

Contains:
- **`ImpairmentProfile` schema** (dataclass)
- **`profile_from_dict`** — dict → ImpairmentProfile
- **Per-interface tc helper functions** (console-agnostic)

### 6.1 ImpairmentProfile Schema

One `ImpairmentProfile` describes impairment for **one kernel interface**. There are no per-direction overrides — asymmetry is expressed by using different `ImpairmentProfile` objects for different interfaces.

```python
from dataclasses import dataclass

@dataclass
class ImpairmentProfile:
    """Parameters for network impairment applied via tc netem on a single interface."""

    latency_ms: int          # One-way delay (ms)
    jitter_ms: int           # Per-packet delay variation (±ms, normal distribution)
    loss_percent: float      # Packet loss fraction (0.0 – 100.0)
    bandwidth_limit_mbps: int | None   # Bandwidth cap. None = no cap (no TBF qdisc)

    reorder_percent: float = 0.0    # Fraction of packets to reorder (%)
    corrupt_percent: float = 0.0    # Fraction of packets to corrupt (%)
    duplicate_percent: float = 0.0  # Fraction of packets to duplicate (%)
```

### 6.2 Linux tc Helper Functions

```python
def apply_tc_profile(console, iface: str, profile: ImpairmentProfile) -> None:
    """Apply profile to a single interface via tc netem (+ optional TBF for bandwidth)."""
    ...

def read_tc_profile(console, iface: str) -> ImpairmentProfile:
    """Read current profile for a single interface from tc -j qdisc show (kernel state)."""
    ...

def clear_tc_profile(console, iface: str) -> None:
    """Remove all qdiscs from iface, returning it to the kernel default."""
    ...
```

**`apply_tc_profile` qdisc structure:**

- Without bandwidth limit: `tc qdisc add dev {iface} root netem {args}`
- With bandwidth limit: stacks netem (root, handle 1:) → TBF (parent 1:1, handle 10:) for rate limiting.

---

## 7. Device Implementations

> **Project Phase alignment:** `LinuxTrafficController` (§7.1) must be implemented and passing its round-trip exit criterion before **Project Phase 1 (Foundation)** is complete. `SpirentTrafficController` (§7.2) is only required when transitioning to a pre-production hardware testbed.

### 7.1 LinuxTrafficController (Standalone Device)

> **Design note — kernel-read profiles:** `get_interface_profile()` and `get_interface_profiles()` do **not** cache state. They parse `tc -j qdisc show` directly from the kernel on every call. This is deliberate:
> 1. **No single-writer guarantee.** A device can be rebooted or manually reconfigured. In-memory state would be stale.
> 2. **Kernel clamping.** `tc netem` silently clamps or rounds certain values. Parsing the applied qdisc catches mismatches.
> 3. **Round-trip fidelity.** The Phase 1 exit criterion requires reading back from `tc qdisc show`, not memory.

**`tc -j qdisc show` JSON field mapping:**

| `tc` JSON field | `ImpairmentProfile` field | Unit conversion |
|---|---|---|
| `options.delay.delay` | `latency_ms` | seconds → ms (`× 1000`) |
| `options.delay.jitter` | `jitter_ms` | seconds → ms (`× 1000`) |
| `options.loss-random.loss` | `loss_percent` | fraction → percent (`× 100`) |
| `options.rate` (tbf) | `bandwidth_limit_mbps` | B/s → Mbps (`× 8 ÷ 1 000 000`) |

```python
class LinuxTrafficController(LinuxDevice, TrafficController):
    def __init__(self, config: dict, cmdline_args: Namespace) -> None:
        super().__init__(config, cmdline_args)
        interfaces_config: dict = config.get("interfaces", {})
        if not interfaces_config:
            raise KeyError("'interfaces' is required in environment_def[device_name]")
        self._interfaces: list[str] = list(interfaces_config.keys())
        self._interfaces_config: dict[str, dict] = interfaces_config
        self._restore_cancel: threading.Event | None = None

    def set_impairment_profile(self, profile: ImpairmentProfile | dict) -> None:
        self._cancel_restore()
        p = profile_from_dict(profile) if isinstance(profile, dict) else profile
        for iface in self._interfaces:
            apply_tc_profile(self._console, iface, p)

    def set_interface_profile(self, interface: str, profile: ImpairmentProfile | dict) -> None:
        self._validate_interface(interface)
        self._cancel_restore()
        p = profile_from_dict(profile) if isinstance(profile, dict) else profile
        apply_tc_profile(self._console, interface, p)

    def get_interface_profile(self, interface: str) -> ImpairmentProfile:
        self._validate_interface(interface)
        return read_tc_profile(self._console, interface)

    def get_interface_profiles(self) -> dict[str, ImpairmentProfile]:
        return {iface: read_tc_profile(self._console, iface) for iface in self._interfaces}

    def clear(self) -> None:
        self._cancel_restore()
        for iface in self._interfaces:
            clear_tc_profile(self._console, iface)
```

### 7.2 SpirentTrafficController (Hardware Appliance)

The Spirent appliance manages multiple ports natively. `set_impairment_profile` maps to applying the profile to all configured ports; `set_interface_profile` maps to a single-port API call.

```python
class SpirentTrafficController(BoardfarmDevice, TrafficController):
    def set_impairment_profile(self, profile: ImpairmentProfile | dict) -> None:
        p = profile_from_dict(profile) if isinstance(profile, dict) else profile
        for port in self._ports:
            self._api.apply_impairment(port, p)

    def set_interface_profile(self, interface: str, profile: ImpairmentProfile | dict) -> None:
        p = profile_from_dict(profile) if isinstance(profile, dict) else profile
        self._api.apply_impairment(interface, p)

    def get_interface_profile(self, interface: str) -> ImpairmentProfile:
        return self._api.query_impairment(interface)

    def get_interface_profiles(self) -> dict[str, ImpairmentProfile]:
        return {port: self._api.query_impairment(port) for port in self._ports}

    def clear(self) -> None:
        for port in self._ports:
            self._api.clear_impairment(port)
```

---

### 7.3 `inject_transient()` — Automatic Restoration

> **Contract:** `inject_transient()` is **fire-and-forget**. The caller never needs to restore state — the method applies the transient condition to ALL interfaces and automatically restores each interface to its previous kernel profile after `duration_ms`. The call returns immediately.

#### Why fire-and-forget?

The primary consumer is `measure_failover_convergence()`: inject a blackout, then immediately poll `dut.get_active_wan_interface()` while timing the DUT's response. If the caller had to restore state manually, a polling loop would need to know *when* to call restore — which conflates test assertion logic with impairment control.

#### `LinuxTrafficController` implementation

```python
def inject_transient(self, event: str, duration_ms: int, **kwargs) -> None:
    self._cancel_restore()

    # Read current per-interface kernel state before applying transient
    previous: dict[str, ImpairmentProfile] = self.get_interface_profiles()

    # Build transient using first interface's profile as the reference baseline
    baseline = previous[self._interfaces[0]]
    transient = _build_transient_profile(event, baseline, **kwargs)

    # Apply transient to ALL interfaces
    for iface in self._interfaces:
        apply_tc_profile(self._console, iface, transient)

    cancel_event = threading.Event()
    self._restore_cancel = cancel_event

    def _restore() -> None:
        cancelled = cancel_event.wait(timeout=duration_ms / 1000)
        if not cancelled:
            # Restore each interface to its individual pre-injection profile
            for iface, prof in previous.items():
                apply_tc_profile(self._console, iface, prof)

    threading.Thread(target=_restore, daemon=True, name=f"tc-restore-{self.device_name}").start()
```

#### Transient profile construction

`_build_transient_profile()` builds the transient from the first interface's profile as baseline.  The transient is applied symmetrically to all interfaces; each interface is restored individually to its own pre-injection profile:

| `event` | Transient profile |
|---|---|
| `"blackout"` | `loss_percent=100.0`, preserves baseline latency/jitter |
| `"brownout"` | `latency_ms` and `loss_percent` from kwargs, preserves baseline bandwidth |
| `"latency_spike"` | `latency_ms=spike_latency_ms` from kwargs, preserves baseline loss/bandwidth |
| `"packet_storm"` | `loss_percent` from kwargs, preserves baseline latency/bandwidth |

#### Thread-safety summary

| Scenario | Behaviour |
|---|---|
| `inject_transient()` while a restore is pending | Cancels pending restore, applies new transient, schedules new restore |
| `set_impairment_profile()` while a restore is pending | Cancels pending restore; explicit profile takes effect permanently |
| `set_interface_profile()` while a restore is pending | Cancels pending restore; per-interface profile takes effect permanently |
| `clear()` while a restore is pending | Cancels pending restore; clears all impairment immediately |
| Two concurrent `inject_transient()` calls | Second call cancels first restore; last write wins |

---

## 8. Topology: Dedicated Impairment Devices

Impairment is **always** handled by a dedicated, standalone device — never co-hosted on another container.

| Phase | Impairment device | Class |
|---|---|---|
| Functional (Raikou containers) | Dedicated Linux container per WAN link | `LinuxTrafficController` |
| Pre-production (hardware) | Spirent / Keysight appliance | `SpirentTrafficController` |

Each WAN link has exactly one `TrafficController` device in inventory. Test use cases retrieve it by name or by iterating `get_devices_by_type(TrafficController)`.

---

## 9. Use Cases

**Location:** `boardfarm3/use_cases/traffic_control.py`

### 9.1 Symmetric Operations (All Interfaces)

```python
def set_impairment_profile(controller: TrafficController, profile: ImpairmentProfile | dict) -> None:
    """Apply profile to ALL interfaces (sustained — no auto-restore)."""
    controller.set_impairment_profile(profile)


def clear_impairment(controller: TrafficController) -> None:
    """Remove all impairments from ALL interfaces."""
    controller.clear()


def apply_preset(
    controller: TrafficController,
    preset_name: str,
    config: BoardfarmConfig,
    duration_ms: int | None = None,
) -> None:
    """Resolve preset from env config and apply to ALL interfaces.

    If duration_ms is given, applies as a timed transient (auto-restores).
    Otherwise, applies as a sustained profile.
    """
    preset = _get_preset_from_config(config, preset_name)
    if duration_ms is not None:
        event = preset.pop("event", "brownout")
        controller.inject_transient(event, duration_ms, **preset)
    else:
        controller.set_impairment_profile(profile_from_dict(preset))
```

### 9.2 Per-Interface Operations

```python
def set_interface_profile(
    controller: TrafficController,
    interface: str,
    profile: ImpairmentProfile | dict,
) -> None:
    """Apply profile to a single named interface (sustained)."""
    controller.set_interface_profile(interface, profile)


def get_impairment_profile(controller: TrafficController, interface: str) -> ImpairmentProfile:
    """Read current profile for a single interface from device/kernel (no cache)."""
    return controller.get_interface_profile(interface)


def get_all_impairment_profiles(controller: TrafficController) -> dict[str, ImpairmentProfile]:
    """Read current profiles for ALL configured interfaces from device/kernel (no cache)."""
    return controller.get_interface_profiles()
```

### 9.3 Transient Event Helpers

```python
def inject_blackout(controller: TrafficController, duration_ms: int) -> None:
    """100% packet loss on ALL interfaces for duration_ms; auto-restores."""
    controller.inject_transient("blackout", duration_ms)


def inject_brownout(controller, duration_ms, latency_ms=200, loss_percent=5.0) -> None:
    """Degraded conditions on ALL interfaces for duration_ms; auto-restores."""
    controller.inject_transient("brownout", duration_ms, latency_ms=latency_ms, loss_percent=loss_percent)


def inject_latency_spike(controller, duration_ms, spike_latency_ms=500) -> None:
    """High latency spike on ALL interfaces for duration_ms; auto-restores."""
    controller.inject_transient("latency_spike", duration_ms, spike_latency_ms=spike_latency_ms)


def inject_packet_storm(controller, duration_ms, loss_percent=10.0) -> None:
    """Burst packet loss on ALL interfaces for duration_ms; auto-restores."""
    controller.inject_transient("packet_storm", duration_ms, loss_percent=loss_percent)
```

---

## 10. Multi-Path Topologies

The number of WAN links and the number of interfaces per TC are **config-driven** — never hardcoded.

- **Single WAN**: One `TrafficController` device. Use `get_traffic_controller()` (no name).
- **Dual WAN**: Two devices (e.g., `wan1_tc`, `wan2_tc`). Use `get_traffic_controller(name="wan1_tc")` or target all via `get_devices_by_type(TrafficController)`.
- **Triple WAN (LTE + 2× broadband)**: Three devices (e.g., `wan1_tc`, `wan2_tc`, `lte_tc`).

**BDD step targeting:**

- **Single link**: `Given the "wan1_tc" network is set to "cable_typical"` — applies symmetric preset to both interfaces of `wan1_tc`.
- **All links**: `Given all networks are set to "cable_typical"` — applies to every `TrafficController`.
- **Per-interface asymmetry**: Use `set_interface_profile()` directly from a step definition.

---

## 11. Component Summary

| Component | Type | Location | Purpose |
|---|---|---|---|
| `TrafficController` | Template (ABC) | `templates/traffic_controller.py` | Abstract interface |
| `interfaces` | Env config | `environment_def[device_name].interfaces` | Per-interface initial profiles |
| `impairment_presets` | Env config | `environment_def.impairment_presets` | Named presets for BDD steps |
| `ImpairmentProfile` | Lib | `lib/traffic_control.py` | Per-interface parameter schema |
| `profile_from_dict` | Lib | `lib/traffic_control.py` | Dict → ImpairmentProfile parser |
| `apply_tc_profile` | Lib | `lib/traffic_control.py` | Apply profile to one interface |
| `read_tc_profile` | Lib | `lib/traffic_control.py` | Read profile from one interface (kernel) |
| `clear_tc_profile` | Lib | `lib/traffic_control.py` | Remove all qdiscs from one interface |
| `_build_transient_profile` | Lib | `lib/traffic_control.py` | Build transient ImpairmentProfile |
| `LinuxTrafficController` | Device | `devices/linux_traffic_controller.py` | Standalone Linux tc (multi-interface) |
| `SpirentTrafficController` | Device | `devices/spirent_traffic_controller.py` | Hardware appliance (future) |
| `get_traffic_controller` | Use case | `use_cases/traffic_control.py` | Device selection (single/multi-path) |
| `set_impairment_profile` | Use case | `use_cases/traffic_control.py` | Symmetric: apply to all interfaces |
| `set_interface_profile` | Use case | `use_cases/traffic_control.py` | Per-interface: apply to one interface |
| `get_impairment_profile` | Use case | `use_cases/traffic_control.py` | Per-interface: read from one interface |
| `get_all_impairment_profiles` | Use case | `use_cases/traffic_control.py` | Read from all interfaces |
| `clear_impairment` | Use case | `use_cases/traffic_control.py` | Remove all impairments |
| `apply_preset` | Use case | `use_cases/traffic_control.py` | Resolve + apply named preset |
| `inject_blackout` / `inject_brownout` / `inject_latency_spike` / `inject_packet_storm` | Use cases | `use_cases/traffic_control.py` | Transient event injection |
