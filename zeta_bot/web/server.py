"""
Web控制面板与监控面板

基于aiohttp，直接运行在机器人的事件循环中（不需要额外线程，可以直接访问机器人状态），
通过Server-Sent Events向浏览器实时推送播放状态与日志。

配置文件：./configs/web_config.json（首次运行自动生成）
    enabled     是否启用
    host        监听地址（0.0.0.0 为所有网卡，127.0.0.1 为仅本机）
    port        监听端口
    base_path   URL前缀，用于反向代理挂载到子路径，例如 "/zeta"
    public_url  /webauth 指令中显示的面板地址（使用反向代理或公网地址时设置）
    api_token   只读API令牌（用于外部监控工具，请求头 Authorization: Bearer <令牌>，仅允许GET请求）
命令行参数 --web-port / --web-host / --web-base-path / --no-web 与环境变量 ZETA_WEB_PORT / ZETA_WEB_HOST 可覆盖配置文件
"""
from typing import *
import os
import re
import json
import time
import hmac
import asyncio
import urllib.parse
from pathlib import Path

from aiohttp import web

import errors
import utils

from zeta_bot import output_console, events
from zeta_bot.web.auth import WebAuth
from zeta_bot.web.monitor import Monitor, SAMPLE_INTERVAL

STATIC_DIR = Path(__file__).resolve().parent / "static"
CONFIG_PATH = "./configs/web_config.json"
FAVORITES_PATH = "./data/favorites"
SESSION_COOKIE = "zeta_session"

DEFAULT_CONFIG = {
    "enabled": True,
    "host": "0.0.0.0",
    "port": 5000,
    "base_path": "",
    "public_url": "",
    "api_token": "",
}

# 网页操作对应的权限（与Discord指令权限一致）
PERMISSION_OPERATIONS = ["play", "pause", "resume", "skip", "move", "clear", "volume", "join", "leave", "search_audio"]

PUBLIC_PATHS = {"/login", "/api/login", "/healthz"}
PUBLIC_PREFIXES = ("/static/",)

monitor = Monitor()
auth: Optional[WebAuth] = None
_core = None
_config: dict = dict(DEFAULT_CONFIG)
_runner: Optional[web.AppRunner] = None
_background_tasks: List[asyncio.Task] = []
_go_music_status = {"available": None, "checked_at": None}

# 尽早注册日志监听器，使启动过程中的日志也能在网页中查看
try:
    output_console.Console().add_listener(monitor.on_log)
except TypeError:
    pass


def _console() -> output_console.Console:
    return output_console.Console()


# ---------------------------------------- 配置 ----------------------------------------
def _normalize_base_path(base_path) -> str:
    base_path = "/" + str(base_path or "").strip().strip("/")
    return "" if base_path == "/" else base_path


def load_config(overrides: Optional[dict] = None) -> dict:
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            loaded = utils.json_load(CONFIG_PATH)
            if isinstance(loaded, dict):
                config.update({key: loaded[key] for key in loaded if key in DEFAULT_CONFIG})
                # 补全新增的配置项
                if any(key not in loaded for key in DEFAULT_CONFIG):
                    utils.json_save(CONFIG_PATH, {**DEFAULT_CONFIG, **loaded})
        except errors.JSONFileError:
            pass
    else:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        utils.json_save(CONFIG_PATH, config)

    if os.environ.get("ZETA_WEB_PORT"):
        config["port"] = os.environ["ZETA_WEB_PORT"]
    if os.environ.get("ZETA_WEB_HOST"):
        config["host"] = os.environ["ZETA_WEB_HOST"]
    for key, value in (overrides or {}).items():
        if key in DEFAULT_CONFIG and value is not None:
            config[key] = value

    config["port"] = int(config["port"])
    config["base_path"] = _normalize_base_path(config["base_path"])
    return config


def is_running() -> bool:
    return _runner is not None


def public_url() -> str:
    if _config.get("public_url"):
        return str(_config["public_url"]).rstrip("/") + "/"
    host = _config.get("host") or "localhost"
    if host in ("0.0.0.0", "::", ""):
        host = "localhost"
    return f"http://{host}:{_config['port']}{_config['base_path']}/"


