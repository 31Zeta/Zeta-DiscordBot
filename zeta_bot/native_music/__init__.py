"""
内置音乐平台接口：网易云音乐、QQ音乐

直接请求各平台的接口，不需要部署go-music-api等外部服务。
返回的数据结构与go-music-api模块一致（{"songs": [...]} 与 extra），机器人的其他部分可以通用。

登录（会员歌曲）：将Cookie放在 data/cookies/netease.json、data/cookies/qq.json，
网易云音乐可以使用 python music_login.py 扫码登录。
配置：configs/music_config.json（代理、音质）
"""
from typing import *
import os
import time
import asyncio

import aiohttp

import utils
from utils import Result, success_result, failed_result

from zeta_bot import output_console, audio
from zeta_bot.resource import MediaPlatform, DownloadHandler, DownloadType, ResourceClassifier
from zeta_bot.native_music import netease, qq
from zeta_bot.native_music.common import MusicError, USER_AGENT, load_config, load_cookie, proxy, new_session

console = output_console.Console()
resource_classifier = ResourceClassifier()

level = "内置音乐模块"

PLATFORM_MODULES = {MediaPlatform.NETEASE: netease, MediaPlatform.QQ: qq}
SOURCE_MODULES = {netease.SOURCE: netease, qq.SOURCE: qq}

CHUNK_SIZE = 64 * 1024
# 音频地址缓存时间（秒），获取文件大小与下载时共用同一个地址
STREAM_CACHE_TTL = 600
MAX_FILE_TITLE_LENGTH = 120
_stream_cache: Dict[str, Tuple[float, List[str], Optional[int], str]] = {}


def supports(platform: MediaPlatform) -> bool:
    return platform in PLATFORM_MODULES


async def _failed(exception: Exception, description: str) -> Result:
    if isinstance(exception, MusicError):
        message, retryable = exception.message, exception.retryable
    elif isinstance(exception, (aiohttp.ClientError, asyncio.TimeoutError)):
        message, retryable = "网络连接异常", True
    else:
        await console.on_error(exception)
        message, retryable = f"{type(exception).__name__}", False
    await console.rp(f"{description}：{message}", f"[{level}]", message_type=utils.PrintType.ERROR, print_head=True)
    return failed_result(exception=exception, message=message, retryable=retryable)


async def get_info(url: str, platform: MediaPlatform) -> Result:
    """
    获取链接（单曲、歌单或专辑）中的歌曲信息
    返回结构与go_music.get_info一致：result为{"songs": [...]}，extra包含type以及歌单或专辑信息
    """
    module = PLATFORM_MODULES.get(platform)
    if module is None:
        return failed_result(exception=None, message=f"内置接口不支持{platform.value}", retryable=False)

    await console.rp(f"开始提取信息：{url}", f"[{level}]")
    try:
        async with new_session() as session:
            kind, title, cover, songs = await module.get_info(session, url)
    except Exception as e:
        return await _failed(e, f"{module.NAME}信息获取失败")

    if len(songs) == 0:
        return failed_result(exception=None, message="没有获取到任何歌曲", retryable=False)

    await console.rp(f"信息提取完毕：[{module.NAME}] {title}（{len(songs)} 首）", f"[{level}]")
    result = success_result(result={"songs": songs})
    result.extra = {
        "type": kind,
        "title": title,
        "cover": cover,
        "playlist_info_dict": {"playlists": [{"name": title, "cover": cover}]} if kind == "playlist" else None,
        "album_info_dict": {"albums": [{"name": title, "cover": cover}]} if kind == "album" else None,
    }
    return result


def get_music_uid(song: dict) -> str:
    return f"{song['source']}_{song['id']}"


async def _resolve_stream(session, song: dict) -> Tuple[List[str], Optional[int], str]:
    uid = get_music_uid(song)
    cached = _stream_cache.get(uid)
    if cached is not None and time.monotonic() - cached[0] < STREAM_CACHE_TTL:
        return cached[1], cached[2], cached[3]
    urls, size, extension = await SOURCE_MODULES[song["source"]].get_stream(session, song)
    _stream_cache[uid] = (time.monotonic(), urls, size, extension)
    return urls, size, extension


