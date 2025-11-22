# GenieACS UI Automation Approach - Advisory Document

## Executive Summary

This document explores approaches for introducing UI-based methods in the `GenieACS` device class to complement the existing NBI (Northbound Interface) API methods. The goal is to provide a consistent API for test automation while hiding implementation details, whether using NBI or UI interactions.

## Current State Analysis

### Existing Architecture

The current implementation follows a clean separation of concerns:

```
Test Layer (pytest-bdd)
    ↓
Step Definitions (boardfarm-bdd/tests/step_defs/)
    ↓
Device Class Methods (boardfarm/boardfarm3/devices/genie_acs.py)
    ↓
GenieACS NBI API (HTTP/REST)
```

**Key Characteristics:**
- Device class provides abstract methods: `Reboot()`, `GPV()`, `SPV()`, `Download()`, etc.
- Methods hide implementation details (HTTP requests, authentication, error handling)
- Consistent interface across different ACS implementations (GenieACS, AxirosACS, etc.)
- Step definitions use device methods without knowing the underlying protocol

### Existing GUI Framework

The codebase already has a Selenium-based GUI automation framework:

**Location:** `boardfarm/boardfarm3/lib/gui/`

**Components:**
- `gui_helper.py`: WebDriver setup, screenshot capture, event listeners
- `prplos/pages/`: Page Object Model (POM) for PrplOS CPE GUI
  - `prplos_base_pom.py`: Base class for all page objects
  - `login.py`, `home.py`, `wifi.py`: Specific page implementations

**Pattern Used:**
```python
class HomePage(PrplOSBasePOM):
    def __init__(self, driver, gw_ip, fluent_wait=20):
        super().__init__(driver, gw_ip, fluent_wait)
        self.wait.until(self.is_page_loaded)
    
    @property
    def system_info_element(self) -> WebElement:
        return get_element_by_css(self, "div.col-md-3:nth-child(1)")
```

## Proposed Approaches

### Approach 1: Dual-Method Pattern (Recommended)

Create parallel UI-based methods alongside existing NBI methods, with clear naming conventions.

#### Architecture

```
GenieACS Device Class
├── NBI Methods (existing)
│   ├── Reboot(cpe_id, CommandKey)
│   ├── GPV(param, timeout, cpe_id)
│   └── SPV(param_value, timeout, cpe_id)
│
└── UI Methods (new)
    ├── Reboot_UI(cpe_id, CommandKey)
    ├── GPV_UI(param, timeout, cpe_id)
    └── SPV_UI(param_value, timeout, cpe_id)
```

#### Implementation Strategy

```python
# File: boardfarm/boardfarm3/devices/genie_acs.py

class GenieACS(LinuxDevice, ACS):
    """GenieACS connection class for TR-069 operations."""
    
    def __init__(self, config: dict, cmdline_args: Namespace) -> None:
        super().__init__(config, cmdline_args)
        self._client: httpx.Client | None = None
        self._cpeid: str | None = None
        self._base_url: str | None = None
        self._ui_helper: GenieACSUIHelper | None = None  # NEW
    
    def _init_ui_helper(self) -> None:
        """Initialize UI automation helper."""
        if self._ui_helper is None:
            self._ui_helper = GenieACSUIHelper(
                base_url=self._base_url,
                username=self.config.get("http_username", "admin"),
                password=self.config.get("http_password", "admin"),
            )
    
    # Existing NBI method
    def Reboot(self, CommandKey: str = "reboot", cpe_id: str | None = None) -> list[dict]:
        """Execute Reboot RPC via GenieACS NBI API."""
        # ... existing implementation ...
    
    # New UI method
    def Reboot_UI(self, CommandKey: str = "reboot", cpe_id: str | None = None) -> list[dict]:
        """Execute Reboot via GenieACS UI.
        
        Provides the same interface as Reboot() but uses UI automation
        instead of NBI API. Useful for testing UI workflows or when
        NBI access is restricted.
        
        :param CommandKey: reboot command key, defaults to "reboot"
        :param cpe_id: CPE identifier
        :return: reboot task creation response (empty list for compatibility)
        """
        self._init_ui_helper()
        return self._ui_helper.reboot_device(cpe_id, CommandKey)
```

