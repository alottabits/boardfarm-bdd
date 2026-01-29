# Robot Framework Keyword Reference

This document provides a reference for keywords available in boardfarm-bdd Robot Framework tests.

## Libraries Overview

| Library | Purpose | Import |
|---------|---------|--------|
| `BoardfarmLibrary` | Device access, configuration | `Library    BoardfarmLibrary` |
| `UseCaseLibrary` | High-level test operations | `Library    UseCaseLibrary` |

**Recommendation**: Use `UseCaseLibrary` for test operations. It provides the same functionality as `boardfarm3.use_cases`, ensuring consistency with pytest-bdd tests.

---

## BoardfarmLibrary Keywords

### Device Access

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `Get Device By Type` | `device_type`, `index=0` | Get device instance by type |
| `Get All Devices` | | Get all devices in testbed |
| `Get Boardfarm Config` | | Get testbed configuration |

#### Examples

```robot
# Get primary CPE
${cpe}=    Get Device By Type    CPE

# Get second SIP phone (index 1)
${phone}=    Get Device By Type    SIPPhone    index=1

# Get all devices
${devices}=    Get All Devices
```

### Logging

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `Log Step` | `message` | Log a test step |
| `Log Info` | `message` | Log informational message |

---

## UseCaseLibrary Keywords

UseCaseLibrary dynamically exposes `boardfarm3.use_cases` functions as Robot keywords.

### Naming Convention

| Use Case Module | Function | Robot Keyword |
|-----------------|----------|---------------|
| `acs` | `get_parameter_value()` | `Acs Get Parameter Value` |
| `cpe` | `get_cpu_usage()` | `Cpe Get Cpu Usage` |
| `voice` | `call_a_phone()` | `Voice Call A Phone` |

### ACS Keywords

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `Acs Get Parameter Value` | `acs`, `cpe`, `parameter` | Get TR-069 parameter value |
| `Acs Set Parameter Value` | `acs`, `cpe`, `parameter`, `value` | Set TR-069 parameter value |
| `Acs Get Multiple Parameters` | `acs`, `cpe`, `parameters` | Get multiple parameters |
| `Acs Is Cpe Online` | `acs`, `cpe` | Check if CPE is online |
| `Acs Is Cpe Registered` | `acs`, `cpe`, `timeout=60` | Check if CPE is registered |
| `Acs Initiate Reboot` | `acs`, `cpe` | Initiate CPE reboot via ACS |
| `Acs Wait For Inform Message` | `acs`, `cpe`, `since`, `timeout=120` | Wait for Inform message |
| `Acs Wait For Reboot Rpc` | `acs`, `cpe`, `since`, `timeout=90` | Wait for Reboot RPC |
| `Acs Wait For Boot Inform` | `acs`, `cpe`, `since`, `timeout=240` | Wait for boot Inform |
| `Acs Get Device Id` | `acs`, `cpe` | Get device identifier |

#### Examples

```robot
*** Test Cases ***
ACS Parameter Operations
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    
    # Get parameter
    ${version}=    Acs Get Parameter Value    ${acs}    ${cpe}
    ...    Device.DeviceInfo.SoftwareVersion
    Log    Version: ${version}
    
    # Set parameter
    Acs Set Parameter Value    ${acs}    ${cpe}
    ...    Device.Users.User.1.Password    newpassword
    
    # Check online status
    ${online}=    Acs Is Cpe Online    ${acs}    ${cpe}
    Should Be True    ${online}
```

### CPE Keywords

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `Cpe Get Cpu Usage` | `cpe` | Get current CPU usage |
| `Cpe Get Memory Usage` | `cpe` | Get memory usage |
| `Cpe Get Seconds Uptime` | `cpe` | Get uptime in seconds |
| `Cpe Is Device Online` | `cpe`, `timeout=120` | Check if device is online |
| `Cpe Is Console Connected` | `cpe` | Check console connection |
| `Cpe Execute Command` | `cpe`, `command` | Execute console command |
| `Cpe Factory Reset` | `cpe` | Factory reset the CPE |
| `Cpe Boot Device` | `cpe` | Boot the device |
| `Cpe Refresh Console Connection` | `cpe` | Refresh console connection |
| `Cpe Stop Tr069 Client` | `cpe` | Stop TR-069 client |
| `Cpe Start Tr069 Client` | `cpe` | Start TR-069 client |

#### Examples

```robot
*** Test Cases ***
CPE Status Check
    ${cpe}=    Get Device By Type    CPE
    
    # Get performance metrics
    ${cpu}=    Cpe Get Cpu Usage    ${cpe}
    ${memory}=    Cpe Get Memory Usage    ${cpe}
    ${uptime}=    Cpe Get Seconds Uptime    ${cpe}
    
    Log    CPU: ${cpu}%, Memory: ${memory}%, Uptime: ${uptime}s
    
    # Verify thresholds
    Should Be True    ${cpu} < 90    CPU usage too high
    Should Be True    ${memory} < 85    Memory usage too high
```