def _url(path: str) -> str:
    return f"{_config['base_path']}{path}"


# ---------------------------------------- 工具 ----------------------------------------
def json_error(message: str, status: int = 400) -> web.Response:
    return web.json_response({"error": message}, status=status)


async def _read_json(request: web.Request) -> dict:
    if not request.can_read_body:
        return {}
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise web.HTTPBadRequest(text=json.dumps({"error": "请求内容不是有效的JSON"}), content_type="application/json")
    return data if isinstance(data, dict) else {}


def _relative_path(request: web.Request) -> str:
    path = request.path
    base_path = _config["base_path"]
    if base_path and path.startswith(base_path):
        path = path[len(base_path):] or "/"
    return path


def _authenticate(request: web.Request) -> Optional[dict]:
    user = auth.verify_token(request.cookies.get(SESSION_COOKIE)) if auth is not None else None
    if user is not None:
        group = _core.user_group(user["id"]) if _core is not None else "owner"
        if group in ("banned", "blocked"):
            return None
        user["group"] = group
        user["admin"] = group in ("owner", "administrator")
        user["via"] = "session"
        return user

    api_token = str(_config.get("api_token") or "")
    header = request.headers.get("Authorization", "")
    if api_token and request.method == "GET" and header.startswith("Bearer ") and hmac.compare_digest(header[7:].strip(), api_token):
        return {"id": "api", "name": "API", "group": "api", "admin": True, "via": "token"}
    return None


def _member_guild_ids(user_id: str) -> set:
    """
    用户使用过指令的服务器（成员缓存不完整时作为补充）
    """
    path = f"{_core.member_lib.root}/{user_id}.json"
    try:
        return {str(key) for key in (utils.json_load(path).get("guilds") or {})}
    except (errors.JSONFileError, FileNotFoundError, OSError, AttributeError):
        return set()


def _accessible_guilds(user: dict) -> list:
    guilds = sorted(_core.bot.guilds, key=lambda item: item.name.lower())
    if user["admin"]:
        return guilds
    try:
        user_id = int(user["id"])
    except ValueError:
        return []
    known = _member_guild_ids(user["id"])
    return [item for item in guilds if item.get_member(user_id) is not None or str(item.id) in known]


def _require_guild(request: web.Request) -> str:
    guild_id = request.match_info["guild_id"]
    if not any(str(item.id) == guild_id for item in _accessible_guilds(request["user"])):
        raise web.HTTPForbidden(text=json.dumps({"error": "无权访问该服务器"}), content_type="application/json")
    return guild_id


def _require_permission(user: dict, operation: str) -> None:
    if user["via"] == "token":
        raise web.HTTPForbidden(text=json.dumps({"error": "API令牌为只读权限"}), content_type="application/json")
    if not _core.user_allowed(user["id"], operation):
        raise web.HTTPForbidden(text=json.dumps({"error": "权限不足"}), content_type="application/json")


def _require_admin(user: dict) -> None:
    if not user["admin"]:
        raise web.HTTPForbidden(text=json.dumps({"error": "仅管理员可以查看"}), content_type="application/json")


def _audio_source_url(target_audio) -> Optional[str]:
    """
    根据音频来源还原原始链接（用于收藏夹，缓存被清理后可以重新下载）
    """
    source = target_audio.get_source()
    source_id = target_audio.get_source_id()
    if source == "youtube":
        return f"https://www.youtube.com/watch?v={source_id}"
    if source == "bilibili" and str(source_id).startswith("BV"):
        page_match = re.search(r"_p(\d+)$", target_audio.get_uid())
        return f"https://www.bilibili.com/video/{source_id}" + (f"?p={page_match.group(1)}" if page_match else "")
    if source == "netease":
        return f"https://music.163.com/song?id={source_id}"
    if source == "qq":
        return f"https://y.qq.com/n/ryqq/songDetail/{source_id}"
    return None


def _content_disposition(filename: str) -> str:
    fallback = re.sub(r"[^A-Za-z0-9._ -]", "_", filename) or "audio"
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{urllib.parse.quote(filename)}"


