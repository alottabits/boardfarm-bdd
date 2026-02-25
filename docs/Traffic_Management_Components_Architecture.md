# Traffic Management Components Architecture

**Date:** February 11, 2026  
**Status:** Design Document  

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
        :param profile: ImpairmentProfile or dict with latency_ms, jitter_ms, loss_percent, bandwidth_limit_mbps
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
        "bandwidth_limit_mbps": 1000
      }
    },
    "impairment_presets": {
      "pristine":      { "latency_ms": 5,   "jitter_ms": 1,  "loss_percent": 0,   "bandwidth_limit_mbps": 1000 },
      "cable_typical": { "latency_ms": 15,  "jitter_ms": 5,  "loss_percent": 0.1, "bandwidth_limit_mbps": 100  },
      "4g_mobile":     { "latency_ms": 80,  "jitter_ms": 30, "loss_percent": 1,   "bandwidth_limit_mbps": 20   },
      "satellite":     { "latency_ms": 600, "jitter_ms": 50, "loss_percent": 2,   "bandwidth_limit_mbps": 10   },
      "congested":     { "latency_ms": 25,  "jitter_ms": 40, "loss_percent": 3,   "bandwidth_limit_mbps": null }
    }
  }
}
```

**Structure:** `environment_def` contains both **device-specific keys** (device names like `wan1_impairment`) and **shared keys** (like `impairment_presets`). Device keys are merged into each device's config; shared keys like `impairment_presets` provide a BDD vocabulary used by all TrafficController devices.

- **environment_def[device_name].impairment_profile**: Default parameters for that device. Merged into device config and applied at init.
- **environment_def.impairment_presets**: Optional named presets for BDD steps (e.g. "Given the network is set to cable_typical"). Steps resolve preset names from the merged config.

### 4.3 Initialization Flow

1. Device boots and connects.
2. Merged config (inventory + env) provides `impairment_profile` for the device.
3. `set_impairment_profile(config["impairment_profile"])` is called at init.
4. The link starts in the configured state.

### 4.4 Runtime Changes

During tests, `set_impairment_profile(profile)` can be called again with new parameters—either from a preset name (resolved via env config) or explicit dict.

> **Teardown requirement:** Before calling `set_impairment_profile()` in a test step, the step (or its use-case helper) must save the current profile to `bf_context["original_impairments"][device_name]`. The `reset_sdwan_testbed_after_scenario` autouse fixture in `tests/conftest.py` reads this registry and restores all modified profiles after each scenario, ensuring a clean baseline for the next test. See `WAN_Edge_Appliance_testing.md §3.9` for the full teardown strategy.
>
> `inject_transient()` does **not** require manual teardown — it auto-restores the previous kernel state after `duration_ms` via a background daemon thread (see §7.2).

---

## 5. Device Getter and BDD Steps

### 5.1 get_traffic_controller(name=None)

**Location:** `boardfarm3/use_cases/traffic_control.py` or `boardfarm3/use_cases/device_getters.py`

Consistent with `get_lan_clients`, `get_wan_clients`. Supports single-WAN (omit name) and multi-path (specify device name).

**Note:** `get_device_manager().get_devices_by_type(TrafficController)` returns `dict[str, TrafficController]` (device name → instance). Use `devs[name]` for lookup by name, or `devs.values()` to iterate over all devices.

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

### 6.1 ImpairmentProfile Schema

```python
from dataclasses import dataclass

@dataclass
class ImpairmentProfile:
    """Parameters for network impairment."""
    # Symmetric baseline (applied to both directions if overrides not set)
    latency_ms: int
    jitter_ms: int
    loss_percent: float
    bandwidth_limit_mbps: int | None  # None = no limit (no TBF qdisc applied)

    # Per-direction overrides (None = use symmetric value above)
    egress_bandwidth_limit_mbps: int | None = None   # DUT → WAN (upload)
    ingress_bandwidth_limit_mbps: int | None = None  # WAN → DUT (download)
    egress_loss_percent: float | None = None
    ingress_loss_percent: float | None = None

    # Advanced impairments (packet corruption, reordering, duplication)
    reorder_percent: float = 0.0
    corrupt_percent: float = 0.0
    duplicate_percent: float = 0.0

