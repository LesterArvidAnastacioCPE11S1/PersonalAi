const els = {
  sidebar: document.getElementById("sidebar"),
  scrim: document.getElementById("scrim"),
  menuButton: document.getElementById("menu-button"),
  sidebarClose: document.getElementById("sidebar-close"),
  newChat: document.getElementById("new-chat"),
  logout: document.getElementById("logout-button"),
  loggedOff: document.getElementById("logged-off"),
  scenarioButton: document.getElementById("scenario-button"),
  personaTop: document.getElementById("persona-top"),
  composerPlus: document.getElementById("composer-plus"),
  plusMenu: document.getElementById("plus-menu"),
  plusFiles: document.getElementById("plus-files"),
  plusStyle: document.getElementById("plus-style"),
  plusStyleCurrent: document.getElementById("plus-style-current"),
  fileInput: document.getElementById("file-input"),
  composerAttachments: document.getElementById("composer-attachments"),
  chatList: document.getElementById("chat-list"),
  recycleCount: document.getElementById("recycle-count"),
  recycleList: document.getElementById("recycle-list"),
  topbarTitle: document.getElementById("topbar-title"),
  statusPill: document.getElementById("status-pill"),
  statusText: document.getElementById("status-text"),
  offlineBanner: document.getElementById("offline-banner"),
  offlineDetail: document.getElementById("offline-detail"),
  retryStatus: document.getElementById("retry-status"),
  messages: document.getElementById("messages"),
  emptyState: document.getElementById("empty-state"),
  messageList: document.getElementById("message-list"),
  composer: document.getElementById("composer"),
  setupBar: document.getElementById("setup-bar"),
  beginStory: document.getElementById("begin-story"),
  justChat: document.getElementById("just-chat"),
  input: document.getElementById("input"),
  sendButton: document.getElementById("send-button"),
  stopButton: document.getElementById("stop-button"),
  scenarioDialog: document.getElementById("scenario-dialog"),
  scenarioForm: document.getElementById("scenario-form"),
  scenarioClose: document.getElementById("scenario-close"),
  scenarioClear: document.getElementById("scenario-clear"),
  scenarioTitle: document.getElementById("scenario-title"),
  scenarioPremise: document.getElementById("scenario-premise"),
  scenarioSetting: document.getElementById("scenario-setting"),
  scenarioCharacters: document.getElementById("scenario-characters"),
  scenarioStyle: document.getElementById("scenario-style"),
  personaDialog: document.getElementById("persona-dialog"),
  personaForm: document.getElementById("persona-form"),
  personaClose: document.getElementById("persona-close"),
  personaCancel: document.getElementById("persona-cancel"),
  personaDelete: document.getElementById("persona-delete"),
  personaNew: document.getElementById("persona-new"),
  personaSelect: document.getElementById("persona-select"),
  personaName: document.getElementById("persona-name"),
  personaInstructions: document.getElementById("persona-instructions"),
  styleDialog: document.getElementById("style-dialog"),
  styleForm: document.getElementById("style-form"),
  styleClose: document.getElementById("style-close"),
  styleCancel: document.getElementById("style-cancel"),
  styleSave: document.getElementById("style-save"),
  styleOptions: document.getElementById("style-options"),
  memoryTop: document.getElementById("memory-top"),
  settingsTop: document.getElementById("settings-top"),
  memoryDrawer: document.getElementById("memory-drawer"),
  memoryScrim: document.getElementById("memory-scrim"),
  memoryClose: document.getElementById("memory-close"),
  memorySubtitle: document.getElementById("memory-subtitle"),
  memoryEmpty: document.getElementById("memory-empty"),
  memoryContent: document.getElementById("memory-content"),
  memorySummary: document.getElementById("memory-summary"),
  memoryCount: document.getElementById("memory-count"),
  approvalCount: document.getElementById("approval-count"),
  approvalHistory: document.getElementById("approval-history"),
  memoryExtract: document.getElementById("memory-extract"),
  loreList: document.getElementById("lore-list"),
  loreForm: document.getElementById("lore-form"),
  loreFormTitle: document.getElementById("lore-form-title"),
  loreCategory: document.getElementById("lore-category"),
  loreSubject: document.getElementById("lore-subject"),
  loreDetail: document.getElementById("lore-detail"),
  loreKeywords: document.getElementById("lore-keywords"),
  loreCancel: document.getElementById("lore-cancel"),
  loreSave: document.getElementById("lore-save"),
  settingsDialog: document.getElementById("settings-dialog"),
  settingsForm: document.getElementById("settings-form"),
  settingsClose: document.getElementById("settings-close"),
  settingsReload: document.getElementById("settings-reload"),
  settingsNoRefusals: document.getElementById("settings-no-refusals"),
  settingsCustom: document.getElementById("settings-custom"),
  settingsModel: document.getElementById("settings-model"),
  settingsBaseUrl: document.getElementById("settings-base-url"),
  settingsTemperature: document.getElementById("settings-temperature"),
  settingsMaxTokens: document.getElementById("settings-max-tokens"),
  settingsAutoExtract: document.getElementById("settings-auto-extract"),
  settingsExtractEvery: document.getElementById("settings-extract-every"),
  settingsVision: document.getElementById("settings-vision"),
  settingsVisionModel: document.getElementById("settings-vision-model"),
  settingsMobile: document.getElementById("settings-mobile"),
  settingsAccessCode: document.getElementById("settings-access-code"),
  settingsGenerateCode: document.getElementById("settings-generate-code"),
  settingsPhoneUrls: document.getElementById("settings-phone-urls"),
  settingsToolRoots: document.getElementById("settings-tool-roots"),
  settingsToolPath: document.getElementById("settings-tool-path"),
  settingsToolAdd: document.getElementById("settings-tool-add"),
  settingsDrives: document.getElementById("settings-drives"),
  artifactPanel: document.getElementById("artifact-panel"),
  artifactTitle: document.getElementById("artifact-title"),
  artifactSub: document.getElementById("artifact-sub"),
  artifactCode: document.getElementById("artifact-code"),
  artifactCopy: document.getElementById("artifact-copy"),
  artifactDownload: document.getElementById("artifact-download"),
  artifactClose: document.getElementById("artifact-close"),
  toast: document.getElementById("toast")
};

const state = {
  conversations: [],
  conversation: null,
  currentId: null,
  messages: [],
  pendingScenario: emptyScenario(),
  pendingStyle: "",
  personas: [],
  personaDefaultId: "",
  editingPersonaId: "",
  pendingPersonaId: "",
  styles: null,
  selectedStyle: "",
  editingId: null,
  streaming: false,
  controller: null,
  status: null,
  memory: null,
  memoryOpen: false,
  editingLoreId: null,
  settings: null,
  toolRoots: [],
  toolDrives: [],
  attachments: [],
  uploads: 0,
  plusOpen: false,
  queuedAction: null,
  painting: false
};

const MAX_FILES = 6;
let localFileId = 0;

const CATEGORY_LABELS = {
  character: "Characters",
  place: "Places",
  faction: "Factions",
  item: "Items",
  event: "Events",
  relationship: "Relationships",
  rule: "World rules",
  fact: "Facts"
};

let toastTimer = null;

function emptyScenario() {
  return {
    title: "",
    premise: "",
    setting: "",
    characters: "",
    style: ""
  };
}

function scenarioOf(conversation) {
  if (!conversation) {
    return emptyScenario();
  }

  return {
    title: conversation.title === "New chat" ? "" : conversation.title || "",
    premise: conversation.premise || "",
    setting: conversation.setting || "",
    characters: conversation.characters || "",
    style: conversation.style || ""
  };
}

function hasScenario(conversation) {
  if (!conversation) {
    return false;
  }

  return Boolean(
    conversation.premise ||
    conversation.setting ||
    conversation.characters ||
    conversation.style
  );
}

function styleOf(conversation) {
  return conversation ? conversation.narrative_style || "" : "";
}

function activeStyle() {
  return state.conversation
    ? styleOf(state.conversation)
    : state.pendingStyle;
}

function styleLabel(key) {
  const match = (state.styles || []).find(
    (item) => item.key === (key || "")
  );

  return match ? match.name : "Default";
}

function updateStyleLabel() {
  els.plusStyleCurrent.textContent = styleLabel(activeStyle());
}

async function api(path, options = {}) {
  const request = {
    method: options.method || "GET",
    headers: {}
  };

  if (options.body !== undefined) {
    request.headers["Content-Type"] = "application/json";
    request.body = JSON.stringify(options.body);
  }

  const response = await fetch(path, request);

  if (!response.ok) {
    let detail = response.statusText;

    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch (error) {
      detail = response.statusText || "Request failed.";
    }

    throw new Error(detail);
  }

  return response.json();
}

function toast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");

  clearTimeout(toastTimer);

  toastTimer = setTimeout(
    () => els.toast.classList.remove("show"),
    3200
  );
}

async function copyText(text) {
  const value = String(text || "");

  if (!value) {
    toast("Nothing to copy.");
    return;
  }

  try {
    await navigator.clipboard.writeText(value);
    toast("Copied.");
    return;
  } catch (clipboardError) {
  }

  const field = document.createElement("textarea");
  field.value = value;
  field.setAttribute("readonly", "");
  field.style.position = "fixed";
  field.style.top = "0";
  field.style.left = "0";
  field.style.opacity = "0";
  document.body.append(field);
  field.select();

  try {
    document.execCommand("copy");
    toast("Copied.");
  } catch (error) {
    toast("Could not copy.");
  } finally {
    field.remove();
  }
}

function escapeHtml(value) {
  return String(value).replace(
    /[&<>"']/g,
    (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    })[character]
  );
}

function formatBytes(size) {
  if (!Number.isFinite(size) || size <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  let value = size;
  let index = 0;

  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }

  const rounded = index === 0
    ? Math.round(value)
    : value >= 10
      ? Math.round(value)
      : value.toFixed(1);

  return `${rounded} ${units[index]}`;
}

function attachmentKindLabel(kind) {
  return {
    pdf: "PDF",
    docx: "DOCX",
    roblox: "ROBLOX",
    image: "Image",
    text: "Text"
  }[kind] || "File";
}

function fileIcon() {
  return `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
      stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/>
      <path d="M14 2v6h6"/>
    </svg>
  `;
}

function pendingAttachments() {
  return state.attachments.filter(
    (entry) => !entry.message_id
  );
}

const artifactStore = new Map();
const ARTIFACT_STORE_LIMIT = 300;
let activeArtifactKey = null;

function hashString(value) {
  let hash = 5381;

  for (let index = 0; index < value.length; index += 1) {
    hash = (
      ((hash << 5) + hash + value.charCodeAt(index)) >>> 0
    );
  }

  return `${hash.toString(36)}_${value.length.toString(36)}`;
}

function artifactLanguageLabel(language) {
  const map = {
    lua: "LUA",
    luau: "LUA",
    python: "PY",
    py: "PY",
    javascript: "JS",
    js: "JS",
    typescript: "TS",
    ts: "TS",
    html: "HTML",
    css: "CSS",
    json: "JSON",
    yaml: "YAML",
    bash: "SH",
    sh: "SH",
    shell: "SH",
    csharp: "C#",
    cs: "C#",
    java: "JAVA",
    cpp: "C++",
    sql: "SQL"
  };

  const key = String(language || "").toLowerCase();

  return map[key] || (key ? key.toUpperCase() : "CODE");
}

