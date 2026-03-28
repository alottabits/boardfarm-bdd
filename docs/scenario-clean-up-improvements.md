# Scenario Cleanup Improvements

> **Status**: Complete (All phases implemented)  
> **Created**: March 26, 2026  
> **Updated**: March 27, 2026  
> **Audience**: Test Developers, Framework Contributors

---

## Problem

The current cleanup approach in `tests/conftest.py` relies on autouse fixtures that inspect `bf_context` after each scenario to determine what needs to be undone:

1. ~~`cleanup_cpe_config_after_scenario`~~ — **removed** (migrated to yield-based step teardown; console refresh extracted to `refresh_cpe_console_after_scenario`)
2. ~~`cleanup_sip_phones_after_scenario`~~ — **removed** (migrated to yield-based step teardown)
3. ~~`cleanup_sdwan_impairments_after_scenario`~~ — **removed** (migrated to yield-based step teardown)
4. ~~`cleanup_traffic_generators_after_scenario`~~ — **removed** (migrated to yield-based step teardown)

This design has several weaknesses:

| Weakness | Description |
|----------|-------------|
| **Coupling** | Steps must store undo data in `bf_context` with a specific structure that the conftest cleanup understands |
| **Fragility** | If a step forgets to populate `bf_context.original_config`, cleanup silently skips |
| **Ordering** | Autouse fixtures run in a fixed order, not necessarily the reverse of what the scenario actually did |
| **Complexity** | The CPE config cleanup fixture embeds ~150 lines of business logic (SPV iteration, password special-casing, console reconnection) |
| **Redundancy** | Cleanup fixtures must guard every attribute with `hasattr(bf_context, ...)` or `getattr(..., None)` |
| **Scope** | Cleanup runs for *every* scenario, even ones that didn't touch the relevant subsystem |

---

## Solution: Yield-Based Step Teardown

pytest-bdd step definitions are **pytest fixtures under the hood**. A step function that `yield`s splits into setup (before yield) and teardown (after yield). Teardown runs automatically when the scenario ends — even on failure — in **LIFO (reverse) order**.

This means each step can clean up after itself, eliminating the need for centralized cleanup fixtures and `bf_context`-based undo tracking.

### Core Pattern

```python
@given("some precondition is established")
def establish_precondition(device):
    # Setup
    original_state = device.get_state()
    device.change_state("new_value")

    yield  # scenario steps execute

    # Teardown — runs automatically in reverse order
    device.restore_state(original_state)
```

### With Context Managers

Existing context managers compose naturally with yield:

```python
from contextlib import contextmanager

@contextmanager
def impaired_wan_link(tc, profile):
    tc_use_cases.set_impairment_profile(tc, profile)
    yield
    tc_use_cases.clear_impairment(tc)


@when('"{wan_link}" experiences a complete link failure')
def wan_link_complete_failure(bf_context, wan_link):
    tc = _get_tc_for_wan(bf_context, wan_link)
    profile = ImpairmentProfile(loss_percent=100.0, ...)

    with impaired_wan_link(tc, profile):
        yield  # scenario continues; impairment cleared on exit
```

---

## Execution Order

Given a scenario:

```gherkin
Given status A is set
When action B is performed
Then result C is verified
```

With yield-based steps, execution flows as a nested stack:

```
1.  Given setup    — "status A is set"
2.    When setup   — "action B is performed"
3.      Then       — "result C is verified" (no yield, completes)
4.    When teardown — undo action B
5.  Given teardown  — undo status A
```

Teardown unwinds in **reverse order**, matching the natural expectation that the last thing set up is the first thing torn down.

---

## Migration Examples

### CPE Password Change — IMPLEMENTED

**Before** (step stores data, conftest interprets it):

```python
# background_steps.py — setup
@given('the user has set the CPE GUI password to "{password}"')
def user_sets_cpe_gui_password(acs, cpe, bf_context, password):
    original_password = acs_use_cases.get_parameter_value(acs, cpe, param)
    acs_use_cases.set_parameter_value(acs, cpe, param, password)

    # Store for conftest cleanup to find later
    bf_context.original_config["users"]["items"][idx]["Password"] = {
        "gpv_param": param,
        "value": original_password,
    }

# conftest.py — cleanup (~150 lines)
@pytest.fixture(scope="function", autouse=True)
def cleanup_cpe_config_after_scenario(acs, cpe, bf_context):
    yield
    # ... iterate bf_context.original_config ...
    # ... special-case passwords ...
    # ... call acs.SPV() directly ...
```

**After** (step cleans up after itself):

```python
@given('the user has set the CPE GUI password to "{password}"')
def user_sets_cpe_gui_password(acs, cpe, bf_context, password):
    admin_idx = discover_admin_user_index(acs, cpe)
    param = f"Device.Users.User.{admin_idx}.Password"

    acs_use_cases.set_parameter_value(acs, cpe, param, password)
    print(f"✓ CPE GUI password set for user {admin_idx}")

    yield

    acs_use_cases.set_parameter_value(acs, cpe, param, "admin")
    print("✓ CPE GUI password restored to default")
```

### SIP Phone Registration & Calls — IMPLEMENTED

> Migrated in Phase 3. Autouse fixture `cleanup_sip_phones_after_scenario` removed from `conftest.py`.

