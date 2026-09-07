from __future__ import annotations

import json
from pathlib import Path

from . import __version__
from .contracts import PanelMetadata


def write_provenance(path: Path, metadata: PanelMetadata, command: str, inputs: list[str] | None = None) -> None:
    payload = {
        "schema_version": 1,
        "package_version": __version__,
        "command": command,
        "inputs": sorted(inputs or []),
        "metadata": metadata.as_dict(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
