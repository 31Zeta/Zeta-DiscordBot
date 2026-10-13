"use strict";

/* ====================== 基础工具 ====================== */
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

const ICON_PATHS = {
  play: "M8 5.14v13.72a1 1 0 0 0 1.52.85l10.6-6.86a1 1 0 0 0 0-1.7L9.52 4.29A1 1 0 0 0 8 5.14z",
  pause: "M7 4h3.5v16H7zM13.5 4H17v16h-3.5z",
  next: "M5 5.27v13.46a.8.8 0 0 0 1.22.68L15 13.5V19h2V5h-2v5.5L6.22 4.59A.8.8 0 0 0 5 5.27z",
  prev: "M19 5.27v13.46a.8.8 0 0 1-1.22.68L9 13.5V19H7V5h2v5.5l8.78-5.91A.8.8 0 0 1 19 5.27z",
  plus: "M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6z",
  heart: "M12 20.3l-1.3-1.2C5.9 14.7 3 12.1 3 8.9 3 6.3 5 4.3 7.6 4.3c1.5 0 2.9.7 3.9 1.8a5.2 5.2 0 0 1 3.9-1.8C18 4.3 20 6.3 20 8.9c0 3.2-2.9 5.8-7.7 10.2z",
  trash: "M9 3h6l1 2h4v2H4V5h4zM6 8h12l-1 13H7z",
  download: "M11 4h2v8.2l3.3-3.3 1.4 1.4L12 16l-5.7-5.7 1.4-1.4L11 12.2zM5 18h14v2H5z",
  up: "M12 5l7 7-1.4 1.4-4.6-4.6V19h-2V8.8l-4.6 4.6L5 12z",
  drag: "M8 6h2v2H8zm6 0h2v2h-2zM8 11h2v2H8zm6 0h2v2h-2zM8 16h2v2H8zm6 0h2v2h-2z",
  close: "M6.4 5 12 10.6 17.6 5 19 6.4 13.4 12 19 17.6 17.6 19 12 13.4 6.4 19 5 17.6 10.6 12 5 6.4z",
};

function icon(name) {
  return `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${ICON_PATHS[name]}"/></svg>`;
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[ch]));
}

function fmtTime(seconds) {
  seconds = Math.max(0, Math.floor(Number(seconds) || 0));
  const h = Math.floor(seconds / 3600), m = Math.floor(seconds % 3600 / 60), s = seconds % 60;
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
}

function fmtBytes(bytes) {
  if (bytes == null) return "—";
  const units = ["B", "KiB", "MiB", "GiB", "TiB"];
  let value = Number(bytes), unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit++; }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function fmtUptime(seconds) {
  seconds = Math.floor(seconds || 0);
  const d = Math.floor(seconds / 86400), h = Math.floor(seconds % 86400 / 3600), m = Math.floor(seconds % 3600 / 60);
  if (d > 0) return `${d}${t("unit.d")} ${h}${t("unit.h")}`;
  if (h > 0) return `${h}${t("unit.h")} ${m}${t("unit.m")}`;
  return `${m}${t("unit.m")}`;
}

function sourceTag(source) {
  const names = {youtube: "YouTube", bilibili: "Bilibili", netease: t("src.netease"), qq: t("src.qq"), kugou: t("src.kugou"), kuwo: t("src.kuwo"), migu: t("src.migu")};
  const cls = ["youtube", "bilibili", "netease", "qq"].includes(source) ? source : "";
  return `<span class="tag ${cls}">${esc(names[source] || source || "?")}</span>`;
}

