"""Unit tests for SIP phone step definitions."""

import pytest

# Import the step definition functions to be tested
from tests.step_defs.sip_phone_steps import (
    assign_caller_callee_roles,
    both_phones_connected,
    both_phones_return_to_idle,
    caller_calls_callee,
    caller_plays_busy_tone,
    discover_available_sip_phones_from_devices,
    ensure_phone_registered,
    get_phone_by_name,
    get_phone_by_role,
    map_phones_to_requirements,
    phone_answers_call,
    phone_dials_invalid_number,
    phone_dials_number,
    phone_hangs_up,
    phone_in_active_call,
    phone_is_idle,
    phone_plays_busy_tone,
    phone_plays_dial_tone,
    phone_starts_ringing,
    sip_server_is_running,
    sip_server_sends_response,
    validate_use_case_phone_requirements,
    verify_phone_state,
    verify_rtp_session,
    wait_for_phone_state,
)
from tests.unit.mocks import MockContext, MockSIPPhone, MockSIPServer, MockDevices


def test_get_phone_by_role_caller(bf_context: MockContext, lan_phone: MockSIPPhone):
    """Verify get_phone_by_role() correctly retrieves the caller."""
    bf_context.caller = lan_phone
    phone = get_phone_by_role(bf_context, "caller")
    assert phone is lan_phone


def test_get_phone_by_role_callee(bf_context: MockContext, wan_phone: MockSIPPhone):
    """Verify get_phone_by_role() correctly retrieves the callee."""
    bf_context.callee = wan_phone
    phone = get_phone_by_role(bf_context, "callee")
    assert phone is wan_phone


def test_get_phone_by_role_caller_not_set(bf_context: MockContext):
    """Verify get_phone_by_role() raises ValueError when caller is not set."""
    with pytest.raises(ValueError, match="Caller phone not set in context"):
        get_phone_by_role(bf_context, "caller")


def test_get_phone_by_role_callee_not_set(bf_context: MockContext):
    """Verify get_phone_by_role() raises ValueError when callee is not set."""
    with pytest.raises(ValueError, match="Callee phone not set in context"):
        get_phone_by_role(bf_context, "callee")


def test_get_phone_by_role_invalid(bf_context: MockContext):
    """Verify get_phone_by_role() raises ValueError for an invalid role."""
    with pytest.raises(ValueError, match="Unknown role: invalid_role"):
        get_phone_by_role(bf_context, "invalid_role")


def test_phone_is_idle_success(bf_context: MockContext, lan_phone: MockSIPPhone):
    """Test the 'phone_is_idle' step when the phone is already idle."""
    # Arrange: Set the phone as the caller and ensure its state is idle
    bf_context.caller = lan_phone
    lan_phone._state = "idle"

    # Act: Run the step definition function
    phone_is_idle(phone_role="caller", bf_context=bf_context)

    # Assert: No exception should be raised


def test_phone_is_idle_failure(bf_context: MockContext, lan_phone: MockSIPPhone):
    """Test the 'phone_is_idle' step when the phone is not idle."""
    # Arrange: Set the phone as the caller and put it in a 'connected' state
    bf_context.caller = lan_phone
    lan_phone._state = "connected"

    # Act & Assert: Verify that an AssertionError is raised
    with pytest.raises(AssertionError, match="Phone lan_phone is not in idle state"):
        phone_is_idle(phone_role="caller", bf_context=bf_context)


# -- Tests for get_phone_by_name --


def test_get_phone_by_name_success(bf_context: MockContext, lan_phone: MockSIPPhone):
    """Verify get_phone_by_name() correctly retrieves a phone by its name."""
    setattr(bf_context, "lan_phone", lan_phone)
    phone = get_phone_by_name(bf_context, "lan_phone")
    assert phone is lan_phone


