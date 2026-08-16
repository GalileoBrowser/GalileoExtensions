"use strict";

const grid = document.querySelector("#catalog-grid");
const status = document.querySelector("#catalog-status");

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderExtension(extension) {
  const card = element("article", "extension-card");
  const top = element("div", "extension-card__top");
  top.append(element("div", "extension-mark", extension.name.slice(0, 1)));
  top.append(element("span", "badge", extension.channel));
  card.append(top);
  card.append(element("h3", "", extension.name));
  card.append(element("p", "", extension.summary));

  const meta = element("div", "extension-meta");
  meta.append(element("span", "", `v${extension.version}`));
  meta.append(element("span", "", `${extension.rule_count} rules`));
  meta.append(element("span", "", extension.capability.replaceAll("-", " ")));
  card.append(meta);

  const actions = element("div", "extension-card__actions");
  const download = element("a", "button button-primary", "Download bundle ↓");
  download.href = extension.download_url;
  download.setAttribute("download", "");
  const source = element("a", "button", "Review source ↗");
  source.href = extension.source_url;
  actions.append(download, source);
  card.append(actions);

  const digest = element("p", "digest", `SHA-256 ${extension.package_sha256}`);
  card.append(digest);
  return card;
}

async function loadCatalog() {
  try {
    const response = await fetch("catalog.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const catalog = await response.json();
    if (!Array.isArray(catalog.extensions)) throw new Error("invalid catalog shape");
    grid.replaceChildren(...catalog.extensions.map(renderExtension));
    status.textContent = `${catalog.extensions.length} reviewed preview package${catalog.extensions.length === 1 ? "" : "s"}. Generated ${catalog.generated_at.slice(0, 10)}.`;
  } catch (error) {
    status.textContent = "The visual catalog could not be loaded.";
    const notice = element("p", "notice", "Use the machine-readable catalog or GitHub source while this page recovers.");
    const raw = element("a", "", "Open catalog.json");
    raw.href = "catalog.json";
    notice.append(" ", raw);
    grid.replaceChildren(notice);
  }
}

loadCatalog();
