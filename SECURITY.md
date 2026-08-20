# Security policy

Please report catalog, package, or website vulnerabilities privately through
GitHub's security-advisory interface for this repository. Do not include live
credentials, private browsing data, or a user's profile in a public issue.

The catalog publishes manually reviewed static bundles and explicitly labelled
runtime packages. A listing is not a signature and does not grant code
execution: Galileo independently validates the manifest, resources, static
rules, permissions, host access, size limits, and exact review digest before
enabling a package. Runtime packages are installed disabled by default.

Until the signed-package pipeline exists, the catalog must not claim:

- one-click installation;
- automatic updates;
- Chrome Web Store or Firefox Add-ons compatibility;
- complete Chrome/Firefox or uBlock Origin parity merely because a runtime
  package is published; each package's unsupported surface must remain
  visible in its catalog metadata; or
- that a preview privacy list blocks every advertisement or tracker.
