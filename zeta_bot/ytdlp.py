from __future__ import unicode_literals
from typing import *
import os
import re
import shutil
import asyncio
import logging

import yt_dlp
from yt_dlp import YoutubeDL
from yt_dlp import version as yt_dlp_version

import errors
import utils
from utils import Result, success_result, failed_result

from zeta_bot import (
    output_console,
    audio
)
from zeta_bot.resource import MediaPlatform, LinkType, DownloadHandler, DownloadType, ResourceClassifier

# 设置控制台
console = output_console.Console()

# 加载资源分类器
resource_classifier = ResourceClassifier()

level = "YT-DLP模块"
SOURCE_MAP = {
    "youtube": "YouTube",
    "netease": "网易云音乐",
    "unknown": "未知来源",
}

# yt-dlp相关配置（首次运行时自动生成）
#   cookie_file: Netscape格式的cookie文件，YouTube要求"登录以确认您不是机器人"时需要
#   js_runtime: YouTube签名解析所需的JavaScript运行时，auto为自动检测（deno -> node -> bun），none为禁用
#   proxy: 代理地址，例如 http://127.0.0.1:7890 或 socks5://127.0.0.1:1080，留空为不使用
CONFIG_PATH = "./configs/ytdlp_config.json"
DEFAULT_CONFIG = {
    "cookie_file": "./configs/cookies.txt",
    "js_runtime": "auto",
    "proxy": "",
}

# 文件名最大长度（不含扩展名），避免超出Windows路径长度限制
MAX_FILE_TITLE_LENGTH = 120

_config: Optional[dict] = None
_logger = logging.getLogger("yt-dlp")


class _YtdlpLogger:
    """
    将yt-dlp的输出重定向到日志，避免打乱控制台（下载进度条、警告等）
    """
    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        _logger.warning(msg)

    def error(self, msg):
        _logger.error(msg)


def load_config() -> dict:
    global _config
    if _config is None:
        config = dict(DEFAULT_CONFIG)
        if os.path.exists(CONFIG_PATH):
            try:
                loaded = utils.json_load(CONFIG_PATH)
                if isinstance(loaded, dict):
                    config.update({key: loaded[key] for key in loaded if key in DEFAULT_CONFIG})
            except errors.JSONFileError:
                pass
        else:
            try:
                os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
                utils.json_save(CONFIG_PATH, config)
            except OSError:
                pass
        _config = config
    return _config


def detect_js_runtime() -> Optional[str]:
    """
    返回yt-dlp要使用的JavaScript运行时名称，未找到时返回None
    """
    runtime = str(load_config().get("js_runtime") or "auto").strip().lower()
    if runtime in ("", "none", "off", "false"):
        return None
    if runtime != "auto":
        return runtime
    for name in ("deno", "node", "bun"):
        if shutil.which(name):
            return name
    return None


def build_opts(cookie_file_path=None, **extra) -> dict:
    """
    构造通用的yt-dlp参数
    """
    config = load_config()
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noprogress": True,
        "logger": _YtdlpLogger(),
    }

    if cookie_file_path is None:
        cookie_file_path = config.get("cookie_file")
    if cookie_file_path and os.path.exists(str(cookie_file_path)):
        ydl_opts["cookiefile"] = str(cookie_file_path)

    js_runtime = detect_js_runtime()
    if js_runtime is not None:
        ydl_opts["js_runtimes"] = {js_runtime: {}}

    if config.get("proxy"):
        ydl_opts["proxy"] = str(config["proxy"])

    ydl_opts.update(extra)
    return ydl_opts


def describe() -> dict:
    """
    返回当前yt-dlp环境的状态（用于Web监控面板）
    """
    config = load_config()
    cookie_file = config.get("cookie_file")
    return {
        "version": yt_dlp_version.__version__,
        "js_runtime": detect_js_runtime(),
        "cookie_file": bool(cookie_file and os.path.exists(str(cookie_file))),
        "proxy": bool(config.get("proxy")),
    }


