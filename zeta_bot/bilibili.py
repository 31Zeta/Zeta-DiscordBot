from bilibili_api import video, Credential
import aiohttp
from zeta_bot import (
    log,
    utils,
    audio
)

# https://bili.moyu.moe/#/examples/video

SESSDATA = ""
BILI_JCT = ""
BUVID3 = ""

# FFMPEG 路径，查看：http://ffmpeg.org/
FFMPEG_PATH = "./zeta_bot/bin/ffmpeg"

# logger = log.Log()
level = "哔哩哔哩模块"


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
    title = utils.legal_name(title)

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
    title = utils.legal_name(title)

    duration = int(info_dict["duration"])

    return title, duration


async def audio_download(info_dict: dict, download_path: str, download_type="bili_single", num_p=0) -> audio.Audio:
    """
    使用bilibili_api，下载来自哔哩哔哩的音频
    需要处理以下异常：
        - bilibili_api.ResponseCodeException 接口无响应（视频不存在）
        - bilibili_api.ArgsException 参数错误（bvid错误）
        - httpx.ConnectTimeout 无响应（可重试）
        - httpx.RemoteProtocolError 无响应（可重试）
    """
    # 获取日志记录器
    logger = log.Log()

    bvid = info_dict["bvid"]
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

    # 处理 bilibili_api.exceptions.ArgsException.ArgsException: bvid 提供错误，必须是以 BV 开头的纯字母和数字组成的 12 位字符串（大小写敏感）。
    # bilibili_api.exceptions.ResponseCodeException.ResponseCodeException

    async with aiohttp.ClientSession() as sess:
        # 下载音频流
        async with sess.get(audio_url, headers=headers) as resp:
            length = resp.headers.get('content-length')
            size = utils.convert_byte(int(length))
            logger.rp(f"开始下载：{title}.mp3 大小：{size[0]} {size[1]}", f"[{level}]")
            with open(path, 'wb') as f:
                process = 0
                while True:
                    chunk = await resp.content.read(1024)
                    if not chunk:
                        break

                    process += len(chunk)
                    f.write(chunk)
                    # TODO 添加聊天界面进度显示
                    # 旧版进度显示
                    # print(f'\r    {process} / {length}', end="")

    # print("\n\n" + current_time + f"\n    下载完成\n")

    new_audio = audio.Audio(original_title, download_type, bvid, path, duration)
    logger.rp(
        f"下载完成\n"
        f"文件名：{title}.mp3\n"
        f"来源：{bvid}\n"
        f"路径：{download_path}\n"
        f"大小：{size[0]} {size[1]}\n"
        f"时长：{utils.convert_duration_to_time_str(duration)}",
        f"[{level}]"
    )

    return new_audio
