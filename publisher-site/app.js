const briefsTab = document.getElementById("briefsTab");
const deepReadsTab = document.getElementById("deepReadsTab");
const briefPanels = document.getElementById("briefPanels");
const deepReadPanels = document.getElementById("deepReadPanels");

const briefUnreadList = document.getElementById("briefUnreadList");
const briefReadList = document.getElementById("briefReadList");
const briefUnreadCount = document.getElementById("briefUnreadCount");
const briefReadCount = document.getElementById("briefReadCount");

const deepUnreadList = document.getElementById("deepUnreadList");
const deepReadList = document.getElementById("deepReadList");
const deepUnreadCount = document.getElementById("deepUnreadCount");
const deepReadCount = document.getElementById("deepReadCount");

const articleTitle = document.getElementById("articleTitle");
const articleMeta = document.getElementById("articleMeta");
const preview = document.getElementById("preview");
const statusBar = document.getElementById("statusBar");
const queueDeepReadButton = document.getElementById("queueDeepReadButton");
const markReadButton = document.getElementById("markReadButton");
const itemTemplate = document.getElementById("articleItemTemplate");

let currentItem = null;
let currentTab = "briefs";

const INLINE = {
  article:
    "box-sizing:border-box;width:100%;max-width:720px;margin:0 auto;padding:0 12px;background:#ffffff;color:#172033;font-size:16px;line-height:1.92;letter-spacing:0.01em;text-align:left;font-family:'PingFang SC','Noto Sans SC','Helvetica Neue',sans-serif;",
  lead:
    "width:100%;height:2px;margin:0 0 24px;border-radius:999px;background:linear-gradient(90deg,#2d7dff 0%,#51d6ff 100%);box-shadow:0 0 18px rgba(81,214,255,0.24);",
  image:
    "width:100%;border-radius:24px;display:block;margin:0 0 30px;box-shadow:0 16px 36px rgba(31,59,112,0.12);",
  info:
    "position:relative;margin:0 0 18px;padding:12px 14px;background:linear-gradient(135deg,#f8fbff 0%,#f0f7ff 100%);border:1px solid rgba(89,166,255,0.18);border-radius:14px;box-shadow:inset 0 1px 0 rgba(255,255,255,0.72),0 10px 22px rgba(47,107,255,0.06);",
  infoGlow:
    "position:absolute;top:8px;right:10px;width:34px;height:34px;border-radius:999px;background:radial-gradient(circle,rgba(24,199,255,0.14),transparent 66%);",
  infoTitle:
    "margin:0 0 6px;font-size:13px;line-height:1.35;color:#2f6bff;letter-spacing:0.08em;text-transform:uppercase;",
  infoList: "margin:6px 0 0;padding-left:18px;color:#24324a;font-size:14px;line-height:1.6;",
  infoSource: "margin:6px 0 0;font-size:13px;line-height:1.55;color:#5f7190;",
  sectionTitle:
    "margin:38px 0 14px;padding:0 0 10px;border-bottom:1px solid rgba(89,166,255,0.26);font-size:23px;line-height:1.4;letter-spacing:0.02em;color:#172033;",
  sectionAccent:
    "width:74px;height:2px;margin:-15px 0 13px;border-radius:999px;background:linear-gradient(90deg,#2d7dff 0%,#51d6ff 100%);",
  paragraph: "margin:0 0 16px;line-height:1.92;font-size:16px;color:#24324a;",
  strong: "font-weight:700;color:#10203a;",
};

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = "";
    try {
      detail = await response.text();
    } catch {
      detail = "";
    }
    throw new Error(`Request failed: ${response.status}${detail ? ` ${detail}` : ""}`);
  }
  return response.json();
}

function setStatus(message) {
  statusBar.textContent = message;
}

function setCurrentTab(tab) {
  currentTab = tab;
  briefsTab.classList.toggle("active", tab === "briefs");
  deepReadsTab.classList.toggle("active", tab === "deep-reads");
  briefPanels.classList.toggle("hidden", tab !== "briefs");
  deepReadPanels.classList.toggle("hidden", tab !== "deep-reads");
}

function formatReadDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return date.toLocaleDateString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" });
}

function isHttpUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function renderSourceLink(url, label = url) {
  if (!isHttpUrl(url)) return formatInline(label);
  const escapedUrl = escapeHtml(url);
  return `<a class="source-link" href="${escapedUrl}" target="_blank" rel="noopener noreferrer">${formatInline(label)}</a>`;
}