# ---------------------------------------- 中间件 ----------------------------------------
@web.middleware
async def auth_middleware(request: web.Request, handler):
    relative_path = _relative_path(request)
    request["user"] = _authenticate(request)
    if request["user"] is None and relative_path not in PUBLIC_PATHS and not relative_path.startswith(PUBLIC_PREFIXES):
        if relative_path.startswith("/api/") or relative_path.startswith("/files/"):
            return json_error("未登录或登录已过期", 401)
        raise web.HTTPFound(_url("/login"))
    return await handler(request)


@web.middleware
async def error_middleware(request: web.Request, handler):
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except asyncio.CancelledError:
        raise
    except Exception as e:
        if _core is not None and isinstance(e, _core.PlayerError):
            return json_error(e.message, e.status)
        if isinstance(e, (KeyError, ValueError, TypeError)):
            return json_error(f"参数错误：{e}", 400)
        await _console().on_error(e)
        return json_error("服务器内部错误，详情请查看错误日志", 500)


# ---------------------------------------- 页面与登录 ----------------------------------------
def _static_page(name: str) -> web.FileResponse:
    return web.FileResponse(STATIC_DIR / name, headers={"Cache-Control": "no-cache"})


async def handle_index(request: web.Request):
    return _static_page("index.html")


async def handle_login_page(request: web.Request):
    if request["user"] is not None:
        raise web.HTTPFound(_url("/"))
    return _static_page("login.html")


async def handle_login(request: web.Request):
    client_key = request.remote or "unknown"
    if not auth.allow_attempt(client_key):
        return json_error("尝试次数过多，请稍后再试", 429)
    data = await _read_json(request)
    info = auth.redeem_code(data.get("code", ""))
    if info is None:
        await _console().rp(f"Web控制面板登录失败：来自 {client_key} 的验证码无效", "[Web控制面板]", message_type=utils.PrintType.WARNING)
        return json_error("验证码无效或已过期，请在Discord中使用 /webauth 重新获取", 401)

    token, max_age = auth.make_token(info["user_id"], info["username"], info["days"])
    response = web.json_response({"ok": True, "username": info["username"]})
    response.set_cookie(
        SESSION_COOKIE, token, max_age=max_age, httponly=True, samesite="Lax",
        path=_config["base_path"] or "/", secure=request.secure,
    )
    await _console().rp(f"用户 {info['username']} 登录Web控制面板（来自 {client_key}）", "[Web控制面板]")
    return response


async def handle_logout(request: web.Request):
    response = web.HTTPFound(_url("/login"))
    response.del_cookie(SESSION_COOKIE, path=_config["base_path"] or "/")
    raise response


async def handle_healthz(request: web.Request):
    bot = _core.bot if _core is not None else None
    ready = bot is not None and bot.is_ready() and not bot.is_closed()
    return web.json_response({
        "status": "ok" if ready else "starting",
        "discord_connected": ready,
        "uptime": round(monitor.uptime()),
    }, status=200 if ready else 503)


# ---------------------------------------- 状态与监控 ----------------------------------------
async def handle_me(request: web.Request):
    user = request["user"]
    permissions = {operation: user["via"] != "token" and _core.user_allowed(user["id"], operation) for operation in PERMISSION_OPERATIONS}
    return web.json_response({**user, "permissions": permissions})


def _finite_ms(value) -> Optional[int]:
    if value is None or value != value or value == float("inf"):
        return None
    return round(value * 1000)


