# A Framework-Based Strategy for Automated UI Maintenance

## Overview

To solve this, the `boardfarm` framework should provide a suite of tools for automated discovery and maintenance. This document describes a strategy where these tools are used to generate the `selectors.yaml` and `navigation.yaml` files, which are then used to configure a device's `gui` component (e.g., `GenieAcsGui`).

## The Challenge

UI-based automation is fragile because:
- UI elements change (IDs, classes, structure)
- Navigation paths evolve (new pages, reorganized menus)
- Features are added/removed
- Manual POM maintenance is time-consuming and error-prone

## Solution: A Framework-Driven Maintenance Pipeline

The `boardfarm` framework can provide the scripts and tools to automate the following pipeline for maintaining the UI test artifacts.

```mermaid
graph LR
    A[Scheduled Scan] --> B[UI Discovery]
    B --> C[Navigation Mapper]
    C --> D[Change Detection]
    D --> E{Changes Found?}
    E -->|Yes| F[Generate/Update Artifacts (selector & navigation YAML)]
    E -->|No| G[No Action]
    F --> H[Create PR/Report against Test Suite]
    H --> I[Human Review]
    I --> J[Merge Updated YAMLs into Test Suite repo]
```

## Component 1: Framework Tool - UI Discovery & Navigation Mapping

The `boardfarm` framework should include a powerful discovery script that can be pointed at any device's UI.

```python
# In boardfarm/boardfarm3/tools/ui_discovery.py

import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from typing import Any, Dict, List, Set
from urllib.parse import urlparse, urljoin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UIDiscoveryTool:
    """
    A generic tool within the boardfarm framework to crawl a web UI,
    discover its pages and elements, and map navigation paths.
    """
    
    def __init__(self, base_url: str, username: str, password: str, headless: bool = True):
        self.base_url = base_url
        self.username = username
        self.password = password
        
        options = Options()
        if headless:
            options.add_argument("--headless")
        self.driver = webdriver.Firefox(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
        self.visited_urls: Set[str] = set()
        self.navigation_graph: Dict[str, Any] = {}
        self.pages: List[Dict[str, Any]] = []
    
    def login(self) -> None:
        """Login to the application."""
        logger.info("Logging in to %s", self.base_url)
        self.driver.get(f"{self.base_url}/login")
        
        username_field = self.wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        username_field.send_keys(self.username)
        
        password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_field.send_keys(self.password)
        
        login_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        
        self.wait.until(lambda d: "/login" not in d.current_url)
        logger.info("Login successful")
    
    def discover_site(self, max_depth: int = 3) -> Dict[str, Any]:
        """Crawls the entire UI and returns a structured map."""
        self.login()
        
        # Start from home page
        home_url = self.driver.current_url
        self._crawl_page(home_url, depth=0, max_depth=max_depth)
        
        return {
            "base_url": self.base_url,
            "pages": self.pages,
            "navigation_graph": self.navigation_graph,
        }
    
    def _crawl_page(self, url: str, depth: int, max_depth: int) -> None:
        """Recursively crawl pages to discover navigation paths."""
        if depth > max_depth or url in self.visited_urls:
            return
        
        # Normalize URL
        parsed = urlparse(url)
        normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        if normalized_url in self.visited_urls:
            return
        
        logger.info("Crawling: %s (depth: %d)", normalized_url, depth)
        self.visited_urls.add(normalized_url)
        
        try:
            self.driver.get(url)
            self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            
            # Discover page elements
            page_info = self._discover_page_info(normalized_url)
            self.pages.append(page_info)
            
            # Find all navigation links
            links = self._find_navigation_links()
            
            # Store navigation graph
            self.navigation_graph[normalized_url] = {
                "title": page_info["title"],
                "links": [link["href"] for link in links],
            }
            
            # Recursively crawl linked pages
            for link in links:
                if self._is_internal_link(link["href"]):
                    self._crawl_page(link["href"], depth + 1, max_depth)
        
        except Exception as e:
            logger.error("Error crawling %s: %s", url, e)
    
    def _discover_page_info(self, url: str) -> Dict[str, Any]:
        """Discover information about the current page."""
        return {
            "url": url,
            "title": self.driver.title,
            "page_type": self._classify_page(url),
            "buttons": self._discover_buttons(),
            "inputs": self._discover_inputs(),
            "links": self._discover_links(),
            "tables": self._discover_tables(),
        }
    
    def _classify_page(self, url: str) -> str:
        """Classify the page type based on URL."""
        path = urlparse(url).path
        
        if "/login" in path:
            return "login"
        elif "/devices/" in path and len(path.split("/")) > 2:
            return "device_details"
        elif "/devices" in path:
            return "device_list"
        elif "/tasks" in path:
            return "tasks"
        elif "/files" in path:
            return "files"
        elif "/presets" in path:
            return "presets"
        else:
            return "unknown"
    
    def _find_navigation_links(self) -> List[Dict[str, str]]:
        """Find all navigation links on the current page."""
        links = []
        for link in self.driver.find_elements(By.TAG_NAME, "a"):
            href = link.get_attribute("href")
            if href and self._is_internal_link(href):
                links.append({
                    "text": link.text.strip(),
                    "href": href,
                    "css_selector": self._get_css_selector(link),
                })
        return links
    
    def _is_internal_link(self, href: str) -> bool:
        """Check if link is internal to the application."""
        if not href:
            return False
        
        parsed = urlparse(href)
        base_parsed = urlparse(self.base_url)
        
        # Same domain or relative URL
        return (not parsed.netloc or parsed.netloc == base_parsed.netloc)
    
    def _discover_buttons(self) -> List[Dict[str, Any]]:
        """Discover all buttons on the page."""
        buttons = []
        for btn in self.driver.find_elements(By.TAG_NAME, "button"):
            buttons.append({
                "text": btn.text.strip(),
                "title": btn.get_attribute("title"),
                "id": btn.get_attribute("id"),
                "class": btn.get_attribute("class"),
                "css_selector": self._get_css_selector(btn),
            })
        return buttons
    
    def _discover_inputs(self) -> List[Dict[str, Any]]:
        """Discover all input fields on the page."""
        inputs = []
        for inp in self.driver.find_elements(By.TAG_NAME, "input"):
            inputs.append({
                "type": inp.get_attribute("type"),
                "name": inp.get_attribute("name"),
                "id": inp.get_attribute("id"),
                "placeholder": inp.get_attribute("placeholder"),
                "css_selector": self._get_css_selector(inp),
            })
        return inputs
    
    def _discover_links(self) -> List[Dict[str, Any]]:
        """Discover all links on the page."""
        links = []
        for link in self.driver.find_elements(By.TAG_NAME, "a"):
            href = link.get_attribute("href")
            if href:
                links.append({
                    "text": link.text.strip(),
                    "href": href,
                    "css_selector": self._get_css_selector(link),
                })
        return links
    
    def _discover_tables(self) -> List[Dict[str, Any]]:
        """Discover all tables on the page."""
        tables = []
        for table in self.driver.find_elements(By.TAG_NAME, "table"):
            headers = [th.text.strip() for th in table.find_elements(By.TAG_NAME, "th")]
            tables.append({
                "id": table.get_attribute("id"),
                "class": table.get_attribute("class"),
                "headers": headers,
                "css_selector": self._get_css_selector(table),
            })
        return tables
    
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
    
    def close(self) -> None:
        """Close the browser."""
        self.driver.quit()

# This script can be run from the command line against any target UI.
```

