"""
Web UI server that runs alongside the Discord bot.
Provides search, download, playlist management and playback control.
Started as a background thread from core.py on_ready.
"""
import os
import json
import uuid
import html as html_lib
import threading
import asyncio
import subprocess
import platform
import time as _time
import secrets
import string
import functools
from flask import Flask, render_template_string, request, jsonify, send_from_directory, session, redirect, url_for
from yt_dlp import YoutubeDL
from bilibili_api import search as bilibili_search

import utils
from zeta_bot import audio as audio_module
from zeta_bot.resource import DownloadType

DOWNLOAD_PATH = "./downloads"
COOKIE_FILE = "./configs/cookies.txt"
FAVORITES_PATH = "./data/favorites"

if platform.system().lower() == "windows":
    FFPROBE_PATH = "./bin/ffprobe.exe"
else:
    FFPROBE_PATH = "./bin/ffprobe"


def get_audio_duration(filepath):
    """Get audio duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [FFPROBE_PATH, "-v", "quiet", "-print_format", "json", "-show_format", filepath],
            capture_output=True, text=True, timeout=10
        )
        info = json.loads(result.stdout)
        return int(float(info["format"]["duration"]))
    except Exception:
        return 0


app = Flask(__name__)

AUTH_CODES_PATH = "./data/web_auth_codes.json"
AUTH_DEFAULT_VALIDITY_DAYS = 3

# Load or generate a persistent secret key for Flask sessions
_SECRET_KEY_PATH = "./data/web_secret_key"
def _get_secret_key():
    os.makedirs("./data", exist_ok=True)
    if os.path.exists(_SECRET_KEY_PATH):
        with open(_SECRET_KEY_PATH, "r") as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(_SECRET_KEY_PATH, "w") as f:
        f.write(key)
    return key

app.secret_key = _get_secret_key()

# These are set by init() from core.py
bot = None
bot_loop = None
guild_lib = None
audio_lib_main = None
ffmpeg_path = None

# Reference to core module's play functions (set by init)
_core = None

# Download task tracking
tasks = {}


# ── Auth Code Management (persistent across restarts) ──

def _load_auth_codes():
    if not os.path.exists(AUTH_CODES_PATH):
        return []
    try:
        with open(AUTH_CODES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("codes", [])
    except Exception:
        return []


def _save_auth_codes(codes):
    os.makedirs(os.path.dirname(AUTH_CODES_PATH), exist_ok=True)
    with open(AUTH_CODES_PATH, "w", encoding="utf-8") as f:
        json.dump({"codes": codes}, f, ensure_ascii=False, indent=2)


def _cleanup_expired_codes(codes):
    now = _time.time()
    return [c for c in codes if c["expires_at"] > now]


def generate_auth_code(user_id, username, validity_days=AUTH_DEFAULT_VALIDITY_DAYS):
    """Generate a new auth code for a Discord user. Called from core.py slash command."""
    codes = _load_auth_codes()
    codes = _cleanup_expired_codes(codes)

    # Remove existing codes for this user
    codes = [c for c in codes if c["user_id"] != user_id]

    code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    now = _time.time()
    codes.append({
        "code": code,
        "user_id": user_id,
        "username": username,
        "created_at": now,
        "expires_at": now + validity_days * 86400,
    })
    _save_auth_codes(codes)
    return code, validity_days


def verify_auth_code(code):
    """Verify an auth code. Returns user info dict or None."""
    codes = _load_auth_codes()
    codes = _cleanup_expired_codes(codes)
    _save_auth_codes(codes)
    for c in codes:
        if c["code"] == code.strip().upper():
            return {"user_id": c["user_id"], "username": c["username"]}
    return None


def require_auth(f):
    """Decorator to protect Flask routes."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated


def init(_bot, _bot_loop, _guild_lib, _audio_lib_main, _ffmpeg_path):
    global bot, bot_loop, guild_lib, audio_lib_main, ffmpeg_path, _core
    bot = _bot
    bot_loop = _bot_loop
    guild_lib = _guild_lib
    audio_lib_main = _audio_lib_main
    ffmpeg_path = _ffmpeg_path
    from zeta_bot import core as core_module
    _core = core_module


def start(port=5000):
    thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False), daemon=True)
    thread.start()


def ydl_opts_base():
    opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "js_runtimes": {"node": {}},
    }
    if os.path.exists(COOKIE_FILE):
        opts["cookiefile"] = COOKIE_FILE
    return opts


def convert_duration_to_str(duration):
    if duration is None or not isinstance(duration, (int, float)):
        return "00:00"
    duration = int(duration)
    if duration <= 0:
        return "00:00"
    hour = duration // 3600
    minutes = (duration % 3600) // 60
    seconds = duration % 60
    if hour > 0:
        return f"{hour:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def convert_byte(byte_count):
    if byte_count is None:
        return "unknown"
    b = int(byte_count)
    for unit in ["B", "KiB", "MiB", "GiB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TiB"


# ── Search ──────────────────────────────────────────

def search_youtube(query, num=5):
    opts = ydl_opts_base()
    opts["extract_flat"] = True
    opts["default_search"] = "ytsearch"
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{num}:{query}", download=False)
    results = []
    for item in info.get("entries", []):
        results.append({
            "title": item.get("title", ""),
            "id": item.get("id", ""),
            "url": f"https://www.youtube.com/watch?v={item.get('id', '')}",
            "duration": convert_duration_to_str(item.get("duration")),
            "thumbnail": (item.get("thumbnails", [{}])[-1].get("url", "")
                          if item.get("thumbnails") else ""),
            "source": "youtube",
        })
    return results


def search_bilibili(query, num=5):
    """Bilibili search (runs its own event loop since bilibili_api is async)."""
    async def _search():
        info_dict = await bilibili_search.search_by_type(
            query, search_type=bilibili_search.SearchObjectType.VIDEO
        )
        results = []
        counter = 0
        for item in info_dict.get("result", []):
            if counter >= num:
                break
            title = html_lib.unescape(item.get("title", ""))
            title = title.replace("<em class=\"keyword\">", "").replace("</em>", "")
            duration = utils.convert_str_to_duration(item.get("duration", "0:0"))
            results.append({
                "title": title,
                "id": item.get("bvid", ""),
                "url": f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                "duration": convert_duration_to_str(duration),
                "thumbnail": item.get("pic", "").replace("//", "https://") if item.get("pic", "").startswith("//") else item.get("pic", ""),
                "source": "bilibili",
            })
            counter += 1
        return results

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_search())
    finally:
        loop.close()


# ── Download ────────────────────────────────────────

def do_download(url, task_id):
    tasks[task_id] = {"status": "downloading", "progress": "0%", "title": "", "filename": ""}
    try:
        opts = ydl_opts_base()
        opts["outtmpl"] = os.path.join(DOWNLOAD_PATH, "%(title)s.%(ext)s")

        def progress_hook(d):
            if d["status"] == "downloading":
                tasks[task_id]["progress"] = d.get("_percent_str", "0%").strip()
                tasks[task_id]["title"] = d.get("filename", "")
            elif d["status"] == "finished":
                tasks[task_id]["progress"] = "100%"
                tasks[task_id]["filename"] = d.get("filename", "")

        opts["progress_hooks"] = [progress_hook]
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            tasks[task_id]["title"] = info.get("title", "")
            tasks[task_id]["status"] = "done"
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)


# ── Bot helpers (run async on bot loop) ─────────────

def run_on_bot_loop(coro):
    """Submit a coroutine to the bot's event loop and wait for the result."""
    future = asyncio.run_coroutine_threadsafe(coro, bot_loop)
    return future.result(timeout=30)


async def _ensure_guild_initialized(discord_guild):
    """Auto-initialize a guild in guild_lib if it hasn't been yet."""
    if discord_guild.id not in guild_lib._guild_dict:
        await guild_lib.check_by_guild_obj(discord_guild, audio_lib_main)


async def _get_guilds_info():
    """Return list of guilds the bot is connected to (runs on bot loop)."""
    result = []
    for g in bot.guilds:
        await _ensure_guild_initialized(g)
        try:
            vc = g.voice_client
            result.append({
                "id": str(g.id),
                "name": g.name,
                "voice_connected": vc is not None,
                "voice_channel": vc.channel.name if vc and vc.channel else None,
                "is_playing": vc.is_playing() if vc else False,
                "is_paused": vc.is_paused() if vc else False,
            })
        except Exception:
            result.append({
                "id": str(g.id),
                "name": g.name,
                "voice_connected": False,
                "voice_channel": None,
                "is_playing": False,
                "is_paused": False,
            })
    return result


