"""Root conftest.py - Fixtures, shared helpers, and step definition imports.

This file contains:
- Pytest fixtures for device access (CPE, ACS, WAN)
- Shared helper functions used across step definitions
- Imports all step definition modules so pytest-bdd can discover them
"""

import pytest
from boardfarm3.lib.device_manager import DeviceManager
from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from boardfarm3.templates.wan import WAN as WanTemplate

# Import all step definition modules so pytest-bdd can discover them
# The 'noqa: F401' comments tell linters these imports are intentional (side effects)
from tests.step_defs import (  # noqa: F401
    acs_steps,
    background_steps,
    cpe_config_steps,
    firmware_steps,
    provisioning_steps,
    verification_steps,
)


# Import shared helpers from the helpers module
# This allows step definitions to import from helpers reliably
from tests.step_defs.helpers import (
    get_console_uptime_seconds,
    gpv_value,
    install_file_on_http_server,
)

# Expose helpers with original names for backward compatibility
# (if any code still uses the underscore-prefixed names)
_gpv_value = gpv_value
_get_console_uptime_seconds = get_console_uptime_seconds
_install_file_on_http_server = install_file_on_http_server


# Fixtures for easy device access
@pytest.fixture(scope="session")
def CPE(device_manager: DeviceManager) -> CpeTemplate:
    """Fixture providing access to the CPE device."""
    return device_manager.get_device_by_type(CpeTemplate)  # type: ignore[type-abstract]


@pytest.fixture(scope="session")
def ACS(device_manager: DeviceManager) -> AcsTemplate:
    """Fixture providing access to the ACS (Auto Configuration Server) device."""
    return device_manager.get_device_by_type(AcsTemplate)  # type: ignore[type-abstract]


@pytest.fixture(scope="session")
def WAN(device_manager: DeviceManager) -> WanTemplate:
    """Fixture providing access to the WAN device (acts as HTTP server for firmware files)."""
    return device_manager.get_device_by_type(WanTemplate)  # type: ignore[type-abstract]


@pytest.fixture(scope="session")
def http_server(WAN: WanTemplate) -> WanTemplate:
    """Alias fixture for WAN device, emphasizing its role as HTTP server for firmware files."""
    return WAN
