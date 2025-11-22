#!/usr/bin/env python3
"""
Complete UI Discovery and POM Generation Tool

This script combines navigation discovery, element discovery, and POM generation
into a single tool for easy use.

Usage:
    python ui_discovery_complete.py --url http://localhost:3000 --username admin --password admin
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Set
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompleteUIDiscovery:
    """Complete UI discovery with navigation mapping and POM generation."""
    
    def __init__(self, base_url: str, username: str, password: str, headless: bool = True):
        self.base_url = base_url
        self.username = username
        self.password = password
        
        # Setup Firefox
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.set_preference("security.enterprise_roots.enabled", True)
        
        self.driver = webdriver.Firefox(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
        self.visited_urls: Set[str] = set()
        self.pages: List[Dict[str, Any]] = []
        self.navigation_graph: Dict[str, Any] = {}
    
    def run_complete_discovery(self, max_depth: int = 2) -> Dict[str, Any]:
        """Run complete UI discovery process."""
        try:
            logger.info("Starting complete UI discovery for %s", self.base_url)
            
            # Step 1: Login
            self.login()
            
            # Step 2: Discover navigation paths
            logger.info("Discovering navigation paths...")
            home_url = self.driver.current_url
            self._crawl_page(home_url, depth=0, max_depth=max_depth)
            
            # Step 3: Compile results
            results = {
                "base_url": self.base_url,
                "total_pages": len(self.pages),
                "pages": self.pages,
                "navigation_graph": self.navigation_graph,
            }
            
            logger.info("Discovery complete! Found %d pages", len(self.pages))
            
            return results
        
        finally:
            self.driver.quit()
    
    def login(self) -> None:
        """Login to the application."""
        logger.info("Logging in to %s", self.base_url)
        self.driver.get(f"{self.base_url}/login")
        
        try:
            # Try to find username field
            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_field.send_keys(self.username)
            
            # Find password field
            password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            password_field.send_keys(self.password)
            
            # Click login button
            login_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_btn.click()
            
            # Wait for redirect
            self.wait.until(lambda d: "/login" not in d.current_url)
            logger.info("Login successful")
        
        except Exception as e:
            logger.error("Login failed: %s", e)
            raise
    
    def _crawl_page(self, url: str, depth: int, max_depth: int) -> None:
        """Recursively crawl pages."""
        if depth > max_depth:
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
            
            # Discover page info
            page_info = self._discover_page(normalized_url)
            self.pages.append(page_info)
            
            # Find navigation links
            links = self._find_navigation_links()
            
            # Store in navigation graph
            self.navigation_graph[normalized_url] = {
                "title": page_info["title"],
                "page_type": page_info["page_type"],
                "links": [link["href"] for link in links],
            }
            
            # Recursively crawl (only for certain page types)
            if page_info["page_type"] in ["device_list", "unknown"] and depth < max_depth:
                for link in links[:5]:  # Limit to first 5 links to avoid explosion
                    if self._is_internal_link(link["href"]):
                        self._crawl_page(link["href"], depth + 1, max_depth)
        
        except Exception as e:
            logger.error("Error crawling %s: %s", url, e)
    
    def _discover_page(self, url: str) -> Dict[str, Any]:
        """Discover all elements on the current page."""
        page_type = self._classify_page(url)
        
        return {
            "url": url,
            "title": self.driver.title,
            "page_type": page_type,
            "buttons": self._discover_buttons(),
            "inputs": self._discover_inputs(),
            "links": self._discover_links(),
            "tables": self._discover_tables(),
        }
    
    def _classify_page(self, url: str) -> str:
        """Classify page type based on URL."""
        path = urlparse(url).path.lower()
        
        if "/login" in path:
            return "login"
        elif path.count("/") > 2 and "/devices/" in path:
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
    
    def _discover_buttons(self) -> List[Dict[str, Any]]:
        """Discover all buttons."""
        buttons = []
        for btn in self.driver.find_elements(By.TAG_NAME, "button"):
            try:
                buttons.append({
                    "text": btn.text.strip(),
                    "title": btn.get_attribute("title"),
                    "id": btn.get_attribute("id"),
                    "class": btn.get_attribute("class"),
                    "type": btn.get_attribute("type"),
                    "css_selector": self._get_css_selector(btn),
                    "visible": btn.is_displayed(),
                })
            except:
                pass  # Skip stale elements
        return buttons
    
    def _discover_inputs(self) -> List[Dict[str, Any]]:
        """Discover all input fields."""
        inputs = []
        for inp in self.driver.find_elements(By.TAG_NAME, "input"):
            try:
                inputs.append({
                    "type": inp.get_attribute("type"),
                    "name": inp.get_attribute("name"),
                    "id": inp.get_attribute("id"),
                    "placeholder": inp.get_attribute("placeholder"),
                    "css_selector": self._get_css_selector(inp),
                })
            except:
                pass
        return inputs
    
    def _discover_links(self) -> List[Dict[str, Any]]:
        """Discover all links."""
        links = []
        for link in self.driver.find_elements(By.TAG_NAME, "a"):
            try:
                href = link.get_attribute("href")
                if href:
                    links.append({
                        "text": link.text.strip(),
                        "href": href,
                        "css_selector": self._get_css_selector(link),
                    })
            except:
                pass
        return links
    
    def _discover_tables(self) -> List[Dict[str, Any]]:
        """Discover all tables."""
        tables = []
        for table in self.driver.find_elements(By.TAG_NAME, "table"):
            try:
                headers = [th.text.strip() for th in table.find_elements(By.TAG_NAME, "th")]
                tables.append({
                    "id": table.get_attribute("id"),
                    "class": table.get_attribute("class"),
                    "headers": headers,
                    "css_selector": self._get_css_selector(table),
                })
            except:
                pass
        return tables
    
    def _find_navigation_links(self) -> List[Dict[str, str]]:
        """Find navigation links."""
        links = []
        for link in self.driver.find_elements(By.TAG_NAME, "a"):
            try:
                href = link.get_attribute("href")
                if href and self._is_internal_link(href):
                    links.append({
                        "text": link.text.strip(),
                        "href": href,
                        "css_selector": self._get_css_selector(link),
                    })
            except:
                pass
        return links
    
    def _is_internal_link(self, href: str) -> bool:
        """Check if link is internal."""
        if not href:
            return False
        
        parsed = urlparse(href)
        base_parsed = urlparse(self.base_url)
        
        return not parsed.netloc or parsed.netloc == base_parsed.netloc
    
    def _get_css_selector(self, element) -> str:
        """Generate CSS selector for element."""
        elem_id = element.get_attribute("id")
        if elem_id:
            return f"#{elem_id}"
        
        elem_class = element.get_attribute("class")
        if elem_class:
            first_class = elem_class.split()[0]
            if first_class:
                return f".{first_class}"
        
        return element.tag_name


class SimplePOMGenerator:
    """Generate simple POM classes from discovery data."""
    
    def __init__(self, discovery_data: Dict[str, Any], output_dir: str):
        self.data = discovery_data
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_poms(self) -> None:
        """Generate POM classes for all pages."""
        logger.info("Generating POM classes in %s", self.output_dir)
        
        # Generate base POM
        self._generate_base_pom()
        
        # Generate page POMs
        for page in self.data["pages"]:
            if page["page_type"] != "unknown":
                self._generate_page_pom(page)
        
        # Generate __init__.py
        self._generate_init()
        
        logger.info("POM generation complete")
    
    def _generate_base_pom(self) -> None:
        """Generate base POM class."""
        code = '''"""Base Page Object Model for GenieACS UI."""

from selenium.webdriver.support.ui import WebDriverWait


class GenieACSBasePOM:
    """Base class for all GenieACS page objects."""
    
    def __init__(self, driver, base_url: str, fluent_wait: int = 20):
        """Initialize base POM.
        
        :param driver: WebDriver instance
        :param base_url: Base URL of GenieACS
        :param fluent_wait: Wait timeout in seconds
        """
        self.driver = driver
        self.base_url = base_url
        self.fluent_wait = fluent_wait
        self.wait = WebDriverWait(driver, fluent_wait)
    
    def is_page_loaded(self, driver) -> bool:
        """Check if page is loaded. Override in subclass."""
        raise NotImplementedError("Subclass must implement is_page_loaded()")
'''
        
        with open(self.output_dir / "genieacs_base_pom.py", "w") as f:
            f.write(code)
    
    def _generate_page_pom(self, page: Dict[str, Any]) -> None:
        """Generate POM for a specific page."""
        class_name = self._get_class_name(page["page_type"])
        file_name = page["page_type"].lower()
        
        code = self._build_page_code(page, class_name)
        
        with open(self.output_dir / f"{file_name}.py", "w") as f:
            f.write(code)
        
        logger.info("Generated %s", file_name)
    
    def _get_class_name(self, page_type: str) -> str:
        """Convert page type to class name."""
        return "".join(word.capitalize() for word in page_type.split("_")) + "Page"
    
    def _build_page_code(self, page: Dict[str, Any], class_name: str) -> str:
        """Build page class code."""
        lines = [
            f'"""Page Object Model for {page["title"]}."""',
            "",
            "from selenium.webdriver.common.by import By",
            "from selenium.webdriver.support import expected_conditions as EC",
            "from .genieacs_base_pom import GenieACSBasePOM",
            "",
            "",
            f"class {class_name}(GenieACSBasePOM):",
            f'    """Page object for {page["title"]}."""',
            "",
        ]
        
        # Add locators
        if page.get("buttons"):
            lines.append("    # Button locators")
            for btn in page["buttons"][:10]:  # Limit to first 10
                if btn.get("css_selector") and (btn.get("text") or btn.get("title")):
                    name = self._sanitize_name(btn.get("text") or btn.get("title"))
                    lines.append(f'    {name}_BTN = (By.CSS_SELECTOR, "{btn["css_selector"]}")')
            lines.append("")
        
        if page.get("inputs"):
            lines.append("    # Input locators")
            for inp in page["inputs"][:10]:
                if inp.get("css_selector") and (inp.get("name") or inp.get("placeholder")):
                    name = self._sanitize_name(inp.get("name") or inp.get("placeholder"))
                    lines.append(f'    {name}_INPUT = (By.CSS_SELECTOR, "{inp["css_selector"]}")')
            lines.append("")
        
        # Add __init__
        path = urlparse(page["url"]).path
        lines.extend([
            "    def __init__(self, driver, base_url: str, fluent_wait: int = 20):",
            f'        """Initialize {class_name}."""',
            "        super().__init__(driver, base_url, fluent_wait)",
            f'        self.driver.get(f"{{self.base_url}}{path}")',
            "        self.wait.until(self.is_page_loaded)",
            "",
        ])
        
        # Add is_page_loaded
        lines.extend([
            "    def is_page_loaded(self, driver) -> bool:",
            f'        """Check if {page["title"]} is loaded."""',
            "        return driver.execute_script('return document.readyState') == 'complete'",
            "",
        ])
        
        return "\n".join(lines)
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for Python identifier."""
        sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
        return sanitized.strip("_").upper()
    
    def _generate_init(self) -> None:
        """Generate __init__.py."""
        code = '''"""GenieACS Page Object Models."""

from .genieacs_base_pom import GenieACSBasePOM

__all__ = ["GenieACSBasePOM"]
'''
        
        with open(self.output_dir / "__init__.py", "w") as f:
            f.write(code)