function artifactTitleFrom(code) {
  const firstLine = (code.split("\n", 1)[0] || "").trim();
  const comment = firstLine.match(/^(?:--|\/\/|#)\s*(.+)$/);

  if (comment) {
    const title = comment[1].trim();

    if (title && title.length <= 90) {
      return title;
    }
  }

  return "";
}

function registerArtifact(language, code) {
  const key = hashString(`${language || ""}\u0000${code}`);

  if (!artifactStore.has(key)) {
    if (artifactStore.size >= ARTIFACT_STORE_LIMIT) {
      artifactStore.delete(artifactStore.keys().next().value);
    }

    artifactStore.set(key, {
      code,
      language: artifactLanguageLabel(language),
      rawLanguage: String(language || "").toLowerCase(),
      title: artifactTitleFrom(code)
    });
  }

  return key;
}

function artifactCardHtml(key, meta) {
  const title = meta.title || "Code";
  const sub = `Code - ${meta.language}`;

  return `
    <div class="artifact-card" data-artifact="${key}" role="button" tabindex="0" title="Open in side panel">
      <span class="artifact-card-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m16 18 6-6-6-6"/><path d="m8 6-6 6 6 6"/></svg>
      </span>
      <span class="artifact-card-info">
        <span class="artifact-card-title">${escapeHtml(title)}</span>
        <span class="artifact-card-sub">${escapeHtml(sub)}</span>
      </span>
      <button type="button" class="artifact-card-copy" data-artifact-copy="${key}">Copy</button>
    </div>`;
}

function renderArtifactLines(code) {
  const maxLines = 6000;
  const lines = code.split("\n");
  const shown = lines.slice(0, maxLines);

  const rows = shown.map(
    (line, index) =>
      `<span class="line"><span class="line-num">${index + 1}</span><span class="line-text">${escapeHtml(line)}</span></span>`
  );

  if (lines.length > maxLines) {
    rows.push(
      `<span class="line artifact-line-note"><span class="line-text">[showing first ${maxLines} of ${lines.length} lines]</span></span>`
    );
  }

  return rows.join("");
}

function artifactFileName(meta) {
  const map = {
    lua: "lua",
    luau: "lua",
    python: "py",
    py: "py",
    javascript: "js",
    js: "js",
    typescript: "ts",
    ts: "ts",
    html: "html",
    css: "css",
    json: "json",
    yaml: "yaml",
    bash: "sh",
    sh: "sh",
    shell: "sh",
    csharp: "cs",
    cs: "cs",
    java: "java",
    cpp: "cpp",
    sql: "sql"
  };

  const base = (meta.title || "code")
    .replace(/\s*\([^)]*\)\s*/g, " ")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 60) || "code";

  return `${base}.${map[meta.rawLanguage] || "txt"}`;
}

function openArtifact(key) {
  const meta = artifactStore.get(key);

  if (!meta) {
    toast("That code block is no longer available.");
    return;
  }

  activeArtifactKey = key;

  els.artifactTitle.textContent = meta.title || "Code";
  els.artifactSub.textContent = `Code - ${meta.language}`;
  els.artifactCode.innerHTML = renderArtifactLines(meta.code);

  els.artifactPanel.classList.add("open");
  els.artifactPanel.setAttribute("aria-hidden", "false");
}

function closeArtifact() {
  activeArtifactKey = null;

  els.artifactPanel.classList.remove("open");
  els.artifactPanel.setAttribute("aria-hidden", "true");
}

function copyActiveArtifact() {
  if (!activeArtifactKey) {
    return;
  }

  const meta = artifactStore.get(activeArtifactKey);

  if (meta) {
    copyText(meta.code);
  }
}

function downloadActiveArtifact() {
  if (!activeArtifactKey) {
    return;
  }

  const meta = artifactStore.get(activeArtifactKey);

  if (!meta) {
    return;
  }

  const blob = new Blob([meta.code], {
    type: "text/plain;charset=utf-8"
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = artifactFileName(meta);
  link.click();

  URL.revokeObjectURL(url);
}

function messageAttachmentsFor(message) {
  if (Array.isArray(message.attachments)) {
    return message.attachments;
  }

  if (!message.id) {
    return [];
  }

  return state.attachments.filter(
    (entry) => entry.message_id === message.id
  );
}

function renderInline(value) {
  let output = escapeHtml(value);
  output = output.replace(
    /`([^`]+)`/g,
    "<code>$1</code>"
  );

  output = output.replace(
    /\*\*([^*]+)\*\*/g,
    "<strong>$1</strong>"
  );

  output = output.replace(
    /(^|[^*])\*([^*\n]+)\*/g,
    "$1<em>$2</em>"
  );

  return output;
}

function renderMarkdown(text) {
  const blocks = [];

  const source = String(text).replace(
    /```([\w-]*)\n?([\s\S]*?)```/g,
    (match, language, code) => {
      const clean = code.replace(/\n$/, "");
      const key = registerArtifact(language, clean);

      blocks.push(
        artifactCardHtml(key, artifactStore.get(key))
      );

      return `\n%%CODE${blocks.length - 1}%%\n`;
    }
  );

  const lines = source.split("\n");
  const output = [];

  let paragraph = [];
  let listType = null;
  let listItems = [];
  let quote = [];

  const flushParagraph = () => {
    if (!paragraph.length) {
      return;
    }

    output.push(
      `<p>${paragraph.map(renderInline).join("<br>")}</p>`
    );

    paragraph = [];
  };

  const flushList = () => {
    if (!listType) {
      return;
    }

    output.push(
      `<${listType}>${listItems
        .map((item) => `<li>${renderInline(item)}</li>`)
        .join("")}</${listType}>`
    );

    listType = null;
    listItems = [];
  };

  const flushQuote = () => {
    if (!quote.length) {
      return;
    }

    output.push(
      `<blockquote>${quote.map(renderInline).join("<br>")}</blockquote>`
    );

    quote = [];
  };

  const flushAll = () => {
    flushParagraph();
    flushList();
    flushQuote();
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    const codeMatch = line.match(/^%%CODE(\d+)%%$/);

    if (codeMatch) {
      flushAll();
      output.push(blocks[Number(codeMatch[1])]);
      continue;
    }

    if (!line.trim()) {
      flushParagraph();
      flushQuote();
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.*)$/);

    if (heading) {
      flushAll();
      const level = heading[1].length;
      output.push(
        `<h${level}>${renderInline(heading[2])}</h${level}>`
      );
      continue;
    }

    if (/^(-{3,}|\*{3,})$/.test(line.trim())) {
      flushAll();
      output.push("<hr>");
      continue;
    }

    const quoteLine = line.match(/^>\s?(.*)$/);

    if (quoteLine) {
      flushParagraph();
      flushList();
      quote.push(quoteLine[1]);
      continue;
    }

    const bullet = line.match(/^\s*[-*+]\s+(.*)$/);

    if (bullet) {
      flushParagraph();
      flushQuote();

      if (listType !== "ul") {
        flushList();
        listType = "ul";
      }

      listItems.push(bullet[1]);
      continue;
    }

    const ordered = line.match(/^\s*\d+[.)]\s+(.*)$/);

    if (ordered) {
      flushParagraph();
      flushQuote();

      if (listType !== "ol") {
        flushList();
        listType = "ol";
      }

      listItems.push(ordered[1]);
      continue;
    }

    flushList();
    flushQuote();
    paragraph.push(line);
  }

  flushAll();

  return output.join("");
}

function scrollToBottom(instant = false) {
  if (instant) {
    els.messages.style.scrollBehavior = "auto";
  }

  els.messages.scrollTop = els.messages.scrollHeight;

  if (instant) {
    els.messages.style.scrollBehavior = "";
  }
}

function isNearBottom() {
  return (
    els.messages.scrollHeight -
    els.messages.scrollTop -
    els.messages.clientHeight
  ) < 140;
}

function setMessagesVisible(visible) {
  els.messageList.classList.toggle("hidden", !visible);
  els.emptyState.classList.toggle("hidden", visible);
}

function resetCurrentConversation() {

  // The open conversation no longer exists (deleted or purged
  // from the recycle bin elsewhere). Reset to a fresh new chat
  // so uploads and messages stop failing with 404.

  state.currentId = null;
  state.conversation = null;
  state.messages = [];
  state.attachments = [];
  state.editingId = null;
  state.memory = null;

  history.replaceState(null, "", location.pathname);

  els.messageList.innerHTML = "";
  setMessagesVisible(false);
  updateHeader();
  renderSidebar();
  renderAttachments();
  updateSendState();
  setMemoryVisibility();
}

function conversationMissing(error) {
  return /not found/i.test(
    String((error && error.message) || "")
  );
}

function isSetup() {
  return Boolean(
    state.currentId
    && state.conversation
    && state.conversation.phase === "setup"
  );
}

function renderSetupBar() {
  els.setupBar.classList.toggle("hidden", !isSetup());
  els.beginStory.disabled = state.streaming || state.uploads > 0;
  els.justChat.disabled = state.streaming || state.uploads > 0;
}

function updateHeader() {
  const title = state.conversation
    ? state.conversation.title
    : "New chat";

  els.topbarTitle.textContent = title || "New chat";
  els.topbarTitle.title = title || "New chat";

  updatePersonaLabel();

  renderSetupBar();
}

function renderSidebar() {
  els.chatList.innerHTML = "";

  if (!state.conversations.length) {
    const empty = document.createElement("div");
    empty.className = "chat-list-empty";
    empty.textContent = "No conversations yet.";
    els.chatList.append(empty);
    return;
  }

  for (const conversation of state.conversations) {
    const item = document.createElement("div");

    item.className = "chat-item";

    if (conversation.id === state.currentId) {
      item.classList.add("active");
    }

    item.dataset.id = conversation.id;
    item.tabIndex = 0;
    item.setAttribute("role", "button");

    const title = document.createElement("div");
    title.className = "chat-item-title";
    title.textContent = conversation.title || "New chat";

    const preview = document.createElement("div");
    preview.className = "chat-item-preview";
    preview.textContent = conversation.preview
      || (conversation.attachment_count ? "Attachment" : "Empty conversation");

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "chat-item-delete";
    remove.dataset.id = conversation.id;
    remove.setAttribute("aria-label", "Delete conversation");
    remove.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 6h18"/>
        <path d="M8 6V4h8v2"/>
        <path d="M19 6l-1 14H6L5 6"/>
      </svg>
    `;

    item.append(title, preview, remove);
    els.chatList.append(item);
  }
}

function renderMessageAttachments(entries) {
  const wrap = document.createElement("div");
  wrap.className = "message-attachments";

  for (const entry of entries) {
    const link = document.createElement("a");
    const scene = entry.kind === "image"
      && /^scene-/.test(entry.filename || "");
    link.className = entry.kind !== "image"
      ? "message-attachment"
      : scene
        ? "message-attachment image scene"
        : "message-attachment image";
    link.href = entry.url;
    link.target = "_blank";
    link.rel = "noopener";
    link.title = entry.filename;

    if (entry.kind === "image") {
      const image = document.createElement("img");
      image.src = entry.url;
      image.alt = entry.filename;
      image.loading = "lazy";

      const caption = document.createElement("span");
      caption.textContent = entry.filename;

      link.append(image, caption);
    } else {
      const icon = document.createElement("span");
      icon.innerHTML = fileIcon();

      const name = document.createElement("span");
      name.className = "name";
      name.textContent = entry.filename;

      link.append(icon, name);
    }

    wrap.append(link);
  }

  return wrap;
}

function renderToolCalls(calls) {
  const wrap = document.createElement("div");
  wrap.className = "tool-calls";

  for (const call of calls) {
    const details = document.createElement("details");
    details.className = "tool-call"
      + (call.ok ? "" : " failed");

    const summary = document.createElement("summary");

    const label = document.createElement("span");
    label.className = "tool-call-name";
    label.textContent = String(call.tool || "tool").replace(/_/g, " ");

    const status = document.createElement("span");
    status.className = "tool-call-status";
    const seconds = Number(call.seconds || 0);
    status.textContent = (call.ok ? "done" : "failed")
      + (seconds ? ` · ${seconds.toFixed(2)}s` : "");

    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "tool-copy";
    copy.textContent = "Copy";
    copy.title = "Copy tool details";

    const side = document.createElement("span");
    side.className = "tool-call-side";
    side.append(status, copy);

    summary.append(label, side);

    const body = document.createElement("pre");
    body.className = "tool-call-body";

    const args = call.args && Object.keys(call.args).length
      ? JSON.stringify(call.args)
      : "";

    body.textContent = (args ? `${args}\n\n` : "")
      + (call.output || "(no output)");

    copy.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      copyText(body.textContent);
    });

    details.append(summary, body);
    wrap.append(details);
  }

  return wrap;
}

