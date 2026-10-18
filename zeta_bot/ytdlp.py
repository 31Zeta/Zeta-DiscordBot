from __future__ import unicode_literals
from typing import *
from enum import Enum
import asyncio
import json
import time
from pathlib import Path
from urllib.parse import urlparse, urlsplit, urlunsplit, parse_qs

import yt_dlp
from yt_dlp import YoutubeDL
from yt_dlp.networking import Request
from yt_dlp.networking.exceptions import RequestError

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
BILIBILI_COOKIE_FILE = Path(__file__).resolve().parent.parent / "data" / "cookies" / "bilibili_ytdlp.txt"
BILIBILI_UNRELIABLE_CDN_HOSTS = {"upos-sz-mirrorcosov.bilivideo.com"}
BILIBILI_FALLBACK_CDN_HOSTS = (
    "upos-sz-mirrorcos.bilivideo.com",
    "upos-sz-mirror08c.bilivideo.com",
)
SOURCE_MAP = {
    "youtube": "YouTube",
    "bilibili": "哔哩哔哩",
    "netease": "网易云音乐",
    "unknown": "未知来源",
}


def bilibili_part_number(url: str) -> Optional[int]:
    values = parse_qs(urlsplit(url).query, keep_blank_values=True).get("p")
    if values is None:
        return None
    if not values[-1].isascii() or not values[-1].isdigit() or int(values[-1]) < 1:
        raise ValueError("B站分P号必须是大于0的整数")
    return int(values[-1])


def normalize_bilibili_parts(info_dict: dict, pages=None) -> dict:
    """保留分P号；目录接口不可用时仍可按P号选择，不逐集请求播放地址。"""
    page_map = {
        page.get("page"): page for page in (pages or []) if isinstance(page, dict)
    }
    entries = []
    for item in info_dict.get("entries") or []:
        if not isinstance(item, dict):
            raise ValueError("B站分集目录包含无效条目，请提供带 ?p=数字 的视频链接")
        part = bilibili_part_number(item.get("url") or "")
        if part is None:
            raise ValueError("该B站列表不是普通分P视频，请提供具体视频链接")
        page = page_map.get(part, {})
        entries.append({
            **item,
            "page": part,
            "id": f"{info_dict['id']}_p{part}",
            "title": page.get("part") or item.get("title") or f"第 {part} P（标题暂不可用）",
            "duration": page.get("duration", item.get("duration")),
        })
    entries.sort(key=lambda item: item["page"])
    if not entries or [item["page"] for item in entries] != list(range(1, len(entries) + 1)):
        raise ValueError("B站分集目录不完整，请提供带 ?p=数字 的视频链接")
    return {**info_dict, "entries": entries, "pages": entries}


def source_from_download_type(download_type: DownloadType) -> str:
    if download_type.name.startswith("YOUTUBE"):
        return "youtube"
    if download_type.name.startswith("BILIBILI"):
        return "bilibili"
    if download_type.name.startswith("NETEASE"):
        return "netease"
    return "unknown"


def cookie_file_for_url(url: str, cookie_file_path=None):
    """B站匿名会话持久化buvid等Cookie，避免每次请求都被识别为全新客户端。"""
    if cookie_file_path is not None:
        return str(cookie_file_path)
    if "bilibili.com" in str(url) or "b23.tv" in str(url):
        BILIBILI_COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
        return str(BILIBILI_COOKIE_FILE)
    return None


def prefer_reliable_bilibili_audio(info_dict: dict, url: str) -> dict:
    """本机不可达的B站CDN出现时，改选最高码率的其他音频CDN。"""
    if "bilibili.com" not in str(url):
        return info_dict
    selected_host = urlparse(str(info_dict.get("url") or "")).hostname
    if selected_host not in BILIBILI_UNRELIABLE_CDN_HOSTS:
        return info_dict

    candidates = []
    for audio_format in info_dict.get("formats") or []:
        format_url = str(audio_format.get("url") or "")
        host = urlparse(format_url).hostname
        if audio_format.get("vcodec") == "none" and format_url and host not in BILIBILI_UNRELIABLE_CDN_HOSTS:
            candidates.append(audio_format)
    if not candidates:
        return info_dict

    selected = max(candidates, key=lambda item: float(item.get("abr") or item.get("tbr") or 0))
    result = dict(info_dict)
    for key in ("url", "format_id", "format", "ext", "filesize", "filesize_approx", "tbr", "abr", "asr", "http_headers"):
        if key in selected:
            result[key] = selected[key]
    return result


