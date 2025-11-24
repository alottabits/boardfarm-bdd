"""
ACS UI Helper Functions

Provides reusable UI automation functions for GenieACS.
Selectors are loaded from YAML configuration files for easy maintenance.
"""

from pathlib import Path
from typing import Any, Dict, Tuple

import yaml
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class ACSUIHelpers:
    """Reusable UI helper functions for ACS automation.
    
    This class provides high-level UI operations that can be used in step definitions.
    All UI selectors are loaded from YAML configuration files, making them easy to
    update when the UI changes without modifying code.
    
    Example usage in step definitions:
        @when("operator initiates reboot via UI")
        def step(acs_ui_helpers, cpe):
            acs_ui_helpers.login()
            acs_ui_helpers.navigate_to_device(cpe_id)
            acs_ui_helpers.click_reboot_button()
    """
    
    def __init__(self, ui_driver_info: Dict[str, Any], acs_version: str = "default"):
        """Initialize ACS UI helpers.
        
        Args:
            ui_driver_info: Dictionary containing driver, base_url, username, password
            acs_version: GenieACS version to load selectors for (default: "default")
        """
        self.driver = ui_driver_info["driver"]
        self.base_url = ui_driver_info["base_url"]
        self.username = ui_driver_info["username"]
        self.password = ui_driver_info["password"]
        self.wait = WebDriverWait(self.driver, 20)
        
        # Load selectors from version-specific config
        self.selectors = self._load_selectors(acs_version)
        self._logged_in = False
    
    def _load_selectors(self, version: str) -> Dict[str, Any]:
        """Load UI selectors from YAML configuration.
        
        Args:
            version: GenieACS version (e.g., "1.2.8" or "default")
        
        Returns:
            Dictionary of selectors organized by page
        """
        # Try version-specific config first
        version_config = Path(__file__).parent / f"acs_ui_selectors_v{version}.yaml"
        if version_config.exists():
            with open(version_config) as f:
                return yaml.safe_load(f)
        
        # Fall back to default config
        default_config = Path(__file__).parent / "acs_ui_selectors.yaml"
        with open(default_config) as f:
            return yaml.safe_load(f)
    
    def _get_locator(self, selector_path: str, **kwargs) -> Tuple[str, str]:
        """Get locator from configuration with optional formatting.
        
        Args:
            selector_path: Dot-notation path to selector (e.g., "login.username_field")
            **kwargs: Variables to format into selector (e.g., cpe_id="ABC-123")
        
        Returns:
            Tuple of (By.TYPE, selector_string)
        
        Example:
            # Get static selector
            locator = self._get_locator("login.username_field")
            # Returns: (By.NAME, "username")
            
            # Get dynamic selector with formatting
            locator = self._get_locator("device_list.device_link", cpe_id="ABC-123")
            # Returns: (By.CSS_SELECTOR, "a[href='/devices/ABC-123']")
        """
        # Navigate nested dict using dot notation
        parts = selector_path.split(".")
        value = self.selectors
        for part in parts:
            value = value[part]
        
        # Format selector with kwargs if provided
        if kwargs:
            selector = value["selector"].format(**kwargs)
        else:
            selector = value["selector"]
        
        # Convert string to By constant
        by_type = getattr(By, value["by"].upper())
        
        return (by_type, selector)
    
    def login(self) -> None:
        """Login to ACS UI.
        
        Uses credentials from ui_driver_info and selectors from config.
        Skips if already logged in.
        """
        if self._logged_in:
            return
        
        self.driver.get(f"{self.base_url}/login")
        
        # Find and fill username field
        username_field = self.wait.until(
            EC.presence_of_element_located(
                self._get_locator("login.username_field")
            )
        )
        username_field.send_keys(self.username)
        
        # Find and fill password field
        password_field = self.driver.find_element(
            *self._get_locator("login.password_field")
        )
        password_field.send_keys(self.password)
        
        # Click login button
        login_btn = self.driver.find_element(
            *self._get_locator("login.login_button")
        )
        login_btn.click()
        
        # Wait for redirect away from login page
        self.wait.until(lambda d: "/login" not in d.current_url)
        self._logged_in = True
    
    def navigate_to_device(self, cpe_id: str) -> None:
        """Navigate to device details page.
        
        Args:
            cpe_id: CPE identifier (e.g., "ABC-CPE-123456")
        """
        # Ensure logged in
        self.login()
        
        # Navigate to device list
        self.driver.get(f"{self.base_url}/devices")
        
        # Search for device
        search_box = self.wait.until(
            EC.presence_of_element_located(
                self._get_locator("device_list.search_box")
            )
        )
        search_box.clear()
        search_box.send_keys(cpe_id)
        
        # Wait a moment for search results to update
        import time
        time.sleep(1)
        
        # Click on device link
        device_link = self.wait.until(
            EC.element_to_be_clickable(
                self._get_locator("device_list.device_link", cpe_id=cpe_id)
            )
        )
        device_link.click()
        
        # Wait for device details page to load
        self.wait.until(EC.url_contains(f"/devices/{cpe_id}"))
    
    def click_reboot_button(self) -> None:
        """Click the Reboot button on device details page.
        
        Handles confirmation dialog if present.
        """
        # Wait for and click reboot button
        reboot_btn = self.wait.until(
            EC.element_to_be_clickable(
                self._get_locator("device_details.reboot_button")
            )
        )
        reboot_btn.click()
        
        # Handle confirmation dialog if present
        try:
            confirm_btn = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable(
                    self._get_locator("device_details.confirm_button")
                )
            )
            confirm_btn.click()
        except:
            # No confirmation dialog
            pass
    
    def click_refresh_button(self) -> None:
        """Click the Refresh button to trigger connection request."""
        refresh_btn = self.wait.until(
            EC.element_to_be_clickable(
                self._get_locator("device_details.refresh_button")
            )
        )
        refresh_btn.click()
    
    def get_parameter_value(self, param_name: str) -> str:
        """Get the value of a parameter from the UI.
        
        Args:
            param_name: Parameter name (e.g., "Device.DeviceInfo.SoftwareVersion")
        
        Returns:
            Parameter value as string
        """
        # This would need to be implemented based on actual UI structure
        # Example implementation:
        param_row = self.wait.until(
            EC.presence_of_element_located(
                self._get_locator("device_details.parameter_row", param=param_name)
            )
        )
        value_cell = param_row.find_element(
            *self._get_locator("device_details.parameter_value")
        )
        return value_cell.text
    
    def wait_for_task_completion(self, timeout: int = 60) -> bool:
        """Wait for pending tasks to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
        
        Returns:
            True if tasks completed, False if timeout
        """
        try:
            # Wait for task status to show completion
            # This is a simplified example - actual implementation depends on UI
            self.wait.until(
                EC.text_to_be_present_in_element(
                    self._get_locator("device_details.task_status"),
                    "completed"
                )
            )
            return True
        except:
            return False
