"""Robot Framework keyword libraries for Boardfarm BDD tests.

This package provides keyword libraries that mirror the pytest-bdd step definitions
in tests/step_defs/. Each library uses the @keyword decorator to map clean Python
function names to scenario step text.

Libraries:
    BoardfarmKeywords: Base keywords for device access and testbed utilities
    AcsKeywords: ACS (Auto Configuration Server) operations
    CpeKeywords: CPE (Customer Premises Equipment) operations
    VoiceKeywords: SIP phone and voice call operations
    BackgroundKeywords: Background/setup operations
    OperatorKeywords: Operator-initiated operations
    AcsGuiKeywords: ACS GUI operations
    DeviceClassKeywords: Device initialization and class operations
    HelloKeywords: Simple hello/smoke test keywords

Usage:
    *** Settings ***
    Library    ../libraries/boardfarm_keywords.py
    Library    ../libraries/acs_keywords.py

    *** Test Cases ***
    Example Test
        ${acs}=    Get Device By Type    ACS
        ${cpe}=    Get Device By Type    CPE
        The CPE Is Online Via ACS    ${acs}    ${cpe}
"""

from robot.libraries.boardfarm_keywords import BoardfarmKeywords
from robot.libraries.acs_keywords import AcsKeywords
from robot.libraries.cpe_keywords import CpeKeywords
from robot.libraries.voice_keywords import VoiceKeywords
from robot.libraries.background_keywords import BackgroundKeywords
from robot.libraries.operator_keywords import OperatorKeywords
from robot.libraries.acs_gui_keywords import AcsGuiKeywords
from robot.libraries.device_class_keywords import DeviceClassKeywords
from robot.libraries.hello_keywords import HelloKeywords

__all__ = [
    "BoardfarmKeywords",
    "AcsKeywords",
    "CpeKeywords",
    "VoiceKeywords",
    "BackgroundKeywords",
    "OperatorKeywords",
    "AcsGuiKeywords",
    "DeviceClassKeywords",
    "HelloKeywords",
]
