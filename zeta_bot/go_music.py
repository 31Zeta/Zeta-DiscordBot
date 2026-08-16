from typing import *
import aiohttp
import asyncio
import json
import os
import re
from pathlib import Path
from enum import Enum

import errors
import utils
from utils import Result, success_result, failed_result

from zeta_bot import (
    output_console,
    audio,
)
from zeta_bot.resource import MediaPlatform, LinkType, DownloadHandler, DownloadType, ResourceClassifier

# 设置控制台
console = output_console.Console()

# 加载资源分类器
resource_classifier = ResourceClassifier()

level = "Go-Music-API模块"

CHUNK_SIZE = 256 * 1024
GO_MUSIC_SUPPORTED_PLATFORM = {"bilibili", "netease", "qq", "kugou", "kuwo", "migu", "qianqian", "soda", "fivesing", "jamendo", "joox"}
GO_MUSIC_INFO_TYPE = {"song", "playlist", "album"}
GO_MUSIC_DOWNLOAD_TYPE = {f"{i}_{j}" for i in GO_MUSIC_SUPPORTED_PLATFORM for j in GO_MUSIC_INFO_TYPE}
SOURCE_MAP = {
    "bilibili": "哔哩哔哩",
    "netease": "网易云音乐",
    "qq": "QQ音乐",
    "kugou": "酷狗音乐",
    "kuwo": "酷我音乐",
    "migu": "咪咕音乐",
    "qianqian": "千千音乐",
    "soda": "汽水音乐",
    "fivesing": "5sing",
    "jamendo": "Jamendo",
    "joox": "JOOX"
}


def api_url_format(api_url: str) -> str:
    return str(api_url).strip().rstrip("/")


