"""CPE configuration step definitions."""

from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from pytest_bdd import given, parsers
from pytest_boardfarm3.boardfarm_fixtures import bf_context


@given(
    parsers.parse(
        'the user has set the CPE GUI username to "{username}" and password to "{password}"'
    )
)
def user_sets_cpe_credentials(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any, username: str, password: str
) -> None:
    """Set the CPE's GUI login credentials via the ACS."""
    param_values = {
        "Device.Users.User.1.Username": username,
        "Device.Users.User.1.Password": password,
    }
    acs.SPV(param_values, cpe_id=cpe.sw.cpe_id)
    bf_context.custom_username = username
    bf_context.custom_password = password
    print(f"Set CPE credentials to {username}/{password} via ACS")


@given(parsers.parse('the user has set the SSID to "{ssid}"'))
def user_sets_ssid(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any, ssid: str
) -> None:
    """Set the CPE's Wi-Fi SSID via the ACS."""
    param_value = {"Device.WiFi.SSID.1.SSID": ssid}
    acs.SPV(param_value, cpe_id=cpe.sw.cpe_id)
    bf_context.custom_ssid = ssid
    print(f"Set SSID to {ssid} via ACS")