Four state-creating steps now carry their own yield-based teardown:

- `validate_use_case_phone_requirements` — hangup + phone_kill for each registered phone
- `phone_dials_number` — disconnects the caller's active call
- `phone_calls_number` — disconnects the caller's active call
- `phone_in_active_call` — disconnects the busy-maker's background call

One delegate step propagates teardown via `yield from`:

- `caller_calls_callee` — delegates to `phone_dials_number` with `yield from`

Steps that remove state (hangup, answer, reject) have no teardown — they move the system toward the clean end-state.

**Before** (centralized fixture):

```python
# conftest.py
@pytest.fixture(scope="function", autouse=True)
def cleanup_sip_phones_after_scenario(devices, bf_context):
    yield
    for device_name in dir(devices):
        device = getattr(devices, device_name)
        if isinstance(device, SIPPhone):
            device.hangup()
            device.phone_kill()
    bf_context.configured_phones = {}
```

**After** (co-located in each state-creating step):

Phone registration teardown — captures the list of registered phones at setup:

```python
@given("the following phones are required for this use case:")
def validate_use_case_phone_requirements(sipcenter, bf_context, devices, datatable):
    # ... discover, configure, register phones ...
    registered_phones = list(phone_mapping.values())

    yield

    for fixture_name, phone in registered_phones:
        try:
            phone.hangup()
        except Exception:
            pass
        try:
            phone.phone_kill()
        except Exception as exc:
            print(f"⚠ Could not stop phone {fixture_name}: {exc}")
```

Call initiation teardown — captures the caller in its closure:

```python
@when('the {caller_role} dials the {callee_role}\'s number')
def phone_dials_number(caller_role, callee_role, bf_context):
    caller = get_phone_by_role(bf_context, caller_role)
    callee = get_phone_by_role(bf_context, callee_role)
    voice_use_cases.call_a_phone(caller, callee)

    yield

    try:
        voice_use_cases.disconnect_the_call(caller)
    except Exception as exc:
        print(f"⚠ Could not disconnect call for {caller.name}: {exc}")
```

Busy-state teardown — disconnects the busy-maker phone:

```python
@given("the {phone_role} phone is in an active call")
def phone_in_active_call(phone_role, bf_context):
    # ... establish background call via busy_maker_phone ...

    yield

    try:
        voice_use_cases.disconnect_the_call(busy_maker_phone)
    except Exception as exc:
        print(f"⚠ Could not disconnect busy-maker call: {exc}")
```

**Key design decisions**:

| Decision | Rationale |
|----------|-----------|
| Teardown on dial step, not answer step | Dial creates the call; answer transitions existing state |
| `caller_calls_callee` uses `yield from` | Delegates fully to `phone_dials_number`, propagating its teardown lifecycle |
| No teardown on `phone_hangs_up` | Hang-up removes state; no cleanup needed |
| `phone_in_active_call` fallback path still yields | Even when no third phone is available, the step yields to maintain generator protocol |

**Verified**: 131 unit tests pass (68 SIP phone + 63 SD-WAN), zero regressions.

### WAN Impairment — IMPLEMENTED

> Migrated in Phase 1. Autouse fixture `cleanup_sdwan_impairments_after_scenario` removed from `conftest.py`.

Three steps now carry their own yield-based teardown:

- `network_conditions_set_to_preset` — clears impairments on both `wan1_tc` and `wan2_tc`
- `wan_link_complete_failure` — clears the impairment on the affected WAN link's TC
- `wan_link_degraded` — clears the impairment on the affected WAN link's TC

Each teardown wraps `clear_impairment` in try/except to avoid masking test failures.

**Before** (centralized fixture):

```python
# conftest.py
@pytest.fixture(scope="function", autouse=True)
def cleanup_sdwan_impairments_after_scenario(bf_context):
    yield
    for attr in ("wan1_tc", "wan2_tc"):
        tc = getattr(bf_context, attr, None)
        if tc is not None:
            tc_use_cases.clear_impairment(tc)
```

**After** (co-located in each step — example: `wan_link_complete_failure`):

```python
@when('"{wan_link}" experiences a complete link failure')
def wan_link_complete_failure(bf_context, wan_link):
    tc = _get_tc_for_wan(bf_context, wan_link)
    tc_use_cases.set_impairment_profile(
        tc, ImpairmentProfile(loss_percent=100.0, ...)
    )
    bf_context.impaired_wan = wan_link
    bf_context.failure_start_time = time.monotonic()

    yield

    try:
        tc_use_cases.clear_impairment(tc)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Could not clear impairment: {exc}")
```

**conftest.py change**: the dynamic step re-registration wrapper was updated to detect generator functions (`inspect.isgeneratorfunction`) and emit `yield from` instead of `return`, so pytest-bdd correctly manages the setup/teardown lifecycle of yielding steps.

**Verified**: `WAN Failover Maintains Application Continuity.feature` — 2/3 scenarios pass (streaming SLO failure is a pre-existing flake).

### Traffic Generators — IMPLEMENTED

> Migrated in Phase 2. Autouse fixture `cleanup_traffic_generators_after_scenario` removed from `conftest.py`.

Only the state-creating step (`network_ops_starts_upstream_traffic`) gets a yield teardown. The state-removing step (`network_ops_stops_upstream_traffic`) does not need one — it already moves the system toward the clean end-state.

