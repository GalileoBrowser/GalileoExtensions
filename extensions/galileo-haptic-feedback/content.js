(() => {
  "use strict";

  // The catalog marks this package Android-only. Keep the runtime guard too:
  // it makes an accidentally sideloaded desktop package a no-op instead of
  // adding listeners or trying to emulate haptics with audio.
  const userAgent = navigator.userAgent || "";
  const userAgentPlatform = navigator.userAgentData?.platform || "";
  const platform = navigator.platform || "";
  const isAndroid = /android/i.test(
    `${userAgent} ${userAgentPlatform} ${platform}`,
  );

  if (!isAndroid || typeof navigator.vibrate !== "function") {
    return;
  }

  const DEFAULTS = Object.freeze({
    enabled: true,
    linkFeedback: true,
    scrollFeedback: true,
    linkDuration: 9,
    scrollDuration: 5,
    scrollThreshold: 120,
    scrollCooldown: 160,
  });

  let settings = { ...DEFAULTS };
  let lastLinkPulseAt = -Infinity;
  let lastScrollPulseAt = -Infinity;

  const extensionApi = globalThis.browser || globalThis.chrome;
  const storage = extensionApi?.storage?.local;

  function finiteNumber(value, fallback, minimum, maximum) {
    const number = Number(value);
    if (!Number.isFinite(number)) return fallback;
    return Math.min(maximum, Math.max(minimum, Math.round(number)));
  }

  function normaliseSettings(candidate) {
    const source = candidate && typeof candidate === "object" ? candidate : {};
    return {
      enabled: source.enabled !== false,
      linkFeedback: source.linkFeedback !== false,
      scrollFeedback: source.scrollFeedback !== false,
      linkDuration: finiteNumber(
        source.linkDuration,
        DEFAULTS.linkDuration,
        1,
        40,
      ),
      scrollDuration: finiteNumber(
        source.scrollDuration,
        DEFAULTS.scrollDuration,
        1,
        30,
      ),
      scrollThreshold: finiteNumber(
        source.scrollThreshold,
        DEFAULTS.scrollThreshold,
        40,
        480,
      ),
      scrollCooldown: finiteNumber(
        source.scrollCooldown,
        DEFAULTS.scrollCooldown,
        80,
        800,
      ),
    };
  }

  function applySettings(candidate) {
    settings = normaliseSettings({ ...settings, ...candidate });
  }

  function loadSettings() {
    if (!storage || typeof storage.get !== "function") return;
    const apply = (result) => applySettings(result);
    try {
      // Firefox's WebExtension API and modern Chromium return a Promise;
      // older Chromium Android builds expose the callback form.
      if (storage.get.length >= 2) {
        storage.get(DEFAULTS, apply);
      } else {
        Promise.resolve(storage.get(DEFAULTS)).then(apply).catch(() => {});
      }
    } catch (_error) {
      // A missing storage bridge must never make page interaction fail.
    }
  }

  loadSettings();

  const storageChanges = extensionApi?.storage?.onChanged;
  if (storageChanges && typeof storageChanges.addListener === "function") {
    storageChanges.addListener((changes, areaName) => {
      if (areaName !== "local" || !changes || typeof changes !== "object") {
        return;
      }
      const next = {};
      for (const key of Object.keys(DEFAULTS)) {
        if (Object.prototype.hasOwnProperty.call(changes, key)) {
          next[key] = changes[key]?.newValue;
        }
      }
      applySettings(next);
    });
  }

  function now() {
    return typeof performance?.now === "function" ? performance.now() : Date.now();
  }

  function pulse(kind) {
    if (!settings.enabled) return false;
    const timestamp = now();
    if (kind === "link") {
      if (!settings.linkFeedback || timestamp - lastLinkPulseAt < 45) {
        return false;
      }
    } else if (!settings.scrollFeedback) {
      return false;
    } else if (timestamp - lastScrollPulseAt < settings.scrollCooldown) {
      return false;
    }

    const duration =
      kind === "link" ? settings.linkDuration : settings.scrollDuration;
    try {
      const accepted = navigator.vibrate(duration);
      if (accepted === false) return false;
    } catch (_error) {
      return false;
    }

    if (kind === "link") {
      lastLinkPulseAt = timestamp;
    } else {
      lastScrollPulseAt = timestamp;
    }
    return true;
  }

  const ACTIVATABLE_SELECTOR = [
    "a[href]",
    "area[href]",
    "button",
    "input[type='button']",
    "input[type='image']",
    "input[type='reset']",
    "input[type='submit']",
    "[role='button']",
    "[role='link']",
  ].join(",");

  function activatableFrom(target) {
    if (!(target instanceof Element)) return null;
    const element = target.closest(ACTIVATABLE_SELECTOR);
    if (!element || element.matches(":disabled, [aria-disabled='true']")) {
      return null;
    }
    return element;
  }

  function pointerIsPrimary(event) {
    return event.isPrimary !== false && (event.button === undefined || event.button === 0);
  }

  function handlePointerDown(event) {
    if (event.defaultPrevented || !pointerIsPrimary(event)) return;
    // A mouse event is useful for testing, but haptic feedback is explicitly
    // an Android touch affordance and should not fire for a desktop mouse.
    if (event.pointerType === "mouse") return;
    if (activatableFrom(event.target)) pulse("link");
  }

  function handleTouchStart(event) {
    if (!event.defaultPrevented && activatableFrom(event.target)) {
      pulse("link");
    }
  }

  function handleKeyDown(event) {
    if (event.defaultPrevented || event.repeat) return;
    const target = activatableFrom(event.target);
    if (!target) return;
    if (event.key === "Enter" || (event.key === " " && target.matches("button, [role='button']"))) {
      pulse("link");
    }
  }

  function handleKeyboardClick(event) {
    // Pointer activation already pulsed on pointerdown/touchstart. detail === 0
    // identifies keyboard activation in the normal DOM event model.
    if (event.detail === 0 && activatableFrom(event.target)) pulse("link");
  }

  document.addEventListener("pointerdown", handlePointerDown, true);
  if (typeof PointerEvent === "undefined") {
    document.addEventListener("touchstart", handleTouchStart, {
      capture: true,
      passive: true,
    });
  }
  document.addEventListener("keydown", handleKeyDown, true);
  document.addEventListener("click", handleKeyboardClick, true);

  const scrollStates = new WeakMap();
  const pendingScrolls = new Set();
  let scrollFrame = 0;

  function scrollTarget(event) {
    if (event.target === document || event.target === document.documentElement || event.target === document.body) {
      return document.scrollingElement || document.documentElement;
    }
    return event.target instanceof Element ? event.target : null;
  }

  function scrollPosition(target) {
    if (target === document.scrollingElement || target === document.documentElement || target === document.body) {
      return { x: window.scrollX || 0, y: window.scrollY || 0 };
    }
    return { x: target.scrollLeft || 0, y: target.scrollTop || 0 };
  }

  function scheduleScrollFlush() {
    if (scrollFrame) return;
    const flush = () => {
      scrollFrame = 0;
      flushScrolls();
    };
    if (typeof requestAnimationFrame === "function") {
      scrollFrame = requestAnimationFrame(flush);
    } else {
      scrollFrame = setTimeout(flush, 16);
    }
  }

  function handleScroll(event) {
    if (!settings.enabled || !settings.scrollFeedback) return;
    const target = scrollTarget(event);
    if (!target) return;
    let state = scrollStates.get(target);
    if (!state) {
      const position = scrollPosition(target);
      state = {
        position,
        direction: 0,
        distance: 0,
      };
      scrollStates.set(target, state);
    }
    pendingScrolls.add(target);
    scheduleScrollFlush();
  }

  function flushScrolls() {
    for (const target of pendingScrolls) {
      const state = scrollStates.get(target);
      if (!state) continue;
      const position = scrollPosition(target);
      const deltaX = position.x - state.position.x;
      const deltaY = position.y - state.position.y;
      const delta = Math.abs(deltaY) >= Math.abs(deltaX) ? deltaY : deltaX;
      state.position = position;
      if (!delta) continue;

      const direction = Math.sign(delta);
      if (state.direction && direction !== state.direction) {
        state.distance = 0;
        pulse("scroll");
      } else {
        state.distance += Math.abs(delta);
        if (state.distance >= settings.scrollThreshold && pulse("scroll")) {
          state.distance = 0;
        }
      }
      state.direction = direction;
    }
    pendingScrolls.clear();
  }

  document.addEventListener("scroll", handleScroll, {
    capture: true,
    passive: true,
  });
})();