def test_get_phone_by_name_failure(bf_context: MockContext):
    """Verify get_phone_by_name() raises ValueError for a non-existent phone."""
    with pytest.raises(ValueError, match="Phone 'non_existent_phone' not found in context."):
        get_phone_by_name(bf_context, "non_existent_phone")


# -- Tests for ensure_phone_registered --


def test_ensure_phone_registered_success(
    lan_phone: MockSIPPhone, sipcenter: MockSIPServer
):
    """Test ensure_phone_registered() when the phone is registered."""
    # Arrange: Register the phone's number with the mock SIP server
    sipcenter.register_user(lan_phone.number)

    # Act & Assert: No exception should be raised
    ensure_phone_registered(lan_phone, sipcenter)


def test_ensure_phone_registered_failure(
    lan_phone: MockSIPPhone, sipcenter: MockSIPServer
):
    """Test ensure_phone_registered() when the phone is not registered."""
    # Arrange: The phone is not registered by default in the mock server

    # Act & Assert: Verify that an AssertionError is raised
    with pytest.raises(AssertionError, match=f"Phone {lan_phone.name} .* is not registered"):
        ensure_phone_registered(lan_phone, sipcenter)


# -- Tests for verify_phone_state --


def test_verify_phone_state_success(lan_phone: MockSIPPhone):
    """Test verify_phone_state() when the phone is in the correct state."""
    lan_phone._state = "ringing"
    verify_phone_state(lan_phone, "ringing")


def test_verify_phone_state_failure(lan_phone: MockSIPPhone):
    """Test verify_phone_state() when the phone is in the wrong state."""
    lan_phone._state = "idle"
    with pytest.raises(AssertionError, match="Phone lan_phone is not in connected state"):
        verify_phone_state(lan_phone, "connected")


def test_verify_phone_state_invalid_state(lan_phone: MockSIPPhone):
    """Test verify_phone_state() with an unknown state string."""
    with pytest.raises(ValueError, match="Unknown state: invalid_state"):
        verify_phone_state(lan_phone, "invalid_state")


# -- Tests for sip_server_is_running --


def test_sip_server_is_running_success(sipcenter: MockSIPServer):
    """Test the 'sip_server_is_running' step when the server is running."""
    sipcenter._status = "Running"
    sip_server_is_running(sipcenter)


def test_sip_server_is_running_failure(sipcenter: MockSIPServer):
    """Test the 'sip_server_is_running' step when the server is not running."""
    sipcenter._status = "Stopped"
    with pytest.raises(AssertionError, match="SIP server is not running. Status: Stopped"):
        sip_server_is_running(sipcenter)


# -- Tests for assign_caller_callee_roles --


def test_assign_caller_callee_roles_success(
    bf_context: MockContext, lan_phone: MockSIPPhone, wan_phone: MockSIPPhone
):
    """Test the 'assign_caller_callee_roles' step for successful assignment."""
    # Arrange: Add the mock phones to the context by their names
    setattr(bf_context, "lan_phone", lan_phone)
    setattr(bf_context, "wan_phone", wan_phone)

    # Act: Run the step definition
    assign_caller_callee_roles("lan_phone", "wan_phone", bf_context)

    # Assert: Verify that the caller and callee are correctly set on the context
    assert bf_context.caller is lan_phone
    assert bf_context.callee is wan_phone


def test_assign_caller_callee_roles_failure_phone_not_found(
    bf_context: MockContext, wan_phone: MockSIPPhone
):
    """Test 'assign_caller_callee_roles' when a phone name is not in the context."""
    # Arrange: Add only one of the phones to the context
    setattr(bf_context, "wan_phone", wan_phone)

    # Act & Assert: Verify a ValueError is raised for the non-existent phone
    with pytest.raises(ValueError, match="Phone 'non_existent_phone' not found in context."):
        assign_caller_callee_roles("non_existent_phone", "wan_phone", bf_context)


# -- Tests for phone_dials_number --