async def _get_guild_playlist(guild_id):
    """Return playlist info for a guild (runs on bot loop)."""
    guild_id = int(guild_id)
    discord_guild = bot.get_guild(guild_id)
    if discord_guild is None:
        return None
    await _ensure_guild_initialized(discord_guild)
    g = guild_lib._guild_dict.get(guild_id)
    if g is None:
        return None
    pl = g.get_playlist()
    items = []
    for i, info in enumerate(pl.get_list_info()):
        items.append({
            "index": i + 1,
            "title": info[0],
            "duration": info[1],
            "is_current": i == 0,
        })
    vc = discord_guild.voice_client
    is_playing = vc.is_playing() if vc else False
    is_paused = vc.is_paused() if vc else False

    # Track playback state transitions
    current_audio = pl.get_audio(0) if len(pl) > 0 else None
    if current_audio and is_playing:
        st = _core._playback_state.get(guild_id) if _core else None
        if not st or st.get("title") != current_audio.get_title():
            _core.playback_track_start(guild_id, current_audio.get_title(), current_audio.get_duration())
        elif "paused_at" in st:
            _core.playback_track_resume(guild_id)
    elif current_audio and is_paused:
        _core.playback_track_pause(guild_id)
    elif not current_audio:
        _core.playback_track_stop(guild_id)

    position, total = _core.playback_get_position(guild_id) if _core else (0, 0)
    cur_total = current_audio.get_duration() if current_audio else 0

    return {
        "guild_name": g.get_name(),
        "length": len(pl),
        "total_duration": pl.get_duration_str(),
        "volume": g.get_voice_volume(),
        "is_playing": is_playing,
        "is_paused": is_paused,
        "position": position,
        "track_duration": cur_total,
        "items": items,
    }


# ── API Routes ──────────────────────────────────────

@app.before_request
def check_auth():
    """Protect all routes except login and static files."""
    open_paths = ("/login", "/api/login")
    if request.path in open_paths or request.path.startswith("/static"):
        return
    if not session.get("authenticated"):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "unauthorized"}), 401
        return redirect(url_for("login_page"))


@app.route("/login")
def login_page():
    if session.get("authenticated"):
        return redirect(url_for("index"))
    return render_template_string(LOGIN_TEMPLATE)


@app.route("/api/login", methods=["POST"])
def api_login():
    code = request.json.get("code", "").strip()
    if not code:
        return jsonify({"error": "Please enter a code"}), 400
    user = verify_auth_code(code)
    if user is None:
        return jsonify({"error": "Invalid or expired code"}), 401
    session["authenticated"] = True
    session["user_id"] = user["user_id"]
    session["username"] = user["username"]
    session.permanent = True
    app.permanent_session_lifetime = __import__("datetime").timedelta(days=AUTH_DEFAULT_VALIDITY_DAYS)
    return jsonify({"ok": True, "username": user["username"]})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/search", methods=["POST"])
def api_search():
    query = request.json.get("query", "").strip()
    source = request.json.get("source", "all")
    if not query:
        return jsonify({"error": "empty query"}), 400
    try:
        results = []
        if source in ("all", "youtube"):
            results += search_youtube(query)
        if source in ("all", "bilibili"):
            results += search_bilibili(query)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download", methods=["POST"])
def api_download():
    url = request.json.get("url", "").strip()
    if not url:
        return jsonify({"error": "empty url"}), 400
    task_id = str(uuid.uuid4())[:8]
    thread = threading.Thread(target=do_download, args=(url, task_id), daemon=True)
    thread.start()
    return jsonify({"task_id": task_id})


@app.route("/api/status/<task_id>")
def api_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "not found"}), 404
    return jsonify(task)


@app.route("/api/files")
def api_files():
    files = []
    if os.path.exists(DOWNLOAD_PATH):
        for f in sorted(os.listdir(DOWNLOAD_PATH),
                        key=lambda x: os.path.getmtime(os.path.join(DOWNLOAD_PATH, x)),
                        reverse=True):
            path = os.path.join(DOWNLOAD_PATH, f)
            if os.path.isfile(path):
                dur = get_audio_duration(path)
                files.append({"name": f, "size": convert_byte(os.path.getsize(path)), "duration": convert_duration_to_str(dur)})
    return jsonify({"files": files})


@app.route("/files/<path:filename>")
def serve_file(filename):
    return send_from_directory(os.path.abspath(DOWNLOAD_PATH), filename, as_attachment=True)


# ── Bot control API ─────────────────────────────────

@app.route("/api/guilds")
def api_guilds():
    if bot is None or bot_loop is None:
        return jsonify({"error": "bot not ready"}), 503
    try:
        guilds = run_on_bot_loop(_get_guilds_info())
        return jsonify({"guilds": guilds})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/guild/<guild_id>/playlist")
def api_playlist(guild_id):
    if bot is None or bot_loop is None:
        return jsonify({"error": "bot not ready"}), 503
    try:
        pl = run_on_bot_loop(_get_guild_playlist(guild_id))
        if pl is None:
            return jsonify({"error": "guild not found"}), 404
        return jsonify(pl)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/guild/<guild_id>/pause", methods=["POST"])
def api_pause(guild_id):
    try:
        async def _pause():
            discord_guild = bot.get_guild(int(guild_id))
            if not discord_guild:
                return {"error": "guild not found"}
            await _ensure_guild_initialized(discord_guild)
            vc = discord_guild.voice_client
            if vc and vc.is_playing():
                vc.pause()
                return {"ok": True, "action": "paused"}
            elif vc and vc.is_paused():
                vc.resume()
                return {"ok": True, "action": "resumed"}
            return {"error": "not playing"}
        result = run_on_bot_loop(_pause())
        status = 400 if "error" in result else 200
        return jsonify(result), status
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/guild/<guild_id>/skip", methods=["POST"])
def api_skip(guild_id):
    try:
        req_index = request.json.get("index") if request.json else None

        async def _skip():
            discord_guild = bot.get_guild(int(guild_id))
            if not discord_guild:
                return {"error": "guild not found"}
            await _ensure_guild_initialized(discord_guild)
            g = guild_lib._guild_dict.get(int(guild_id))
            if not g:
                return {"error": "guild not initialized"}
            pl = g.get_playlist()
            vc = discord_guild.voice_client

            if req_index is not None:
                idx = int(req_index) - 1
                if idx == 0 and vc and (vc.is_playing() or vc.is_paused()):
                    vc.stop()
                elif 0 <= idx < len(pl):
                    pl.remove_audio(idx)
                return {"ok": True}

            if vc and (vc.is_playing() or vc.is_paused()):
                vc.stop()
            elif len(pl) > 0:
                pl.remove_audio(0)
            return {"ok": True}

        result = run_on_bot_loop(_skip())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/guild/<guild_id>/move", methods=["POST"])
def api_move(guild_id):
    try:
        data = request.json
        from_val = int(data["from"])
        to_val = int(data["to"])

        async def _move():
            discord_guild = bot.get_guild(int(guild_id))
            if not discord_guild:
                return {"error": "guild not found"}
            await _ensure_guild_initialized(discord_guild)
            g = guild_lib._guild_dict.get(int(guild_id))
            if not g:
                return {"error": "guild not initialized"}
            pl = g.get_playlist()
            vc = discord_guild.voice_client
            from_idx = from_val - 1
            to_idx = to_val - 1

            if from_idx == 0 and vc and (vc.is_playing() or vc.is_paused()):
                current_audio = pl.get_audio(0)
                pl.insert_audio(current_audio, to_idx + 1)
                vc.stop()
            elif to_idx == 0 and vc and (vc.is_playing() or vc.is_paused()):
                current_audio = pl.get_audio(0)
                target = pl.get_audio(from_idx)
                pl.remove_audio(from_idx)
                pl.insert_audio(current_audio, 1)
                pl.insert_audio(target, 1)
                vc.stop()
            else:
                pl.move_audio(from_idx, to_idx)
            return {"ok": True}

        result = run_on_bot_loop(_move())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/guild/<guild_id>/volume", methods=["POST"])