#### Advantages
- ✅ Clear separation between NBI and UI methods
- ✅ Backward compatible (existing tests unchanged)
- ✅ Easy to switch between NBI and UI in tests
- ✅ Consistent return types and error handling

#### Disadvantages
- ⚠️ Code duplication (two methods for same functionality)
- ⚠️ Maintenance overhead (keep both methods in sync)

---

### Approach 2: Strategy Pattern with Configuration

Use a strategy pattern where the implementation (NBI vs UI) is selected via configuration.

#### Architecture

```python
class GenieACS(LinuxDevice, ACS):
    def __init__(self, config: dict, cmdline_args: Namespace) -> None:
        super().__init__(config, cmdline_args)
        
        # Select strategy based on config
        self._strategy = config.get("acs_interaction_mode", "nbi")  # "nbi" or "ui"
        
        if self._strategy == "nbi":
            self._backend = GenieACSNBIBackend(config)
        elif self._strategy == "ui":
            self._backend = GenieACSUIBackend(config)
    
    def Reboot(self, CommandKey: str = "reboot", cpe_id: str | None = None) -> list[dict]:
        """Execute Reboot RPC (via configured strategy)."""
        return self._backend.reboot(cpe_id, CommandKey)
```

#### Advantages
- ✅ Single method interface
- ✅ Easy to switch between NBI and UI globally
- ✅ Reduces code duplication

#### Disadvantages
- ⚠️ Cannot mix NBI and UI in same test
- ⚠️ More complex architecture
- ⚠️ Harder to debug (indirection through strategy)

---

### Approach 3: Page Object Model for GenieACS UI

Create a dedicated POM structure for GenieACS UI, similar to the existing PrplOS POM.

#### Proposed Structure

```
boardfarm/boardfarm3/lib/gui/genieacs/
├── __init__.py
├── pages/
│   ├── __init__.py
│   ├── genieacs_base_pom.py      # Base class for all GenieACS pages
│   ├── login.py                   # Login page
│   ├── device_list.py             # Device list/overview page
│   ├── device_details.py          # Individual device details page
│   ├── tasks.py                   # Tasks page
│   └── page_helper.py             # Helper functions
└── genieacs_ui_helper.py          # Main UI helper class
```

#### Example Implementation

```python
# File: boardfarm/boardfarm3/lib/gui/genieacs/pages/genieacs_base_pom.py

from __future__ import annotations
from typing import TYPE_CHECKING
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

class GenieACSBasePOM:
    """Base Page Object Model for GenieACS UI."""
    
    def __init__(self, driver: WebDriver, base_url: str, fluent_wait: int = 20):
        self.driver = driver
        self.base_url = base_url
        self.fluent_wait = fluent_wait
        self.wait = WebDriverWait(driver, fluent_wait)
    
    def is_page_loaded(self, driver: WebDriver) -> bool:
        """Must be overridden in derived class."""
        raise NotImplementedError
```

```python
# File: boardfarm/boardfarm3/lib/gui/genieacs/pages/device_details.py

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from .genieacs_base_pom import GenieACSBasePOM

class DeviceDetailsPage(GenieACSBasePOM):
    """Page Object for GenieACS Device Details page."""
    
    # Locators
    REBOOT_BUTTON = (By.CSS_SELECTOR, "button[title='Reboot']")
    REFRESH_BUTTON = (By.CSS_SELECTOR, "button[title='Refresh']")
    DEVICE_ID_HEADER = (By.CSS_SELECTOR, "h3.device-id")
    TASK_STATUS = (By.CSS_SELECTOR, ".task-status")
    
    def __init__(self, driver, base_url, cpe_id, fluent_wait=20):
        super().__init__(driver, base_url, fluent_wait)
        self.cpe_id = cpe_id
        self.navigate_to_device()
        self.wait.until(self.is_page_loaded)
    
    def navigate_to_device(self):
        """Navigate to device details page."""
        url = f"{self.base_url}/devices/{self.cpe_id}"
        self.driver.get(url)
    
    def is_page_loaded(self, driver) -> bool:
        """Check if device details page is loaded."""
        try:
            device_id_element = self.wait.until(
                EC.presence_of_element_located(self.DEVICE_ID_HEADER)
            )
            return device_id_element.is_displayed()
        except:
            return False
    
    def click_reboot_button(self) -> None:
        """Click the Reboot button."""
        reboot_btn = self.wait.until(
            EC.element_to_be_clickable(self.REBOOT_BUTTON)
        )
        reboot_btn.click()
    
    def get_task_status(self) -> str:
        """Get current task status."""
        status_element = self.wait.until(
            EC.presence_of_element_located(self.TASK_STATUS)
        )
        return status_element.text
```