async def handle_overview(request: web.Request):
    user = request["user"]
    bot = _core.bot
    voice_clients = list(bot.voice_clients)
    guild_summaries = [_core.guild_summary(item) for item in _accessible_guilds(user)]
    library = _core.audio_lib_main
    overview = {
        "bot": {
            "name": str(bot.user) if bot.user else None,
            "avatar": bot.user.display_avatar.url if bot.user else None,
            "ready": bot.is_ready() and not bot.is_closed(),
            "latency_ms": _finite_ms(bot.latency),
            "version": _core.version,
            "update_time": _core.update_time,
            "pycord": _core.pycord_version,
            "startup_time": _core.startup_time,
            "uptime": round(monitor.uptime()),
        },
        "counts": {
            "guilds": len(bot.guilds),
            "voice": len(voice_clients),
            "playing": sum(1 for client in voice_clients if client.is_playing()),
            "paused": sum(1 for client in voice_clients if client.is_paused()),
            "queued": sum(summary["queue_length"] for summary in guild_summaries),
        },
        "library": {
            "used": library.get_used_storage_size(),
            "capacity": library.get_storage_capacity(),
            "percent": library.get_used_storage_percentage(1),
            "files": len(library),
            "locked": library.get_locked_count(),
        },
        "downloads": library.get_download_activity(),
        "sources": {
            "go_music": {"url": _core.go_music_url, "used": _core.resource_classifier.uses(_core.DownloadHandler.GO_MUSIC_API), **_go_music_status},
            "native": _core.native_music.describe(),
            "ytdlp": _core.ytdlp.describe(),
            "bilibili_api": _core.bilibili_api_version,
            "ffmpeg": os.path.exists(_core.ffmpeg_path),
            "handlers": _core.resource_classifier.describe(),
        },
        "commands": {
            "total": monitor.command_total,
            "top": monitor.commands.most_common(8),
        },
        "events": dict(monitor.counters),
        "samples": list(monitor.samples),
        "guilds": guild_summaries,
        "web": {"url": public_url(), "clients": events.subscriber_count()},
    }
    if user["admin"]:
        overview["system"] = monitor.system_info(_core.audio_lib_main._root)
    return web.json_response(overview)


async def handle_logs(request: web.Request):
    _require_admin(request["user"])
    after = int(request.query.get("after", 0))
    limit = max(1, min(1000, int(request.query.get("limit", 300))))
    return web.json_response({"logs": monitor.get_logs(after, limit)})


# ---------------------------------------- 播放控制 ----------------------------------------
async def handle_guilds(request: web.Request):
    return web.json_response({"guilds": [_core.guild_summary(item) for item in _accessible_guilds(request["user"])]})


async def handle_guild_state(request: web.Request):
    guild_id = _require_guild(request)
    discord_guild, current_guild = await _core.get_guild_pair(guild_id)
    return web.json_response(_core.guild_state(discord_guild, current_guild))


GUILD_ACTIONS: Dict[str, Tuple[str, Callable[..., Awaitable[dict]]]] = {}


def _register_actions() -> None:
    core = _core
    GUILD_ACTIONS.update({
        "pause": ("pause", lambda gid, name, body: core.player_toggle_pause(gid, name)),
        "skip": ("skip", lambda gid, name, body: core.player_skip(gid, name, body.get("index"))),
        "previous": ("skip", lambda gid, name, body: core.player_previous(gid, name)),
        "seek": ("play", lambda gid, name, body: core.player_seek(gid, name, float(body["position"]))),
        "move": ("move", lambda gid, name, body: core.player_move(gid, name, int(body["from"]), int(body["to"]))),
        "volume": ("volume", lambda gid, name, body: core.player_set_volume(gid, name, float(body["volume"]))),
        "mode": ("play", lambda gid, name, body: core.player_set_mode(gid, name, int(body["mode"]))),
        "clear": ("clear", lambda gid, name, body: core.player_clear(gid, name)),
        "join": ("join", lambda gid, name, body: core.player_join(gid, name, body["channel_id"])),
        "leave": ("leave", lambda gid, name, body: core.player_leave(gid, name)),
        "add": ("play", lambda gid, name, body: core.player_add_url(gid, name, str(body["url"]).strip())),
        "add-cached": ("play", lambda gid, name, body: core.player_add_cached(gid, name, str(body["uid"]))),
    })


async def handle_guild_action(request: web.Request):
    guild_id = _require_guild(request)
    action = request.match_info["action"]
    if action not in GUILD_ACTIONS:
        return json_error("未知操作", 404)
    operation, function = GUILD_ACTIONS[action]
    user = request["user"]
    _require_permission(user, operation)
    body = await _read_json(request)
    return web.json_response(await function(guild_id, user["name"], body))