## Component 2: Framework Tool - Change Detection

The framework should also provide a script to compare two discovery JSON files (a baseline and a current scan) to detect changes.

```python
# In boardfarm/boardfarm3/tools/ui_change_detector.py

import json
import logging
from typing import Any, Dict, List
from difflib import unified_diff

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UIChangeDetector:
    """
    A generic tool to compare two UI discovery maps and report differences.
    """
    
    def __init__(self, baseline_file: str, current_file: str):
        self.baseline_file = baseline_file
        self.current_file = current_file
        
        with open(baseline_file) as f:
            self.baseline = json.load(f)
        
        with open(current_file) as f:
            self.current = json.load(f)
    
    def detect_changes(self) -> Dict[str, Any]:
        """Finds new pages, removed pages, and modified elements."""
        changes = {
            "new_pages": self._find_new_pages(),
            "removed_pages": self._find_removed_pages(),
            "modified_pages": self._find_modified_pages(),
            "navigation_changes": self._find_navigation_changes(),
            "summary": {},
        }
        
        # Generate summary
        changes["summary"] = {
            "total_changes": (
                len(changes["new_pages"]) +
                len(changes["removed_pages"]) +
                len(changes["modified_pages"])
            ),
            "new_pages_count": len(changes["new_pages"]),
            "removed_pages_count": len(changes["removed_pages"]),
            "modified_pages_count": len(changes["modified_pages"]),
        }
        
        return changes
    
    def _find_new_pages(self) -> List[Dict[str, Any]]:
        """Find pages that exist in current but not in baseline."""
        baseline_urls = {page["url"] for page in self.baseline["pages"]}
        current_urls = {page["url"] for page in self.current["pages"]}
        
        new_urls = current_urls - baseline_urls
        
        return [
            page for page in self.current["pages"]
            if page["url"] in new_urls
        ]
    
    def _find_removed_pages(self) -> List[Dict[str, Any]]:
        """Find pages that exist in baseline but not in current."""
        baseline_urls = {page["url"] for page in self.baseline["pages"]}
        current_urls = {page["url"] for page in self.current["pages"]}
        
        removed_urls = baseline_urls - current_urls
        
        return [
            page for page in self.baseline["pages"]
            if page["url"] in removed_urls
        ]
    
    def _find_modified_pages(self) -> List[Dict[str, Any]]:
        """Find pages that have changed."""
        baseline_pages = {page["url"]: page for page in self.baseline["pages"]}
        current_pages = {page["url"]: page for page in self.current["pages"]}
        
        modified = []
        
        for url in baseline_pages:
            if url in current_pages:
                baseline_page = baseline_pages[url]
                current_page = current_pages[url]
                
                changes = self._compare_pages(baseline_page, current_page)
                if changes:
                    modified.append({
                        "url": url,
                        "changes": changes,
                    })
        
        return modified
    
    def _compare_pages(self, baseline: Dict, current: Dict) -> Dict[str, Any]:
        """Compare two pages and return differences."""
        changes = {}
        
        # Compare buttons
        baseline_buttons = {btn["css_selector"]: btn for btn in baseline.get("buttons", [])}
        current_buttons = {btn["css_selector"]: btn for btn in current.get("buttons", [])}
        
        new_buttons = set(current_buttons.keys()) - set(baseline_buttons.keys())
        removed_buttons = set(baseline_buttons.keys()) - set(current_buttons.keys())
        
        if new_buttons or removed_buttons:
            changes["buttons"] = {
                "new": [current_buttons[sel] for sel in new_buttons],
                "removed": [baseline_buttons[sel] for sel in removed_buttons],
            }
        
        # Compare inputs
        baseline_inputs = {inp["css_selector"]: inp for inp in baseline.get("inputs", [])}
        current_inputs = {inp["css_selector"]: inp for inp in current.get("inputs", [])}
        
        new_inputs = set(current_inputs.keys()) - set(baseline_inputs.keys())
        removed_inputs = set(baseline_inputs.keys()) - set(current_inputs.keys())
        
        if new_inputs or removed_inputs:
            changes["inputs"] = {
                "new": [current_inputs[sel] for sel in new_inputs],
                "removed": [baseline_inputs[sel] for sel in removed_inputs],
            }
        
        # Compare title
        if baseline.get("title") != current.get("title"):
            changes["title"] = {
                "old": baseline.get("title"),
                "new": current.get("title"),
            }
        
        return changes
    
    def _find_navigation_changes(self) -> List[Dict[str, Any]]:
        """Find changes in navigation structure."""
        baseline_nav = self.baseline.get("navigation_graph", {})
        current_nav = self.current.get("navigation_graph", {})
        
        changes = []
        
        for url in baseline_nav:
            if url in current_nav:
                baseline_links = set(baseline_nav[url]["links"])
                current_links = set(current_nav[url]["links"])
                
                new_links = current_links - baseline_links
                removed_links = baseline_links - current_links
                
                if new_links or removed_links:
                    changes.append({
                        "page": url,
                        "new_links": list(new_links),
                        "removed_links": list(removed_links),
                    })
        
        return changes
    
    def generate_report(self) -> str:
        """Generates a human-readable markdown report of the changes."""
        lines = ["# UI Change Detection Report", ""]
        
        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Total changes: {self.detect_changes()['summary']['total_changes']}")
        lines.append(f"- New pages: {self.detect_changes()['summary']['new_pages_count']}")
        lines.append(f"- Removed pages: {self.detect_changes()['summary']['removed_pages_count']}")
        lines.append(f"- Modified pages: {self.detect_changes()['summary']['modified_pages_count']}")
        lines.append("")
        
        # New pages
        if self.detect_changes()["new_pages"]:
            lines.append("## New Pages")
            lines.append("")
            for page in self.detect_changes()["new_pages"]:
                lines.append(f"- **{page['title']}** - `{page['url']}`")
                lines.append(f"  - Type: {page['page_type']}")
                lines.append(f"  - Buttons: {len(page['buttons'])}")
                lines.append(f"  - Inputs: {len(page['inputs'])}")
            lines.append("")
        
        # Removed pages
        if self.detect_changes()["removed_pages"]:
            lines.append("## Removed Pages")
            lines.append("")
            for page in self.detect_changes()["removed_pages"]:
                lines.append(f"- **{page['title']}** - `{page['url']}`")
            lines.append("")
        
        # Modified pages
        if self.detect_changes()["modified_pages"]:
            lines.append("## Modified Pages")
            lines.append("")
            for mod in self.detect_changes()["modified_pages"]:
                lines.append(f"### {mod['url']}")
                lines.append("")
                
                if "buttons" in mod["changes"]:
                    btn_changes = mod["changes"]["buttons"]
                    if btn_changes.get("new"):
                        lines.append("**New buttons:**")
                        for btn in btn_changes["new"]:
                            lines.append(f"- {btn['text']} (`{btn['css_selector']}`)")
                    if btn_changes.get("removed"):
                        lines.append("**Removed buttons:**")
                        for btn in btn_changes["removed"]:
                            lines.append(f"- {btn['text']} (`{btn['css_selector']}`)")
                
                lines.append("")
        
        return "\n".join(lines)
```