def bilibili_audio_url_candidates(info_dict: dict, url: str) -> list[str]:
    """为不稳定的B站音频地址生成保持路径和签名不变的备用CDN地址。"""
    primary_url = str(info_dict.get("url") or "")
    if "bilibili.com" not in str(url) or not primary_url:
        return [primary_url] if primary_url else []

    parts = urlsplit(primary_url)
    if parts.hostname not in BILIBILI_UNRELIABLE_CDN_HOSTS:
        return [primary_url]

    candidates = []
    for host in (*BILIBILI_FALLBACK_CDN_HOSTS, parts.hostname):
        candidate = urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates

async def get_info(url, cookie_file_path=None) -> Result:
    ydl_opts = {
        'format': 'bestaudio/best',
        'extract_flat': True,
        "quiet": True,
        "retries": 3,
        "extractor_retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 10,
    }
    cookie_file_path = cookie_file_for_url(url, cookie_file_path)
    if cookie_file_path is not None:
        ydl_opts["cookiefile"] = cookie_file_path

    await console.rp(f"开始提取信息：{url}", f"[{level}]")

    try:
        is_bilibili = (urlsplit(url).hostname or "").endswith("bilibili.com")
        requested_part = bilibili_part_number(url) if is_bilibili else None

        def extract_info():
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if is_bilibili and info and info.get("_type") == "playlist":
                    if requested_part is not None:
                        raise ValueError(f"无法解析第 {requested_part} P，请检查分P号是否有效")
                    pages = []
                    try:
                        request = Request(
                            f"https://api.bilibili.com/x/player/pagelist?bvid={info['id']}",
                            headers={"Referer": "https://www.bilibili.com/"},
                        )
                        with ydl.urlopen(request) as response:
                            payload = json.loads(response.read())
                        if payload.get("code") == 0 and isinstance(payload.get("data"), list):
                            pages = payload["data"]
                    except (RequestError, ValueError, TypeError, AttributeError):
                        # 保留可用的分P链接，标题和时长可以在用户选择后获取。
                        pass
                    info = normalize_bilibili_parts(info, pages)
                return info

        # B站的播放格式接口偶尔会短暂返回空列表；使用新会话重试，
        # 同时把同步的yt-dlp请求移出Discord事件循环。
        for attempt in range(3):
            try:
                info_dict = await asyncio.to_thread(extract_info)
                info_dict = prefer_reliable_bilibili_audio(info_dict, url)
                break
            except yt_dlp.utils.DownloadError as exception:
                transient_empty_formats = "No video formats found" in str(exception)
                if transient_empty_formats and attempt < 2:
                    await asyncio.sleep(attempt + 1)
                    continue
                raise

        video_id = info_dict["id"]
        video_title = info_dict["title"]

        await console.rp(f"信息提取完毕：[{video_id}] {video_title}", f"[{level}]")

    except ValueError as e:
        return failed_result(exception=e, message=str(e), retryable=False)
    except yt_dlp.utils.DownloadError as e:
        await console.rp(
            "触发异常yt_dlp.utils.DownloadError，YT-DLP信息获取失败，该视频/音频可能已失效或存在区域版权限制",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="YT-DLP下载失败，该视频/音频可能已失效或存在区域版权限制", retryable=False)
    except yt_dlp.utils.ExtractorError as e:
        await console.rp(
            "触发异常yt_dlp.utils.ExtractorError，视频/音频提取失败",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="视频/音频提取失败", retryable=False)
    except yt_dlp.utils.UnavailableVideoError as e:
        await console.rp(
            "触发异常yt_dlp.utils.UnavailableVideoError，视频/音频不可用",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="视频/音频不可用", retryable=False)
    else:
        if info_dict is None:
            await console.rp(
                f"返回信息为空，异常未捕获，请参照错误日志",
                f"[{level}]",
                message_type=utils.PrintType.ERROR,
                print_head=True
            )
            return failed_result(exception=None, message="结果为空，未知错误", retryable=False)
        else:
            return success_result(result=info_dict)


