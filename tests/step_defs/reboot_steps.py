"""Reboot-related step definitions."""

from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from pytest_bdd import then

from .helpers import get_console_uptime_seconds


@then("the CPE does not reboot")
def cpe_does_not_reboot(acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any) -> None:
    """Verify the CPE does not reboot by checking that its uptime has increased."""
    import time
    time.sleep(5)
    current_uptime = get_console_uptime_seconds(cpe)

    assert bf_context.initial_uptime, "Initial uptime was not set in a previous step"
    assert current_uptime > bf_context.initial_uptime, (
        f"CPE appears to have rebooted. "
        f"Initial uptime: {bf_context.initial_uptime}, Current uptime: {current_uptime}"
    )
    print(
        f"Verified that CPE did not reboot. Uptime increased from {bf_context.initial_uptime} to {current_uptime}."
    )