async def handle_search(request: web.Request):
    _require_permission(request["user"], "search_audio")
    body = await _read_json(request)
    query = str(body.get("query", "")).strip()
    if not query:
        return json_error("请输入搜索内容")
    source = body.get("source", "all")
    if source not in ("all", "bilibili", "youtube", "netease", "qq"):
        source = "all"
    results = await _core.search_all(query, source, query_num=8)
    return web.json_response({"results": results})


# ---------------------------------------- 音频库 ----------------------------------------
async def handle_library(request: web.Request):
    library = _core.audio_lib_main
    items = []
    for cached_audio in library.list_audios():
        item = _core.audio_to_dict(cached_audio)
        try:
            item["size"] = os.path.getsize(cached_audio.get_path())
        except OSError:
            item["size"] = None
        item["in_use"] = library.using(cached_audio)
        item["url"] = _audio_source_url(cached_audio)
        items.append(item)
    return web.json_response({
        "items": items,
        "used": library.get_used_storage_size(),
        "capacity": library.get_storage_capacity(),
        "percent": library.get_used_storage_percentage(1),
    })


async def handle_library_fetch(request: web.Request):
    """
    下载链接对应的音频到音频库（不加入播放列表）
    """
    _require_permission(request["user"], "play")
    body = await _read_json(request)
    new_audio = await _core.download_single(str(body.get("url", "")).strip())
    item = _core.audio_to_dict(new_audio)
    item["url"] = _audio_source_url(new_audio)
    return web.json_response({"ok": True, "audio": item})


async def handle_file(request: web.Request):
    cached_audio = _core.audio_lib_main.get_audio_by_uid(request.match_info["uid"])
    if cached_audio is None or not os.path.isfile(cached_audio.get_path()):
        return json_error("文件不存在", 404)
    extension = os.path.splitext(cached_audio.get_path())[1]
    filename = utils.legal_name(cached_audio.get_title())[:100] + extension
    return web.FileResponse(cached_audio.get_path(), headers={"Content-Disposition": _content_disposition(filename)})


# ---------------------------------------- 收藏夹 ----------------------------------------
_FAVORITE_NAME_PATTERN = re.compile(r"^[^\\/:*?\"<>|\x00-\x1f]{1,40}$")


def _favorite_name(name) -> str:
    name = str(name or "").strip()
    if not name or name.startswith(".") or not _FAVORITE_NAME_PATTERN.fullmatch(name):
        raise web.HTTPBadRequest(text=json.dumps({"error": "无效的收藏夹名称（1-40个字符，不能包含 \\ / : * ? \" < > |）"}), content_type="application/json")
    return name


def _favorite_path(name: str) -> str:
    return os.path.join(FAVORITES_PATH, f"{name}.json")


def _load_favorite(name: str) -> Optional[dict]:
    path = _favorite_path(name)
    if not os.path.exists(path):
        return None
    try:
        data = utils.json_load(path)
    except errors.JSONFileError:
        return None
    if not isinstance(data, dict):
        return None
    data.setdefault("name", name)
    data.setdefault("songs", [])
    return data


def _save_favorite(name: str, data: dict) -> None:
    os.makedirs(FAVORITES_PATH, exist_ok=True)
    utils.json_save(_favorite_path(name), data)


async def handle_favorites(request: web.Request):
    folders = []
    if os.path.isdir(FAVORITES_PATH):
        for filename in sorted(os.listdir(FAVORITES_PATH)):
            if filename.endswith(".json"):
                data = _load_favorite(filename[:-5])
                if data is not None:
                    folders.append({"name": filename[:-5], "count": len(data["songs"])})
    return web.json_response({"folders": folders})


async def handle_favorite_create(request: web.Request):
    name = _favorite_name((await _read_json(request)).get("name"))
    if os.path.exists(_favorite_path(name)):
        return json_error("收藏夹已存在", 409)
    _save_favorite(name, {"name": name, "songs": []})
    return web.json_response({"ok": True, "name": name})


async def handle_favorite_get(request: web.Request):
    name = _favorite_name(request.match_info["name"])
    data = _load_favorite(name)
    if data is None:
        return json_error("收藏夹不存在", 404)
    library = _core.audio_lib_main
    for song in data["songs"]:
        cached = library.get_audio_by_uid(song["uid"]) if song.get("uid") else None
        song["cached"] = cached is not None and os.path.exists(cached.get_path())
    return web.json_response(data)


