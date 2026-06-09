from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str | Path) -> dict[str, Any]:
    resolved = resolve_path(path)
    with resolved.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {resolved}")
    return data


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def apply_environment_overrides(settings: dict[str, Any]) -> dict[str, Any]:
    overrides = {
        ("database", "path"): os.getenv("JOB_RADAR_DATABASE_PATH"),
        ("excel", "path"): os.getenv("JOB_RADAR_EXCEL_PATH"),
        ("logging", "path"): os.getenv("JOB_RADAR_LOG_PATH"),
    }
    for (section, key), value in overrides.items():
        if value:
            settings.setdefault(section, {})[key] = value
    return settings