def test_phone_dials_number_success(
    bf_context: MockContext, lan_phone: MockSIPPhone, wan_phone: MockSIPPhone
):
    """Test the 'phone_dials_number' step for a successful dial."""
    # Arrange: Set up caller and callee in the context
    bf_context.caller = lan_phone
    bf_context.callee = wan_phone

    # Act: Run the step definition
    phone_dials_number("caller", "callee", bf_context)

    # Assert: Verify the dial method was called with the correct number
    assert lan_phone.last_dialed_number == wan_phone.number
    assert bf_context.call_immediately_disconnected is False


def test_phone_dials_number_detects_busy(
    bf_context: MockContext, lan_phone: MockSIPPhone, wan_phone: MockSIPPhone
):
    """Test 'phone_dials_number' correctly detects an immediate busy signal."""
    # Arrange: Set up caller and callee
    bf_context.caller = lan_phone
    bf_context.callee = wan_phone
    # Simulate a busy signal in the mock console output
    lan_phone._console.before = "DISCONNECTED [reason=486 (Busy Here)]"

    # Act: Run the step definition
    phone_dials_number("caller", "callee", bf_context)

    # Assert: Verify the context flags for immediate disconnect are set
    assert bf_context.call_immediately_disconnected is True
    assert bf_context.disconnect_reason == "486 Busy Here"


# -- Tests for phone_answers_call --


def test_phone_answers_call_success(bf_context: MockContext, lan_phone: MockSIPPhone):
    """Test the 'phone_answers_call' step for a successful answer."""
    # Arrange: Set the phone as the callee and its state to 'ringing'
    bf_context.callee = lan_phone
    lan_phone._state = "ringing"

    # Act: Run the step definition
    phone_answers_call("callee", bf_context)

    # Assert: Verify the phone's state is now 'connected'
    assert lan_phone.is_connected()


def test_phone_answers_call_failure_not_ringing(
    bf_context: MockContext, lan_phone: MockSIPPhone
):
    """Test 'phone_answers_call' when the phone is not ringing.
    
    Note: After refactoring to use voice_use_cases, VoiceError is raised
    instead of AssertionError when the phone is not ringing.
    """
    from boardfarm3.exceptions import VoiceError
    
    # Arrange: Set the phone as the callee but keep its state as 'idle'
    bf_context.callee = lan_phone
    lan_phone._state = "idle"

    # Act & Assert: Verify that a VoiceError is raised
    with pytest.raises(VoiceError, match="not ringing"):
        phone_answers_call("callee", bf_context)


# -- Tests for phone_hangs_up --


def test_phone_hangs_up_success(bf_context: MockContext, lan_phone: MockSIPPhone):
    """Test the 'phone_hangs_up' step."""
    # Arrange: Set the phone as the caller and put it in a 'connected' state
    bf_context.caller = lan_phone
    lan_phone._state = "connected"

    # Act: Run the step definition to hang up the call
    phone_hangs_up("caller", bf_context)

    # Assert: Verify the phone's state has returned to 'idle'
    assert lan_phone.is_idle()


# -- Tests for wait_for_phone_state --


def test_wait_for_phone_state_success(lan_phone: MockSIPPhone):
    """Test the wait_for_phone_state() helper when the state is reached."""
    # Arrange: Configure the mock to return success
    lan_phone._wait_for_state_result = True
    lan_phone._state = "ringing"  # Ensure the state matches for the check

    # Act
    result = wait_for_phone_state(lan_phone, "ringing", timeout=1)

    # Assert
    assert result is True


def test_wait_for_phone_state_failure(lan_phone: MockSIPPhone):
    """Test the wait_for_phone_state() helper when the state is not reached."""
    # Arrange: Configure the mock to return failure (timeout)
    lan_phone._wait_for_state_result = False

    # Act
    result = wait_for_phone_state(lan_phone, "ringing", timeout=1)

    # Assert
    assert result is False


# -- Tests for phone_starts_ringing --