async def _probe_size(session, urls: List[str]) -> int:
    for url in urls:
        try:
            async with session.get(url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"}, proxy=proxy()) as response:
                if response.status == 206:
                    total = response.headers.get("Content-Range", "").rsplit("/", 1)[-1]
                    if total.isdigit():
                        return int(total)
                if response.status == 200 and response.headers.get("Content-Length", "").isdigit():
                    return int(response.headers["Content-Length"])
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue
    return 0


async def get_filesize(song: dict) -> Result:
    """
    返回预计的文件大小（字节），无法预知时返回0
    """
    try:
        async with new_session() as session:
            urls, size, _ = await _resolve_stream(session, song)
            if not size:
                size = await _probe_size(session, urls)
    except Exception as e:
        return await _failed(e, f"{song.get('name')} 获取失败")
    return success_result(result=int(size or 0))


async def _download_to_file(session, url: str, path: str) -> int:
    part_path = f"{path}.part"
    try:
        async with session.get(url, headers={"User-Agent": USER_AGENT}, proxy=proxy()) as response:
            if response.status != 200:
                raise MusicError(f"下载失败（HTTP {response.status}）", retryable=True)
            with open(part_path, "wb") as file:
                async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                    file.write(chunk)
        size = os.path.getsize(part_path)
        if size < 1024:
            raise MusicError("下载的文件无效", retryable=True)
        os.replace(part_path, path)
        return size
    finally:
        if os.path.exists(part_path):
            try:
                os.remove(part_path)
            except OSError:
                pass


async def audio_download(song: dict, download_dir: str, download_type: DownloadType) -> Result:
    if resource_classifier.handler(download_type) is not DownloadHandler.NATIVE:
        raise ValueError(f"错误下载类型：{download_type.name}")

    uid = get_music_uid(song)
    title = f"{song.get('artist') or '未知歌手'} - {song.get('name') or '未知歌曲'}"
    module = SOURCE_MODULES[song["source"]]
    try:
        async with new_session(total_timeout=None) as session:
            urls, _, extension = await _resolve_stream(session, song)
            file_title = utils.legal_name(f"{uid} - {title}")[:MAX_FILE_TITLE_LENGTH].rstrip(". ")
            path = f"{download_dir.rstrip('/')}/{file_title}.{extension}"
            await console.rp(f"开始下载：{file_title}.{extension}", f"[{level}]")

            last_error: Optional[Exception] = None
            size = 0
            # 依次尝试各个CDN地址
            for url in urls:
                try:
                    size = await _download_to_file(session, url, path)
                    break
                except (aiohttp.ClientError, asyncio.TimeoutError, MusicError) as e:
                    last_error = e
            else:
                raise last_error or MusicError("下载失败", retryable=True)
    except Exception as e:
        # 地址可能已过期，下次重新获取
        _stream_cache.pop(uid, None)
        return await _failed(e, f"{title} 下载失败")

    new_audio = audio.Audio(
        title=title,
        uid=uid,
        source=song["source"],
        source_id=str(song["id"]),
        download_type=download_type,
        path=path,
        duration=int(song.get("duration") or 0),
    )
    if song.get("cover"):
        new_audio.set_cover_url(song["cover"])

    converted_size = utils.convert_byte(size)
    await console.rp(
        f"下载完成\n"
        f"文件名：{os.path.basename(path)}\n"
        f"来源：[{module.NAME}] {song['id']}\n"
        f"路径：{download_dir}\n"
        f"大小：{converted_size[0]} {converted_size[1]}\n"
        f"时长：{utils.convert_duration_to_str(new_audio.get_duration())}",
        f"[{level}]"
    )
    return success_result(result=new_audio)


async def search(query: str, source: str, num: int = 5) -> List[dict]:
    """
    搜索歌曲，返回与其他平台搜索一致的结果格式
    """
    module = SOURCE_MODULES[source]
    query = query.strip()
    if not query:
        return []
    await console.rp(f"开始搜索：[{module.NAME}] {query}", f"[{level}]")
    try:
        async with new_session() as session:
            songs = await module.search(session, query, num)
    except Exception as e:
        await _failed(e, f"{module.NAME}搜索失败")
        return []
    return [
        {
            "title": f"{song['name']} - {song['artist']}",
            "id": module.song_url(song["id"]),
            "duration": song["duration"],
            "duration_str": utils.convert_duration_to_str(song["duration"]),
            "thumbnail": song["cover"],
            "source": source,
        }
        for song in songs
    ]


def describe() -> dict:
    """
    返回内置接口的状态（用于Web监控面板）
    """
    config = load_config()
    return {
        "netease_login": bool(load_cookie(netease.SOURCE)),
        "qq_login": bool(load_cookie(qq.SOURCE)),
        "proxy": bool(proxy()),
        "netease_level": config.get("netease_level"),
        "qq_quality": config.get("qq_quality"),
    }
