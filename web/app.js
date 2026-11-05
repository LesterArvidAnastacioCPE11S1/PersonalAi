const els = {
  sidebar: document.getElementById("sidebar"),
  scrim: document.getElementById("scrim"),
  menuButton: document.getElementById("menu-button"),
  sidebarClose: document.getElementById("sidebar-close"),
  newChat: document.getElementById("new-chat"),
  scenarioButton: document.getElementById("scenario-button"),
  scenarioTop: document.getElementById("scenario-top"),
  composerPlus: document.getElementById("composer-plus"),
  plusMenu: document.getElementById("plus-menu"),
  plusFiles: document.getElementById("plus-files"),
  plusScenario: document.getElementById("plus-scenario"),
  fileInput: document.getElementById("file-input"),
  composerAttachments: document.getElementById("composer-attachments"),
  chatList: document.getElementById("chat-list"),
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
  settingsMobile: document.getElementById("settings-mobile"),
  settingsAccessCode: document.getElementById("settings-access-code"),
  settingsGenerateCode: document.getElementById("settings-generate-code"),
  settingsPhoneUrls: document.getElementById("settings-phone-urls"),
  toast: document.getElementById("toast")
};

const state = {
  conversations: [],
  conversation: null,
  currentId: null,
  messages: [],
  pendingScenario: emptyScenario(),
  streaming: false,
  controller: null,
  status: null,
  memory: null,
  memoryOpen: false,
  editingLoreId: null,
  settings: null,
  attachments: [],
  uploads: 0,
  plusOpen: false
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
      blocks.push(
        `<pre><code>${escapeHtml(code.replace(/\n$/, ""))}</code></pre>`
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
      flushAll();
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
}

function updateHeader() {
  const title = state.conversation
    ? state.conversation.title
    : "New chat";

  els.topbarTitle.textContent = title || "New chat";
  els.topbarTitle.title = title || "New chat";

  els.scenarioTop.textContent = hasScenario(state.conversation)
    ? "Scenario set"
    : "Scenario";

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
    link.className = entry.kind === "image"
      ? "message-attachment image"
      : "message-attachment";
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

function appendMessage(message, attachments = null) {
  const root = document.createElement("div");
  root.className = `message ${message.role}`;

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

  body.append(name, text, error);
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

async function loadConversations() {
  try {
    const data = await api("/api/conversations");
    state.conversations = data.conversations;
    renderSidebar();
  } catch (error) {
    toast(error.message);
  }
}

async function checkStatus() {
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
  state.memory = null;
  state.attachments = [];
  setPlusMenu(false);

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
    state.messages = data.messages;
    state.attachments = data.attachments || [];
    state.pendingScenario = scenarioOf(data.conversation);
    state.memory = null;

    history.replaceState(null, "", `#${conversationId}`);

    updateHeader();
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
    mobile_access: els.settingsMobile.checked,
    access_token: els.settingsAccessCode.value
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

function handleEvent(payload, assistant, elements) {
  if (payload.event === "meta") {
    state.conversation = payload.data.conversation;
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

  const data = await api("/api/conversations", {
    method: "POST",
    body: state.pendingScenario
  });

  state.currentId = data.conversation.id;
  state.conversation = data.conversation;
  state.pendingScenario = scenarioOf(data.conversation);

  history.replaceState(null, "", `#${state.currentId}`);
  updateHeader();
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

    const response = await fetch(
      `/api/conversations/${conversationId}/attachments`,
      {
        method: "POST",
        body,
        signal: placeholder.controller.signal
      }
    );

    if (!response.ok) {
      let detail = response.statusText;

      try {
        const payload = await response.json();
        detail = payload.detail || detail;
      } catch (error) {
        detail = response.statusText || "Upload failed.";
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

  setStreaming(true);
  state.controller = new AbortController();

  let aborted = false;

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        conversation_id: state.currentId,
        message,
        attachments: entries.map((entry) => entry.id)
      }),
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
  }
}

els.newChat.addEventListener("click", startNewChat);

els.scenarioButton.addEventListener("click", openScenario);
els.scenarioTop.addEventListener("click", openScenario);
els.plusScenario.addEventListener("click", () => {
  setPlusMenu(false);
  openScenario();
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

els.chatList.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") {
    return;
  }

  const item = event.target.closest(".chat-item");

  if (item) {
    event.preventDefault();
    openConversation(item.dataset.id);
  }
});

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
