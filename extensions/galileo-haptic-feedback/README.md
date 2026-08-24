# Galileo Haptic Feedback 0.1.0

An Android-only Galileo Browser extension that adds small, bounded vibration
cues when a user activates a link or control and when a deliberate scroll
passes a distance threshold. It uses the standard `navigator.vibrate()` API;
there is no audio fallback and no native bridge hidden behind the extension.

## Behaviour

- A short pulse is emitted on a primary touch/pen activation of links, buttons,
  and accessible button/link controls.
- Keyboard activation is covered for keyboard and assistive-technology users.
- Scrolling is coalesced to animation frames and throttled. A pulse occurs
  after the configured distance, or once when the direction changes.
- Dynamic page content is covered through delegated document listeners.
- Settings are stored locally in the extension's storage area and can be
  changed from the extension options page.
- Desktop and non-Android installations are a safe no-op, even if a package is
  sideloaded outside Galileo's Android-only catalog policy.

The defaults are intentionally conservative to avoid buzzes during tiny
scrolls, accidental double events, or rapid touch gestures. The device and
browser may still decline vibration according to their own accessibility,
power-saving, focus, or user settings.

## Privacy and permissions

The package requests only `storage`. It does not read page text, collect URLs,
send telemetry, inject remote code, or make network requests. The content
script observes only activation and scroll events needed to decide whether to
call `navigator.vibrate()`.

This package is published as Android-only in Galileo's catalog and carries the
same platform declaration in its manifest. It should not be presented as a
desktop extension.

## Compatibility boundary

The extension requires a Galileo build that can run Manifest V3 JavaScript
content scripts and the `storage` API. Devices or browser builds without
`navigator.vibrate()` simply receive no feedback. It does not claim to expose
the Android system haptics engine or vendor-specific vibration patterns.