function approvalStatusText(status) {
  switch (status) {
    case "approved":
      return "done";
    case "failed":
      return "failed";
    case "denied":
      return "denied";
    default:
      return "waiting for you";
  }
}

function approvalClipboardText(approval) {
  const args = approval.args || {};
  const lines = [approval.summary || approval.tool || "Approval"];

  if (approval.risk === "exec" && args.command) {
    lines.push(`$ ${args.command}`);
  } else if (args.source) {
    lines.push(args.source);
    lines.push(`-> ${args.destination || ""}`);
  } else if (args.path) {
    lines.push(args.path);

    if (args.content) {
      lines.push("", args.content);
    }
  }

  if (approval.result) {
    lines.push("", approval.result);
  }

  return lines.join("\n");
}

function renderApprovals(approvals) {
  const wrap = document.createElement("div");
  wrap.className = "tool-calls approval-calls";

  for (const approval of approvals) {
    const card = document.createElement("div");
    card.className = `approval ${approval.status || "pending"}`;
    card.dataset.approval = String(approval.id);

    const head = document.createElement("div");
    head.className = "approval-head";

    const title = document.createElement("span");
    title.className = "approval-title";
    title.textContent = approval.risk === "exec"
      ? "Command approval"
      : approval.tool === "files_move"
        ? "File move approval"
        : approval.tool === "files_delete"
          ? "Delete approval"
          : "File write approval";

    const status = document.createElement("span");
    status.className = "approval-status";
    status.textContent = approvalStatusText(approval.status);

    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "approval-copy";
    copy.textContent = "Copy";
    copy.title = "Copy approval details";
    copy.addEventListener("click", () => {
      copyText(approvalClipboardText(approval));
    });

    const side = document.createElement("span");
    side.className = "approval-side";
    side.append(status, copy);

    head.append(title, side);

    const summary = document.createElement("div");
    summary.className = "approval-summary";
    summary.textContent = approval.summary || approval.tool;

    card.append(head, summary);

    if (approval.risk === "exec") {
      const command = document.createElement("pre");
      command.className = "approval-preview";
      command.textContent = `$ ${(approval.args || {}).command || ""}`;
      card.append(command);
    } else if (approval.args && approval.args.source) {
      const source = document.createElement("div");
      source.className = "approval-path";
      source.textContent = approval.args.source;
      card.append(source);

      const destination = document.createElement("div");
      destination.className = "approval-path";
      destination.textContent = `-> ${approval.args.destination || ""}`;
      card.append(destination);
    } else if (approval.args && approval.args.path) {
      const path = document.createElement("div");
      path.className = "approval-path";
      path.textContent = approval.args.path;
      card.append(path);

      const content = String(approval.args.content || "");

      if (content) {
        const preview = document.createElement("pre");
        preview.className = "approval-preview";
        preview.textContent = content.length > 800
          ? `${content.slice(0, 800)}\n...`
          : content;
        card.append(preview);
      } else if (approval.tool === "files_delete") {
        const note = document.createElement("div");
        note.className = "approval-note";
        note.textContent =
          "Sends the file or folder to the Windows Recycle Bin, where it "
          + "can be restored.";
        card.append(note);
      }
    }

    if ((approval.status || "pending") === "pending") {
      const actions = document.createElement("div");
      actions.className = "approval-actions";

      const approve = document.createElement("button");
      approve.type = "button";
      approve.className = "approval-button approve";
      approve.dataset.approve = String(approval.id);
      approve.textContent = "Approve";

      const deny = document.createElement("button");
      deny.type = "button";
      deny.className = "approval-button deny";
      deny.dataset.deny = String(approval.id);
      deny.textContent = "Deny";

      actions.append(approve, deny);
      card.append(actions);
    } else if (approval.status === "failed" && approval.result) {
      const result = document.createElement("pre");
      result.className = "approval-preview";
      result.textContent = approval.result;
      card.append(result);
    }

    wrap.append(card);
  }

  return wrap;
}

function applyApproval(card, approval) {
  if (!card || !approval) {
    return;
  }

  card.className = `approval ${approval.status || "pending"}`;

  const status = card.querySelector(".approval-status");

  if (status) {
    status.textContent = approvalStatusText(approval.status);
  }

  const actions = card.querySelector(".approval-actions");

  if (actions) {
    actions.remove();
  }
}

function attachApprovals(messages, approvals) {
  for (const approval of approvals) {
    let owner = messages.find(
      (message) => message.role === "assistant"
        && message.id != null
        && message.id > (approval.message_id || 0)
    );

    if (!owner) {
      owner = [...messages].reverse().find(
        (message) => message.role === "assistant"
      );
    }

    if (owner) {
      owner.approvals = owner.approvals || [];
      owner.approvals.push(approval);
    }
  }
}

async function decideApproval(card, button, decision) {
  if (state.streaming) {
    return;
  }

  const id = Number(button.dataset.approve || button.dataset.deny);
  const actions = card.querySelectorAll(".approval-button");
  actions.forEach((item) => {
    item.disabled = true;
  });

  if (decision === "deny") {
    try {
      const data = await api(`/api/tool-approvals/${id}/deny`, {
        method: "POST"
      });
      applyApproval(card, data.approval);
      loadRecycle();
    } catch (error) {
      actions.forEach((item) => {
        item.disabled = false;
      });
      toast(error.message);
    }

    return;
  }

  card.classList.add("running");

  const status = card.querySelector(".approval-status");

  if (status) {
    status.textContent = "running...";
  }

  const assistant = { role: "assistant", content: "" };
  const elements = appendMessage(assistant);

  await runStream(
    {},
    assistant,
    elements,
    `/api/tool-approvals/${id}/approve`
  );

  loadRecycle();
}

function copyAction(text) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "message-action";
  button.dataset.copyText = "";
  button.title = "Copy message";
  button.setAttribute("aria-label", "Copy message");
  button.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
      stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <rect x="9" y="9" width="12" height="12" rx="2"/>
      <path d="M5 15V5a2 2 0 0 1 2-2h8"/>
    </svg>
    <span>Copy</span>
  `;

  button.addEventListener("click", () => {
    copyText(typeof text === "function" ? text() : text);
  });

  return button;
}

function editAction(messageId) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "message-action";
  button.dataset.edit = messageId;
  button.title = "Edit message";
  button.setAttribute("aria-label", "Edit message");
  button.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
      stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 20h9"/>
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>
    </svg>
    <span>Edit</span>
  `;

  return button;
}