/* ====================== 多语言 ====================== */
const I18N = {
  zh: {
    "nav.dashboard": "监控", "nav.player": "播放", "nav.search": "搜索", "nav.library": "音频库", "nav.favorites": "收藏夹", "nav.logs": "日志", "logout": "退出",
    "dashboard.title": "运行状态", "dashboard.trend": "趋势（最近1小时）", "dashboard.system": "系统资源", "dashboard.library": "音频库缓存", "dashboard.sources": "音源状态",
    "dashboard.downloads": "下载任务", "dashboard.commands": "指令统计", "dashboard.guilds": "服务器", "dashboard.updated": "更新于 {time}",
    "col.guild": "服务器", "col.voice": "语音频道", "col.status": "状态", "col.now": "正在播放", "col.queue": "队列", "col.ping": "语音延迟",
    "stat.discord": "Discord", "stat.connected": "已连接", "stat.disconnected": "未连接", "stat.latency": "延迟 {ms} ms", "stat.uptime": "运行时间", "stat.since": "启动于 {time}",
    "stat.guilds": "服务器", "stat.voice": "语音连接", "stat.playing": "{n} 个正在播放", "stat.queued": "队列中的音频", "stat.issues": "错误 / 警告", "stat.version": "版本 {v}",
    "sys.cpu": "进程CPU", "sys.mem": "进程内存", "sys.threads": "线程数", "sys.syscpu": "系统CPU", "sys.sysmem": "系统内存", "sys.disk": "磁盘可用", "sys.python": "Python", "sys.platform": "系统", "sys.nopsutil": "安装 psutil 以显示CPU与内存信息",
    "lib.usage": "已用 {used} / {cap}（{pct}%）", "lib.files": "文件数", "lib.locked": "使用中",
    "src.gomusic": "go-music-api", "src.ytdlp": "yt-dlp", "src.js": "JS运行时", "src.cookie": "YouTube Cookie", "src.proxy": "代理", "src.ffmpeg": "FFmpeg", "src.bili": "bilibili-api",
    "src.handler": "{p} 下载器", "src.netease": "网易云", "src.qq": "QQ音乐", "src.netease_full": "网易云音乐", "src.qq_full": "QQ音乐", "src.native_netease": "网易云登录", "src.native_qq": "QQ音乐登录", "src.music_proxy": "音乐平台代理", "src.quality": "音质", "src.unused": "未使用", "logged_in": "已登录", "guest": "游客", "src.kugou": "酷狗", "src.kuwo": "酷我", "src.migu": "咪咕",
    "ok": "正常", "missing": "未找到", "unavailable": "不可用", "enabled": "已启用", "disabled": "未启用", "unknown": "未知",
    "dl.none": "当前没有下载任务", "dl.stats": "成功 {s} · 失败 {f}", "dl.running": "下载中 {s}s",
    "cmd.none": "暂无指令记录", "cmd.total": "共 {n} 次",
    "chart.latency": "网关延迟", "chart.cpu": "CPU", "chart.voice": "语音连接",
    "player.join": "加入频道", "player.leave": "离开频道", "player.add": "添加音频", "player.add_placeholder": "粘贴哔哩哔哩 / YouTube / 网易云等链接", "player.add_btn": "添加到队列",
    "player.queue": "播放队列", "player.clear": "清空", "player.history": "播放历史", "player.empty": "队列为空", "player.no_history": "暂无历史记录", "player.idle": "当前没有播放",
    "player.summary": "{n} 首 · {d}", "player.choose_channel": "选择语音频道", "player.text_channel": "通知频道：#{c}", "player.play_next": "下一首播放", "player.remove": "移除", "player.readd": "重新加入队列",
    "player.select_guild": "请先在右下角选择服务器", "player.confirm_clear": "确定清空播放列表吗？",
    "pb.prev": "上一首", "pb.play": "播放/暂停", "pb.next": "下一首", "pb.not_connected": "不在语音频道", "pb.choose": "选择服务器…",
    "status.0": "待机中", "status.1": "正在播放", "status.2": "已暂停", "status.3": "不在语音频道",
    "search.placeholder": "搜索哔哩哔哩、YouTube、网易云音乐、QQ音乐…", "search.all": "全部平台", "search.btn": "搜索", "search.hint": "输入关键词开始搜索", "search.none": "没有找到结果", "search.searching": "搜索中…",
    "act.add": "添加", "act.cache": "缓存", "act.fav": "收藏", "act.save": "下载文件", "act.adding": "添加中…",
    "library.filter": "筛选标题…", "library.fetch_placeholder": "链接（仅缓存，不播放）", "library.fetch": "缓存", "library.empty": "音频库为空", "library.in_use": "使用中", "library.summary": "{n} 个文件 · {used} / {cap}",
    "fav.new": "新建收藏夹…", "fav.select": "选择或新建一个收藏夹", "fav.empty": "收藏夹为空", "fav.play_all": "全部加入队列", "fav.delete": "删除收藏夹", "fav.confirm_delete": "确定删除收藏夹「{n}」吗？",
    "fav.none": "还没有收藏夹", "fav.new_here": "新建并收藏…", "fav.cached": "已缓存", "fav.added": "已收藏到「{n}」", "fav.exists": "已在「{n}」中", "fav.queued": "已将 {n} 首加入队列",
    "logs.all": "全部级别", "logs.warn": "警告及以上", "logs.error": "仅错误", "logs.filter": "筛选内容…", "logs.follow": "自动滚动", "logs.empty": "暂无日志",
    "toast.added": "已添加：{t}", "toast.started": "开始播放：{t}", "toast.cached": "已缓存：{t}", "toast.no_guild": "请先选择服务器", "toast.no_permission": "权限不足",
    "conn.live": "实时", "conn.reconnecting": "重新连接中…",
    "unit.d": "天", "unit.h": "小时", "unit.m": "分钟",
  },
  en: {
    "nav.dashboard": "Monitor", "nav.player": "Player", "nav.search": "Search", "nav.library": "Library", "nav.favorites": "Favorites", "nav.logs": "Logs", "logout": "Log out",
    "dashboard.title": "Status", "dashboard.trend": "Trend (last hour)", "dashboard.system": "System", "dashboard.library": "Audio cache", "dashboard.sources": "Sources",
    "dashboard.downloads": "Downloads", "dashboard.commands": "Commands", "dashboard.guilds": "Servers", "dashboard.updated": "Updated {time}",
    "col.guild": "Server", "col.voice": "Voice channel", "col.status": "Status", "col.now": "Now playing", "col.queue": "Queue", "col.ping": "Voice ping",
    "stat.discord": "Discord", "stat.connected": "Connected", "stat.disconnected": "Disconnected", "stat.latency": "Latency {ms} ms", "stat.uptime": "Uptime", "stat.since": "Since {time}",
    "stat.guilds": "Servers", "stat.voice": "Voice connections", "stat.playing": "{n} playing", "stat.queued": "Queued tracks", "stat.issues": "Errors / warnings", "stat.version": "Version {v}",
    "sys.cpu": "Process CPU", "sys.mem": "Process memory", "sys.threads": "Threads", "sys.syscpu": "System CPU", "sys.sysmem": "System memory", "sys.disk": "Disk free", "sys.python": "Python", "sys.platform": "OS", "sys.nopsutil": "Install psutil to see CPU and memory",
    "lib.usage": "{used} of {cap} used ({pct}%)", "lib.files": "Files", "lib.locked": "In use",
    "src.gomusic": "go-music-api", "src.ytdlp": "yt-dlp", "src.js": "JS runtime", "src.cookie": "YouTube cookies", "src.proxy": "Proxy", "src.ffmpeg": "FFmpeg", "src.bili": "bilibili-api",
    "src.handler": "{p} handler", "src.netease": "NetEase", "src.qq": "QQ Music", "src.netease_full": "NetEase Cloud Music", "src.qq_full": "QQ Music", "src.native_netease": "NetEase login", "src.native_qq": "QQ Music login", "src.music_proxy": "Music proxy", "src.quality": "Quality", "src.unused": "Not used", "logged_in": "Logged in", "guest": "Guest", "src.kugou": "Kugou", "src.kuwo": "Kuwo", "src.migu": "Migu",
    "ok": "OK", "missing": "Missing", "unavailable": "Unavailable", "enabled": "On", "disabled": "Off", "unknown": "Unknown",
    "dl.none": "No downloads right now", "dl.stats": "{s} ok · {f} failed", "dl.running": "Downloading {s}s",
    "cmd.none": "No commands yet", "cmd.total": "{n} total",
    "chart.latency": "Gateway latency", "chart.cpu": "CPU", "chart.voice": "Voice connections",
    "player.join": "Join", "player.leave": "Leave", "player.add": "Add audio", "player.add_placeholder": "Paste a Bilibili / YouTube / NetEase link", "player.add_btn": "Add to queue",
    "player.queue": "Queue", "player.clear": "Clear", "player.history": "History", "player.empty": "Queue is empty", "player.no_history": "No history yet", "player.idle": "Nothing playing",
    "player.summary": "{n} tracks · {d}", "player.choose_channel": "Choose a voice channel", "player.text_channel": "Notifications: #{c}", "player.play_next": "Play next", "player.remove": "Remove", "player.readd": "Add to queue again",
    "player.select_guild": "Pick a server in the bottom-right first", "player.confirm_clear": "Clear the whole queue?",
    "pb.prev": "Previous", "pb.play": "Play/Pause", "pb.next": "Next", "pb.not_connected": "Not in a voice channel", "pb.choose": "Choose server…",
    "status.0": "Idle", "status.1": "Playing", "status.2": "Paused", "status.3": "Not connected",
    "search.placeholder": "Search Bilibili, YouTube, NetEase, QQ Music…", "search.all": "All sources", "search.btn": "Search", "search.hint": "Type something to search", "search.none": "No results", "search.searching": "Searching…",
    "act.add": "Add", "act.cache": "Cache", "act.fav": "Favorite", "act.save": "Download file", "act.adding": "Adding…",
    "library.filter": "Filter by title…", "library.fetch_placeholder": "Link (cache only, don't play)", "library.fetch": "Cache", "library.empty": "Library is empty", "library.in_use": "In use", "library.summary": "{n} files · {used} / {cap}",
    "fav.new": "New folder…", "fav.select": "Pick or create a folder", "fav.empty": "This folder is empty", "fav.play_all": "Queue all", "fav.delete": "Delete folder", "fav.confirm_delete": "Delete folder \"{n}\"?",
    "fav.none": "No folders yet", "fav.new_here": "New folder…", "fav.cached": "Cached", "fav.added": "Saved to \"{n}\"", "fav.exists": "Already in \"{n}\"", "fav.queued": "Queued {n} tracks",
    "logs.all": "All levels", "logs.warn": "Warnings and up", "logs.error": "Errors only", "logs.filter": "Filter…", "logs.follow": "Follow", "logs.empty": "No logs yet",
    "toast.added": "Added: {t}", "toast.started": "Now playing: {t}", "toast.cached": "Cached: {t}", "toast.no_guild": "Pick a server first", "toast.no_permission": "Not allowed",
    "conn.live": "Live", "conn.reconnecting": "Reconnecting…",
    "unit.d": "d", "unit.h": "h", "unit.m": "m",
  },
};

