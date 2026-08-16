# Security policy

Please report catalog, package, or website vulnerabilities privately through
GitHub's security-advisory interface for this repository. Do not include live
credentials, private browsing data, or a user's profile in a public issue.

The catalog currently publishes manually installed flat bundles. A listing is
not a signature and does not grant code execution: Galileo independently
validates the manifest, static rules, permissions, host access, size limits,
and exact review digest before enabling a package.

Until the signed-package pipeline exists, the catalog must not claim:

- one-click installation;
- automatic updates;
- Chrome Web Store or Firefox Add-ons compatibility;
- execution of background scripts, content scripts, or extension popups; or
- that a preview privacy list blocks every advertisement or tracker.