function paintAction(messageId) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "message-action";
  button.dataset.paint = messageId;
  button.title = "Paint this scene";
  button.setAttribute("aria-label", "Paint this scene");
  button.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
      stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 3a9 9 0 1 0 0 18h1.5a2.5 2.5 0 0 0 0-5H13a2 2 0 0 1 0-4h4a4 4 0 0 0 4-4c0-3-4-5-9-5Z"/>
      <circle cx="8" cy="9" r="1"/>
      <circle cx="7" cy="14" r="1"/>
      <circle cx="11" cy="17" r="1"/>
    </svg>
    <span>Paint</span>
  `;

  return button;
}

function attachToMessage(root, attachment) {
  const body = root.querySelector(".message-body");
  if (!body) {
    return;
  }

  let wrap = body.querySelector(".message-attachments");

  if (!wrap) {
    wrap = document.createElement("div");
    wrap.className = "message-attachments";

    const actions = body.querySelector(".message-actions");

    if (actions) {
      body.insertBefore(wrap, actions);
    } else {
      body.append(wrap);
    }
  }

  wrap.append(...renderMessageAttachments([attachment]).children);
}

async function paintScene(messageId) {
  if (state.painting || !state.currentId || messageId == null) {
    return;
  }

  state.painting = true;

  const root = els.messageList.querySelector(
    `.message[data-message-id="${messageId}"]`
  );
  const button = root ? root.querySelector("[data-paint]") : null;
  const label = button ? button.querySelector("span") : null;

  if (button) {
    button.disabled = true;
    button.classList.add("painting");
  }

  if (label) {
    label.textContent = "Painting...";
  }

  let note = null;

  if (root) {
    const body = root.querySelector(".message-body");
    const previous = body.querySelector(".paint-note");

    if (previous) {
      previous.remove();
    }

    note = document.createElement("div");
    note.className = "paint-note";
    note.textContent = "Painting the scene. This can take up to two minutes.";
    body.append(note);
  }

  try {
    const data = await api("/api/images/generate", {
      method: "POST",
      body: {
        conversation_id: state.currentId,
        message_id: messageId
      }
    });

    state.attachments.push(data.attachment);

    if (root) {
      attachToMessage(root, data.attachment);
    }

    const message = state.messages.find(
      (entry) => entry.id === messageId
    );

    if (message) {
      message.attachments = messageAttachmentsFor(message);
    }

    if (note) {
      note.remove();
    }

    toast("Scene painted.");
  } catch (error) {
    if (note) {
      note.className = "paint-note error";
      note.textContent = error.message || "Could not paint the scene.";
    }

    toast(error.message || "Could not paint the scene.");
  } finally {
    state.painting = false;

    if (button) {
      button.disabled = false;
      button.classList.remove("painting");
    }

    if (label) {
      label.textContent = "Paint";
    }
  }
}

function appendMessage(message, attachments = null) {
  const root = document.createElement("div");
  root.className = `message ${message.role}`;
  root.dataset.messageId =
    message.id != null ? String(message.id) : "";
  message.element = root;

  if (message.role === "user") {
    const entries = attachments || messageAttachmentsFor(message);
    const stack = document.createElement("div");
    stack.className = "user-stack";

    if (message.content) {
      const bubble = document.createElement("div");
      bubble.className = "bubble";
      bubble.textContent = message.content;
      stack.append(bubble);
    }

    if (entries.length) {
      stack.append(renderMessageAttachments(entries));
    }

    const actions = document.createElement("div");
    actions.className = "message-actions";

    if (message.content) {
      actions.append(copyAction(() => message.content));
    }

    if (message.id != null) {
      actions.append(editAction(message.id));
    }

    stack.append(actions);
    root.append(stack);
    els.messageList.append(root);
    return { root, textEl: null, errorEl: null };
  }

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "P";

  const body = document.createElement("div");
  body.className = "message-body";

  const name = document.createElement("div");
  name.className = "message-name";
  name.textContent = "PersonalAI";

  const text = document.createElement("div");
  text.className = "message-text";
  text.innerHTML = message.content
    ? renderMarkdown(message.content)
    : '<div class="typing"><span></span><span></span><span></span></div>';

  const error = document.createElement("div");
  error.className = "message-error hidden";

  body.append(name);

  if (message.tool_calls && message.tool_calls.length) {
    body.append(renderToolCalls(message.tool_calls));
  }

  if (message.approvals && message.approvals.length) {
    body.append(renderApprovals(message.approvals));
  }

  body.append(text, error);

  const entries = attachments || messageAttachmentsFor(message);

  if (entries.length) {
    body.append(renderMessageAttachments(entries));
  }

  if (message.id != null) {
    const actions = document.createElement("div");
    actions.className = "message-actions";

    if (message.content) {
      actions.append(copyAction(() => message.content));
    }

    actions.append(paintAction(message.id));
    body.append(actions);
  }

  root.append(avatar, body);
  els.messageList.append(root);

  return { root, textEl: text, errorEl: error };
}

function renderMessages() {
  els.messageList.innerHTML = "";

  for (const message of state.messages) {
    appendMessage(message);
  }

  setMessagesVisible(state.messages.length > 0);

  if (state.messages.length) {
    requestAnimationFrame(() => scrollToBottom(true));
  }
}

function beginEdit(messageId) {
  if (state.streaming || state.editingId !== null) {
    return;
  }

  const index = state.messages.findIndex(
    (item) => item.id === messageId && item.role === "user"
  );

  if (index === -1) {
    return;
  }

  const message = state.messages[index];
  const root = message.element;

  if (!root) {
    return;
  }

  const stack = root.querySelector(".user-stack");

  if (!stack) {
    return;
  }

  const bubble = stack.querySelector(".bubble");
  const actions = stack.querySelector(".message-actions");
  const later = state.messages.length - index - 1;

  const editor = document.createElement("div");
  editor.className = "message-editor";
  editor.dataset.editor = messageId;

  const area = document.createElement("textarea");
  area.className = "edit-input";
  area.value = message.content;
  area.rows = 2;

  const note = document.createElement("div");
  note.className = "edit-note";
  note.textContent = later
    ? `Saving removes ${later} later message${later === 1 ? "" : "s"} and regenerates the reply.`
    : "Saving regenerates the reply.";

  const buttons = document.createElement("div");
  buttons.className = "edit-actions";

  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.className = "ghost-button small";
  cancel.textContent = "Cancel";

  const save = document.createElement("button");
  save.type = "button";
  save.className = "primary-button small";
  save.textContent = "Save & regenerate";

  buttons.append(cancel, save);
  editor.append(area, note, buttons);

  if (bubble) {
    bubble.classList.add("editing-hidden");
  }

  if (actions) {
    actions.classList.add("editing-hidden");
  }

  stack.classList.add("editing");
  stack.append(editor);
  state.editingId = messageId;

  const resize = () => {
    area.style.height = "auto";
    area.style.height = `${Math.min(area.scrollHeight, 220)}px`;
  };

  area.addEventListener("input", resize);
  area.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      cancelEdit(messageId);
      return;
    }

    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.isComposing
    ) {
      event.preventDefault();
      saveEditedMessage(messageId, area.value);
    }
  });

  cancel.addEventListener("click", () => cancelEdit(messageId));
  save.addEventListener("click", () => {
    saveEditedMessage(messageId, area.value);
  });

  resize();
  area.focus();
  area.selectionStart = area.value.length;
  area.selectionEnd = area.value.length;
}

function cancelEdit(messageId) {
  const editor = els.messageList.querySelector(
    `[data-editor="${messageId}"]`
  );

  if (editor) {
    const stack = editor.parentElement;

    editor.remove();

    if (stack) {
      stack.classList.remove("editing");

      const bubble = stack.querySelector(".bubble");
      const actions = stack.querySelector(".message-actions");

      if (bubble) {
        bubble.classList.remove("editing-hidden");
      }

      if (actions) {
        actions.classList.remove("editing-hidden");
      }
    }
  }

  state.editingId = null;
}

async function saveEditedMessage(messageId, value) {
  if (state.streaming) {
    return;
  }

  const text = value.trim();
  const index = state.messages.findIndex(
    (item) => item.id === messageId && item.role === "user"
  );

  if (index === -1) {
    return;
  }

  if (!text) {
    toast("Message cannot be empty.");
    return;
  }

  if (text === state.messages[index].content) {
    cancelEdit(messageId);
    return;
  }

  state.messages = state.messages.slice(0, index + 1);
  state.messages[index] = {
    ...state.messages[index],
    content: text
  };
  state.editingId = null;

  renderMessages();
  setMessagesVisible(true);
  scrollToBottom();

  const assistant = { role: "assistant", content: "" };
  const elements = appendMessage(assistant);

  await runStream({
    conversation_id: state.currentId,
    message: text,
    edit_message_id: messageId,
    attachments: []
  }, assistant, elements);
}

async function loadConversations() {
  try {
    const data = await api("/api/conversations");
    state.conversations = data.conversations;
    renderSidebar();
  } catch (error) {
    toast(error.message);
  }
}

function recycleTime(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function recycleAction(kind, entry, label) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `icon-button recycle-${kind}`;
  button.dataset.action = kind;
  button.dataset.key = entry.key;
  button.dataset.name = entry.name;
  button.title = label;
  button.setAttribute("aria-label", label);
  button.innerHTML = kind === "restore"
    ? `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 12a9 9 0 1 0 3-6.7"/>
        <path d="M3 4v5h5"/>
      </svg>
    `
    : `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 6 6 18"/>
        <path d="m6 6 12 12"/>
      </svg>
    `;
  return button;
}

function renderRecycle(entries) {
  els.recycleList.innerHTML = "";
  els.recycleCount.textContent = entries.length
    ? String(entries.length)
    : "";

  if (!entries.length) {
    const empty = document.createElement("div");
    empty.className = "recycle-empty";
    empty.textContent = "The Recycle Bin is empty.";
    els.recycleList.append(empty);
    return;
  }

  for (const entry of entries) {
    const item = document.createElement("div");
    item.className = "recycle-item";
    item.title = entry.original || "Original location unknown";

    const copy = document.createElement("div");
    copy.className = "recycle-copy";

    const name = document.createElement("div");
    name.className = "recycle-name";
    name.textContent = entry.folder ? `${entry.name}/` : entry.name;

    const meta = document.createElement("div");
    meta.className = "recycle-meta";
    meta.textContent = [
      entry.folder ? "Folder" : "File",
      formatBytes(entry.size),
      recycleTime(entry.deleted_at)
    ].filter(Boolean).join(" · ");

    copy.append(name, meta);

    const actions = document.createElement("div");
    actions.className = "recycle-actions";
    actions.append(
      recycleAction("restore", entry, "Restore this item"),
      recycleAction("purge", entry, "Delete forever")
    );

    item.append(copy, actions);
    els.recycleList.append(item);
  }
}

async function loadRecycle() {
  try {
    const data = await api("/api/recycle");
    renderRecycle(Array.isArray(data.entries) ? data.entries : []);
  } catch (error) {
    els.recycleList.innerHTML = "";

    const failed = document.createElement("div");
    failed.className = "recycle-empty";
    failed.textContent = error.message;
    els.recycleList.append(failed);
  }
}

async function restoreRecycle(key, name) {
  try {
    await api("/api/recycle/restore", {
      method: "POST",
      body: { key }
    });
    toast(`Restored ${name}.`);
  } catch (error) {
    toast(error.message);
  }

  await loadConversations();
  loadRecycle();
}

async function purgeRecycle(key, name) {
  const message = `Permanently delete "${name}"? This cannot be undone.`;

  if (!window.confirm(message)) {
    return;
  }

  try {
    await api("/api/recycle/purge", {
      method: "POST",
      body: { key }
    });
    toast(`Deleted ${name} permanently.`);
  } catch (error) {
    toast(error.message);
  }

  await loadConversations();

  if (
    state.currentId
    && !state.conversations.some(
      (conversation) => conversation.id === state.currentId
    )
  ) {

    // The purged item was the open chat; recover to a new chat
    // so uploads and messages stop hitting a missing id.

    resetCurrentConversation();
    toast("The open chat was deleted. Starting a new chat.");
  }

  loadRecycle();
}

async function checkStatus() {

  // Watch for app updates: if the UI files on the server changed
  // since this window loaded, reload so old code never lingers.

  if (!state.streaming) {
    try {
      const versionData = await api("/api/ui-version");

      if (versionData && versionData.version) {
        const stored = sessionStorage.getItem("pai-ui-version");

        if (stored && stored !== versionData.version) {
          sessionStorage.setItem("pai-ui-version", versionData.version);
          toast("PersonalAI updated — reloading.");

          setTimeout(() => {
            location.reload();
          }, 800);

          return;
        }

        if (!stored) {
          sessionStorage.setItem("pai-ui-version", versionData.version);
        }
      }
    } catch (error) {

      // Older server without the endpoint — nothing to do.
    }
  }

  try {
    const data = await api("/api/status");
    state.status = data;

    els.statusPill.classList.toggle("online", data.online);
    els.statusPill.classList.toggle("offline", !data.online);
    els.statusPill.title = data.online
      ? data.base_url
      : data.error || data.base_url;

    els.statusText.textContent = data.online
      ? data.model || (data.available && data.available[0]) || "Ready"
      : "Model offline";

    els.offlineBanner.classList.toggle("hidden", data.online);

    if (!data.online) {
      els.offlineDetail.textContent =
        `${data.base_url} — ${data.error || "No response."}`;
    }
  } catch (error) {
    els.statusPill.classList.remove("online");
    els.statusPill.classList.add("offline");
    els.statusText.textContent = "App offline";
    els.offlineBanner.classList.remove("hidden");
    els.offlineDetail.textContent = error.message;
  }
}

function openSidebar() {
  els.sidebar.classList.add("open");
  els.scrim.classList.add("show");
}

function closeSidebar() {
  els.sidebar.classList.remove("open");
  els.scrim.classList.remove("show");
}

function startNewChat() {
  if (state.streaming) {
    return;
  }

  state.currentId = null;
  state.conversation = null;
  state.messages = [];
  state.pendingScenario = emptyScenario();
  state.pendingStyle = "";
  state.editingId = null;
  state.memory = null;
  state.attachments = [];
  setPlusMenu(false);
  updateStyleLabel();

  history.replaceState(null, "", location.pathname);

  els.messageList.innerHTML = "";
  setMessagesVisible(false);
  updateHeader();
  renderSidebar();
  closeSidebar();
  closeMemory();
  setMemoryVisibility();
  renderMemory();

  els.input.value = "";
  autoGrow();
  renderAttachments();
  updateSendState();
  els.input.focus();
}

async function openConversation(conversationId) {
  if (state.streaming) {
    return;
  }

  try {
    const data = await api(`/api/conversations/${conversationId}`);

    state.currentId = conversationId;
    state.conversation = data.conversation;
    state.pendingPersonaId = data.conversation.persona_id || "";
    state.messages = data.messages;
    attachApprovals(state.messages, data.approvals || []);
    state.attachments = data.attachments || [];
    state.pendingScenario = scenarioOf(data.conversation);
    state.pendingStyle = styleOf(data.conversation);
    state.editingId = null;
    state.memory = null;

    history.replaceState(null, "", `#${conversationId}`);

    updateHeader();
    updateStyleLabel();
    renderMessages();
    renderAttachments();
    updateSendState();
    renderSidebar();
    closeSidebar();
    setMemoryVisibility();

    if (state.memoryOpen) {
      await refreshMemory();
    }
  } catch (error) {

    if (conversationMissing(error)) {

      resetCurrentConversation();
      toast(
        "That chat no longer exists. Starting a new chat."
      );

      return;
    }

    toast(error.message);
  }
}

async function deleteConversation(conversationId) {
  if (state.streaming) {
    return;
  }

  if (!confirm("Delete this conversation? This cannot be undone.")) {
    return;
  }

  try {
    await api(`/api/conversations/${conversationId}`, {
      method: "DELETE"
    });

    state.conversations = state.conversations.filter(
      (conversation) => conversation.id !== conversationId
    );

    if (state.currentId === conversationId) {
      startNewChat();
    } else {
      renderSidebar();
    }

    toast("Conversation deleted.");
  } catch (error) {
    toast(error.message);
  }
}

function memoryEntries() {
  if (!state.memory || !Array.isArray(state.memory.lore)) {
    return [];
  }

  return state.memory.lore;
}

function setMemoryVisibility() {
  const active = Boolean(state.currentId);

  els.memoryEmpty.classList.toggle("hidden", active);
  els.memoryContent.classList.toggle("hidden", !active);
  els.memorySubtitle.textContent = active
    ? "Facts PersonalAI carries into every reply."
    : "Start or open a chat to build its memory.";
}

function openMemory() {
  state.memoryOpen = true;
  setMemoryVisibility();
  els.memoryDrawer.classList.add("open");
  els.memoryScrim.classList.add("show");

  if (state.currentId) {
    refreshMemory();
  } else {
    state.memory = null;
    renderMemory();
  }
}

function closeMemory() {
  state.memoryOpen = false;
  els.memoryDrawer.classList.remove("open");
  els.memoryScrim.classList.remove("show");
}

async function refreshMemory() {
  const conversationId = state.currentId;

  if (!conversationId) {
    state.memory = null;
    renderMemory();
    return;
  }

  try {
    const data = await api(
      `/api/conversations/${conversationId}/memory`
    );

    if (state.currentId !== conversationId) {
      return;
    }

    state.memory = data;
    renderMemory();
  } catch (error) {
    toast(error.message);
  }
}