def profile_from_dict(data: dict) -> ImpairmentProfile:
    """Parse dict to ImpairmentProfile."""
    return ImpairmentProfile(
        latency_ms=data["latency_ms"],
        jitter_ms=data["jitter_ms"],
        loss_percent=data["loss_percent"],
        bandwidth_limit_mbps=data.get("bandwidth_limit_mbps"),
        egress_bandwidth_limit_mbps=data.get("egress_bandwidth_limit_mbps"),
        ingress_bandwidth_limit_mbps=data.get("ingress_bandwidth_limit_mbps"),
        egress_loss_percent=data.get("egress_loss_percent"),
        ingress_loss_percent=data.get("ingress_loss_percent"),
        reorder_percent=data.get("reorder_percent", 0.0),
        corrupt_percent=data.get("corrupt_percent", 0.0),
        duplicate_percent=data.get("duplicate_percent", 0.0),
    )
```

### 6.2 Linux tc Helper Functions

**Note — Ingress Limitation:** Linux `tc netem` operates on egress only. Ingress rate-limiting and impairment require an IFB (Intermediate Functional Block) virtual device with an ingress filter redirect. The helper functions must handle IFB setup automatically when `ingress_*` overrides are set.

```python
def set_profile_via_tc(
    console: _LinuxConsole,
    interface: str,
    profile: ImpairmentProfile,
) -> None:
    """Build and execute tc qdisc/netem commands.
    
    Handles IFB creation for ingress impairments if required.
    """
    ...

def clear_tc_impairment(console: _LinuxConsole, interface: str) -> None:
    """Remove netem qdisc from interface."""
    ...
