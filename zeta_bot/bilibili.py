from typing import *
import os
import time
import asyncio
import aiohttp
import html
import httpx
from enum import Enum

import bilibili_api
from bilibili_api import video, Credential, sync, select_client
from bilibili_api import search as bilibili_search

import errors
import utils
from utils import Result, success_result, failed_result

from zeta_bot import (
    output_console,
    audio
)
from zeta_bot.resource import MediaPlatform, LinkType, DownloadHandler, DownloadType, ResourceClassifier

# https://bili.moyu.moe/#/examples/video

# 设定请求库
select_client("curl_cffi")

SESSDATA = ""
BILI_JCT = ""
BUVID3 = ""

# FFMPEG 路径，查看：http://ffmpeg.org/
FFMPEG_PATH = "./zeta_bot/bin/ffmpeg"

# 设置控制台
console = output_console.Console()

# 加载资源分类器
resource_classifier = ResourceClassifier()

level = "哔哩哔哩模块"
SOURCE = "bilibili"

# 下载分块大小
CHUNK_SIZE = 64 * 1024
# 音频流地址缓存时间（秒），避免获取文件大小与下载时重复请求
AUDIO_URL_CACHE_TTL = 600
_audio_url_cache: Dict[Tuple[str, int], Tuple[float, str]] = {}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/"
}


def _credential() -> Optional[Credential]:
    """
    未设置登录信息时返回None，由bilibili-api自动生成buvid等指纹Cookie
    """
    if SESSDATA or BILI_JCT or BUVID3:
        return Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
    return None


async def _fetch_view(v: video.Video) -> dict:
    """
    获取视频信息
    旧版接口 x/web-interface/view 对未登录请求触发风控（HTTP 412），优先使用带wbi签名的 x/web-interface/wbi/view/detail
    """
    try:
        detail = await v.get_detail()
        view = detail.get("View") if isinstance(detail, dict) else None
        if view:
            return view
    except bilibili_api.NetworkException:
        pass
    return await v.get_info()


async def _get_audio_url(info_dict: dict, num_p: int = 0) -> str:
    """
    获取音频流地址
    直接传入cid，否则bilibili-api会先调用已被风控的旧版信息接口获取cid
    """
    bvid = info_dict["bvid"]
    cid = int(info_dict["pages"][num_p]["cid"])
    key = (bvid, cid)

    cached = _audio_url_cache.get(key)
    if cached is not None and time.monotonic() - cached[0] < AUDIO_URL_CACHE_TTL:
        return cached[1]

    v = video.Video(bvid=bvid, credential=_credential())
    url_info = await v.get_download_url(cid=cid)

    if "dash" in url_info and url_info["dash"].get("audio"):
        best_audio = max(url_info["dash"]["audio"], key=lambda item: item.get("bandwidth", 0))
        audio_url = best_audio.get("baseUrl") or best_audio.get("base_url")
    elif url_info.get("durl"):
        # 部分老视频不提供DASH格式，使用音视频合流地址，FFmpeg可直接从中读取音轨
        audio_url = url_info["durl"][0]["url"]
    else:
        raise bilibili_api.ResponseCodeException(-1, "未获取到音频流地址", url_info)

    _audio_url_cache[key] = (time.monotonic(), audio_url)
    return audio_url


async def get_info(bvid) -> Result:
    """
    返回视频信息

    :param bvid: 目标视频BV号
    :return:
    """
    await console.rp(f"开始提取信息：{bvid}", f"[{level}]")

    try:
        # 实例化 Video 类
        v = video.Video(bvid=bvid, credential=_credential())
        # 获取视频信息
        info_dict = await _fetch_view(v)

        video_id = info_dict["bvid"]
        video_title = info_dict["title"]
        await console.rp(f"信息提取完毕：[{video_id}] {video_title}", f"[{level}]")

    except bilibili_api.ResponseCodeException as e:
        await console.rp(
            f"触发异常bilibili_api.ResponseCodeException，哔哩哔哩无响应，{bvid}可能已失效或存在区域版权限制",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="无响应，资源可能已失效或存在区域版权限制", retryable=False)
    except bilibili_api.ArgsException as e:
        await console.rp(
            f"触发异常bilibili_api.ArgsException，{bvid}信息获取失败，参数异常，可能为bvid错误",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="参数错误，请检查链接中的BV号是否正确完整", retryable=False)
    except bilibili_api.NetworkException as e:
        await console.rp(
            f"触发异常bilibili_api.NetworkException，网络异常",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="哔哩哔哩连接异常", retryable=False)
    except aiohttp.ClientResponseError as e:
        await console.rp(
            f"触发异常aiohttp.ClientResponseError，{bvid}信息获取失败，可能为请求繁忙",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="请求繁忙", retryable=True)
    except httpx.ConnectTimeout as e:
        await console.rp(
            f"触发异常httpx.ConnectTimeout，{bvid}信息获取失败，网络主机连接超时",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="网络主机连接超时", retryable=True)
    except httpx.RemoteProtocolError as e:
        await console.rp(
            f"触发异常httpx.RemoteProtocolError，{bvid}信息获取失败，服务器协议错误",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="服务器协议错误", retryable=True)
    else:
        if info_dict is None:
            await console.rp(
                f"{bvid}返回信息为空，异常未捕获，请参照错误日志",
                f"[{level}]",
                message_type=utils.PrintType.ERROR,
                print_head=True
            )
            return failed_result(exception=None, message="结果为空，未知错误", retryable=False)
        else:
            return success_result(result=info_dict)