function loreItem(entry) {
  const item = document.createElement("div");
  item.className = "lore-item";

  const copy = document.createElement("div");
  copy.className = "lore-copy";

  if (entry.subject) {
    const subject = document.createElement("div");
    subject.className = "lore-subject";
    subject.textContent = entry.subject;
    copy.append(subject);
  }

  const detail = document.createElement("div");
  detail.className = "lore-detail";
  detail.textContent = entry.detail || "";
  copy.append(detail);

  if (entry.keywords) {
    const keywords = document.createElement("div");
    keywords.className = "lore-keywords";
    keywords.textContent = entry.keywords;
    copy.append(keywords);
  }

  const actions = document.createElement("div");
  actions.className = "lore-actions";
  actions.innerHTML = `
    <button type="button" class="icon-button" data-action="edit"
      data-id="${entry.id}" aria-label="Edit memory entry">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 20h9"/>
        <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>
      </svg>
    </button>
    <button type="button" class="icon-button" data-action="delete"
      data-id="${entry.id}" aria-label="Delete memory entry">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 6h18"/>
        <path d="M8 6V4h8v2"/>
        <path d="M19 6l-1 14H6L5 6"/>
      </svg>
    </button>
  `;

  item.append(copy, actions);

  return item;
}

function renderApprovalHistory(approvals) {
  const items = Array.isArray(approvals)
    ? [...approvals].reverse()
    : [];

  els.approvalCount.textContent = `${items.length} ${
    items.length === 1 ? "action" : "actions"
  }`;
  els.approvalHistory.innerHTML = "";

  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "lore-empty";
    empty.textContent = "No tool actions in this chat yet.";
    els.approvalHistory.append(empty);
    return;
  }

  for (const approval of items) {
    const item = document.createElement("div");
    item.className = `history-item ${approval.status || "pending"}`;

    const copy = document.createElement("div");
    copy.className = "history-copy";

    const summary = document.createElement("div");
    summary.className = "history-summary";
    summary.textContent = approval.summary || approval.tool;
    copy.append(summary);

    if (approval.status === "failed" && approval.result) {
      const result = document.createElement("div");
      result.className = "history-result";
      result.textContent = approval.result;
      copy.append(result);
    }

    const status = document.createElement("span");
    status.className = "history-status";
    status.textContent = approvalStatusText(approval.status);

    item.append(copy, status);
    els.approvalHistory.append(item);
  }
}

function renderMemory() {
  const entries = memoryEntries();
  const summary = state.memory
    ? state.memory.summary || ""
    : "";

  els.memorySummary.textContent = summary
    || "No recap yet. PersonalAI writes one as the story grows.";

  els.memoryCount.textContent = `${entries.length} ${
    entries.length === 1 ? "entry" : "entries"
  }`;

  renderApprovalHistory(
    state.memory ? state.memory.approvals : []
  );

  const running = Boolean(
    state.memory && state.memory.running
  );

  els.memoryExtract.disabled = running || state.streaming;
  els.memoryExtract.textContent = running
    ? "Updating..."
    : "Update memory";

  els.loreList.innerHTML = "";

  if (!entries.length) {
    const empty = document.createElement("div");
    empty.className = "lore-empty";
    empty.textContent =
      "No facts saved yet. Add one below, or let automatic memory fill the library.";
    els.loreList.append(empty);
    return;
  }

  const groups = new Map();

  for (const entry of entries) {
    const category = entry.category || "fact";

    if (!groups.has(category)) {
      groups.set(category, []);
    }

    groups.get(category).push(entry);
  }

  const known = Object.keys(CATEGORY_LABELS);
  const order = known.concat(
    [...groups.keys()].filter(
      (category) => !known.includes(category)
    )
  );

  for (const category of order) {
    const items = groups.get(category);

    if (!items || !items.length) {
      continue;
    }

    const group = document.createElement("div");
    group.className = "lore-group";

    const title = document.createElement("div");
    title.className = "lore-group-title";
    title.textContent = CATEGORY_LABELS[category] || category;
    group.append(title);

    for (const entry of items) {
      group.append(loreItem(entry));
    }

    els.loreList.append(group);
  }
}

function resetLoreForm() {
  state.editingLoreId = null;
  els.loreCategory.value = "fact";
  els.loreSubject.value = "";
  els.loreDetail.value = "";
  els.loreKeywords.value = "";
  els.loreFormTitle.textContent = "Add memory";
  els.loreSave.textContent = "Add";
  els.loreCancel.classList.add("hidden");
}

function startLoreEdit(entry) {
  state.editingLoreId = entry.id;
  els.loreCategory.value = CATEGORY_LABELS[entry.category]
    ? entry.category
    : "fact";
  els.loreSubject.value = entry.subject || "";
  els.loreDetail.value = entry.detail || "";
  els.loreKeywords.value = entry.keywords || "";
  els.loreFormTitle.textContent = "Edit memory";
  els.loreSave.textContent = "Save changes";
  els.loreCancel.classList.remove("hidden");
  els.loreForm.scrollIntoView({
    behavior: "smooth",
    block: "nearest"
  });
  els.loreDetail.focus();
}

async function submitLore(event) {
  event.preventDefault();

  if (!state.currentId) {
    toast("Start a chat first.");
    return;
  }

  const values = {
    category: els.loreCategory.value,
    subject: els.loreSubject.value.trim(),
    detail: els.loreDetail.value.trim(),
    keywords: els.loreKeywords.value.trim()
  };

  if (!values.detail) {
    toast("Add a detail first.");
    return;
  }

  const editing = state.editingLoreId;

  els.loreSave.disabled = true;

  try {
    if (editing) {
      await api(`/api/lore/${editing}`, {
        method: "PATCH",
        body: values
      });
    } else {
      await api(
        `/api/conversations/${state.currentId}/lore`,
        {
          method: "POST",
          body: values
        }
      );
    }

    resetLoreForm();
    await refreshMemory();
    await loadConversations();
    toast(editing ? "Memory updated." : "Memory added.");
  } catch (error) {
    toast(error.message);
  } finally {
    els.loreSave.disabled = false;
  }
}

async function deleteLoreEntry(loreId) {
  if (!confirm("Delete this memory entry?")) {
    return;
  }

  try {
    await api(`/api/lore/${loreId}`, {
      method: "DELETE"
    });

    if (state.editingLoreId === loreId) {
      resetLoreForm();
    }

    await refreshMemory();
    await loadConversations();
    toast("Memory entry deleted.");
  } catch (error) {
    toast(error.message);
  }
}

async function updateMemory() {
  if (!state.currentId || state.streaming) {
    return;
  }

  els.memoryExtract.disabled = true;
  els.memoryExtract.textContent = "Updating...";

  try {
    const data = await api(
      `/api/conversations/${state.currentId}/memory/extract`,
      { method: "POST" }
    );

    state.memory = data;
    toast(data.message || "Memory updated.");
    await loadConversations();
  } catch (error) {
    toast(error.message);
  } finally {
    await refreshMemory();
  }
}

