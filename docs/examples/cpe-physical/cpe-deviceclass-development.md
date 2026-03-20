# RPi prplOS CPE Device Class Development Plan

**Document Version**: 1.0  
**Created**: January 9, 2026  
**Status**: 📋 **Planning Phase**

---

## Executive Summary

This document outlines the incremental development plan for implementing the `RPiPrplOSCPE` device class for physical Raspberry Pi 4 hardware running prplOS. The implementation will follow an iterative approach, implementing and testing methods one by one to ensure functionality at each step.

**Goal**: Create a production-ready device class that enables Boardfarm to instantiate and manage a physical RPi4 running prplOS as a CPE device in the testbed.

**Strategy**: Implement everything needed for Boardfarm to initialize the CPE (device classes + registration + config) in Phase 1, then incrementally add functionality based on testing and requirements.

**Testing Approach**: Follow the established BDD structure in `boardfarm-bdd`, treating the testbed as the system under test. All tests follow: Use Case → Feature → Step Definitions → Unit Tests → Integration Tests.

**Key Design Decision**: Create **`RPiPrplOSSW`** as a device-specific software class (similar to how `PrplOSSW` exists for containerized prplOS). Even though the software stack is identical, each device type should have its own SW class for clarity, separation of concerns, and potential future divergence. `RPiPrplOSSW` will inherit from `CPESwLibraries` (the library component) and can leverage `PrplOSSW` as a reference implementation.

---

## Development Phases Overview

### Phase 1: Complete Implementation - Boardfarm Can Initialize CPE ✅

**Goal**: Everything needed for Boardfarm to successfully initialize the CPE device.

**Includes**:
- Device class implementation (HW, SW, CPE)
- Device registration (Boardfarm plugin system)
- Configuration file (testbed config)
- Basic validation (verify Boardfarm can initialize device)

**Success Criteria**: Boardfarm can instantiate device, boot it, and device registers with ACS.

**Estimated Time**: 8-11 hours

### Phase 2: Incremental Method Addition 🔄

**Goal**: Add methods incrementally as testbed requirements emerge.

**Strategy**: Implement → Unit Test → Direct Test → Integration Test → Next Method

**Examples**: `boardfarm_device_configure` hook, additional network operations, factory reset, etc.

**Estimated Time**: As needed (per method)

---

---

## Reference Implementations

### Primary References

1. **`prplos_cpe.py`** (`PrplDockerCPE`)
   - Containerized prplOS implementation
   - TR-181 data model access via `ubus-cli`
   - TR-069 ACS configuration
   - Network interface management