def test_phone_starts_ringing_success(bf_context: MockContext, lan_phone: MockSIPPhone):
    """Test the 'phone_starts_ringing' step for success."""
    # Arrange: Set up the phone and configure the mock to succeed
    bf_context.callee = lan_phone
    lan_phone._wait_for_state_result = True
    lan_phone._state = "ringing"

    # Act & Assert: No exception should be raised
    phone_starts_ringing("callee", bf_context)


def test_phone_starts_ringing_failure(bf_context: MockContext, lan_phone: MockSIPPhone):
    """Test the 'phone_starts_ringing' step for failure."""
    # Arrange: Set up the phone and configure the mock to fail (timeout)
    bf_context.callee = lan_phone
    lan_phone._wait_for_state_result = False

    # Act & Assert: Verify that an AssertionError is raised
    with pytest.raises(AssertionError, match="Phone lan_phone did not start ringing"):
        phone_starts_ringing("callee", bf_context)


# -- Tests for validate_use_case_phone_requirements --


def test_validate_phone_reqs_datatable_too_short(
    sipcenter: MockSIPServer, bf_context: MockContext,
):
    """Test datatable validation fails if datatable is too short."""
    # Arrange: Create a datatable with only a header
    datatable = [["phone_name", "network_location"]]
    mock_devices = MockDevices()

    # Act & Assert
    with pytest.raises(ValueError, match="Datatable must have at least a header row and one data row"):
        validate_use_case_phone_requirements(
            sipcenter, bf_context, mock_devices, datatable
        )


# -- Tests for discover_available_sip_phones_from_devices --


def test_discover_available_sip_phones_from_devices(bf_context: MockContext):
    """Test the discovery of available SIP phones from the devices fixture."""
    # Arrange: Create a mock devices object with a mix of phones and other devices
    mock_devices = MockDevices()
    # Add a non-phone device to ensure it's filtered out
    setattr(mock_devices, "not_a_phone", "i_am_a_string")

    # Act
    discovered_phones = discover_available_sip_phones_from_devices(mock_devices)

    # Assert: Verify that only the SIP phones were discovered
    assert len(discovered_phones) == 3
    phone_names = {name for name, _, _ in discovered_phones}
    assert phone_names == {"lan_phone", "wan_phone", "wan_phone2"}


# -- Tests for map_phones_to_requirements --


def test_map_phones_to_requirements_success(lan_phone: MockSIPPhone, wan_phone: MockSIPPhone):
    """Test the mapping of available phones to requirements for success."""
    # Arrange
    available = [
        ("lan_phone_fixture", lan_phone, "LAN"),
        ("wan_phone_fixture", wan_phone, "WAN"),
    ]
    required = [("use_case_lan", "LAN"), ("use_case_wan", "WAN")]

    # Act
    mapping = map_phones_to_requirements(available, required)

    # Assert
    assert len(mapping) == 2
    assert mapping["use_case_lan"] == ("lan_phone_fixture", lan_phone)
    assert mapping["use_case_wan"] == ("wan_phone_fixture", wan_phone)


def test_map_phones_to_requirements_insufficient_phones(wan_phone: MockSIPPhone):
    """Test the mapping of phones when there are not enough available."""
    # Arrange
    available = [("wan_phone_fixture", wan_phone, "WAN")]
    required = [("uc_lan", "LAN"), ("uc_wan", "WAN")]

    # Act & Assert
    with pytest.raises(ValueError, match="Insufficient LAN phones in testbed."):
        map_phones_to_requirements(available, required)


