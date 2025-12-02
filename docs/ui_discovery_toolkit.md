# UI Discovery Toolkit for Boardfarm

## Overview

The `boardfarm` framework provides tools to help you discover, document, and generate selector configurations for any device UI. This document provides practical examples of how to use these tools to create the `selector.yaml` test artifacts needed to configure a device's `gui` component.

## Tool 1: Browser Console Inspector

When you need to manually identify a specific selector or understand the UI's structure, the browser's built-in developer tools are invaluable.

### Quick Element Discovery

Open the browser console (F12) and use these JavaScript snippets to discover elements:

```javascript
// Find all buttons on the page
Array.from(document.querySelectorAll('button')).map(btn => ({
  text: btn.textContent.trim(),
  title: btn.getAttribute('title'),
  id: btn.id,
  class: btn.className,
  selector: btn.id ? `#${btn.id}` : `.${btn.className.split(' ')[0]}`
}))

// Find all input fields
Array.from(document.querySelectorAll('input')).map(inp => ({
  type: inp.type,
  name: inp.name,
  placeholder: inp.placeholder,
  id: inp.id,
  selector: inp.id ? `#${inp.id}` : `input[name="${inp.name}"]`
}))

// Find all links
Array.from(document.querySelectorAll('a')).map(link => ({
  text: link.textContent.trim(),
  href: link.href,
  selector: `a[href="${link.getAttribute('href')}"]`
}))

// Get CSS selector for a specific element
// First, click on the element in the Elements tab, then run:
function getCssSelector(el) {
  if (el.id) return `#${el.id}`;
  if (el.className) return `.${el.className.split(' ')[0]}`;
  return el.tagName.toLowerCase();
}
getCssSelector($0)  // $0 is the currently selected element in DevTools

// Find element by text content
function findByText(text) {
  return Array.from(document.querySelectorAll('*')).find(el => 
    el.textContent.trim() === text && el.children.length === 0
  );
}
findByText('Reboot')
```

### Network Traffic Monitor

Monitor API calls made by UI actions:

```javascript
// In Console, before performing UI action:
const originalFetch = window.fetch;
window.fetch = function(...args) {
  console.log('Fetch:', args);
  return originalFetch.apply(this, args);
};

// Or use the Network tab in DevTools:
// 1. Open Network tab
// 2. Click "Preserve log"
// 3. Perform UI action (e.g., click Reboot)
// 4. Look for API calls in the list
// 5. Right-click → Copy → Copy as cURL
```

## Tool 2: The Framework's Python UI Discovery Script

For comprehensive analysis, the `boardfarm` framework includes a Python-based discovery script that can automatically crawl a UI and generate a selector file to be used by a specific `gui` component (e.g., `GenieAcsGui`).

### Automated Selector File Generation

This script is the primary tool for creating and maintaining your `selectors.yaml` files.

```python
#!/usr/bin/env python3
"""
UI Element Discovery Script

Usage:
    python discover_ui.py --url http://localhost:3000 --username admin --password admin
"""