2. **`rpirdkb_cpe.py`** (`RPiRDKBCPE`)
   - Physical RPi4 hardware implementation
   - Serial console connection patterns
   - MAC address and serial number retrieval from RPi hardware
   - Power cycle via PDU (we'll use soft reboot instead)

### Template Structure

- **`boardfarm3/templates/cpe/cpe.py`**: Base CPE class (abstract)
- **`boardfarm3/templates/cpe/cpe_hw.py`**: Hardware abstraction template
- **`boardfarm3/templates/cpe/cpe_sw.py`**: Software operations template
- **`boardfarm3/lib/cpe_sw.py`**: `CPESwLibraries` base class (provides common implementations)

---

## Architecture Overview

### Class Hierarchy

**Inheritance Relationships**:
```
CPEHW (Template)
└── RPiPrplOSHW (device-specific class)

CPESW (Template)
└── CPESwLibraries (Library component - in boardfarm3/lib/cpe_sw.py)
    └── RPiPrplOSSW (device-specific class - inherits from CPESwLibraries)

CPE (Template)
└── RPiPrplOSCPE (Main device class - inherits from CPE + BoardfarmDevice)
```

**Composition (RPiPrplOSCPE contains)**:
```
RPiPrplOSCPE (in rpiprplos_cpe.py)
├── hw: RPiPrplOSHW (hardware component)
└── sw: RPiPrplOSSW (software component)
```

**File Locations**:
- **Library**: `boardfarm3/lib/cpe_sw.py` → `CPESwLibraries`
- **Device File**: `boardfarm3/devices/rpiprplos_cpe.py` → `RPiPrplOSHW`, `RPiPrplOSSW`, `RPiPrplOSCPE`

**Architecture Pattern**: Each device type has its own HW and SW classes:
- `PrplOSSW` in `prplos_cpe.py` (for containerized prplOS)
- `RPiRDKBSW` in `rpirdkb_cpe.py` (for RPi RDKB)
- `RPiPrplOSSW` in `rpiprplos_cpe.py` (for RPi prplOS) ← **We create this**

**Note**: `RPiPrplOSSW` inherits from `CPESwLibraries` (library) and can leverage `PrplOSSW` as a reference implementation since the software stack is identical, but it should be a separate class for clarity and potential future divergence.

### Key Differences from Reference Implementations

| Aspect | PrplDockerCPE | RPiRDKBCPE | RPiPrplOSCPE |
|--------|---------------|------------|--------------|
| **Hardware** | Container | Physical RPi4 | Physical RPi4 |
| **Connection** | `docker exec` | Serial console | Serial console |
| **Power Cycle** | Container restart | PDU power cycle | Soft reboot via console |
| **MAC Address** | From config/eth1 | From RPi hardware | From USB dongle (eth1) |
| **Serial Number** | From config/env | From `/proc/cpuinfo` | From `/proc/cpuinfo` |
| **TR-181 Access** | `ubus-cli` | `dmcli` | `ubus-cli` (like PrplDockerCPE) |
| **WAN Interface** | eth1 | erouter0 | eth1 |
| **LAN Interface** | br-lan | brlan0 | br-lan |

---

## Phase 1: Complete Implementation - Boardfarm Can Initialize CPE

**Goal**: Implement everything needed for Boardfarm to successfully initialize the CPE device:
1. **Device class implementation** (HW, SW, CPE classes)
2. **Device registration** (register with Boardfarm plugin system)
3. **Configuration file** (create Boardfarm config for testbed)
4. **Basic validation** (verify Boardfarm can initialize device)

**Strategy**: Get end-to-end working first (Boardfarm → Device → ACS), then incrementally add other methods as needed.

**Success Criteria**:
- ✅ Device class implemented (HW, SW, CPE)
- ✅ Device registered in Boardfarm (`boardfarm3/plugins/core.py`)
- ✅ Configuration file created (`boardfarm_config_prplos_rpi.json`)
- ✅ Device can be instantiated via Boardfarm (`--skip-boot` works)
- ✅ Serial console connection works
- ✅ Device boots and comes online (via `boardfarm_device_boot`)
- ✅ Device registers with ACS
- ✅ Device is accessible via ACS (can query parameters)

### 1.1 Hardware Class (`RPiPrplOSHW`) - Absolute Minimum

**File**: `boardfarm/boardfarm3/devices/rpiprplos_cpe.py`

**Goal**: Enable serial console connection and basic hardware operations needed for boot and ACS registration.

#### Required Abstract Methods (from `CPEHW` template) - Minimum Set

| Method | Priority | Why Needed | Implementation Strategy | Reference |
|--------|----------|------------|----------------------|-----------|
| `__init__` | **CRITICAL** | Device instantiation | Store config and cmdline_args, initialize `_console = None` | `RPiRDKBHW.__init__` |
| `config` (property) | **CRITICAL** | Device instantiation | Return `self._config` | `RPiRDKBHW.config` |
| `connect_to_consoles` | **CRITICAL** | Serial port access | Serial console via `connection_factory` | `RPiRDKBHW.connect_to_consoles` |
| `get_console` | **CRITICAL** | Serial port access | Return `self._console` for "console" | `RPiRDKBHW.get_console` |
| `disconnect_from_consoles` | **CRITICAL** | Cleanup | Close `self._console` if not None | `RPiRDKBHW.disconnect_from_consoles` |
| `get_interactive_consoles` | **CRITICAL** | Abstract requirement | Return `{"console": self._console}` | `RPiRDKBHW.get_interactive_consoles` |
| `mac_address` (property) | **CRITICAL** | ACS registration (provisioning) | Read from USB dongle (eth1) or config | `PrplOSx86HW.mac_address` |
| `wan_iface` (property) | **CRITICAL** | Abstract requirement | Return `"eth1"` | `PrplOSx86HW.wan_iface` |
| `mta_iface` (property) | **CRITICAL** | Abstract requirement | Raise `NotSupportedError` | `PrplOSx86HW.mta_iface` |
| `power_cycle` | **CRITICAL** | Boot sequence | Soft reboot via console: `reboot -f` | `PrplOSx86HW.power_cycle` |
| `wait_for_hw_boot` | **CRITICAL** | Boot sequence | Wait for WAN interface (eth1) to appear | `RPiRDKBHW.wait_for_hw_boot` |
| `flash_via_bootloader` | **CRITICAL** | Abstract requirement | Raise `NotSupportedError` | `RPiRDKBHW.flash_via_bootloader` |

#### Additional Required Methods (for ACS registration)

| Method | Priority | Why Needed | Implementation Strategy | Reference |
|--------|----------|------------|----------------------|-----------|
| `serial_number` (property) | **CRITICAL** | CPE ID generation (for ACS) | Read from `/proc/cpuinfo` | `RPiRDKBHW.serial_number` |
| `_shell_prompt` (property) | **CRITICAL** | Console connection | Return `[r"/[a-zA-Z]* #"]` (prplOS prompt) | `PrplOSx86HW._shell_prompt` |

**Estimated Lines**: ~120 lines

**Note**: Other methods can be added incrementally as needed (e.g., `wait_for_hw_boot` improvements, additional hardware operations).

### 1.2 Software Class (`RPiPrplOSSW`) - Absolute Minimum

**File**: `boardfarm/boardfarm3/devices/rpiprplos_cpe.py`

**Inherits from**: `CPESwLibraries` (library component in `boardfarm3/lib/cpe_sw.py`)

**Goal**: Enable device online detection, ACS configuration, and ACS registration.

**Reference Implementation**: `PrplOSSW` in `prplos_cpe.py` (can copy/adapt methods since software stack is identical)

#### Critical Methods for ACS Registration

| Method | Priority | Why Needed | Implementation Strategy | Reference |
|--------|----------|------------|----------------------|-----------|
| `__init__` | **CRITICAL** | Device instantiation | Call `super().__init__(hardware)` | `PrplOSSW.__init__` |
| `cpe_id` (property) | **CRITICAL** | ACS identification | Build from OUI + Serial (from `/var/etc/environment`) | `PrplOSSW.cpe_id` |
| `tr69_cpe_id` (property) | **CRITICAL** | Abstract requirement | Return `self.cpe_id` | `PrplOSSW.tr69_cpe_id` |
| `wait_device_online` | **CRITICAL** | Boot sequence | Wait for WAN online + TR-181 ready | `PrplOSSW.wait_device_online` |
| `configure_management_server` | **CRITICAL** | ACS registration | Configure ACS URL via `ubus-cli` | `PrplOSSW.configure_management_server` |
| `wait_for_acs_connection` | **CRITICAL** | ACS registration | Wait for CPE to register with ACS | `PrplOSSW.wait_for_acs_connection` |
| `_is_tr181_ready` | **CRITICAL** | Boot sequence | Check TR-181 accessibility | `PrplOSSW._is_tr181_ready` |

#### Abstract Methods - Minimal Stubs (Required by Template)

These must exist but can be minimal implementations initially:

| Method | Priority | Implementation Strategy | Reference |
|--------|----------|----------------------|-----------|
| `version` (property) | **HIGH** | Read from `/etc/build.prplos.version` | `PrplOSSW.version` |
| `lan_iface` (property) | **HIGH** | Return `"br-lan"` | `PrplOSSW.lan_iface` |
| `erouter_iface` (property) | **HIGH** | Return `"eth1"` | `PrplOSSW.erouter_iface` |
| `guest_iface` (property) | **MEDIUM** | Return `"br-guest"` or raise | `PrplOSSW.guest_iface` |
| `lan_gateway_ipv4` (property) | **MEDIUM** | Read from `br-lan` interface | `PrplOSSW.lan_gateway_ipv4` |
| `lan_gateway_ipv6` (property) | **MEDIUM** | Return `IPv6Address("::")` (placeholder) | Minimal |
| `lan_network_ipv4` (property) | **MEDIUM** | Derive from `lan_gateway_ipv4` | Minimal |
| `json_values` (property) | **MEDIUM** | Parse `uci show` output | `PrplOSSW.json_values` |
| `gui_password` (property) | **MEDIUM** | Return from config or default | `PrplOSSW.gui_password` |
| `wifi` (property) | **LOW** | Raise `NotSupportedError` | `PrplOSSW.wifi` |
| `wait_for_boot` | **HIGH** | Call `self._hw.wait_for_hw_boot()` | `PrplOSSW.wait_for_boot` |
| `is_online` | **HIGH** | Check WAN interface connectivity | `CPESwLibraries` provides base |
| `finalize_boot` | **LOW** | Raise `NotImplementedError` | `PrplOSSW.finalize_boot` |
| `aftr_iface` (property) | **LOW** | Raise `NotImplementedError` | `PrplOSSW.aftr_iface` |
| `get_interface_mtu_size` | **LOW** | Use `jc.parse("ifconfig", ...)` | `PrplOSSW.get_interface_mtu_size` |
| `verify_cpe_is_booting` | **LOW** | Raise `NotSupportedError` | `PrplOSSW.verify_cpe_is_booting` |
| `get_provision_mode` | **LOW** | Return from config or default | `PrplOSSW.get_provision_mode` |
| `is_production` | **LOW** | Return `False` | `PrplOSSW.is_production` |
| `reset` | **MEDIUM** | Call `self._hw.power_cycle()` | `PrplOSSW.reset` |
| `factory_reset` | **LOW** | Raise `NotSupportedError` | `PrplOSSW.factory_reset` |

**Note**: Many methods are provided by `CPESwLibraries` base class (no implementation needed).

**Estimated Lines**: ~250 lines (can copy most from `PrplOSSW`)

**Strategy**: Implement critical methods first, add stubs for abstract requirements, then incrementally implement other methods as needed.

### 1.3 Main Device Class (`RPiPrplOSCPE`) - Absolute Minimum

**Goal**: Enable Boardfarm to instantiate device and execute boot sequence.

#### Required Methods

| Method | Priority | Why Needed | Implementation Strategy | Reference |
|--------|----------|------------|----------------------|-----------|
| `__init__` | **CRITICAL** | Device instantiation | Initialize `_hw` and `_sw = None` | `RPiRDKBCPE.__init__` |
| `config` (property) | **CRITICAL** | Device instantiation | Return `self._config` | `RPiRDKBCPE.config` |
| `hw` (property) | **CRITICAL** | Device instantiation | Return `self._hw` | `RPiRDKBCPE.hw` |
| `sw` (property) | **CRITICAL** | Device instantiation | Return `self._sw` | `RPiRDKBCPE.sw` |
| `boardfarm_device_boot` (hook) | **CRITICAL** | Boot sequence + ACS registration | Full boot: connect, provision, reboot, wait, configure ACS | `PrplDockerCPE.boardfarm_device_boot` |
| `boardfarm_skip_boot` (hook) | **CRITICAL** | Skip-boot mode | Connect console, initialize `_sw` | `RPiRDKBCPE.boardfarm_skip_boot` |

**Boot Hook Implementation** (from `PrplDockerCPE.boardfarm_device_boot`):
```python
def boardfarm_device_boot(self, device_manager: DeviceManager) -> None:
    self.hw.connect_to_consoles(self.device_name)
    self._sw = RPiPrplOSSW(self._hw)
    # Provision (if provisioner available)
    # Power cycle
    # Wait for boot
    # Wait for online
    # Configure ACS
    # Log CPE ID
```

**Estimated Lines**: ~60 lines

**Total Phase 1.1-1.3 (Device Classes)**: ~430 lines

### 1.4 Device Registration

**Goal**: Register device class with Boardfarm so it can be instantiated.

**File**: `boardfarm/boardfarm3/plugins/core.py`

#### Tasks

| Task | Priority | Implementation | Reference |
|------|----------|----------------|-----------|
| Add import | **CRITICAL** | `from boardfarm3.devices.rpiprplos_cpe import RPiPrplOSCPE` | See `core.py` for pattern |
| Add to registry | **CRITICAL** | Add `"bf_rpiprplos_cpe": RPiPrplOSCPE` to `boardfarm_add_devices()` | See existing devices |

**Implementation**:
```python
# In boardfarm3/plugins/core.py

from boardfarm3.devices.rpiprplos_cpe import RPiPrplOSCPE

def boardfarm_add_devices() -> dict[str, type[BoardfarmDevice]]:
    return {
        # ... existing devices ...
        "bf_rpiprplos_cpe": RPiPrplOSCPE,
    }
```

**Estimated Lines**: ~5 lines

### 1.5 Boardfarm Configuration File

**Goal**: Create testbed configuration file so Boardfarm can instantiate the device.

**File**: `boardfarm-bdd/bf_config/boardfarm_config_prplos_rpi.json`

#### Required Configuration

**Device Entry**:
```json
{
    "prplos-rpi-1": {
        "devices": [
            {
                "conn_cmd": [
                    "picocom -b 115200 /dev/ttyUSB0"
                ],
                "connection_type": "local_cmd",
                "lan_iface": "br-lan",
                "name": "board",
                "type": "bf_rpiprplos_cpe",
                "wan_iface": "eth1",
                "wan_mac": "00:e0:4c:1f:65:b8"
            },
            {
                "name": "wan",
                "type": "bf_wan",
                // ... existing wan config ...
            },
            {
                "name": "lan",
                "type": "bf_lan",
                // ... existing lan config ...
            },
            {
                "name": "genieacs",
                "type": "bf_acs",
                // ... existing ACS config ...
            }
            // ... other devices unchanged ...
        ]
    }
}
```

**Key Fields**:
- `conn_cmd`: Serial console command (from Phase 2 network config)
- `connection_type`: `"local_cmd"`
- `wan_iface`: `"eth1"` (USB-Ethernet dongle)
- `lan_iface`: `"br-lan"` (bridge with eth0)
- `wan_mac`: USB dongle MAC address (from Phase 2)
- `type`: `"bf_rpiprplos_cpe"` (must match registration)
- `name`: `"board"` (CPE device name)

**Estimated Lines**: ~50 lines (JSON)

### 1.6 Testing Implementation (BDD Structure)

**Goal**: Create comprehensive tests following the BDD structure established in `boardfarm-bdd`.

#### 1.6.1 Use Case Document

**File**: `requirements/Device Class - RPi prplOS CPE.md`

**Content**: Document the use case for device class initialization, including:
- **Goal**: Boardfarm can successfully instantiate and boot a physical RPi4 running prplOS
- **Main Success Scenario**: Steps from instantiation to ACS registration
- **Extensions**: Error cases (device not found, console connection failure, boot failure, ACS registration failure)

**Estimated Lines**: ~100 lines (Markdown)

#### 1.6.2 BDD Feature File

**File**: `tests/features/Device Class Initialization.feature`

**Scenarios**:
- `UC-Device-Init-Main: Successful Device Initialization`
- `UC-Device-Init-1.a: Device Not Found in Configuration`
- `UC-Device-Init-2.a: Serial Console Connection Failure`
- `UC-Device-Init-3.a: Boot Sequence Failure`
- `UC-Device-Init-4.a: ACS Registration Failure`

**Example**:
```gherkin
Feature: Device Class Initialization
  Background:
    Given the testbed is configured with RPi prplOS CPE

  Scenario: UC-Device-Init-Main: Successful Device Initialization
    Given Boardfarm instantiates the device from configuration
    When Boardfarm connects to the serial console
    And Boardfarm boots the device
    Then the device comes online
    And the device registers with ACS
```

**Estimated Lines**: ~50 lines (Gherkin)

#### 1.6.3 Step Definitions

**File**: `tests/step_defs/device_class_steps.py`

**Steps to implement**:
- `given("the testbed is configured with RPi prplOS CPE")`
- `given("Boardfarm instantiates the device from configuration")`
- `when("Boardfarm connects to the serial console")`
- `when("Boardfarm boots the device")`
- `then("the device comes online")`
- `then("the device registers with ACS")`

**Example**:
```python
from pytest_bdd import given, when, then
from boardfarm3.devices.rpiprplos_cpe import RPiPrplOSCPE

@given("Boardfarm instantiates the device from configuration")
def boardfarm_instantiates_device(device_manager):
    """Verify Boardfarm can instantiate device."""
    cpe = device_manager.get_device_by_type(RPiPrplOSCPE)
    assert cpe is not None
    return cpe

@when("Boardfarm connects to the serial console")
def boardfarm_connects_console(cpe: RPiPrplOSCPE):
    """Connect to serial console."""
    cpe.hw.connect_to_consoles("test-device")
    assert cpe.hw._console is not None
```

**Estimated Lines**: ~150 lines (Python)

#### 1.6.4 Unit Tests for Step Definitions

**File**: `tests/unit/test_step_defs/test_device_class_steps.py`

**Purpose**: Validate step definition logic with mocks before integration testing.

**Example**:
```python
from unittest.mock import Mock
from boardfarm3.devices.rpiprplos_cpe import RPiPrplOSCPE
from tests.step_defs.device_class_steps import boardfarm_instantiates_device

def test_boardfarm_instantiates_device(mock_device_manager):
    """Unit test for device instantiation step."""
    mock_device_manager.get_device_by_type.return_value = Mock(spec=RPiPrplOSCPE)
    result = boardfarm_instantiates_device(mock_device_manager)
    assert result is not None
    mock_device_manager.get_device_by_type.assert_called_once_with(RPiPrplOSCPE)
```

**Estimated Lines**: ~100 lines (Python)

#### 1.6.5 Direct Tests (Device Class Methods)

**Purpose**: Test device class methods directly with hardware (no Boardfarm).

**Location**: Standalone scripts or direct method calls during development.

**Example**: `test_rpiprplos_hw_direct.py` (as shown in testing strategy section)

**Estimated Lines**: ~50 lines per test script

#### 1.6.6 Integration Tests (BDD Scenarios)

**Purpose**: End-to-end validation via pytest-bdd with full testbed.

**Execution**:
```bash
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate

# Run all device class initialization scenarios
pytest --board-name prplos-rpi-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_prplos_rpi.json \
  -k "DeviceInit" -v

# Run specific scenario
pytest --board-name prplos-rpi-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_prplos_rpi.json \
  -k "UCDeviceInitMain" -v
```

#### 1.6.7 Testing Checklist

**Use Case**:
- [ ] Use case document created in `requirements/`
- [ ] Use case reviewed and approved

**Feature File**:
- [ ] Feature file created in `tests/features/`
- [ ] All scenarios written (Main + Extensions)
- [ ] Scenarios verify Success Guarantees

**Step Definitions**:
- [ ] Step definitions implemented in `tests/step_defs/device_class_steps.py`
- [ ] All steps from feature file have corresponding definitions
- [ ] Steps use proper type hints (device templates)

**Unit Tests**:
- [ ] Unit tests created in `tests/unit/test_step_defs/test_device_class_steps.py`
- [ ] All step definitions have unit tests
- [ ] Unit tests pass with mocks

**Direct Tests**:
- [ ] Direct tests created for device class methods
- [ ] Direct tests pass with real hardware

**Integration Tests**:
- [ ] BDD scenarios run successfully via pytest-bdd
- [ ] All scenarios pass with full testbed
- [ ] Testbed functions properly as system under test

**Total Phase 1.6 (Testing)**: ~450 lines (100 use case + 50 feature + 150 steps + 100 unit tests + 50 direct tests)

**Total Phase 1**: ~935 lines (430 implementation + 5 registration + 50 config + 450 testing)

**Phase 1 Complete When**:
- ✅ All device classes implemented
- ✅ Device registered in Boardfarm
- ✅ Configuration file created
- ✅ Use case document created
- ✅ Feature file with scenarios created
- ✅ Step definitions implemented
- ✅ Unit tests for step definitions created and passing
- ✅ Direct tests for device class methods created and passing
- ✅ BDD scenarios run successfully via pytest-bdd
- ✅ Boardfarm can instantiate device (BDD scenario passes)
- ✅ Boardfarm can boot device (BDD scenario passes)
- ✅ Device registers with ACS (BDD scenario passes)
- ✅ Testbed functions properly as system under test

---

## Phase 2: Incremental Method Implementation

**Goal**: After Phase 1 is complete (Boardfarm can initialize CPE), incrementally add other methods as needed.

**Strategy**: 
- Add methods one at a time based on testbed requirements
- Test each new method in isolation (unit tests)
- Test with hardware (direct tests)
- Test via Boardfarm (integration tests)

### 2.1 Additional Hardware Methods (As Needed)

Methods to add incrementally:
- Enhanced `wait_for_hw_boot` (better error handling)
- Additional hardware operations (if needed)

### 2.2 Additional Software Methods (As Needed)

Methods to add incrementally:
- `boardfarm_device_configure` hook (HTTP GUI verification)
- Additional network operations
- Additional TR-181 operations
- Factory reset (if needed)
- Other methods as testbed requirements emerge

### 2.3 Testing Strategy for New Methods

**For Each New Method**:
1. **Unit Test**: Test with mocks (no hardware needed)
2. **Direct Test**: Test with actual hardware (no Boardfarm needed)
3. **Integration Test**: Test via Boardfarm (full testbed)

**Example Workflow**:
```python
# 1. Implement method
def new_method(self):
    # Implementation

# 2. Unit test (immediately)
def test_new_method(mock_hw):
    # Test with mocks

# 3. Direct test (with hardware)
device = RPiPrplOSCPE(config, cmdline_args)
device.boardfarm_skip_boot()
result = device.sw.new_method()
assert result == expected

# 4. Integration test (via Boardfarm)
# Run via pytest with full testbed
```

---

## Testing Strategy - BDD Approach with Testbed as System Under Test

### Testing Philosophy

Following the established BDD structure in `boardfarm-bdd`, we treat the **testbed as the system under test**. This means:

1. **Define Use Cases**: Document what the device class should enable
2. **Define Features**: Translate use cases into BDD scenarios
3. **Build Test Cases**: Implement step definitions that exercise the device class
4. **Create Unit Tests**: Validate step definition logic with mocks
5. **Verify Test Cases**: Ensure step definitions work correctly
6. **Verify Testbed**: End-to-end validation that the testbed functions properly

### Test Organization Structure

All tests follow the established `boardfarm-bdd` structure:

```
boardfarm-bdd/
├── requirements/
│   └── Device Class - RPi prplOS CPE.md          # Use case for device class
├── tests/
│   ├── features/
│   │   └── Device Class Initialization.feature   # BDD scenarios
│   ├── step_defs/
│   │   ├── device_class_steps.py                  # Steps for device class operations
│   │   └── boardfarm_steps.py                     # Steps for Boardfarm operations
│   ├── unit/
│   │   └── test_step_defs/
│   │       └── test_device_class_steps.py         # Unit tests for step definitions
│   └── test_artifacts/
│       └── (config files, test data)
```

### Testing Layers

**Layer 1: Unit Tests** (Step Definition Logic)
- **Location**: `tests/unit/test_step_defs/test_device_class_steps.py`
- **Purpose**: Validate step definition logic with mocks
- **When**: Immediately after implementing step definitions
- **Example**: Test `device_connects_to_serial_console` with mocked console

**Layer 2: Direct Tests** (Device Class Methods)
- **Location**: Standalone scripts or direct method calls
- **Purpose**: Test device class methods with actual hardware (no Boardfarm)
- **When**: After unit tests pass
- **Example**: Test `mac_address` property with real serial connection

**Layer 3: Integration Tests** (BDD Scenarios via Boardfarm)
- **Location**: `tests/features/Device Class Initialization.feature`
- **Purpose**: End-to-end validation via pytest-bdd with full testbed
- **When**: After direct tests pass
- **Example**: Run BDD scenario "Successful Device Initialization" via pytest

### Benefits of This Approach

1. **Consistency**: Same structure as CPE functionality tests
2. **Traceability**: Use case → Feature → Step → Unit test
3. **Reusability**: Step definitions can be reused across scenarios
4. **Maintainability**: Clear separation of concerns
5. **Early Validation**: Unit tests catch logic errors before integration
6. **Documentation**: BDD scenarios serve as executable documentation

---

## Testing Strategy - Incremental Development Approach

### ⚠️ Virtual Environment Requirement

**CRITICAL**: All Python and pytest commands must be executed in the virtual environment (`.venv-3.12`).

**Virtual Environment Location**: `~/projects/req-tst/boardfarm-bdd/.venv-3.12`

**Always activate before running any tests**:
```bash
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate
```

**Prompt will show**: `(.venv-3.12) rjvisser@alottabytes:~/projects/req-tst/boardfarm-bdd$`

### Overview: Three-Layer Testing Strategy

Given the incremental implementation plan, we use a **three-layer testing approach**:

1. **Unit Testing** (Layer 1): Test methods with mocks - fast, no hardware needed
2. **Direct Testing** (Layer 2): Test with actual hardware but without Boardfarm - quick iteration
3. **Integration Testing** (Layer 3): Test via Boardfarm - full testbed validation

**Workflow**: Implement → Unit Test → Direct Test → Integration Test → Next Method

**All commands assume virtual environment is activated** (`.venv-3.12`).

### Testing Without Boardfarm Configuration

**Yes, you can test device class methods directly without Boardfarm configuration!**

The device classes can be instantiated directly by providing:
- `config`: Dictionary with device configuration
- `cmdline_args`: Namespace object with command-line arguments

This allows for:
1. **Unit Testing**: Test individual methods with mocks (no hardware needed)
2. **Direct Testing**: Test with actual hardware/console without full Boardfarm setup
3. **Incremental Development**: Test each method as you implement it

### Testing Approaches

#### Approach 1: Direct Instantiation (No Boardfarm)

**Create a simple test script**:

```python
# test_rpiprplos_direct.py
from argparse import Namespace
from boardfarm3.devices.rpiprplos_cpe import RPiPrplOSHW, RPiPrplOSSW, RPiPrplOSCPE

# Minimal config for testing
config = {
    "conn_cmd": ["picocom -b 115200 /dev/ttyUSB0"],
    "connection_type": "local_cmd",
    "wan_iface": "eth1",
    "lan_iface": "br-lan",
    "mac": "00:e0:4c:1f:65:b8",  # Optional: USB dongle MAC
}

# Minimal cmdline_args
cmdline_args = Namespace(
    save_console_logs=None,
)

# Test hardware class
hw = RPiPrplOSHW(config, cmdline_args)
print(f"WAN interface: {hw.wan_iface}")
print(f"MAC address: {hw.mac_address}")  # Will read from eth1 if not in config

# Test software class (requires connected console)
hw.connect_to_consoles("test-device")
sw = RPiPrplOSSW(hw)
print(f"Version: {sw.version}")
print(f"CPE ID: {sw.cpe_id}")

# Test main device class
device = RPiPrplOSCPE(config, cmdline_args)
print(f"Device HW: {device.hw}")
print(f"Device SW: {device.sw}")
```

#### Approach 2: Unit Testing with Mocks

**Create unit tests** (`boardfarm/unittests/devices/test_rpiprplos_cpe.py`):

```python
# test_rpiprplos_cpe.py
import pytest
from unittest.mock import Mock, MagicMock, patch
from argparse import Namespace
from boardfarm3.devices.rpiprplos_cpe import RPiPrplOSHW, RPiPrplOSSW, RPiPrplOSCPE

class TestRPiPrplOSHW:
    """Unit tests for RPiPrplOSHW."""
    
    def test_init(self):
        """Test hardware class initialization."""
        config = {"wan_iface": "eth1"}
        cmdline_args = Namespace(save_console_logs=None)
        hw = RPiPrplOSHW(config, cmdline_args)
        assert hw.config == config
        assert hw._console is None
    
    def test_wan_iface(self):
        """Test WAN interface property."""
        config = {}
        cmdline_args = Namespace(save_console_logs=None)
        hw = RPiPrplOSHW(config, cmdline_args)
        assert hw.wan_iface == "eth1"
    
    @patch('boardfarm3.devices.rpiprplos_cpe.connection_factory')
    def test_connect_to_consoles(self, mock_connection_factory):
        """Test console connection."""
        mock_console = MagicMock()
        mock_connection_factory.return_value = mock_console
        
        config = {"conn_cmd": ["picocom -b 115200 /dev/ttyUSB0"], "connection_type": "local_cmd"}
        cmdline_args = Namespace(save_console_logs=None)
        hw = RPiPrplOSHW(config, cmdline_args)
        hw.connect_to_consoles("test-device")
        
        assert hw._console == mock_console
        mock_console.login_to_server.assert_called_once()
    
    @patch('boardfarm3.devices.rpiprplos_cpe.connection_factory')
    def test_mac_address_from_config(self, mock_connection_factory):
        """Test MAC address retrieval from config."""
        config = {"mac": "00:e0:4c:1f:65:b8"}
        cmdline_args = Namespace(save_console_logs=None)
        hw = RPiPrplOSHW(config, cmdline_args)
        assert hw.mac_address == "00:e0:4c:1f:65:b8"
    
    @patch('boardfarm3.devices.rpiprplos_cpe.connection_factory')
    def test_mac_address_from_interface(self, mock_connection_factory):
        """Test MAC address retrieval from eth1 interface."""
        mock_console = MagicMock()
        mock_console.execute_command.return_value = "00:e0:4c:1f:65:b8"
        mock_connection_factory.return_value = mock_console
        
        config = {"conn_cmd": ["picocom -b 115200 /dev/ttyUSB0"], "connection_type": "local_cmd"}
        cmdline_args = Namespace(save_console_logs=None)
        hw = RPiPrplOSHW(config, cmdline_args)
        hw.connect_to_consoles("test-device")
        
        mac = hw.mac_address
        assert mac == "00:e0:4c:1f:65:b8"
        mock_console.execute_command.assert_called()

class TestRPiPrplOSSW:
    """Unit tests for RPiPrplOSSW."""
    
    @patch('boardfarm3.devices.rpiprplos_cpe.connection_factory')
    def test_version(self, mock_connection_factory):
        """Test version property."""
        mock_console = MagicMock()
        mock_console.execute_command.return_value = "4.0.3"
        mock_connection_factory.return_value = mock_console
        
        config = {"conn_cmd": ["picocom -b 115200 /dev/ttyUSB0"], "connection_type": "local_cmd"}
        cmdline_args = Namespace(save_console_logs=None)
        hw = RPiPrplOSHW(config, cmdline_args)
        hw.connect_to_consoles("test-device")
        
        sw = RPiPrplOSSW(hw)
        version = sw.version
        assert version == "4.0.3"
        mock_console.execute_command.assert_called_with("cat /etc/build.prplos.version")
```

#### Approach 3: Integration Testing with Real Hardware

**Create integration test script** (can run standalone):

```python
# test_rpiprplos_integration.py
#!/usr/bin/env python3
"""Integration test for RPiPrplOSCPE - tests with actual hardware."""

from argparse import Namespace
from boardfarm3.devices.rpiprplos_cpe import RPiPrplOSCPE

def test_basic_functionality():
    """Test basic device functionality with real hardware."""
    config = {
        "conn_cmd": ["picocom -b 115200 /dev/ttyUSB0"],
        "connection_type": "local_cmd",
        "wan_iface": "eth1",
        "lan_iface": "br-lan",
    }
    
    cmdline_args = Namespace(save_console_logs=None)
    
    # Create device instance
    device = RPiPrplOSCPE(config, cmdline_args)
    
    # Test skip-boot (just connect console)
    device.boardfarm_skip_boot()
    
    # Test properties
    print(f"WAN interface: {device.hw.wan_iface}")
    print(f"MAC address: {device.hw.mac_address}")
    print(f"Serial number: {device.hw.serial_number}")
    print(f"Version: {device.sw.version}")
    print(f"CPE ID: {device.sw.cpe_id}")
    
    # Cleanup
    device.hw.disconnect_from_consoles()

if __name__ == "__main__":
    test_basic_functionality()
```

### Testing Checklist

#### Phase 1 Testing (Complete Implementation)

**Device Classes**:
- [ ] **Unit Tests**: Test `RPiPrplOSHW.__init__` with mock config
- [ ] **Unit Tests**: Test `wan_iface`, `mta_iface` properties
- [ ] **Unit Tests**: Test `mac_address` property (from config, from interface)
- [ ] **Unit Tests**: Test `serial_number` property (mock `/proc/cpuinfo`)
- [ ] **Unit Tests**: Test `RPiPrplOSSW` methods (version, cpe_id, etc.)
- [ ] **Direct Test**: Test `connect_to_consoles` with actual serial connection
- [ ] **Direct Test**: Test `mac_address` property (read from eth1)
- [ ] **Direct Test**: Test `serial_number` property (read from `/proc/cpuinfo`)
- [ ] **Direct Test**: Test `power_cycle` (soft reboot)
- [ ] **Direct Test**: Test `wait_for_hw_boot` (verify eth1 appears)

**Boot Sequence**:
- [ ] **Direct Test**: Test `boardfarm_device_boot` hook (full boot sequence)
- [ ] **Direct Test**: Test `wait_device_online` (network + TR-181)
- [ ] **Unit Tests**: Test `_is_tr181_ready` with mocked console

**ACS Integration**:
- [ ] **Direct Test**: Test `configure_management_server` (ACS configuration)
- [ ] **Direct Test**: Test `wait_for_acs_connection` (ACS registration)

**Boardfarm Integration (BDD Scenarios)**:
- [ ] **Integration**: Run BDD scenarios via pytest-bdd (`-k "DeviceInit"`)
- [ ] **Integration**: Test device registration (verify device appears in registry)
- [ ] **Integration**: Test device instantiation scenario (`UC-Device-Init-Main`)
- [ ] **Integration**: Test boot sequence scenario
- [ ] **Integration**: Test ACS registration scenario
- [ ] **Integration**: Test error scenarios (extensions)
- [ ] **Integration**: Verify testbed functions properly as system under test

#### Phase 2 Testing (Per Method - Incremental)

**For each new method added**:
- [ ] **Unit Test**: Test with mocks
- [ ] **Direct Test**: Test with hardware (no Boardfarm)
- [ ] **Integration Test**: Test via Boardfarm

### Benefits of Direct Testing

1. **Faster Development**: Test methods immediately without full Boardfarm setup
2. **Isolated Testing**: Test individual methods without dependencies
3. **Debugging**: Easier to debug issues in isolation
4. **CI/CD**: Can run unit tests in CI without hardware
5. **Documentation**: Test scripts serve as usage examples

### Running Tests

**⚠️ IMPORTANT**: All Python and pytest commands must be run in the virtual environment (`.venv-3.12`).

**Virtual Environment Location**: `~/projects/req-tst/boardfarm-bdd/.venv-3.12`

**Always activate before running tests**:
```bash
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate
```

# Unit tests (no hardware needed)
cd ../boardfarm
pytest unittests/devices/test_rpiprplos_cpe.py -v

# Direct integration test (requires hardware)
# (from boardfarm-bdd directory)
python test_rpiprplos_integration.py

# Full Boardfarm test (requires full setup)
# (from boardfarm-bdd directory)
pytest --skip-boot --board-name prplos-rpi-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_prplos_rpi.json \
  -v
```

---

## Detailed Testing Strategy for Incremental Development

### Overview: Three-Layer Testing Strategy

Given the incremental implementation plan, we use a **three-layer testing approach**:

1. **Unit Testing** (Layer 1): Test methods with mocks - fast, no hardware needed
2. **Direct Testing** (Layer 2): Test with actual hardware but without Boardfarm - quick iteration
3. **Integration Testing** (Layer 3): Test via Boardfarm - full testbed validation

**Workflow**: Implement → Unit Test → Direct Test → Integration Test → Next Method

### Iterative Development Workflow

**For each method you implement:**

```
┌─────────────────────────────────────────────────────────┐
│ 1. Implement Method                                      │
│    - Copy/adapt from reference implementation           │
│    - Add minimal implementation                         │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Unit Test (Layer 1)                                  │
│    - Test with mocks                                    │
│    - No hardware needed                                 │
│    - Fast feedback                                      │
│    cd ~/projects/req-tst/boardfarm-bdd                 │
│    source .venv-3.12/bin/activate                      │
│    cd ../boardfarm                                      │
│    pytest unittests/devices/test_*.py::test_method -v  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼ (if unit test passes)
┌─────────────────────────────────────────────────────────┐
│ 3. Direct Test (Layer 2)                                │
│    - Test with actual hardware                          │
│    - No Boardfarm needed                                │
│    - Quick iteration                                    │
│    cd ~/projects/req-tst/boardfarm-bdd                 │
│    source .venv-3.12/bin/activate                      │
│    python test_*_direct.py                              │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼ (if direct test passes)
┌─────────────────────────────────────────────────────────┐
│ 4. Integration Test (Layer 3)                           │
│    - Test via Boardfarm                                 │
│    - Full testbed                                       │
│    - Final validation                                   │
│    cd ~/projects/req-tst/boardfarm-bdd                 │
│    source .venv-3.12/bin/activate                      │
│    pytest --board-name prplos-rpi-1 ...                 │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼ (if integration test passes)
┌─────────────────────────────────────────────────────────┐
│ 5. Move to Next Method                                  │
│    - Repeat cycle                                       │
└─────────────────────────────────────────────────────────┘
```

### Phase 1 Testing: Step-by-Step Examples

#### Example 1: Testing Hardware Class Methods

**After implementing `mac_address` property:**

**Step 1: Unit Test (immediately)**
```python
# boardfarm/unittests/devices/test_rpiprplos_hw_unit.py
@patch('boardfarm3.devices.rpiprplos_cpe.connection_factory')
def test_mac_address_from_interface(self, mock_connection_factory):
    """Test MAC address from eth1 interface."""
    mock_console = MagicMock()
    mock_console.execute_command.return_value = "00:e0:4c:1f:65:b8"
    mock_connection_factory.return_value = mock_console
    
    config = {"conn_cmd": ["picocom -b 115200 /dev/ttyUSB0"], "connection_type": "local_cmd"}
    cmdline_args = Namespace(save_console_logs=None)
    hw = RPiPrplOSHW(config, cmdline_args)
    hw.connect_to_consoles("test-device")
    
    mac = hw.mac_address
    assert mac == "00:e0:4c:1f:65:b8"
```

**Step 2: Direct Test (with hardware)**
```python
# test_rpiprplos_hw_direct.py
def test_mac_address_direct():
    """Test MAC address with real hardware."""
    config = {
        "conn_cmd": ["picocom -b 115200 /dev/ttyUSB0"],
        "connection_type": "local_cmd",
    }
    cmdline_args = Namespace(save_console_logs=None)
    hw = RPiPrplOSHW(config, cmdline_args)
    
    try:
        hw.connect_to_consoles("test-device")
        mac = hw.mac_address
        print(f"✅ MAC address: {mac}")
        assert len(mac) == 17, "MAC should be 17 characters"
    finally:
        hw.disconnect_from_consoles()
```

**Run**: 
```bash
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate
python test_rpiprplos_hw_direct.py
```

**Step 3: Integration Test (via Boardfarm)**
```python
# boardfarm-bdd/tests/integration/test_rpiprplos_integration.py
def test_mac_address_via_boardfarm(device_manager):
    """Test MAC address via Boardfarm."""
    cpe = device_manager.get_device_by_type(RPiPrplOSCPE)
    mac = cpe.hw.mac_address
    assert len(mac) == 17
```

**Run**: 
```bash
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate
pytest --board-name prplos-rpi-1 -k test_mac_address_via_boardfarm -v
```

#### Example 2: Testing Software Class Methods

**After implementing `wait_device_online`:**

**Step 1: Unit Test**
```python
@patch('boardfarm3.devices.rpiprplos_cpe.sleep')
def test_wait_device_online(self, mock_sleep, mock_hw):
    """Test wait_device_online."""
    call_count = [0]
    def mock_is_online():
        call_count[0] += 1
        return call_count[0] >= 2
    
    sw = RPiPrplOSSW(mock_hw)
    sw.is_online = mock_is_online
    sw._is_tr181_ready = lambda: True
    
    sw.wait_device_online()  # Should not raise
    assert call_count[0] >= 2
```

**Step 2: Direct Test**
```python
def test_wait_device_online_direct():
    """Test wait_device_online with real hardware."""
    hw = RPiPrplOSHW(config, cmdline_args)
    hw.connect_to_consoles("test-device")
    sw = RPiPrplOSSW(hw)
    
    # Device should already be online, but test the method
    sw.wait_device_online()  # Should complete quickly
    assert sw.is_online()
```

**Step 3: Integration Test**
```python
def test_wait_device_online_via_boardfarm(device_manager):
    """Test wait_device_online via Boardfarm."""
    cpe = device_manager.get_device_by_type(RPiPrplOSCPE)
    cpe.sw.wait_device_online()
    assert cpe.sw.is_online()
```

#### Example 3: Testing Boot Sequence

**After implementing `boardfarm_device_boot`:**

**Step 1: Unit Test (mocked sequence)**
```python
@patch('boardfarm3.devices.rpiprplos_cpe.connection_factory')
@patch('boardfarm3.devices.rpiprplos_cpe.sleep')
def test_boot_sequence(self, mock_sleep, mock_connection_factory, device):
    """Test boot sequence."""
    mock_console = MagicMock()
    mock_connection_factory.return_value = mock_console
    
    device_manager = Mock(spec=DeviceManager)
    device_manager.get_device_by_type.return_value = None
    
    # Mock methods
    device.hw.power_cycle = MagicMock()
    device.hw.wait_for_hw_boot = MagicMock()
    device.sw.wait_device_online = MagicMock()
    device.sw.configure_management_server = MagicMock()
    
    device.boardfarm_device_boot(device_manager)
    
    # Verify sequence
    mock_console.login_to_server.assert_called_once()
    device.hw.power_cycle.assert_called_once()
    device.hw.wait_for_hw_boot.assert_called_once()
    device.sw.wait_device_online.assert_called_once()
```

**Step 2: Direct Test (with hardware, no ACS)**
```python
def test_boot_sequence_direct():
    """Test boot sequence with real hardware."""
    device = RPiPrplOSCPE(config, cmdline_args)
    device_manager = Mock(spec=DeviceManager)
    device_manager.get_device_by_type.return_value = None  # No provisioner, no ACS
    
    try:
        device.boardfarm_device_boot(device_manager)
        assert device.sw.is_online()
    finally:
        device.hw.disconnect_from_consoles()
```

**Run**:
```bash
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate
python test_rpiprplos_boot_direct.py
```

**Step 3: Integration Test (full Boardfarm)**
```bash
# Activate virtual environment first
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate

# Test via Boardfarm
pytest --board-name prplos-rpi-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_prplos_rpi.json \
  -k "test_boot" -v
```

### Iterating with Boardfarm

**Once Phase 1 is complete and device is registered:**

#### Iteration Pattern for New Methods

**Scenario**: Adding `get_interface_ip()` method after Phase 1.

```python
# 1. Implement method
def get_interface_ip(self, interface: str) -> str:
    """Get IP address of interface."""
    console = self._get_console("default_shell")
    return console.execute_command(
        f"ip addr show {interface} | grep 'inet ' | awk '{{print $2}}' | cut -d/ -f1"
    ).strip()

# 2. Unit test (immediately)
def test_get_interface_ip(mock_hw):
    mock_hw._console.execute_command.return_value = "10.1.1.100"
    sw = RPiPrplOSSW(mock_hw)
    ip = sw.get_interface_ip("eth1")
    assert ip == "10.1.1.100"

# 3. Direct test (with hardware)
def test_get_interface_ip_direct():
    hw = RPiPrplOSHW(config, cmdline_args)
    hw.connect_to_consoles("test")
    sw = RPiPrplOSSW(hw)
    ip = sw.get_interface_ip("eth1")
    assert ip.startswith("10.1.1.")
    hw.disconnect_from_consoles()

# 4. Integration test (via Boardfarm)
def test_get_interface_ip_via_boardfarm(device_manager):
    cpe = device_manager.get_device_by_type(RPiPrplOSCPE)
    ip = cpe.sw.get_interface_ip("eth1")
    assert ip.startswith("10.1.1.")
```

**Run**:
```bash
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate
pytest --board-name prplos-rpi-1 -k test_get_interface_ip_via_boardfarm -v
```

#### Boardfarm Testing Workflow

**For testing via Boardfarm:**

1. **Skip-Boot Testing** (fast iteration):
```bash
# Activate virtual environment first
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate

# Test without boot sequence (device already running)
pytest --skip-boot \
  --board-name prplos-rpi-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_prplos_rpi.json \
  -k "test_specific_method" -v
```

2. **Full Boot Testing** (complete validation):
```bash
# Activate virtual environment first
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate

# Test with full boot sequence
pytest \
  --board-name prplos-rpi-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_prplos_rpi.json \
  -k "test_boot_sequence" -v
```

3. **Specific Test Development**:
```python
# boardfarm-bdd/tests/integration/test_rpiprplos_methods.py
def test_new_method_via_boardfarm(device_manager):
    """Test new method via Boardfarm."""
    cpe = device_manager.get_device_by_type(RPiPrplOSCPE)
    result = cpe.sw.new_method()
    assert result == expected_value
```

### Testing Checklist for Phase 1

#### Hardware Class
- [ ] **Unit**: `__init__`, `config`, `wan_iface`, `mta_iface`
- [ ] **Unit**: `connect_to_consoles`, `get_console`, `disconnect_from_consoles`
- [ ] **Unit**: `mac_address` (config, interface)
- [ ] **Unit**: `serial_number`
- [ ] **Direct**: Console connection
- [ ] **Direct**: MAC address from eth1
- [ ] **Direct**: Serial number
- [ ] **Direct**: `power_cycle`
- [ ] **Direct**: `wait_for_hw_boot`
- [ ] **Integration**: All via Boardfarm

#### Software Class
- [ ] **Unit**: `__init__`, `version`, `cpe_id`, `tr69_cpe_id`
- [ ] **Unit**: `lan_iface`, `erouter_iface`
- [ ] **Unit**: `wait_device_online` (mocked)
- [ ] **Unit**: `configure_management_server` (mocked)
- [ ] **Unit**: `wait_for_acs_connection` (mocked)
- [ ] **Direct**: Version, CPE ID
- [ ] **Direct**: `wait_device_online` (real hardware)
- [ ] **Direct**: `configure_management_server` (real hardware)
- [ ] **Direct**: `wait_for_acs_connection` (real ACS)
- [ ] **Integration**: All via Boardfarm

#### Boot Sequence
- [ ] **Unit**: `boardfarm_device_boot` (mocked sequence)
- [ ] **Direct**: Full boot (no Boardfarm)
- [ ] **Integration**: Boot via Boardfarm
- [ ] **Integration**: Verify ACS registration

### Benefits of This Approach

1. **Fast Feedback Loop**: Unit tests run instantly, catch issues immediately
2. **Rapid Iteration**: Direct tests allow quick development without Boardfarm overhead
3. **Confidence Building**: Each layer validates the previous one
4. **Easy Debugging**: Problems isolated to specific methods/layers
5. **Documentation**: Test code serves as usage examples
6. **CI/CD Ready**: Unit tests can run in CI without hardware
7. **Incremental Validation**: Test each method before moving to the next

---

## Implementation Order

### Iteration 1: Complete Phase 1 (Device Implementation + Registration + Config)

**Goal**: Get Boardfarm to successfully initialize the CPE device.

**Steps**:
1. Create file `rpiprplos_cpe.py`
2. Implement `RPiPrplOSHW` critical methods (console, MAC, serial, boot)
3. Implement `RPiPrplOSSW` critical methods (cpe_id, wait_online, configure_ACS, wait_ACS)
4. Implement `RPiPrplOSCPE` with `boardfarm_device_boot` hook
5. Add minimal stubs for abstract requirements
6. Register device class in `boardfarm3/plugins/core.py`
7. Create configuration file `boardfarm_config_prplos_rpi.json`
8. **Test**: Verify Boardfarm can instantiate device (`--skip-boot`)
9. **Test**: Verify Boardfarm can boot device (`boardfarm_device_boot`)
10. **Test**: Verify device registers with ACS

**Success**: Boardfarm can initialize CPE and device registers with ACS ✅

### Iteration 2: Incremental Method Addition (Phase 2)

**Goal**: Add methods incrementally as testbed requirements emerge.

**Workflow for Each New Method**:

**Implementation**:
1. Implement method in device class

**Testing (BDD Structure)**:
2. Add scenario to feature file (if needed)
3. Add/update step definitions
4. **Unit Test**: Test step definition logic with mocks
5. **Direct Test**: Test device class method with hardware
6. **Integration Test**: Run BDD scenario via pytest-bdd
7. Move to next method

**Examples**:
- `boardfarm_device_configure` hook → Add scenario + steps
- Additional network operations → Add scenario + steps
- Factory reset → Add scenario + steps
- Other methods as needed

---

## Key Implementation Details

### Serial Console Connection

**Pattern** (from `RPiRDKBHW`):
```python
self._console = connection_factory(
    connection_type=str(self._config.get("connection_type")),
    connection_name=f"{device_name}.console",
    conn_command=self._config["conn_cmd"][0],
    save_console_logs=self._cmdline_args.save_console_logs,
    shell_prompt=self._shell_prompt,
)
self._console.login_to_server()
```

**Shell Prompt**: `[r"/[a-zA-Z]* #"]` (prplOS OpenWrt prompt)

### MAC Address Retrieval

**Strategy** (from `PrplOSx86HW`):
1. Try config first: `self._config.get("mac")`
2. Try `/var/etc/environment`: `grep HWMACADDRESS`
3. Fallback to `/sys/class/net/eth1/address`

### Serial Number Retrieval

**Strategy** (from `RPiRDKBHW`):
```python
self._console.execute_command("grep Serial /proc/cpuinfo |awk '{print $3}'")
```

### TR-181 Access

**Pattern** (from `PrplOSSW`):
- Use `ubus-cli` interactive shell
- Commands: `Device.ManagementServer.URL="..."`, `Device.ManagementServer.EnableCWMP=1`
- Exit with `exit` command

### Power Cycle

**Strategy**: Soft reboot via console (like `PrplOSx86HW`):
```python
self._console.execute_command("reboot -f -d 5")
sleep(10)
self.disconnect_from_consoles()
self.connect_to_consoles("board")
```

---

## Success Criteria

### Phase 1 Complete ✅
- [ ] Device classes implemented (HW, SW, CPE)
- [ ] Device registered in Boardfarm (`boardfarm3/plugins/core.py`)
- [ ] Configuration file created (`boardfarm_config_prplos_rpi.json`)
- [ ] Device can be instantiated via Boardfarm (`--skip-boot` works)
- [ ] Serial console connection works
- [ ] MAC address and serial number can be retrieved
- [ ] Full boot sequence completes successfully (`boardfarm_device_boot` works)
- [ ] Device comes online (network + TR-181)
- [ ] ACS can be configured via TR-181
- [ ] CPE registers with ACS
- [ ] Device is accessible via ACS (can query parameters)

**Phase 1 Success**: Boardfarm can initialize CPE and device registers with ACS ✅

### Phase 2 Complete ✅ (Per Method)
- [ ] Method implemented
- [ ] Unit test passes
- [ ] Direct test passes (with hardware)
- [ ] Integration test passes (via Boardfarm)

---

## Estimated Timeline

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1 | Complete implementation (HW + SW + CPE + Registration + Config) | 6-8 hours |
| **Testing** | Phase 1 validation (unit + direct + integration) | 2-3 hours |
| **Total Phase 1** | | **8-11 hours** |
| Phase 2 | Incremental method addition | As needed (per method) |

---

## Notes

1. **Architecture Pattern**: Each device type has its own HW and SW classes in the device file:
   - `PrplOSSW` in `prplos_cpe.py` (containerized prplOS)
   - `RPiRDKBSW` in `rpirdkb_cpe.py` (RPi RDKB)
   - `RPiPrplOSSW` in `rpiprplos_cpe.py` (RPi prplOS) ← **We create this**
   - All inherit from `CPESwLibraries` (library component in `boardfarm3/lib/cpe_sw.py`)

2. **Code Reuse Strategy**: Copy/adapt methods from `PrplOSSW` since the software stack is identical, but keep as separate class for clarity and potential future divergence.

3. **Incremental Approach**: Implement and test methods one by one to catch issues early.

3. **Reference Code**: Leverage existing implementations (`PrplDockerCPE`, `RPiRDKBCPE`) but adapt for prplOS-specific differences.

4. **TR-181 Access**: prplOS uses `ubus-cli` (like containerized version), not `dmcli` (like RDKB).

5. **Power Cycle**: Use soft reboot via console (no PDU needed for RPi4).

6. **Interface Names**: 
   - WAN: `eth1` (USB-Ethernet dongle)
   - LAN: `br-lan` (bridge with eth0)

7. **Testing**: Test with actual hardware early to catch hardware-specific issues.

8. **Error Handling**: Implement proper error handling and logging from the start.

---

## Next Steps

1. **Review this plan** and adjust priorities/order as needed
2. **Start with Phase 1**: Implement minimal methods for testbed instantiation
3. **Test incrementally**: Verify each phase before moving to the next
4. **Document findings**: Note any deviations from plan or unexpected issues

---

**Document End**