async def handle_favorite_delete(request: web.Request):
    name = _favorite_name(request.match_info["name"])
    path = _favorite_path(name)
    if os.path.exists(path):
        os.remove(path)
    return web.json_response({"ok": True})


def _song_key(song: dict) -> str:
    return str(song.get("uid") or song.get("url") or "")


async def handle_favorite_add(request: web.Request):
    name = _favorite_name(request.match_info["name"])
    data = _load_favorite(name)
    if data is None:
        return json_error("收藏夹不存在", 404)
    body = await _read_json(request)
    song = {key: body.get(key) for key in ("title", "url", "uid", "source", "duration", "thumbnail")}
    song["title"] = str(song.get("title") or "未知标题")[:200]
    if not song.get("url") and not song.get("uid"):
        return json_error("缺少链接或音频ID")
    if any(_song_key(item) == _song_key(song) or (song.get("url") and item.get("url") == song.get("url")) for item in data["songs"]):
        return web.json_response({"ok": True, "duplicate": True, "count": len(data["songs"])})
    data["songs"].append(song)
    _save_favorite(name, data)
    return web.json_response({"ok": True, "count": len(data["songs"])})


async def handle_favorite_remove(request: web.Request):
    name = _favorite_name(request.match_info["name"])
    data = _load_favorite(name)
    if data is None:
        return json_error("收藏夹不存在", 404)
    key = str((await _read_json(request)).get("key", ""))
    data["songs"] = [song for song in data["songs"] if _song_key(song) != key and song.get("url") != key]
    _save_favorite(name, data)
    return web.json_response({"ok": True, "count": len(data["songs"])})


# ---------------------------------------- 实时推送 ----------------------------------------
async def _sse_send(response: web.StreamResponse, event: str, data: Any) -> None:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    await response.write(f"event: {event}\ndata: {payload}\n\n".encode("utf-8"))


async def handle_events(request: web.Request):
    """
    Server-Sent Events：推送服务器状态变化、日志（管理员）与监控采样
    ?guild=<ID> 订阅该服务器的完整播放状态
    """
    user = request["user"]
    guild_id = request.query.get("guild")
    if guild_id and not any(str(item.id) == guild_id for item in _accessible_guilds(user)):
        guild_id = None
    accessible_ids = {str(item.id) for item in _accessible_guilds(user)}

    response = web.StreamResponse(headers={
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })
    await response.prepare(request)
    queue = events.subscribe()

    async def send_state():
        discord_guild, current_guild = await _core.get_guild_pair(guild_id)
        await _sse_send(response, "state", _core.guild_state(discord_guild, current_guild))

    try:
        await _sse_send(response, "hello", {"time": time.time()})
        if guild_id:
            await send_state()
        while True:
            try:
                first = await asyncio.wait_for(queue.get(), timeout=15)
            except asyncio.TimeoutError:
                await response.write(b": ping\n\n")
                continue
            # 合并短时间内的多个事件
            await asyncio.sleep(0.15)
            batch = [first]
            while not queue.empty():
                batch.append(queue.get_nowait())

            changed_guilds = set()
            for kind, data in batch:
                if kind == "guild" and str(data) in accessible_ids:
                    changed_guilds.add(str(data))
                elif kind == "log" and user["admin"]:
                    await _sse_send(response, "log", data)
                elif kind == "sample":
                    await _sse_send(response, "sample", data)
            if changed_guilds:
                await _sse_send(response, "guilds", sorted(changed_guilds))
                if guild_id in changed_guilds:
                    await send_state()
    except (ConnectionResetError, asyncio.CancelledError, RuntimeError):
        pass
    finally:
        events.unsubscribe(queue)
    return response


# ---------------------------------------- 后台任务 ----------------------------------------
async def _check_go_music() -> None:
    url = _core.go_music_url
    # 没有平台使用go-music-api时不检测
    if not _core.resource_classifier.uses(_core.DownloadHandler.GO_MUSIC_API):
        _go_music_status.update({"available": None, "checked_at": int(time.time())})
        return
    if not url:
        _go_music_status.update({"available": False, "checked_at": int(time.time())})
        return
    try:
        available = await _core.go_music.is_available(url, silent=True)
    except Exception:
        available = False
    _go_music_status.update({"available": available, "checked_at": int(time.time())})