```

---

## 7. Device Implementations

> **Project Phase alignment:** `LinuxTrafficController` (§7.1) must be implemented and passing its round-trip exit criterion before **Project Phase 1 (Foundation)** is complete. `SpirentTrafficController` (§7.2) is only required when transitioning to a pre-production hardware testbed. See the [Component Readiness Map](WAN_Edge_Appliance_testing.md#component-readiness-map) in `WAN_Edge_Appliance_testing.md §5`.

### 7.1 LinuxTrafficController (Standalone Device)

> **Design note — kernel-read `get_impairment_profile()`:** This class does **not** cache `self._current` and does **not** return in-memory state. It parses `tc -j qdisc show` directly from the kernel on every call. This is deliberate:
> 1. **No single-writer guarantee.** A standalone device can be rebooted, manually reconfigured, or initialised by a fixture before `set_impairment_profile()` is ever called. In-memory state would be stale or `None` in all these cases.
> 2. **Kernel clamping.** `tc netem` silently clamps or rounds certain parameter values (e.g., very small delays, out-of-range correlation). Parsing the applied qdisc catches mismatches between what was requested and what the kernel actually programmed.
> 3. **Round-trip fidelity.** The Phase 1 exit criterion explicitly requires `get_impairment_profile()` to be verified against `tc qdisc show` output, not memory. This mirrors how `SpirentTrafficController` queries the appliance's REST API for current hardware state.
>
> `set_impairment_profile()` intentionally omits `self._current` assignment — `get` always reads from the kernel.

**`tc -j qdisc show` JSON parsing** — the relevant fields for an interface with netem + tbf:

```json
[
  {
    "kind": "netem", "dev": "eth1",
    "options": {
      "delay": {"delay": 0.05, "jitter": 0.005, "correlation": 0.25},
      "loss-random": {"loss": 0.01, "correlation": 0.0}
    }
  },
  {
    "kind": "tbf", "dev": "eth1",
    "options": {"rate": {"rate": 10000000}}
  }
]
```

Field mapping:
| `tc` JSON field | `ImpairmentProfile` field | Unit conversion |
|---|---|---|
| `options.delay.delay` | `latency_ms` | seconds → ms (`× 1000`) |
| `options.delay.jitter` | `jitter_ms` | seconds → ms (`× 1000`) |
| `options.loss-random.loss` | `loss_pct` | fraction → percent (`× 100`) |
| `options.rate.rate` (tbf) | `bandwidth_limit_mbps` | bps → Mbps (`÷ 1_000_000`) |

If no netem qdisc is present the interface is unimpaired; return `ImpairmentProfile(0, 0, 0.0, None)`.

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
        # No self._current assignment — get_impairment_profile reads from the kernel.

    def get_impairment_profile(self) -> ImpairmentProfile:
        """Parse current impairment from tc -j qdisc show (kernel state, not memory).

        Parses netem qdisc for latency/jitter/loss and tbf qdisc for bandwidth.
        Returns ImpairmentProfile(0, 0, 0.0, None) if no netem qdisc is present.
        """
        raw = self._console.sendline_and_read(
            f"tc -j qdisc show dev {self._interface}"
        )
        qdiscs = json.loads(raw)
        latency_ms = jitter_ms = 0
        loss_pct = 0.0
        bandwidth_limit_mbps = None
        for q in qdiscs:
            if q.get("kind") == "netem":
                opts = q.get("options", {})
                if delay := opts.get("delay"):
                    latency_ms = int(delay.get("delay", 0) * 1000)
                    jitter_ms = int(delay.get("jitter", 0) * 1000)
                if loss := opts.get("loss-random"):
                    loss_pct = round(loss.get("loss", 0.0) * 100, 2)
            elif q.get("kind") == "tbf":
                rate = q.get("options", {}).get("rate", {}).get("rate")
                if rate:
                    bandwidth_limit_mbps = rate // 1_000_000
        return ImpairmentProfile(latency_ms, jitter_ms, loss_pct, bandwidth_limit_mbps)

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

### 7.3 `inject_transient()` — Automatic Restoration

> **Contract:** `inject_transient()` is **fire-and-forget**. The caller never needs to restore state — the method applies the transient condition and automatically restores the previous profile after `duration_ms` expires. The call returns immediately so the test can begin polling the DUT right away.

#### Why fire-and-forget?

The primary consumer is `measure_failover_convergence()`: inject a blackout, then immediately poll `dut.get_active_wan_interface()` while timing the DUT's response. If the caller had to restore state manually, a polling loop would need to know *when* to call restore — which conflates the test assertion logic with impairment control, and breaks the clean use-case separation.

Commercial hardware appliances (Spirent, Ixia) handle timed transients natively. The `LinuxTrafficController` implementation mirrors this behaviour using a background thread.

#### `LinuxTrafficController` implementation

```python
def inject_transient(self, event: str, duration_ms: int, **kwargs) -> None:
    """Apply a timed transient impairment, then auto-restore the previous profile.

    The method returns immediately. A daemon thread restores the pre-injection
    kernel state after duration_ms. Any concurrent call to set_impairment_profile()
    or inject_transient() cancels the pending restore before proceeding.
    """
    self._cancel_restore()  # cancel any previously scheduled restore

    previous = self.get_impairment_profile()  # read kernel state, not memory
    transient = _build_transient_profile(event, previous, **kwargs)
    set_profile_via_tc(self._console, self._interface, transient)

    cancel_event = threading.Event()
    self._restore_cancel = cancel_event

    def _restore() -> None:
        cancelled = cancel_event.wait(timeout=duration_ms / 1000)
        if not cancelled:
            set_profile_via_tc(self._console, self._interface, previous)

    threading.Thread(target=_restore, daemon=True).start()