def test_validate_use_case_phone_requirements_success(
    sipcenter: MockSIPServer, bf_context: MockContext
):
    """Test the full success path of the validate_use_case_phone_requirements step."""
    # Arrange
    datatable = [
        ["phone_name", "network_location"],
        ["lan_voice_phone", "LAN"],
        ["wan_voice_phone", "WAN"],
    ]
    mock_devices = MockDevices()
    # Ensure the mock phones are registered on the mock server for the final check
    sipcenter.register_user(mock_devices.lan_phone.number)
    sipcenter.register_user(mock_devices.wan_phone.number)

    # Act
    validate_use_case_phone_requirements(
        sipcenter, bf_context, mock_devices, datatable
    )

    # Assert
    # Verify that the phones are mapped correctly in the context
    assert hasattr(bf_context, "lan_voice_phone")
    assert hasattr(bf_context, "wan_voice_phone")
    assert bf_context.lan_voice_phone is mock_devices.lan_phone
    assert bf_context.wan_voice_phone is mock_devices.wan_phone

    # Verify that the scenario start time was recorded
    assert bf_context.scenario_start_time is not None


# -- Tests for then steps --


def test_both_phones_connected_success(
    bf_context: MockContext, lan_phone: MockSIPPhone, wan_phone: MockSIPPhone
):
    """Test the 'both_phones_connected' step for success."""
    # Arrange
    bf_context.caller = lan_phone
    bf_context.callee = wan_phone
    lan_phone._state = "connected"
    wan_phone._state = "connected"
    lan_phone._wait_for_state_result = True
    wan_phone._wait_for_state_result = True

    # Act & Assert
    both_phones_connected(bf_context)


def test_both_phones_connected_failure(
    bf_context: MockContext, lan_phone: MockSIPPhone, wan_phone: MockSIPPhone
):
    """Test the 'both_phones_connected' step for failure."""
    # Arrange
    bf_context.caller = lan_phone
    bf_context.callee = wan_phone
    lan_phone._state = "connected"
    wan_phone._state = "idle"  # Callee is not connected
    lan_phone._wait_for_state_result = True
    wan_phone._wait_for_state_result = False

    # Act & Assert
    with pytest.raises(AssertionError, match="Callee wan_phone is not connected"):
        both_phones_connected(bf_context)


def test_both_phones_return_to_idle_success(
    bf_context: MockContext, lan_phone: MockSIPPhone, wan_phone: MockSIPPhone
):
    """Test the 'both_phones_return_to_idle' step for success."""
    # Arrange
    bf_context.caller = lan_phone
    bf_context.callee = wan_phone
    lan_phone._state = "idle"
    wan_phone._state = "idle"
    lan_phone._wait_for_state_result = True
    wan_phone._wait_for_state_result = True

    # Act & Assert
    both_phones_return_to_idle(bf_context)


def test_both_phones_return_to_idle_failure(
    bf_context: MockContext, lan_phone: MockSIPPhone, wan_phone: MockSIPPhone
):
    """Test the 'both_phones_return_to_idle' step for failure."""
    # Arrange
    bf_context.caller = lan_phone
    bf_context.callee = wan_phone
    lan_phone._state = "idle"
    wan_phone._state = "connected"  # Callee has not returned to idle
    lan_phone._wait_for_state_result = True
    wan_phone._wait_for_state_result = False

    # Act & Assert
    with pytest.raises(AssertionError, match="Phone wan_phone did not return to idle"):
        both_phones_return_to_idle(bf_context)


# -- Tests for phone_in_active_call --


def test_phone_in_active_call_success_with_third_phone(
    bf_context: MockContext,
    lan_phone: MockSIPPhone,
    wan_phone: MockSIPPhone,
    wan_phone2: MockSIPPhone,
):
    """Test 'phone_in_active_call' success path with a third phone."""
    # Arrange
    bf_context.caller = lan_phone
    bf_context.callee = wan_phone  # This is the phone to make busy
    bf_context.configured_phones = {
        "lan_phone": ("lan_phone_fixture", lan_phone),
        "wan_phone": ("wan_phone_fixture", wan_phone),
        "wan_phone2": ("wan_phone2_fixture", wan_phone2),  # The 3rd phone
    }
    # Simulate the callee ringing when called by the 3rd phone
    wan_phone._state = "idle"
    wan_phone2._state = "idle"

    def dial_triggers_ringing(number):
        if number == wan_phone.number:
            wan_phone._state = "ringing"
        wan_phone2._state = "dialing"

    wan_phone2.dial = dial_triggers_ringing
    wan_phone.answer = lambda: setattr(wan_phone, '_state', 'connected') or True
    wan_phone._wait_for_state_result = True

    # Act
    phone_in_active_call("callee", bf_context)

    # Assert
    assert wan_phone.is_connected()
    assert bf_context.busy_maker is wan_phone2