## Component 3: Framework Tool - Selector YAML Generator

Finally, the framework should provide a tool to convert the discovery JSON into the clean, human-readable selector YAML format that our `BaseGuiComponent` consumes.

```python
# In boardfarm/boardfarm3/tools/selector_generator.py

import yaml
import json

class SelectorGenerator:
    """
    Converts a UI discovery JSON map into a selector.yaml file.
    """
    def __init__(self, discovery_file: str):
        # ...
        
    def generate_yaml(self) -> str:
        """Generates the YAML content."""
        # ... logic to transform the detailed JSON into the clean YAML format ...
        
# Usage:
# 1. Run discovery tool -> get ui_map.json
# 2. Run selector generator -> get selectors.yaml, which configures the device's specific '.gui' component.
```

## Component 4: Framework Tool - Navigation YAML Generator

The framework will also provide a tool to analyze the navigation graph from the discovery output and generate suggested navigation paths.

```python
# In boardfarm/boardfarm3/tools/navigation_generator.py

import yaml
import json

class NavigationGenerator:
    """
    Converts a UI discovery JSON map into a navigation.yaml file.
    """
    def __init__(self, discovery_file: str):
        # ...
        
    def generate_yaml(self) -> str:
        """Generates the YAML content by finding common paths."""
        # ... logic to analyze the navigation_graph from the JSON ...
        # ... and generate common user journeys.
```