def _error_reason(exception: Exception) -> str:
    """
    从yt-dlp的异常信息中提取简短的失败原因
    """
    message = re.sub(r"\x1b\[[0-9;]*m", "", str(exception))
    message = re.sub(r"^ERROR:\s*", "", message.strip())
    message = re.sub(r"^\[[^\]]+\]\s*[\w-]+:\s*", "", message)
    if "Sign in to confirm" in message:
        return "YouTube要求登录验证，请将cookie文件放置在configs/cookies.txt"
    if "Private video" in message:
        return "该视频为私享视频"
    if "Video unavailable" in message:
        return "该视频不可用"
    if "This live event" in message or "Premieres in" in message:
        return "直播或首映尚未开始"
    return message[:150]


async def _log_ytdlp_error(exception: Exception, description: str) -> Result:
    reason = _error_reason(exception)
    await console.rp(
        f"触发异常{type(exception).__module__}.{type(exception).__name__}，{description}：{reason}",
        f"[{level}]",
        message_type=utils.PrintType.ERROR,
        print_head=True
    )
    return failed_result(exception=exception, message=f"YT-DLP获取失败：{reason}", retryable=False)


async def get_info(url, cookie_file_path=None) -> Result:
    ydl_opts = build_opts(cookie_file_path, extract_flat=True)

    await console.rp(f"开始提取信息：{url}", f"[{level}]")

    def _extract():
        with YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        # yt-dlp为同步阻塞调用，放入线程中执行，防止阻塞机器人的事件循环（会导致所有按钮与指令卡顿）
        info_dict = await asyncio.to_thread(_extract)
    except yt_dlp.utils.DownloadError as e:
        return await _log_ytdlp_error(e, "YT-DLP信息获取失败，该视频/音频可能已失效或存在区域版权限制")
    except yt_dlp.utils.ExtractorError as e:
        return await _log_ytdlp_error(e, "视频/音频提取失败")
    except yt_dlp.utils.UnavailableVideoError as e:
        return await _log_ytdlp_error(e, "视频/音频不可用")

    if info_dict is None:
        await console.rp(
            f"返回信息为空，异常未捕获，请参照错误日志",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=None, message="结果为空，未知错误", retryable=False)

    await console.rp(f"信息提取完毕：[{info_dict.get('id')}] {info_dict.get('title')}", f"[{level}]")
    return success_result(result=info_dict)


async def get_filesize(info_dict: dict) -> Result:
    """
    返回预计的文件大小（字节），部分资源无法预知大小，此时返回0
    """
    size = info_dict.get("filesize") or info_dict.get("filesize_approx")
    if not size and info_dict.get("requested_formats"):
        size = sum(
            (item.get("filesize") or item.get("filesize_approx") or 0) for item in info_dict["requested_formats"]
        )
    try:
        return success_result(result=int(size or 0))
    except (TypeError, ValueError):
        return success_result(result=0)


def construct_uid(video_id: str, download_type: DownloadType) -> str:
    if resource_classifier.handler(download_type) is not DownloadHandler.YT_DLP:
        raise ValueError(f"错误下载类型：{download_type.name}")

    if download_type.name.startswith("YOUTUBE"):
        source = "youtube"
    elif download_type.name.startswith("NETEASE"):
        source = "netease"
    else:
        source = "unknown"
    uid = f"{source}_{video_id}"
    return uid


