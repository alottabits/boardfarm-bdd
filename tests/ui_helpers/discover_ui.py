#!/usr/bin/env python3
"""Convenience wrapper for UI discovery tool.

This script provides a local entry point for the UI discovery functionality
from boardfarm3.lib.gui.ui_discovery.

Features:
    - Automatic crawling and graph generation
    - Query parameter capture on navigation edges
    - Interaction discovery (modals, forms)
    - URL pattern detection

Prerequisites:
    - Boardfarm must be installed in the active Python environment
      (e.g., with 'pip install -e /path/to/boardfarm')
    - Required dependencies: selenium, networkx

Usage:
    python discover_ui.py --url http://127.0.0.1:3000 --username admin --password admin

All command-line options from ui_discovery.py are supported:
    --url                    Base URL of the application to crawl (required)
    --output                 Output file for UI map (default: ui_map.json)
    --username               Login username (optional)
    --password               Login password (optional)
    --login-url              Custom login URL (optional)
    --headless               Run browser in headless mode (default: True)
    --no-headless            Run browser with GUI
    --no-login               Skip login step
    --disable-pattern-detection    Disable URL pattern detection
    --pattern-min-count      Minimum URLs required to form a pattern (default: 3)
    --skip-pattern-duplicates      Skip URLs matching detected patterns after sampling
    --pattern-sample-size    Number of pattern instances to crawl before skipping (default: 3)
    --discover-interactions  Discover modals and dialogs by clicking buttons
    --safe-buttons           Comma-separated list of safe button text patterns
    --interaction-timeout    Seconds to wait for modals to appear after clicking (default: 2)
"""

from boardfarm3.lib.gui.ui_discovery import main

if __name__ == "__main__":
    main()