### Voice Keywords

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `Voice Initialize Phone` | `phone` | Initialize SIP phone |
| `Voice Shutdown Phone` | `phone` | Shutdown SIP phone |
| `Voice Register Phone` | `phone`, `number=None` | Register phone with SIP server |
| `Voice Unregister Phone` | `phone` | Unregister phone |
| `Voice Is Phone Registered` | `phone` | Check registration status |
| `Voice Is Phone Idle` | `phone` | Check if phone is idle |
| `Voice Call A Phone` | `caller`, `callee` | Initiate call |
| `Voice Answer A Call` | `phone` | Answer incoming call |
| `Voice Disconnect The Call` | `phone` | Hang up call |
| `Voice Reject Call` | `phone` | Reject incoming call |
| `Voice Is Call Ringing` | `phone`, `timeout=30` | Check if call is ringing |
| `Voice Is Call Connected` | `phone` | Check if call is connected |
| `Voice Is Media Established` | `phone_a`, `phone_b` | Check RTP media |
| `Voice Dial Number` | `phone`, `number` | Dial a number |
| `Voice Get Last Sip Response` | `phone` | Get last SIP response |

#### Examples

```robot
*** Test Cases ***
Voice Call Test
    ${phone_a}=    Get Device By Type    SIPPhone    index=0
    ${phone_b}=    Get Device By Type    SIPPhone    index=1
    
    # Setup phones
    Voice Initialize Phone    ${phone_a}
    Voice Initialize Phone    ${phone_b}
    Voice Register Phone    ${phone_a}    number=1000
    Voice Register Phone    ${phone_b}    number=2000
    
    # Make call
    Voice Call A Phone    ${phone_a}    ${phone_b}
    
    # Verify ringing
    ${ringing}=    Voice Is Call Ringing    ${phone_b}
    Should Be True    ${ringing}
    
    # Answer and verify connected
    Voice Answer A Call    ${phone_b}
    ${connected_a}=    Voice Is Call Connected    ${phone_a}
    ${connected_b}=    Voice Is Call Connected    ${phone_b}
    Should Be True    ${connected_a}
    Should Be True    ${connected_b}
    
    # Hang up
    Voice Disconnect The Call    ${phone_a}
    
    [Teardown]    Cleanup Voice Test    ${phone_a}    ${phone_b}
```

### Networking Keywords

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `Networking Ping` | `source`, `target`, `count=4` | Ping from source to target |
| `Networking Get Ip Address` | `device`, `interface` | Get IP address |
| `Networking Check Connectivity` | `source`, `target` | Verify connectivity |

### Device Getters Keywords

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `Device Getters Get Acs` | | Get ACS device |
| `Device Getters Get Cpe` | | Get CPE device |
| `Device Getters Get Lan` | | Get LAN device |

---

## Resource Files

### common.resource

Common setup/teardown keywords:

| Keyword | Description |
|---------|-------------|
| `Setup Testbed Connection` | Suite setup - establish connection |
| `Teardown Testbed Connection` | Suite teardown - cleanup |
| `Cleanup After Test` | Test teardown - cleanup artifacts |
| `Verify CPE Is Online` | Verify CPE is online |
| `Wait Until CPE Is Online` | Wait for CPE to come online |
| `Get TR069 Parameter` | Get TR-069 parameter (shortcut) |
| `Set TR069 Parameter` | Set TR-069 parameter (shortcut) |

### variables.resource

Common variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `${DEFAULT_TIMEOUT}` | 30 | Default timeout (seconds) |
| `${REBOOT_TIMEOUT}` | 240 | Reboot timeout (seconds) |
| `${CALL_TIMEOUT}` | 30 | Call setup timeout (seconds) |
| `${PARAM_SOFTWARE_VERSION}` | `Device.DeviceInfo.SoftwareVersion` | SW version path |

### cleanup.resource

Cleanup keywords:

| Keyword | Description |
|---------|-------------|
| `Cleanup SIP Phones` | Clean up all SIP phones |
| `Cleanup ACS GUI Session` | Logout from ACS GUI |
| `Refresh CPE Console Connection` | Refresh console after reboot |
| `Full Testbed Cleanup` | Comprehensive cleanup |

### voice.resource

Voice-specific keywords:

| Keyword | Description |
|---------|-------------|
| `Setup Voice Test Environment` | Initialize voice test |
| `Teardown Voice Test Environment` | Cleanup voice test |
| `Register Phone On LAN Side` | Register LAN phone |
| `Register Phone On WAN Side` | Register WAN phone |
| `Complete Successful Call` | Execute full call flow |

---

## Tags Reference

Common tags used in test suites:

| Tag | Description |
|-----|-------------|
| `smoke` | Quick verification tests |
| `reboot` | Tests involving CPE reboot |
| `voice` | Voice/SIP call tests |
| `gui` | ACS GUI tests |
| `UC-12347` | Use case identifier |
| `main-scenario` | Main success scenario |
| `extension` | Extension/error scenario |

### Filtering by Tags

```bash
# Run smoke tests only
robot --include smoke robot/tests/

# Run voice tests
robot --include voice robot/tests/

# Exclude slow tests
robot --exclude slow robot/tests/

# Combine tags
robot --include "smoke AND reboot" robot/tests/
```

---

## Further Reading

- [Getting Started Guide](getting_started.md)
- [Use Case Architecture](../use_case_architecture.md)
- [robotframework-boardfarm README](../../../robotframework-boardfarm/README.md)