async def get_filesize(info_dict: dict) -> Result:
    filesize = info_dict.get("filesize") or info_dict.get("filesize_approx")
    if filesize is not None:
        return success_result(result=int(filesize))
    else:
        await console.rp(
            f"文件大小获取失败",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=None, message="结果为空，未知错误", retryable=False)


def construct_uid(video_id: str, download_type: DownloadType) -> str:
    if resource_classifier.handler(download_type) is not DownloadHandler.YT_DLP:
        raise ValueError(f"错误下载类型：{download_type.name}")

    source = source_from_download_type(download_type)
    uid = f"{source}_{video_id}"
    return uid


def compact_stream_info(info_dict: dict) -> dict:
    """保存下载回退所需字段，避免把完整formats和临时签名写进服务器队列。"""
    keys = (
        "id", "title", "ext", "duration", "filesize", "filesize_approx", "url",
        "format_id", "protocol", "acodec", "thumbnail", "http_headers",
    )
    return {key: info_dict.get(key) for key in keys if info_dict.get(key) is not None}


def create_stream_audio(url: str, info_dict: dict, download_type: DownloadType) -> audio.Audio:
    video_id = info_dict["id"]
    uid = construct_uid(video_id, download_type)
    new_audio = audio.Audio(
        title=info_dict["title"],
        uid=uid,
        source=source_from_download_type(download_type),
        source_id=video_id,
        download_type=download_type,
        path=f"stream://{uid}",
        duration=int(info_dict.get("duration") or 0),
        stream=True,
        stream_origin=url,
        stream_data={"info": compact_stream_info(info_dict), "resolved_at": time.time()},
    )
    if info_dict.get("thumbnail"):
        new_audio.set_cover_url(info_dict["thumbnail"])
    return new_audio


