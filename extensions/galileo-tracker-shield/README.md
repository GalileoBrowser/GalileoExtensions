# Galileo Tracker Shield 0.2.0

This is a deliberately small preview package for Galileo's reviewed extension
runtime. It blocks subresources from eight common advertising and tracking host
families and applies one browser-parsed cosmetic stylesheet to hide high-
confidence empty advertising containers. It does not execute JavaScript,
inspect or transmit page content, collect telemetry, or update itself.

It is not a replacement for mature blockers such as uBlock Origin. Broader
filter syntax, procedural cosmetic filtering, per-site controls, signed
packages, and maintained upstream lists require additional GalileoEngine work.

The cosmetic selectors intentionally target vendor-specific ad containers
rather than generic words such as `.ad` or `[class*=sponsor]`. This keeps the
preview conservative and auditable. Disable the extension for a site if a
legitimate element is hidden.

To report a false positive or a site breakage, open an issue containing the
affected public URL and the rule ID. Do not attach private browsing history or
profile files.
