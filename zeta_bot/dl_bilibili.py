from bilibili_api import video, Credential
import aiohttp
import datetime
from zeta_bot import (
    audio
)

# https://bili.moyu.moe/#/examples/video

SESSDATA = ""
BILI_JCT = ""
BUVID3 = ""

# FFMPEG 路径，查看：http://ffmpeg.org/
FFMPEG_PATH = "./bin/ffmpeg"


async def get_info(bvid) -> dict:
    """
    返回视频信息

    :param bvid: 目标视频BV号
    :return:
    """
    # 实例化 Credential 类
    credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
    # 实例化 Video 类
    v = video.Video(bvid=bvid, credential=credential)
    # 获取视频信息
    info = await v.get_info()
    return info


async def get_title(bvid):
    """
    返回视频标题

    :param bvid: 目标视频BV号
    :return:
    """
    info_dict = await get_info(bvid)
    title = info_dict["title"]
    title = legal_name(title)

    return title


async def get_duration(bvid):
    """
    返回视频的时长，以秒为单位

    :param bvid: 目标视频bv号
    :return:
    """
    info_dict = await get_info(bvid)
    duration = int(info_dict["duration"])

    return duration


async def get_title_duration(bvid):
    """
    返回视频标题\n
    返回视频的时长，以秒为单位\n

    本方法防止请求两遍info

    :param bvid: 目标视频bv号
    :return:
    """

    info_dict = await get_info(bvid)

    title = info_dict["title"]
    title = legal_name(title)

    duration = int(info_dict["duration"])

    return title, duration


def legal_name(name_str: str) -> str:
    """
    将字符串转换为合法的文件名

    :param name_str: 原文件名
    :return: 转换后文件名
    """

    name_str = name_str.replace("\\", "_")
    name_str = name_str.replace("/", "_")
    name_str = name_str.replace(":", "_")
    name_str = name_str.replace("*", "_")
    name_str = name_str.replace("?", "_")
    name_str = name_str.replace("\"", "_")
    name_str = name_str.replace("<", "_")
    name_str = name_str.replace(">", "_")
    name_str = name_str.replace("|", "_")

    return name_str


async def audio_download(bvid: str, info_dict: dict, download_path: str,
                         download_type="bili_single", num_p=0) -> audio.Audio:
    # 实例化 Credential 类
    credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
    # 实例化 Video 类
    v = video.Video(bvid=bvid, credential=credential)

    if download_type == "bili_p":
        title = info_dict["pages"][num_p]["part"]
    # 普通下载
    else:
        title = info_dict["title"]

    original_title = title
    title = legal_name(title)
    duration = int(info_dict["pages"][num_p]["duration"])

    path = f"{download_path}/{title}.mp3"

    # 获取视频下载链接
    url = await v.get_download_url(num_p)

    # 音频轨链接
    audio_url = url["dash"]["audio"][0]['baseUrl']

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bilibili.com/"
    }

    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f"\n    开始下载: {title}.mp3\n下载进度:")

    async with aiohttp.ClientSession() as sess:
        # 下载音频流
        async with sess.get(audio_url, headers=headers) as resp:
            length = resp.headers.get('content-length')
            with open(path, 'wb') as f:
                process = 0
                while True:
                    chunk = await resp.content.read(1024)
                    if not chunk:
                        break

                    process += len(chunk)
                    print(f'\r    {process} / {length}', end="")
                    f.write(chunk)

    current_time = str(datetime.datetime.now())[:19]
    print("\n\n" + current_time + f"\n    下载完成\n")

    new_audio = audio.Audio(original_title, download_type, bvid, path, duration)

    return new_audio