async def _sampler() -> None:
    tick = 0
    while True:
        try:
            bot = _core.bot
            voice_clients = list(bot.voice_clients)
            monitor.sample(
                _finite_ms(bot.latency),
                len(voice_clients),
                sum(1 for client in voice_clients if client.is_playing()),
            )
            if tick % 6 == 0:
                await _check_go_music()
        except Exception as e:
            await _console().on_error(e)
        tick += 1
        await asyncio.sleep(SAMPLE_INTERVAL)


# ---------------------------------------- 启动 ----------------------------------------
def create_app() -> web.Application:
    app = web.Application(middlewares=[error_middleware, auth_middleware], client_max_size=1024 * 1024)
    prefix = _config["base_path"]
    routes = [
        web.get(prefix + "/", handle_index),
        web.get(prefix + "/login", handle_login_page),
        web.get(prefix + "/logout", handle_logout),
        web.get(prefix + "/healthz", handle_healthz),
        web.post(prefix + "/api/login", handle_login),
        web.get(prefix + "/api/me", handle_me),
        web.get(prefix + "/api/overview", handle_overview),
        web.get(prefix + "/api/logs", handle_logs),
        web.get(prefix + "/api/events", handle_events),
        web.get(prefix + "/api/guilds", handle_guilds),
        web.get(prefix + "/api/guild/{guild_id}", handle_guild_state),
        web.post(prefix + "/api/guild/{guild_id}/{action}", handle_guild_action),
        web.post(prefix + "/api/search", handle_search),
        web.get(prefix + "/api/library", handle_library),
        web.post(prefix + "/api/library/fetch", handle_library_fetch),
        web.get(prefix + "/files/{uid}", handle_file),
        web.get(prefix + "/api/favorites", handle_favorites),
        web.post(prefix + "/api/favorites", handle_favorite_create),
        web.get(prefix + "/api/favorites/{name}", handle_favorite_get),
        web.delete(prefix + "/api/favorites/{name}", handle_favorite_delete),
        web.post(prefix + "/api/favorites/{name}/items", handle_favorite_add),
        web.delete(prefix + "/api/favorites/{name}/items", handle_favorite_remove),
        web.static(prefix + "/static", STATIC_DIR),
    ]
    if prefix:
        async def redirect_to_prefix(request: web.Request):
            raise web.HTTPFound(prefix + "/")
        routes.append(web.get(prefix, redirect_to_prefix))
    app.add_routes(routes)
    return app


async def start_from_bot(core_module, overrides: Optional[dict] = None) -> bool:
    """
    在机器人的事件循环中启动Web控制面板，返回是否启动成功
    """
    global _core, auth, _runner, _config
    if _runner is not None:
        return True
    _core = core_module
    _config = load_config(overrides)
    console = _console()

    if not _config.get("enabled", True):
        await console.rp("Web控制面板已在配置中禁用（configs/web_config.json）", "[Web控制面板]")
        return False

    auth = WebAuth()
    _register_actions()
    runner = web.AppRunner(create_app(), access_log=None, handle_signals=False)
    await runner.setup()
    site = web.TCPSite(runner, _config["host"], _config["port"])
    try:
        await site.start()
    except OSError as e:
        await runner.cleanup()
        await console.rp(
            f"Web控制面板启动失败，端口 {_config['port']} 可能已被占用：{e}\n可通过 configs/web_config.json 或启动参数 --web-port 修改端口",
            "[Web控制面板]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return False

    _runner = runner
    _background_tasks.append(asyncio.get_running_loop().create_task(_sampler()))
    await console.rp(f"Web控制面板已启动：{public_url()}（监听 {_config['host']}:{_config['port']}）\n在Discord中使用 /webauth 获取登录验证码", "[Web控制面板]")
    return True


async def stop() -> None:
    global _runner
    for task in _background_tasks:
        task.cancel()
    _background_tasks.clear()
    if _runner is not None:
        await _runner.cleanup()
        _runner = None
