# Quick Start Guide: Automated UI Discovery and Maintenance

## Overview

This guide shows you how to use the automated UI discovery and maintenance tools to keep your GenieACS UI methods up-to-date with minimal manual effort.

## Prerequisites

```bash
# Install Selenium
pip install selenium

# Install Firefox and geckodriver (if not already installed)
# On Ubuntu/Debian:
sudo apt-get install firefox
wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz
tar -xvzf geckodriver-v0.33.0-linux64.tar.gz
chmod +x geckodriver
sudo mv geckodriver /usr/local/bin/
```

## Quick Start: One-Command Discovery

The easiest way to get started is with the all-in-one discovery tool:

```bash
cd /home/rjvisser/projects/req-tst/boardfarm-bdd

# Run complete discovery (replace with your GenieACS URL)
python tools/ui_discovery_complete.py \
  --url http://localhost:3000 \
  --username admin \
  --password admin \
  --output-json ui_discovery.json \
  --output-pom generated_poms \
  --max-depth 2 \
  --headless
```

This will:
1. ✅ Login to GenieACS
2. ✅ Discover all pages (up to depth 2)
3. ✅ Map navigation paths
4. ✅ Extract all UI elements (buttons, inputs, links, tables)
5. ✅ Generate Page Object Model classes
6. ✅ Save discovery data to JSON

### Output

After running, you'll have:
- `ui_discovery.json` - Complete UI structure data
- `generated_poms/` - Generated POM classes
  - `genieacs_base_pom.py` - Base class
  - `device_list.py` - Device list page
  - `device_details.py` - Device details page
  - `login.py` - Login page
  - etc.

## Step-by-Step Workflow

### Step 1: Initial Discovery (First Time)

```bash
# Discover current UI state
python tools/ui_discovery_complete.py \
  --url http://localhost:3000 \
  --username admin \
  --password admin \
  --output-json baseline_ui.json \
  --output-pom boardfarm/boardfarm3/lib/gui/genieacs/pages \
  --headless

# Save as baseline
cp baseline_ui.json ui_baseline.json
```

### Step 2: Review Generated POMs

```bash
# Check what was generated
ls -la boardfarm/boardfarm3/lib/gui/genieacs/pages/

# Review a generated POM
cat boardfarm/boardfarm3/lib/gui/genieacs/pages/device_details.py
```

### Step 3: Integrate with Device Class

Now you can use the generated POMs in your `GenieACS` device class:

```python
# In boardfarm/boardfarm3/devices/genie_acs.py

from boardfarm3.lib.gui.genieacs.pages.device_details import DeviceDetailsPage
from boardfarm3.lib.gui.gui_helper import GuiHelperNoProxy

class GenieACS(LinuxDevice, ACS):
    
    def _init_ui_helper(self) -> None:
        """Initialize UI helper with generated POMs."""
        if self._ui_helper is None:
            self._gui_helper = GuiHelperNoProxy(default_delay=20, headless=True)
            driver = self._gui_helper.get_web_driver()
            self._ui_helper = {
                "driver": driver,
                "base_url": self._base_url,
            }
    
    def Reboot_UI(self, CommandKey: str = "reboot", cpe_id: str | None = None) -> list[dict]:
        """Execute Reboot via GenieACS UI using generated POM."""
        cpe_id = cpe_id if cpe_id else self._cpeid
        if not cpe_id:
            raise ValueError("cpe_id is required")
        
        self._init_ui_helper()
        
        # Use generated POM
        device_page = DeviceDetailsPage(
            self._ui_helper["driver"],
            self._ui_helper["base_url"]
        )
        
        # Click reboot button (method name from generated POM)
        device_page.click_REBOOT_BTN()
        
        return []
```

### Step 4: Regular Maintenance (Weekly/Monthly)

```bash
# Discover current UI state
python tools/ui_discovery_complete.py \
  --url http://localhost:3000 \
  --username admin \
  --password admin \
  --output-json current_ui.json \
  --output-pom /tmp/current_poms \
  --headless

# Compare with baseline (manual for now)
diff ui_baseline.json current_ui.json
```

## Advanced: Change Detection

### Detect UI Changes

Create a simple change detection script:

```bash
#!/bin/bash
# tools/check_ui_changes.sh

# Discover current state
python tools/ui_discovery_complete.py \
  --url http://localhost:3000 \
  --username admin \
  --password admin \
  --output-json current_ui.json \
  --output-pom /tmp/poms \
  --headless

# Compare with baseline
if ! diff -q ui_baseline.json current_ui.json > /dev/null; then
  echo "⚠️  UI changes detected!"
  echo ""
  echo "Differences:"
  diff ui_baseline.json current_ui.json | head -20
  echo ""
  echo "Run the following to update POMs:"
  echo "  cp current_ui.json ui_baseline.json"
  echo "  python tools/ui_discovery_complete.py --url ... --output-pom boardfarm/boardfarm3/lib/gui/genieacs/pages"
else
  echo "✅ No UI changes detected"
fi
```

