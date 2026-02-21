"""Load voice_keywords module without triggering robot.libraries package init.

The robot/libraries/__init__.py imports all libraries, which requires
the boardfarm plugin. We load voice_keywords.py directly for unit tests.
"""

import importlib.util
from pathlib import Path

_root = Path(__file__).resolve().parents[3]
_voice_keywords_path = _root / "robot" / "libraries" / "voice_keywords.py"

_spec = importlib.util.spec_from_file_location("voice_keywords", _voice_keywords_path)
_voice_keywords = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_voice_keywords)

VoiceKeywords = _voice_keywords.VoiceKeywords
discover_phones_by_location = _voice_keywords.discover_phones_by_location
