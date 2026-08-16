from __future__ import unicode_literals
from typing import *
from enum import Enum

import yt_dlp
from yt_dlp import YoutubeDL

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

async def get_info(url, cookie_file_path=None) -> Result:
    ydl_opts = {
        'format': 'bestaudio/best',
        'extract_flat': True,
        "quiet": True,
    }
    if cookie_file_path is not None:
        ydl_opts["cookiefile"] = str(cookie_file_path)

    await console.rp(f"开始提取信息：{url}", f"[{level}]")

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)

        video_id = info_dict["id"]
        video_title = info_dict["title"]

        await console.rp(f"信息提取完毕：[{video_id}] {video_title}", f"[{level}]")

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
    if "filesize" in info_dict:
        return success_result(result=info_dict["filesize"])
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
    video_title = info_dict["title"]
    file_extension = info_dict["ext"]
    video_duration = info_dict["duration"]
    size = utils.convert_byte(int(info_dict["filesize"]))

    uid = construct_uid(video_id=video_id, download_type=download_type)
    file_title = utils.legal_name(f"{uid} - {video_title}")
    download_path = f"{download_dir}/{file_title}.{file_extension}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": download_path,
        "extract_flat": True,
        "quiet": True,
    }

    if cookie_file_path is not None:
        ydl_opts["cookiefile"] = str(cookie_file_path)

    await console.rp(f"开始下载：{file_title}.{file_extension}", f"[{level}]")

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

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

    for item in extracted_info["entries"]:
        if counter > query_num:
            break
        result.append(
            {
                "title": item["title"],
                "id": id_header + item["id"],
                "duration": item["duration"],
                "duration_str": utils.convert_duration_to_str(item["duration"]),
            }
        )
        log_message += f"\n{counter}. {item['id']}：{item['title']} [{utils.convert_duration_to_str(item['duration'])}]"
        counter += 1

    await console.rp(log_message, f"[{level}]")

    return result