def api_volume(guild_id):
    try:
        vol_input = float(request.json.get("volume", 100))

        async def _volume():
            discord_guild = bot.get_guild(int(guild_id))
            if not discord_guild:
                return {"error": "guild not found"}
            await _ensure_guild_initialized(discord_guild)
            g = guild_lib._guild_dict.get(int(guild_id))
            if not g:
                return {"error": "guild not initialized"}
            vol = max(0.0, min(200.0, vol_input))
            g.set_voice_volume(vol)
            vc = discord_guild.voice_client
            if vc and vc.is_playing() and vc.source:
                vc.source.volume = vol / 100.0
            return {"ok": True, "volume": vol}

        result = run_on_bot_loop(_volume())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/guild/<guild_id>/seek", methods=["POST"])
def api_seek(guild_id):
    try:
        seconds = int(request.json.get("position", 0))

        async def _seek():
            discord_guild = bot.get_guild(int(guild_id))
            if not discord_guild:
                return {"error": "guild not found"}
            await _ensure_guild_initialized(discord_guild)
            g = guild_lib._guild_dict.get(int(guild_id))
            if not g:
                return {"error": "guild not initialized"}
            pl = g.get_playlist()
            vc = discord_guild.voice_client
            if not vc or pl.is_empty():
                return {"error": "nothing playing"}

            current_audio = pl.get_audio(0)
            # Insert duplicate so play_next_from_guild doesn't advance
            pl.insert_audio(current_audio, 0)
            # Set seek offset — play_next_from_guild will use it
            _core._seek_offsets[int(guild_id)] = seconds
            # Stop triggers play_next_from_guild callback
            vc.stop()
            return {"ok": True, "position": seconds}

        result = run_on_bot_loop(_seek())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Favorites helpers ────────────────────────────────

def _fav_path(folder_name):
    return os.path.join(FAVORITES_PATH, f"{folder_name}.json")