function renderItemList(container, items, scope, group) {
  container.replaceChildren();
  for (const item of items) {
    const node = itemTemplate.content.firstElementChild.cloneNode(true);
    node.dataset.id = item.id;
    node.dataset.scope = scope;
    const image = node.querySelector(".article-item-image");
    if (item.preview_image) {
      image.src = item.preview_image;
      image.classList.remove("hidden");
    } else {
      image.removeAttribute("src");
      image.classList.add("hidden");
    }
    node.querySelector(".article-item-title").textContent = item.title;

    const meta = node.querySelector(".article-item-meta");
    if (group === "read") {
      meta.textContent = `已读：${formatReadDate(item.read_at)}`;
    } else if (scope === "briefs" && item.queued_for_deep_read) {
      meta.textContent = `已加入详读候选 · ${formatReadDate(item.queued_at) || "待生成"}`;
    } else if (item.published_at) {
      meta.textContent = `来源日期：${item.published_at}`;
    } else {
      meta.textContent = "未读";
    }

    node.addEventListener("click", () => loadContent({ ...item, scope }));
    container.appendChild(node);
  }
}

function setActiveItem(contentId, scope) {
  document.querySelectorAll(".article-item").forEach((button) => {
    button.classList.toggle(
      "active",
      button.dataset.id === contentId && button.dataset.scope === scope,
    );
  });
}

