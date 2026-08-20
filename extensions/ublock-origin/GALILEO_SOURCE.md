# uBlock Origin 1.73.0 catalog record

This directory is a review-first packaging of the upstream uBlock Origin
Chromium release for Galileo's pre-alpha extension catalog. It retains the
upstream package files and adds this catalog record; the browser's catalog
digest covers the resulting published package exactly.

- Upstream project: <https://github.com/gorhill/uBlock>
- Upstream release: `1.73.0`
- Upstream license: `LICENSE.txt` (GPL-3.0-or-later)
- Galileo status: installed disabled; explicit permission and enable review is required

Galileo does not claim complete uBlock Origin compatibility. In particular,
popup-to-page DOM mediation, isolated-world semantics, response-body filter
streaming, and automatic updates remain browser work. This file is catalog
metadata and is not executed by the extension.
