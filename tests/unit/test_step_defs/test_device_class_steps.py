"""Unit tests for device class step definitions."""

from unittest.mock import MagicMock, Mock

import pytest
from boardfarm3.devices.rpiprplos_cpe import RPiPrplOSCPE

from tests.step_defs.device_class_steps import (
    boardfarm_boots_device,
    boardfarm_connects_console,
    boardfarm_instantiates_device,
    device_comes_online,
)


@pytest.fixture
def mock_device_manager():
    """Mock device manager."""
    dm = Mock()
    return dm


def test_boardfarm_instantiates_device(mock_device_manager):
    """Unit test for device instantiation step."""
    mock_cpe = Mock(spec=RPiPrplOSCPE)
    mock_device_manager.get_device_by_type.return_value = mock_cpe

    result = boardfarm_instantiates_device(mock_device_manager)

    assert result == mock_cpe
    mock_device_manager.get_device_by_type.assert_called_once_with(RPiPrplOSCPE)


def test_boardfarm_connects_console(mock_device_manager):
    """Unit test for console connection step."""
    mock_cpe = Mock(spec=RPiPrplOSCPE)
    # Mock hw.get_console returning a mock console
    mock_cpe.hw.get_console.return_value = Mock()
    mock_device_manager.get_device_by_type.return_value = mock_cpe

    boardfarm_connects_console(mock_device_manager)

    mock_cpe.hw.get_console.assert_called_with("console")


def test_device_comes_online(mock_device_manager):
    """Unit test for device online verification."""
    mock_cpe = Mock(spec=RPiPrplOSCPE)
    mock_cpe.sw.is_online.return_value = True
    mock_device_manager.get_device_by_type.return_value = mock_cpe

    device_comes_online(mock_device_manager)

    mock_cpe.sw.is_online.assert_called_once()
