# Robot Framework Keyword Reference

This document provides a reference for keywords available in boardfarm-bdd Robot Framework tests.

## Libraries Overview

| Library | Purpose | Import |
|---------|---------|--------|
| `BoardfarmLibrary` | Device access, configuration | `Library    robotframework_boardfarm.BoardfarmLibrary` |
| `acs_keywords.py` | ACS operations | `Library    ../libraries/acs_keywords.py` |
| `cpe_keywords.py` | CPE operations | `Library    ../libraries/cpe_keywords.py` |
| `voice_keywords.py` | Voice/SIP operations | `Library    ../libraries/voice_keywords.py` |
| `background_keywords.py` | Background/setup operations | `Library    ../libraries/background_keywords.py` |
| `operator_keywords.py` | Operator actions | `Library    ../libraries/operator_keywords.py` |

**Architecture**: All keyword libraries delegate to `boardfarm3.use_cases`, ensuring consistency with pytest-bdd tests.

---

## BoardfarmLibrary Keywords

Provided by `robotframework-boardfarm`, these keywords handle device access and testbed configuration.

### Device Access

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `Get Device By Type` | `device_type`, `index=0` | Get device instance by type |
| `Get Devices By Type` | `device_type` | Get all devices of a type |
| `Get Device Manager` | | Get DeviceManager instance |
| `Get Boardfarm Config` | | Get testbed configuration |

#### Examples

```robot
# Get primary CPE
${cpe}=    Get Device By Type    CPE

# Get second SIP phone (index 1)
${phone}=    Get Device By Type    SIPPhone    index=1

# Get ACS device
${acs}=    Get Device By Type    ACS
```

### Test Utilities

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `Log Step` | `message` | Log a test step |
| `Set Test Context` | `key`, `value` | Store value in context |
| `Get Test Context` | `key`, `default=None` | Retrieve value from context |
| `Require Environment` | `requirement` | Assert environment requirement |

---

## Keyword Libraries (robot/libraries/)

These Python keyword libraries mirror the pytest-bdd step definitions and delegate to `boardfarm3.use_cases`.

### acs_keywords.py - ACS Operations

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `The CPE is online via ACS` | `acs`, `cpe` | Verify CPE is online via ACS |
| `The ACS initiates a remote reboot of the CPE` | `acs`, `cpe` | Initiate CPE reboot via ACS |
| `Get ACS Parameter Value` | `acs`, `cpe`, `parameter` | Get TR-069 parameter value |
| `Set ACS Parameter Value` | `acs`, `cpe`, `parameter`, `value` | Set TR-069 parameter value |
| `Wait For Boot Inform` | `acs`, `cpe`, `since`, `timeout` | Wait for boot Inform message |
| `Get CPE Device ID` | `acs`, `cpe` | Get device identifier |

#### Examples

```robot
*** Test Cases ***
ACS Parameter Operations
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    
    # Verify online
    The CPE Is Online Via ACS    ${acs}    ${cpe}
    
    # Get parameter
    ${version}=    Get ACS Parameter Value    ${acs}    ${cpe}
    ...    Device.DeviceInfo.SoftwareVersion
    Log    Version: ${version}
    
    # Set parameter
    Set ACS Parameter Value    ${acs}    ${cpe}
    ...    Device.Users.User.1.Password    newpassword
```

### cpe_keywords.py - CPE Operations

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `The CPE is rebooted` | `cpe` | Verify CPE has rebooted |
| `The CPE should have rebooted` | `cpe` | Assert CPE rebooted (checks uptime) |
| `Record CPE uptime` | `cpe` | Record current uptime for later comparison |
| `The CPE uptime should be less than before` | `cpe` | Verify uptime reset |
| `Get CPE Performance Metrics` | `cpe` | Get CPU, memory, uptime |

#### Examples

```robot
*** Test Cases ***
CPE Status Check
    ${cpe}=    Get Device By Type    CPE
    
    # Record uptime before reboot
    ${initial_uptime}=    Record CPE Uptime    ${cpe}
    
    # ... reboot happens ...
    
    # Verify reboot
    The CPE Should Have Rebooted    ${cpe}
```

### voice_keywords.py - Voice/SIP Operations

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `User makes a call to another user` | `caller`, `callee` | Initiate call |
| `The called party answers` | `phone` | Answer incoming call |
| `The calling party hangs up` | `phone` | Disconnect call |
| `Voice call is connected` | `phone_a`, `phone_b` | Verify call connected |
| `Initialize voice phones` | `phone_a`, `phone_b` | Setup phones for test |
| `Cleanup voice phones` | `phone_a`, `phone_b` | Cleanup phones after test |

#### Examples

```robot
*** Test Cases ***
Voice Call Test
    ${phone_a}=    Get Device By Type    SIPPhone    index=0
    ${phone_b}=    Get Device By Type    SIPPhone    index=1
    
    # Setup
    Initialize Voice Phones    ${phone_a}    ${phone_b}
    
    # Make call
    User Makes A Call To Another User    ${phone_a}    ${phone_b}
    
    # Answer
    The Called Party Answers    ${phone_b}
    
    # Verify
    Voice Call Is Connected    ${phone_a}    ${phone_b}
    
    # Hangup
    The Calling Party Hangs Up    ${phone_a}
    
    [Teardown]    Cleanup Voice Phones    ${phone_a}    ${phone_b}
```

### background_keywords.py - Background/Setup Operations

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `A CPE is online and fully provisioned` | `acs`, `cpe` | Verify CPE preconditions |
| `The testbed is ready` | | Verify testbed state |

### operator_keywords.py - Operator Actions

| Keyword | Arguments | Description |
|---------|-----------|-------------|
| `The operator initiates a reboot task on the ACS for the CPE` | `acs`, `cpe` | Operator triggers reboot |
| `Use case succeeds and all success guarantees are met` | `acs`, `cpe` | Verify success guarantees |

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
bfrobot ... --include smoke robot/tests/

# Run voice tests
bfrobot ... --include voice robot/tests/

# Exclude slow tests
bfrobot ... --exclude slow robot/tests/

# Combine tags
bfrobot ... --include "smoke AND reboot" robot/tests/
```

---

## Creating New Keywords

When adding new keywords, follow this pattern:

```python
# robot/libraries/my_keywords.py
from robot.api.deco import keyword
from boardfarm3.use_cases import my_module as my_use_cases

class MyKeywords:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("The action is performed")
    def perform_action(self, device, parameter):
        """Perform the action.
        
        Maps to scenario step: "When the action is performed"
        """
        return my_use_cases.perform_action(device, parameter)
```

Key guidelines:
1. Use `@keyword` decorator with scenario step text
2. Delegate to `boardfarm3.use_cases` functions
3. Mirror the corresponding `tests/step_defs/` file structure
4. Add docstring describing the keyword

---

## Further Reading

- [Getting Started Guide](getting_started.md)
- [Keyword Libraries Documentation](../../robot/libraries/README.md)
- [Use Case Architecture](../use_case_architecture.md)
- [robotframework-boardfarm README](../../../robotframework-boardfarm/README.md)
