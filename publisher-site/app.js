const unscheduledList = document.getElementById("unscheduledList");
const scheduledList = document.getElementById("scheduledList");
const unscheduledCount = document.getElementById("unscheduledCount");
const scheduledCount = document.getElementById("scheduledCount");
const briefUnreadList = document.getElementById("briefUnreadList");
const briefArchivedList = document.getElementById("briefArchivedList");
const briefUnreadCount = document.getElementById("briefUnreadCount");
const briefArchivedCount = document.getElementById("briefArchivedCount");
const articleTitle = document.getElementById("articleTitle");
const articleMeta = document.getElementById("articleMeta");
const preview = document.getElementById("preview");
const statusBar = document.getElementById("statusBar");
const copyButton = document.getElementById("copyButton");
const promoteButton = document.getElementById("promoteButton");
const scheduleButton = document.getElementById("scheduleButton");
const scheduleDateInput = document.getElementById("scheduleDateInput");
const refreshButton = document.getElementById("refreshButton");
const selectedTab = document.getElementById("selectedTab");
const briefsTab = document.getElementById("briefsTab");
const selectedPanels = document.getElementById("selectedPanels");
const briefPanels = document.getElementById("briefPanels");
const itemTemplate = document.getElementById("articleItemTemplate");

let currentItem = null;
let currentTab = "selected";
let pendingSelection = null;

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

function splitSelected(articles) {
  const scheduled = [];
  const unscheduled = [];

  for (const article of articles) {
    if (article.scheduled_date) {
      scheduled.push(article);
    } else {
      unscheduled.push(article);
    }
  }

  scheduled.sort((a, b) => a.scheduled_date.localeCompare(b.scheduled_date));
  unscheduled.sort((a, b) => a.title.localeCompare(b.title, "zh-CN"));
  return { scheduled, unscheduled };
}

function renderItemList(container, items, scope) {
  container.replaceChildren();
  for (const item of items) {
    const node = itemTemplate.content.firstElementChild.cloneNode(true);
    node.dataset.filename = item.filename;
    node.dataset.scope = scope;
    node.querySelector(".article-item-title").textContent = item.title;

    const meta = node.querySelector(".article-item-meta");
    if (scope === "selected") {
      meta.textContent = item.scheduled_date ? `已分配时间：${item.scheduled_date}` : "待分配时间";
    } else if (scope === "briefs") {
      meta.textContent = "未读简报";
    } else {
      meta.textContent = "已读简报";
    }

    node.addEventListener("click", () => loadContent({ ...item, scope }));
    container.appendChild(node);
  }
}

function setActiveItem(filename, scope) {
  document.querySelectorAll(".article-item").forEach((button) => {
    button.classList.toggle(
      "active",
      button.dataset.filename === filename && button.dataset.scope === scope,
    );
  });
}

