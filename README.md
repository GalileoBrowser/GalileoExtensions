# Galileo Extensions

This repository is the source of the official, reviewed extension catalog for
[Galileo Browser](https://galileobrowser.com/).

- Catalog: <https://extensions.galileobrowser.com/>
- Machine-readable index: <https://extensions.galileobrowser.com/catalog.json>
- Browser engine: <https://github.com/GalileoBrowser/GalileoEngine>

Galileo's current extension runtime is intentionally narrow. It can install
reviewed Manifest V3 packages containing static `declarativeNetRequest` rules
and can expose browser-owned toolbar metadata. Background scripts, content
scripts, popup execution, dynamic rules, and broad Chrome/Firefox extension API
compatibility are not yet available. The catalog labels that boundary instead
of presenting unsupported packages as installable.

## Local build

```bash
python3 scripts/build_site.py --output dist
python3 tests/validate_catalog.py --site dist
python3 -m http.server 4173 --directory dist
```

The build creates deterministic extension archives and a catalog whose SHA-256
digests are calculated from the exact published bytes.

## Installing the preview blocker

1. Download the bundle from the catalog and extract it.
2. In Galileo, open **Menu → More tools → Manage Extensions**.
3. Choose **Install local add-on**.
4. Select `manifest.json` and `rules.json` together.
5. Review the requested hosts, enable the extension, and separately opt into
   private windows only if desired.

One-click remote installation is deliberately unavailable until Galileo has a
signed-package and catalog-trust pipeline.

## Security

Catalog submissions must remain auditable and bounded. Do not add executable
remote code, obfuscated payloads, telemetry, or update URLs. See
[SECURITY.md](SECURITY.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Site code and Galileo-authored extension packages are available under the MIT
license. Third-party additions must retain their own compatible license and
attribution.
