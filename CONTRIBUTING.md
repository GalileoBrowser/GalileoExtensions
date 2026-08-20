# Contributing catalog entries

The pre-alpha catalog accepts either the static package capability (Manifest V3
static `declarativeNetRequest` rules, browser-parsed `content_scripts.css`, and
bounded native action metadata) or the explicitly reviewed `runtime-package`
capability. Runtime packages are executable resources, but they remain
disabled until the browser's permission and enable reviews are complete and
must list their unsupported API contracts honestly.

Every contribution must:

1. use a stable extension identifier and semantic version;
2. include unobfuscated source files in `extensions/<id>/`;
3. request the narrowest practical HTTP(S) host permissions;
4. contain no remote executable code, telemetry, secrets, or user identifiers;
5. document false-positive and site-breakage reporting;
6. keep rule IDs unique and deterministic; and
7. keep content CSS flat, UTF-8, free of `@import`, and scoped by explicit
   HTTP(S) match patterns; runtime packages must not declare
   `content_scripts.css` until the catalog has separate CSS inventory metadata;
8. retain upstream license/source attribution for third-party runtime packages;
9. pass `python3 tests/validate_catalog.py`.

Executable runtime packages are accepted only after their engine-side
isolated-world, permission, lifecycle, process, and privacy contracts are
reviewed. A catalog entry is not evidence that every API used by the package
already has Chrome/Firefox parity.
