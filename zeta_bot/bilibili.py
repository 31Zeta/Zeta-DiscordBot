from typing import *
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

async def get_info(bvid) -> Result:
    """
    返回视频信息

    :param bvid: 目标视频BV号
    :return:
    """
    await console.rp(f"开始提取信息：{bvid}", f"[{level}]")

    try:
        # 实例化 Credential 类
        credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
        # 实例化 Video 类
        v = video.Video(bvid=bvid, credential=credential)
        # 获取视频信息
        info_dict = await v.get_info()

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
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/"
        }

        # 实例化 Credential 类
        credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
        # 实例化 Video 类
        v = video.Video(bvid=bvid, credential=credential)

        # 获取视频下载链接
        url = await v.get_download_url(num_p)

        # 音频轨链接
        audio_url = url["dash"]["audio"][0]['baseUrl']

        async with aiohttp.ClientSession() as sess:
            # 下载音频流
            async with sess.get(audio_url, headers=headers) as resp:
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
    else:
        try:
            length = int(length)
        except ValueError as e:
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
        # 实例化 Credential 类
        credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
        # 实例化 Video 类
        v = video.Video(bvid=bvid, credential=credential)

        # 获取视频下载链接
        url = await v.get_download_url(num_p)

        # 音频轨链接
        audio_url = url["dash"]["audio"][0]['baseUrl']

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/"
        }

        # print(current_time + f"\n    开始下载: {file_title}.mp3\n下载进度:")

        async with aiohttp.ClientSession() as sess:
            # 下载音频流
            async with sess.get(audio_url, headers=headers) as resp:
                length = resp.headers.get('content-length')
                size = utils.convert_byte(int(length))
                await console.rp(f"开始下载：{file_title}.mp3 大小：{size[0]} {size[1]}", f"[{level}]")
                with open(download_path, 'wb') as f:
                    process = 0
                    while True:
                        chunk = await resp.content.read(1024)
                        if not chunk:
                            break

                        process += len(chunk)
                        f.write(chunk)
                        # TODO 待定 可以添加聊天界面进度显示
                        # 旧版进度显示
                        # print(f'\r    {process} / {length}', end="")

        # print("\n\n" + current_time + f"\n    下载完成\n")

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

    info_dict = await bilibili_search.search_by_type(query, search_type=bilibili_search.SearchObjectType.VIDEO)

    result = []
    log_message = f"搜索 {query} 结果为："
    counter = 1

    id_header = "https://www.bilibili.com/video/"

    for item in info_dict["result"]:
        if counter > query_num:
            break

        title = html.unescape(item["title"])
        title = title.replace("<em class=\"keyword\">", "")
        title = title.replace("</em>", "")

        duration = utils.convert_str_to_duration(item["duration"])

        result.append(
            {
                "title": title,
                "id": id_header + item["bvid"],
                "duration": duration,
                "duration_str": utils.convert_duration_to_str(duration),
            }
        )

        log_message += f"\n{counter}. {item['bvid']}：{title} [{item['duration']}]"
        counter += 1

    await console.rp(log_message, f"[{level}]")

    return result
