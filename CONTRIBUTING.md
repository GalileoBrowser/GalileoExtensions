# Contributing catalog entries

The initial catalog accepts only packages supported by Galileo's reviewed
runtime: Manifest V3 static `declarativeNetRequest` rules, browser-parsed
`content_scripts.css`, and bounded native action metadata.

Every contribution must:

1. use a stable extension identifier and semantic version;
2. include unobfuscated source files in `extensions/<id>/`;
3. request the narrowest practical HTTP(S) host permissions;
4. contain no remote executable code, telemetry, secrets, or user identifiers;
5. document false-positive and site-breakage reporting;
6. keep rule IDs unique and deterministic; and
7. keep content CSS flat, UTF-8, free of `@import`, and scoped by explicit
   HTTP(S) match patterns; and
8. pass `python3 tests/validate_catalog.py`.

Executable JavaScript WebExtension APIs will be accepted only after their
engine-side isolated-world, permission, lifecycle, process, and privacy
contracts have landed in GalileoEngine.