async def get_filesize(info_dict: dict, num_p=0) -> Result:
    bvid = info_dict["bvid"]
    try:
        # 音频轨链接
        audio_url = await _get_audio_url(info_dict, num_p)

        timeout = aiohttp.ClientTimeout(total=20, connect=10)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            # 只读取响应头
            async with sess.get(audio_url, headers=HEADERS) as resp:
                resp.raise_for_status()
                length = resp.headers.get('content-length')

    except bilibili_api.ResponseCodeException as e:
        await console.rp(
            f"触发异常bilibili_api.ResponseCodeException，哔哩哔哩无响应，{bvid}可能已失效或存在区域版权限制",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="无响应，资源可能已失效或存在区域版权限制", retryable=False)
    except bilibili_api.ArgsException as e:
        await console.rp(
            f"触发异常bilibili_api.ArgsException，{bvid}获取失败，参数异常，可能为bvid错误",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="参数错误，请检查链接中的BV号是否正确完整", retryable=False)
    except bilibili_api.NetworkException as e:
        await console.rp(
            f"触发异常bilibili_api.NetworkException，网络异常",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="哔哩哔哩连接异常", retryable=False)
    except aiohttp.ClientResponseError as e:
        await console.rp(
            f"触发异常aiohttp.ClientResponseError，{bvid}获取失败，可能为请求繁忙",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="请求繁忙", retryable=True)
    except httpx.ConnectTimeout as e:
        await console.rp(
            f"触发异常httpx.ConnectTimeout，{bvid}获取失败，网络主机连接超时",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="网络主机连接超时", retryable=True)
    except httpx.RemoteProtocolError as e:
        await console.rp(
            f"触发异常httpx.RemoteProtocolError，{bvid}获取失败，服务器协议错误",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="服务器协议错误", retryable=True)
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        await console.rp(
            f"触发异常{type(e).__name__}，{bvid}获取失败，网络连接异常",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="网络连接异常", retryable=True)
    else:
        try:
            length = int(length)
        except (TypeError, ValueError) as e:
            await console.rp(
                f"{bvid}文件大小获取失败，获取到的结果不为数字",
                f"[{level}]",
                message_type=utils.PrintType.ERROR,
                print_head=True
            )
            return failed_result(exception=e, message="结果为空，未知错误", retryable=False)
        else:
            return success_result(result=length)


def construct_uid(bvid: str, download_type: DownloadType, num_p: int) -> str:
    if resource_classifier.handler(download_type) is not DownloadHandler.BILIBILI_API_PYTHON:
        raise ValueError(f"错误下载类型：{download_type.name}")
    uid = f"{SOURCE}_{bvid}"
    if download_type is DownloadType.BILIBILI_P:
        uid += f"_p{str(num_p + 1)}"
    return uid


# TODO 检查下载报错代码，是否和异步并发有关
# aiohttp.http_exceptions.ContentLengthError: 400, message:
#   Not enough data to satisfy content length header.
# aiohttp.client_exceptions.ClientPayloadError: Response payload is not completed: <ContentLengthError: 400, message='Not enough data to satisfy content length header.'>