function setCurrentTab(tab) {
  currentTab = tab;
  selectedTab.classList.toggle("active", tab === "selected");
  briefsTab.classList.toggle("active", tab === "briefs");
  selectedPanels.classList.toggle("hidden", tab !== "selected");
  briefPanels.classList.toggle("hidden", tab !== "briefs");
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
      ? `<p style="${INLINE.infoSource}">原始来源：${formatInline(infoSource)}</p>`
      : "";
    parts.push(
      `<section class="wechat-info" style="${INLINE.info}"><div aria-hidden="true" style="${INLINE.infoGlow}"></div><h4 style="${INLINE.infoTitle}">${formatInline(
        infoTitle || "访谈信息",
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

async function loadSelected() {
  const articles = await fetchJson("/api/selected");
  const { scheduled, unscheduled } = splitSelected(articles);
  renderItemList(unscheduledList, unscheduled, "selected");
  renderItemList(scheduledList, scheduled, "selected");
  unscheduledCount.textContent = String(unscheduled.length);
  scheduledCount.textContent = String(scheduled.length);
  const first = unscheduled[0] || scheduled[0] || null;
  return first ? { ...first, scope: "selected" } : null;
}

async function loadBriefs() {
  const payload = await fetchJson("/api/briefs");
  renderItemList(briefUnreadList, payload.unread, "briefs");
  renderItemList(briefArchivedList, payload.archived, "archived");
  briefUnreadCount.textContent = String(payload.unread.length);
  briefArchivedCount.textContent = String(payload.archived.length);
  if (payload.unread[0]) {
    return { ...payload.unread[0], scope: "briefs" };
  }
  if (payload.archived[0]) {
    return { ...payload.archived[0], scope: "archived" };
  }
  return null;
}

async function refreshData(preferredTab = currentTab) {
  setStatus("加载内容中…");
  const [firstSelected, firstBrief] = await Promise.all([loadSelected(), loadBriefs()]);
  setCurrentTab(preferredTab);

  const candidate =
    pendingSelection ||
    currentItem ||
    (preferredTab === "selected" ? firstSelected : firstBrief);

  pendingSelection = null;
  if (candidate) {
    await loadContent(candidate);
  }
  setStatus("内容已刷新");
}

async function loadContent(item) {
  setStatus(`加载《${item.title}》中…`);
  const payload = await fetchJson(
    `/api/content?scope=${encodeURIComponent(item.scope)}&filename=${encodeURIComponent(item.filename)}`,
  );
  currentItem = item;
  articleTitle.textContent = item.title;
  if (item.scope === "selected") {
    articleMeta.textContent = item.scheduled_date ? `已分配时间：${item.scheduled_date}` : "待分配时间";
  } else if (item.scope === "briefs") {
    articleMeta.textContent = "未读简报";
  } else {
    articleMeta.textContent = "已读简报";
  }

  preview.classList.remove("empty-state");
  preview.innerHTML = renderMarkdown(payload.content);
  copyButton.disabled = false;
  promoteButton.classList.toggle("hidden", item.scope !== "briefs");
  scheduleButton.classList.toggle("hidden", item.scope !== "selected");
  scheduleButton.textContent = item.scheduled_date ? "修改发送时间" : "设置发送时间";
  scheduleDateInput.value = item.scheduled_date || "";
  setActiveItem(item.filename, item.scope);
  setStatus("内容已加载，可复制");
}

async function copyStyledContent() {
  if (!currentItem) return;
  const html = preview.innerHTML;
  const text = preview.innerText;

  if (window.ClipboardItem && navigator.clipboard?.write) {
    const item = new ClipboardItem({
      "text/html": new Blob([html], { type: "text/html" }),
      "text/plain": new Blob([text], { type: "text/plain" }),
    });
    await navigator.clipboard.write([item]);
  } else {
    const listener = (event) => {
      event.preventDefault();
      event.clipboardData.setData("text/html", html);
      event.clipboardData.setData("text/plain", text);
    };
    document.addEventListener("copy", listener, { once: true });
    document.execCommand("copy");
  }

  setStatus(`《${currentItem.title}》已复制，可直接粘贴到公众号编辑器`);
}

selectedTab.addEventListener("click", () => setCurrentTab("selected"));
briefsTab.addEventListener("click", () => setCurrentTab("briefs"));

copyButton.addEventListener("click", async () => {
  try {
    await copyStyledContent();
  } catch (error) {
    setStatus(`复制失败：${error.message}`);
  }
});

promoteButton.addEventListener("click", async () => {
  try {
    const title = currentItem?.title;
    await fetchJson("/api/promote-brief", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: currentItem.filename }),
    });
    currentItem = null;
    await refreshData("selected");
    setStatus(`《${title}》已移动到精选`);
  } catch (error) {
    setStatus(`移动失败：${error.message}`);
  }
});

scheduleButton.addEventListener("click", () => {
  if (!currentItem || currentItem.scope !== "selected") return;
  scheduleDateInput.value = currentItem.scheduled_date || "";
  if (typeof scheduleDateInput.showPicker === "function") {
    scheduleDateInput.showPicker();
    return;
  }
  scheduleDateInput.click();
});

scheduleDateInput.addEventListener("change", async () => {
  if (!currentItem || currentItem.scope !== "selected" || !scheduleDateInput.value) return;

  try {
    const payload = await fetchJson("/api/schedule-selected", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: currentItem.filename,
        scheduled_date: scheduleDateInput.value,
      }),
    });
    pendingSelection = { ...payload, scope: "selected" };
    currentItem = null;
    await refreshData("selected");
    setStatus(`《${payload.title}》已设置发送时间：${payload.scheduled_date}`);
  } catch (error) {
    setStatus(`设置发送时间失败：${error.message}`);
  }
});

refreshButton.addEventListener("click", async () => {
  try {
    currentItem = null;
    pendingSelection = null;
    await refreshData(currentTab);
  } catch (error) {
    setStatus(`刷新失败：${error.message}`);
  }
});

refreshData().catch((error) => {
  setStatus(`加载失败：${error.message}`);
});
