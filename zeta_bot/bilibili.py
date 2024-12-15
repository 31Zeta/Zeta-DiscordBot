from typing import *
import aiohttp
import html
from bilibili_api import video, Credential, sync
from bilibili_api import search as bilibili_search

from zeta_bot import (
    console,
    utils,
    audio
)

# https://bili.moyu.moe/#/examples/video

SESSDATA = ""
BILI_JCT = ""
BUVID3 = ""

# FFMPEG 路径，查看：http://ffmpeg.org/
FFMPEG_PATH = "./zeta_bot/bin/ffmpeg"

# 控制台设置
console = console.Console()

level = "哔哩哔哩模块"

async def get_info(bvid) -> dict:
    """
    返回视频信息

    :param bvid: 目标视频BV号
    :return:
    """
    await console.rp(f"开始提取信息：{bvid}", f"[{level}]")

    # 实例化 Credential 类
    credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
    # 实例化 Video 类
    v = video.Video(bvid=bvid, credential=credential)
    # 获取视频信息
    info_dict = await v.get_info()

    video_id = info_dict["bvid"]
    video_title = info_dict["title"]
    await console.rp(f"信息提取完毕：{video_title} [{video_id}]", f"[{level}]")

    return info_dict


async def get_filesize(info_dict: dict, num_p=0) -> Union[int, None]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bilibili.com/"
    }

    bvid = info_dict["bvid"]
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
            return int(length)


async def audio_download(info_dict: dict, download_path: str, download_type="bilibili_single", num_p=0) -> audio.Audio:
    """
    使用bilibili_api，下载来自哔哩哔哩的音频
    需要处理以下异常：
        - bilibili_api.ResponseCodeException 接口无响应（视频不存在）
        - bilibili_api.ArgsException 参数错误（bvid错误）
        - httpx.ConnectTimeout 连接超时（可重试）
        - httpx.RemoteProtocolError 服务器违反了协议（可重试）
    """
    bvid = info_dict["bvid"]
    # 实例化 Credential 类
    credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)
    # 实例化 Video 类
    v = video.Video(bvid=bvid, credential=credential)

    if download_type == "bilibili_p":
        title = info_dict["pages"][num_p]["part"]
    # 普通下载
    else:
        title = info_dict["title"]

    original_title = title
    title = utils.legal_name(title)
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

    # print(current_time + f"\n    开始下载: {title}.mp3\n下载进度:")

    async with aiohttp.ClientSession() as sess:
        # 下载音频流
        async with sess.get(audio_url, headers=headers) as resp:
            length = resp.headers.get('content-length')
            size = utils.convert_byte(int(length))
            await console.rp(f"开始下载：{title}.mp3 大小：{size[0]} {size[1]}", f"[{level}]")
            with open(path, 'wb') as f:
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

    new_audio = audio.Audio(original_title, download_type, bvid, path, duration)
    if download_type == "bilibili_p":
        logger_prompt = (
            f"下载完成\n"
            f"文件名：{title}.mp3\n"
            f"来源：[哔哩哔哩] {bvid}\n"
            f"分P号：{num_p + 1}\n"
            f"路径：{download_path}\n"
            f"大小：{size[0]} {size[1]}\n"
            f"时长：{utils.convert_duration_to_str(duration)}"
        )
    else:
        logger_prompt = (
            f"下载完成\n"
            f"文件名：{title}.mp3\n"
            f"来源：[哔哩哔哩] {bvid}\n"
            f"路径：{download_path}\n"
            f"大小：{size[0]} {size[1]}\n"
            f"时长：{utils.convert_duration_to_str(duration)}"
        )
    await console.rp(logger_prompt, f"[{level}]")

    return new_audio


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
