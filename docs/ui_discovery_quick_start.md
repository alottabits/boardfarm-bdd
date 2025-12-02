# Quick Start Guide: Using the Framework's UI Discovery Tools

## Overview

This guide shows you how to use the automated UI discovery tools included with the `boardfarm` framework to generate the `selector.yaml` file needed to configure a device's `gui` component.

## The Goal

The goal is to run a framework-provided discovery tool against a device's UI and generate a `selectors.yaml` file. You will then add this file to your test suite (e.g., `boardfarm-bdd`) and use it to test the device's UI via its `.gui` component, which is initialized by `device.init_gui()`.

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

## Quick Start: One-Command Discovery and Generation

The `boardfarm` framework provides an all-in-one discovery tool that scans a UI and generates the selector file.

```bash
# Navigate to your test suite directory
cd /home/rjvisser/projects/req-tst/boardfarm-bdd

# Run the framework's discovery tool
# (Assuming boardfarm tools are in your PATH or accessed via relative path)
python /path/to/boardfarm/tools/ui_discovery.py \
  --url http://your-device-ip \
  --username admin \
  --password admin \
  --output-yaml ./tests/ui_helpers/device_selectors.yaml \
  --headless
```

This single command will:
1. ✅ Login to the device UI.
2. ✅ Discover all pages and interactive elements.
3. ✅ Convert the findings directly into the `selectors.yaml` format.
4. ✅ Save the file in your test suite, ready to be used.

### Output

The command generates the key test artifact:
- `tests/ui_helpers/device_selectors.yaml`: The selector configuration file for your UI helper.

You can now commit this file to your test suite's repository.

## Step-by-Step Workflow

### Step 1: Generate the Initial Selector File

When starting with a new device or UI, run the discovery tool to create your first selector file.

```bash
# The output path points directly into your test suite structure
python /path/to/boardfarm/tools/ui_discovery.py \
  --url http://your-device-ip \
  --output-yaml ./tests/ui_helpers/acs_selectors_v1.2.8.yaml
```

### Step 2: Add the Selector File to Version Control

This YAML file is a critical test artifact.

```bash
git add ./tests/ui_helpers/acs_selectors_v1.2.8.yaml
git commit -m "feat: Add initial UI selectors for ACS v1.2.8"
```

### Step 3: Use the Selector File in Tests

Your BDD steps can now use this file by passing its path to the device's UI helper factory.

```python
# In a BDD step definition

def some_ui_step(acs):
    selector_path = "./tests/ui_helpers/acs_selectors_v1.2.8.yaml"
    
    # Initialize the gui component with the artifact
    gui = acs.init_gui(selector_file=selector_path)
    
    # Use the component
    gui.login()
    # ...
```

### Step 4: Regular Maintenance

When the UI under test is updated, simply re-run the discovery tool to overwrite your existing selector file with the updated selectors.

```bash
# Re-run the discovery tool to update the selectors
python /path/to/boardfarm/tools/ui_discovery.py \
  --url http://your-device-ip \
  --output-yaml ./tests/ui_helpers/acs_selectors_v1.2.8.yaml

# Review the changes
git diff ./tests/ui_helpers/acs_selectors_v1.2.8.yaml

# Commit the updated artifact
git commit -am "chore: Update UI selectors for ACS v1.2.8"
```

## Advanced: Change Detection

For a fully automated workflow, you can use the framework's change detection tools.

```bash
# 1. The test suite stores a baseline UI map (e.g., baseline_map.json)

# 2. A CI job runs the discovery tool to get the current map
python /path/to/boardfarm/tools/ui_discovery.py --output-json current_map.json

# 3. The CI job runs the change detector
python /path/to/boardfarm/tools/ui_change_detector.py \
  --baseline baseline_map.json \
  --current current_map.json

# 4. If changes are found, the generator tool creates the new YAML file
#    and a pull request is automatically created.
```

Refer to the **Automated UI Maintenance Strategy** document for full details on setting up this CI workflow.

## Summary

The UI discovery and maintenance workflow is simple:

1.  **Run Tool**: Use the `boardfarm` framework's discovery tool to generate a `selectors.yaml` file.
2.  **Add to Test Suite**: Add this file to your test project as a version-controlled artifact.
3.  **Use in Tests**: Pass the path to your selector file to `device.init_gui()` to configure and initialize the `.gui` component.
4.  **Update**: Re-run the tool to update the YAML file whenever the device UI changes.

This process keeps your tests in sync with the UI with minimal manual effort.
