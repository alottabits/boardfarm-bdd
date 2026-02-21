"""Unit tests for Robot Framework voice keywords.

Tests the device discovery keywords: discover_phones_by_location,
Discover Phones By Location, Assign Phones For Scenario.

Validates both assessment outcomes per UNIT_TEST_STRATEGY:
- Statement is true (phones available, classification succeeds) → keyword passes
- Statement is not true (insufficient phones, unknown location) → keyword fails

Structure mirrors tests/unit/test_step_defs/.
"""

import pytest

from tests.unit.mocks import MockSIPPhone

from .voice_keywords_loader import (
    VoiceKeywords,
    discover_phones_by_location,
)


# =============================================================================
# discover_phones_by_location (module-level function)
# =============================================================================


def test_discover_phones_by_location_success_by_name(
    lan_phone: MockSIPPhone, wan_phone: MockSIPPhone
):
    """Statement is true: phones with lan/wan name prefix → correct classification."""
    phones = {"lan_phone": lan_phone, "wan_phone": wan_phone}

    result = discover_phones_by_location(phones)

    assert result["LAN"] == [lan_phone]
    assert result["WAN"] == [wan_phone]


def test_discover_phones_by_location_success_by_options():
    """Statement is true: phones with dev.options metadata → correct classification."""
    lan = MockSIPPhone(name="phone_a", number="1000")
    lan.dev = type("Dev", (), {"options": "lan-ip-dhcp"})()
    wan = MockSIPPhone(name="phone_b", number="2000")
    wan.dev = type("Dev", (), {"options": "wan-static-ip"})()
    phones = {"phone_a": lan, "phone_b": wan}

    result = discover_phones_by_location(phones)

    assert result["LAN"] == [lan]
    assert result["WAN"] == [wan]


def test_discover_phones_by_location_empty_dict():
    """Statement is true: empty dict → returns empty LAN and WAN lists."""
    result = discover_phones_by_location({})

    assert result["LAN"] == []
    assert result["WAN"] == []


def test_discover_phones_by_location_skips_unclassifiable(lan_phone: MockSIPPhone):
    """Phones that cannot be classified (no options, name not lan/wan) are skipped."""
    unknown = MockSIPPhone(name="foo", number="9999")
    phones = {"lan_phone": lan_phone, "unknown_phone": unknown}

    result = discover_phones_by_location(phones)

    assert result["LAN"] == [lan_phone]
    assert result["WAN"] == []


def test_discover_phones_by_location_multiple_per_type(
    lan_phone: MockSIPPhone,
    wan_phone: MockSIPPhone,
    wan_phone2: MockSIPPhone,
):
    """Multiple LAN and WAN phones → all classified correctly."""
    lan2 = MockSIPPhone(name="lan_phone2", number="1001")
    phones = {
        "lan_phone": lan_phone,
        "lan_phone2": lan2,
        "wan_phone": wan_phone,
        "wan_phone2": wan_phone2,
    }

    result = discover_phones_by_location(phones)

    assert result["LAN"] == [lan_phone, lan2]
    assert result["WAN"] == [wan_phone, wan_phone2]


# =============================================================================
# Discover Phones By Location (keyword)
# =============================================================================


def test_discover_phones_by_location_keyword_success(
    voice_keywords_lib: VoiceKeywords,
    lan_phone: MockSIPPhone,
    wan_phone: MockSIPPhone,
):
    """Keyword wraps discover_phones_by_location correctly."""
    phones = {"lan_phone": lan_phone, "wan_phone": wan_phone}

    result = voice_keywords_lib.discover_phones_by_location_keyword(phones)

    assert result["LAN"] == [lan_phone]
    assert result["WAN"] == [wan_phone]


# =============================================================================
# Assign Phones For Scenario (keyword)
# =============================================================================