The teardown captures `flow_id` in the closure at setup time and always attempts to stop it. If the explicit stop step already ran, the redundant stop call raises and is swallowed by try/except — idempotent by design.

**Before** (centralized fixture):

```python
# conftest.py
@pytest.fixture(scope="function", autouse=True)
def cleanup_traffic_generators_after_scenario(bf_context):
    yield
    for attr in ("lan_traffic_gen", "north_traffic_gen"):
        tg = getattr(bf_context, attr, None)
        if tg is not None and tg.active_flows:
            tg_use_cases.stop_all_traffic(tg)
```

**After** (co-located, idempotent teardown on the creator step):

```python
@when(parsers.parse(
    "network operations starts {bandwidth:d} Mbps of"
    " best-effort upstream background traffic"
    " through the appliance"
))
def network_ops_starts_upstream_traffic(bf_context, bandwidth):
    flow_id = tg_use_cases.saturate_wan_link(
        source=bf_context.lan_traffic_gen,
        destination=bf_context.north_traffic_gen,
        link_bandwidth_mbps=bandwidth / 0.85,
        dscp=0, utilisation_pct=0.85, duration_s=120,
    )
    bf_context.upstream_flow_id = flow_id

    yield

    try:
        tg_use_cases.stop_traffic(bf_context.lan_traffic_gen, flow_id)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Could not stop traffic flow {flow_id}: {exc}")
```

The explicit stop step is a plain function — no yield, no sentinel:

```python
@when("network operations stops the upstream background traffic")
def network_ops_stops_upstream_traffic(bf_context):
    result = tg_use_cases.stop_traffic(
        bf_context.lan_traffic_gen, bf_context.upstream_flow_id,
    )
    bf_context.upstream_traffic_result = result
```

**Verified**: `QoS Priority Under WAN Contention.feature` — 1/1 scenario passes.

### CPE Config Restoration & TR-069 — IMPLEMENTED

> Migrated in Phase 4. Autouse fixture `cleanup_cpe_config_after_scenario` (~150 lines) removed from `conftest.py`. Console reconnection extracted to lightweight `refresh_cpe_console_after_scenario` autouse fixture.

Two state-creating steps now carry their own yield-based teardown:

- `user_sets_cpe_gui_password` in `background_steps.py` — restores password to PrplOS default ("admin")
- `cpe_is_unreachable_for_tr069` in `cpe_steps.py` — restarts the TR-069 client

Steps that don't need teardown:

- `cpe_is_online_and_provisioned` — read-only baseline capture
- `operator_initiates_reboot_task` — reboot is self-completing (no un-reboot)
- `cpe_comes_online_and_connects` — removes state (brings CPE back online)
- All `then`/verification steps — read-only

**Before** (centralized fixture):

```python
# conftest.py — ~150 lines
@pytest.fixture(scope="function", autouse=True)
def cleanup_cpe_config_after_scenario(acs, cpe, bf_context):
    yield
    # ... console reconnection ...
    # ... iterate bf_context.original_config ...
    # ... special-case passwords vs regular params ...
    # ... call acs.SPV() directly ...
```

**After** (co-located in each state-creating step):

Admin user discovery — uses batched GPV to handle non-contiguous TR-069 indices:

```python
def discover_admin_user_index(acs, cpe):
    # 1. Query UserNumberOfEntries → e.g. 11
    user_count = int(acs_use_cases.get_parameter_value(
        acs, cpe, "Device.Users.UserNumberOfEntries",
    ))
    # 2. Single batched GPV for indices 1 … user_count * 5
    max_idx = user_count * 5
    candidate_params = [
        f"Device.Users.User.{i}.Username"
        for i in range(1, max_idx + 1)
    ]
    result = acs.nbi.GPV(candidate_params, timeout=30, cpe_id=cpe_id)
    # 3. Find the entry with value "admin" and extract its index
    for item in result:
        key, value = item["key"], item["value"]
        if "usernam" in key.lower() and value.strip().lower() == "admin":
            return _extract_index_from_key(key)  # e.g. 10
```

Password restoration — captures `param` and `admin_user_idx` in the closure:

```python
@given('the user has set the CPE GUI password to "{password}"')
def user_sets_cpe_gui_password(acs, cpe, bf_context, password):
    admin_user_idx = discover_admin_user_index(acs, cpe)
    param = f"Device.Users.User.{admin_user_idx}.Password"

    acs_use_cases.set_parameter_value(acs, cpe, param, password)

    yield

    try:
        acs_use_cases.set_parameter_value(acs, cpe, param, "admin")
    except Exception as exc:
        print(f"⚠ Could not restore CPE GUI password: {exc}")
```

TR-069 client restoration — captures `cpe` in the closure:

```python
@given("the CPE is unreachable for TR-069 sessions")
def cpe_is_unreachable_for_tr069(acs, cpe, bf_context):
    cpe_use_cases.stop_tr069_client(cpe)

    yield

    try:
        cpe_use_cases.start_tr069_client(cpe)
    except Exception as exc:
        print(f"⚠ Could not restart TR-069 client: {exc}")
```

**Key design decisions**:

