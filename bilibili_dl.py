import re

from bilibili_api import video, Credential, favorite_list
import aiohttp
import os
import asyncio
import datetime

# https://bili.moyu.moe/#/examples/video

SESSDATA = ""
BILI_JCT = ""
BUVID3 = ""

# FFMPEG 路径，查看：http://ffmpeg.org/
FFMPEG_PATH = "./bin/ffmpeg"


async def bili_get_info(bvid) -> dict:
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


async def bili_get_title(bvid):
    """
    返回视频标题

    :param bvid: 目标视频BV号
    :return:
    """
    info_dict = await bili_get_info(bvid)
    title = info_dict["title"]
    title = bili_legal_name(title)

    return title


async def bili_get_duration(bvid):
    """
    返回视频的时长，以秒为单位

    :param bvid: 目标视频bv号
    :return:
    """
    info_dict = await bili_get_info(bvid)
    duration = int(info_dict["duration"])

    return duration


async def bili_get_title_duration(bvid):
    """
    返回视频标题\n
    返回视频的时长，以秒为单位\n

    本方法防止请求两遍info

    :param bvid: 目标视频bv号
    :return:
    """

    info_dict = await bili_get_info(bvid)

    title = info_dict["title"]
    title = bili_legal_name(title)

    duration = int(info_dict["duration"])

    return title, duration


def bili_legal_name(name_str: str) -> str:
    """
    将字符串转换为合法的文件名

    :param name_str: 原文件名
    :return: 转换后文件名
    """

    name_str = name_str.replace("\\", "")
    name_str = name_str.replace("/", "")
    name_str = name_str.replace(":", "")
    name_str = name_str.replace("*", "")
    name_str = name_str.replace("?", "")
    name_str = name_str.replace("\"", "")
    name_str = name_str.replace("<", "")
    name_str = name_str.replace(">", "")
    name_str = name_str.replace("|", "")

    return name_str


def bili_get_bvid(url):
    """
    提取目标地址对应的BV号

    :param url: 目标地址
    :return:
    """
    re_result = re.search("BV(\d|[a-zA-Z]){10}", url)

    if re_result is None:
        return "error_bvid"

    bvid_start = re_result.span()[0]
    bvid_end = re_result.span()[1]
    result = url[bvid_start:bvid_end]

    return result


async def bili_video_download(bvid):
    # 实例化 Credential 类
    credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
    # 实例化 Video 类
    v = video.Video(bvid=bvid, credential=credential)
    # 获取视频下载链接
    url = await v.get_download_url(0)
    # 视频轨链接
    video_url = url["dash"]["video"][0]['baseUrl']
    # 音频轨链接
    audio_url = url["dash"]["audio"][0]['baseUrl']
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bilibili.com/"
    }
    async with aiohttp.ClientSession() as sess:
        # 下载视频流
        async with sess.get(video_url, headers=headers) as resp:
            length = resp.headers.get('content-length')
            with open('video_temp.m4s', 'wb') as f:
                process = 0
                while True:
                    chunk = await resp.content.read(1024)
                    if not chunk:
                        break

                    process += len(chunk)
                    print(f'下载视频流 {process} / {length}')
                    f.write(chunk)

        # 下载音频流
        async with sess.get(audio_url, headers=headers) as resp:
            length = resp.headers.get('content-length')
            with open('audio_temp.m4s', 'wb') as f:
                process = 0
                while True:
                    chunk = await resp.content.read(1024)
                    if not chunk:
                        break

                    process += len(chunk)
                    print(f'下载音频流 {process} / {length}')
                    f.write(chunk)

        # 混流
        print('混流中')
        os.system(f'{FFMPEG_PATH}'
                  f' -i video_temp.m4s -i audio_temp.m4s '
                  f'-vcodec copy -acodec copy video.mp4')

        # 删除临时文件
        os.remove("video_temp.m4s")
        os.remove("audio_temp.m4s")

        print('已下载为：video.mp4')


async def bili_audio_download(bvid, info_dict, download_type="bili_single",
                              num_p=0):
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
    title = bili_legal_name(title)
    duration = int(info_dict["pages"][num_p]["duration"])

    # # 检查重名文件
    # num = 0
    # new_title = title
    # while os.path.exists(f"./downloads/{title}.mp3"):
    #     num += 1
    #     new_title = title + f"_{num}"

    path = f"./downloads/{title}.mp3"

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

    return original_title, path, duration


if __name__ == '__main__':
    a = asyncio.get_event_loop().run_until_complete(
        bili_audio_download("BV1Hx411A7QU")
    )
    print(a)
