# Zeta Discord Bot
[中文](../README.md) | English  

A Discord bot built with Pycord  
The author currently programs as a hobby. Please bear with any unconventional practices; feedback and suggestions are welcome.  

The bot currently supports Chinese only  

Table of contents
------------------------
- [Core Features](#core-features)
- [Run](#run)
- [Web Control Panel and Monitoring](#web-control-panel-and-monitoring)
- [NetEase Cloud Music and QQ Music](#netease-cloud-music-and-qq-music)
- [(Optional) Using go-music-api](#optional-using-go-music-api)

## Core Features
- Plays audio from Bilibili, YouTube, NetEase Cloud Music and QQ Music in Discord voice channels (built in, no extra service to deploy)
- Plays audio from YouTube in Discord voice channels
- Supports searching for and playing content from Bilibili or YouTube directly within Discord channels
- Interactive playlists (sequential / repeat one / repeat all / shuffle, previous track, playback progress)
- Web control panel and monitoring dashboard: live status, playback control, search, audio library, favorites and logs

![Demo_Play](Demo_Play.gif)

![Demo_Playlist](Demo_Playlist.gif)
![Demo_List](Demo_List.gif)

## Run
**Please use Python 3.10–3.13**

### Downloading the Source Code and Installing Dependencies
Download the source code for the latest version from **[Releases](https://github.com/31Zeta/Zeta-DiscordBot/releases)** and extract it.  
  
Run the following command in the root directory of the extracted source code to install the dependencies:  
```
pip install -r requirements.txt
```

On Linux, you also need to install:  
```
sudo apt install libopus0
```

### Installing or Linking FFmpeg
On Windows, visit the [FFmpeg website](https://ffmpeg.org/download.html) to obtain ffmpeg.exe, or [direct download](https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z) and extract ffmpeg.exe from the archive's bin folder.  
  
On Linux, you can use the ffmpeg bundled in the bin folder or obtain the latest version from the [FFmpeg website](https://ffmpeg.org/download.html).  

Place the extracted ffmpeg file in the repository's bin folder.

### Starting the Bot
Run the following command to start the bot:  
```
python main.py
```

Follow the prompts to complete the setup, and keep the window open to ensure the bot continues running.  
Consider using a daemon to prevent the bot from shutting down unexpectedly.  

### Changing Settings
To change the settings, start the bot with the following command (version 0.7.0 and later):
```
python main.py --mode=setting
```

### [Optional] yt-dlp Configuration
If you need the bot's YouTube features, enabling a JavaScript runtime for `yt-dlp-ejs` is recommended.
`yt-dlp-ejs` is already included through `yt-dlp[default]` in `requirements.txt` and will be installed automatically when you install the dependencies. For guidance on choosing and installing a runtime, see [Step 1: Install a supported JavaScript Runtime](https://github.com/yt-dlp/yt-dlp/wiki/EJS#step-1-install-a-supported-javascript-runtime).  

`configs/ytdlp_config.json` is created on first start:
| Option | Description |
| --- | --- |
| `cookie_file` | Netscape-format cookie file (default `./configs/cookies.txt`), needed when YouTube asks you to "sign in to confirm you're not a bot" |
| `js_runtime` | JavaScript runtime; `auto` checks deno, node and bun in that order. You can also name one (e.g. `node`), or use `none` to disable |
| `proxy` | Proxy URL such as `http://127.0.0.1:7890`; leave empty for none |


## Web Control Panel and Monitoring
The bot starts a web control panel alongside itself (default `http://localhost:5000`):
- **Monitor**: Discord connection and latency, uptime, per-server playback state, system resources (CPU/memory/disk, requires `psutil`), audio cache usage, source health (NetEase/QQ login state, yt-dlp, FFmpeg), downloads, command stats and a latency trend chart
- **Player**: join/leave voice channels, play/pause/previous/next, seek, volume, play mode, drag-to-reorder queue, history
- **Search / Library / Favorites**: search and queue, queue or download cached audio directly, favorite folders
- **Logs** (admins only): live log stream

The page updates in real time via Server-Sent Events, so actions taken in Discord show up immediately.

**Logging in**: use `/webauth` in Discord to get a one-time code (valid for 10 minutes). How long you stay logged in is set by the command's `days` option (default 3). Web permissions match the Discord command permissions, and regular users only see servers they are in.

**Port and mounting**: `configs/web_config.json` is created on first start:
| Option | Description |
| --- | --- |
| `enabled` | Turn the panel on or off |
| `host` | Bind address: `0.0.0.0` for all interfaces, `127.0.0.1` for local only |
| `port` | Port, default `5000` |
| `base_path` | URL prefix when mounting under a sub-path behind a reverse proxy, e.g. `/zeta` |
| `public_url` | Panel address shown in the `/webauth` reply (set this when using a domain or proxy) |
| `api_token` | Read-only API token for external monitoring tools (`Authorization: Bearer <token>`, GET only) |

Command-line flags and environment variables override the file:
```
python main.py --web-port 8090 --web-host 127.0.0.1 --web-base-path /zeta
python main.py --no-web
```
Environment variables: `ZETA_WEB_PORT`, `ZETA_WEB_HOST`. The `/healthz` endpoint needs no login, for tools like Uptime Kuma.

Behind Nginx, turn off buffering so live updates work:
```
location /zeta/ {
    proxy_pass http://127.0.0.1:5000;
    proxy_buffering off;
    proxy_read_timeout 1h;
}
```
**Note**: the panel has no built-in HTTPS. Put it behind a reverse proxy with HTTPS before exposing it to the internet.

## NetEase Cloud Music and QQ Music
The bot has built-in clients for NetEase Cloud Music and QQ Music (`zeta_bot/native_music`). They talk to the platforms directly, so **you don't need to deploy go-music-api or any other service**. Song, playlist and album links (including share short links) work, and `/search_audio` searches both platforms too.

**Logging in (for VIP songs)**
**Note: once a login is configured, every download uses that account, no matter which user sent the command. Use your own judgment about the account risk.**
- NetEase Cloud Music: run `python music_login.py netease` and scan the QR code shown in the terminal with the NetEase app. The cookie is saved to `data/cookies/netease.json`.
- QQ Music: log in at https://y.qq.com in your browser, export the cookies as JSON with an extension such as Cookie-Editor, and paste them into `data/cookies/qq.json` (`python music_login.py qq` shows the steps).
- Restart the bot after changing logins.

**Region limits**: most songs on both platforms only play from mainland China, logged in or not. Elsewhere the bot reports that the song isn't available in your region; you can set a proxy in `configs/music_config.json`.

`configs/music_config.json` is created on first start:
| Option | Description |
| --- | --- |
| `proxy` | HTTP proxy for NetEase and QQ Music requests, e.g. `http://127.0.0.1:7890`; empty for none |
| `netease_level` | NetEase quality: `standard` / `higher` / `exhigh` (default) / `lossless` / `hires`; higher tiers need VIP |
| `qq_quality` | QQ Music quality: `320` (default) / `128` / `aac`; falls back automatically when unavailable |

## (Optional) Using go-music-api
If you prefer [go-music-api](https://github.com/guohuiyuan/go-music-api) as the download backend, deploy it, then set the platform's value to `GO_MUSIC_API` in `configs/resource_handler.json` (values: `NATIVE` built-in, `GO_MUSIC_API`, `BILIBILI_API_PYTHON`, `YT_DLP`) and enter its URL in the settings. If go-music-api is unreachable, the bot falls back to the built-in clients.

Cookies for go-music-api:
- Configure them on the go-music-api service itself, see [Cookie 配置](https://github.com/guohuiyuan/go-music-api#cookie-配置)
- Or put browser-exported cookies in `data/cookies/<platform>.json`; the bot syncs them to go-music-api
- Or run `python go_music_qr_login.py` to log in by QR code through go-music-api
