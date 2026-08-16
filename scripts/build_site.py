#!/usr/bin/env python3
"""Build deterministic Galileo extension packages and the static catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CATALOG = ROOT / "catalog" / "catalog.source.json"
EXTENSION_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION = re.compile(r"^\d+(?:\.\d+){1,3}$")
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def build_archive(output: Path, extension_dir: Path, files: list[str]) -> bytes:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in files:
            data = (extension_dir / relative).read_bytes()
            info = zipfile.ZipInfo(relative, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output.read_bytes()


def validate_manifest(extension_id: str, version: str, directory: Path) -> tuple[dict, list[str], int]:
    manifest = load_json(directory / "manifest.json")
    if not isinstance(manifest, dict) or manifest.get("manifest_version") != 3:
        raise ValueError(f"{extension_id}: only Manifest V3 is publishable")
    if manifest.get("version") != version:
        raise ValueError(f"{extension_id}: catalog and manifest versions differ")
    if manifest.get("permissions") != ["declarativeNetRequest"]:
        raise ValueError(f"{extension_id}: unexpected permission set")
    resources = manifest.get("declarative_net_request", {}).get("rule_resources")
    if not isinstance(resources, list) or not resources:
        raise ValueError(f"{extension_id}: a static rule resource is required")
    files = ["manifest.json"]
    rule_count = 0
    rule_ids: set[int] = set()
    for descriptor in resources:
        if not isinstance(descriptor, dict) or descriptor.get("enabled") is not True:
            raise ValueError(f"{extension_id}: every published rule resource must be enabled")
        path = descriptor.get("path")
        if not isinstance(path, str) or Path(path).name != path or not path.endswith(".json"):
            raise ValueError(f"{extension_id}: rule resources must be flat JSON files")
        rules = load_json(directory / path)
        if not isinstance(rules, list):
            raise ValueError(f"{extension_id}: {path} is not a rule array")
        for rule in rules:
            if not isinstance(rule, dict) or not isinstance(rule.get("id"), int):
                raise ValueError(f"{extension_id}: every rule needs an integer id")
            if rule["id"] in rule_ids:
                raise ValueError(f"{extension_id}: duplicate rule id {rule['id']}")
            rule_ids.add(rule["id"])
            if rule.get("action") != {"type": "block"}:
                raise ValueError(f"{extension_id}: preview catalog accepts block actions only")
        rule_count += len(rules)
        files.append(path)
    return manifest, files, rule_count


def build(output: Path) -> None:
    if output.resolve() == ROOT.resolve():
        raise ValueError("output directory must not be the repository root")
    shutil.rmtree(output, ignore_errors=True)
    shutil.copytree(ROOT / "public", output)
    (output / "downloads").mkdir()
    (output / "source").mkdir()

    source = load_json(SOURCE_CATALOG)
    if not isinstance(source, dict) or source.get("schema_version") != 1:
        raise ValueError("catalog schema_version must be 1")
    extensions = source.get("extensions")
    if not isinstance(extensions, list):
        raise ValueError("catalog extensions must be an array")

    published: list[dict] = []
    seen: set[str] = set()
    for entry in extensions:
        if not isinstance(entry, dict):
            raise ValueError("catalog entries must be objects")
        extension_id = entry.get("id")
        version = entry.get("version")
        if not isinstance(extension_id, str) or not EXTENSION_ID.fullmatch(extension_id):
            raise ValueError("catalog extension id is invalid")
        if extension_id in seen:
            raise ValueError(f"duplicate catalog extension id: {extension_id}")
        seen.add(extension_id)
        if not isinstance(version, str) or not VERSION.fullmatch(version):
            raise ValueError(f"{extension_id}: version is invalid")
        relative_source = entry.get("source_directory")
        expected_source = f"extensions/{extension_id}"
        if relative_source != expected_source:
            raise ValueError(f"{extension_id}: source_directory must be {expected_source}")
        extension_dir = ROOT / expected_source
        _, files, rule_count = validate_manifest(extension_id, version, extension_dir)

        source_output = output / "source" / extension_id
        source_output.mkdir()
        file_digests: dict[str, str] = {}
        source_files: dict[str, str] = {}
        for relative in files:
            data = (extension_dir / relative).read_bytes()
            (source_output / relative).write_bytes(data)
            file_digests[relative] = sha256(data)
            source_files[relative] = f"source/{extension_id}/{relative}"

        archive_name = f"{extension_id}-{version}.zip"
        archive_path = output / "downloads" / archive_name
        archive_bytes = build_archive(archive_path, extension_dir, files)
        public_entry = dict(entry)
        public_entry.pop("source_directory", None)
        public_entry.update(
            {
                "rule_count": rule_count,
                "download_url": f"downloads/{archive_name}",
                "package_bytes": len(archive_bytes),
                "package_sha256": sha256(archive_bytes),
                "files": file_digests,
                "source_files": source_files,
            }
        )
        published.append(public_entry)

    generated = {key: value for key, value in source.items() if key != "extensions"}
    generated["generated_at"] = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    generated["extensions"] = published
    (output / "catalog.json").write_bytes(canonical_json(generated))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    build(args.output.resolve())
    print(f"Built Galileo Extensions catalog at {args.output.resolve()}")


if __name__ == "__main__":
    main()