async def audio_download(youtube_url, info_dict: dict, download_dir: str, download_type: DownloadType = DownloadType.YOUTUBE_SINGLE, cookie_file_path=None) -> Result:
    if resource_classifier.handler(download_type) is not DownloadHandler.YT_DLP:
        raise ValueError(f"错误下载类型：{download_type.name}")

    if download_dir.endswith("/"):
        download_dir = download_dir.rstrip("/")

    video_id = info_dict["id"]
    video_title = info_dict["title"]
    file_extension = info_dict["ext"]
    video_duration = info_dict["duration"]
    target_filesize = info_dict.get("filesize") or info_dict.get("filesize_approx")
    if target_filesize is None:
        return failed_result(exception=None, message="结果为空，未知错误", retryable=False)
    size = utils.convert_byte(int(target_filesize))

    uid = construct_uid(video_id=video_id, download_type=download_type)
    file_title = utils.legal_name(f"{uid} - {video_title}")
    download_path = f"{download_dir}/{file_title}.{file_extension}"

    selected_format = (
        str(info_dict.get("format_id") or "bestaudio/best")
        if download_type.name.startswith("BILIBILI")
        else "bestaudio/best"
    )
    ydl_opts = {
        "format": selected_format,
        "outtmpl": download_path,
        "extract_flat": True,
        "quiet": True,
        # CDN连接偶尔会在传输中失去响应；快速失败，避免Discord界面无限加载。
        "socket_timeout": 10,
        "retries": 1,
        "extractor_retries": 2,
        "fragment_retries": 1,
        "file_access_retries": 1,
        "continuedl": False,
    }

    cookie_file_path = cookie_file_for_url(youtube_url, cookie_file_path)
    if cookie_file_path is not None:
        ydl_opts["cookiefile"] = cookie_file_path

    await console.rp(f"开始下载：{file_title}.{file_extension}", f"[{level}]")

    try:
        def download():
            if download_type.name.startswith("BILIBILI"):
                # 不重新提取视频信息，否则yt-dlp会丢掉我们选择的CDN并再次落回
                # mirrorcosov。直接下载已解析出的音频URL，并在超时时切换镜像。
                candidates = bilibili_audio_url_candidates(info_dict, youtube_url)
                direct_ydl_opts = dict(ydl_opts)
                direct_ydl_opts["format"] = "bestaudio/best"
                last_exception = None
                for candidate_url in candidates:
                    direct_info = {
                        "_type": "video",
                        "id": video_id,
                        "title": video_title,
                        "url": candidate_url,
                        "ext": file_extension,
                        "protocol": info_dict.get("protocol") or "https",
                        "vcodec": "none",
                        "acodec": info_dict.get("acodec") or "mp4a.40.2",
                        "http_headers": info_dict.get("http_headers") or {},
                        "webpage_url": youtube_url,
                    }
                    try:
                        with YoutubeDL(direct_ydl_opts) as ydl:
                            return ydl.process_ie_result(direct_info, download=True)
                    except yt_dlp.utils.DownloadError as exception:
                        last_exception = exception
                if last_exception is not None:
                    raise last_exception
                raise yt_dlp.utils.DownloadError("B站音频地址为空")

            with YoutubeDL(ydl_opts) as ydl:
                return ydl.download([youtube_url])

        await asyncio.to_thread(download)

        source = source_from_download_type(download_type)

        new_audio = audio.Audio(
            title=video_title,
            uid=uid,
            source=source,
            source_id=video_id,
            download_type=download_type,
            path=download_path,
            duration=video_duration
        )

        if "thumbnail" in info_dict.keys():
            new_audio.set_cover_url(info_dict["thumbnail"])

        await console.rp(
            f"下载完成\n"
            f"文件名：{file_title}.{file_extension}\n"
            f"来源：[{SOURCE_MAP[source]}] {video_id}\n"
            f"路径：{download_dir}\n"
            f"大小：{size[0]} {size[1]}\n"
            f"时长：{utils.convert_duration_to_str(video_duration)}",
            f"[{level}]"
        )

    except yt_dlp.utils.DownloadError as e:
        await console.rp(
            "触发异常yt_dlp.utils.DownloadError，YT-DLP下载失败，该视频/音频可能已失效或存在区域版权限制",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="YT-DLP下载失败，该视频/音频可能已失效或存在区域版权限制", retryable=False)
    except yt_dlp.utils.ExtractorError as e:
        await console.rp(
            "触发异常yt_dlp.utils.ExtractorError，视频/音频提取失败",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="视频/音频提取失败", retryable=False)
    except yt_dlp.utils.UnavailableVideoError as e:
        await console.rp(
            "触发异常yt_dlp.utils.UnavailableVideoError，视频/音频不可用",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="视频/音频不可用", retryable=False)
    else:
        if new_audio is None:
            await console.rp(
                f"音频对象返回为空，异常未捕获，请参照错误日志",
                f"[{level}]",
                message_type=utils.PrintType.ERROR,
                print_head=True
            )
            return failed_result(exception=None, message="结果为空，未知错误", retryable=False)
        else:
            return success_result(result=new_audio)


async def youtube_search(query, query_num=5) -> list:

    query = query.strip()

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': "./downloads/" + '/%(title)s.%(ext)s',
        'default_search': "ytsearch",
        'extract_flat': True,
        "quiet": True,
    }

    if query == "":
        return []

    await console.rp(f"开始搜索：{query}", f"[{level}]")

    with YoutubeDL(ydl_opts) as ydl:
        extracted_info = ydl.extract_info(f"ytsearch{query_num}:{query}", download=False)

    result = []
    log_message = f"搜索 {query} 结果为："
    counter = 1

    id_header = "https://www.youtube.com/watch?v="

    for item in extracted_info.get("entries") or []:
        if counter > query_num:
            break
        if not isinstance(item, dict):
            continue

        video_id = item.get("id")
        title = item.get("title")
        duration = item.get("duration")

        # YouTube搜索偶尔混入直播、首映或已失效条目，这些结果没有duration。
        # 跳过它们，避免一个异常条目让B站和YouTube的整个搜索菜单一起失败，
        # 同时防止误选直播后产生没有结束时间的下载。
        if not video_id or not title or duration is None:
            continue

        result.append(
            {
                "title": title,
                "id": id_header + video_id,
                "duration": duration,
                "duration_str": utils.convert_duration_to_str(duration),
            }
        )
        log_message += f"\n{counter}. {video_id}：{title} [{utils.convert_duration_to_str(duration)}]"
        counter += 1

    await console.rp(log_message, f"[{level}]")

    return result
