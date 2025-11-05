"""Background step definitions for BDD tests."""

from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from pytest_bdd import given
from pytest_boardfarm3.boardfarm_fixtures import bf_context

from tests.step_defs.helpers import get_console_uptime_seconds, gpv_value


@given("a CPE is online and fully provisioned")
def cpe_is_online_and_provisioned(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any
) -> None:
    """Black-box: confirm online/provisioned state via ACS and store baseline state."""
    cpe_id = cpe.sw.cpe_id

    # Store original firmware version for later comparison (from ACS).
    bf_context.original_firmware = gpv_value(
        acs, cpe, "Device.DeviceInfo.SoftwareVersion"
    )

    # Store initial uptime from console for reliable reboot detection.
    bf_context.initial_uptime = get_console_uptime_seconds(cpe)