function loadLang() {
  try {
    const saved = localStorage.getItem("zeta.lang");
    if (saved === "zh" || saved === "en") return saved;
  } catch (e) { /* 浏览器存储不可用 */ }
  return (navigator.language || "zh").toLowerCase().startsWith("zh") ? "zh" : "en";
}

let lang = loadLang();

function t(key, vars) {
  let text = (I18N[lang] && I18N[lang][key]) || I18N.zh[key] || key;
  if (vars) for (const [name, value] of Object.entries(vars)) text = text.split(`{${name}}`).join(value);
  return text;
}

function applyI18n() {
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  document.title = lang === "zh" ? "Zeta-Bot 控制面板" : "Zeta-Bot Control Panel";
  $$("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
  $$("[data-i18n-placeholder]").forEach(el => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  $$("[data-i18n-title]").forEach(el => { el.title = t(el.dataset.i18nTitle); });
  $("#lang-toggle").textContent = lang === "zh" ? "EN" : "中文";
}

/* ====================== 状态与请求 ====================== */
const S = {
  me: null,
  guilds: [],
  guildId: null,
  guild: null,
  overview: null,
  view: "dashboard",
  logs: [],
  clock: {pos: 0, at: 0, playing: false, dur: 0},
  seeking: false,
  library: [],
  folders: [],
  folder: null,
  events: null,
  eventsOpen: false,
};

function store(key, value) {
  try { localStorage.setItem(key, value); } catch (e) { /* 浏览器存储不可用 */ }
}

function stored(key) {
  try { return localStorage.getItem(key); } catch (e) { return null; }
}

async function api(path, {method = "GET", body} = {}) {
  const options = {method, credentials: "same-origin", headers: {}};
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  if (response.status === 401) {
    location.href = "login";
    throw new Error("unauthorized");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `${response.status} ${response.statusText}`);
  return data;
}

function toast(message, kind = "info") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = message;
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), kind === "err" ? 6000 : 3500);
}

function can(operation) {
  return !!(S.me && S.me.permissions && S.me.permissions[operation]);
}

async function busy(button, task) {
  if (button) { button.disabled = true; button.classList.add("busy"); }
  try { return await task(); }
  catch (e) { if (e.message !== "unauthorized") toast(e.message, "err"); return null; }
  finally { if (button) { button.disabled = false; button.classList.remove("busy"); } }
}

async function act(action, body = {}, button = null) {
  if (!S.guildId) { toast(t("toast.no_guild"), "err"); return null; }
  return busy(button, async () => {
    const result = await api(`api/guild/${S.guildId}/${action}`, {method: "POST", body});
    const state = result.state || result;
    if (state && Array.isArray(state.queue)) applyState(state);
    return result;
  });
}

/* ====================== 视图切换 ====================== */
function showView(name) {
  if (name === "logs" && !(S.me && S.me.admin)) name = "dashboard";
  S.view = name;
  store("zeta.view", name);
  $$(".view").forEach(section => { section.hidden = section.id !== `view-${name}`; });
  $$("#nav button").forEach(button => button.classList.toggle("active", button.dataset.view === name));
  if (name === "dashboard") loadOverview();
  if (name === "player") renderPlayer();
  if (name === "library") loadLibrary();
  if (name === "favorites") loadFolders();
  if (name === "logs") loadLogs();
}

/* ====================== 服务器与实时推送 ====================== */
async function loadGuilds() {
  const data = await api("api/guilds");
  S.guilds = data.guilds;
  const select = $("#guild-select");
  select.innerHTML = `<option value="">${esc(t("pb.choose"))}</option>` + S.guilds.map(g =>
    `<option value="${esc(g.id)}">${esc(g.name)}${g.voice_channel ? " · 🔊" : ""}</option>`).join("");
  if (!S.guildId) {
    const saved = stored("zeta.guild");
    const preferred = S.guilds.find(g => g.id === saved) || S.guilds.find(g => g.status === 1) || S.guilds.find(g => g.voice_channel) || S.guilds[0];
    if (preferred) await selectGuild(preferred.id);
  }
  select.value = S.guildId || "";
  if (S.view === "dashboard" && S.overview) {
    S.overview.guilds = S.guilds;
    renderGuildTable();
  }
}

let guildRefreshTimer = null;
function scheduleGuildRefresh() {
  if (guildRefreshTimer) return;
  guildRefreshTimer = setTimeout(() => { guildRefreshTimer = null; loadGuilds().catch(() => {}); }, 800);
}

async function selectGuild(id) {
  S.guildId = id || null;
  store("zeta.guild", S.guildId || "");
  $("#guild-select").value = S.guildId || "";
  connectEvents();
  if (S.guildId) {
    try { applyState(await api(`api/guild/${S.guildId}`)); }
    catch (e) { toast(e.message, "err"); }
  } else {
    S.guild = null;
    renderPlayerBar();
    if (S.view === "player") renderPlayer();
  }
}

function setConnection(open) {
  S.eventsOpen = open;
  $("#conn-dot").className = `dot ${open ? "ok" : "warn"}`;
  const latency = S.overview && S.overview.bot.latency_ms;
  $("#conn-text").textContent = open ? (latency != null ? `${latency} ms` : t("conn.live")) : t("conn.reconnecting");
}

function connectEvents() {
  if (S.events) S.events.close();
  const source = new EventSource("api/events" + (S.guildId ? `?guild=${encodeURIComponent(S.guildId)}` : ""));
  S.events = source;
  source.addEventListener("hello", () => setConnection(true));
  source.addEventListener("state", event => applyState(JSON.parse(event.data)));
  source.addEventListener("guilds", () => scheduleGuildRefresh());
  source.addEventListener("log", event => addLog(JSON.parse(event.data)));
  source.addEventListener("sample", event => {
    if (!S.overview) return;
    S.overview.samples.push(JSON.parse(event.data));
    if (S.overview.samples.length > 360) S.overview.samples.shift();
    if (S.view === "dashboard") drawChart();
  });
  source.onerror = () => setConnection(false);
}

function applyState(state) {
  if (!state || state.id !== S.guildId) return;
  S.guild = state;
  const playing = !!state.now_playing && !state.paused && state.status === 1;
  S.clock = {pos: state.position || 0, at: performance.now(), playing, dur: state.now_playing ? state.now_playing.duration : 0};
  renderPlayerBar();
  if (S.view === "player") renderPlayer();
}

function currentPosition() {
  const clock = S.clock;
  if (!clock.playing) return clock.pos;
  return Math.min(clock.dur || Infinity, clock.pos + (performance.now() - clock.at) / 1000);
}

