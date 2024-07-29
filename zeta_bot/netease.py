import yt_dlp.utils
from yt_dlp import YoutubeDL
from yt_dlp import version as yt_dlp_version
from typing import Union

from zeta_bot import (
    log,
    utils,
    audio
)

level = "网易云音乐模块"


def get_info(netease_url):

    # 获取日志记录器
    logger = log.Log()

    ydl_opts = {
        'format': 'bestaudio/best',
        'extract_flat': True,
        "quiet": True,
    }

    logger.rp(f"开始提取信息：{netease_url}", f"[{level}]")

    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(netease_url, download=False)

    audio_id = info_dict["id"]
    audio_title = info_dict["title"]

    logger.rp(f"信息提取完毕：{audio_title} [{audio_id}]", f"[{level}]")

    return info_dict


def get_filesize(info_dict: dict) -> Union[int, None]:
    if "filesize" in info_dict:
        return info_dict["filesize"]
    else:
        return None


def audio_download(netease_url, info_dict, download_path, download_type="netease_single") -> audio.Audio:

    # 获取日志记录器
    logger = log.Log()

    if download_path.endswith("/"):
        download_path = download_path.rstrip("/")

    audio_id = info_dict["id"]
    audio_title = info_dict["title"]
    # audio_authors = info_dict["creators"]
    audio_path_title = utils.legal_name(audio_title)
    audio_name_extension = info_dict["ext"]
    audio_duration = info_dict["duration"]
    size = utils.convert_byte(int(info_dict["filesize"]))

    audio_path = f"{download_path}/{audio_path_title}.{audio_name_extension}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": audio_path,
        "extract_flat": True,
        "quiet": True,
    }

    logger.rp(f"开始下载：{audio_path_title}.{audio_name_extension}", f"[{level}]")

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([netease_url])

    new_audio = audio.Audio(audio_title, download_type, audio_id, audio_path, audio_duration)
    logger.rp(
        f"下载完成\n"
        f"文件名：{audio_path_title}.{audio_name_extension}\n"
        f"来源：[NetEase] {audio_id}\n"
        f"路径：{download_path}\n"
        f"大小：{size[0]} {size[1]}\n"
        f"时长：{utils.convert_duration_to_str(audio_duration)}",
        f"[{level}]"
    )

    return new_audio