async def handle_exception(exception: Exception) -> Result:
    message = "音乐服务发生错误"
    if isinstance(exception, RuntimeError):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False
    elif isinstance(exception, errors.ResourceRestrictedError):
        await console.rp(
            f"获取失败，资源可能存在会员或者区域版权限制：{exception}",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False
        message = "资源可能存在会员或者区域版权限制"
    # 不支持链接的情况
    elif isinstance(exception, errors.URLNotSupportedError):
        await console.rp(
            f"触发异常URLNotSupportedError：{exception}",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False
        message = str(exception)  # 将API报错信息发至上层message打印到Discord中
    # 网络连接、响应中断和超时
    elif isinstance(exception, (aiohttp.ClientConnectionError, aiohttp.ClientPayloadError, asyncio.TimeoutError)):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}，无法连接go-music-api或请求超时",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = True

    # 无效服务地址
    elif isinstance(exception, aiohttp.InvalidURL):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}，go-music-api服务地址无效",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False

    elif isinstance(exception, (aiohttp.ClientError, aiohttp.ClientResponseError)):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}，go-music-api网络请求失败",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = True

    elif isinstance(exception, json.JSONDecodeError):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}，返回的JSON格式无效",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False

    elif isinstance(exception, OSError):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}，本地音频文件处理失败",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False

    elif isinstance(exception, (ValueError, TypeError, KeyError)):
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}，参数或响应数据无效",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False

    else:
        await console.rp(
            f"触发异常{type(exception).__module__}.{type(exception).__name__}：{exception}",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        retryable = False

    return failed_result(exception=exception, message=message, retryable=retryable)


async def request_json(api_url: str, session: aiohttp.ClientSession, endpoint: str, params: Optional[dict] = None) -> dict:
    """
    请求go-music-api并解析JSON对象

    :param api_url: go-music-api 服务根地址
    :param session: aiohttp 客户端会话
    :param endpoint: API 路径
    :param params: 查询参数
    :return: API 返回的 JSON 对象
    """
    request_url = f"{api_url_format(api_url)}{endpoint}"

    async with session.get(request_url, params=params) as response:
        body = await response.text(errors="replace")

        try:
            result = json.loads(body)
        except json.JSONDecodeError as exception:
            raise RuntimeError(f"状态码：{response.status}，返回的JSON格式无效：{body}") from exception

        # 错误状态码的情况
        if response.status >= 400:
            error_message = str(result.get("msg", result.get("error", body)))
            # 资源受限，go-music-api返回404 Failed to get URL
            if response.status == 404:
                raise errors.ResourceRestrictedError(f"疑似资源受限，状态码：{response.status}，{error_message}")
            # 处理不支持的链接的情况，需要将API报错信息发至上层message打印到Discord中
            elif "不支持" in error_message:
                raise errors.URLNotSupportedError(error_message)
            else:
                raise RuntimeError(f"状态码：{response.status}，{error_message}")

    return result


def build_music_params(info_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    构造大小探测和下载接口需要的歌曲参数（主要需要将extra重新构造为字典，否则extra是字符串）

    :param info_dict: 标准化后的歌曲信息字典
    :return: 音频流接口查询参数
    """
    extra = info_dict.get("extra") or {}

    # 字符串形式的extra必须可以被解析为JSON
    if isinstance(extra, str):
        try:
            json.loads(extra)
        except json.JSONDecodeError as exception:
            raise RuntimeError("歌曲extra字段不是有效的JSON") from exception
        extra_json = extra

    # 字典等结构统一序列化为 JSON 字符串
    else:
        try:
            extra_json = json.dumps(extra, ensure_ascii=False)
        except (TypeError, ValueError) as exception:
            raise RuntimeError("歌曲extra字段无法转换为JSON") from exception

    return {
        "id": info_dict["id"],
        "name": info_dict["name"] or "未知音频",
        "artist": info_dict["artist"] or "未知作者",
        "album": info_dict.get("album", ""),
        "duration": info_dict.get("duration", 0),
        "source": info_dict.get("source") or "未知来源",
        "cover": info_dict.get("cover") or "",
        "extra": extra_json,
    }


async def is_available(api_url: str, silent: bool = True) -> bool:
    """
    检测go-music-api服务是否正常响应

    :param api_url: go-music-api 服务根地址
    :param silent: 是否取消打印测试信息
    :return: 服务是否可用
    """
    timeout = aiohttp.ClientTimeout(total=3)

    # 请求不依赖外部音乐平台的轻量接口
    try:
        if not silent: await console.rp(
            f"测试go-music-api连接：{api_url}",
            f"[{level}]",
        )
        async with aiohttp.ClientSession(timeout=timeout) as session:
            result = await request_json(api_url, session, "/api/v1/system/qr_login/sources",)
    except Exception as e:
        if not silent: await console.rp(
            f"go-music-api服务连接失败：触发异常{type(e).__module__}.{type(e).__name__}",
            f"[{level}]",
            message_type=utils.PrintType.WARNING,
            print_head=True
        )
        return False
    else:
        if not silent: await console.rp(
            f"go-music-api服务连接成功",
            f"[{level}]",
            print_head=True
        )
        return True


async def get_info_album(api_url: str, music_url: str, suppress_errors: bool = False) -> Optional[Result]:
    """
    通过音乐链接获取专辑信息

    :param api_url: go-music-api 服务根地址
    :param music_url: 音乐平台的单曲分享链接
    :param suppress_errors: 出现错误时是否阻止异常抛出
    :return: 包含歌曲信息或异常的统一结果字典
    """
    try:
        music_url = str(music_url).strip()

        # 请求链接解析接口
        timeout = aiohttp.ClientTimeout(total=20, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            result = await request_json(
                api_url_format(api_url),
                session,
                "/api/v1/music/search",
                {
                    "q": music_url,
                    "type": "album",
                },
            )

        info_dict = result.get("data")
        if not isinstance(info_dict, dict):
            if suppress_errors: return None
            raise RuntimeError("音乐链接解析结果缺少data对象")

        albums = info_dict.get("albums")
        if not isinstance(albums, list):
            if suppress_errors: return None
            raise RuntimeError("音乐链接解析结果缺少albums列表")
        if "id" not in albums[0]:
            if suppress_errors: return None
            raise RuntimeError("音乐链接中没有解析到专辑")

        album_id = albums[0]["id"]
        album_source = albums[0].get("source")
        album_name = albums[0].get("name")

        await console.rp(f"信息提取完毕：{album_source}专辑：[{album_id}] {album_name}", f"[{level}]")

    except Exception as e:
        return await handle_exception(e)

    result = success_result(result=info_dict)
    result.get_extra()["type"] = "album"
    return result


async def get_info_playlist(api_url: str, music_url: str, suppress_errors: bool = False) -> Optional[Result]:
    """
    通过音乐链接获取歌单信息

    :param api_url: go-music-api 服务根地址
    :param music_url: 音乐平台的单曲分享链接
    :param suppress_errors: 出现错误时是否阻止异常抛出
    :return: 包含歌曲信息或异常的统一结果字典
    """
    try:
        music_url = str(music_url).strip()

        # 请求链接解析接口
        timeout = aiohttp.ClientTimeout(total=20, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            result = await request_json(
                api_url_format(api_url),
                session,
                "/api/v1/music/search",
                {
                    "q": music_url,
                    "type": "playlist",
                },
            )

        info_dict = result.get("data")
        if not isinstance(info_dict, dict):
            if suppress_errors: return None
            raise RuntimeError("音乐链接解析结果缺少data对象")

        playlists = info_dict.get("playlists")
        if not isinstance(playlists, list):
            if suppress_errors: return None
            raise RuntimeError("音乐链接解析结果缺少playlists列表")
        if len(playlists) <= 0:
            if suppress_errors: return None
            raise RuntimeError("音乐链接中没有解析到歌单")

        playlist_id = playlists[0]["id"]
        playlist_source = playlists[0].get("source")
        playlist_name = playlists[0].get("name")

        await console.rp(f"信息提取完毕：{playlist_source}歌单：[{playlist_id}] {playlist_name}", f"[{level}]")

    except Exception as e:
        return await handle_exception(e)

    result = success_result(result=info_dict)
    result.get_extra()["type"] = "playlist"
    return result


async def get_info(api_url: str, music_url: str) -> Result:
    """
    通过音乐链接获取歌曲信息

    :param api_url: go-music-api 服务根地址
    :param music_url: 音乐平台的单曲分享链接
    :return: 包含歌曲信息或异常的统一结果字典
    """
    try:
        music_url = str(music_url).strip()

        await console.rp(f"开始提取信息：{music_url}", f"[{level}]")

        # 请求链接解析接口
        timeout = aiohttp.ClientTimeout(total=20, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            result = await request_json(
                api_url_format(api_url),
                session,
                "/api/v1/music/search",
                {
                    "q": music_url,
                    "type": "song",
                },
            )

        info_dict = result.get("data")
        if not isinstance(info_dict, dict):
            raise RuntimeError("音乐链接解析结果缺少data对象")

        songs = info_dict.get("songs")
        if not isinstance(songs, list):
            raise RuntimeError("音乐链接解析结果缺少songs列表")

        extra_info: Dict[str, Any] = {
            "type": "song",
            "playlist_info_dict": None,
            "album_info_dict": None,
        }

        if len(songs) <= 0:
            raise RuntimeError("音乐链接中没有解析到歌曲")
        # 单曲
        elif len(songs) == 1:
            target_id = info_dict["songs"][0]['id']
        # 目标可能为歌单，尝试以歌单方式解析
        else:
            playlist_info_dict_result = await get_info_playlist(api_url, music_url, suppress_errors=True)
            if playlist_info_dict_result is not None and playlist_info_dict_result.result is not None:
                playlist_info_dict = playlist_info_dict_result.result
                extra_info["type"] = "playlist"
                extra_info["playlist_info_dict"] = playlist_info_dict
                target_id = playlist_info_dict["playlists"][0]['id']
            else:
                album_info_dict_result = await get_info_album(api_url, music_url, suppress_errors=True)
                if album_info_dict_result is not None and album_info_dict_result.result is not None:
                    album_info_dict = album_info_dict_result.result
                    extra_info["type"] = "album"
                    extra_info["album_info_dict"] = album_info_dict
                    target_id = album_info_dict["albums"][0]['id']
                # 错误分支，回退至第一音频id
                else:
                    target_id = info_dict["songs"][0]['id']

        await console.rp(f"信息提取完毕：{music_url} [{target_id}]", f"[{level}]")
    except Exception as e:
        return await handle_exception(e)

    result = success_result(result=info_dict)
    result.extra = extra_info
    return result


async def get_filesize(api_url: str, info_dict: dict) -> Result:
    request_url = f"{api_url_format(api_url)}/api/v1/music/stream"
    try:
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(request_url, params=build_music_params(info_dict), headers={"Range": "bytes=0-0"}) as response:
                if response.status == 206:
                    content_range = response.headers.get("Content-Range", "")
                    total_size = content_range.rsplit("/", 1)[-1]

                    if total_size and total_size != "*":
                        return success_result(result=int(total_size))

                # 某些情况可能不支持Range，而直接返回完整响应
                elif response.status == 200:
                    content_length = response.headers.get("Content-Length")
                    if content_length is not None:
                        return success_result(result=int(content_length))

                # 资源受限，go-music-api返回404 Failed to get URL
                elif response.status == 404:
                    body = await response.text(errors="replace")
                    raise errors.ResourceRestrictedError(f"{info_dict['source']}_{info_dict['id']}: {info_dict['name']} 疑似资源受限，状态码：{response.status}，{body}")

                else:
                    body = await response.text(errors="replace")
                    raise RuntimeError(f"状态码：{response.status}，{body}")

                raise RuntimeError("获取文件大小失败，响应中不存在有效的Content-Range或Content-Length")
    except Exception as e:
        return await handle_exception(e)


def construct_uid(source, song_id) -> str:
    return f"{source}_{song_id}"


def extension_format(value: Any) -> str:
    """
    将接口返回的扩展名转换为安全的音频扩展名

    :param value: 接口返回的原始扩展名
    :return: 清理后的扩展名
    """
    extension = str(value or "").strip().lstrip(".").lower()
    extension = re.sub(r"[^a-z0-9]", "", extension)
    if not extension or len(extension) > 10:
        return "mp3"

    return extension


def detect_stream_extension(content_type: Optional[str], first_chunk: bytes, fallback: Any) -> str:
    """
    根据响应类型和文件头识别实际音频扩展名

    :param content_type: 音频流响应的 Content-Type
    :param first_chunk: 音频流的首个数据块
    :param fallback: 无法识别时使用的扩展名
    :return: 识别后的音频扩展名
    """
    # 优先使用文件签名识别实际容器格式
    if first_chunk.startswith(b"ID3"):
        return "mp3"
    if first_chunk.startswith(b"fLaC"):
        return "flac"
    if first_chunk.startswith(b"OggS"):
        return "ogg"
    if first_chunk.startswith(b"RIFF") and first_chunk[8:12] == b"WAVE":
        return "wav"
    if len(first_chunk) >= 8 and first_chunk[4:8] == b"ftyp":
        return "m4a"
    if first_chunk.startswith(b"\x1a\x45\xdf\xa3"):
        return "webm"

    # 使用标准 Content-Type 映射
    normalized_content_type = str(content_type or "").split(";", 1)[0]
    normalized_content_type = normalized_content_type.strip().lower()
    content_type_extensions = {
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/mp4": "m4a",
        "audio/x-m4a": "m4a",
        "video/mp4": "m4a",
        "audio/flac": "flac",
        "audio/x-flac": "flac",
        "audio/ogg": "ogg",
        "application/ogg": "ogg",
        "audio/wav": "wav",
        "audio/wave": "wav",
        "audio/x-wav": "wav",
        "audio/aac": "aac",
        "audio/webm": "webm",
        "video/webm": "webm",
    }
    detected_extension = content_type_extensions.get(normalized_content_type)
    if detected_extension is not None:
        return detected_extension

    # 第三阶段无法识别时使用接口扩展名
    return extension_format(fallback)


async def download_to_file(api_url: str, session: aiohttp.ClientSession, info_dict: Dict[str, Any], download_dir: Union[str, Path]) -> Tuple[Path, int]:
    """
    从音频流接口分块下载音频并原子保存到UID对应的确定路径

    :param api_url: go-music-api服务根地址
    :param session: aiohttp客户端会话
    :param info_dict: 标准化后的歌曲信息字典
    :param download_dir: 音频下载目录
    :return: 最终音频路径和实际下载字节数
    """
    stream_params = build_music_params(info_dict)
    stream_url = f"{api_url_format(api_url)}/api/v1/music/stream"
    uid = construct_uid(info_dict["source"], info_dict["id"])

    # 初始化临时文件状态
    part_path: Optional[Path] = None
    part_created = False

    try:
        # 请求go-music-api代理音频流
        async with session.get(stream_url, params=stream_params) as response:
            response.raise_for_status()
            # 资源受限，go-music-api返回404 Failed to get URL
            if response.status == 404:
                body = await response.text(errors="replace")
                raise errors.ResourceRestrictedError(f"{info_dict['source']}_{info_dict['id']}: {info_dict['name']} 疑似资源受限，状态码：{response.status}，{body}")
            elif response.status not in (200, 206):
                raise RuntimeError(
                    f"音频流返回不支持的HTTP状态：{response.status}"
                )

            expected_size = response.content_length
            first_chunk = await response.content.read(CHUNK_SIZE)

            # 创建并校验下载目录
            download_dir = Path(download_dir).expanduser()
            download_dir.mkdir(parents=True, exist_ok=True)
            if not download_dir.is_dir():
                raise RuntimeError(f"下载路径不是目录：{download_dir}")

            # 整理文件名所需的歌曲信息
            if "artist" not in info_dict or info_dict["artist"] is None or info_dict["artist"].strip() == "":
                artist = "未知歌手"
            else:
                artist = info_dict["artist"].strip()

            if "name" not in info_dict or info_dict["name"] is None or info_dict["name"].strip() == "":
                title = "未知歌曲"
            else:
                title = info_dict["name"].strip()

            # 根据真实响应确定扩展名和目标路径
            file_extension = extension_format(
                detect_stream_extension(
                    response.headers.get("Content-Type"),
                    first_chunk,
                    info_dict.get("ext")
                )
            )

            # 使用UID构造确定的文件名
            file_title = utils.legal_name(f"{uid} - {artist} - {title}")
            download_path = download_dir / f"{file_title}.{file_extension}"

            part_path = download_path.with_name(f"{download_path.name}.part")
            await console.rp(f"开始下载：{download_path.name}", f"[{level}]",)

            # 将响应分块写入独立临时文件
            downloaded_size = len(first_chunk)
            with part_path.open("xb") as file:
                part_created = True

                if first_chunk:
                    file.write(first_chunk)

                async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                    if not chunk:
                        continue

                    file.write(chunk)
                    downloaded_size += len(chunk)

                file.flush()
                os.fsync(file.fileno())

        # 校验下载结果
        if downloaded_size <= 0:
            raise RuntimeError("音频流为空，没有下载到任何数据")

        if expected_size is not None and downloaded_size != expected_size:
            raise RuntimeError(f"音频下载不完整，预期 {expected_size} 字节，实际 {downloaded_size} 字节")

        # 使用完整临时文件原子替换正式文件
        part_path.replace(download_path)
        return download_path, downloaded_size

    except BaseException:
        # 下载失败或任务取消时只删除当前任务创建的临时文件
        if part_created and part_path is not None and part_path.exists():
            try:
                part_path.unlink()
            except OSError:
                pass
        raise


async def audio_download(api_url: str, info_dict: Dict[str, Any], download_dir: Union[str, Path], download_type: DownloadType) -> Result:
    """
    使用歌曲信息下载音频并创建 Audio 对象

    :param api_url: go-music-api服务根地址
    :param info_dict: get_info返回的歌曲信息字典
    :param download_dir: 音频下载目录
    :param download_type: 写入Audio对象的下载来源类型
    :return: 包含 Audio 对象或异常的统一结果字典
    """
    try:
        if resource_classifier.handler(download_type) is not DownloadHandler.GO_MUSIC_API:
            raise ValueError(f"错误下载类型：{download_type.name}")

        timeout = aiohttp.ClientTimeout(
            total=None,
            connect=10,
            sock_connect=10,
            sock_read=60,
        )
        async with aiohttp.ClientSession(timeout=timeout) as session:
            target_path, downloaded_size = await download_to_file(
                api_url,
                session,
                info_dict,
                download_dir,
            )

        converted_size = utils.convert_byte(downloaded_size)
        await console.rp(
            f"下载完成\n"
            f"文件名：{target_path.name}\n"
            f"来源：[{SOURCE_MAP[info_dict['source']]}] {info_dict['id']}\n"
            f"路径：{target_path.parent}\n"
            f"大小：{converted_size[0]} {converted_size[1]}\n"
            f"时长：{utils.convert_duration_to_str(info_dict['duration'])}",
            f"[{level}]",
        )

        new_audio = audio.Audio(
            title=info_dict["name"],
            uid=f"{info_dict['source']}_{info_dict['id']}",
            source=info_dict["source"],
            source_id=info_dict['id'],
            download_type=download_type,
            path=str(target_path),
            duration=info_dict["duration"],
        )

        if "cover" in info_dict:
            new_audio.set_cover_url(info_dict["cover"])

    except Exception as exception:
        return await handle_exception(exception)

    return success_result(result=new_audio)
