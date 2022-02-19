from __future__ import unicode_literals
from yt_dlp import YoutubeDL


# import asyncio


def ytb_get_info(ytb_url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': "./downloads/" + '/%(title)s.%(ext)s',
    }

    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(ytb_url, download=False)

    if "_type" not in info_dict:
        return "single", info_dict

    else:
        return "list", info_dict


def ytb_audio_download(ytb_url, info_dict):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': "./downloads/" + '/%(title)s.%(ext)s',
    }

    with YoutubeDL(ydl_opts) as ydl:
        video_title = info_dict.get('title', None)
        video_duration = info_dict.get('duration', None)
        ydl.download([ytb_url])

    video_path = f"./downloads/{legal_name(video_title)}.webm"

    return video_title, video_path, video_duration


def ytb_audio_download_list(ytb_url, info_dict):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': "./downloads/" + '/%(title)s.%(ext)s',
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([ytb_url])

    title_list = []
    path_list = []
    duration_list = []

    for v in info_dict["entries"]:

        video_title = v["fulltitle"]
        video_duration = v["duration"]

        title_list.append(video_title)
        path_list.append(f"./downloads/{legal_name(video_title)}.webm")
        duration_list.append(video_duration)

    return title_list, path_list, duration_list


def legal_name(name_str: str) -> str:
    """
    将字符串转换为合法的文件名

    :param name_str: 原文件名
    :return: 转换后文件名
    """

    name_str = name_str.replace("\\", " -")
    name_str = name_str.replace("/", " -")
    name_str = name_str.replace(":", " -")
    name_str = name_str.replace("*", " -")
    name_str = name_str.replace("?", "")
    name_str = name_str.replace("\"", "'")
    name_str = name_str.replace("<", " -")
    name_str = name_str.replace(">", " -")
    name_str = name_str.replace("|", "_")

    return name_str
