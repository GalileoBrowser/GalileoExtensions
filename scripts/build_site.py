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
MAX_CONTENT_SCRIPT_DESCRIPTORS = 64
MAX_CONTENT_SCRIPT_PATTERNS = 256
MAX_CONTENT_SCRIPT_FILES = 64
MAX_CONTENT_STYLE_FILE_BYTES = 256 * 1024
MAX_TOTAL_CONTENT_STYLE_BYTES = 1024 * 1024
MAX_RUNTIME_PACKAGE_FILES = 4096
MAX_RUNTIME_PACKAGE_FILE_BYTES = 4 * 1024 * 1024
MAX_RUNTIME_PACKAGE_BYTES = 32 * 1024 * 1024


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_match_pattern(extension_id: str, value: object, label: str) -> None:
    if not isinstance(value, str) or not value or len(value.encode()) > 512:
        raise ValueError(f"{extension_id}: {label} contains an invalid match pattern")
    if value == "<all_urls>":
        return
    match = re.fullmatch(
        r"(http|https|\*)://(\*|\*\.[A-Za-z0-9.-]+|[A-Za-z0-9.-]+)(/.*)", value
    )
    if match is None:
        raise ValueError(
            f"{extension_id}: {label} contains unsupported pattern {value!r}"
        )
    host = match.group(2).removeprefix("*.")
    if host != "*" and any(
        not part or len(part) > 63 or part.startswith("-") or part.endswith("-")
        for part in host.split(".")
    ):
        raise ValueError(f"{extension_id}: {label} contains invalid host {host!r}")


def validate_content_scripts(
    extension_id: str, manifest: dict, directory: Path
) -> tuple[list[str], int, int]:
    descriptors = manifest.get("content_scripts", [])
    if (
        not isinstance(descriptors, list)
        or len(descriptors) > MAX_CONTENT_SCRIPT_DESCRIPTORS
    ):
        raise ValueError(
            f"{extension_id}: content_scripts exceeds the descriptor limit"
        )

    files: list[str] = []
    seen_files: set[str] = set()
    total_bytes = 0
    allowed_keys = {"matches", "exclude_matches", "css", "all_frames", "run_at"}
    for index, descriptor in enumerate(descriptors):
        label = f"content_scripts[{index}]"
        if not isinstance(descriptor, dict) or set(descriptor) - allowed_keys:
            raise ValueError(f"{extension_id}: {label} has unsupported fields")
        matches = descriptor.get("matches")
        excludes = descriptor.get("exclude_matches", [])
        css_files = descriptor.get("css")
        if (
            not isinstance(matches, list)
            or not matches
            or len(matches) > MAX_CONTENT_SCRIPT_PATTERNS
        ):
            raise ValueError(f"{extension_id}: {label}.matches is invalid")
        if (
            not isinstance(excludes, list)
            or len(excludes) > MAX_CONTENT_SCRIPT_PATTERNS
        ):
            raise ValueError(f"{extension_id}: {label}.exclude_matches is invalid")
        if len(set(matches)) != len(matches) or len(set(excludes)) != len(excludes):
            raise ValueError(
                f"{extension_id}: {label} contains duplicate match patterns"
            )
        for pattern in matches:
            validate_match_pattern(extension_id, pattern, f"{label}.matches")
        for pattern in excludes:
            validate_match_pattern(extension_id, pattern, f"{label}.exclude_matches")
        if (
            not isinstance(css_files, list)
            or not css_files
            or len(css_files) > MAX_CONTENT_SCRIPT_FILES
        ):
            raise ValueError(f"{extension_id}: {label}.css is invalid")
        if len(set(css_files)) != len(css_files):
            raise ValueError(f"{extension_id}: {label}.css contains duplicates")
        if not isinstance(descriptor.get("all_frames", False), bool):
            raise ValueError(f"{extension_id}: {label}.all_frames must be boolean")
        if descriptor.get("run_at", "document_idle") not in {
            "document_start",
            "document_end",
            "document_idle",
        }:
            raise ValueError(f"{extension_id}: {label}.run_at is unsupported")

        for relative in css_files:
            if (
                not isinstance(relative, str)
                or Path(relative).name != relative
                or not relative.endswith(".css")
            ):
                raise ValueError(
                    f"{extension_id}: content CSS must be a flat .css file"
                )
            if relative in seen_files:
                continue
            seen_files.add(relative)
            try:
                data = (directory / relative).read_bytes()
                source = data.decode("utf-8")
            except (OSError, UnicodeDecodeError) as error:
                raise ValueError(
                    f"{extension_id}: {relative} is not readable UTF-8"
                ) from error
            if len(data) > MAX_CONTENT_STYLE_FILE_BYTES or b"\0" in data:
                raise ValueError(
                    f"{extension_id}: {relative} exceeds the content CSS limit"
                )
            if re.search(r"@import\b", source, re.IGNORECASE):
                raise ValueError(
                    f"{extension_id}: {relative} may not import remote styles"
                )
            total_bytes += len(data)
            if total_bytes > MAX_TOTAL_CONTENT_STYLE_BYTES:
                raise ValueError(
                    f"{extension_id}: content CSS exceeds the aggregate limit"
                )
            files.append(relative)
    return files, len(files), total_bytes