import argparse
import json
import logging
from typing import Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UIDiscovery:
    """Discover UI elements on a web page."""
    
    def __init__(self, base_url: str, username: str, password: str, headless: bool = True):
        self.base_url = base_url
        self.username = username
        self.password = password
        
        # Setup Firefox
        options = Options()
        if headless:
            options.add_argument("--headless")
        self.driver = webdriver.Firefox(options=options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def login(self) -> None:
        """Login to the application."""
        logger.info("Logging in to %s", self.base_url)
        self.driver.get(f"{self.base_url}/login")
        
        # Try common login field selectors
        username_selectors = [
            (By.NAME, "username"),
            (By.ID, "username"),
            (By.CSS_SELECTOR, "input[type='text']"),
        ]
        
        for by, selector in username_selectors:
            try:
                username_field = self.wait.until(
                    EC.presence_of_element_located((by, selector))
                )
                break
            except:
                continue
        else:
            raise Exception("Could not find username field")
        
        username_field.send_keys(self.username)
        
        # Find password field
        password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_field.send_keys(self.password)
        
        # Find and click login button
        login_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        
        # Wait for redirect
        self.wait.until(lambda d: "/login" not in d.current_url)
        logger.info("Login successful")
    
    def discover_page(self, url: str, page_name: str) -> dict[str, Any]:
        """Discover all interactive elements on a page."""
        logger.info("Discovering elements on %s", url)
        self.driver.get(url)
        
        # Wait for page to load
        self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        
        elements = {
            "page_name": page_name,
            "url": url,
            "title": self.driver.title,
            "buttons": self._discover_buttons(),
            "inputs": self._discover_inputs(),
            "links": self._discover_links(),
            "tables": self._discover_tables(),
            "forms": self._discover_forms(),
        }
        
        return elements
    
    def _discover_buttons(self) -> list[dict]:
        """Discover all buttons on the page."""
        buttons = []
        for btn in self.driver.find_elements(By.TAG_NAME, "button"):
            buttons.append({
                "text": btn.text.strip(),
                "title": btn.get_attribute("title"),
                "id": btn.get_attribute("id"),
                "class": btn.get_attribute("class"),
                "type": btn.get_attribute("type"),
                "css_selector": self._get_css_selector(btn),
                "xpath": self._get_xpath(btn),
            })
        return buttons
    
    def _discover_inputs(self) -> list[dict]:
        """Discover all input fields on the page."""
        inputs = []
        for inp in self.driver.find_elements(By.TAG_NAME, "input"):
            inputs.append({
                "type": inp.get_attribute("type"),
                "name": inp.get_attribute("name"),
                "id": inp.get_attribute("id"),
                "placeholder": inp.get_attribute("placeholder"),
                "value": inp.get_attribute("value"),
                "css_selector": self._get_css_selector(inp),
                "xpath": self._get_xpath(inp),
            })
        return inputs
    
    def _discover_links(self) -> list[dict]:
        """Discover all links on the page."""
        links = []
        for link in self.driver.find_elements(By.TAG_NAME, "a"):
            href = link.get_attribute("href")
            if href:  # Only include links with href
                links.append({
                    "text": link.text.strip(),
                    "href": href,
                    "id": link.get_attribute("id"),
                    "class": link.get_attribute("class"),
                    "css_selector": self._get_css_selector(link),
                })
        return links
    
    def _discover_tables(self) -> list[dict]:
        """Discover all tables on the page."""
        tables = []
        for table in self.driver.find_elements(By.TAG_NAME, "table"):
            headers = [th.text.strip() for th in table.find_elements(By.TAG_NAME, "th")]
            tables.append({
                "id": table.get_attribute("id"),
                "class": table.get_attribute("class"),
                "headers": headers,
                "row_count": len(table.find_elements(By.TAG_NAME, "tr")),
                "css_selector": self._get_css_selector(table),
            })
        return tables
    
    def _discover_forms(self) -> list[dict]:
        """Discover all forms on the page."""
        forms = []
        for form in self.driver.find_elements(By.TAG_NAME, "form"):
            forms.append({
                "id": form.get_attribute("id"),
                "class": form.get_attribute("class"),
                "action": form.get_attribute("action"),
                "method": form.get_attribute("method"),
                "css_selector": self._get_css_selector(form),
            })
        return forms
    
    def _get_css_selector(self, element) -> str:
        """Generate CSS selector for element."""
        elem_id = element.get_attribute("id")
        if elem_id:
            return f"#{elem_id}"
        
        elem_class = element.get_attribute("class")
        if elem_class:
            first_class = elem_class.split()[0]
            return f".{first_class}"
        
        return element.tag_name
    
    def _get_xpath(self, element) -> str:
        """Generate XPath for element."""
        # This is a simplified version
        # In production, use a library like cssify or generate full XPath
        elem_id = element.get_attribute("id")
        if elem_id:
            return f"//*[@id='{elem_id}']"
        
        return f"//{element.tag_name}"
    
    def close(self) -> None:
        """Close the browser."""
        self.driver.quit()


def main():
    parser = argparse.ArgumentParser(description="Discover UI elements on a web page")
    parser.add_argument("--url", required=True, help="Base URL of the application")
    parser.add_argument("--username", default="admin", help="Username for login")
    parser.add_argument("--password", default="admin", help="Password for login")
    parser.add_argument("--output", default="ui_elements.json", help="Output JSON file")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--output-yaml", help="Output selector YAML file")
    args = parser.parse_args()
    
    discovery = UIDiscovery(args.url, args.username, args.password, args.headless)
    
    try:
        # Login
        discovery.login()
        
        # Discover pages
        pages = []
        
        # Device list page
        pages.append(discovery.discover_page(
            f"{args.url}/devices",
            "Device List"
        ))
        
        # You can add more pages here
        # pages.append(discovery.discover_page(
        #     f"{args.url}/devices/DEVICE-ID",
        #     "Device Details"
        # ))
        
        # Save to JSON
        with open(args.output, "w") as f:
            json.dump(pages, f, indent=2)
        
        logger.info("UI elements saved to %s", args.output)
        
    finally:
        discovery.close()


if __name__ == "__main__":
    main()
```

### Usage

You run this script from your test suite's directory to generate the artifact directly where it's needed.

```bash
# From your boardfarm-bdd directory:

# Run the framework's discovery tool
python /path/to/boardfarm/tools/ui_discovery.py \
  --url http://device-ip \
  --username admin \
  --password admin \
  --output-yaml ./tests/ui_helpers/mydevice_selectors.yaml \
  --headless

# View the generated artifact
cat ./tests/ui_helpers/mydevice_selectors.yaml
```

## Recommended Workflow

1.  **Initial Discovery**: Run the framework's `ui_discovery.py` tool to generate your first `selectors.yaml` file for a specific UI version.

2.  **Manual Verification**: Use the **Browser Console Inspector** tools to spot-check a few key selectors from the generated YAML file to ensure they are robust. Good selectors use stable attributes like `id`, `name`, or `data-testid` where possible.

3.  **Commit Artifact**: Add the generated and verified `selectors.yaml` file to your test suite's version control.

4.  **Use in Tests**: Pass the path to this artifact to your device's `init_gui()` method to configure its `gui` component.

5.  **Maintain**: When the UI is updated, re-run the discovery script to regenerate the `selectors.yaml` file. Review the diff in version control to understand what changed before committing.

## Tips and Best Practices

### Selector Priority

When manually inspecting or editing selectors, prefer them in this order for maximum stability:

1.  **ID** (best) - `#element-id`
2.  **Data attributes** - `[data-testid="reboot"]` (if available)
3.  **Name** - `input[name="username"]`
4.  **Class** - `.btn-primary` (use with caution; can be non-unique)
5.  **XPath** (last resort) - `//button[text()='Reboot']` (can be brittle)

### Wait Strategies

The framework's `BaseGuiComponent` (which your specific `gui` component should extend) should handle wait conditions for you. When adding new methods, always use explicit waits to ensure the UI is ready.

```python
# In your device-specific Gui component class (e.g., GenieAcsGui)
from selenium.webdriver.support import expected_conditions as EC

def wait_for_and_click_a_button(self):
    locator = self._get_locator("my_page.my_button")
    
    # Good: Wait for the element to be ready before interacting
    element = self.wait.until(EC.element_to_be_clickable(locator))
    element.click()
```

## Conclusion

By combining the power of the framework's automated discovery tools with manual verification using browser tools, you can efficiently create and maintain the `selector.yaml` artifacts needed for a robust and scalable UI testing strategy.