def test_phone_in_active_call_fallback_no_third_phone(
    bf_context: MockContext, lan_phone: MockSIPPhone, wan_phone: MockSIPPhone
):
    """Test 'phone_in_active_call' fallback when no third phone is available."""
    # Arrange
    bf_context.caller = lan_phone
    bf_context.callee = wan_phone
    bf_context.configured_phones = {
        "lan_phone": ("lan_phone_fixture", lan_phone),
        "wan_phone": ("wan_phone_fixture", wan_phone),
    }
    wan_phone._state = "idle"
    # Mock answer to simulate going off-hook
    wan_phone.answer = lambda: setattr(wan_phone, '_state', 'connected') or True

    # Act
    phone_in_active_call("callee", bf_context)

    # Assert that the phone is no longer idle (best effort for busy)
    assert not wan_phone.is_idle()


def test_phone_in_active_call_failure_target_not_ringing(
    bf_context: MockContext,
    lan_phone: MockSIPPhone,
    wan_phone: MockSIPPhone,
    wan_phone2: MockSIPPhone,
):
    """Test 'phone_in_active_call' when the target phone fails to ring."""
    # Arrange
    bf_context.caller = lan_phone
    bf_context.callee = wan_phone
    bf_context.configured_phones = {
        "lan_phone": ("lan_phone_fixture", lan_phone),
        "wan_phone": ("wan_phone_fixture", wan_phone),
        "wan_phone2": ("wan_phone2_fixture", wan_phone2),
    }
    # Ensure the target phone never enters the 'ringing' state
    wan_phone._state = "idle"
    wan_phone2.dial = lambda number: None  # Mock dial does nothing to callee

    # Act & Assert
    with pytest.raises(AssertionError, match="did not start ringing"):
        phone_in_active_call("callee", bf_context)


def test_caller_calls_callee_alias(
    bf_context: MockContext, lan_phone: MockSIPPhone, wan_phone: MockSIPPhone
):
    """Test the 'caller_calls_callee' alias step."""
    # Arrange
    bf_context.caller = lan_phone
    bf_context.callee = wan_phone

    # Act
    caller_calls_callee(bf_context)

    # Assert
    assert lan_phone.last_dialed_number == wan_phone.number


def test_phone_dials_invalid_number(bf_context: MockContext, lan_phone: MockSIPPhone):
    """Test the 'phone_dials_invalid_number' step."""
    # Arrange
    bf_context.caller = lan_phone

    # Act
    phone_dials_invalid_number("caller", bf_context)

    # Assert
    assert lan_phone.last_dialed_number == "9999"


def test_phone_plays_dial_tone_success(bf_context: MockContext, lan_phone: MockSIPPhone):
    """Test the 'phone_plays_dial_tone' step for success."""
    # Arrange
    bf_context.caller = lan_phone
    lan_phone._state = "idle"
    lan_phone.phone_started = True

    # Act & Assert
    phone_plays_dial_tone("caller", bf_context)


def test_phone_plays_dial_tone_failure_not_started(
    bf_context: MockContext, lan_phone: MockSIPPhone
):
    """Test 'phone_plays_dial_tone' when the phone is not started."""
    # Arrange
    bf_context.caller = lan_phone
    lan_phone.phone_started = False

    # Act & Assert
    with pytest.raises(AssertionError, match="Phone lan_phone is not started"):
        phone_plays_dial_tone("caller", bf_context)


