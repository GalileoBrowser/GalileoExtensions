# Galileo Extensions

This repository is the source of the official, reviewed extension catalog for
[Galileo Browser](https://galileobrowser.com/).

- Catalog: <https://extensions.galileobrowser.com/>
- Machine-readable index: <https://extensions.galileobrowser.com/catalog.json>
- Browser engine: <https://github.com/GalileoBrowser/GalileoEngine>

Galileo's current extension runtime is intentionally bounded. It can install
reviewed Manifest V3 packages containing static `declarativeNetRequest` rules,
browser-parsed `content_scripts.css`, and browser-owned toolbar metadata. The
official catalog also carries a digest-verified uBlock Origin runtime package
so the browser's executable-resource path can be tested. Runtime packages
remain disabled until permission review and explicit enablement, and the
catalog labels missing Chrome/Firefox behaviours instead of presenting
unsupported APIs as complete.

The catalog also includes Galileo Haptic Feedback, a small Android-only
Manifest V3 package. It uses the standard `navigator.vibrate()` API for
bounded link/control and deliberate-scroll cues, stores only local preferences,
and safely becomes a no-op on desktop or on devices without vibration support.

## Local build

```bash
python3 scripts/build_site.py --output dist
python3 tests/validate_catalog.py --site dist
python3 -m http.server 4173 --directory dist
```

The build creates deterministic extension archives and a catalog whose SHA-256
digests are calculated from the exact published bytes.

## Installing a reviewed package

1. Open **Get Extensions** or **Manage Extensions** in Galileo.
2. Choose **Review in Galileo** for Galileo Tracker Shield, Galileo Haptic
   Feedback, or uBlock Origin.
   The catalog returns to `servo:addons` with that exact package selected.
3. Galileo downloads each published package file from this fixed catalog and
   checks its exact SHA-256 digest before parsing it.
4. Review the requested hosts and permissions, install it disabled, then complete
   the separate enable review. uBlock Origin is a compatibility preview: its
   full popup, isolated-DOM, filter-response streaming, and update semantics
   still require browser work.

The deterministic zip remains available for auditing and for the local-package
fallback used by older Galileo builds. Unattended installation and automatic
updates remain unavailable until Galileo has package signing, revocation, and a
browser-owned update pipeline.

## Security

Catalog submissions must remain auditable and bounded. Do not add executable
remote code, obfuscated payloads, telemetry, or update URLs. See
[SECURITY.md](SECURITY.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Site code and Galileo-authored extension packages are available under the MIT
license. Third-party additions must retain their own compatible license and
attribution.
