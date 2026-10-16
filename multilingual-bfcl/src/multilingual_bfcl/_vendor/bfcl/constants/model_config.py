"""Checker-only registry: explicit canonical names or API dot-to-underscore names.

The upstream registry imports every inference provider. This adapter needs only its
underscore_to_dot flag; no model behavior or scoring rules are changed.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class CheckerConfig:
    underscore_to_dot: bool

MODEL_CONFIG_MAPPING = {
    'canonical': CheckerConfig(False),
    'api': CheckerConfig(True),
}