function sameToolPath(left, right) {
  const clean = (value) => String(value || "")
    .trim()
    .replace(/\//g, "\\")
    .replace(/\\+$/, "")
    .toLowerCase();

  return clean(left) === clean(right);
}

function renderToolRoots() {
  els.settingsToolRoots.innerHTML = "";

  if (!state.toolRoots.length) {
    const empty = document.createElement("div");
    empty.className = "tool-root-empty";
    empty.textContent = "No allowed folders. Add at least one.";
    els.settingsToolRoots.append(empty);
    return;
  }

  for (const root of state.toolRoots) {
    const row = document.createElement("div");
    row.className = "tool-root";

    const path = document.createElement("span");
    path.className = "tool-root-path";
    path.textContent = root;
    path.title = root;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "icon-button tool-root-remove";
    remove.dataset.root = root;
    remove.title = "Remove folder";
    remove.setAttribute("aria-label", "Remove folder");
    remove.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 6 6 18"/>
        <path d="m6 6 12 12"/>
      </svg>
    `;

    row.append(path, remove);
    els.settingsToolRoots.append(row);
  }
}

function renderDrives() {
  els.settingsDrives.innerHTML = "";

  if (!state.toolDrives.length) {
    return;
  }

  const label = document.createElement("span");
  label.className = "drive-label";
  label.textContent = "Disks:";
  els.settingsDrives.append(label);

  for (const drive of state.toolDrives) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "drive-chip";
    button.dataset.drive = drive;

    const added = state.toolRoots.some(
      (root) => sameToolPath(root, drive)
    );

    button.disabled = added;
    button.textContent = drive;
    button.title = added ? "Already allowed" : `Allow ${drive}`;
    els.settingsDrives.append(button);
  }
}

function addToolRoot(value) {
  const text = String(value || "").trim();

  if (!text) {
    return;
  }

  if (state.toolRoots.some((root) => sameToolPath(root, text))) {
    toast("That folder is already allowed.");
    return;
  }

  state.toolRoots.push(text);
  els.settingsToolPath.value = "";
  renderToolRoots();
  renderDrives();
}

function removeToolRoot(root) {
  state.toolRoots = state.toolRoots.filter(
    (item) => item !== root
  );
  renderToolRoots();
  renderDrives();
}

function fillSettings(data) {
  const available = new Set(data.available || []);

  if (data.model) {
    available.add(data.model);
  }

  els.settingsModel.innerHTML = "";

  const auto = document.createElement("option");
  auto.value = "";
  auto.textContent = "Auto (first available)";
  els.settingsModel.append(auto);

  for (const id of [...available].sort(
    (left, right) => left.localeCompare(right)
  )) {
    const option = document.createElement("option");
    option.value = id;
    option.textContent = id;
    els.settingsModel.append(option);
  }

  els.settingsModel.value = data.model || "";
  els.settingsBaseUrl.value = data.base_url || "";

  const availableIds = [...available].sort(
    (left, right) => left.localeCompare(right)
  );

  els.settingsVisionModel.replaceChildren();

  for (const id of availableIds) {
    const option = document.createElement("option");
    option.value = id;
    option.textContent = id;
    els.settingsVisionModel.append(option);
  }

  if (data.vision_model && !available.has(data.vision_model)) {
    const option = document.createElement("option");
    option.value = data.vision_model;
    option.textContent = data.vision_model;
    els.settingsVisionModel.append(option);
  }

  els.settingsVisionModel.value = data.vision_model || "";
  els.settingsTemperature.value = data.temperature;
  els.settingsMaxTokens.value = data.max_tokens;
  els.settingsNoRefusals.checked = Boolean(data.no_refusals);
  els.settingsCustom.value = data.custom_instructions || "";
  els.settingsAutoExtract.checked = Boolean(data.auto_extract);
  els.settingsExtractEvery.value = data.extract_every;
  els.settingsVision.checked = Boolean(data.vision);
  els.settingsMobile.checked = Boolean(data.mobile_access);

  const accessCode = data.access_token || "";

  els.settingsAccessCode.value = accessCode.length === 10
    ? `${accessCode.slice(0, 5)}-${accessCode.slice(5)}`
    : accessCode;

  const urls = data.phone_urls || [];

  els.settingsPhoneUrls.textContent = urls.length
    ? `Open this on your phone: ${urls.join("  |  ")}`
    : "No LAN address found. Connect the PC to Wi-Fi or Ethernet.";

  state.toolRoots = Array.isArray(data.tool_roots)
    ? [...data.tool_roots]
    : [];
  state.toolDrives = Array.isArray(data.tool_drives)
    ? [...data.tool_drives]
    : [];

  renderToolRoots();
  renderDrives();
  syncMemoryControls();
}

function syncMemoryControls() {
  const enabled = els.settingsAutoExtract.checked;

  els.settingsExtractEvery.disabled = !enabled;
  els.settingsExtractEvery
    .closest(".field")
    .classList.toggle("muted", !enabled);
}

async function loadSettings() {
  const data = await api("/api/settings");
  state.settings = data;
  fillSettings(data);
  return data;
}

async function openSettings() {
  try {
    await loadSettings();
    els.settingsDialog.showModal();
  } catch (error) {
    toast(error.message);
  }
}

async function saveSettings(event) {
  event.preventDefault();

  const previous = state.settings || {};
  const temperatureText = els.settingsTemperature.value.trim();
  const temperature = temperatureText === ""
    ? NaN
    : Number(temperatureText);
  const maxTokens = Number(els.settingsMaxTokens.value);
  const every = Number(els.settingsExtractEvery.value);

  const pendingRoot = els.settingsToolPath.value.trim();

  if (pendingRoot) {
    addToolRoot(pendingRoot);
  }

  if (!state.toolRoots.length) {
    toast("Add at least one allowed folder.");
    return;
  }

  const body = {
    model: els.settingsModel.value,
    base_url: els.settingsBaseUrl.value.trim(),
    temperature: Number.isFinite(temperature)
      ? temperature
      : previous.temperature,
    max_tokens: (
      Number.isFinite(maxTokens) && maxTokens > 0
    )
      ? maxTokens
      : previous.max_tokens,
    no_refusals: els.settingsNoRefusals.checked,
    custom_instructions: els.settingsCustom.value,
    auto_extract: els.settingsAutoExtract.checked,
    extract_every: (
      Number.isFinite(every) && every > 0
    )
      ? every
      : previous.extract_every,
    vision: els.settingsVision.checked,
    vision_model: els.settingsVisionModel.value,
    mobile_access: els.settingsMobile.checked,
    access_token: els.settingsAccessCode.value,
    tool_roots: state.toolRoots
  };

  try {
    const data = await api("/api/settings", {
      method: "PATCH",
      body
    });

    state.settings = data;
    fillSettings(data);
    toast("Settings saved.");
    els.settingsDialog.close();
    checkStatus();
  } catch (error) {
    toast(error.message);
  }
}

function autoGrow() {
  els.input.style.height = "auto";
  els.input.style.height =
    `${Math.min(els.input.scrollHeight, 200)}px`;
}

function personaById(personaId) {
  return state.personas.find(
    (persona) => persona.id === personaId
  ) || null;
}

function activePersonaId() {
  if (state.currentId && state.conversation) {
    const selected = state.conversation.persona_id;

    return selected && personaById(selected)
      ? selected
      : state.personaDefaultId;
  }

  return state.pendingPersonaId
    && personaById(state.pendingPersonaId)
    ? state.pendingPersonaId
    : state.personaDefaultId;
}

function updatePersonaLabel() {
  const persona = personaById(activePersonaId());

  els.personaTop.textContent = persona
    ? persona.name
    : "Persona";
  els.personaTop.title = persona
    ? `Persona: ${persona.name}`
    : "Persona";
}

async function loadPersonas() {
  const data = await api("/api/personas");

  state.personas = data.personas || [];
  state.personaDefaultId = data.default_id
    || (state.personas[0] ? state.personas[0].id : "");

  updatePersonaLabel();

  return state.personas;
}

function renderPersonaOptions(selectedId) {
  els.personaSelect.innerHTML = "";

  if (!state.personas.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No personas";
    els.personaSelect.append(option);
    els.personaSelect.value = "";
    return;
  }

  for (const persona of state.personas) {
    const option = document.createElement("option");
    option.value = persona.id;
    option.textContent = persona.name;
    els.personaSelect.append(option);
  }

  els.personaSelect.value = selectedId
    || state.personas[0].id;
}

function fillPersonaEditor(persona) {
  els.personaName.value = persona ? persona.name : "";
  els.personaInstructions.value = persona
    ? persona.instructions
    : "";
  els.personaDelete.disabled = !persona;
}

async function applyPersona(personaId) {
  if (state.currentId) {
    const data = await api(
      `/api/conversations/${state.currentId}`,
      {
        method: "PATCH",
        body: { persona_id: personaId || "" }
      }
    );

    state.conversation = data.conversation;
    state.pendingPersonaId = data.conversation.persona_id || "";

    await loadConversations();
  } else {
    state.pendingPersonaId = personaId || "";
  }

  updatePersonaLabel();
}

async function openPersona() {
  try {
    if (!state.personas.length) {
      await loadPersonas();
    }

    const selectedId = activePersonaId()
      || (state.personas[0] ? state.personas[0].id : "");

    state.editingPersonaId = selectedId;
    renderPersonaOptions(selectedId);
    fillPersonaEditor(personaById(selectedId));
    els.personaDialog.showModal();
  } catch (error) {
    toast(error.message);
  }
}

function closePersona() {
  els.personaDialog.close();
}

function newPersona() {
  state.editingPersonaId = "";
  els.personaSelect.value = "";
  els.personaName.value = "";
  els.personaInstructions.value = "";
  els.personaDelete.disabled = true;
  els.personaName.focus();
}

async function savePersona(event) {
  event.preventDefault();

  const name = els.personaName.value.trim();
  const instructions = els.personaInstructions.value;
  const save = els.personaForm.querySelector(
    'button[type="submit"]'
  );

  save.disabled = true;

  try {
    let persona;

    if (state.editingPersonaId) {
      const data = await api(
        `/api/personas/${state.editingPersonaId}`,
        {
          method: "PATCH",
          body: { name, instructions }
        }
      );

      persona = data.persona;
    } else {
      const data = await api("/api/personas", {
        method: "POST",
        body: { name, instructions }
      });

      persona = data.persona;
    }

    state.editingPersonaId = persona.id;

    await loadPersonas();
    renderPersonaOptions(persona.id);
    fillPersonaEditor(personaById(persona.id));
    await applyPersona(persona.id);

    toast("Persona saved.");
  } catch (error) {
    toast(error.message);
  } finally {
    save.disabled = false;
  }
}

async function removePersona() {
  const persona = personaById(state.editingPersonaId);

  if (!persona) {
    return;
  }

  if (!confirm(`Delete persona "${persona.name}"?`)) {
    return;
  }

  try {
    await api(`/api/personas/${persona.id}`, {
      method: "DELETE"
    });

    await loadPersonas();

    const next = activePersonaId()
      || state.personaDefaultId
      || (state.personas[0] ? state.personas[0].id : "");

    state.editingPersonaId = next;
    renderPersonaOptions(next);
    fillPersonaEditor(personaById(next));

    if (next) {
      await applyPersona(next);
    }

    toast("Persona deleted.");
  } catch (error) {
    toast(error.message);
  }
}

function openScenario() {
  const source = state.conversation
    ? scenarioOf(state.conversation)
    : state.pendingScenario;

  els.scenarioTitle.value = source.title;
  els.scenarioPremise.value = source.premise;
  els.scenarioSetting.value = source.setting;
  els.scenarioCharacters.value = source.characters;
  els.scenarioStyle.value = source.style;

  els.scenarioDialog.showModal();
}

function closeScenario() {
  els.scenarioDialog.close();
}

async function saveScenario(event) {
  event.preventDefault();

  const values = {
    title: els.scenarioTitle.value,
    premise: els.scenarioPremise.value,
    setting: els.scenarioSetting.value,
    characters: els.scenarioCharacters.value,
    style: els.scenarioStyle.value
  };

  if (state.currentId) {
    try {
      const data = await api(
        `/api/conversations/${state.currentId}`,
        {
          method: "PATCH",
          body: values
        }
      );

      state.conversation = data.conversation;
      state.pendingScenario = scenarioOf(data.conversation);

      updateHeader();
      await loadConversations();
      closeScenario();
      toast("Scenario saved.");
    } catch (error) {
      toast(error.message);
    }

    return;
  }

  state.pendingScenario = values;

  closeScenario();
  toast("Scenario saved for this chat.");
  els.input.focus();
}

async function loadStyles() {
  if (state.styles) {
    return state.styles;
  }

  const data = await api("/api/styles");
  state.styles = data.styles || [];
  updateStyleLabel();

  return state.styles;
}

function renderStyleOptions(selected) {
  els.styleOptions.innerHTML = "";

  for (const style of state.styles || []) {
    const label = document.createElement("label");
    label.className = "style-option";

    if (style.key === selected) {
      label.classList.add("selected");
    }

    const input = document.createElement("input");
    input.type = "radio";
    input.name = "narrative-style";
    input.value = style.key;
    input.className = "style-radio";
    input.checked = style.key === selected;

    const body = document.createElement("div");
    body.className = "style-option-body";

    const head = document.createElement("div");
    head.className = "style-option-head";

    const name = document.createElement("span");
    name.className = "style-option-name";
    name.textContent = style.name;

    const check = document.createElement("span");
    check.className = "style-option-check";
    check.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="m20 6-11 11-5-5"/>
      </svg>
    `;

    const desc = document.createElement("p");
    desc.className = "style-option-desc";
    desc.textContent = style.description;

    head.append(name, check);
    body.append(head, desc);
    label.append(input, body);
    els.styleOptions.append(label);
  }
}

function selectStyle(key) {
  state.selectedStyle = key;

  for (const option of els.styleOptions.children) {
    const input = option.querySelector("input");

    if (!input) {
      continue;
    }

    const active = input.value === key;
    input.checked = active;
    option.classList.toggle("selected", active);
  }
}

async function openStyleDialog() {
  setPlusMenu(false);

  try {
    await loadStyles();
  } catch (error) {
    toast(error.message);
    return;
  }

  state.selectedStyle = activeStyle();
  renderStyleOptions(state.selectedStyle);
  els.styleDialog.showModal();
}

function closeStyleDialog() {
  els.styleDialog.close();
}

async function saveStyle(event) {
  event.preventDefault();

  const style = state.selectedStyle || "";

  if (!state.currentId) {
    state.pendingStyle = style;
    updateStyleLabel();
    closeStyleDialog();
    toast("Storytelling style set.");
    return;
  }

  els.styleSave.disabled = true;

  try {
    const data = await api(`/api/conversations/${state.currentId}`, {
      method: "PATCH",
      body: { narrative_style: style }
    });

    state.conversation = data.conversation;
    state.pendingStyle = styleOf(data.conversation);
    updateStyleLabel();
    closeStyleDialog();
    await loadConversations();
    toast("Storytelling style updated.");
  } catch (error) {
    toast(error.message);
  } finally {
    els.styleSave.disabled = false;
  }
}

function parseEvent(chunk) {
  let event = "message";
  let data = "";

  for (const line of chunk.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      data += line.slice(5).trim();
    }
  }

  try {
    return {
      event,
      data: data ? JSON.parse(data) : {}
    };
  } catch (error) {
    return { event, data: {} };
  }
}

function adoptMessageId(saved) {
  if (saved.role !== "user" || saved.id == null) {
    return;
  }

  for (let index = state.messages.length - 1; index >= 0; index -= 1) {
    const message = state.messages[index];

    if (message.role !== "user" || message.id != null) {
      continue;
    }

    message.id = saved.id;

    const root = message.element;

    if (root) {
      root.dataset.messageId = String(saved.id);

      let actions = root.querySelector(".message-actions");

      if (!actions) {
        actions = document.createElement("div");
        actions.className = "message-actions";
        root.querySelector(".user-stack").append(actions);
      }

      if (!actions.querySelector("[data-copy-text]")) {
        actions.prepend(copyAction(() => message.content));
      }

      if (!actions.querySelector("[data-edit]")) {
        actions.append(editAction(saved.id));
      }
    }

    return;
  }
}

function adoptAssistant(saved, assistant, elements) {
  if (!saved || saved.role !== "assistant" || saved.id == null) {
    return;
  }

  assistant.id = saved.id;

  const body = elements.root.querySelector(".message-body");

  if (!body) {
    return;
  }

  elements.root.dataset.messageId = String(saved.id);

  let actions = body.querySelector(".message-actions");

  if (!actions) {
    actions = document.createElement("div");
    actions.className = "message-actions";
    body.append(actions);
  }

  if (!actions.querySelector("[data-copy-text]")) {
    actions.prepend(copyAction(() => assistant.content));
  }

  if (!actions.querySelector("[data-paint]")) {
    actions.append(paintAction(saved.id));
  }
}