## Component 5: Recommended CI/CD Workflow for Product Development

To ensure that UI test artifacts are kept in sync with the application, we recommend integrating an automated maintenance workflow directly into the product's development CI/CD pipeline. This workflow leverages the framework's tools to detect UI changes on every pull request or nightly build, providing immediate feedback to developers.

### CI/CD Integration in the Product Repository

The following is an example of a CI job that would run within the *product's* repository (not the test suite's). Its goal is to automatically update and validate the test artifacts, which can then be synchronized with the `boardfarm-bdd` repository.

```yaml
# In a CI workflow for the PRODUCT repository (e.g., .github/workflows/ui_validation.yml)

# ... (setup steps, checkout product code) ...

      - name: Discover current UI state
        run: |
          python /path/to/boardfarm/tools/ui_discovery.py \
            --url ${{ secrets.ACS_URL }} \
            --output current_ui_map.json \
            --headless
      
      - name: Detect changes against baseline
        id: detect
        run: |
          # The baseline_ui_map.json is a file stored with the product code or fetched
          # from a shared artifact storage.
          python /path/to/boardfarm/tools/ui_change_detector.py \
            --baseline ./path/to/baseline_ui_map.json \
            --current current_ui_map.json \
            --output ui_changes.md

      - name: Generate updated Selector YAML if changes were detected
        if: steps.detect.outputs.changes_detected == 'true'
        run: |
          python /path/to/boardfarm/tools/selector_generator.py \
            --input current_ui_map.json \
            --output ./tests/ui_helpers/new_acs_selectors.yaml
      
      - name: Generate updated Navigation YAML if changes were detected
        if: steps.detect.outputs.changes_detected == 'true'
        run: |
          python /path/to/boardfarm/tools/navigation_generator.py \
            --input current_ui_map.json \
            --output ./tests/ui_helpers/new_acs_navigation.yaml

      - name: Create Pull Request with updated YAML artifacts against the Test Suite repo
        if: steps.detect.outputs.changes_detected == 'true'
        uses: peter-evans/create-pull-request@v5
        with:
          # This would target the boardfarm-bdd repository
          repository: your-org/boardfarm-bdd
          token: ${{ secrets.BFF_BDD_PAT }} # A token with permissions to the test repo
          commit-message: 'chore: Update UI test artifacts from product build'
          title: 'UI Changes Detected: Update selector and navigation artifacts'
          body-path: ui_changes.md
          branch: ui-maintenance/auto-update-artifacts
```