| Decision | Rationale |
|----------|-----------|
| Batched GPV for admin user discovery | TR-069 instance indices are not contiguous (e.g., admin at index 10, not 1). Single batched GPV with `user_count × 5` candidates avoids per-index round-trips and scales with the device. |
| `acs.nbi.GPV` (direct NBI) for discovery | `acs_use_cases.get_parameter_value` returns a single scalar. Batched GPV needs the raw list response to scan all usernames in one call. |
| Password restored to "admin" default, not original encrypted hash | SPV expects plaintext; encrypted hash from GPV cannot be round-tripped |
| No teardown on `cpe_is_online_and_provisioned` | Read-only step; captures baseline but doesn't change state |
| No teardown on `operator_initiates_reboot_task` | Reboot is self-completing; CPE restarts on its own |
| `cpe_comes_online_and_connects` has no teardown | It removes state (brings CPE back online), which is the clean end-state |
| `original_config` scaffolding removed from `user_sets_cpe_gui_password` | No longer needed; cleanup is co-located, not mediated through bf_context |
| `config_before_reboot` tracking preserved | Used by `cpe_configuration_preserved_after_reboot` for reboot verification (not cleanup) |

**Simplification**: the `user_sets_cpe_gui_password` step was reduced from ~140 lines to ~80 lines by removing the `original_config` scaffolding — all the `hasattr`/`setdefault`/nested-dict wiring that existed solely to communicate undo data to the conftest cleanup fixture.

**Verified**: 159 unit tests pass (21 CPE/background + 7 CPE steps + 68 SIP + 63 SD-WAN), zero regressions. Integration test (`Remote CPE Reboot.feature` UC-12347-Main) confirmed: admin user discovered at index 10 via batched GPV, password set and restored correctly. Test progressed past all Phase 4 steps; remaining failure is an Inform timeout in a later step (unrelated to cleanup changes).

---

## Console Reconnection

The `cleanup_cpe_config_after_scenario` fixture also handled CPE console reconnection after reboot. This concern is orthogonal to config restoration and has been extracted to a lightweight autouse fixture:

```python
@pytest.fixture(scope="function", autouse=True)
def refresh_cpe_console_after_scenario(cpe):
    """Ensure CPE console is usable for the next scenario."""
    yield
    if cpe is None:
        return
    try:
        cpe.hw.disconnect_from_consoles()
        cpe.hw.connect_to_consoles(getattr(cpe, "device_name", "cpe"))
    except Exception:
        pass
```

This is a true cross-cutting concern (any scenario might reboot the CPE) and is appropriate as an autouse fixture — unlike config/phone/impairment cleanup which is step-specific. This fixture is now the **only** autouse cleanup fixture remaining in `conftest.py`.

---

## Benefits Summary

| Aspect | Before (bf_context) | After (yield) |
|--------|---------------------|------------------|
| **Cleanup location** | Centralized in conftest.py | Co-located with setup in each step |
| **Ordering** | Fixed fixture order | Automatic LIFO matching scenario flow |
| **Scope** | Runs for every scenario | Only runs for steps that executed |
| **Coupling** | Steps + conftest must agree on bf_context structure | Self-contained per step |
| **Failure safety** | Relies on `hasattr` guards | Guaranteed by pytest fixture lifecycle |
| **Lines of cleanup code in conftest** | ~250 | ~15 (console reconnect only) |
| **bf_context usage** | Tracks undo data + inter-step communication | Inter-step communication only |

---

## Prerequisites

- **pytest-bdd 6+** required (step definitions as proper fixtures with yield support)
- Verify current pytest-bdd version in `pyproject.toml` / `requirements.txt`

## Migration Strategy

| Phase | Area                                      | Status                                | Verified by                                             |
| ----- | ----------------------------------------- | ------------------------------------- | ------------------------------------------------------- |
| 1     | **SD-WAN impairments**                    | ✅ Complete                            | `WAN Failover Maintains Application Continuity.feature` |
| 2     | **Traffic generators**                    | ✅ Complete                            | `QoS Priority Under WAN Contention.feature`             |
| 3     | **SIP phone registration & calls**        | ✅ Complete                            | 131 unit tests (68 SIP + 63 SD-WAN)                     |
| 4     | **CPE config restoration & TR-069**       | ✅ Complete                            | 159 unit tests + integration test (Remote CPE Reboot)   |
| —     | Remove corresponding autouse fixtures     | ✅ Done for all phases                 |                                                         |
| —     | Keep `refresh_cpe_console_after_scenario` | N/A (lightweight, remains as autouse) |                                                         |

### Implementation notes

- **conftest.py wrapper fix**: the dynamic step re-registration mechanism in `conftest.py` was updated to detect generator functions via `inspect.isgeneratorfunction()` and use `yield from` instead of `return` in generated wrappers. Without this, pytest-bdd would receive the generator object rather than driving its lifecycle, causing step setup code to silently not execute.
- **Unit tests**: all step test files include a `_run_step()` helper that advances generators to first yield, plus dedicated teardown test classes verifying cleanup behavior:
  - `TestYieldTeardownBehavior` and `TestTrafficGeneratorYieldTeardown` (SD-WAN)
  - `TestPhoneRegistrationYieldTeardown`, `TestPhoneDialsNumberYieldTeardown`, `TestCallerCallsCalleeYieldTeardown`, `TestPhoneCallsNumberYieldTeardown`, `TestPhoneInActiveCallYieldTeardown` (SIP phones)
  - `TestPasswordYieldTeardown`, `TestCpeTr069YieldTeardown`, `TestDiscoverAdminUserIndex` (CPE config & TR-069)
