# Boardfarm-BDD Tools

This directory contains automation tools for maintaining and testing the boardfarm-bdd framework.

## UI Discovery and Maintenance

### ui_discovery_complete.py

**Purpose:** Automated discovery of GenieACS UI elements and generation of Page Object Model (POM) classes.

**Features:**
- Automatically crawls GenieACS UI to discover all pages
- Maps navigation paths between pages
- Extracts UI elements (buttons, inputs, links, tables)
- Generates POM classes for discovered pages
- Saves discovery data to JSON for change detection

**Usage:**

```bash
# Basic usage
python tools/ui_discovery_complete.py \
  --url http://localhost:3000 \
  --username admin \
  --password admin

# With all options
python tools/ui_discovery_complete.py \
  --url http://localhost:3000 \
  --username admin \
  --password admin \
  --output-json ui_discovery.json \
  --output-pom generated_poms \
  --max-depth 2 \
  --headless
```

**Options:**
- `--url` - GenieACS URL (required)
- `--username` - Login username (default: admin)
- `--password` - Login password (default: admin)
- `--output-json` - Output JSON file (default: ui_discovery.json)
- `--output-pom` - Output directory for POMs (default: generated_poms)
- `--max-depth` - Maximum crawl depth (default: 2)
- `--headless` - Run browser in headless mode

**Output:**
- JSON file with complete UI structure
- Generated POM classes in output directory
- Console summary of discovered pages

**Example Output:**

```
INFO - Starting complete UI discovery for http://localhost:3000
INFO - Logging in to http://localhost:3000
INFO - Login successful
INFO - Discovering navigation paths...
INFO - Crawling: http://localhost:3000/devices (depth: 0)
INFO - Crawling: http://localhost:3000/devices/ABC-CPE-123 (depth: 1)
INFO - Discovery complete! Found 5 pages
INFO - Discovery data saved to ui_discovery.json
INFO - Generating POM classes in generated_poms
INFO - Generated device_list
INFO - Generated device_details
INFO - POM generation complete
INFO - ============================================================
INFO - SUMMARY
INFO - ============================================================
INFO - Total pages discovered: 5
INFO - Discovery data: ui_discovery.json
INFO - Generated POMs: generated_poms
INFO - 
INFO - Page types found:
INFO -   - device_details: 1
INFO -   - device_list: 1
INFO -   - login: 1
INFO -   - tasks: 1
INFO -   - unknown: 1
```

## Future Tools

Additional tools will be added here for:
- Change detection between UI baselines
- Automated test generation
- Configuration validation
- Log analysis
- Performance monitoring

## Documentation

See the following documents for more information:
- [UI Discovery Quick Start](../docs/ui_discovery_quick_start.md)
- [Automated UI Maintenance Strategy](../docs/automated_ui_maintenance_strategy.md)
- [GenieACS UI Automation Approach](../docs/genieacs_ui_automation_approach.md)