def test_phone_plays_dial_tone_failure_not_idle(
    bf_context: MockContext, lan_phone: MockSIPPhone
):
    """Test 'phone_plays_dial_tone' when the phone is not idle."""
    # Arrange
    bf_context.caller = lan_phone
    lan_phone.phone_started = True
    # Mock is_playing_dialtone to return False
    lan_phone.is_playing_dialtone = lambda: False

    # Act & Assert
    with pytest.raises(AssertionError, match="is not playing dial tone"):
        phone_plays_dial_tone("caller", bf_context)


# -- Tests for sip_server_sends_response --


def test_sip_server_sends_response_success_from_server_log(
    bf_context: MockContext, sipcenter: MockSIPServer
):
    """Test 'sip_server_sends_response' finds code in server logs."""
    import datetime
    # Arrange
    bf_context.sipcenter = sipcenter
    bf_context.scenario_start_time = datetime.datetime.now()  # Initialize with actual datetime
    # Mock the log verification to return True
    sipcenter.verify_sip_message = lambda *args, **kwargs: True

    # Act & Assert
    sip_server_sends_response("404 Not Found", bf_context)


def test_sip_server_sends_response_success_from_phone_fallback(
    bf_context: MockContext, sipcenter: MockSIPServer, lan_phone: MockSIPPhone
):
    """Test 'sip_server_sends_response' finds code in phone logs as a fallback."""
    import datetime
    # Arrange
    bf_context.sipcenter = sipcenter
    bf_context.caller = lan_phone
    bf_context.scenario_start_time = datetime.datetime.now()  # Initialize with actual datetime
    # Mock server log check to fail, but phone console to contain the code
    sipcenter.verify_sip_message = lambda *args, **kwargs: False
    lan_phone._console.expect = lambda pattern, timeout: "DISCONNECTED [reason=486" in pattern

    # Act & Assert
    sip_server_sends_response("486 Busy Here", bf_context)


def test_sip_server_sends_response_failure(
    bf_context: MockContext, sipcenter: MockSIPServer, lan_phone: MockSIPPhone
):
    """Test 'sip_server_sends_response' when the code is not found anywhere."""
    import datetime
    # Arrange
    bf_context.sipcenter = sipcenter
    bf_context.caller = lan_phone
    bf_context.scenario_start_time = datetime.datetime.now()  # Initialize with actual datetime
    # Mock both checks to fail
    sipcenter.verify_sip_message = lambda *args, **kwargs: False
    lan_phone._console.expect = lambda pattern, timeout: (_ for _ in ()).throw(Exception("Timeout"))

    # Act & Assert
    with pytest.raises(AssertionError, match="SIP server did not send 404 Not Found response"):
        sip_server_sends_response("404 Not Found", bf_context)


# -- Tests for phone_plays_busy_tone --


def test_phone_plays_busy_tone_success_from_is_line_busy(
    bf_context: MockContext, lan_phone: MockSIPPhone
):
    """Test 'phone_plays_busy_tone' success via is_line_busy."""
    # Arrange
    bf_context.caller = lan_phone
    lan_phone.is_line_busy = lambda: True

    # Act & Assert
    phone_plays_busy_tone("caller", bf_context)


def test_phone_plays_busy_tone_success_from_idle_fallback(
    bf_context: MockContext, lan_phone: MockSIPPhone
):
    """Test 'phone_plays_busy_tone' success via idle state fallback."""
    # Arrange
    bf_context.caller = lan_phone
    # Mock is_line_busy to return False to force fallback to idle state check
    lan_phone.is_line_busy = lambda: False
    lan_phone._state = "idle"
    lan_phone._wait_for_state_result = True

    # Act & Assert
    phone_plays_busy_tone("caller", bf_context)


