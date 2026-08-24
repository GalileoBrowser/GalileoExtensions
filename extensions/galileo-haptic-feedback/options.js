(() => {
  "use strict";

  const DEFAULTS = Object.freeze({
    enabled: true,
    linkFeedback: true,
    scrollFeedback: true,
    linkDuration: 9,
    scrollDuration: 5,
    scrollThreshold: 120,
    scrollCooldown: 160,
  });

  const api = globalThis.browser || globalThis.chrome;
  const storage = api?.storage?.local;
  const form = document.querySelector("#settings-form");
  const status = document.querySelector("#status");

  function number(value, fallback, minimum, maximum) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.min(maximum, Math.max(minimum, Math.round(parsed)));
  }

  function normalise(candidate) {
    const source = candidate && typeof candidate === "object" ? candidate : {};
    return {
      enabled: source.enabled !== false,
      linkFeedback: source.linkFeedback !== false,
      scrollFeedback: source.scrollFeedback !== false,
      linkDuration: number(source.linkDuration, DEFAULTS.linkDuration, 1, 40),
      scrollDuration: number(source.scrollDuration, DEFAULTS.scrollDuration, 1, 30),
      scrollThreshold: number(source.scrollThreshold, DEFAULTS.scrollThreshold, 40, 480),
      scrollCooldown: number(source.scrollCooldown, DEFAULTS.scrollCooldown, 80, 800),
    };
  }

  function read() {
    if (!storage || typeof storage.get !== "function") return Promise.resolve({ ...DEFAULTS });
    try {
      if (storage.get.length >= 2) {
        return new Promise((resolve) => storage.get(DEFAULTS, resolve));
      }
      return Promise.resolve(storage.get(DEFAULTS));
    } catch (_error) {
      return Promise.resolve({ ...DEFAULTS });
    }
  }

  function write(value) {
    if (!storage || typeof storage.set !== "function") return Promise.resolve();
    try {
      if (storage.set.length >= 2) {
        return new Promise((resolve) => storage.set(value, resolve));
      }
      return Promise.resolve(storage.set(value));
    } catch (_error) {
      return Promise.reject(_error);
    }
  }

  function setForm(settings) {
    for (const key of ["enabled", "linkFeedback", "scrollFeedback"]) {
      document.querySelector(`#${key}`).checked = settings[key];
    }
    for (const key of ["linkDuration", "scrollDuration", "scrollThreshold", "scrollCooldown"]) {
      document.querySelector(`#${key}`).value = settings[key];
    }
    updateOutputs(settings);
  }

  function readForm() {
    return normalise({
      enabled: document.querySelector("#enabled").checked,
      linkFeedback: document.querySelector("#linkFeedback").checked,
      scrollFeedback: document.querySelector("#scrollFeedback").checked,
      linkDuration: document.querySelector("#linkDuration").value,
      scrollDuration: document.querySelector("#scrollDuration").value,
      scrollThreshold: document.querySelector("#scrollThreshold").value,
      scrollCooldown: document.querySelector("#scrollCooldown").value,
    });
  }

  function updateOutputs(settings) {
    document.querySelector("#linkDurationOutput").value = `${settings.linkDuration} ms`;
    document.querySelector("#scrollDurationOutput").value = `${settings.scrollDuration} ms`;
    document.querySelector("#scrollThresholdOutput").value = `${settings.scrollThreshold} px`;
    document.querySelector("#scrollCooldownOutput").value = `${settings.scrollCooldown} ms`;
  }

  function announce(message) {
    status.textContent = message;
    window.clearTimeout(announce.timer);
    announce.timer = window.setTimeout(() => {
      status.textContent = "";
    }, 2400);
  }

  async function save(event) {
    event?.preventDefault();
    const settings = readForm();
    try {
      await write(settings);
      setForm(settings);
      announce("Settings saved.");
    } catch (_error) {
      announce("Settings could not be saved in this browser build.");
    }
  }

  form.addEventListener("submit", save);
  form.addEventListener("input", () => updateOutputs(readForm()));
  document.querySelector("#reset").addEventListener("click", async () => {
    setForm(DEFAULTS);
    await save();
  });

  read().then((settings) => setForm(normalise(settings)));
})();
