from __future__ import unicode_literals
from yt_dlp import YoutubeDL
from audio import Audio
# import asyncio


def ytb_get_info(ytb_url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': "./downloads/" + '/%(title)s.%(ext)s',
    }

    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(ytb_url, download=False)

    if "_type" not in info_dict:
        return "ytb_single", info_dict

    else:
        return "ytb_playlist", info_dict


def ytb_audio_download(ytb_url, info_dict, download_path,
                       download_type="ytb_single") -> Audio:

    if download_path.endswith("/"):
        download_path = download_path.rstrip("/")

    video_title = info_dict["title"]
    video_path_title = ytb_legal_name(video_title)
    video_name_extension = info_dict["ext"]
    video_duration = info_dict["duration"]

    video_path = f"{download_path}/{video_path_title}.{video_name_extension}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": video_path
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([ytb_url])

    audio = Audio(video_title)
    audio.download_init(download_type, ytb_url, video_path, video_duration)

    return audio


def ytb_legal_name(name_str: str) -> str:
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