```python
# File: boardfarm/boardfarm3/lib/gui/genieacs/genieacs_ui_helper.py

from typing import TYPE_CHECKING
from boardfarm3.lib.gui.gui_helper import GuiHelperNoProxy
from .pages.login import LoginPage
from .pages.device_details import DeviceDetailsPage

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

class GenieACSUIHelper:
    """Helper class for GenieACS UI automation."""
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password
        self._driver: WebDriver | None = None
        self._gui_helper = GuiHelperNoProxy(default_delay=20, headless=True)
    
    def _get_driver(self) -> WebDriver:
        """Get or create WebDriver instance."""
        if self._driver is None:
            self._driver = self._gui_helper.get_web_driver()
        return self._driver
    
    def login(self) -> None:
        """Login to GenieACS UI."""
        driver = self._get_driver()
        login_page = LoginPage(driver, self.base_url)
        login_page.login(self.username, self.password)
    
    def reboot_device(self, cpe_id: str, command_key: str = "reboot") -> list[dict]:
        """Reboot a device via UI.
        
        :param cpe_id: CPE identifier
        :param command_key: Command key for reboot task
        :return: Empty list for compatibility with NBI method
        """
        self.login()
        driver = self._get_driver()
        
        # Navigate to device details page
        device_page = DeviceDetailsPage(driver, self.base_url, cpe_id)
        
        # Click reboot button
        device_page.click_reboot_button()
        
        # Wait for task to be created
        # (In real implementation, you'd wait for confirmation dialog, etc.)
        
        return []  # Return empty list for compatibility
    
    def close(self) -> None:
        """Close WebDriver."""
        if self._driver:
            self._driver.quit()
            self._driver = None
```

---

## Charting UI Interactions

### Step 1: UI Discovery Process

To systematically chart GenieACS UI interactions, follow this process:

#### 1.1 Manual Exploration
1. **Access GenieACS UI** in a browser
2. **Document each page** with screenshots
3. **Identify key elements** (buttons, forms, tables)
4. **Record user workflows** (e.g., "Login → Devices → Select Device → Reboot")

#### 1.2 Browser Developer Tools
Use browser DevTools to inspect elements:

```javascript
// In browser console, find element selectors
document.querySelector('button[title="Reboot"]')

// Get all buttons on page
document.querySelectorAll('button')

// Find by text content
Array.from(document.querySelectorAll('button'))
  .find(btn => btn.textContent.includes('Reboot'))
```

#### 1.3 Network Traffic Analysis
Monitor network requests to understand UI → API mapping:

1. Open DevTools → Network tab
2. Perform UI action (e.g., click Reboot)
3. Observe API calls made
4. Document request/response format

**Example for Reboot:**
```
Request: POST /devices/{cpe_id}/tasks?connection_request=
Payload: {"name": "reboot", "commandKey": "reboot"}
Response: 200 OK
```

### Step 2: Create UI Interaction Map

Document all UI interactions in a structured format:

```markdown
# GenieACS UI Interaction Map

## Login Page
- **URL**: `http://{acs_ip}:3000/login`
- **Elements**:
  - Username field: `input[name="username"]`
  - Password field: `input[name="password"]`
  - Login button: `button[type="submit"]`
- **Actions**:
  - `login(username, password)` → Navigate to device list

## Device List Page
- **URL**: `http://{acs_ip}:3000/devices`
- **Elements**:
  - Search box: `input[placeholder="Search"]`
  - Device rows: `tr.device-row`
  - Device link: `a[href="/devices/{cpe_id}"]`
- **Actions**:
  - `search_device(cpe_id)` → Filter devices
  - `select_device(cpe_id)` → Navigate to device details