def test_assign_phones_for_scenario_lan_wan_success(
    voice_keywords_lib: VoiceKeywords,
    lan_phone: MockSIPPhone,
    wan_phone: MockSIPPhone,
):
    """Statement is true: LAN caller, WAN callee, sufficient phones → returns (caller, callee)."""
    lan_phones = [lan_phone]
    wan_phones = [wan_phone]

    caller, callee = voice_keywords_lib.assign_phones_for_scenario(
        "LAN", "WAN", lan_phones, wan_phones
    )

    assert caller is lan_phone
    assert callee is wan_phone
    assert voice_keywords_lib._caller is caller
    assert voice_keywords_lib._callee is callee


def test_assign_phones_for_scenario_lan_wan2_success(
    voice_keywords_lib: VoiceKeywords,
    lan_phone: MockSIPPhone,
    wan_phone: MockSIPPhone,
    wan_phone2: MockSIPPhone,
):
    """Statement is true: LAN caller, WAN2 callee, 2 WAN phones → returns correct pair."""
    lan_phones = [lan_phone]
    wan_phones = [wan_phone, wan_phone2]

    caller, callee = voice_keywords_lib.assign_phones_for_scenario(
        "LAN", "WAN2", lan_phones, wan_phones
    )

    assert caller is lan_phone
    assert callee is wan_phone2


def test_assign_phones_for_scenario_wan_wan2_success(
    voice_keywords_lib: VoiceKeywords,
    wan_phone: MockSIPPhone,
    wan_phone2: MockSIPPhone,
):
    """Statement is true: WAN caller, WAN2 callee → both from WAN list."""
    lan_phones = []
    wan_phones = [wan_phone, wan_phone2]

    caller, callee = voice_keywords_lib.assign_phones_for_scenario(
        "WAN", "WAN2", lan_phones, wan_phones
    )

    assert caller is wan_phone
    assert callee is wan_phone2


def test_assign_phones_for_scenario_no_lan_phone_fails(
    voice_keywords_lib: VoiceKeywords,
    wan_phone: MockSIPPhone,
):
    """Statement is not true: LAN required but no LAN phone → AssertionError."""
    lan_phones = []
    wan_phones = [wan_phone]

    with pytest.raises(AssertionError, match="No LAN phone available"):
        voice_keywords_lib.assign_phones_for_scenario(
            "LAN", "WAN", lan_phones, wan_phones
        )


def test_assign_phones_for_scenario_no_wan_phone_fails(
    voice_keywords_lib: VoiceKeywords,
    lan_phone: MockSIPPhone,
):
    """Statement is not true: WAN required but no WAN phone → AssertionError."""
    lan_phones = [lan_phone]
    wan_phones = []

    with pytest.raises(AssertionError, match="No WAN phone available"):
        voice_keywords_lib.assign_phones_for_scenario(
            "LAN", "WAN", lan_phones, wan_phones
        )


def test_assign_phones_for_scenario_wan2_insufficient_wan_fails(
    voice_keywords_lib: VoiceKeywords,
    lan_phone: MockSIPPhone,
    wan_phone: MockSIPPhone,
):
    """Statement is not true: WAN2 required but only 1 WAN phone → AssertionError."""
    lan_phones = [lan_phone]
    wan_phones = [wan_phone]

    with pytest.raises(AssertionError, match="Need at least 2 WAN phones for WAN2"):
        voice_keywords_lib.assign_phones_for_scenario(
            "LAN", "WAN2", lan_phones, wan_phones
        )


def test_assign_phones_for_scenario_unknown_location_fails(
    voice_keywords_lib: VoiceKeywords,
    lan_phone: MockSIPPhone,
    wan_phone: MockSIPPhone,
):
    """Statement is not true: unknown location → ValueError."""
    lan_phones = [lan_phone]
    wan_phones = [wan_phone]

    with pytest.raises(ValueError, match="Unknown location.*INVALID"):
        voice_keywords_lib.assign_phones_for_scenario(
            "LAN", "INVALID", lan_phones, wan_phones
        )