function performAction(action) {
  if (!action || !action.name) {
    return;
  }

  if (action.name === "open_settings") {
    openSettings();
  } else if (action.name === "open_memory") {
    openMemory();
  } else if (action.name === "open_scenario") {
    openScenario();
  } else if (action.name === "open_styles") {
    openStyleDialog();
  } else if (action.name === "open_sidebar") {
    openSidebar();
  } else if (action.name === "new_chat") {
    state.queuedAction = "new_chat";
  } else if (action.name === "generate_image") {
    state.queuedAction = "generate_image";
  }
}

function handleEvent(payload, assistant, elements) {
  if (payload.event === "meta") {
    state.conversation = payload.data.conversation;

    if (payload.data.message) {
      adoptMessageId(payload.data.message);
    }

    if (payload.data.action) {
      performAction(payload.data.action);
    }

    if (payload.data.approval) {
      const card = document.querySelector(
        `.approval[data-approval="${payload.data.approval.id}"]`
      );
      applyApproval(card, payload.data.approval);
    }

    if (
      Array.isArray(payload.data.tool_approvals)
      && payload.data.tool_approvals.length
      && elements.textEl
    ) {
      assistant.approvals = payload.data.tool_approvals;

      const body = elements.textEl.parentElement;

      if (body) {
        body.insertBefore(
          renderApprovals(payload.data.tool_approvals),
          elements.textEl
        );

        if (isNearBottom()) {
          scrollToBottom();
        }
      }
    }

    if (
      Array.isArray(payload.data.tool_calls)
      && payload.data.tool_calls.length
      && elements.textEl
    ) {
      assistant.tool_calls = payload.data.tool_calls;

      const body = elements.textEl.parentElement;

      if (body) {
        body.insertBefore(
          renderToolCalls(payload.data.tool_calls),
          elements.textEl
        );

        if (isNearBottom()) {
          scrollToBottom();
        }
      }
    }

    updateStyleLabel();
    updateHeader();
    return;
  }

  if (payload.event === "delta") {
    const follow = isNearBottom();

    assistant.content += payload.data.text || "";

    elements.textEl.innerHTML = renderMarkdown(
      assistant.content
    );

    elements.root.classList.add("streaming");

    if (follow) {
      scrollToBottom();
    }

    return;
  }

  if (payload.event === "error") {
    elements.errorEl.textContent = payload.data.message;
    elements.errorEl.classList.remove("hidden");
    return;
  }

  if (payload.event === "done") {
    state.conversation = payload.data.conversation;

    if (payload.data.message) {
      adoptAssistant(payload.data.message, assistant, elements);
    }

    updateHeader();

    if (state.memoryOpen) {
      refreshMemory();

      setTimeout(() => {
        if (state.memoryOpen) {
          refreshMemory();
        }
      }, 6000);
    }
  }
}

function setStreaming(streaming) {
  state.streaming = streaming;
  els.sendButton.classList.toggle("hidden", streaming);
  els.stopButton.classList.toggle("hidden", !streaming);
  els.input.disabled = streaming;

  if (state.memoryOpen) {
    renderMemory();
  }

  updateSendState();
}

function setPlusMenu(open) {
  state.plusOpen = open;
  els.plusMenu.classList.toggle("hidden", !open);
  els.composerPlus.setAttribute(
    "aria-expanded",
    open ? "true" : "false"
  );
}

async function ensureConversation() {
  if (state.currentId) {
    return state.conversation;
  }

  const payloads = [
    {
      narrative_style: state.pendingStyle,
      persona_id: activePersonaId() || ""
    },
    {
      narrative_style: state.pendingStyle,
      persona_id: ""
    },
    {
      narrative_style: "",
      persona_id: ""
    }
  ];

  let data = null;
  let lastError = null;

  for (const payload of payloads) {

    try {
      data = await api("/api/conversations", {
        method: "POST",
        body: {
          ...state.pendingScenario,
          ...payload
        }
      });

      break;
    } catch (error) {
      lastError = error;
    }
  }

  if (!data) {
    throw lastError;
  }

  state.currentId = data.conversation.id;
  state.conversation = data.conversation;
  state.pendingScenario = scenarioOf(data.conversation);
  state.pendingStyle = styleOf(data.conversation);
  state.pendingPersonaId = data.conversation.persona_id || "";

  history.replaceState(null, "", `#${state.currentId}`);
  updateHeader();
  updateStyleLabel();
  await loadConversations();

  return state.conversation;
}