## Benefits of This Approach

### 1. **Early Detection**
- Developers are immediately notified of the impact their UI changes have on the test suite.
- Reduces the feedback loop between development and QA.

### 2. **Framework-Provided Tooling**
- No need to rewrite discovery and maintenance scripts for every project.
- Ensures a standard process for all UI test suites.

### 3. **Test Suite-Owned Artifacts**
- The UI baseline and the final `selectors.yaml` and `navigation.yaml` files are version-controlled alongside the tests that use them.
- CI/CD operates on the test suite repository, not the core framework.

### 4. **Clear Separation**
- The framework provides the *how* (the tools).
- The test suite provides the *what* (the UI-specific baseline and artifact files).

## Implementation Roadmap

### Phase 1: Framework - Build the Tools (Week 1)
1. ✅ Create the `ui_discovery.py` tool.
2. ✅ Create the `ui_change_detector.py` tool.
3. ✅ Create the `selector_generator.py` tool.
4. ✅ Create the `navigation_generator.py` tool.
5. ✅ Create the `BaseGuiComponent` class in `lib/gui/base_gui_component.py` that will serve as the foundation for specific `gui` components.

### Phase 2: Test Suite - Integration (Week 2)
1. ✅ Run the discovery tool to create a `baseline_ui_map.json`.
2. ✅ Commit the baseline to the `boardfarm-bdd` repo.
3. ✅ Run the generators to create the first `acs_selectors.yaml` and `acs_navigation.yaml`.
4. ✅ Implement the composite `GenieACS` class in `devices` with its `nbi` and `gui` components.
5. ✅ Start writing tests using `acs.gui.navigate_to()`.

### Phase 3: Automation (Week 3)
1. ✅ Create the CI/CD workflow.
2. ✅ Set up scheduled scans.
3. ✅ Test the automated pull request generation.

### Phase 4: Optimization (Week 4)
1. ✅ Tune change detection sensitivity
2. ✅ Optimize crawl performance
3. ✅ Add visual regression testing
4. ✅ Refine POM generation templates

## Best Practices

### 1. **Baseline Management**
- Update baseline after verifying changes
- Version control baseline files
- Document baseline update process

### 2. **Change Review**
- Always review generated POMs
- Test before merging
- Update tests if needed

### 3. **Selective Generation**
- Only generate POMs for pages you use
- Skip admin/config pages if not needed
- Focus on critical user journeys

### 4. **Performance**
- Limit crawl depth (max 3 levels)
- Use headless mode
- Run during off-peak hours

### 5. **Error Handling**
- Handle dynamic content gracefully
- Retry on transient failures
- Log all errors for review

## Monitoring and Alerts

### Slack Integration

A CI job can be configured to send a Slack notification when the UI change detection workflow is triggered, providing immediate visibility to the test team.

```python
# tools/notify_slack.py

import json
import requests

def notify_slack(webhook_url: str, changes: dict):
    """Send notification to Slack."""
    message = {
        "text": "GenieACS UI Changes Detected",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*UI Changes Summary*\n"
                           f"• New pages: {changes['summary']['new_pages_count']}\n"
                           f"• Removed pages: {changes['summary']['removed_pages_count']}\n"
                           f"• Modified pages: {changes['summary']['modified_pages_count']}"
                }
            }
        ]
    }
    
    requests.post(webhook_url, json=message)
```

## Conclusion

This automated maintenance strategy, driven by tools within the `boardfarm` framework, provides a powerful and scalable way to manage UI test artifacts. It:
- ✅ Minimizes manual maintenance of selectors and navigation paths.
- ✅ Detects UI changes early and automatically.
- ✅ Generates consistent, standardized selector and navigation files.
- ✅ Integrates cleanly with CI/CD for a hands-off maintenance process.

By treating the UI map, selector file, and navigation file as test artifacts that are automatically maintained by framework tools and consumed by a device's standard `gui` component, we achieve a robust and efficient workflow.
