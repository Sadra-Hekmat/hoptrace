"""Tiny dependency-free PEP 517 backend for Packet Odyssey CLI.

This backend exists so a fresh Python virtual environment can install the CLI
without downloading setuptools, hatchling, poetry-core, or another build tool.
It is intentionally project-specific rather than pretending to be a general
packaging framework. Civilization has enough of those already.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
import tarfile
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
NAME = "packet-odyssey-cli"
NORMALIZED_NAME = "packet_odyssey_cli"
VERSION = "0.1.0"
DIST_INFO = f"{NORMALIZED_NAME}-{VERSION}.dist-info"
WHEEL_NAME = f"{NORMALIZED_NAME}-{VERSION}-py3-none-any.whl"


def _metadata() -> str:
    return "\n".join(
        [
            "Metadata-Version: 2.3",
            f"Name: {NAME}",
            f"Version: {VERSION}",
            "Summary: A lightweight terminal simulator for the journey from browser to database.",
            "Requires-Python: >=3.11",
            "License: Apache-2.0",
            "",
        ]
    )


def _wheel() -> str:
    return "\n".join(
        [
            "Wheel-Version: 1.0",
            "Generator: packet-odyssey-build-backend 0.1",
            "Root-Is-Purelib: true",
            "Tag: py3-none-any",
            "",
        ]
    )


def _entry_points() -> str:
    return "[console_scripts]\npacket-odyssey = packet_odyssey.cli:entrypoint\n"


def _hash(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"sha256={encoded}"


def _dist_info_files() -> dict[str, bytes]:
    return {
        f"{DIST_INFO}/METADATA": _metadata().encode(),
        f"{DIST_INFO}/WHEEL": _wheel().encode(),
        f"{DIST_INFO}/entry_points.txt": _entry_points().encode(),
    }


def _write_wheel(wheel_directory: str, editable: bool) -> str:
    destination = Path(wheel_directory)
    destination.mkdir(parents=True, exist_ok=True)
    wheel_path = destination / WHEEL_NAME
    files: dict[str, bytes] = _dist_info_files()

    if editable:
        files[f"{NORMALIZED_NAME}.pth"] = (str(ROOT / "src") + os.linesep).encode()
    else:
        package_root = ROOT / "src" / "packet_odyssey"
        for source in sorted(package_root.rglob("*.py")):
            relative = source.relative_to(ROOT / "src").as_posix()
            files[relative] = source.read_bytes()

    record_rows: list[tuple[str, str, str]] = []
    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, data in files.items():
            archive.writestr(path, data)
            record_rows.append((path, _hash(data), str(len(data))))

        record_path = f"{DIST_INFO}/RECORD"
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerows(record_rows)
        writer.writerow((record_path, "", ""))
        archive.writestr(record_path, buffer.getvalue().encode())

    return wheel_path.name


def get_requires_for_build_wheel(config_settings: dict[str, Any] | None = None) -> list[str]:
    return []


def get_requires_for_build_editable(config_settings: dict[str, Any] | None = None) -> list[str]:
    return []


def get_requires_for_build_sdist(config_settings: dict[str, Any] | None = None) -> list[str]:
    return []


def prepare_metadata_for_build_wheel(
    metadata_directory: str, config_settings: dict[str, Any] | None = None
) -> str:
    target = Path(metadata_directory) / DIST_INFO
    target.mkdir(parents=True, exist_ok=True)
    for path, data in _dist_info_files().items():
        (target / Path(path).name).write_bytes(data)
    return DIST_INFO


def prepare_metadata_for_build_editable(
    metadata_directory: str, config_settings: dict[str, Any] | None = None
) -> str:
    return prepare_metadata_for_build_wheel(metadata_directory, config_settings)


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    return _write_wheel(wheel_directory, editable=False)


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    return _write_wheel(wheel_directory, editable=True)


def build_sdist(sdist_directory: str, config_settings: dict[str, Any] | None = None) -> str:
    destination = Path(sdist_directory)
    destination.mkdir(parents=True, exist_ok=True)
    name = f"{NORMALIZED_NAME}-{VERSION}.tar.gz"
    output = destination / name
    prefix = f"{NORMALIZED_NAME}-{VERSION}"
    excluded = {".git", ".venv", "build", "dist", "__pycache__"}
    with tarfile.open(output, "w:gz") as archive:
        for source in sorted(ROOT.rglob("*")):
            if any(part in excluded for part in source.relative_to(ROOT).parts):
                continue
            if source.is_file() and not source.name.endswith((".pyc", ".db")):
                archive.add(source, arcname=f"{prefix}/{source.relative_to(ROOT)}")
    return name