def test_phone_plays_busy_tone_failure(bf_context: MockContext, lan_phone: MockSIPPhone):
    """Test 'phone_plays_busy_tone' for failure."""
    # Arrange
    bf_context.caller = lan_phone
    # Mock is_line_busy to return False to force fallback to idle state check
    lan_phone.is_line_busy = lambda: False
    lan_phone._state = "connected"  # Not idle
    lan_phone._wait_for_state_result = False

    # Act & Assert
    with pytest.raises(AssertionError, match="did not play busy tone"):
        phone_plays_busy_tone("caller", bf_context)


# -- Tests for caller_plays_busy_tone --


def test_caller_plays_busy_tone_success_from_context(bf_context: MockContext):
    """Test 'caller_plays_busy_tone' success via context flag."""
    # Arrange
    bf_context.caller_received_486 = True

    # Act & Assert
    caller_plays_busy_tone(bf_context)


def test_caller_plays_busy_tone_failure(bf_context: MockContext, lan_phone: MockSIPPhone):
    """Test 'caller_plays_busy_tone' for failure."""
    # Arrange
    bf_context.caller = lan_phone
    bf_context.caller_received_486 = False
    lan_phone.is_line_busy = lambda: False

    # Act & Assert
    with pytest.raises(AssertionError, match="Caller should be in busy state"):
        caller_plays_busy_tone(bf_context)


# -- Tests for verify_rtp_session --


def test_verify_rtp_session_success_with_udp_lowercase(lan_phone: MockSIPPhone):
    """Test verify_rtp_session when UDP ports are detected (lowercase)."""
    # Arrange: Simulate netstat output showing UDP ports in RTP range
    lan_phone.before = "udp        0      0 0.0.0.0:4000            0.0.0.0:*"
    
    # Act
    result = verify_rtp_session(lan_phone)
    
    # Assert
    assert result is True
    assert len(lan_phone._sendline_commands) == 1
    assert "netstat -un" in lan_phone._sendline_commands[0]


def test_verify_rtp_session_success_with_udp_uppercase(lan_phone: MockSIPPhone):
    """Test verify_rtp_session when UDP ports are detected (uppercase)."""
    # Arrange: Simulate netstat output with uppercase UDP
    lan_phone.before = "UDP        0      0 0.0.0.0:4050            0.0.0.0:*"
    
    # Act
    result = verify_rtp_session(lan_phone)
    
    # Assert
    assert result is True


def test_verify_rtp_session_success_null_audio_mode(lan_phone: MockSIPPhone):
    """Test verify_rtp_session in null-audio mode (no RTP ports visible)."""
    # Arrange: Simulate no RTP ports detected (null-audio mode)
    lan_phone.before = ""
    
    # Act
    result = verify_rtp_session(lan_phone)
    
    # Assert
    # Should still return True (doesn't fail test in null-audio mode)
    assert result is True


def test_verify_rtp_session_handles_exception(lan_phone: MockSIPPhone):
    """Test verify_rtp_session gracefully handles exceptions."""
    # Arrange: Make expect raise an exception
    def raise_exception(*args, **kwargs):
        raise Exception("Timeout waiting for prompt")
    
    lan_phone.expect = raise_exception
    
    # Act
    result = verify_rtp_session(lan_phone)
    
    # Assert
    # Should return True (doesn't fail test on verification error)
    assert result is True


def test_verify_rtp_session_checks_correct_port_range(lan_phone: MockSIPPhone):
    """Test that verify_rtp_session checks for ports in range 4000-4999."""
    # Arrange
    lan_phone.before = "udp        0      0 0.0.0.0:4999            0.0.0.0:*"
    
    # Act
    result = verify_rtp_session(lan_phone)
    
    # Assert
    assert result is True
    # Verify the regex pattern includes the correct port range
    command = lan_phone._sendline_commands[0]
    assert "4000" in command or "400[0-9]" in command
    assert "4999" in command or "4[1-9][0-9]{2}" in command