/* ====================== 底部播放栏 ====================== */
function renderPlayerBar() {
  const state = S.guild;
  const now = state && state.now_playing;
  $("#pb-title").textContent = now ? now.title : (state ? t("player.idle") : "—");
  const parts = [];
  if (state) {
    parts.push(state.name);
    parts.push(state.connected ? `🔊 ${state.voice_channel ? state.voice_channel.name : ""}` : t("pb.not_connected"));
    if (now) parts.push(t(`status.${state.status}`));
  }
  $("#pb-sub").textContent = parts.join(" · ");
  const cover = $("#pb-cover");
  if (now && now.cover) { cover.src = now.cover; cover.style.visibility = "visible"; }
  else { cover.removeAttribute("src"); cover.style.visibility = "hidden"; }

  const isPlaying = state && state.status === 1;
  $("#pb-play").innerHTML = icon(isPlaying ? "pause" : "play");
  $("#pb-play").disabled = !state || !can("pause");
  $("#pb-next").disabled = !state || !state.queue.length || !can("skip");
  $("#pb-prev").disabled = !state || !state.history.length || !can("skip");
  $("#pb-seek").classList.toggle("disabled", !now || !can("play"));
  $("#pb-dur").textContent = fmtTime(now ? now.duration : 0);

  const modeSelect = $("#pb-mode");
  if (state) {
    modeSelect.innerHTML = Object.entries(state.play_modes).map(([value, name]) => `<option value="${value}">${esc(name)}</option>`).join("");
    modeSelect.value = String(state.play_mode);
  }
  modeSelect.disabled = !state || !can("play");

  const volume = $("#pb-volume");
  if (state && document.activeElement !== volume) {
    volume.value = state.volume;
    $("#pb-volume-label").textContent = `${Math.round(state.volume)}%`;
  }
  volume.disabled = !state || !can("volume");
  updateProgress();
}

function updateProgress() {
  if (S.seeking) return;
  const position = currentPosition();
  const duration = S.clock.dur || 0;
  const percent = duration > 0 ? Math.min(100, position / duration * 100) : 0;
  $("#pb-fill").style.width = `${percent}%`;
  $("#pb-knob").style.left = `${percent}%`;
  $("#pb-pos").textContent = fmtTime(position);
}

function setupSeek() {
  const bar = $("#pb-seek");
  const ratioAt = event => {
    const rect = bar.getBoundingClientRect();
    return Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
  };
  const preview = ratio => {
    $("#pb-fill").style.width = `${ratio * 100}%`;
    $("#pb-knob").style.left = `${ratio * 100}%`;
    $("#pb-pos").textContent = fmtTime(ratio * (S.clock.dur || 0));
  };
  bar.addEventListener("pointerdown", event => {
    if (bar.classList.contains("disabled") || !S.clock.dur) return;
    S.seeking = true;
    bar.classList.add("dragging");
    bar.setPointerCapture(event.pointerId);
    preview(ratioAt(event));
  });
  bar.addEventListener("pointermove", event => { if (S.seeking) preview(ratioAt(event)); });
  bar.addEventListener("pointerup", async event => {
    if (!S.seeking) return;
    const position = Math.floor(ratioAt(event) * S.clock.dur);
    bar.classList.remove("dragging");
    S.clock = {...S.clock, pos: position, at: performance.now()};
    S.seeking = false;
    updateProgress();
    await act("seek", {position});
  });
}

/* ====================== 播放页 ====================== */
function renderPlayer() {
  const state = S.guild;
  if (!state) {
    $("#player-guild-name").textContent = t("nav.player");
    $("#now-card").innerHTML = `<div class="empty" style="flex:1">${esc(t("player.select_guild"))}</div>`;
    $("#queue-list").innerHTML = "";
    $("#history-list").innerHTML = "";
    $("#voice-select").innerHTML = "";
    return;
  }
  $("#player-guild-name").textContent = state.name;

  const voiceSelect = $("#voice-select");
  voiceSelect.innerHTML = `<option value="">${esc(t("player.choose_channel"))}</option>` + state.voice_channels.map(channel =>
    `<option value="${esc(channel.id)}">🔊 ${esc(channel.name)}${channel.members ? ` (${channel.members})` : ""}</option>`).join("");
  voiceSelect.value = state.voice_channel ? state.voice_channel.id : "";
  $("#btn-join").disabled = !can("join");
  $("#btn-leave").disabled = !state.connected || !can("leave");
  $("#btn-clear").disabled = !state.queue.length || !can("clear");

  const now = state.now_playing;
  $("#now-card").innerHTML = now ? `
      <img referrerpolicy="no-referrer" class="cover" src="${esc(now.cover || "")}" alt="" onerror="this.style.visibility='hidden'">
      <div style="min-width:0">
        <div class="faint">${esc(t(`status.${state.status}`))}</div>
        <div class="title" title="${esc(now.title)}">${esc(now.title)}</div>
        <div class="row" style="margin-top:8px">${sourceTag(now.source)}<span class="faint">${esc(now.duration_str)}</span>
        ${state.text_channel ? `<span class="faint">${esc(t("player.text_channel", {c: state.text_channel}))}</span>` : ""}</div>
      </div>` : `<div class="empty" style="flex:1">${esc(state.connected ? t("player.idle") : t("pb.not_connected"))}</div>`;

  $("#queue-summary").textContent = t("player.summary", {n: state.queue.length, d: state.queue_duration});
  const queueList = $("#queue-list");
  if (!state.queue.length) {
    queueList.innerHTML = `<div class="empty">${esc(t("player.empty"))}</div>`;
  } else {
    queueList.innerHTML = state.queue.map(item => `
      <div class="item${item.index === 1 && now ? " current" : ""}" draggable="${can("move")}" data-index="${item.index}">
        <span class="drag-handle">${icon("drag")}</span>
        <span class="index">${item.index}</span>
        <div class="info"><div class="title" title="${esc(item.title)}">${esc(item.title)}</div>
          <div class="meta">${sourceTag(item.source)}<span>${esc(item.duration_str)}</span></div></div>
        <div class="actions">
          ${item.index > 2 ? `<button class="btn small icon-only" data-act="next" title="${esc(t("player.play_next"))}" ${can("move") ? "" : "disabled"}>${icon("up")}</button>` : ""}
          <button class="btn small icon-only" data-act="fav" title="${esc(t("act.fav"))}">${icon("heart")}</button>
          <button class="btn small icon-only danger" data-act="remove" title="${esc(t("player.remove"))}" ${can("skip") ? "" : "disabled"}>${icon("close")}</button>
        </div>
      </div>`).join("");
  }

  const historyList = $("#history-list");
  historyList.innerHTML = state.history.length ? state.history.map((item, i) => `
      <div class="item" data-history="${i}">
        <div class="info"><div class="title" title="${esc(item.title)}">${esc(item.title)}</div>
          <div class="meta">${sourceTag(item.source)}<span>${esc(item.duration_str)}</span></div></div>
        <div class="actions"><button class="btn small icon-only" data-act="readd" title="${esc(t("player.readd"))}" ${can("play") ? "" : "disabled"}>${icon("plus")}</button></div>
      </div>`).join("") : `<div class="empty">${esc(t("player.no_history"))}</div>`;
}