Make it executable:

```bash
chmod +x tools/check_ui_changes.sh
```

Run it:

```bash
./tools/check_ui_changes.sh
```

## Customizing Discovery

### Limit Crawl Depth

```bash
# Only discover top-level pages (faster)
python tools/ui_discovery_complete.py \
  --url http://localhost:3000 \
  --max-depth 1 \
  --headless
```

### Non-Headless Mode (for debugging)

```bash
# See the browser in action
python tools/ui_discovery_complete.py \
  --url http://localhost:3000 \
  --username admin \
  --password admin
  # Note: no --headless flag
```

### Specific Pages Only

Modify the script to only crawl specific page types:

```python
# In ui_discovery_complete.py, modify _crawl_page method:

# Only crawl device-related pages
if page_info["page_type"] in ["device_list", "device_details"]:
    for link in links:
        self._crawl_page(link["href"], depth + 1, max_depth)
```

## Troubleshooting

### Issue: "geckodriver not found"

```bash
# Install geckodriver
wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz
tar -xvzf geckodriver-v0.33.0-linux64.tar.gz
sudo mv geckodriver /usr/local/bin/
```

### Issue: "Login failed"

Check your credentials:

```bash
# Test login manually
python -c "
from selenium import webdriver
driver = webdriver.Firefox()
driver.get('http://localhost:3000/login')
# Manually login and verify
"
```

### Issue: "Too many pages discovered"

Reduce max depth:

```bash
python tools/ui_discovery_complete.py \
  --url http://localhost:3000 \
  --max-depth 1  # Only immediate pages
```

### Issue: "Stale element references"

This is normal for dynamic pages. The script handles this gracefully by skipping stale elements.

## Best Practices

### 1. Version Control

```bash
# Commit baseline
git add ui_baseline.json
git commit -m "Add UI baseline for GenieACS"

# Commit generated POMs
git add boardfarm/boardfarm3/lib/gui/genieacs/pages/
git commit -m "Add generated GenieACS POMs"
```

### 2. Regular Scans

Set up a cron job or CI/CD workflow:

```bash
# Add to crontab (run weekly on Monday at 2 AM)
0 2 * * 1 cd /path/to/boardfarm-bdd && ./tools/check_ui_changes.sh
```

### 3. Review Generated Code

Always review generated POMs before using in production:

```bash
# Review all generated files
for file in generated_poms/*.py; do
  echo "=== $file ==="
  head -20 "$file"
  echo ""
done
```

### 4. Selective Updates

Only update POMs for pages you actually use:

```bash
# Copy only specific POMs
cp generated_poms/device_details.py boardfarm/boardfarm3/lib/gui/genieacs/pages/
cp generated_poms/device_list.py boardfarm/boardfarm3/lib/gui/genieacs/pages/
```

## Integration with Existing Tests

### Example: Using Generated POM in BDD Steps

```python
# boardfarm-bdd/tests/step_defs/reboot_ui_steps.py

from boardfarm3.lib.gui.genieacs.pages.device_details import DeviceDetailsPage

@when("the operator initiates a reboot task via the ACS UI for the CPE")
def operator_initiates_reboot_ui(acs, cpe, bf_context):
    """Use generated POM to reboot via UI."""
    # Get CPE ID
    cpe_id = f"{cpe.config['oui']}-{cpe.config['product_class']}-{cpe.config['serial']}"
    
    # Initialize UI
    acs._init_ui_helper()
    
    # Use generated POM
    device_page = DeviceDetailsPage(
        acs._ui_helper["driver"],
        acs._base_url
    )
    
    # Click reboot (method from generated POM)
    device_page.click_REBOOT_BTN()
```

## Next Steps

1. ✅ Run initial discovery
2. ✅ Review generated POMs
3. ✅ Integrate one POM into device class
4. ✅ Test with a simple scenario
5. ✅ Set up regular scans
6. ✅ Automate change detection

## Summary

The automated UI discovery and maintenance workflow:

1. **Discover** - Automatically crawl and map UI
2. **Generate** - Create POM classes from discovered elements
3. **Detect** - Compare with baseline to find changes
4. **Update** - Regenerate POMs when UI changes
5. **Integrate** - Use generated POMs in device class

This minimizes manual maintenance while keeping UI tests up-to-date!
