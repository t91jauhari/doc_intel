"""Native engine registry and captured compatibility defaults."""

from pathlib import Path
from .configuration.native_catalog import native_catalog
from .engine.context import check_directory
from .engine.profiles import PROFILE_NAMES, get_profile
from .engine.account_opening.profiles import REFERENCE as ACCOUNT_REFERENCE

ENGINE = Path(__file__).resolve().parent / "engine"

_NATIVE_CATALOG = native_catalog()
LABELS = _NATIVE_CATALOG["labels"]
CLASSIFY_DESCRIPTIONS = _NATIVE_CATALOG["classification_descriptions"]
SUFFIXES = _NATIVE_CATALOG["suffixes"]
GROUPING_PREFIXES = _NATIVE_CATALOG["grouping_prefixes"]
SUFFIX_ALIASES = _NATIVE_CATALOG["suffix_aliases"]
SOP_MESSAGE_TEMPLATES = _NATIVE_CATALOG["message_templates"]