def _cancel_restore(self) -> None:
    """Signal any pending restore thread to abort."""
    if hasattr(self, "_restore_cancel") and self._restore_cancel:
        self._restore_cancel.set()
        self._restore_cancel = None
```

`set_impairment_profile()` and `clear()` also call `_cancel_restore()` at entry so that an explicit profile change always wins over a scheduled auto-restore.

#### "Previous state" definition

`previous` is obtained via `get_impairment_profile()` — i.e., parsed from `tc -j qdisc show` (kernel state) at the moment `inject_transient()` is called, not from in-memory cache. This guarantees the restore target is the actual applied state, regardless of how the current profile was set.

#### `_build_transient_profile()` helper

Constructs the `ImpairmentProfile` for the transient condition from the event type and kwargs, using `previous` as the baseline:

| `event` | Result profile |
|---|---|
| `"blackout"` | `ImpairmentProfile(0, 0, 100.0, 0)` — 100% loss, effectively drops all traffic |
| `"brownout"` | `previous` with `latency_ms` and `loss_percent` overridden from kwargs |
| `"latency_spike"` | `previous` with `latency_ms` overridden from kwargs |
| `"packet_storm"` | `previous` with `loss_percent` overridden from kwargs |

#### `SpirentTrafficController` implementation

The Spirent REST API supports timed events natively. `inject_transient()` translates to a single API call; no background thread is needed:

```python
def inject_transient(self, event: str, duration_ms: int, **kwargs) -> None:
    """Delegate timed transient to Spirent hardware — hardware manages the timer."""
    self._api.inject_transient_event(event, duration_ms, **kwargs)
```

#### Thread-safety summary

| Scenario | Behaviour |
|---|---|
| `inject_transient()` while a restore is pending | Cancels pending restore, applies new transient, schedules new restore |
| `set_impairment_profile()` while a restore is pending | Cancels pending restore; explicit profile takes effect permanently |
| `clear()` while a restore is pending | Cancels pending restore; clears all impairment immediately |
| Two concurrent `inject_transient()` calls | Second call cancels first restore; last write wins |

---

## 8. Topology: Dedicated Impairment Devices

In this testbed impairment is **always** handled by a dedicated, standalone device — never co-hosted on another container. This holds across all phases:

| Phase | Impairment device | Class |
|---|---|---|
| Functional (Raikou containers) | Dedicated Linux container per WAN link | `LinuxTrafficController` |
| Pre-production (hardware) | Spirent / Keysight appliance | `SpirentTrafficController` |

Each WAN link has exactly one `TrafficController` device in inventory. Test use cases retrieve it by name or by iterating `get_devices_by_type(TrafficController)`.

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
    """Inject complete link failure (e.g. cable unplug, interface down)."""
    controller.inject_transient("blackout", duration_ms)


def inject_brownout(
    controller: TrafficController,
    duration_ms: int,
    latency_ms: int = 200,
    loss_percent: float = 5.0,
) -> None:
    """Inject degraded link conditions (high latency/loss without complete failure)."""
    controller.inject_transient(
        "brownout", duration_ms,
        latency_ms=latency_ms,
        loss_percent=loss_percent,
    )


def inject_latency_spike(
    controller: TrafficController,
    duration_ms: int,
    spike_latency_ms: int = 500,
) -> None:
    """Inject temporary latency spike above baseline."""
    controller.inject_transient(
        "latency_spike", duration_ms,
        spike_latency_ms=spike_latency_ms,
    )


def inject_packet_storm(
    controller: TrafficController,
    duration_ms: int,
    loss_percent: float = 10.0,
) -> None:
    """Inject burst of packet loss or packet duplication."""
    controller.inject_transient(
        "packet_storm", duration_ms,
        loss_percent=loss_percent,
    )
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
| `inject_blackout`, `inject_brownout`, `inject_latency_spike`, `inject_packet_storm` | Use cases | `use_cases/traffic_control.py` | Transient event injection |