async def audio_download(info_dict: dict, download_dir: str, download_type: DownloadType = DownloadType.BILIBILI_SINGLE, num_p=0) -> Result:
    """
    使用bilibili_api，下载来自哔哩哔哩的音频
    """
    if resource_classifier.handler(download_type) is not DownloadHandler.BILIBILI_API_PYTHON:
        raise ValueError(f"错误下载类型：{download_type.name}")

    bvid = info_dict["bvid"]
    if download_type is DownloadType.BILIBILI_P:
        title = info_dict["pages"][num_p]["part"]
    # 普通下载
    else:
        title = info_dict["title"]

    duration = int(info_dict["pages"][num_p]["duration"])
    uid = construct_uid(bvid=bvid, download_type=download_type, num_p=num_p)
    file_title = utils.legal_name(f"{uid} - {title}")
    download_path = f"{download_dir}/{file_title}.mp3"

    try:
        # 音频轨链接
        audio_url = await _get_audio_url(info_dict, num_p)

        timeout = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=30)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            # 下载音频流
            async with sess.get(audio_url, headers=HEADERS) as resp:
                resp.raise_for_status()
                length = resp.headers.get('content-length')
                size = utils.convert_byte(int(length)) if length is not None else ("?", "")
                await console.rp(f"开始下载：{file_title}.mp3 大小：{size[0]} {size[1]}", f"[{level}]")
                with open(download_path, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                        f.write(chunk)

        size = utils.convert_byte(os.path.getsize(download_path))

        new_audio = audio.Audio(
            title=title,
            uid=uid,
            source=SOURCE,
            source_id=bvid,
            download_type=download_type,
            path=download_path,
            duration=duration
        )

        if "pic" in info_dict.keys():
            new_audio.set_cover_url(info_dict["pic"])

        if download_type is DownloadType.BILIBILI_P:
            logger_prompt = (
                f"下载完成\n"
                f"文件名：{file_title}.mp3\n"
                f"来源：[哔哩哔哩] {bvid}\n"
                f"分P号：{num_p + 1}\n"
                f"路径：{download_dir}\n"
                f"大小：{size[0]} {size[1]}\n"
                f"时长：{utils.convert_duration_to_str(duration)}"
            )
        else:
            logger_prompt = (
                f"下载完成\n"
                f"文件名：{file_title}.mp3\n"
                f"来源：[哔哩哔哩] {bvid}\n"
                f"路径：{download_dir}\n"
                f"大小：{size[0]} {size[1]}\n"
                f"时长：{utils.convert_duration_to_str(duration)}"
            )
        await console.rp(logger_prompt, f"[{level}]")

    except bilibili_api.ResponseCodeException as e:
        await console.rp(
            f"触发异常bilibili_api.ResponseCodeException，哔哩哔哩无响应，{title}可能已失效或存在区域版权限制",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="无响应，资源可能已失效或存在区域版权限制", retryable=False)
    except bilibili_api.ArgsException as e:
        await console.rp(
            f"触发异常bilibili_api.ArgsException，{title}获取失败，参数异常，可能为bvid错误",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="参数错误，请检查链接中的BV号是否正确完整", retryable=False)
    except bilibili_api.NetworkException as e:
        await console.rp(
            f"触发异常bilibili_api.NetworkException，网络异常",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="哔哩哔哩连接异常", retryable=False)
    except aiohttp.ClientResponseError as e:
        await console.rp(
            f"触发异常aiohttp.ClientResponseError，{title}获取失败，可能为请求繁忙",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="请求繁忙", retryable=True)
    except httpx.ConnectTimeout as e:
        await console.rp(
            f"触发异常httpx.ConnectTimeout，{title}获取失败，网络主机连接超时",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="网络主机连接超时", retryable=True)
    except httpx.RemoteProtocolError as e:
        await console.rp(
            f"触发异常httpx.RemoteProtocolError，{title}获取失败，服务器协议错误",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="服务器协议错误", retryable=True)
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        # 删除下载不完整的文件
        if os.path.exists(download_path):
            try:
                os.remove(download_path)
            except OSError:
                pass
        await console.rp(
            f"触发异常{type(e).__name__}，{title}下载失败，网络连接异常",
            f"[{level}]",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return failed_result(exception=e, message="下载中断，网络连接异常", retryable=True)

    else:
        if new_audio is None:
            await console.rp(
                f"{title}音频对象返回为空，异常未捕获，请参照错误日志",
                f"[{level}]",
                message_type=utils.PrintType.ERROR,
                print_head=True
            )
            return failed_result(exception=None, message="结果为空，未知错误", retryable=False)
        else:
            return success_result(result=new_audio)


async def search(query, query_num=5) -> list:
    """
    搜索哔哩哔哩的视频，最大返回20个结果（一页）
    """
    query = query.strip()

    if query_num > 20:
        query_num = 20

    await console.rp(f"开始搜索：{query}", f"[{level}]")

    try:
        info_dict = await bilibili_search.search_by_type(query, search_type=bilibili_search.SearchObjectType.VIDEO)
    except Exception as e:
        await console.rp(f"搜索失败：触发异常{type(e).__name__}：{e}", f"[{level}]", message_type=utils.PrintType.ERROR, print_head=True)
        return []

    result = []
    log_message = f"搜索 {query} 结果为："
    counter = 1

    id_header = "https://www.bilibili.com/video/"

    for item in info_dict.get("result") or []:
        if counter > query_num:
            break

        title = html.unescape(item["title"])
        title = title.replace("<em class=\"keyword\">", "")
        title = title.replace("</em>", "")

        duration = utils.convert_str_to_duration(item["duration"])

        cover = item.get("pic") or ""
        if cover.startswith("//"):
            cover = "https:" + cover

        result.append(
            {
                "title": title,
                "id": id_header + item["bvid"],
                "duration": duration,
                "duration_str": utils.convert_duration_to_str(duration),
                "thumbnail": cover,
                "source": "bilibili",
            }
        )

        log_message += f"\n{counter}. {item['bvid']}：{title} [{item['duration']}]"
        counter += 1

    await console.rp(log_message, f"[{level}]")

    return result