## Device Details Page
- **URL**: `http://{acs_ip}:3000/devices/{cpe_id}`
- **Elements**:
  - Reboot button: `button[title="Reboot"]`
  - Refresh button: `button[title="Refresh"]`
  - Parameters table: `table.parameters`
  - Tasks section: `div.tasks`
- **Actions**:
  - `reboot()` → Create reboot task
  - `refresh()` → Trigger connection request
  - `get_parameter(name)` → Read parameter value
  - `set_parameter(name, value)` → Set parameter value
```

### Step 3: Automated UI Discovery

Create a script to automatically discover UI elements:

```python
# File: tools/discover_genieacs_ui.py

from selenium import webdriver
from selenium.webdriver.common.by import By
import json

def discover_page_elements(driver, url, page_name):
    """Discover all interactive elements on a page."""
    driver.get(url)
    
    elements = {
        "page_name": page_name,
        "url": url,
        "buttons": [],
        "inputs": [],
        "links": [],
        "forms": []
    }
    
    # Find all buttons
    for btn in driver.find_elements(By.TAG_NAME, "button"):
        elements["buttons"].append({
            "text": btn.text,
            "title": btn.get_attribute("title"),
            "css_selector": get_css_selector(btn),
            "id": btn.get_attribute("id"),
            "class": btn.get_attribute("class")
        })
    
    # Find all inputs
    for inp in driver.find_elements(By.TAG_NAME, "input"):
        elements["inputs"].append({
            "type": inp.get_attribute("type"),
            "name": inp.get_attribute("name"),
            "placeholder": inp.get_attribute("placeholder"),
            "css_selector": get_css_selector(inp)
        })
    
    return elements

def get_css_selector(element):
    """Generate CSS selector for element."""
    # Simplified - in reality, use a library like cssify
    elem_id = element.get_attribute("id")
    if elem_id:
        return f"#{elem_id}"
    
    elem_class = element.get_attribute("class")
    if elem_class:
        return f".{elem_class.split()[0]}"
    
    return element.tag_name

# Usage
driver = webdriver.Firefox()
driver.get("http://localhost:3000")

# Login first
# ... login code ...

# Discover device details page
device_elements = discover_page_elements(
    driver, 
    "http://localhost:3000/devices/ABCDEF-CPE-123456",
    "Device Details"
)

# Save to JSON
with open("genieacs_ui_map.json", "w") as f:
    json.dump(device_elements, f, indent=2)

driver.quit()
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
1. ✅ Create GenieACS POM structure
2. ✅ Implement base classes (`GenieACSBasePOM`, `GenieACSUIHelper`)
3. ✅ Implement Login page object
4. ✅ Set up WebDriver configuration for GenieACS

### Phase 2: Core Pages (Week 3-4)
1. ✅ Implement Device List page object
2. ✅ Implement Device Details page object
3. ✅ Create helper methods for navigation
4. ✅ Add screenshot capture on errors

### Phase 3: Device Operations (Week 5-6)
1. ✅ Implement `Reboot_UI()` method
2. ✅ Implement `GPV_UI()` method (read parameters via UI)
3. ✅ Implement `SPV_UI()` method (set parameters via UI)
4. ✅ Add error handling and retries

### Phase 4: Integration (Week 7-8)
1. ✅ Integrate UI methods into `GenieACS` device class
2. ✅ Create test scenarios using UI methods
3. ✅ Add configuration option to switch between NBI and UI
4. ✅ Documentation and examples

---

## Comparison: NBI vs UI Methods

| Aspect | NBI API | UI Automation |
|--------|---------|---------------|
| **Speed** | ⚡ Fast (direct HTTP) | 🐌 Slower (browser overhead) |
| **Reliability** | ✅ High (stable API) | ⚠️ Medium (UI changes break tests) |
| **Maintenance** | ✅ Low (API rarely changes) | ⚠️ High (UI updates require updates) |
| **Test Coverage** | ❌ API only | ✅ Tests actual UI workflows |
| **Debugging** | ✅ Easy (HTTP logs) | ⚠️ Harder (screenshots, browser logs) |
| **Setup Complexity** | ✅ Simple (HTTP client) | ⚠️ Complex (WebDriver, browser) |
| **Use Cases** | Backend testing, CI/CD | E2E testing, UI validation |