function renderAttachments() {
  const entries = pendingAttachments();

  els.composerAttachments.innerHTML = "";
  els.composerAttachments.classList.toggle(
    "hidden",
    entries.length === 0
  );

  for (const entry of entries) {
    const chip = document.createElement("div");
    chip.className = entry.uploading
      ? "attachment-chip uploading"
      : "attachment-chip";

    const thumb = document.createElement("div");
    thumb.className = "attachment-thumb";

    if (entry.uploading) {
      const spinner = document.createElement("div");
      spinner.className = "spinner";
      thumb.append(spinner);
    } else if (entry.kind === "image" && entry.url) {
      const image = document.createElement("img");
      image.src = entry.url;
      image.alt = entry.filename;
      thumb.append(image);
    } else {
      thumb.innerHTML = fileIcon();
    }

    const info = document.createElement("div");
    info.className = "attachment-info";

    const name = document.createElement("span");
    name.className = "attachment-name";
    name.textContent = entry.filename;
    name.title = entry.filename;

    const meta = document.createElement("span");
    meta.className = "attachment-meta";

    if (entry.uploading) {
      meta.textContent = "Uploading...";
    } else {
      const parts = [
        attachmentKindLabel(entry.kind),
        formatBytes(entry.size)
      ];

      if (entry.vision_needed) {
        parts.push("vision off");
      }

      meta.textContent = parts.join(" · ");
    }

    info.append(name, meta);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "attachment-remove";
    remove.dataset.remove = entry.id;
    remove.title = "Remove";
    remove.setAttribute("aria-label", "Remove attachment");
    remove.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 6 6 18"/>
        <path d="m6 6 12 12"/>
      </svg>
    `;

    chip.append(thumb, info, remove);
    els.composerAttachments.append(chip);
  }
}

function updateSendState() {
  const hasText = els.input.value.trim().length > 0;
  const ready = pendingAttachments().some(
    (entry) => !entry.uploading
  );

  els.sendButton.disabled = (
    state.streaming
    || state.uploads > 0
    || (!hasText && !ready)
  );

  renderSetupBar();
}

async function removeAttachment(attachmentId) {
  const entry = state.attachments.find(
    (item) => item.id === attachmentId
  );

  if (!entry) {
    return;
  }

  if (entry.uploading) {
    state.attachments = state.attachments.filter(
      (item) => item !== entry
    );

    if (entry.controller) {
      entry.controller.abort();
    }

    renderAttachments();
    updateSendState();
    return;
  }

  try {
    await api(`/api/attachments/${attachmentId}`, {
      method: "DELETE"
    });

    state.attachments = state.attachments.filter(
      (item) => item.id !== attachmentId
    );

    renderAttachments();
    updateSendState();
  } catch (error) {
    toast(error.message);
  }
}

async function uploadFile(file) {
  const conversationId = state.currentId;

  if (!conversationId) {
    return;
  }

  localFileId += 1;

  const placeholder = {
    id: `local-${localFileId}`,
    filename: file.name,
    kind: file.type.startsWith("image/") ? "image" : "text",
    size: file.size,
    uploading: true,
    controller: new AbortController()
  };

  state.attachments.push(placeholder);
  state.uploads += 1;

  renderAttachments();
  updateSendState();

  try {
    const body = new FormData();
    body.append("file", file);

    let response = await fetch(
      `/api/conversations/${conversationId}/attachments`,
      {
        method: "POST",
        body,
        signal: placeholder.controller.signal
      }
    );

    if (
      response.status === 404
      && state.currentId
      && conversationId !== state.currentId
    ) {

      // The open chat is stale (deleted elsewhere); retry
      // against the fresh conversation.

      response = await fetch(
        `/api/conversations/${state.currentId}/attachments`,
        {
          method: "POST",
          body,
          signal: placeholder.controller.signal
        }
      );
    }

    if (!response.ok) {
      let detail = response.statusText;

      try {
        const payload = await response.json();
        detail = payload.detail || detail;
      } catch (error) {
        detail = response.statusText || "Upload failed.";
      }

      if (
        response.status === 404
        && /not found/i.test(String(detail))
      ) {
        resetCurrentConversation();

        // Re-register the placeholder for the fresh chat and
        // upload the same file again.

        state.attachments.push(placeholder);
        renderAttachments();
        updateSendState();

        await ensureConversation();

        const retry = await fetch(
          `/api/conversations/${state.currentId}/attachments`,
          {
            method: "POST",
            body,
            signal: placeholder.controller.signal
          }
        );

        if (retry.ok) {
          const retryData = await retry.json();
          const index = state.attachments.indexOf(placeholder);

          if (index !== -1) {
            state.attachments[index] = retryData.attachment;
          }

          if (retryData.warning) {
            toast(retryData.warning);
          }

          return;
        }
      }

      throw new Error(detail);
    }

    const data = await response.json();
    const index = state.attachments.indexOf(placeholder);

    if (index === -1) {
      return;
    }

    state.attachments[index] = data.attachment;

    if (data.warning) {
      toast(data.warning);
    }
  } catch (error) {
    if (error.name === "AbortError") {
      return;
    }

    state.attachments = state.attachments.filter(
      (item) => item !== placeholder
    );

    toast(error.message);
  } finally {
    state.uploads = Math.max(0, state.uploads - 1);
    renderAttachments();
    updateSendState();
  }
}

async function uploadFiles(fileList) {
  const files = Array.from(fileList || []);

  if (!files.length || state.streaming) {
    return;
  }

  const pending = pendingAttachments().length;

  if (pending + files.length > MAX_FILES) {
    toast(`You can attach up to ${MAX_FILES} files.`);
    return;
  }

  try {
    await ensureConversation();
  } catch (error) {
    toast(error.message);
    return;
  }

  for (const file of files) {
    await uploadFile(file);
  }
}

async function beginStory() {
  if (state.streaming || state.uploads > 0) {
    return;
  }

  try {
    await ensureConversation();
  } catch (error) {
    toast(error.message);
    return;
  }

  try {
    const data = await api(
      `/api/conversations/${state.currentId}/phase`,
      {
        method: "POST",
        body: { phase: "story" }
      }
    );

    state.conversation = data.conversation;
    renderSetupBar();
  } catch (error) {
    toast(error.message);
    return;
  }

  await sendMessage("Begin the story.", {
    attachments: false
  });
}

async function justChat() {
  if (state.streaming || state.uploads > 0) {
    return;
  }

  try {
    await ensureConversation();
  } catch (error) {
    toast(error.message);
    return;
  }

  try {
    const data = await api(
      `/api/conversations/${state.currentId}/phase`,
      {
        method: "POST",
        body: { phase: "chat" }
      }
    );

    state.conversation = data.conversation;
    renderSetupBar();
  } catch (error) {
    toast(error.message);
    return;
  }

  await sendMessage("Let's just chat.", {
    attachments: false
  });
}

async function sendMessage(override = null, options = {}) {
  const message = (
    override === null ? els.input.value : override
  ).trim();
  const entries = (
    options.attachments === false
      ? []
      : pendingAttachments()
  ).filter((entry) => !entry.uploading);

  if (state.streaming || state.uploads > 0) {
    return;
  }

  if (!message && !entries.length) {
    return;
  }

  try {
    await ensureConversation();
  } catch (error) {
    toast(error.message);
    return;
  }

  const userMessage = {
    role: "user",
    content: message,
    attachments: entries
  };

  state.messages.push(userMessage);
  appendMessage(userMessage, entries);
  setMessagesVisible(true);

  state.attachments = state.attachments.filter(
    (entry) => !entries.includes(entry)
  );

  renderAttachments();
  updateSendState();

  if (override === null) {
    els.input.value = "";
    autoGrow();
  }

  scrollToBottom();

  const assistant = { role: "assistant", content: "" };
  const elements = appendMessage(assistant);

  await runStream({
    conversation_id: state.currentId,
    message,
    attachments: entries.map((entry) => entry.id)
  }, assistant, elements);

  if (entries.length) {
    toast(
      `${entries.length} file(s) sent to the model.`
    );
  }
}

async function runStream(body, assistant, elements, url = "/api/chat/stream") {
  setStreaming(true);
  state.controller = new AbortController();

  let aborted = false;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body),
      signal: state.controller.signal
    });

    if (!response.ok || !response.body) {
      let detail = response.statusText;

      try {
        const payload = await response.json();
        detail = payload.detail || detail;
      } catch (error) {
        detail = response.statusText || "Request failed.";
      }

      if (
        response.status === 404
        && conversationMissing({ message: detail })
      ) {

        // The open chat was deleted elsewhere. Recover instead
        // of leaving every later send failing with 404.

        resetCurrentConversation();
        detail =
          "This chat was deleted. A new chat has been started — "
          "please send your message again.";
      }

      throw new Error(detail);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      let boundary = buffer.indexOf("\n\n");

      while (boundary !== -1) {
        const chunk = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        handleEvent(parseEvent(chunk), assistant, elements);
        boundary = buffer.indexOf("\n\n");
      }
    }

    if (assistant.content) {
      state.messages.push(assistant);
    }
  } catch (error) {
    if (error.name === "AbortError") {
      aborted = true;

      if (assistant.content) {
        state.messages.push(assistant);
      }

      toast("Generation stopped.");
    } else {
      elements.errorEl.textContent = error.message;
      elements.errorEl.classList.remove("hidden");

      if (assistant.content) {
        state.messages.push(assistant);
      }
    }
  } finally {
    elements.root.classList.remove("streaming");
    setStreaming(false);
    state.controller = null;

    if (!assistant.content) {
      elements.textEl.innerHTML = "";

      if (aborted) {
        elements.root.remove();
      } else if (elements.errorEl.classList.contains("hidden")) {
        elements.errorEl.textContent =
          "The model returned no text. Check the server console.";
        elements.errorEl.classList.remove("hidden");
      }
    }

    await loadConversations();
    updateHeader();

    if (state.queuedAction === "new_chat") {
      state.queuedAction = null;
      startNewChat();
    } else if (state.queuedAction === "generate_image") {
      state.queuedAction = null;

      if (assistant.id != null) {
        await paintScene(assistant.id);
      }
    }
  }
}

async function logOff() {

  if (!window.confirm("Log off and stop PersonalAI?")) {
    return;
  }

  try {

    const response = await fetch("/api/shutdown", { method: "POST" });

    if (!response.ok) {
      toast("Could not stop PersonalAI.");
      return;
    }

  } catch (error) {
  }

  els.loggedOff.classList.remove("hidden");
}

els.newChat.addEventListener("click", startNewChat);
els.logout.addEventListener("click", logOff);

els.artifactClose.addEventListener("click", closeArtifact);
els.artifactCopy.addEventListener("click", copyActiveArtifact);
els.artifactDownload.addEventListener("click", downloadActiveArtifact);

document.addEventListener("keydown", (event) => {
  if (
    event.key === "Escape"
    && els.artifactPanel.classList.contains("open")
  ) {
    closeArtifact();
  }
});

els.messageList.addEventListener("click", (event) => {
  const artifactCopy = event.target.closest("[data-artifact-copy]");

  if (artifactCopy) {
    const meta = artifactStore.get(
      artifactCopy.dataset.artifactCopy
    );

    if (meta) {
      copyText(meta.code);
    }

    return;
  }

  const artifactCard = event.target.closest("[data-artifact]");

  if (artifactCard) {
    openArtifact(artifactCard.dataset.artifact);
    return;
  }

  const code = event.target.closest("[data-copy-code]");

  if (code) {
    const block = code.closest(".code-block");
    const source = block ? block.querySelector("code") : null;
    copyText(source ? source.textContent : "");
    return;
  }

  const approve = event.target.closest("[data-approve]");

  if (approve) {
    decideApproval(approve.closest(".approval"), approve, "approve");
    return;
  }

  const deny = event.target.closest("[data-deny]");

  if (deny) {
    decideApproval(deny.closest(".approval"), deny, "deny");
    return;
  }

  const button = event.target.closest("[data-edit]");

  if (button) {
    beginEdit(Number(button.dataset.edit));
    return;
  }

  const paint = event.target.closest("[data-paint]");

  if (paint) {
    paintScene(Number(paint.dataset.paint));
  }
});

els.scenarioButton.addEventListener("click", openScenario);
els.personaTop.addEventListener("click", openPersona);
els.personaClose.addEventListener("click", closePersona);
els.personaCancel.addEventListener("click", closePersona);
els.personaForm.addEventListener("submit", savePersona);
els.personaNew.addEventListener("click", newPersona);
els.personaDelete.addEventListener("click", removePersona);
els.personaSelect.addEventListener("change", () => {
  const persona = personaById(els.personaSelect.value);

  state.editingPersonaId = persona ? persona.id : "";
  fillPersonaEditor(persona);

  if (persona) {
    applyPersona(persona.id).catch((error) => {
      toast(error.message);
    });
  }
});
els.personaDialog.addEventListener("click", (event) => {
  if (event.target === els.personaDialog) {
    closePersona();
  }
});
els.plusStyle.addEventListener("click", openStyleDialog);
els.styleClose.addEventListener("click", closeStyleDialog);
els.styleCancel.addEventListener("click", closeStyleDialog);
els.styleForm.addEventListener("submit", saveStyle);

els.styleOptions.addEventListener("change", (event) => {
  const input = event.target.closest("input");

  if (input) {
    selectStyle(input.value);
  }
});

els.styleDialog.addEventListener("click", (event) => {
  if (event.target === els.styleDialog) {
    closeStyleDialog();
  }
});
els.scenarioClose.addEventListener("click", closeScenario);
els.scenarioForm.addEventListener("submit", saveScenario);

els.scenarioClear.addEventListener("click", () => {
  els.scenarioTitle.value = "";
  els.scenarioPremise.value = "";
  els.scenarioSetting.value = "";
  els.scenarioCharacters.value = "";
  els.scenarioStyle.value = "";
});

els.memoryTop.addEventListener("click", openMemory);
els.memoryClose.addEventListener("click", closeMemory);
els.memoryScrim.addEventListener("click", closeMemory);
els.memoryExtract.addEventListener("click", updateMemory);
els.loreForm.addEventListener("submit", submitLore);
els.loreCancel.addEventListener("click", resetLoreForm);

els.loreList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");

  if (!button) {
    return;
  }

  const loreId = Number(button.dataset.id);
  const entry = memoryEntries().find(
    (item) => item.id === loreId
  );

  if (!entry) {
    return;
  }

  if (button.dataset.action === "edit") {
    startLoreEdit(entry);
  } else if (button.dataset.action === "delete") {
    deleteLoreEntry(loreId);
  }
});

els.settingsTop.addEventListener("click", openSettings);
els.settingsForm.addEventListener("submit", saveSettings);
els.settingsAutoExtract.addEventListener(
  "change",
  syncMemoryControls
);

els.settingsClose.addEventListener("click", () => {
  els.settingsDialog.close();
});

els.settingsGenerateCode.addEventListener("click", async () => {
  try {
    const data = await api("/api/settings/mobile-token", {
      method: "POST"
    });

    state.settings = data;
    fillSettings(data);
    toast("New access code generated.");
  } catch (error) {
    toast(error.message);
  }
});

els.settingsReload.addEventListener("click", async () => {
  try {
    await loadSettings();
    toast("Settings reloaded.");
  } catch (error) {
    toast(error.message);
  }
});

els.settingsToolAdd.addEventListener("click", () => {
  addToolRoot(els.settingsToolPath.value);
});

els.settingsToolPath.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    addToolRoot(els.settingsToolPath.value);
  }
});

els.settingsToolRoots.addEventListener("click", (event) => {
  const button = event.target.closest(".tool-root-remove");

  if (button) {
    removeToolRoot(button.dataset.root);
  }
});

els.settingsDrives.addEventListener("click", (event) => {
  const button = event.target.closest(".drive-chip");

  if (button && !button.disabled) {
    addToolRoot(button.dataset.drive);
  }
});

els.settingsDialog.addEventListener("click", (event) => {
  if (event.target === els.settingsDialog) {
    els.settingsDialog.close();
  }
});

els.chatList.addEventListener("click", (event) => {
  const remove = event.target.closest(".chat-item-delete");

  if (remove) {
    event.stopPropagation();
    deleteConversation(remove.dataset.id);
    return;
  }

  const item = event.target.closest(".chat-item");

  if (item) {
    openConversation(item.dataset.id);
  }
});

els.recycleList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");

  if (!button || button.disabled) {
    return;
  }

  if (button.dataset.action === "restore") {
    restoreRecycle(button.dataset.key, button.dataset.name);
  } else if (button.dataset.action === "purge") {
    purgeRecycle(button.dataset.key, button.dataset.name);
  }
});

els.chatList.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") {
    return;
  }

  const item = event.target.closest(".chat-item");

  if (item) {
    event.preventDefault();
    openConversation(item.dataset.id);
  }});

els.emptyState.addEventListener("click", (event) => {
  const suggestion = event.target.closest(".suggestion");

  if (!suggestion) {
    return;
  }

  els.input.value = suggestion.dataset.prompt;
  autoGrow();
  els.input.focus();
});

els.composer.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage();
});

els.composerPlus.addEventListener("click", (event) => {
  event.stopPropagation();
  setPlusMenu(!state.plusOpen);
});

els.beginStory.addEventListener("click", beginStory);
els.justChat.addEventListener("click", justChat);

els.plusFiles.addEventListener("click", () => {
  setPlusMenu(false);
  els.fileInput.click();
});

els.fileInput.addEventListener("change", async () => {
  const files = els.fileInput.files;
  els.fileInput.value = "";
  await uploadFiles(files);
});

els.composerAttachments.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-remove]");

  if (button) {
    removeAttachment(button.dataset.remove);
  }
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".composer-plus-wrap")) {
    setPlusMenu(false);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.plusOpen) {
    setPlusMenu(false);
  }
});

els.input.addEventListener("input", () => {
  autoGrow();
  updateSendState();
});

els.input.addEventListener("keydown", (event) => {
  if (
    event.key === "Enter" &&
    !event.shiftKey &&
    !event.isComposing
  ) {
    event.preventDefault();
    sendMessage();
  }
});

els.stopButton.addEventListener("click", () => {
  if (state.controller) {
    state.controller.abort();
  }
});

els.menuButton.addEventListener("click", openSidebar);
els.sidebarClose.addEventListener("click", closeSidebar);
els.scrim.addEventListener("click", closeSidebar);

els.retryStatus.addEventListener("click", () => {
  checkStatus();
  toast("Checking model server.");
});

els.scenarioDialog.addEventListener("click", (event) => {
  if (event.target === els.scenarioDialog) {
    closeScenario();
  }
});

window.addEventListener("focus", checkStatus);

window.addEventListener("hashchange", () => {
  const conversationId = location.hash.slice(1);

  if (conversationId && conversationId !== state.currentId) {
    openConversation(conversationId);
  }
});

setMemoryVisibility();
renderMemory();

checkStatus();
loadConversations();
loadRecycle();
loadPersonas().catch(() => {});
loadStyles().catch(() => {});

const initialConversation = location.hash.slice(1);

if (initialConversation) {
  openConversation(initialConversation);
} else {
  startNewChat();
}

setInterval(checkStatus, 20000);

setInterval(() => {
  if (state.memoryOpen && state.currentId && !state.streaming) {
    refreshMemory();
  }
}, 9000);