function setupPlayerView() {
  $("#queue-list").addEventListener("click", event => {
    const button = event.target.closest("button[data-act]");
    if (!button) return;
    const index = Number(button.closest(".item").dataset.index);
    const item = S.guild.queue[index - 1];
    if (button.dataset.act === "remove") act("skip", {index}, button);
    if (button.dataset.act === "next") act("move", {from: index, to: 2}, button);
    if (button.dataset.act === "fav") showFavPicker(button, songFromAudio(item));
  });
  $("#history-list").addEventListener("click", event => {
    const button = event.target.closest("button[data-act]");
    if (!button) return;
    const item = S.guild.history[Number(button.closest(".item").dataset.history)];
    act("add-cached", {uid: item.uid}, button).then(result => { if (result) toast(t("toast.added", {t: item.title}), "ok"); });
  });

  // 拖动排序
  let dragFrom = null;
  const list = $("#queue-list");
  list.addEventListener("dragstart", event => {
    const item = event.target.closest(".item");
    if (!item) return;
    dragFrom = Number(item.dataset.index);
    item.classList.add("dragging");
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", String(dragFrom));
  });
  list.addEventListener("dragend", () => $$(".item", list).forEach(el => el.classList.remove("dragging", "drop-target")));
  list.addEventListener("dragover", event => {
    const item = event.target.closest(".item");
    if (!item || dragFrom === null) return;
    event.preventDefault();
    $$(".item", list).forEach(el => el.classList.toggle("drop-target", el === item));
  });
  list.addEventListener("drop", event => {
    const item = event.target.closest(".item");
    if (!item || dragFrom === null) return;
    event.preventDefault();
    const to = Number(item.dataset.index);
    if (to !== dragFrom) act("move", {from: dragFrom, to});
    dragFrom = null;
  });

  $("#btn-join").addEventListener("click", event => {
    const channelId = $("#voice-select").value;
    if (!channelId) { toast(t("player.choose_channel"), "err"); return; }
    act("join", {channel_id: channelId}, event.currentTarget);
  });
  $("#btn-leave").addEventListener("click", event => act("leave", {}, event.currentTarget));
  $("#btn-clear").addEventListener("click", event => { if (confirm(t("player.confirm_clear"))) act("clear", {}, event.currentTarget); });
  $("#add-form").addEventListener("submit", async event => {
    event.preventDefault();
    const input = $("#add-url");
    const url = input.value.trim();
    if (!url) return;
    const result = await act("add", {url}, event.submitter);
    if (result) {
      input.value = "";
      toast(t(result.started ? "toast.started" : "toast.added", {t: result.audio.title}), "ok");
    }
  });
}

/* ====================== 监控页 ====================== */
async function loadOverview() {
  try {
    S.overview = await api("api/overview");
    renderDashboard();
  } catch (e) {
    if (e.message !== "unauthorized") toast(e.message, "err");
  }
}

function statCard(label, value, sub = "", dotClass = "") {
  return `<div class="card stat"><div class="label">${dotClass ? `<i class="dot ${dotClass}" style="display:inline-block;margin-right:6px"></i>` : ""}${esc(label)}</div>
    <div class="value">${esc(value)}</div><div class="sub">${esc(sub)}</div></div>`;
}

function renderDashboard() {
  const o = S.overview;
  if (!o) return;
  const bot = o.bot;
  if (bot.avatar) $("#bot-avatar").src = bot.avatar;
  $("#conn-text").textContent = bot.ready ? (bot.latency_ms != null ? `${bot.latency_ms} ms` : t("conn.live")) : t("stat.disconnected");
  if (S.eventsOpen) $("#conn-dot").className = `dot ${bot.ready ? "ok" : "err"}`;
  $("#dash-updated").textContent = t("dashboard.updated", {time: new Date().toLocaleTimeString()});

  $("#stat-cards").innerHTML = [
    statCard(t("stat.discord"), bot.ready ? t("stat.connected") : t("stat.disconnected"), bot.latency_ms != null ? t("stat.latency", {ms: bot.latency_ms}) : "", bot.ready ? "ok" : "err"),
    statCard(t("stat.uptime"), fmtUptime(bot.uptime), t("stat.version", {v: bot.version})),
    statCard(t("stat.guilds"), o.counts.guilds, bot.name || ""),
    statCard(t("stat.voice"), o.counts.voice, t("stat.playing", {n: o.counts.playing})),
    statCard(t("stat.queued"), o.counts.queued, ""),
    statCard(t("stat.issues"), `${o.events.error || 0} / ${o.events.warning || 0}`, "", (o.events.error || 0) > 0 ? "err" : "ok"),
  ].join("");

  drawChart();

  // 系统资源
  const system = o.system;
  $("#system-card").hidden = !system;
  if (system) {
    const rows = [];
    if (system.psutil) {
      rows.push([t("sys.cpu"), `${system.cpu_percent}%`], [t("sys.mem"), fmtBytes(system.memory_rss)], [t("sys.threads"), system.threads],
        [t("sys.syscpu"), `${system.system_cpu_percent}%`], [t("sys.sysmem"), `${fmtBytes(system.system_memory.used)} / ${fmtBytes(system.system_memory.total)}`]);
    }
    if (system.disk) rows.push([t("sys.disk"), `${fmtBytes(system.disk.free)} / ${fmtBytes(system.disk.total)}`]);
    rows.push([t("sys.python"), system.python], [t("sys.platform"), system.platform]);
    $("#system-kv").innerHTML = rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("") +
      (system.psutil ? "" : `<dt></dt><dd class="faint">${esc(t("sys.nopsutil"))}</dd>`);
  }

  // 音频库
  const library = o.library;
  const meterClass = library.percent > 90 ? "warn" : "ok";
  $("#library-usage").innerHTML = `
    <div class="muted">${esc(t("lib.usage", {used: fmtBytes(library.used), cap: fmtBytes(library.capacity), pct: library.percent}))}</div>
    <div class="meter ${meterClass}"><div style="width:${Math.min(100, library.percent)}%"></div></div>
    <dl class="kv" style="margin-top:10px"><dt>${esc(t("lib.files"))}</dt><dd>${library.files}</dd><dt>${esc(t("lib.locked"))}</dt><dd>${library.locked}</dd></dl>`;

  // 音源
  const sources = o.sources;
  const yesNo = (value, good = "ok", bad = "missing") => value ? `<span class="tag ok">${esc(t(good))}</span>` : `<span class="tag err">${esc(t(bad))}</span>`;
  const goMusic = sources.go_music;
  const goMusicState = !goMusic.used ? `<span class="tag">${esc(t("src.unused"))}</span>`
    : goMusic.available == null ? `<span class="tag">${esc(t("unknown"))}</span>` : yesNo(goMusic.available, "ok", "unavailable");
  const native = sources.native || {};
  const loginTag = value => value ? `<span class="tag ok">${esc(t("logged_in"))}</span>` : `<span class="tag">${esc(t("guest"))}</span>`;
  let sourceRows = `
    <dt>${esc(t("src.ffmpeg"))}</dt><dd>${yesNo(sources.ffmpeg)}</dd>
    <dt>${esc(t("src.ytdlp"))}</dt><dd>${esc(sources.ytdlp.version)}</dd>
    <dt>${esc(t("src.js"))}</dt><dd>${sources.ytdlp.js_runtime ? `<span class="tag ok">${esc(sources.ytdlp.js_runtime)}</span>` : `<span class="tag warn">${esc(t("missing"))}</span>`}</dd>
    <dt>${esc(t("src.cookie"))}</dt><dd>${sources.ytdlp.cookie_file ? `<span class="tag ok">${esc(t("enabled"))}</span>` : `<span class="tag">${esc(t("disabled"))}</span>`}</dd>
    <dt>${esc(t("src.proxy"))}</dt><dd>${sources.ytdlp.proxy ? `<span class="tag ok">${esc(t("enabled"))}</span>` : `<span class="tag">${esc(t("disabled"))}</span>`}</dd>
    <dt>${esc(t("src.bili"))}</dt><dd>${esc(sources.bilibili_api)}</dd>
    <dt>${esc(t("src.native_netease"))}</dt><dd>${loginTag(native.netease_login)} <span class="faint">${esc(native.netease_level || "")}</span></dd>
    <dt>${esc(t("src.native_qq"))}</dt><dd>${loginTag(native.qq_login)} <span class="faint">${esc(native.qq_quality || "")}</span></dd>
    <dt>${esc(t("src.music_proxy"))}</dt><dd>${native.proxy ? `<span class="tag ok">${esc(t("enabled"))}</span>` : `<span class="tag">${esc(t("disabled"))}</span>`}</dd>
    <dt>${esc(t("src.gomusic"))}</dt><dd title="${esc(goMusic.url || "")}">${goMusicState}</dd>`;
  for (const [platform, handler] of Object.entries(sources.handlers)) {
    sourceRows += `<dt>${esc(t("src.handler", {p: platform}))}</dt><dd class="muted">${esc(handler)}</dd>`;
  }
  $("#sources-kv").innerHTML = sourceRows;

  // 下载任务
  const downloads = o.downloads;
  $("#download-stats").textContent = t("dl.stats", {s: downloads.stats.success, f: downloads.stats.failed});
  const downloadItems = [
    ...downloads.active.map(d => `<div class="item"><div class="info"><div class="title">${esc(d.title)}</div>
      <div class="meta">${sourceTag(d.source)}<span>${esc(t("dl.running", {s: d.elapsed}))}</span></div></div><span class="tag warn">…</span></div>`),
    ...downloads.recent.slice(0, 8).map(d => `<div class="item"><div class="info"><div class="title" title="${esc(d.message)}">${esc(d.title)}</div>
      <div class="meta">${sourceTag(d.source)}<span>${esc(d.time)}</span><span>${d.seconds}s</span>${d.ok ? "" : `<span style="color:var(--err)">${esc(d.message)}</span>`}</div></div>
      <span class="tag ${d.ok ? "ok" : "err"}">${d.ok ? "✓" : "✕"}</span></div>`),
  ];
  $("#download-list").innerHTML = downloadItems.length ? downloadItems.join("") : `<div class="empty">${esc(t("dl.none"))}</div>`;

  // 指令统计
  $("#command-total").textContent = t("cmd.total", {n: o.commands.total});
  const maxCount = Math.max(1, ...o.commands.top.map(([, count]) => count));
  $("#command-bars").innerHTML = o.commands.top.length ? o.commands.top.map(([name, count]) => `
    <div class="bar-row"><span class="ellipsis">/${esc(name)}</span><div class="track"><div style="width:${count / maxCount * 100}%"></div></div><span class="muted" style="text-align:right">${count}</span></div>`).join("")
    : `<div class="empty">${esc(t("cmd.none"))}</div>`;

  renderGuildTable();
}