---

## Recommendations

### For Your Use Case

Based on your requirements, I recommend **Approach 1: Dual-Method Pattern** with the following implementation:

1. **Keep existing NBI methods** for fast, reliable automation
2. **Add UI methods** with `_UI` suffix for UI-specific testing
3. **Use Page Object Model** for maintainability
4. **Create UI interaction map** before implementation
5. **Start with high-value operations** (Reboot, GPV, SPV)

### When to Use Each Method

**Use NBI Methods (`Reboot()`) when:**
- ✅ Testing backend functionality
- ✅ Running in CI/CD pipelines
- ✅ Need fast execution
- ✅ Testing TR-069 protocol compliance

**Use UI Methods (`Reboot_UI()`) when:**
- ✅ Testing UI workflows
- ✅ Validating operator experience
- ✅ E2E testing with UI validation
- ✅ Debugging UI-specific issues

### Example Test Scenario

```python
# File: boardfarm-bdd/tests/step_defs/reboot_ui_steps.py

from pytest_bdd import given, when, then, scenario

@scenario('../features/Remote CPE Reboot UI.feature', 
          'UC-12347-UI: Successful Remote Reboot via UI')
def test_reboot_via_ui():
    """Test reboot via GenieACS UI."""
    pass

@when("the operator initiates a reboot task via the ACS UI for the CPE")
def operator_initiates_reboot_ui(acs, cpe, bf_context):
    """Operator clicks Reboot button in GenieACS UI."""
    cpe_id = f"{cpe.config['oui']}-{cpe.config['product_class']}-{cpe.config['serial']}"
    
    # Use UI method instead of NBI
    acs.Reboot_UI(cpe_id=cpe_id, CommandKey="reboot_ui_test")
    
    bf_context.reboot_command_key = "reboot_ui_test"
```

---

## Next Steps

1. **Review this document** with your team
2. **Decide on approach** (I recommend Approach 1)
3. **Create UI interaction map** for GenieACS
   - Document all pages and elements
   - Identify CSS selectors
   - Map UI actions to API calls
4. **Prototype one operation** (e.g., Reboot_UI)
5. **Evaluate and iterate** based on results

---

## Additional Resources

### Existing Code to Reference
- **PrplOS POM**: `boardfarm/boardfarm3/lib/gui/prplos/` - Good example of POM pattern
- **GUI Helper**: `boardfarm/boardfarm3/lib/gui/gui_helper.py` - WebDriver setup
- **GenieACS NBI**: `boardfarm/boardfarm3/devices/genie_acs.py` - Current implementation

### Tools for UI Discovery
- **Browser DevTools**: Inspect elements, monitor network
- **Selenium IDE**: Record and playback UI interactions
- **ChroPath**: Chrome extension for generating XPath/CSS selectors

### Testing Frameworks
- **pytest-bdd**: Already in use for BDD scenarios
- **pytest-selenium**: Additional Selenium helpers
- **Allure**: Enhanced reporting with screenshots

---

## Questions for Consideration

Before implementation, consider these questions:

1. **Scope**: Which operations need UI methods? (Reboot, GPV, SPV, Download, etc.)
2. **Browser**: Which browser(s) to support? (Firefox, Chrome, headless?)
3. **Authentication**: How to handle GenieACS authentication in UI?
4. **Error Handling**: How to handle UI timeouts, element not found, etc.?
5. **Screenshots**: When to capture screenshots? (errors only, or all steps?)
6. **Parallel Execution**: Can UI tests run in parallel?
7. **CI/CD**: Will UI tests run in CI? (requires headless browser)
8. **Maintenance**: Who will maintain UI tests when GenieACS UI changes?

---

## Conclusion

Introducing UI-based methods in the GenieACS device class is feasible and can provide value for E2E testing and UI validation. The recommended approach is to:

1. Use **Dual-Method Pattern** (`Reboot()` for NBI, `Reboot_UI()` for UI)
2. Implement **Page Object Model** for maintainability
3. Create **UI interaction map** before coding
4. Start with **high-value operations** (Reboot, GPV, SPV)
5. Keep **consistent API** between NBI and UI methods

This approach maintains backward compatibility, provides flexibility, and follows established patterns in your codebase.