- **Integration verification**: `Remote CPE Reboot.feature` (UC-12347-Main) was run against a live PrplOS device. The batched GPV discovered the admin user at index 10. Password set/restore worked correctly. The test progressed through all Phase 4 steps; the remaining failure is an Inform timeout in the reboot verification step (pre-existing, unrelated to cleanup changes).

---

## Lessons Learned

Five key observations from the Phase 1–4 implementations that should guide future migration work.

### 1. Unit tests must verify teardown behavior, not just setup

When a step becomes a generator (adds `yield`), its unit tests need to be updated in two ways:

**Executing the step**: a helper like `_run_step()` is needed to advance the generator to its first `yield`, so the setup code actually runs. Calling the function directly only returns a generator object — no setup code executes.

```python
def _run_step(step_fn, *args, **kwargs):
    """Execute the setup portion of a step function."""
    result = step_fn(*args, **kwargs)
    if inspect.isgenerator(result):
        next(result)        # drive setup to the yield point
        return result        # return generator so tests can verify teardown
    return result
```

**Testing teardown**: dedicated tests should advance the generator past `yield` (via `next(gen)`, catching `StopIteration`) and then assert that the expected cleanup calls were made. This is a new category of test that did not exist before — previously teardown was implicit in conftest fixtures and untested at the unit level.

```python
def test_teardown_clears_impairment(self, bf_context):
    with patch("...tc_use_cases") as mock_tc:
        gen = _run_step(wan_link_complete_failure, bf_context, "wan1")
        mock_tc.clear_impairment.reset_mock()

        with pytest.raises(StopIteration):
            next(gen)

        mock_tc.clear_impairment.assert_called_once_with(bf_context.wan1_tc)
```