function escapeHtml(text) {
  return text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function formatInline(text) {
  const escaped = escapeHtml(text);
  return escaped.replace(/\*\*(.+?)\*\*/g, `<strong style="${INLINE.strong}">$1</strong>`);
}

function renderMarkdown(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const parts = [
    `<article class="wechat-article" style="${INLINE.article}">`,
    `<div aria-hidden="true" style="${INLINE.lead}"></div>`,
  ];
  let paragraphBuffer = [];
  let inInfoBlock = false;
  let infoItems = [];
  let infoTitle = "";
  let infoSource = "";

  const flushParagraph = () => {
    if (!paragraphBuffer.length) return;
    parts.push(
      `<p class="wechat-paragraph" style="${INLINE.paragraph}">${formatInline(
        paragraphBuffer.join(""),
      )}</p>`,
    );
    paragraphBuffer = [];
  };

  const flushInfo = () => {
    if (!inInfoBlock) return;
    const itemsHtml = infoItems.length
      ? `<ul style="${INLINE.infoList}">${infoItems.map((item) => `<li>${formatInline(item)}</li>`).join("")}</ul>`
      : "";
    const sourceHtml = infoSource
      ? `<p style="${INLINE.infoSource}">原始来源：${renderSourceLink(infoSource)}</p>`
      : "";
    parts.push(
      `<section class="wechat-info" style="${INLINE.info}"><div aria-hidden="true" style="${INLINE.infoGlow}"></div><h4 style="${INLINE.infoTitle}">${formatInline(
        infoTitle || "来源信息",
      )}</h4>${itemsHtml}${sourceHtml}</section>`,
    );
    inInfoBlock = false;
    infoItems = [];
    infoTitle = "";
    infoSource = "";
  };

  for (const line of lines) {
    if (!line.trim()) {
      flushParagraph();
      flushInfo();
      continue;
    }

    if (line.startsWith("![](")) {
      flushParagraph();
      flushInfo();
      parts.push(`<img src="${escapeHtml(line.slice(4, -1))}" alt="" style="${INLINE.image}" />`);
      continue;
    }

    if (line.startsWith(">")) {
      flushParagraph();
      inInfoBlock = true;
      const value = line.slice(1).trim();
      if (value.startsWith("####")) {
        infoTitle = value.replace(/^####\s*/, "");
      } else if (value.startsWith("-")) {
        infoItems.push(value.replace(/^-+\s*/, ""));
      } else if (value.startsWith("原始来源：")) {
        infoSource = value.replace(/^原始来源：/, "").trim();
      } else {
        infoItems.push(value);
      }
      continue;
    }

    if (line.startsWith("## ")) {
      flushParagraph();
      flushInfo();
      parts.push(
        `<h2 class="wechat-section-title" style="${INLINE.sectionTitle}">${formatInline(
          line.slice(3).trim(),
        )}</h2><div aria-hidden="true" style="${INLINE.sectionAccent}"></div>`,
      );
      continue;
    }

    paragraphBuffer.push(line.trim());
  }

  flushParagraph();
  flushInfo();
  parts.push("</article>");
  return parts.join("");
}

async function loadBriefs() {
  const payload = await fetchJson("/api/briefs");
  renderItemList(briefUnreadList, payload.unread, "briefs", "unread");
  renderItemList(briefReadList, payload.read, "briefs", "read");
  briefUnreadCount.textContent = String(payload.unread.length);
  briefReadCount.textContent = String(payload.read.length);
  return payload.unread[0] || payload.read[0] || null;
}

async function loadDeepReads() {
  const payload = await fetchJson("/api/deep-reads");
  renderItemList(deepUnreadList, payload.unread, "deep-reads", "unread");
  renderItemList(deepReadList, payload.read, "deep-reads", "read");
  deepUnreadCount.textContent = String(payload.unread.length);
  deepReadCount.textContent = String(payload.read.length);
  return payload.unread[0] || payload.read[0] || null;
}

async function refreshData(preferredTab = currentTab) {
  setStatus("加载内容中…");
  const [firstBrief, firstDeep] = await Promise.all([loadBriefs(), loadDeepReads()]);
  setCurrentTab(preferredTab);
  const candidate =
    currentItem ||
    (preferredTab === "briefs" ? (firstBrief ? { ...firstBrief, scope: "briefs" } : null) : null) ||
    (preferredTab === "deep-reads"
      ? firstDeep
        ? { ...firstDeep, scope: "deep-reads" }
        : null
      : null);
  currentItem = null;
  if (candidate) {
    await loadContent(candidate);
  } else {
    articleTitle.textContent = "当前没有内容";
    articleMeta.textContent = "";
    preview.classList.add("empty-state");
    preview.textContent = "当前目录中还没有可展示的内容。";
    queueDeepReadButton.classList.add("hidden");
    markReadButton.classList.add("hidden");
  }
  setStatus("内容已刷新");
}

async function loadContent(item) {
  setStatus(`加载《${item.title}》中…`);
  const payload = await fetchJson(
    `/api/content?scope=${encodeURIComponent(item.scope)}&id=${encodeURIComponent(item.id)}`,
  );
  currentItem = { ...item, ...payload };
  articleTitle.textContent = item.title;
  const tags = [];
  if (payload.source_url) tags.push(renderSourceLink(payload.source_url, "打开 YouTube"));
  if (payload.read_at) tags.push(formatInline(`已读：${formatReadDate(payload.read_at)}`));
  if (item.scope === "briefs" && payload.queued_for_deep_read) {
    tags.push(formatInline(`已加入详读候选：${formatReadDate(payload.queued_at) || "待生成"}`));
  }
  if (item.scope === "deep-reads" && payload.generated === false) {
    tags.push(formatInline("详读正文待生成"));
  }
  articleMeta.innerHTML = tags.join(" · ");

  preview.classList.remove("empty-state");
  preview.innerHTML = renderMarkdown(payload.content);
  queueDeepReadButton.classList.toggle("hidden", item.scope !== "briefs");
  if (item.scope === "briefs") {
    queueDeepReadButton.textContent = payload.queued_for_deep_read ? "已加入详读候选" : "详读";
    queueDeepReadButton.disabled = Boolean(payload.queued_for_deep_read);
  } else {
    queueDeepReadButton.disabled = true;
  }
  markReadButton.classList.toggle("hidden", Boolean(payload.read_at));
  markReadButton.disabled = false;
  setActiveItem(item.id, item.scope);
  setStatus("内容已加载");
}

briefsTab.addEventListener("click", () => setCurrentTab("briefs"));
deepReadsTab.addEventListener("click", () => setCurrentTab("deep-reads"));

queueDeepReadButton.addEventListener("click", async () => {
  if (!currentItem || currentItem.scope !== "briefs") return;
  try {
    await fetchJson("/api/queue-deep-read", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: currentItem.id }),
    });
    setStatus(`《${currentItem.title}》已移入详读候选`);
    currentItem = null;
    await refreshData("briefs");
  } catch (error) {
    setStatus(`加入详读失败：${error.message}`);
  }
});

markReadButton.addEventListener("click", async () => {
  if (!currentItem) return;
  try {
    await fetchJson("/api/mark-read", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: currentItem.id, scope: currentItem.scope }),
    });
    setStatus(`《${currentItem.title}》已标记为已读`);
    currentItem = null;
    await refreshData(currentTab);
  } catch (error) {
    setStatus(`标记已读失败：${error.message}`);
  }
});

refreshData().catch((error) => {
  setStatus(`加载失败：${error.message}`);
});