function renderGuildTable() {
  const guilds = S.overview ? S.overview.guilds : [];
  $("#guild-table").innerHTML = guilds.map(g => `
    <tr class="clickable" data-guild="${esc(g.id)}">
      <td class="ellipsis">${esc(g.name)}</td>
      <td class="ellipsis">${g.voice_channel ? `🔊 ${esc(g.voice_channel)}` : '<span class="faint">—</span>'}</td>
      <td><span class="tag ${g.status === 1 ? "ok" : g.status === 2 ? "warn" : ""}">${esc(t(`status.${g.status}`))}</span></td>
      <td class="ellipsis">${g.now_playing ? esc(g.now_playing.title) : '<span class="faint">—</span>'}</td>
      <td>${g.queue_length}</td>
      <td>${g.latency_ms != null ? `${g.latency_ms} ms` : '<span class="faint">—</span>'}</td>
    </tr>`).join("") || `<tr><td colspan="6" class="empty">—</td></tr>`;
}

function drawChart() {
  const svg = $("#chart-latency");
  const samples = (S.overview && S.overview.samples) || [];
  const width = 300, height = 100;
  const series = [
    {key: "latency", color: "var(--accent)", label: t("chart.latency"), unit: " ms"},
    {key: "cpu", color: "var(--info)", label: t("chart.cpu"), unit: "%"},
  ].filter(s => samples.some(p => p[s.key] != null));
  let content = [25, 50, 75].map(y => `<line class="grid-line" x1="0" x2="${width}" y1="${y}" y2="${y}"/>`).join("");
  if (samples.length >= 2) {
    const t0 = samples[0].t, t1 = samples[samples.length - 1].t || t0 + 1;
    for (const s of series) {
      const values = samples.map(p => p[s.key]).filter(v => v != null);
      const max = Math.max(...values) * 1.15 || 1;
      const points = samples.filter(p => p[s.key] != null).map(p =>
        `${((p.t - t0) / Math.max(1, t1 - t0) * width).toFixed(1)},${(height - p[s.key] / max * (height - 6) - 3).toFixed(1)}`);
      content += `<polygon class="area" fill="${s.color}" points="0,${height} ${points.join(" ")} ${width},${height}"/>`;
      content += `<polyline class="line" stroke="${s.color}" points="${points.join(" ")}"/>`;
    }
  }
  svg.innerHTML = content;
  const last = samples[samples.length - 1] || {};
  $("#chart-legend").innerHTML = series.map(s =>
    `<span><i style="background:${s.color}"></i>${esc(s.label)} ${last[s.key] != null ? esc(last[s.key] + s.unit) : ""}</span>`).join("") +
    (last.voice != null ? `<span>${esc(t("chart.voice"))} ${last.voice}</span>` : "");
}

/* ====================== 搜索 ====================== */
function songFromAudio(item) {
  return {title: item.title, url: item.url || null, uid: item.uid || null, source: item.source, duration: item.duration, thumbnail: item.cover || item.thumbnail || null};
}