def normalize_runtime_path(extension_id: str, value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{extension_id}: {label} must be a string path")
    path = value.removeprefix("/")
    if (
        not path
        or len(path.encode()) > 512
        or "\\" in path
        or any(part in {"", ".", ".."} for part in path.split("/"))
        or any(ord(character) < 0x20 or ord(character) == 0x7f for character in path)
    ):
        raise ValueError(f"{extension_id}: {label} is not a safe package path")
    return path


def validate_runtime_package(
    extension_id: str,
    version: str,
    directory: Path,
) -> tuple[dict, list[str], int, int, int]:
    """Validate a reviewed executable package without pretending it is static-only.

    Runtime packages still go through the browser's full manifest/resource
    validator at install time.  The catalog builder only performs the
    bounded, deterministic checks needed to publish exact source-file
    evidence; it deliberately does not reimplement the engine's WebExtension
    parser here.
    """
    manifest = load_json(directory / "manifest.json")
    if not isinstance(manifest, dict) or manifest.get("manifest_version") not in {2, 3}:
        raise ValueError(f"{extension_id}: runtime packages require Manifest V2 or V3")
    if manifest.get("version") != version:
        raise ValueError(f"{extension_id}: catalog and manifest versions differ")
    if not isinstance(manifest.get("name"), str) or not manifest["name"].strip():
        raise ValueError(f"{extension_id}: runtime manifest name is required")

    # The current catalog transport keeps executable CSS out of the runtime
    # capability until the browser can report content-style inventory without
    # confusing package CSS assets with content_scripts.css.  uBlock Origin's
    # reviewed package uses JavaScript content scripts, so this is explicit
    # rather than a silent downgrade.
    for index, descriptor in enumerate(manifest.get("content_scripts", [])):
        if not isinstance(descriptor, dict):
            raise ValueError(f"{extension_id}: content_scripts[{index}] is invalid")
        if descriptor.get("css"):
            raise ValueError(
                f"{extension_id}: runtime catalog packages may not declare content_scripts.css yet"
            )

    files: list[str] = []
    total_bytes = 0
    for path in sorted(directory.rglob("*")):
        if path.is_symlink() or not path.is_file():
            if path.is_symlink():
                raise ValueError(f"{extension_id}: runtime package may not contain symlinks")
            continue
        relative = normalize_runtime_path(
            extension_id,
            path.relative_to(directory).as_posix(),
            "runtime package file",
        )
        data = path.read_bytes()
        if not data or len(data) > MAX_RUNTIME_PACKAGE_FILE_BYTES:
            raise ValueError(
                f"{extension_id}: {relative} exceeds the runtime package file limit"
            )
        total_bytes += len(data)
        if total_bytes > MAX_RUNTIME_PACKAGE_BYTES:
            raise ValueError(
                f"{extension_id}: runtime package exceeds the aggregate byte limit"
            )
        if path.suffix.lower() in {".css", ".html", ".htm", ".js", ".mjs", ".json"}:
            try:
                data.decode("utf-8")
            except UnicodeDecodeError as error:
                raise ValueError(f"{extension_id}: {relative} is not UTF-8") from error
        files.append(relative)
    if "manifest.json" not in files:
        raise ValueError(f"{extension_id}: runtime package manifest.json is missing")
    if len(files) > MAX_RUNTIME_PACKAGE_FILES:
        raise ValueError(f"{extension_id}: runtime package contains too many files")

    # A runtime catalog entry must actually contain an executable surface.  A
    # package with only icons/data would otherwise be labelled executable while
    # never starting a background, content, popup, options, or similar host.
    executable_keys = {
        "background",
        "browser_action",
        "page_action",
        "action",
        "content_scripts",
        "options_page",
        "options_ui",
        "devtools_page",
        "side_panel",
        "sidebar_action",
        "offscreen",
        "chrome_url_overrides",
        "sandbox",
    }
    if not any(manifest.get(key) for key in executable_keys):
        raise ValueError(f"{extension_id}: runtime package has no executable entrypoint")
    return manifest, sorted(files), 0, 0, 0


def build_archive(output: Path, extension_dir: Path, files: list[str]) -> bytes:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for relative in files:
            data = (extension_dir / relative).read_bytes()
            info = zipfile.ZipInfo(relative, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output.read_bytes()


def validate_manifest(
    extension_id: str,
    version: str,
    directory: Path,
    capability: str | None = None,
) -> tuple[dict, list[str], int, int, int]:
    manifest = load_json(directory / "manifest.json")
    if capability == "runtime-package":
        return validate_runtime_package(extension_id, version, directory)
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
            raise ValueError(
                f"{extension_id}: every published rule resource must be enabled"
            )
        path = descriptor.get("path")
        if (
            not isinstance(path, str)
            or Path(path).name != path
            or not path.endswith(".json")
        ):
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
                raise ValueError(
                    f"{extension_id}: preview catalog accepts block actions only"
                )
        rule_count += len(rules)
        files.append(path)
    content_files, content_style_count, content_style_bytes = validate_content_scripts(
        extension_id,
        manifest,
        directory,
    )
    for path in content_files:
        if path in files:
            raise ValueError(
                f"{extension_id}: package resource {path} is referenced twice"
            )
        files.append(path)
    return manifest, files, rule_count, content_style_count, content_style_bytes


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
        if not isinstance(extension_id, str) or not EXTENSION_ID.fullmatch(
            extension_id
        ):
            raise ValueError("catalog extension id is invalid")
        if extension_id in seen:
            raise ValueError(f"duplicate catalog extension id: {extension_id}")
        seen.add(extension_id)
        if not isinstance(version, str) or not VERSION.fullmatch(version):
            raise ValueError(f"{extension_id}: version is invalid")
        relative_source = entry.get("source_directory")
        expected_source = f"extensions/{extension_id}"
        if relative_source != expected_source:
            raise ValueError(
                f"{extension_id}: source_directory must be {expected_source}"
            )
        extension_dir = ROOT / expected_source
        _, files, rule_count, content_style_count, content_style_bytes = (
            validate_manifest(
                extension_id,
                version,
                extension_dir,
                entry.get("capability"),
            )
        )

        source_output = output / "source" / extension_id
        source_output.mkdir()
        file_digests: dict[str, str] = {}
        source_files: dict[str, str] = {}
        for relative in files:
            data = (extension_dir / relative).read_bytes()
            output_path = source_output / relative
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(data)
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
                "content_style_count": content_style_count,
                "content_style_bytes": content_style_bytes,
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