async def audio_download(youtube_url, info_dict: dict, download_dir: str, download_type: DownloadType = DownloadType.YOUTUBE_SINGLE, cookie_file_path=None) -> Result:
    if resource_classifier.handler(download_type) is not DownloadHandler.YT_DLP:
        raise ValueError(f"错误下载类型：{download_type.name}")

    if download_dir.endswith("/"):
        download_dir = download_dir.rstrip("/")

    video_id = info_dict["id"]
    video_title = info_dict.get("title") or video_id

    uid = construct_uid(video_id=video_id, download_type=download_type)
    file_title = utils.legal_name(f"{uid} - {video_title}")[:MAX_FILE_TITLE_LENGTH].rstrip(". ")
    # "%"为yt-dlp输出模板的特殊字符，需要转义；扩展名由yt-dlp根据实际下载的格式决定
    outtmpl = f"{download_dir}/{file_title.replace('%', '%%')}.%(ext)s"
    ydl_opts = build_opts(cookie_file_path, outtmpl=outtmpl)

    await console.rp(f"开始下载：{file_title}", f"[{level}]")

    def _download() -> Tuple[dict, str]:
        with YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(youtube_url, download=True)
            requested = result.get("requested_downloads") or []
            if len(requested) > 0 and requested[0].get("filepath"):
                path = requested[0]["filepath"]
            else:
                path = ydl.prepare_filename(result)
            return result, path

    try:
        result_dict, download_path = await asyncio.to_thread(_download)
    except yt_dlp.utils.DownloadError as e:
        return await _log_ytdlp_error(e, "YT-DLP下载失败，该视频/音频可能已失效或存在区域版权限制")
    except yt_dlp.utils.ExtractorError as e:
        return await _log_ytdlp_error(e, "视频/音频提取失败")
    except yt_dlp.utils.UnavailableVideoError as e:
        return await _log_ytdlp_error(e, "视频/音频不可用")

    if result_dict is None or not os.path.exists(download_path):
        await console.rp(
            f"下载完成后未找到文件，异常未捕获，请参照错误日志",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=None, message="结果为空，未知错误", retryable=False)

    # yt-dlp返回绝对路径，转换为与其他下载器一致的相对路径
    download_path = f"{download_dir}/{os.path.basename(download_path)}"
    video_duration = int(result_dict.get("duration") or info_dict.get("duration") or 0)

    if download_type.name.startswith("YOUTUBE"):
        source = "youtube"
    elif download_type.name.startswith("NETEASE"):
        source = "netease"
    else:
        source = "unknown"

    new_audio = audio.Audio(
        title=video_title,
        uid=uid,
        source=source,
        source_id=video_id,
        download_type=download_type,
        path=download_path,
        duration=video_duration
    )

    thumbnail = result_dict.get("thumbnail") or info_dict.get("thumbnail")
    if thumbnail:
        new_audio.set_cover_url(thumbnail)

    size = utils.convert_byte(os.path.getsize(download_path))
    await console.rp(
        f"下载完成\n"
        f"文件名：{os.path.basename(download_path)}\n"
        f"来源：[{SOURCE_MAP[source]}] {video_id}\n"
        f"路径：{download_dir}\n"
        f"大小：{size[0]} {size[1]}\n"
        f"时长：{utils.convert_duration_to_str(video_duration)}",
        f"[{level}]"
    )
    return success_result(result=new_audio)


async def youtube_search(query, query_num=5) -> list:

    query = query.strip()
    if query == "":
        return []

    ydl_opts = build_opts(default_search="ytsearch", extract_flat=True)

    await console.rp(f"开始搜索：{query}", f"[{level}]")

    def _search():
        with YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(f"ytsearch{query_num}:{query}", download=False)

    try:
        extracted_info = await asyncio.to_thread(_search)
    except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError) as e:
        await console.rp(f"搜索失败：{_error_reason(e)}", f"[{level}]", message_type=utils.PrintType.ERROR, print_head=True)
        return []

    result = []
    log_message = f"搜索 {query} 结果为："
    counter = 1

    id_header = "https://www.youtube.com/watch?v="

    for item in (extracted_info or {}).get("entries") or []:
        if counter > query_num:
            break
        if not item or not item.get("id"):
            continue
        duration = int(item.get("duration") or 0)
        thumbnails = item.get("thumbnails") or []
        result.append(
            {
                "title": item.get("title") or item["id"],
                "id": id_header + item["id"],
                "duration": duration,
                "duration_str": utils.convert_duration_to_str(duration),
                "thumbnail": thumbnails[-1].get("url", "") if len(thumbnails) > 0 else "",
                "source": "youtube",
            }
        )
        log_message += f"\n{counter}. {item['id']}：{item.get('title')} [{utils.convert_duration_to_str(duration)}]"
        counter += 1

    await console.rp(log_message, f"[{level}]")

    return result
