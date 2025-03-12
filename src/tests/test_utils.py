"""
DEPRECATED: Backwards compatibility module for test utilities.
Please use the modules in src.tests.common instead:
- src.tests.common.mocks: Mock objects and functions
- src.tests.common.base: Base test classes
- src.tests.common.speech: Speech synthesis and playback utilities
"""

import warnings

# Display deprecation warning
warnings.warn(
    "test_utils.py is deprecated. Use src.tests.common.* modules instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from common modules for backwards compatibility
from src.tests.common.mocks import *
from src.tests.common.base import *
from src.tests.common.speech import *

# The classes and functions below are maintained for backwards compatibility
# They are simply re-exports from the common modules