Every step that gains a `yield` should also gain at least two teardown-specific tests:
1. Verify the cleanup action fires
2. Verify that cleanup exceptions are swallowed (don't mask the original test failure)

### 2. Teardown rule: idempotent cleanup on state-creating steps only

The initial implementation used two teardown categories: unconditional (Category A) and conditional with a sentinel pattern (Category B). After evaluating the design, we converged on a single, simpler rule:

> **Only steps that create state requiring cleanup get a yield teardown. The teardown is always unconditional and idempotent (safe to call even if the state was already cleaned up).**

This eliminates the need for sentinels, inter-step coordination, and the question of "which category does this step belong to?"

#### The decision: does this step create cleanup-worthy state?

| Step type | Creates state requiring cleanup? | Needs yield? |
|-----------|----------------------------------|--------------|
| Apply impairment | Yes (impairment is active) | Yes |
| Clear impairment (`wan_link_recovers`) | No (removing state) | No |
| Start traffic | Yes (flow is running) | Yes |
| Stop traffic | No (removing state) | No |
| Register SIP phones | Yes (phones registered + pjsua running) | Yes |
| Dial / initiate call | Yes (call is active) | Yes |
| Establish busy state (background call) | Yes (background call is active) | Yes |
| Answer call | No (transitions existing call) | No |
| Hang up call | No (removing state) | No |
| Reject call | No (removing state) | No |
| Set CPE password | Yes (config changed) | Yes |
| Stop TR-069 client | Yes (CPE taken offline) | Yes |
| Restart TR-069 client | No (removing state) | No |
| Initiate reboot | No (self-completing operation) | No |
| Capture baseline state | No (read-only) | No |
| Verify/assert state | No (read-only) | No |

The question is not "will another step undo this?" but simply: **"if this step ran and the scenario failed immediately after, would something need cleaning up?"**

#### Why not conditional teardown (sentinel pattern)?

An earlier iteration used a sentinel pattern for start/stop pairs: the stop step would clear a flag so the start step's teardown would skip. This was rejected because:

- **Coupling**: the stop step must know which sentinel the start step uses
- **Fragility**: any new step that also stops the resource must clear the same sentinel
- **Unnecessary**: if the cleanup operation is wrapped in try/except, a redundant call is harmless

#### Idempotent teardown via captured state and try/except

The teardown captures its undo target at setup time (in the closure) and wraps the cleanup in try/except. If the explicit stop step already ran, the cleanup call raises and is swallowed harmlessly.

```python
def network_ops_starts_upstream_traffic(bf_context, bandwidth):
    flow_id = tg_use_cases.saturate_wan_link(...)    # ← flow_id captured here
    bf_context.upstream_flow_id = flow_id

    yield

    try:
        tg_use_cases.stop_traffic(bf_context.lan_traffic_gen, flow_id)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Could not stop traffic flow {flow_id}: {exc}")
```

Note that `flow_id` is the local variable captured in the closure — not read from `bf_context` at teardown time. This means:
- If the explicit stop step already ran, `stop_traffic` raises "flow not found" → swallowed
- If the scenario failed before the stop step, `stop_traffic` stops the running flow → cleanup succeeds
- No sentinel, no coupling, no coordination between steps

The explicit stop step is a plain function with no yield — it removes state, so no teardown is needed:

```python
def network_ops_stops_upstream_traffic(bf_context):
    result = tg_use_cases.stop_traffic(
        bf_context.lan_traffic_gen, bf_context.upstream_flow_id,
    )
    bf_context.upstream_traffic_result = result
```

#### Failure mode analysis

| Scenario outcome | What happens |
|------------------|--------------|
| Succeeds (start → stop → teardown) | Explicit stop succeeds; teardown tries to stop again, swallows "already stopped" error |
| Fails after start, before stop | Teardown stops the running flow — cleanup succeeds |
| Fails during stop (partial) | Teardown tries to stop again — idempotent, swallows error |
| Succeeds (dial → answer → hangup → teardown) | Hangup succeeds; dial's teardown tries to disconnect again, swallows error |
| Fails after dial, before hangup | Dial's teardown disconnects the active call — cleanup succeeds |
| Succeeds (register → scenario → teardown) | Registration teardown kills all phones — cleanup succeeds |
| Fails mid-scenario with registered phones | Registration teardown still runs — hangup + phone_kill for all phones |
| Succeeds (set password → reboot → verify → teardown) | Teardown restores password to "admin" — cleanup succeeds |
| Fails after password set, before reboot | Teardown still restores password — cleanup succeeds |
| Succeeds (stop TR-069 → reconnect → teardown) | Reconnect restarts client; teardown tries again, swallows error |
| Fails after stop TR-069, before reconnect | Teardown restarts TR-069 client — cleanup succeeds |

#### Unit test coverage for idempotent teardown

Each yielding step should have these teardown tests:
1. **Teardown fires**: verify the cleanup call is made with the correct captured arguments
2. **Teardown is idempotent**: set up the mock to raise (simulating "already cleaned up"), verify no exception propagates
3. **Teardown swallows errors**: set up the mock to raise an infrastructure error, verify no exception propagates

### 3. Delegate steps must use `yield from` to propagate teardown

When one step function delegates to another yielding step (e.g., `caller_calls_callee` delegates to `phone_dials_number`), the delegate **must** use `yield from`, not a plain call.

A plain call returns the generator object without driving it — setup code never executes and teardown is never registered with pytest-bdd:

```python
# WRONG — returns a generator object, nothing happens
@when('the {caller} calls the {callee}')
def caller_calls_callee(caller, callee, bf_context):
    return phone_dials_number(caller, callee, bf_context)  # ← dead generator
```

```python
# CORRECT — drives setup, propagates teardown
@when('the {caller} calls the {callee}')
def caller_calls_callee(caller, callee, bf_context):
    yield from phone_dials_number(caller, callee, bf_context)
```

`yield from` transparently forwards the inner generator's lifecycle to pytest-bdd: setup runs immediately, and teardown runs at scenario end in the correct LIFO position. This avoids duplicating teardown logic in the delegate step.

**When to watch for this**: any time a step is a thin wrapper around another step that yields. Grep for step functions that call other step functions and verify they use `yield from` if the target yields.

### 4. All code paths in a yielding step must reach `yield`

If a step function has conditional branches, **every branch** must reach a `yield` statement. A branch that returns before yielding silently converts the step from a generator into a regular function on that code path. pytest-bdd will not manage its teardown lifecycle, and any cleanup registered after the `yield` on other branches will never execute.

```python
# WRONG — fallback path returns, making the step non-yielding on that path
@given("the {phone_role} phone is in an active call")
def phone_in_active_call(phone_role, bf_context):
    busy_maker = find_busy_maker(bf_context)
    if busy_maker is None:
        print("No third phone available, skipping busy state")
        return  # ← step is no longer a generator on this path

    establish_background_call(busy_maker)
    yield
    try:
        voice_use_cases.disconnect_the_call(busy_maker)
    except Exception:
        pass
```

```python
# CORRECT — both paths yield, maintaining generator protocol
@given("the {phone_role} phone is in an active call")
def phone_in_active_call(phone_role, bf_context):
    busy_maker = find_busy_maker(bf_context)
    if busy_maker is None:
        print("No third phone available, skipping busy state")
        yield  # ← still a generator, no teardown needed on this path
        return

    establish_background_call(busy_maker)
    yield
    try:
        voice_use_cases.disconnect_the_call(busy_maker)
    except Exception:
        pass
```

Python does not warn about this — the presence of `yield` anywhere in the function body makes Python treat it as a generator function at *definition* time, but at *runtime* a branch that doesn't reach `yield` will cause `next(gen)` to raise `StopIteration` immediately, which pytest-bdd interprets as "step completed with no teardown." The subtle risk is that on the yielding branch, teardown works correctly, but on the non-yielding branch it silently does nothing — a bug that only manifests under specific test conditions.

**When to watch for this**: any yielding step with early-return logic, error handling shortcuts, or fallback branches. Each path should end with `yield` (optionally followed by teardown code) rather than `return`.

### 5. TR-069 instance indices are not contiguous — use batched GPV for discovery

TR-069 data model instances (e.g., `Device.Users.User.{i}`) are **not** guaranteed to use contiguous indices starting from 1. On PrplOS devices, the admin user is commonly at index 10 while guest users are at other scattered indices. Hard-coding index 1 or iterating 1…N will silently target the wrong user.

The solution is a **batched GPV** that queries a range of candidate `Username` parameters in a single ACS round-trip and then scans the response for the admin entry:

```python
def discover_admin_user_index(acs, cpe):
    user_count = int(acs_use_cases.get_parameter_value(
        acs, cpe, "Device.Users.UserNumberOfEntries",
    ))
    max_idx = user_count * 5  # over-provision to cover gaps
    candidate_params = [
        f"Device.Users.User.{i}.Username"
        for i in range(1, max_idx + 1)
    ]
    result = acs.nbi.GPV(candidate_params, timeout=30, cpe_id=cpe_id)
    # GenieACS silently drops non-existent indices → only real users in result
    for item in result:
        if item["value"].strip().lower() == "admin":
            return _extract_index_from_key(item["key"])  # e.g. 10
```

**Key details**:

- The multiplier (`× 5`) scales with the actual `UserNumberOfEntries` count, so the range adapts to the device rather than using a fixed ceiling.
- GenieACS silently ignores parameters for non-existent instances, so the response contains only real users — no error handling needed for absent indices.
- GPV response keys may be mangled by GenieACS's `strip('._value')` call (e.g., `Usernam` instead of `Username`), so the key parser splits on dots and extracts the integer at position 3 rather than relying on an exact suffix match.
- `acs.nbi.GPV` (direct NBI call) is required because `acs_use_cases.get_parameter_value` returns only a single scalar value, while discovery needs the full list response.

**When to watch for this**: any step that interacts with TR-069 instance tables (Users, WiFi SSIDs, LANDevice, WANDevice, etc.). Never assume instance index 1 exists or that indices are sequential.

---

# Robot Framework: Listener-Based Teardown Stack

The same problem exists for Robot Framework keyword libraries — any keyword that changes device state needs a way to undo that change after the test. Robot Framework does not have pytest's yield-based fixture lifecycle, but the existing `robotframework-boardfarm` infrastructure provides an equivalent mechanism.

---

## Why the Listener Is the Right Place

The `BoardfarmListener` in `robotframework-boardfarm` already manages the full test lifecycle:

- `start_suite` — deploys devices (root suite only)
- `start_test` — validates environment requirements
- `end_test` — **currently a noop** with `# Future: capture logs, cleanup context, etc.`
- `end_suite` — releases devices (root suite only)

Three properties make it the natural home for per-test cleanup:

1. **`end_test` runs for every test, even on failure** — same guarantee as pytest fixture finalizers
2. **The listener is a singleton** accessible via `get_listener()` — keyword libraries already use this pattern to reach `device_manager` and `boardfarm_config`
3. **No test-level wiring needed** — unlike a `[Teardown]` keyword or `Test Teardown` setting, the listener fires automatically

---

## Design: Teardown Stack on the Listener

### Listener Changes

Add a LIFO stack to `BoardfarmListener` and drain it in `end_test`:

```python
# robotframework_boardfarm/listener.py

class BoardfarmListener:

    def __init__(self, **kwargs):
        # ... existing init ...
        self._teardown_stack: list[tuple[str, callable, tuple, dict]] = []

    def register_teardown(self, description: str, func, *args, **kwargs):
        """Push a cleanup action onto the per-test teardown stack.

        Called by keyword libraries after any state-changing operation.
        Actions execute in LIFO order when the test ends.

        Args:
            description: Human-readable label for logging.
            func: Callable to invoke during teardown.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.
        """
        self._teardown_stack.append((description, func, args, kwargs))
        self._logger.debug("Registered teardown: %s", description)

    def end_test(self, data, result):
        """Execute all registered teardowns in LIFO order, then clear."""
        errors = []
        while self._teardown_stack:
            description, func, args, kwargs = self._teardown_stack.pop()
            try:
                func(*args, **kwargs)
                self._logger.info("✓ Teardown: %s", description)
            except Exception as e:
                self._logger.warning("⚠ Teardown failed: %s: %s", description, e)
                errors.append(f"{description}: {e}")

        if errors:
            self._logger.warning("%d teardown(s) had errors", len(errors))
```

The stack is a simple list of `(description, callable, args, kwargs)` tuples. `end_test` pops from the end (LIFO) so the last action registered is the first to be undone.

### Keyword Libraries Register Cleanup via `get_listener()`

Keyword libraries already call `get_listener()` to access devices. Registering teardown uses the same access pattern — cleanup is co-located with the action that needs undoing:

```python
# robot/libraries/acs_keywords.py
from robot.api.deco import keyword
from boardfarm3.use_cases import acs as acs_use_cases
from robotframework_boardfarm.listener import get_listener


class AcsKeywords:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("The User Sets The CPE GUI Password To")
    def set_cpe_gui_password(self, acs, cpe, password):
        admin_idx = discover_admin_user_index(acs, cpe)
        param = f"Device.Users.User.{admin_idx}.Password"

        acs_use_cases.set_parameter_value(acs, cpe, param, password)

        get_listener().register_teardown(
            "Restore CPE GUI password to default",
            acs_use_cases.set_parameter_value,
            acs, cpe, param, "admin",
        )
```

```python
# robot/libraries/voice_keywords.py
from robotframework_boardfarm.listener import get_listener


class VoiceKeywords:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("The Following Phones Are Registered")
    def register_phones(self, sipcenter, phone_config):
        registered = self._configure_and_register(sipcenter, phone_config)

        def cleanup_phones():
            for phone in registered:
                try:
                    phone.hangup()
                except Exception:
                    pass
                phone.phone_kill()

        get_listener().register_teardown(
            f"Clean up {len(registered)} SIP phones",
            cleanup_phones,
        )
```

```python
# robot/libraries/sdwan_keywords.py
from robotframework_boardfarm.listener import get_listener


class SdwanKeywords:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("WAN Link Experiences Complete Failure")
    def wan_link_failure(self, wan_link):
        tc = self._get_tc_for_wan(wan_link)
        tc_use_cases.set_impairment_profile(
            tc, ImpairmentProfile(loss_percent=100.0, ...),
        )

        get_listener().register_teardown(
            f"Clear {wan_link} impairment",
            tc_use_cases.clear_impairment, tc,
        )

    @keyword("Network Operations Starts Upstream Background Traffic")
    def start_upstream_traffic(self, bandwidth):
        flow_id = tg_use_cases.saturate_wan_link(
            source=self.lan_tg, destination=self.north_tg,
            link_bandwidth_mbps=bandwidth / 0.85,
            dscp=0, utilisation_pct=0.85, duration_s=120,
        )

        get_listener().register_teardown(
            "Stop upstream background traffic",
            tg_use_cases.stop_all_traffic, self.lan_tg,
        )
```

### What `.robot` Files Look Like

No `[Teardown]` or `Test Teardown` needed — the listener handles cleanup transparently:

```robotframework
*** Settings ***
Library    robotframework_boardfarm.BoardfarmLibrary
Library    ../libraries/acs_keywords.py
Library    ../libraries/voice_keywords.py

*** Test Cases ***
UC-12347: Remote CPE Reboot
    [Documentation]    Remote reboot of CPE via ACS
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE

    A CPE Is Online And Fully Provisioned    ${acs}    ${cpe}
    The User Sets The CPE GUI Password To    ${acs}    ${cpe}    secret123
    The Operator Initiates A Reboot Task     ${acs}    ${cpe}
    The CPE Should Have Rebooted             ${cpe}
```

When this test ends (pass or fail), `listener.end_test()` automatically restores the password.

---

## Execution Flow

For a test where keyword A sets a password, keyword B applies an impairment, and keyword C verifies:

```
1.  Keyword A runs  → pushes undo_A onto stack
2.  Keyword B runs  → pushes undo_B onto stack
3.  Keyword C runs  → (no state change, nothing pushed)
4.  Test ends (pass or fail)
5.  listener.end_test() fires:
      pop → undo_B executes   (clear impairment)
      pop → undo_A executes   (restore password)
```

Same LIFO order as pytest-bdd's yield unwinding.

---

## Console Reconnection in Robot Framework

The CPE console refresh is a cross-cutting concern in Robot Framework too. It can be handled in the listener's `end_test` directly, since it applies to every test regardless of which keywords ran:

```python
def end_test(self, data, result):
    # 1. Drain the teardown stack (LIFO)
    while self._teardown_stack:
        description, func, args, kwargs = self._teardown_stack.pop()
        try:
            func(*args, **kwargs)
        except Exception as e:
            self._logger.warning("⚠ Teardown failed: %s: %s", description, e)

    # 2. Cross-cutting: refresh CPE console for next test
    try:
        dm = self._device_manager
        if dm is not None:
            from boardfarm3.templates.cpe.cpe import CPE
            cpe = dm.get_device_by_type(CPE)
            cpe.hw.disconnect_from_consoles()
            cpe.hw.connect_to_consoles(getattr(cpe, "device_name", "cpe"))
    except Exception:
        pass
```

---

## Additional Note: Test Context Clearing

`BoardfarmLibrary` has a `_context` dict (GLOBAL scope) with `Set/Get/Clear Test Context` keywords. Because the library scope is GLOBAL, this context persists across tests unless explicitly cleared. The `end_test` method should also reset it to prevent state leaking between tests:

```python
def end_test(self, data, result):
    # ... drain teardown stack ...
    # ... refresh CPE console ...

    # 3. Clear per-test context on the library
    try:
        from robotframework_boardfarm.library import BoardfarmLibrary
        lib = BoardfarmLibrary._instance  # or via BuiltIn().get_library_instance()
        if lib is not None:
            lib.clear_test_context()
    except Exception:
        pass
```

---

## Comparison: pytest-bdd vs Robot Framework

| Aspect | pytest-bdd (yield) | Robot Framework (listener stack) |
|--------|-------------------|----------------------------------|
| Where cleanup is registered | `yield` in step function | `get_listener().register_teardown()` in keyword |
| Where cleanup executes | pytest fixture finalization | `listener.end_test()` |
| Test author wiring needed | None (yield is implicit) | None (listener is automatic) |
| LIFO ordering | Automatic (fixture stack) | `stack.pop()` in `end_test` |
| Failure safety | pytest runs finalizers on failure | Robot runs `end_test` on failure |
| Access pattern | N/A (fixtures inject directly) | `get_listener()` (already used for devices) |
| Co-location | Setup + teardown in same function | `register_teardown` call sits next to the action |

Both approaches achieve the same goal: cleanup is co-located with the action that needs undoing, runs in LIFO order, only fires for actions that actually executed, and is invisible to the test author.
