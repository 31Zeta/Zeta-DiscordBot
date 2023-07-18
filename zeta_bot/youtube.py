from __future__ import unicode_literals
from yt_dlp import YoutubeDL
from youtubesearchpython import VideosSearch
from zeta_bot import (
    log,
    utils,
    audio
)
# import asyncio


def get_info(ytb_url):
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


def audio_download(ytb_url, info_dict, download_path, download_type="ytb_single") -> audio.Audio:

    if download_path.endswith("/"):
        download_path = download_path.rstrip("/")

    video_title = info_dict["title"]
    video_path_title = utils.legal_name(video_title)
    video_name_extension = info_dict["ext"]
    video_duration = info_dict["duration"]

    video_path = f"{download_path}/{video_path_title}.{video_name_extension}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": video_path
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([ytb_url])

    new_audio = audio.Audio(video_title, download_type, ytb_url, video_path, video_duration)

    return new_audio


async def search_ytb(ctx, input_name):
    name = input_name.strip()

    if name == "":
        ctx.respond("请输入要搜索的名称")
        return

    options = []
    search_result = VideosSearch(name, limit=5)
    info_dict = dict(search_result.result())['result']

    message = f"Youtube搜索 **{name}** 结果为:\n"

    counter = 1
    for result_video in info_dict:

        title = result_video["title"]
        video_id = result_video["id"]
        duration = result_video["duration"]

        options.append([title, video_id, duration])
        message = message + f"**[{counter}]** {title}  [{duration}]\n"

        counter += 1

    # console_message_log(ctx, f"搜索结果为：{options}")

    message = message + "\n请选择："

    if len(info_dict) == 0:
        await ctx.respond("没有搜索到任何结果")
        return

    # view = SearchSelectView(ctx, options)
    # await ctx.respond(message, view=view)

    return options