def main():
    parser = argparse.ArgumentParser(
        description="Complete UI discovery and POM generation for GenieACS"
    )
    parser.add_argument("--url", required=True, help="GenieACS URL")
    parser.add_argument("--username", default="admin", help="Username")
    parser.add_argument("--password", default="admin", help="Password")
    parser.add_argument("--output-json", default="ui_discovery.json", help="Output JSON file")
    parser.add_argument("--output-pom", default="generated_poms", help="Output POM directory")
    parser.add_argument("--max-depth", type=int, default=2, help="Max crawl depth")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    args = parser.parse_args()
    
    # Step 1: Discover UI
    logger.info("=" * 60)
    logger.info("STEP 1: UI Discovery")
    logger.info("=" * 60)
    
    discovery = CompleteUIDiscovery(args.url, args.username, args.password, args.headless)
    results = discovery.run_complete_discovery(max_depth=args.max_depth)
    
    # Save JSON
    with open(args.output_json, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info("Discovery data saved to %s", args.output_json)
    
    # Step 2: Generate POMs
    logger.info("=" * 60)
    logger.info("STEP 2: POM Generation")
    logger.info("=" * 60)
    
    generator = SimplePOMGenerator(results, args.output_pom)
    generator.generate_poms()
    
    # Step 3: Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info("Total pages discovered: %d", results["total_pages"])
    logger.info("Discovery data: %s", args.output_json)
    logger.info("Generated POMs: %s", args.output_pom)
    logger.info("")
    logger.info("Page types found:")
    page_types = {}
    for page in results["pages"]:
        page_type = page["page_type"]
        page_types[page_type] = page_types.get(page_type, 0) + 1
    
    for page_type, count in sorted(page_types.items()):
        logger.info("  - %s: %d", page_type, count)


if __name__ == "__main__":
    main()