def _load_fav(folder_name):
    path = _fav_path(folder_name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_fav(folder_name, data):
    os.makedirs(FAVORITES_PATH, exist_ok=True)
    with open(_fav_path(folder_name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _list_fav_folders():
    if not os.path.exists(FAVORITES_PATH):
        return []
    folders = []
    for f in sorted(os.listdir(FAVORITES_PATH)):
        if f.endswith(".json"):
            name = f[:-5]
            data = _load_fav(name)
            folders.append({"name": name, "count": len(data.get("songs", [])) if data else 0})
    return folders


@app.route("/api/favorites")
def api_favorites():
    return jsonify({"folders": _list_fav_folders()})


@app.route("/api/favorites/folder", methods=["POST"])
def api_fav_create_folder():
    name = request.json.get("name", "").strip()
    if not name:
        return jsonify({"error": "empty name"}), 400
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    if os.path.exists(_fav_path(name)):
        return jsonify({"error": "folder already exists"}), 409
    _save_fav(name, {"name": name, "songs": []})
    return jsonify({"ok": True, "name": name})


@app.route("/api/favorites/folder", methods=["DELETE"])
def api_fav_delete_folder():
    name = request.json.get("name", "").strip()
    path = _fav_path(name)
    if os.path.exists(path):
        os.remove(path)
    return jsonify({"ok": True})


@app.route("/api/favorites/<folder_name>")
def api_fav_get(folder_name):
    data = _load_fav(folder_name)
    if data is None:
        return jsonify({"error": "folder not found"}), 404
    return jsonify(data)


@app.route("/api/favorites/<folder_name>/add", methods=["POST"])
def api_fav_add_song(folder_name):
    data = _load_fav(folder_name)
    if data is None:
        return jsonify({"error": "folder not found"}), 404
    song = {
        "title": request.json.get("title", ""),
        "url": request.json.get("url", ""),
        "source": request.json.get("source", ""),
        "duration": request.json.get("duration", ""),
        "thumbnail": request.json.get("thumbnail", ""),
    }
    # Avoid duplicates by url
    if any(s["url"] == song["url"] for s in data["songs"]):
        return jsonify({"ok": True, "duplicate": True})
    data["songs"].append(song)
    _save_fav(folder_name, data)
    return jsonify({"ok": True, "count": len(data["songs"])})


@app.route("/api/favorites/<folder_name>/remove", methods=["POST"])
def api_fav_remove_song(folder_name):
    data = _load_fav(folder_name)
    if data is None:
        return jsonify({"error": "folder not found"}), 404
    url = request.json.get("url", "")
    data["songs"] = [s for s in data["songs"] if s["url"] != url]
    _save_fav(folder_name, data)
    return jsonify({"ok": True, "count": len(data["songs"])})


@app.route("/api/guild/<guild_id>/add-local", methods=["POST"])
def api_add_local_to_queue(guild_id):
    """Add an already-downloaded local file to a guild's playlist."""
    filename = request.json.get("filename", "").strip()
    if not filename:
        return jsonify({"error": "empty filename"}), 400
    filepath = os.path.join(DOWNLOAD_PATH, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "file not found"}), 404
    try:
        async def _add_local():
            import discord as _discord

            discord_guild = bot.get_guild(int(guild_id))
            if not discord_guild:
                return {"error": "guild not found"}
            await _ensure_guild_initialized(discord_guild)
            g = guild_lib._guild_dict.get(int(guild_id))
            if not g:
                return {"error": "guild not initialized"}
            pl = g.get_playlist()
            vc = discord_guild.voice_client

            # Derive title from filename (strip extension)
            title = os.path.splitext(filename)[0]
            duration = get_audio_duration(filepath)

            new_audio = audio_module.Audio(title, f"local_{filename}", "local", filename, DownloadType.UNKNOWN, filepath, duration)
            pl.append_audio(new_audio)

            if vc and not vc.is_playing() and not vc.is_paused() and len(pl) == 1:
                target = pl.get_audio(0)
                audio_lib_main.lock_audio(f"{discord_guild.id}_NOW_PLAYING", target)
                vc.play(
                    _discord.PCMVolumeTransformer(
                        _discord.FFmpegPCMAudio(executable=ffmpeg_path, source=target.get_path())
                    ),
                    after=lambda e: asyncio.run_coroutine_threadsafe(_core.play_next_from_guild(discord_guild), bot.loop)
                )
                vc.source.volume = g.get_voice_volume() / 100.0

            return {"ok": True, "title": title, "queue_length": len(pl)}

        result = run_on_bot_loop(_add_local())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/guild/<guild_id>/add", methods=["POST"])
def api_add_to_queue(guild_id):
    """Download audio and add it to a guild's playlist."""
    url = request.json.get("url", "").strip()
    source = request.json.get("source", "youtube")
    if not url:
        return jsonify({"error": "empty url"}), 400
    try:
        async def _add():
            import discord as _discord
            from zeta_bot import ytdlp as yt_mod, bilibili as bl_mod

            discord_guild = bot.get_guild(int(guild_id))
            if not discord_guild:
                return {"error": "guild not found"}
            await _ensure_guild_initialized(discord_guild)
            g = guild_lib._guild_dict.get(int(guild_id))
            if not g:
                return {"error": "guild not initialized"}
            pl = g.get_playlist()
            vc = discord_guild.voice_client

            if source == "bilibili":
                # Extract bvid from url
                import re
                bvid_match = re.search(r"(BV[\dA-Za-z]{10})", url)
                if not bvid_match:
                    return {"error": "invalid bilibili url"}
                bvid = bvid_match.group(1)
                info_result = await bl_mod.get_info(bvid)
                if not info_result:
                    return {"error": info_result.message}
                new_result = await audio_lib_main.download_bilibili(info_result.result, DownloadType.BILIBILI_SINGLE, 0)
            else:
                # YouTube / other yt-dlp sources
                info_result = await yt_mod.get_info(url)
                if not info_result:
                    return {"error": info_result.message}
                new_result = await audio_lib_main.download_ytdlp(url, info_result.result, DownloadType.YOUTUBE_SINGLE)
            if not new_result:
                return {"error": new_result.message}
            new_audio = new_result.result
            title = new_audio.get_title()

            # Add to guild playlist
            pl.append_audio(new_audio)

            # If nothing is playing and voice is connected, start playback
            if vc and not vc.is_playing() and not vc.is_paused():
                if len(pl) == 1:
                    target = pl.get_audio(0)
                    audio_lib_main.lock_audio(f"{discord_guild.id}_NOW_PLAYING", target)
                    vc.play(
                        _discord.PCMVolumeTransformer(
                            _discord.FFmpegPCMAudio(executable=ffmpeg_path, source=target.get_path())
                        ),
                        after=lambda e: asyncio.run_coroutine_threadsafe(_core.play_next_from_guild(discord_guild), bot.loop)
                    )
                    vc.source.volume = g.get_voice_volume() / 100.0

            return {"ok": True, "title": title, "queue_length": len(pl)}

        result = run_on_bot_loop(_add())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Login Template ───────────────────────────────────

LOGIN_TEMPLATE = r"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Zeta-Bot Login</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f0f0f;color:#e1e1e1;min-height:100vh;display:flex;align-items:center;justify-content:center}
.login-box{width:360px;background:#181818;border-radius:16px;padding:40px 32px;text-align:center;box-shadow:0 8px 32px rgba(0,0,0,.5)}
.login-box h1{font-size:1.5em;margin-bottom:6px;color:#fff}
.login-box h1 span{color:#ff4444}
.login-box p{font-size:12px;color:#666;margin-bottom:28px}
.login-box input{width:100%;padding:14px 16px;border-radius:10px;border:1px solid #333;background:#111;color:#fff;font-size:18px;text-align:center;letter-spacing:4px;outline:none;font-family:monospace;text-transform:uppercase;margin-bottom:16px}
.login-box input:focus{border-color:#ff4444}
.login-box input::placeholder{letter-spacing:1px;font-size:14px;text-transform:none}
.login-box button{width:100%;padding:14px;border-radius:10px;border:none;background:#ff4444;color:#fff;font-size:15px;cursor:pointer;font-weight:600;transition:background .2s}
.login-box button:hover{background:#e03030}
.login-box button:disabled{background:#555;cursor:wait}
.login-msg{margin-top:14px;font-size:13px;min-height:20px}
.login-msg.error{color:#ff7a7a}
.login-msg.ok{color:#7aff7a}
.login-hint{margin-top:20px;font-size:11px;color:#555;line-height:1.6}
</style></head><body>
<div class="login-box">
    <h1><span>Zeta</span>-Bot</h1>
    <p>Use /webauth on Discord to get your access code</p>
    <input id="code-input" type="text" maxlength="8" placeholder="Enter code" autofocus onkeydown="if(event.key==='Enter')doLogin()">
    <button id="login-btn" onclick="doLogin()">Login</button>
    <div class="login-msg" id="login-msg"></div>
    <div class="login-hint">Code is valid for 3 days. Ask the bot for a new one anytime.</div>
</div>
<script>
async function doLogin(){const code=document.getElementById('code-input').value.trim();if(!code)return;const btn=document.getElementById('login-btn'),msg=document.getElementById('login-msg');btn.disabled=true;btn.textContent='Verifying...';msg.className='login-msg';msg.textContent='';try{const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code})});const d=await r.json();if(d.ok){msg.className='login-msg ok';msg.textContent='Welcome, '+d.username+'!';setTimeout(()=>window.location.href='/',500);}else{msg.className='login-msg error';msg.textContent=d.error||'Login failed';}}catch(e){msg.className='login-msg error';msg.textContent='Connection error';}finally{btn.disabled=false;btn.textContent='Login';}}
</script></body></html>"""

# ── HTML Template ───────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Zeta-Bot Control Panel</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f0f0f;color:#e1e1e1;min-height:100vh;padding-bottom:85px}
.container{max-width:960px;margin:0 auto;padding:16px 20px}
h1{text-align:center;padding:14px 0 4px;font-size:1.5em;color:#fff}h1 span{color:#ff4444}
.subtitle{text-align:center;color:#666;font-size:11px;margin-bottom:14px}
.tabs{display:flex;gap:4px;margin-bottom:16px}
.tab{padding:8px 18px;cursor:pointer;border:none;background:none;color:#888;font-size:13px;border-bottom:2px solid #272727;transition:all .2s;white-space:nowrap;flex-shrink:0}
.tab:hover{color:#ccc}.tab.active{color:#fff;border-bottom-color:#ff4444}
.tab-content{display:none}.tab-content.active{display:block}
.input-row{display:flex;gap:8px;margin-bottom:12px}
.input-row input,.input-row select{padding:10px 12px;border-radius:8px;border:1px solid #333;background:#181818;color:#fff;font-size:14px;outline:none}
.input-row input{flex:1}.input-row input:focus{border-color:#ff4444}
.input-row select{min-width:100px;cursor:pointer}
.input-row button,.btn{padding:10px 22px;border-radius:8px;border:none;background:#ff4444;color:#fff;font-size:14px;cursor:pointer;white-space:nowrap}
.input-row button:hover,.btn:hover{background:#e03030}
.input-row button:disabled,.btn:disabled{background:#555;cursor:wait}
.result-item{display:flex;gap:10px;background:#181818;border-radius:10px;padding:10px;margin-bottom:7px;align-items:center;transition:background .2s}
.result-item:hover{background:#222}
.thumb{width:120px;min-width:120px;height:68px;border-radius:6px;object-fit:cover;background:#222}
.result-info{flex:1;min-width:0}
.result-title{font-size:13px;font-weight:500;margin-bottom:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.result-meta{font-size:11px;color:#888;display:flex;gap:6px;align-items:center}
.source-tag{display:inline-block;padding:1px 7px;border-radius:4px;font-size:10px;font-weight:600}
.source-tag.youtube{background:#cc0000;color:#fff}.source-tag.bilibili{background:#00a1d6;color:#fff}
.result-btns{display:flex;gap:4px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end}
.btn-sm{padding:5px 12px;border-radius:6px;border:none;font-size:11px;cursor:pointer;white-space:nowrap}
.btn-dl{background:#333;color:#ccc}.btn-dl:hover{background:#444;color:#fff}
.btn-add{background:#ff4444;color:#fff}.btn-add:hover{background:#e03030}
.btn-fav{background:none;border:1px solid #555;color:#aaa;font-size:13px;padding:4px 10px}.btn-fav:hover{border-color:#ff6b81;color:#ff6b81}
.btn-sm:disabled{background:#555;cursor:wait;color:#888}
.file-item{display:flex;justify-content:space-between;align-items:center;padding:9px 14px;background:#181818;border-radius:8px;margin-bottom:5px}
.file-item:hover{background:#222}
.file-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}
.file-size{color:#888;font-size:12px;margin:0 12px;white-space:nowrap}
.btn-file{padding:5px 14px;border-radius:6px;border:1px solid #444;background:none;color:#ddd;font-size:12px;cursor:pointer}
.btn-file:hover{border-color:#ff4444;color:#ff4444}
.status{padding:10px;margin:8px 0;border-radius:8px;font-size:13px}
.status.info{background:#1a2a3a;color:#7ab8ff}.status.error{background:#3a1a1a;color:#ff7a7a}.status.done{background:#1a3a1a;color:#7aff7a}
.progress-bar{height:4px;background:#333;border-radius:2px;margin-top:6px;overflow:hidden}
.progress-fill{height:100%;background:#ff4444;transition:width .3s}
.loading{color:#888;padding:20px;text-align:center}
.empty{color:#555;text-align:center;padding:24px;font-size:13px}
/* Bottom Bar */
.bottom-bar{position:fixed;bottom:0;left:0;right:0;height:76px;background:#181818;border-top:1px solid #272727;z-index:100;display:flex;flex-direction:column}
.bb-progress{position:relative;height:6px;background:#333;cursor:pointer;flex-shrink:0;transition:height .15s}
.bb-progress:hover{height:8px}
.bb-progress-fill{height:100%;background:#ff4444;border-radius:0;pointer-events:none;width:0%;transition:width .3s linear}
.bb-progress-thumb{position:absolute;top:50%;width:12px;height:12px;background:#fff;border-radius:50%;transform:translate(-50%,-50%);left:0%;opacity:0;pointer-events:none;transition:opacity .15s}
.bb-progress:hover .bb-progress-thumb{opacity:1}
.bb-progress.seeking .bb-progress-fill{transition:none}
.bb-progress.seeking .bb-progress-thumb{opacity:1}
.bb-content{display:flex;align-items:center;padding:0 20px;flex:1}
.bb-left{display:flex;align-items:center;gap:10px;flex:1;min-width:0}
.bb-now-title{font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:280px}
.bb-now-meta{font-size:11px;color:#888}
.bb-center{display:flex;align-items:center;gap:10px}
.bb-time{font-size:11px;color:#888;min-width:36px;text-align:center;font-variant-numeric:tabular-nums}
.bb-btn{width:36px;height:36px;border-radius:50%;border:none;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;transition:background .2s}
.bb-play{background:#ff4444;color:#fff}.bb-play:hover{background:#e03030}
.bb-skip{background:#333;color:#fff}.bb-skip:hover{background:#444}
.bb-right{display:flex;align-items:center;gap:8px;flex:1;justify-content:flex-end}
.bb-vol{display:flex;align-items:center;gap:5px}
.bb-vol input[type=range]{width:70px;accent-color:#ff4444}
.bb-vol-label{font-size:11px;color:#888;min-width:30px}
.bb-icon-btn{width:36px;height:36px;border-radius:6px;border:1px solid #444;background:none;color:#ccc;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;transition:all .2s}
.bb-icon-btn:hover,.bb-icon-btn.active{border-color:#ff4444;color:#ff4444}
.bb-guild-sel{padding:6px 8px;border-radius:6px;border:1px solid #333;background:#111;color:#ccc;font-size:12px;max-width:140px;outline:none;cursor:pointer}
/* Drawer */
.playlist-drawer{position:fixed;bottom:72px;right:0;width:380px;max-height:calc(100vh - 82px);background:#141414;border-left:1px solid #272727;border-top:1px solid #272727;border-radius:12px 0 0 0;display:none;flex-direction:column;z-index:99;box-shadow:-4px -2px 20px rgba(0,0,0,.4)}
.playlist-drawer.open{display:flex}
.pd-header{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;border-bottom:1px solid #222}
.pd-title{font-size:14px;font-weight:600}
.pd-close{background:none;border:none;color:#888;font-size:18px;cursor:pointer;padding:4px}.pd-close:hover{color:#fff}
.pd-body{flex:1;overflow-y:auto;padding:8px 12px}
.pd-summary{display:flex;justify-content:space-between;font-size:11px;color:#666;padding:4px 4px 8px}
.pl-item{display:flex;align-items:center;gap:8px;padding:7px 10px;background:#181818;border-radius:6px;margin-bottom:3px;transition:background .15s,transform .15s,box-shadow .15s;user-select:none}
.pl-item:hover{background:#1f1f1f}.pl-item.current{background:#1a1a2e;border-left:3px solid #ff4444}
.pl-item.dragging{opacity:.5;transform:scale(.97)}.pl-item.drag-over{box-shadow:0 -2px 0 #ff4444 inset;background:#1c1c2e}
.pl-drag{cursor:grab;color:#555;font-size:14px;padding:0 2px;display:flex;align-items:center}.pl-drag:active{cursor:grabbing}
.pl-index{color:#666;font-size:11px;min-width:20px;text-align:center}
.pl-title{flex:1;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pl-duration{color:#888;font-size:11px;min-width:40px;text-align:right}
.pl-actions{display:flex;gap:3px}
.pl-btn{width:24px;height:24px;border-radius:4px;border:none;background:#272727;color:#999;cursor:pointer;font-size:12px;display:flex;align-items:center;justify-content:center}
.pl-btn:hover{background:#383838;color:#fff}.pl-btn.danger:hover{background:#4a1a1a;color:#ff4444}
/* Favorites */
.fav-layout{display:flex;gap:14px;min-height:300px}
.fav-sidebar{width:200px;flex-shrink:0}
.fav-main{flex:1;min-width:0}
.fav-folder{padding:9px 12px;border-radius:6px;cursor:pointer;margin-bottom:3px;font-size:13px;display:flex;justify-content:space-between;align-items:center;background:#181818;transition:background .15s}
.fav-folder:hover{background:#222}.fav-folder.active{background:#1a1a2e;border-left:3px solid #ff4444}
.fav-folder-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fav-folder-count{color:#666;font-size:11px;flex-shrink:0;margin-left:6px}
.fav-folder-del{background:none;border:none;color:#555;cursor:pointer;font-size:14px;padding:0 2px;margin-left:4px}.fav-folder-del:hover{color:#ff4444}
.fav-song{display:flex;align-items:center;gap:8px;padding:8px 10px;background:#181818;border-radius:6px;margin-bottom:4px;transition:background .15s}
.fav-song:hover{background:#222}
.fav-song-info{flex:1;min-width:0}
.fav-song-title{font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fav-song-meta{font-size:10px;color:#888;display:flex;gap:6px;align-items:center;margin-top:2px}
.fav-song-btns{display:flex;gap:4px;flex-shrink:0}
/* Fav picker popup */
.fav-picker{position:absolute;bottom:100%;right:0;background:#1e1e1e;border:1px solid #333;border-radius:8px;padding:6px;min-width:180px;box-shadow:0 -4px 16px rgba(0,0,0,.5);z-index:200;display:none}
.fav-picker.show{display:block}
.fav-picker-item{padding:7px 10px;border-radius:5px;cursor:pointer;font-size:12px;transition:background .15s}
.fav-picker-item:hover{background:#333}
.fav-picker-new{display:flex;gap:4px;padding:4px 0;margin-top:4px;border-top:1px solid #333}
.fav-picker-new input{flex:1;padding:5px 8px;border-radius:5px;border:1px solid #333;background:#111;color:#fff;font-size:12px;outline:none}
.fav-picker-new button{padding:5px 10px;border-radius:5px;border:none;background:#ff4444;color:#fff;font-size:11px;cursor:pointer}
</style></head><body>
<div class="container">
    <h1><span>Zeta</span>-Bot Control Panel</h1>
    <p class="subtitle">Search &bull; Favorites &bull; Download &bull; Playback Control &bull; <a href="/logout" style="color:#888;text-decoration:none" onmouseover="this.style.color='#ff4444'" onmouseout="this.style.color='#888'">Logout</a></p>
    <div class="tabs">
        <button class="tab active" onclick="switchTab('search')">Search</button>
        <button class="tab" onclick="switchTab('favorites')">Favorites</button>
        <button class="tab" onclick="switchTab('url')">URL Download</button>
        <button class="tab" onclick="switchTab('files')">Downloads</button>
    </div>
    <div id="tab-search" class="tab-content active">
        <div class="input-row">
            <input id="search-input" type="text" placeholder="Search YouTube / Bilibili..." onkeydown="if(event.key==='Enter')doSearch()">
            <select id="search-source"><option value="all">All</option><option value="youtube">YouTube</option><option value="bilibili">Bilibili</option></select>
            <button id="search-btn" onclick="doSearch()">Search</button>
        </div>
        <div id="search-results"></div>
    </div>
    <div id="tab-favorites" class="tab-content">
        <div class="fav-layout">
            <div class="fav-sidebar">
                <div class="input-row" style="margin-bottom:8px"><input id="fav-new-name" type="text" placeholder="New folder..." style="font-size:12px;padding:8px" onkeydown="if(event.key==='Enter')createFavFolder()"><button onclick="createFavFolder()" style="padding:8px 14px;font-size:12px">+</button></div>
                <div id="fav-folder-list"></div>
            </div>
            <div class="fav-main" id="fav-main"><div class="empty">Select or create a folder</div></div>
        </div>
    </div>
    <div id="tab-url" class="tab-content">
        <div class="input-row"><input id="url-input" type="text" placeholder="Paste YouTube or Bilibili URL..." onkeydown="if(event.key==='Enter')doUrlDownload()"><button id="url-btn" onclick="doUrlDownload()">Download</button></div>
        <div id="url-status"></div>
    </div>
    <div id="tab-files" class="tab-content">
        <div id="file-list"><div class="empty">Loading...</div></div>
    </div>
</div>
<div class="bottom-bar">
    <div class="bb-progress" id="bb-progress" onmousedown="seekStart(event)" ontouchstart="seekStart(event)">
        <div class="bb-progress-fill" id="bb-progress-fill"></div>
        <div class="bb-progress-thumb" id="bb-progress-thumb"></div>
    </div>
    <div class="bb-content">
        <div class="bb-left"><div><div class="bb-now-title" id="bb-title">Not connected</div><div class="bb-now-meta" id="bb-meta"></div></div></div>
        <div class="bb-center">
            <span class="bb-time" id="bb-time-cur">0:00</span>
            <button class="bb-btn bb-play" id="bb-play-btn" onclick="togglePause()" title="Play/Pause">&#9654;</button>
            <button class="bb-btn bb-skip" onclick="skipCurrent()" title="Skip">&#9197;</button>
            <span class="bb-time" id="bb-time-total">0:00</span>
        </div>
        <div class="bb-right">
            <div class="bb-vol"><span style="font-size:13px">&#128266;</span><input type="range" min="0" max="200" value="100" id="bb-vol-slider" onchange="setVolume(this.value)" oninput="document.getElementById('bb-vol-label').textContent=this.value+'%'"><span class="bb-vol-label" id="bb-vol-label">100%</span></div>
            <select class="bb-guild-sel" id="guild-select" onchange="onGuildChange()"><option value="">Server...</option></select>
            <button class="bb-icon-btn" id="bb-list-btn" onclick="toggleDrawer()" title="Queue">&#9776;</button>
        </div>
    </div>
</div>
<div class="playlist-drawer" id="playlist-drawer">
    <div class="pd-header"><span class="pd-title">Queue</span><button class="pd-close" onclick="toggleDrawer()">&#10005;</button></div>
    <div class="pd-body" id="pd-body"><div class="empty">Select a server</div></div>
</div>
<script>
let currentGuildId=null,playerPoll=null,drawerOpen=false,currentFavFolder=null,favFolders=[];
let lastPosition=0,lastTrackDur=0,lastIsPlaying=false,lastUpdateTime=0,isSeeking=false;
document.addEventListener('DOMContentLoaded',()=>{loadGuilds();setInterval(updateProgressLocal,250);});
document.addEventListener('click',e=>{if(!e.target.closest('.fav-picker')&&!e.target.closest('.btn-fav')){document.querySelectorAll('.fav-picker').forEach(p=>p.classList.remove('show'));}});
function switchTab(name){document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));document.getElementById('tab-'+name).classList.add('active');event.target.classList.add('active');if(name==='files')loadFiles();if(name==='favorites')loadFavFolders();}
function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}
// ── Guild ──
async function loadGuilds(){try{const r=await fetch('/api/guilds');const d=await r.json();if(d.error)return;const sel=document.getElementById('guild-select');const prev=sel.value;sel.innerHTML='<option value="">Server...</option>';d.guilds.forEach(g=>{const l=g.voice_connected?`${g.name} (${g.voice_channel})`:g.name;sel.innerHTML+=`<option value="${g.id}" ${g.id===prev?'selected':''}>${esc(l)}</option>`;});if(!prev&&d.guilds.length>0){const c=d.guilds.find(g=>g.voice_connected);sel.value=c?c.id:d.guilds[0].id;}onGuildChange();}catch(e){}}
function onGuildChange(){const gid=document.getElementById('guild-select').value;if(playerPoll){clearInterval(playerPoll);playerPoll=null;}currentGuildId=gid||null;if(currentGuildId){refreshPlayer();playerPoll=setInterval(refreshPlayer,3000);}else{document.getElementById('bb-title').textContent='Not connected';document.getElementById('bb-meta').textContent='';document.getElementById('pd-body').innerHTML='<div class="empty">Select a server</div>';}}
// ── Player Bar ──
async function refreshPlayer(){if(!currentGuildId)return;try{const r=await fetch(`/api/guild/${currentGuildId}/playlist`);const pl=await r.json();if(pl.error)return;const cur=pl.items.length>0?pl.items[0]:null;document.getElementById('bb-title').textContent=cur?cur.title:'Nothing playing';document.getElementById('bb-meta').textContent=pl.is_playing?'Playing':(pl.is_paused?'Paused':'Idle');document.getElementById('bb-play-btn').innerHTML=(pl.is_playing?'&#10074;&#10074;':'&#9654;');document.getElementById('bb-vol-slider').value=pl.volume;document.getElementById('bb-vol-label').textContent=Math.round(pl.volume)+'%';lastPosition=pl.position||0;lastTrackDur=pl.track_duration||0;lastIsPlaying=pl.is_playing;lastUpdateTime=Date.now();document.getElementById('bb-time-total').textContent=fmtTime(lastTrackDur);if(!isSeeking)updateProgressBar(lastPosition,lastTrackDur);if(drawerOpen)renderDrawerPlaylist(pl);}catch(e){}}
function fmtTime(s){if(!s||s<0)return '0:00';const m=Math.floor(s/60);const sec=Math.floor(s%60);return m+':'+(sec<10?'0':'')+sec;}
function updateProgressBar(pos,total){const pct=total>0?Math.min(pos/total*100,100):0;document.getElementById('bb-progress-fill').style.width=pct+'%';document.getElementById('bb-progress-thumb').style.left=pct+'%';document.getElementById('bb-time-cur').textContent=fmtTime(pos);}
function updateProgressLocal(){if(isSeeking||!lastIsPlaying||!lastTrackDur)return;const elapsed=(Date.now()-lastUpdateTime)/1000;const pos=Math.min(lastPosition+elapsed,lastTrackDur);updateProgressBar(pos,lastTrackDur);}
function toggleDrawer(){drawerOpen=!drawerOpen;document.getElementById('playlist-drawer').classList.toggle('open',drawerOpen);document.getElementById('bb-list-btn').classList.toggle('active',drawerOpen);if(drawerOpen)refreshPlayer();}
function renderDrawerPlaylist(pl){const body=document.getElementById('pd-body');let h=`<div class="pd-summary"><span>${pl.length} tracks</span><span>${pl.total_duration}</span></div>`;if(!pl.items.length){h+='<div class="empty">Queue is empty</div>';}else{h+='<div id="pl-drag-list">';pl.items.forEach(i=>{h+=`<div class="pl-item${i.is_current?' current':''}" draggable="true" data-index="${i.index}"><span class="pl-drag" title="Drag to reorder">&#9776;</span><span class="pl-index">${i.index}</span><span class="pl-title" title="${esc(i.title)}">${esc(i.title)}</span><span class="pl-duration">${i.duration}</span><div class="pl-actions"><button class="pl-btn danger" onclick="removeTrack(${i.index})" title="Remove">\u2715</button></div></div>`;});h+='</div>';}body.innerHTML=h;initDragAndDrop();}
// ── Drag & Drop ──
let dragSrcIndex=null;
function initDragAndDrop(){const list=document.getElementById('pl-drag-list');if(!list)return;list.querySelectorAll('.pl-item').forEach(item=>{item.addEventListener('dragstart',onDragStart);item.addEventListener('dragend',onDragEnd);item.addEventListener('dragover',onDragOver);item.addEventListener('dragenter',onDragEnter);item.addEventListener('dragleave',onDragLeave);item.addEventListener('drop',onDrop);});}
function onDragStart(e){dragSrcIndex=parseInt(this.dataset.index);this.classList.add('dragging');e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',dragSrcIndex);}
function onDragEnd(){this.classList.remove('dragging');document.querySelectorAll('.pl-item').forEach(el=>el.classList.remove('drag-over'));}
function onDragOver(e){e.preventDefault();e.dataTransfer.dropEffect='move';}
function onDragEnter(e){e.preventDefault();this.classList.add('drag-over');}
function onDragLeave(){this.classList.remove('drag-over');}
function onDrop(e){e.preventDefault();this.classList.remove('drag-over');const to=parseInt(this.dataset.index);if(dragSrcIndex&&dragSrcIndex!==to)moveTrack(dragSrcIndex,to);dragSrcIndex=null;}
// ── Controls ──
async function togglePause(){if(!currentGuildId)return;await fetch(`/api/guild/${currentGuildId}/pause`,{method:'POST'});setTimeout(refreshPlayer,300);}
async function skipCurrent(){if(!currentGuildId)return;await fetch(`/api/guild/${currentGuildId}/skip`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});setTimeout(refreshPlayer,500);}
async function removeTrack(i){if(!currentGuildId)return;await fetch(`/api/guild/${currentGuildId}/skip`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index:i})});setTimeout(refreshPlayer,500);}
async function moveTrack(f,t){if(!currentGuildId)return;await fetch(`/api/guild/${currentGuildId}/move`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:f,to:t})});setTimeout(refreshPlayer,300);}
async function setVolume(v){if(!currentGuildId)return;await fetch(`/api/guild/${currentGuildId}/volume`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({volume:parseFloat(v)})});}
// ── Seek ──
function seekStart(e){if(!currentGuildId||!lastTrackDur)return;e.preventDefault();isSeeking=true;document.getElementById('bb-progress').classList.add('seeking');seekUpdate(e);document.addEventListener('mousemove',seekUpdate);document.addEventListener('mouseup',seekEnd);document.addEventListener('touchmove',seekUpdate);document.addEventListener('touchend',seekEnd);}
function seekUpdate(e){const bar=document.getElementById('bb-progress');const rect=bar.getBoundingClientRect();const clientX=e.touches?e.touches[0].clientX:e.clientX;const pct=Math.max(0,Math.min(1,(clientX-rect.left)/rect.width));const pos=Math.floor(pct*lastTrackDur);updateProgressBar(pos,lastTrackDur);}
function seekEnd(e){document.removeEventListener('mousemove',seekUpdate);document.removeEventListener('mouseup',seekEnd);document.removeEventListener('touchmove',seekUpdate);document.removeEventListener('touchend',seekEnd);const bar=document.getElementById('bb-progress');bar.classList.remove('seeking');const rect=bar.getBoundingClientRect();const clientX=e.changedTouches?e.changedTouches[0].clientX:e.clientX;const pct=Math.max(0,Math.min(1,(clientX-rect.left)/rect.width));const pos=Math.floor(pct*lastTrackDur);isSeeking=false;lastPosition=pos;lastUpdateTime=Date.now();fetch(`/api/guild/${currentGuildId}/seek`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({position:pos})}).then(()=>setTimeout(refreshPlayer,500));}
// ── Search ──
async function doSearch(){const q=document.getElementById('search-input').value.trim();const src=document.getElementById('search-source').value;if(!q)return;const btn=document.getElementById('search-btn'),box=document.getElementById('search-results');btn.disabled=true;btn.textContent='Searching...';box.innerHTML='<div class="loading">Searching...</div>';try{const r=await fetch('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q,source:src})});const d=await r.json();if(d.error){box.innerHTML=`<div class="status error">${esc(d.error)}</div>`;return;}if(!d.results.length){box.innerHTML='<div class="empty">No results found</div>';return;}box.innerHTML=d.results.map(r=>renderResultItem(r)).join('');}catch(e){box.innerHTML=`<div class="status error">${e}</div>`;}finally{btn.disabled=false;btn.textContent='Search';}}
function renderResultItem(r){const songData=btoa(unescape(encodeURIComponent(JSON.stringify({title:r.title,url:r.url,source:r.source,duration:r.duration,thumbnail:r.thumbnail}))));return `<div class="result-item"><img class="thumb" src="${esc(r.thumbnail)}" onerror="this.style.visibility='hidden'" alt=""><div class="result-info"><div class="result-title" title="${esc(r.title)}">${esc(r.title)}</div><div class="result-meta"><span class="source-tag ${r.source}">${r.source==='youtube'?'YouTube':'Bilibili'}</span><span>${r.duration}</span></div></div><div class="result-btns"><button class="btn-sm btn-add" onclick="addToQueue('${esc(r.url)}','${r.source}',this)" title="Add to queue">\u25B6 Add</button><button class="btn-sm btn-fav" onclick="showFavPicker(this,'${songData}')" title="Add to favorites">\u2661</button><button class="btn-sm btn-dl" onclick="startDownload('${esc(r.url)}',this)" title="Download">\u2B07</button></div></div>`;}
// ── Add to Queue ──
async function addToQueue(url,source,btn){if(!currentGuildId){alert('Select a server first');return;}if(btn){btn.disabled=true;btn.textContent='Adding...';}try{const r=await fetch(`/api/guild/${currentGuildId}/add`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url,source})});const d=await r.json();if(d.error){if(btn){btn.textContent='Error';btn.style.background='#888';}return;}if(btn){btn.textContent=`#${d.queue_length}`;btn.style.background='#2a8a2a';}setTimeout(refreshPlayer,500);}catch(e){if(btn){btn.textContent='Error';btn.style.background='#888';}}}
// ── Fav Picker (inline popup on search results) ──
async function showFavPicker(btn,songDataB64){document.querySelectorAll('.fav-picker').forEach(p=>p.remove());const song=JSON.parse(decodeURIComponent(escape(atob(songDataB64))));const wrap=btn.closest('.result-btns');const picker=document.createElement('div');picker.className='fav-picker show';picker.style.position='absolute';let h='';try{const r=await fetch('/api/favorites');const d=await r.json();d.folders.forEach(f=>{h+=`<div class="fav-picker-item" onclick="addSongToFav('${esc(f.name)}',this)" data-song='${songDataB64}'>${esc(f.name)} <span style="color:#666;font-size:10px">(${f.count})</span></div>`;});}catch(e){}h+=`<div class="fav-picker-new"><input type="text" placeholder="New folder..." id="fp-new-input" onkeydown="if(event.key==='Enter')fpCreateAndAdd(this,'${songDataB64}')"><button onclick="fpCreateAndAdd(this.previousElementSibling,'${songDataB64}')">+</button></div>`;picker.innerHTML=h;wrap.style.position='relative';wrap.appendChild(picker);}
async function addSongToFav(folder,el){const songDataB64=el.dataset.song;const song=JSON.parse(decodeURIComponent(escape(atob(songDataB64))));try{const r=await fetch(`/api/favorites/${encodeURIComponent(folder)}/add`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(song)});const d=await r.json();if(d.duplicate){el.textContent='\u2713 exists';}else{el.textContent='\u2713 added';}el.style.color='#7aff7a';setTimeout(()=>{document.querySelectorAll('.fav-picker').forEach(p=>p.remove());},800);}catch(e){}}
async function fpCreateAndAdd(input,songDataB64){const name=input.value.trim();if(!name)return;await fetch('/api/favorites/folder',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});const song=JSON.parse(decodeURIComponent(escape(atob(songDataB64))));await fetch(`/api/favorites/${encodeURIComponent(name)}/add`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(song)});document.querySelectorAll('.fav-picker').forEach(p=>p.remove());}
// ── Favorites Tab ──
async function loadFavFolders(){try{const r=await fetch('/api/favorites');const d=await r.json();favFolders=d.folders;renderFavSidebar();}catch(e){}}
function renderFavSidebar(){const box=document.getElementById('fav-folder-list');if(!favFolders.length){box.innerHTML='<div class="empty" style="padding:12px;font-size:12px">No folders yet</div>';return;}box.innerHTML=favFolders.map(f=>`<div class="fav-folder${currentFavFolder===f.name?' active':''}" onclick="selectFavFolder('${esc(f.name)}')"><span class="fav-folder-name">${esc(f.name)}</span><span><span class="fav-folder-count">${f.count}</span><button class="fav-folder-del" onclick="event.stopPropagation();deleteFavFolder('${esc(f.name)}')" title="Delete">\u2715</button></span></div>`).join('');}
async function createFavFolder(){const input=document.getElementById('fav-new-name');const name=input.value.trim();if(!name)return;await fetch('/api/favorites/folder',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});input.value='';await loadFavFolders();selectFavFolder(name);}
async function deleteFavFolder(name){if(!confirm(`Delete folder "${name}"?`))return;await fetch('/api/favorites/folder',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});if(currentFavFolder===name){currentFavFolder=null;document.getElementById('fav-main').innerHTML='<div class="empty">Select or create a folder</div>';}await loadFavFolders();}
async function selectFavFolder(name){currentFavFolder=name;renderFavSidebar();try{const r=await fetch(`/api/favorites/${encodeURIComponent(name)}`);const d=await r.json();if(d.error){document.getElementById('fav-main').innerHTML=`<div class="status error">${esc(d.error)}</div>`;return;}renderFavSongs(d);}catch(e){}}
function renderFavSongs(data){const box=document.getElementById('fav-main');const hdr=(cnt)=>`<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><h3 style="font-size:15px;font-weight:600">${esc(data.name)}${cnt?` <span style="font-size:12px;color:#888">(${cnt})</span>`:''}</h3>${currentGuildId?`<button class="btn" style="padding:7px 16px;font-size:12px" onclick="addAllFavToQueue()">&#9654; Play All</button>`:''}</div>`;if(!data.songs.length){box.innerHTML=hdr(0)+'<div class="empty">No songs in this folder</div>';return;}let h=hdr(data.songs.length);data.songs.forEach(s=>{const isLocal=s.source==='local';const srcLabel=s.source==='youtube'?'YT':(s.source==='bilibili'?'BL':'Local');const playBtn=isLocal?`<button class="btn-sm btn-add" onclick="addLocalToQueue('${esc(s.url)}',this)" title="Add to queue">\u25B6</button>`:`<button class="btn-sm btn-add" onclick="addToQueue('${esc(s.url)}','${s.source}',this)" title="Add to queue">\u25B6</button>`;const dlBtn=isLocal?'':`<button class="btn-sm btn-dl" onclick="startDownload('${esc(s.url)}',this)" title="Download">\u2B07</button>`;h+=`<div class="fav-song"><div class="fav-song-info"><div class="fav-song-title" title="${esc(s.title)}">${esc(s.title)}</div><div class="fav-song-meta"><span class="source-tag ${s.source}" style="${isLocal?'background:#555':''}">${srcLabel}</span><span>${s.duration||''}</span></div></div><div class="fav-song-btns">${playBtn}${dlBtn}<button class="pl-btn danger" onclick="removeFavSong('${esc(s.url)}')" title="Remove">\u2715</button></div></div>`;});box.innerHTML=h;}
async function removeFavSong(url){if(!currentFavFolder)return;await fetch(`/api/favorites/${encodeURIComponent(currentFavFolder)}/remove`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});await selectFavFolder(currentFavFolder);await loadFavFolders();}
async function addAllFavToQueue(){if(!currentGuildId||!currentFavFolder)return;try{const r=await fetch(`/api/favorites/${encodeURIComponent(currentFavFolder)}`);const d=await r.json();for(const s of d.songs){if(s.source==='local'){await fetch(`/api/guild/${currentGuildId}/add-local`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:s.url})});}else{await fetch(`/api/guild/${currentGuildId}/add`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:s.url,source:s.source})});}}setTimeout(refreshPlayer,500);}catch(e){}}
// ── Download ──
function startDownload(url,btn){if(btn){btn.disabled=true;btn.textContent='...';}fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})}).then(r=>r.json()).then(d=>{if(d.error){if(btn)btn.textContent='Err';return;}if(btn)btn.textContent='0%';pollDl(d.task_id,btn);}).catch(()=>{if(btn)btn.textContent='Err';});}
function pollDl(tid,btn){const iv=setInterval(async()=>{try{const r=await fetch(`/api/status/${tid}`);const d=await r.json();if(d.status==='downloading'){if(btn)btn.textContent=d.progress||'...';}else if(d.status==='done'){clearInterval(iv);if(btn){btn.textContent='\u2713';btn.style.background='#2a8a2a';}}else if(d.status==='error'){clearInterval(iv);if(btn){btn.textContent='Err';btn.style.background='#888';}}}catch(e){clearInterval(iv);}},1000);}
async function doUrlDownload(){const url=document.getElementById('url-input').value.trim();if(!url)return;const btn=document.getElementById('url-btn'),box=document.getElementById('url-status');btn.disabled=true;btn.textContent='Starting...';box.innerHTML='<div class="status info">Starting...<div class="progress-bar"><div class="progress-fill" id="url-progress" style="width:0%"></div></div></div>';try{const r=await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});const d=await r.json();if(d.error){box.innerHTML=`<div class="status error">${esc(d.error)}</div>`;btn.disabled=false;btn.textContent='Download';return;}const iv=setInterval(async()=>{const sr=await fetch(`/api/status/${d.task_id}`);const sd=await sr.json();const pb=document.getElementById('url-progress');if(sd.status==='downloading'){btn.textContent=sd.progress||'...';if(pb)pb.style.width=sd.progress||'0%';}else if(sd.status==='done'){clearInterval(iv);box.innerHTML=`<div class="status done">Done: ${esc(sd.title)}</div>`;btn.textContent='Download';btn.disabled=false;}else if(sd.status==='error'){clearInterval(iv);box.innerHTML=`<div class="status error">${esc(sd.error)}</div>`;btn.textContent='Download';btn.disabled=false;}},1000);}catch(e){box.innerHTML=`<div class="status error">${e}</div>`;btn.disabled=false;btn.textContent='Download';}}
// ── Files ──
async function loadFiles(){const box=document.getElementById('file-list');try{const r=await fetch('/api/files');const d=await r.json();if(!d.files.length){box.innerHTML='<div class="empty">No files yet</div>';return;}box.innerHTML=d.files.map(f=>{const title=f.name.replace(/\.[^.]+$/,'');const songData=btoa(unescape(encodeURIComponent(JSON.stringify({title:title,url:'',source:'local',duration:f.duration||'',thumbnail:''}))));return `<div class="file-item"><span class="file-name" title="${esc(f.name)}">${esc(f.name)}</span><span class="file-size" style="min-width:90px;text-align:right">${f.duration||''} &bull; ${f.size}</span><div style="display:flex;gap:4px;flex-shrink:0"><button class="btn-sm btn-add" onclick="addLocalToQueue('${esc(f.name)}',this)" title="Add to queue" style="padding:4px 10px">\u25B6</button><button class="btn-sm btn-fav" onclick="showFileFavPicker(this,'${songData}','${esc(f.name)}')" title="Add to favorites" style="padding:3px 8px">\u2661</button><a href="/files/${encodeURIComponent(f.name)}"><button class="btn-file">Save</button></a></div></div>`;}).join('');}catch(e){box.innerHTML=`<div class="status error">${e}</div>`;}}
async function addLocalToQueue(filename,btn){if(!currentGuildId){alert('Select a server first');return;}if(btn){btn.disabled=true;btn.textContent='...';}try{const r=await fetch(`/api/guild/${currentGuildId}/add-local`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename})});const d=await r.json();if(d.error){if(btn){btn.textContent='Err';btn.style.background='#888';}return;}if(btn){btn.textContent=`#${d.queue_length}`;btn.style.background='#2a8a2a';}setTimeout(refreshPlayer,500);}catch(e){if(btn){btn.textContent='Err';btn.style.background='#888';}}}
function showFileFavPicker(btn,songDataB64,filename){document.querySelectorAll('.fav-picker').forEach(p=>p.remove());const wrap=btn.parentElement;const picker=document.createElement('div');picker.className='fav-picker show';picker.style.position='absolute';picker.style.bottom='100%';picker.style.right='0';fetch('/api/favorites').then(r=>r.json()).then(d=>{let h='';d.folders.forEach(f=>{h+=`<div class="fav-picker-item" onclick="addFileFav('${esc(f.name)}','${songDataB64}','${esc(filename)}',this)">${esc(f.name)} <span style="color:#666;font-size:10px">(${f.count})</span></div>`;});h+=`<div class="fav-picker-new"><input type="text" placeholder="New folder..." onkeydown="if(event.key==='Enter')fpCreateAndAddFile(this,'${songDataB64}','${esc(filename)}')"><button onclick="fpCreateAndAddFile(this.previousElementSibling,'${songDataB64}','${esc(filename)}')">+</button></div>`;picker.innerHTML=h;wrap.style.position='relative';wrap.appendChild(picker);});}
async function addFileFav(folder,songDataB64,filename,el){const song=JSON.parse(decodeURIComponent(escape(atob(songDataB64))));song.url=filename;song.source='local';try{const r=await fetch(`/api/favorites/${encodeURIComponent(folder)}/add`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(song)});const d=await r.json();el.textContent=d.duplicate?'\u2713 exists':'\u2713 added';el.style.color='#7aff7a';setTimeout(()=>{document.querySelectorAll('.fav-picker').forEach(p=>p.remove());},800);}catch(e){}}
async function fpCreateAndAddFile(input,songDataB64,filename){const name=input.value.trim();if(!name)return;await fetch('/api/favorites/folder',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});const song=JSON.parse(decodeURIComponent(escape(atob(songDataB64))));song.url=filename;song.source='local';await fetch(`/api/favorites/${encodeURIComponent(name)}/add`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(song)});document.querySelectorAll('.fav-picker').forEach(p=>p.remove());}
</script></body></html>"""
