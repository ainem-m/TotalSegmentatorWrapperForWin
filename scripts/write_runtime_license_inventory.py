from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path


def _license_summary(distribution: importlib.metadata.Distribution) -> str:
    metadata = distribution.metadata
    expression = (metadata.get("License-Expression") or "").strip()
    if expression:
        return expression
    classifiers = [
        item.removeprefix("License :: ").strip()
        for item in metadata.get_all("Classifier", [])
        if item.startswith("License :: ")
    ]
    if classifiers:
        return "; ".join(classifiers)
    raw = (metadata.get("License") or "").strip()
    if raw:
        return raw if len(raw) <= 160 else "embedded_license_text"
    return "unresolved"


def _license_files(
    distribution: importlib.metadata.Distribution,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for relative in distribution.files or []:
        lowered = relative.name.lower()
        if not (
            "license" in lowered
            or "copying" in lowered
            or "notice" in lowered
        ):
            continue
        absolute = Path(distribution.locate_file(relative))
        if not absolute.is_file():
            continue
        digest = hashlib.sha256(absolute.read_bytes()).hexdigest()
        records.append(
            {
                "name": relative.name,
                "bytes": absolute.stat().st_size,
                "sha256": digest,
            }
        )
    return sorted(records, key=lambda item: str(item["name"]).lower())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    packages: list[dict[str, object]] = []
    unresolved: list[str] = []
    for distribution in sorted(
        importlib.metadata.distributions(),
        key=lambda item: (item.metadata.get("Name") or "").lower(),
    ):
        name = distribution.metadata.get("Name") or distribution._path.name
        license_summary = _license_summary(distribution)
        license_files = _license_files(distribution)
        if license_summary == "unresolved" and not license_files:
            unresolved.append(name)
        packages.append(
            {
                "name": name,
                "version": distribution.version,
                "license": license_summary,
                "license_files": license_files,
            }
        )

    payload = {
        "schema": "totalsegmentator_wrapper.windows_runtime_license_inventory.v1",
        "status": "pass" if not unresolved else "fail",
        "distribution_count": len(packages),
        "unresolved": sorted(unresolved, key=str.lower),
        "distributions": packages,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