function setupSearch() {
  $("#search-form").addEventListener("submit", async event => {
    event.preventDefault();
    const query = $("#search-input").value.trim();
    if (!query) return;
    const box = $("#search-results");
    box.innerHTML = `<div class="empty">${esc(t("search.searching"))}</div>`;
    const data = await busy(event.submitter, () => api("api/search", {method: "POST", body: {query, source: $("#search-source").value}}));
    if (!data) { box.innerHTML = ""; return; }
    S.searchResults = data.results;
    box.innerHTML = data.results.length ? data.results.map((r, i) => `
      <div class="item" data-result="${i}">
        <img referrerpolicy="no-referrer" class="thumb" src="${esc(r.thumbnail || "")}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">
        <div class="info"><div class="title" title="${esc(r.title)}">${esc(r.title)}</div>
          <div class="meta">${sourceTag(r.source)}<span>${esc(r.duration_str)}</span></div></div>
        <div class="actions">
          <button class="btn small primary" data-act="add" ${can("play") ? "" : "disabled"}>${icon("plus")}${esc(t("act.add"))}</button>
          <button class="btn small icon-only" data-act="fav" title="${esc(t("act.fav"))}">${icon("heart")}</button>
          <button class="btn small icon-only" data-act="cache" title="${esc(t("act.cache"))}" ${can("play") ? "" : "disabled"}>${icon("download")}</button>
        </div>
      </div>`).join("") : `<div class="empty">${esc(t("search.none"))}</div>`;
  });
  $("#search-results").addEventListener("click", async event => {
    const button = event.target.closest("button[data-act]");
    if (!button) return;
    const result = S.searchResults[Number(button.closest(".item").dataset.result)];
    if (button.dataset.act === "add") {
      const response = await act("add", {url: result.id}, button);
      if (response) toast(t(response.started ? "toast.started" : "toast.added", {t: response.audio.title}), "ok");
    } else if (button.dataset.act === "cache") {
      const response = await busy(button, () => api("api/library/fetch", {method: "POST", body: {url: result.id}}));
      if (response) toast(t("toast.cached", {t: response.audio.title}), "ok");
    } else if (button.dataset.act === "fav") {
      showFavPicker(button, {title: result.title, url: result.id, uid: null, source: result.source, duration: result.duration, thumbnail: result.thumbnail});
    }
  });
}

/* ====================== 音频库 ====================== */
async function loadLibrary() {
  const data = await busy(null, () => api("api/library"));
  if (!data) return;
  S.library = data.items;
  $("#library-summary").textContent = t("library.summary", {n: data.items.length, used: fmtBytes(data.used), cap: fmtBytes(data.capacity)});
  renderLibrary();
}

function renderLibrary() {
  const filter = $("#library-filter").value.trim().toLowerCase();
  const items = S.library.map((item, i) => ({item, i})).filter(({item}) => !filter || item.title.toLowerCase().includes(filter));
  $("#library-list").innerHTML = items.length ? items.map(({item, i}) => `
    <div class="item" data-lib="${i}">
      <img referrerpolicy="no-referrer" class="thumb" src="${esc(item.cover || "")}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">
      <div class="info"><div class="title" title="${esc(item.title)}">${esc(item.title)}</div>
        <div class="meta">${sourceTag(item.source)}<span>${esc(item.duration_str)}</span><span>${fmtBytes(item.size)}</span>${item.in_use ? `<span class="tag warn">${esc(t("library.in_use"))}</span>` : ""}</div></div>
      <div class="actions">
        <button class="btn small primary" data-act="add" ${can("play") ? "" : "disabled"}>${icon("plus")}${esc(t("act.add"))}</button>
        <button class="btn small icon-only" data-act="fav" title="${esc(t("act.fav"))}">${icon("heart")}</button>
        <a class="btn small icon-only" href="files/${encodeURIComponent(item.uid)}" title="${esc(t("act.save"))}">${icon("download")}</a>
      </div>
    </div>`).join("") : `<div class="empty">${esc(t("library.empty"))}</div>`;
}

function setupLibrary() {
  $("#library-filter").addEventListener("input", renderLibrary);
  $("#library-list").addEventListener("click", async event => {
    const button = event.target.closest("button[data-act]");
    if (!button) return;
    const item = S.library[Number(button.closest(".item").dataset.lib)];
    if (button.dataset.act === "add") {
      const response = await act("add-cached", {uid: item.uid}, button);
      if (response) toast(t(response.started ? "toast.started" : "toast.added", {t: item.title}), "ok");
    } else if (button.dataset.act === "fav") {
      showFavPicker(button, songFromAudio(item));
    }
  });
  $("#fetch-form").addEventListener("submit", async event => {
    event.preventDefault();
    const url = $("#fetch-url").value.trim();
    if (!url) return;
    const response = await busy(event.submitter, () => api("api/library/fetch", {method: "POST", body: {url}}));
    if (response) {
      $("#fetch-url").value = "";
      toast(t("toast.cached", {t: response.audio.title}), "ok");
      loadLibrary();
    }
  });
}

/* ====================== 收藏夹 ====================== */
async function loadFolders() {
  const data = await busy(null, () => api("api/favorites"));
  if (!data) return;
  S.folders = data.folders;
  $("#folder-list").innerHTML = S.folders.length ? S.folders.map(folder => `
    <div class="folder${S.folder && S.folder.name === folder.name ? " active" : ""}" data-folder="${esc(folder.name)}">
      <span class="ellipsis">${esc(folder.name)}</span><span class="faint">${folder.count}</span>
    </div>`).join("") : `<div class="empty">${esc(t("fav.none"))}</div>`;
}

async function openFolder(name) {
  const data = await busy(null, () => api(`api/favorites/${encodeURIComponent(name)}`));
  if (!data) return;
  S.folder = data;
  loadFolders();
  const songs = data.songs;
  $("#folder-detail").innerHTML = `
    <div class="view-title" style="margin-bottom:12px"><h1 style="font-size:17px">${esc(data.name)}</h1>
      <div class="row">
        <button class="btn primary small" id="fav-play-all" ${songs.length && can("play") ? "" : "disabled"}>${icon("play")}${esc(t("fav.play_all"))}</button>
        <button class="btn small danger" id="fav-delete">${icon("trash")}${esc(t("fav.delete"))}</button>
      </div></div>
    <div class="list" id="fav-songs">${songs.length ? songs.map((song, i) => `
      <div class="item" data-song="${i}">
        <img referrerpolicy="no-referrer" class="thumb" src="${esc(song.thumbnail || "")}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">
        <div class="info"><div class="title" title="${esc(song.title)}">${esc(song.title)}</div>
          <div class="meta">${sourceTag(song.source)}<span>${song.duration ? fmtTime(song.duration) : ""}</span>${song.cached ? `<span class="tag ok">${esc(t("fav.cached"))}</span>` : ""}</div></div>
        <div class="actions">
          <button class="btn small primary" data-act="add" ${can("play") && (song.url || song.cached) ? "" : "disabled"}>${icon("plus")}${esc(t("act.add"))}</button>
          <button class="btn small icon-only danger" data-act="remove" title="${esc(t("player.remove"))}">${icon("close")}</button>
        </div>
      </div>`).join("") : `<div class="empty">${esc(t("fav.empty"))}</div>`}</div>`;
}

async function queueSong(song, button) {
  const body = song.uid && song.cached !== false ? {uid: song.uid} : null;
  if (body) {
    const response = await act("add-cached", body, button);
    if (response) return response;
    if (!song.url) return null;
  }
  return song.url ? act("add", {url: song.url}, button) : null;
}

function setupFavorites() {
  $("#folder-form").addEventListener("submit", async event => {
    event.preventDefault();
    const name = $("#folder-name").value.trim();
    if (!name) return;
    const response = await busy(event.submitter, () => api("api/favorites", {method: "POST", body: {name}}));
    if (response) { $("#folder-name").value = ""; await openFolder(response.name); }
  });
  $("#folder-list").addEventListener("click", event => {
    const folder = event.target.closest("[data-folder]");
    if (folder) openFolder(folder.dataset.folder);
  });
  $("#folder-detail").addEventListener("click", async event => {
    const button = event.target.closest("button");
    if (!button || !S.folder) return;
    if (button.id === "fav-delete") {
      if (!confirm(t("fav.confirm_delete", {n: S.folder.name}))) return;
      await busy(button, () => api(`api/favorites/${encodeURIComponent(S.folder.name)}`, {method: "DELETE"}));
      S.folder = null;
      $("#folder-detail").innerHTML = `<div class="empty">${esc(t("fav.select"))}</div>`;
      loadFolders();
      return;
    }
    if (button.id === "fav-play-all") {
      let count = 0;
      button.disabled = true;
      for (const song of S.folder.songs) {
        if (await queueSong(song, null)) count++;
      }
      button.disabled = false;
      toast(t("fav.queued", {n: count}), "ok");
      return;
    }
    const songEl = button.closest("[data-song]");
    if (!songEl) return;
    const song = S.folder.songs[Number(songEl.dataset.song)];
    if (button.dataset.act === "add") {
      const response = await queueSong(song, button);
      if (response) toast(t(response.started ? "toast.started" : "toast.added", {t: song.title}), "ok");
    } else if (button.dataset.act === "remove") {
      await busy(button, () => api(`api/favorites/${encodeURIComponent(S.folder.name)}/items`, {method: "DELETE", body: {key: song.uid || song.url}}));
      openFolder(S.folder.name);
    }
  });
}

async function addToFolder(name, song) {
  const response = await busy(null, () => api(`api/favorites/${encodeURIComponent(name)}/items`, {method: "POST", body: song}));
  if (response) toast(t(response.duplicate ? "fav.exists" : "fav.added", {n: name}), "ok");
}

async function showFavPicker(anchor, song) {
  closePopovers();
  const data = await busy(null, () => api("api/favorites"));
  if (!data) return;
  const popover = document.createElement("div");
  popover.className = "popover";
  popover.innerHTML = data.folders.map(folder => `<div class="opt" data-folder="${esc(folder.name)}"><span class="ellipsis">${esc(folder.name)}</span><span class="faint">${folder.count}</span></div>`).join("") +
    `<form class="row"><input class="input grow" maxlength="40" placeholder="${esc(t("fav.new_here"))}" style="min-width:0;padding:5px 8px"><button class="btn small" type="submit">+</button></form>`;
  anchor.closest(".actions").appendChild(popover);
  popover.addEventListener("click", async event => {
    const option = event.target.closest("[data-folder]");
    if (!option) return;
    closePopovers();
    await addToFolder(option.dataset.folder, song);
  });
  popover.querySelector("form").addEventListener("submit", async event => {
    event.preventDefault();
    const name = popover.querySelector("input").value.trim();
    if (!name) return;
    const created = await busy(null, () => api("api/favorites", {method: "POST", body: {name}}));
    closePopovers();
    if (created) await addToFolder(created.name, song);
  });
  popover.querySelector("input").focus();
}

function closePopovers() { $$(".popover").forEach(el => el.remove()); }

/* ====================== 日志 ====================== */
function logLevelVisible(entry) {
  const level = $("#log-level").value;
  if (level === "error" && entry.level !== "error") return false;
  if (level === "warning" && !["warning", "error"].includes(entry.level)) return false;
  const filter = $("#log-filter").value.trim().toLowerCase();
  return !filter || `${entry.location} ${entry.content}`.toLowerCase().includes(filter);
}

function logRow(entry) {
  return `<div class="log ${esc(entry.level)}"><span class="t">${esc(entry.time)}</span><span class="l" title="${esc(entry.location)}">${esc(entry.location)}</span><span class="c">${esc(entry.content)}</span></div>`;
}

function renderLogs() {
  const box = $("#log-box");
  const visible = S.logs.filter(logLevelVisible);
  box.innerHTML = visible.length ? visible.map(logRow).join("") : `<div class="empty">${esc(t("logs.empty"))}</div>`;
  if ($("#log-follow").checked) box.scrollTop = box.scrollHeight;
}

async function loadLogs() {
  if (!(S.me && S.me.admin)) return;
  const data = await busy(null, () => api("api/logs?limit=1000"));
  if (!data) return;
  S.logs = data.logs;
  renderLogs();
}

function addLog(entry) {
  if (S.logs.length && S.logs[S.logs.length - 1].id >= entry.id) return;
  S.logs.push(entry);
  if (S.logs.length > 1500) S.logs.splice(0, S.logs.length - 1500);
  if (S.view !== "logs" || !logLevelVisible(entry)) return;
  const box = $("#log-box");
  const empty = box.querySelector(".empty");
  if (empty) empty.remove();
  box.insertAdjacentHTML("beforeend", logRow(entry));
  while (box.children.length > 1500) box.firstElementChild.remove();
  if ($("#log-follow").checked) box.scrollTop = box.scrollHeight;
}

/* ====================== 初始化 ====================== */
function setupPlayerBar() {
  $("#pb-prev").innerHTML = icon("prev");
  $("#pb-next").innerHTML = icon("next");
  $("#pb-play").innerHTML = icon("play");
  $("#pb-play").addEventListener("click", event => act("pause", {}, event.currentTarget));
  $("#pb-next").addEventListener("click", event => act("skip", {}, event.currentTarget));
  $("#pb-prev").addEventListener("click", event => act("previous", {}, event.currentTarget));
  $("#pb-mode").addEventListener("change", event => act("mode", {mode: Number(event.target.value)}));
  const volume = $("#pb-volume");
  volume.addEventListener("input", () => { $("#pb-volume-label").textContent = `${volume.value}%`; });
  volume.addEventListener("change", () => act("volume", {volume: Number(volume.value)}));
  $("#guild-select").addEventListener("change", event => selectGuild(event.target.value));
  setupSeek();
}

async function init() {
  applyI18n();
  $("#lang-toggle").addEventListener("click", () => {
    lang = lang === "zh" ? "en" : "zh";
    store("zeta.lang", lang);
    applyI18n();
    renderPlayerBar();
    showView(S.view);
  });
  $$("#nav button").forEach(button => button.addEventListener("click", () => showView(button.dataset.view)));
  document.addEventListener("click", event => {
    if (!event.target.closest(".popover") && !event.target.closest("[data-act=fav]")) closePopovers();
  });
  setupPlayerBar();
  setupPlayerView();
  setupSearch();
  setupLibrary();
  setupFavorites();
  $("#log-level").addEventListener("change", renderLogs);
  $("#log-filter").addEventListener("input", renderLogs);

  try {
    S.me = await api("api/me");
  } catch (e) {
    return;
  }
  $("#user-name").textContent = S.me.name;
  $("#nav-logs").hidden = !S.me.admin;

  await loadGuilds().catch(e => toast(e.message, "err"));
  if (!S.guildId) connectEvents();
  const initialView = stored("zeta.view") || "dashboard";
  // 顶栏的头像与延迟来自监控数据，其他页面也需要加载一次
  if (initialView !== "dashboard") loadOverview();
  showView(initialView);

  setInterval(updateProgress, 250);
  setInterval(() => { if (S.view === "dashboard" && !document.hidden) loadOverview(); }, 5000);
  // 推送连接异常时（例如反向代理缓冲了SSE）退回定时刷新
  setInterval(() => {
    if (document.hidden) return;
    if (!S.eventsOpen && S.guildId) api(`api/guild/${S.guildId}`).then(applyState).catch(() => {});
    loadGuilds().catch(() => {});
  }, 20000);
}

init();
