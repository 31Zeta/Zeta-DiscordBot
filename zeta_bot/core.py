from typing import *
import sys
import os
import asyncio
import aiohttp
import httpx
import requests
import platform
import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import discord
import discord.voice
from discord.commands import option
from discord.ui import View

import bilibili_api
import yt_dlp
from bilibili_api import BILIBILI_API_VERSION
from yt_dlp import version as yt_dlp_version

import errors
import utils

# 底层模块
from zeta_bot import (
    language,
    setting,
    console,
    icon,
)

startup_time = utils.ctime_str()

version = "0.14.0"
author = "炤融 (31Zeta)"
python_path = sys.executable
pycord_version = discord.__version__
bilibili_api_version = BILIBILI_API_VERSION
yt_dlp_version = yt_dlp_version.__version__
update_time = "2026.03.31"

supported_search_sites = ["哔哩哔哩", "YouTube"]

logo = (
    "________  _______  _________  ________               ________  ________  _________   \n"
    "|\\_____  \\|\\  ___ \\|\\___   ___\\\\   __  \\             |\\   __  \\|\\   __  \\|\\___   ___\\ \n"
    " \\|___/  /\\ \\   __/\\|___ \\  \\_\\ \\  \\|\\  \\  __________\\ \\  \\|\\ /\\ \\  \\|\\  \\|___ \\  \\_| \n"
    "     /  / /\\ \\  \\_|/__  \\ \\  \\ \\ \\   __  \\|\\__________\\ \\   __  \\ \\  \\\\\\  \\   \\ \\  \\  \n"
    "    /  /_/__\\ \\  \\_|\\ \\  \\ \\  \\ \\ \\  \\ \\  \\|__________|\\ \\  \\|\\  \\ \\  \\\\\\  \\   \\ \\  \\ \n"
    "   |\\________\\ \\_______\\  \\ \\__\\ \\ \\__\\ \\__\\            \\ \\_______\\ \\_______\\   \\ \\__\\\n"
    "    \\|_______|\\|_______|   \\|__|  \\|__|\\|__|             \\|_______|\\|_______|    \\|__|"
)

version_header = (
    f"Zeta-Bot Version：{version}\n"
    f"Pycord Version：{pycord_version}\n"
    f"Bilibili API Version：{bilibili_api_version}\n"
    f"yt-dlp Version：{yt_dlp_version}"
)

# 多语言模块
lang = language.Lang()
_ = lang.get_string
printl = lang.printl

# 设置配置文件
utils.create_folder("./configs")
lang_setting = setting.Setting("./configs/language_config.json", setting.language_setting_configs)
lang.set_system_language(lang_setting.value("language"))
setting = setting.Setting("./configs/system_config.json", setting.bot_setting_configs, lang_setting.value("language"))
bot_name = setting.value("bot_name")

# TODO 添加维护模式

# 设置控制台日志记录器
LOG_DIRECTORY_PATH = "./logs"
utils.create_folder(LOG_DIRECTORY_PATH)
log_name_time = startup_time.replace(":", "_")
console = console.Console(LOG_DIRECTORY_PATH, log_name_time, setting.value("log"), version_header)

# 设置图标库
icon_lib = icon.IconLib()
icon_lib.load_icons("./zeta_bot/icons")

# 功能型模块
from zeta_bot import (
    bilibili,
    ytdlp,
    file_management,
    member,
    guild,
    audio,
    playlist,
)
from zeta_bot.help import HelpMenu

print(f"\nZeta-Bot程序启动\n{logo}\n\n{version_header}\n")

# 系统检测
if platform.system().lower() == "windows":
    ffmpeg_path = "./bin/ffmpeg.exe"
else:
    ffmpeg_path = "./bin/ffmpeg"

# 初始化机器人设置
intents = discord.Intents.all()
bot = discord.Bot(help_command=None, case_insensitive=True, intents=intents)

# 设置用户和Discord服务器管理
utils.create_folder("./data")
member_lib = member.MemberLibrary()
guild_lib = guild.GuildLibrary()

# 设置下载文件管理
utils.create_folder("./downloads")
audio_lib_main = file_management.AudioFileLibrary(
    "./downloads",
    "./data/audio_lib_main.json",
    "主音频文件库",
    setting.value("audio_library_storage_capacity") * 1024 * 1024  # 要求用户输入的单位为MB，转换为字节Byte
)

# Py-cord 颜色快捷方式
dark_teal = discord.Colour.dark_teal()
orange = discord.Colour.orange()
red = discord.Colour.red()

# 聊天AI API 效果较差，暂时弃用
# 设置聊天AI
# if setting.value("chat_ai"):
#     utils.create_folder("./data/ai")
#     chat_ai = ai.ChatAI(
#         setting.value("chat_ai_base_url"),
#         setting.value("chat_ai_api_key"),
#         setting.value("chat_ai_model_name"),
#         "./data/ai",
#         bot_name
#     )
# else:
#     chat_ai = None


def start(mode: str) -> None:
    """
    根据模式启动程序
    """
    if mode == "normal" or mode == "":
        run_bot()
    elif mode == "setting":
        setting.modify_mode()
        run_bot()
    elif mode == "reset":
        setting.reset_setting()
        run_bot()
    else:
        raise ValueError("未找到指定启动模式")


if __name__ == "__main__":
    start("normal")


def run_bot() -> None:
    """启动机器人"""
    try:
        bot.run(setting.value("token"))
    except errors.LoginFailure:
        print("登录失败，请检查Discord机器人令牌是否正确，在启动指令后添加\" --mode=setting\"来修改设置")


@bot.event
async def on_error(exception):
    await console.on_error(exception)


@bot.event
async def on_application_command_error(ctx, exception):
    await console.on_application_command_error(ctx, exception)

    # 向用户回复发生错误
    await embed_respond(ctx, "发生错误", colour=red, silent=True)


async def command_check(ctx: discord.ApplicationContext) -> bool:
    """
    对指令触发进行日志记录，检测用户是否记录在案，检测用户是否有权限使用该条指令
    """
    member_lib.check(ctx)
    user_group = member_lib.get_group(ctx.user.id)
    operation = str(ctx.command)
    # 如果用户是机器人所有者
    if str(ctx.user.id) == setting.value("owner"):
        await console.rp(f"用户 {ctx.user} [用户组: 机器人所有者] 发送指令：<{operation}>", ctx.guild)
        return True
    elif member_lib.allow(ctx.user.id, operation):
        await console.rp(f"用户 {ctx.user} [用户组: {user_group}] 发送指令：<{operation}>", ctx.guild)
        return True
    else:
        await console.rp(f"用户 {ctx.user} [用户组: {user_group}] 发送指令：<{operation}>，权限不足，操作已被拒绝", ctx.guild)
        await embed_respond(ctx, "权限不足", colour=red, silent=True)
        return False


# 启动就绪时
@bot.event
async def on_ready():
    """
    当机器人启动完成时自动调用
    """

    current_time = utils.ctime_str()
    await console.rp(f"登录完成：以{bot.user}的身份登录，登录时间：{current_time}", "[系统]")

    # 启动定时任务框架
    scheduler_ar_1 = AsyncIOScheduler()
    scheduler_ar_2 = AsyncIOScheduler()

    if setting.value("auto_reboot"):
        # 设置自动重启
        ar_timezone = "Asia/Shanghai"
        ar_time = utils.time_split(setting.value("ar_time"))
        scheduler_ar_1.add_job(
            auto_reboot, CronTrigger(
                timezone=ar_timezone, hour=ar_time[0],
                minute=ar_time[1], second=ar_time[2]
            )
        )

        if setting.value("ar_reminder"):
            # 设置自动重启提醒
            ar_r_time = utils.time_split(setting.value("ar_reminder_time"))
            scheduler_ar_2.add_job(
                auto_reboot_reminder, CronTrigger(
                    timezone=ar_timezone, hour=ar_r_time[0],
                    minute=ar_r_time[1], second=ar_r_time[2]
                )
            )

        scheduler_ar_1.start()
        scheduler_ar_2.start()

        await console.rp(
            f"设置自动重启时间为 {ar_time[0]}时{ar_time[1]}分{ar_time[2]}秒",
            "[系统]"
        )

    # 初始化主音频库
    await audio_lib_main.initialize()

    # 设置机器人状态
    bot_activity_type = discord.ActivityType.playing
    await bot.change_presence(
        activity=discord.Activity(type=bot_activity_type, name=setting.value("default_activity"))
    )

    # FFmpeg检测
    if not os.path.exists(ffmpeg_path):
        await console.rp(
            "未发现FFmpeg程序，将无法使用音频播放相关功能，请下载FFmpeg并将其放在程序根目录内的bin文件夹内",
            "[系统]",
            message_type=utils.PrintType.WARNING,
            print_head=True
        )

    await console.rp(f"启动完成", "[系统]")

# 需要@某人时：<@{user_id}>

# 文字频道中收到信息时
@bot.event
async def on_message(message: discord.Message):
    """
    当检测到消息时调用

    :param message:频道中的消息
    :return:
    """
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message):
        await message.channel.send(f"{message.author.mention} 你好！如果需要我可以使用 /help 或 /帮助 查看帮助菜单")
        # if setting.value("chat_ai") and chat_ai is not None:
        #     loading_message = await chat_ai.loading_message()
        #     respond_message = await message.channel.send(loading_message)
        #
        #     channel_id = str(message.channel.id)
        #     ai_response = await chat_ai.chat(channel_id, f"{message.content[message.content.find('>') + 2:]}", str(message.author.name))
        #
        #     if isinstance(ai_response, dict) and "message" in ai_response:
        #         if len(ai_response["message"]) == 0:
        #             no_response_message = await chat_ai.no_response_message()
        #             await respond_message.edit(content=no_response_message)
        #         else:
        #             await respond_message.edit(content=f"{ai_response['message']}")
        #             if ai_response["function_call"] == "play_music":
        #                 pass
        #     else:
        #         error_message = await chat_ai.error_message()
        #         await respond_message.edit(content=error_message)
        # else:
        #     await message.channel.send(f"机器人未启用人工智能功能，详情请咨询管理员")

    if message.content.startswith(bot_name):
        await message.channel.send(f"{message.author.mention} 我在")

    if message.content.startswith("test"):
        await message.channel.send(_("custom.reply_1"))


# 新成员加入时调用
@bot.event
async def on_member_join(new_member):
    await new_member.send(
        f"你好，{new_member.mention}！我是{bot_name}，可以在语言频道内播放音乐！使用 /help 或 /帮助 指令来查看我的用法吧！"
    )


async def auto_reboot():
    """
    用于执行定时重启，如果<auto_reboot_announcement>为True则广播重启消息
    """
    current_time = utils.ctime_str()
    await console.rp(f"执行自动定时重启", "[系统]")
    await guild_lib.save_all()
    # user_library.save()
    if setting.value("ar_announcement"):
        for current_guild in bot.guilds:
            voice_client = current_guild.voice_client
            if voice_client is not None:
                await current_guild.text_channels[0].send(f"{current_time} 开始执行自动定时重启")
    os.execl(python_path, python_path, * sys.argv)


async def auto_reboot_reminder():
    """
    向机器人仍在语音频道中的所有服务器的第一个文字频道发送即将重启通知
    """
    ar_time = setting.value("ar_time")
    await console.rp(f"发送自动重启通知", "[系统]")
    for current_guild in bot.guilds:
        voice_client = current_guild.voice_client
        if voice_client is not None:
            await current_guild.text_channels[0].send(f"注意：将在{ar_time}时自动重启")


async def embed_send(
        ctx: discord.ApplicationContext,
        description: Optional[str] = None,
        title: Optional[str] = None,
        colour: discord.Colour = discord.Colour.dark_teal(),
        timestamp: bool = False,
        author_name: Optional[str] = None,
        author_url: Optional[str] = None,
        author_icon_url: Optional[str] = None,
        footer_text: Optional[str] = None,
        footer_icon_url: Optional[str] = None,
        image: Optional[str] = None,
        thumbnail: Optional[str] = None,
        files: Optional[List[discord.File]] = None,
        view: Optional[discord.ui.View] = None,
        silent: bool = False
) -> Tuple[Union[discord.interactions, discord.WebhookMessage], discord.Embed]:
    embed = discord.Embed(
        colour=colour,
        title=title,
        description=description,
    )
    if timestamp:
        embed.timestamp = utils.ctime_datetime()
    if author_name:
        embed.set_author(name=author_name, url=author_url, icon_url=author_icon_url)
    if footer_text or footer_icon_url:
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)
    if image:
        embed.set_image(url=image)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    if files is not None and len(files) < 1:
        files = None

    message = await ctx.send(content=None, embed=embed, files=files, view=view, silent=silent)

    return message, embed


async def embed_respond(
        ctx: discord.ApplicationContext,
        description: Optional[str] = None,
        title: Optional[str] = None,
        colour: discord.Colour = discord.Colour.dark_teal(),
        timestamp: bool = False,
        author_name: Optional[str] = None,
        author_url: Optional[str] = None,
        author_icon_url: Optional[str] = None,
        footer_text: Optional[str] = None,
        footer_icon_url: Optional[str] = None,
        image: Optional[str] = None,
        thumbnail: Optional[str] = None,
        files: Optional[List[discord.File]] = None,
        view: Optional[discord.ui.View] = None,
        ephemeral: bool = False,
        silent: bool = False
) -> Tuple[Union[discord.interactions, discord.WebhookMessage], discord.Embed]:
    embed = discord.Embed(
        colour=colour,
        title=title,
        description=description,
    )
    if timestamp:
        embed.timestamp = utils.ctime_datetime()
    if author_name:
        embed.set_author(name=author_name, url=author_url, icon_url=author_icon_url)
    if footer_text or footer_icon_url:
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)
    if image:
        embed.set_image(url=image)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    if files is not None and len(files) < 1:
        files = None

    message = await ctx.respond(content=None, embed=embed, files=files, view=view, ephemeral=ephemeral, silent=silent)

    return message, embed


async def eos(
        ctx: discord.ApplicationContext,
        response: Union[discord.Interaction, discord.InteractionMessage, discord.Message],
        content: Optional[str] = None,
        silent: bool = False,
        embed: Optional[discord.Embed] = None,
        files: Optional[List[discord.File]] = None,
        view: Optional[discord.ui.View] = None,
        debug=False
) -> Union[discord.InteractionMessage, discord.Message]:
    """
    [Edit Or Send]
    如果<response>可以被编辑，则将<response>编辑为<content>
    否则使用<ctx>发送<content>
    """
    if debug:
        print(f"[DEBUG] eos参数response类型为：{type(response)}\n")

    if files is not None and len(files) < 1:
        files = None

    # 如files为空需要清除附件，确保附件不会被传到修改后的信息中
    if isinstance(response, discord.Interaction):
        if files is None:
            return await response.edit_original_response(content=content, embed=embed, attachments=[], view=view)
        else:
            return await response.edit_original_response(content=content, embed=embed, files=files, view=view)
    elif isinstance(response, discord.InteractionMessage):
        if files is None:
            return await response.edit(content=content, embed=embed, attachments=[], view=view)
        else:
            return await response.edit(content=content, embed=embed, files=files, view=view)
    elif isinstance(response, discord.Message):
        if files is None:
            return await response.edit(content=content, embed=embed, attachments=[], view=view)
        else:
            return await response.edit(content=content, embed=embed, files=files, view=view)
    else:
        return await ctx.send(content=content, embed=embed, files=files, view=view, silent=silent)


async def embed_eos(
        ctx: discord.ApplicationContext,
        response,
        description: Optional[str] = None,
        title: Optional[str] = None,
        colour: discord.Colour = discord.Colour.dark_teal(),
        timestamp: bool = False,
        author_name: Optional[str] = None,
        author_url: Optional[str] = None,
        author_icon_url: Optional[str] = None,
        footer_text: Optional[str] = None,
        footer_icon_url: Optional[str] = None,
        image: Optional[str] = None,
        thumbnail: Optional[str] = None,
        files: Optional[List[discord.File]] = None,
        view: Optional[discord.ui.View] = None,
        silent: bool = False,
        debug=False
) -> Tuple[Union[discord.InteractionMessage, discord.Message], discord.Embed]:
    if debug:
        print(f"[DEBUG] embed_eos参数response类型为：{type(response)}\n")

    embed = discord.Embed(
        colour=colour,
        title=title,
        description=description,
    )
    if timestamp:
        embed.timestamp = utils.ctime_datetime()
    if author_name:
        embed.set_author(name=author_name, url=author_url, icon_url=author_icon_url)
    if footer_text or footer_icon_url:
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)
    if image:
        embed.set_image(url=image)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    if files is not None and len(files) < 1:
        files = None

    # 如files为空需要清除附件，确保附件不会被传到修改后的信息中
    if isinstance(response, discord.Interaction):
        if files is None:
            return await response.edit_original_response(content=None, embed=embed, attachments=[], view=view), embed
        else:
            return await response.edit_original_response(content=None, embed=embed, files=files, view=view), embed
    elif isinstance(response, discord.InteractionMessage):
        if files is None:
            return await response.edit(content=None, embed=embed, attachments=[], view=view), embed
        else:
            return await response.edit(content=None, embed=embed, files=files, view=view), embed
    elif isinstance(response, discord.Message):
        if files is None:
            return await response.edit(content=None, embed=embed, attachments=[], view=view), embed
        else:
            return await response.edit(content=None, embed=embed, files=files, view=view), embed
    else:
        return await ctx.send(content=None, embed=embed, files=files, view=view, silent=silent), embed


async def append_content(target, content: str, embed=None, view=None) -> Optional[discord.Message]:
    """
    如果修改次数大于一次，请确保传入本方法第一次返回的Message对象，因为Interaction只能获取最初的信息
    """
    if isinstance(target, discord.Message):
        original_message = target.content
    elif isinstance(target, discord.Interaction):
        target_original_response = await target.original_response()
        original_message = target_original_response.content
    elif isinstance(target, discord.InteractionMessage):
        original_message = target.content
    else:
        return None
    new_content = original_message + "\n" + content
    return await target.edit(content=new_content, embed=embed, view=view)


def embed_append_description(embed: discord.Embed, content: str):
    embed.description += "\n" + content
    embed.timestamp = utils.ctime_datetime()


def embed_replace_description_last_line(embed: discord.Embed, content: str):
    new_line_index = str(embed.description).rfind("\n")
    # 如果没有找到换行符：替换全部
    if new_line_index == -1:
        embed.description = content
    else:
        embed.description = embed.description[:new_line_index] + "\n" + content
    embed.timestamp = utils.ctime_datetime()


async def delete_response(target) -> bool:
    try:
        if isinstance(target, discord.Interaction):
            await target.delete_original_response()
            return True
        if isinstance(target, (discord.InteractionMessage, discord.Message)):
            await target.delete()
            return True
    except discord.NotFound:
        return True
    except discord.HTTPException:
        return False
    return False


def get_voice_client_status(voice_client: discord.voice.VoiceClient) -> int:
    """
    获取voice_client的播放状态
        0 - 待机中
        1 - 正在播放
        2 - 暂停
        3 - 不在语音频道中
    """
    if not voice_client:
        voice_client_status = 3
    elif voice_client.is_playing():
        voice_client_status = 1
    elif voice_client.is_paused():
        voice_client_status = 2
    else:
        voice_client_status = 0
    return voice_client_status


def get_voice_client_status_str(status_code: int) -> str:
    """
    将voice_client播放状态代码转换为文本
        0 - 待机中
        1 - 正在播放
        2 - 暂停
        3 - 不在语音频道中
    """
    if status_code == 3:
        voice_client_status = "不在语音频道中"
    elif status_code == 1:
        voice_client_status = "正在播放"
    elif status_code == 2:
        voice_client_status = "暂停"
    elif status_code == 0:
        voice_client_status = "待机中"
    else:
        voice_client_status = "未知"
    return voice_client_status


async def autocomplete_search_sites(ctx: discord.AutocompleteContext):
    """
    search指令用自动填充 - 可选的搜索平台
    """
    await guild_lib.check(ctx, audio_lib_main)
    return supported_search_sites


async def autocomplete_skip_playlist(ctx: discord.AutocompleteContext):
    """
    skip指令用自动填充 - 播放列表音频名称列表生成
    """
    await guild_lib.check(ctx, audio_lib_main)

    audio_str_list = ["全部"]
    audio_str_list += guild_lib.get_guild(ctx).get_playlist().get_audio_str_list(index_start=True)
    return audio_str_list


async def autocomplete_skipi_playlist_index(ctx: discord.AutocompleteContext):
    """
    skipi指令用自动填充 - 播放列表序号列表生成
    """
    await guild_lib.check(ctx, audio_lib_main)

    playlist_len = len(guild_lib.get_guild(ctx).get_playlist())
    number_list = []
    for i in range(1, playlist_len + 1):
        number_list.append(i)
    return number_list


async def get_guild_playlist_length(ctx: discord.AutocompleteContext) -> int:
    """
    获取<ctx>对应的服务器的主播放列表长度
    """
    await guild_lib.check(ctx, audio_lib_main)
    return len(guild_lib.get_guild(ctx).get_playlist())


@bot.slash_command(description="[管理员] 测试指令1")
async def debug1(ctx):
    """
    测试用指令
    """
    if not await command_check(ctx):
        return

    await join_callback(ctx, None)


@bot.slash_command(description="[管理员] 测试指令2")
async def debug2(ctx):
    """
    测试用指令
    """
    if not await command_check(ctx):
        return

    await guild_lib.check(ctx, audio_lib_main)
    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    if voice_client:
        vc = True
    else:
        vc = False

    print(f"Voice client is True/False：{vc}")
    print(f"Voice client 正在播放：{voice_client.is_playing()}")
    print(f"Voice client 正在暂停：{voice_client.is_paused()}")
    print(f"主播放列表为空：{current_playlist.is_empty()}")
    print(current_playlist)

    await ctx.respond("测试结果已打印")


@bot.slash_command(description="[管理员] 测试指令3")
async def debug3(ctx):
    """
    测试用指令
    """
    if not await command_check(ctx):
        return

    audio_lib_main.print_info()

    await ctx.respond("测试结果已打印")


@bot.slash_command(name_localizations=lang.get_command_name("info"), description="关于Zeta-Discord机器人")
async def info(ctx: discord.ApplicationContext) -> None:
    await ctx.defer()
    if not await command_check(ctx):
        return
    await info_callback(ctx)


@bot.slash_command(name_localizations=lang.get_command_name("help"), description="召唤帮助菜单")
async def help(ctx: discord.ApplicationContext) -> None:
    await ctx.defer()
    if not await command_check(ctx):
        return
    await help_callback(ctx)


# @bot.slash_command(name_localizations={"zh-CN": "广播"}, description="[管理员] 向机器人所在的所有服务器广播消息")
async def broadcast(ctx: discord.ApplicationContext, message) -> None:
    await ctx.defer()
    if not await command_check(ctx):
        return
    await broadcast_callback(ctx, message)


@bot.slash_command(name_localizations=lang.get_command_name("join"), description=f"让{bot_name}加入当前所在或者指定语音频道")
@option(
    "channel", discord.VoiceChannel,
    description=f"要让{bot_name}加入的频道，如果不选择则加入指令发送者所在的频道",
    required=False
)
async def join(ctx: discord.ApplicationContext, channel: Union[discord.VoiceChannel, None]) -> bool:
    await ctx.defer()
    if not await command_check(ctx):
        return False
    return await join_callback(ctx, channel, command_call=True)


@bot.slash_command(name_localizations=lang.get_command_name("leave"), description=f"让{bot_name}离开当前所在语音频道")
async def leave(ctx: discord.ApplicationContext) -> None:
    await ctx.defer()
    if not await command_check(ctx):
        return
    await leave_callback(ctx)


@bot.slash_command(name_localizations=lang.get_command_name("search_audio"), description="搜索并播放来自哔哩哔哩，Youtube的音频")
@option(
    "query",
    description="搜索的名称",
    required=True
)
@option(
    "site",
    description="搜索的平台（为空则在所有支持的平台进行搜索）",
    required=False,
    # autocomplete=autocomplete_search_sites
    choices=supported_search_sites
)
async def search_audio(ctx: discord.ApplicationContext, query, site) -> None:
    await ctx.defer()
    if not await command_check(ctx):
        return
    await search_audio_callback(ctx, query, site)


@bot.slash_command(name_localizations=lang.get_command_name("play"), description="播放来自哔哩哔哩，Youtube，网易云音乐的音频")
@option(
    "link",
    description="要播放的音频（视频）的链接或者哔哩哔哩BV号",
    required=True
)
async def play(ctx: discord.ApplicationContext, link=None) -> None:
    await ctx.defer()
    if not await command_check(ctx):
        return
    await play_callback(ctx, link)


@bot.slash_command(name_localizations=lang.get_command_name("pause"), description="暂停正在播放的音频")
async def pause(ctx: discord.ApplicationContext):
    await ctx.defer()
    if not await command_check(ctx):
        return
    await pause_callback(ctx, command_call=True)


@bot.slash_command(name_localizations=lang.get_command_name("resume"), description="继续播放暂停或被意外中断的音频")
async def resume(ctx: discord.ApplicationContext):
    await ctx.defer()
    if not await command_check(ctx):
        return
    await resume_callback(ctx, command_call=True)


@bot.slash_command(name_localizations=lang.get_command_name("list"), description="召唤当前播放列表")
async def list(ctx: discord.ApplicationContext):
    await ctx.defer()
    if not await command_check(ctx):
        return
    await list_callback(ctx)


@bot.slash_command(name_localizations=lang.get_command_name("skip"), description="跳过正在播放或播放列表中的音频")
@option(
    "start",
    description="需要跳过的音频 / 从第几个音频开始跳过",
    required=False,
    autocomplete=autocomplete_skip_playlist,
)
@option(
    "end",
    description="需要跳过的音频 / 跳过到第几个音频",
    required=False,
    autocomplete=autocomplete_skip_playlist,
)
async def skip(ctx: discord.ApplicationContext, start=None, end=None):
    await ctx.defer()
    if not await command_check(ctx):
        return

    await guild_lib.check(ctx, audio_lib_main)
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"

    if start is None and end is None:
        await skip_callback(ctx, first_index=None, second_index=None, command_call=True)

    elif start is not None and end is None:
        if start == "全部":
            await skip_callback(ctx, "*", command_call=True)
        else:
            if start.isdigit():
                start_index = int(start)
            elif "[" and "]" in start and start[1:start.find("]")].isdigit():
                start_index = int(start[1:start.find("]")])
            else:
                await embed_respond(ctx, author_name="参数错误", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
                await console.rp(f"用户 {ctx.author} 的skip指令参数错误", ctx.guild)
                return
            await skip_callback(ctx, first_index=start_index, command_call=True)

    elif start is None and end is not None:
        if end == "全部":
            await skip_callback(ctx, "*", command_call=True)
        else:
            if end.isdigit():
                start_index = int(end)
            elif "[" and "]" in end and end[1:end.find("]")].isdigit():
                start_index = int(end[1:end.find("]")])
            else:
                await embed_respond(ctx, author_name="参数错误", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
                await console.rp(f"用户 {ctx.author} 的skip指令参数错误", ctx.guild)
                return
            await skip_callback(ctx, first_index=start_index, command_call=True)

    else:
        if start == "全部" and end == "全部":
            await skip_callback(ctx, "*", command_call=True)
        if start == "全部":
            if end.isdigit():
                end_index = int(end)
            elif "[" and "]" in end and end[1:end.find("]")].isdigit():
                end_index = int(end[1:end.find("]")])
            else:
                await embed_respond(ctx, author_name="参数错误", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
                await console.rp(f"用户 {ctx.author} 的skip指令参数错误", ctx.guild)
                return
            await skip_callback(ctx, first_index=1, second_index=end_index, command_call=True)
        elif end == "全部":
            if start.isdigit():
                start_index = int(start)
            elif "[" and "]" in start and start[1:start.find("]")].isdigit():
                start_index = int(start[1:start.find("]")])
            else:
                await embed_respond(ctx, author_name="参数错误", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
                await console.rp(f"用户 {ctx.author} 的skip指令参数错误", ctx.guild)
                return
            await skip_callback(ctx, first_index=start_index, second_index=len(current_playlist), command_call=True)
        else:
            if start.isdigit():
                start_index = int(start)
            elif "[" and "]" in start and start[1:start.find("]")].isdigit():
                start_index = int(start[1:start.find("]")])
            else:
                await embed_respond(ctx, author_name="参数错误", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
                await console.rp(f"用户 {ctx.author} 的skip指令参数错误", ctx.guild)
                return
            if end.isdigit():
                end_index = int(end)
            elif "[" and "]" in end and end[1:end.find("]")].isdigit():
                end_index = int(end[1:end.find("]")])
            else:
                await embed_respond(ctx, author_name="参数错误", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
                await console.rp(f"用户 {ctx.author} 的skip指令参数错误", ctx.guild)
                return
            await skip_callback(ctx, first_index=start_index, second_index=end_index, command_call=True)


@bot.slash_command(name_localizations=lang.get_command_name("move"), description="移动播放列表中音频的位置")
@option(
    "move", int,
    description="需要移动的音频的序号",
    required=True,
    min_value=1
)
@option(
    "to", int,
    description="需要移动到第几号位置",
    required=True,
    min_value=1
)
async def move(ctx, move: int, to: int):
    await ctx.defer()
    if not await command_check(ctx):
        return
    await move_callback(ctx, move, to)


@bot.slash_command(name_localizations=lang.get_command_name("clear"), description="清空主播放列表中的所有音频")
async def clear(ctx: discord.ApplicationContext):
    await ctx.defer()
    if not await command_check(ctx):
        return
    await clear_callback(ctx)


@bot.slash_command(name_localizations=lang.get_command_name("volume"), description=f"调整{bot_name}的语音频道音量")
@option(
    "volume_number", int,
    description="目标音量大小（0 - 200）%",
    required=False,
    min_value=0,
    max_value=200,
)
async def volume(ctx: discord.ApplicationContext, volume_number=None) -> None:
    await ctx.defer()
    if not await command_check(ctx):
        return
    await volume_callback(ctx, volume_number)


@bot.slash_command(name_localizations=lang.get_command_name("reboot"), description="[管理员] 重启机器人")
async def reboot(ctx):
    await ctx.defer()
    if not await command_check(ctx):
        return
    await reboot_callback(ctx)


@bot.slash_command(name_localizations=lang.get_command_name("shutdown"), description="[管理员] 关闭机器人")
async def shutdown(ctx):
    await ctx.defer()
    if not await command_check(ctx):
        return
    await shutdown_callback(ctx)


async def info_callback(ctx: discord.ApplicationContext) -> None:
    """
    显示关于信息

    :param ctx: 指令原句
    :return:
    """
    icon_filename = "sticky_notes_in_reveal_animated_0ms_100px.gif"
    embed = discord.Embed(
        colour=discord.Colour.dark_teal(),
        description=f"   基于 Pycord v{pycord_version} 运行\n"
                    f"   版本更新日期：{update_time}\n"
                    f"   作者：31Zeta"
    )
    embed.set_author(name=f"Zeta-Discord机器人 [版本 v{version}]", icon_url=icon.url(icon_filename))
    await ctx.respond(embed=embed, silent=True, files=icon_lib.files(icon_filename))


async def help_callback(ctx: discord.ApplicationContext) -> None:
    """
    覆盖掉原有help指令, 向频道发送帮助菜单

    :param ctx: 指令原句
    :return:
    """
    menu = HelpMenu(ctx)
    await menu.init_respond()


async def broadcast_callback(ctx: discord.ApplicationContext, message) -> None:
    """
    让机器人在所有服务器的第一个频道发送参数message

    :param ctx: 指令原句
    :param message: 需要发送的信息
    :return:
    """
    if not await command_check(ctx):
        return

    for current_guild in bot.guilds:
        await current_guild.text_channels[0].send(message)

    await embed_respond(ctx, "已发送", silent=True)


async def join_callback(ctx: discord.ApplicationContext, channel: discord.VoiceChannel = None, command_call: bool = False) -> bool:
    """
    让机器人加入指令发送者所在的语音频道并发送提示\n
    如果机器人已经加入一个频道则转移到新频道并发送提示
    如发送者未加入任何语音频道发送提示

    :param ctx: 指令原句
    :param channel: 要加入的频道
    :param command_call: 该指令是否是由用户指令调用
    :return: 布尔值，是否成功加入频道
    """
    await guild_lib.check(ctx, audio_lib_main)
    current_guild = guild_lib.get_guild(ctx)

    icon_filename = "add_chat_in_reveal_animated_0ms_100px.gif"
    icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif.gif"

    # 未输入参数的情况
    if channel is None:
        # 指令发送者未加入频道的情况
        if not ctx.user.voice:
            await console.rp(f"频道加入失败，用户 {ctx.user} 发送指令时未加入任何语音频道", ctx.guild)
            await embed_respond(ctx, author_name="您未加入任何语音频道", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
            return False

        # 目标频道设定为指令发送者所在的频道
        else:
            channel = ctx.user.voice.channel

    voice_client = ctx.guild.voice_client

    # 机器人未在任何语音频道的情况
    if voice_client is None:
        await channel.connect()
        if command_call:
            await embed_respond(ctx, author_name=f"已加入语音频道：->  {channel.name}", author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename))

    # 机器人已经在一个频道的情况
    else:
        previous_channel = voice_client.channel
        await voice_client.move_to(channel)
        if command_call:
            await embed_respond(ctx, author_name=f"已转移语音频道：{previous_channel}  ->  {channel.name}", author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename))

    await console.rp(f"加入语音频道：{channel.name}", ctx.guild)
    await current_guild.refresh_list_view()
    return True


async def leave_callback(ctx: discord.ApplicationContext) -> None:
    """
    让机器人离开语音频道并发送提示

    :param ctx: 指令原句
    :return:
    """
    await guild_lib.check(ctx, audio_lib_main)

    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    icon_filename = "logout_hover_pinch_animated_0ms_100px.gif"

    if voice_client is not None:
        # 防止因退出频道自动删除正在播放的音频
        if len(current_playlist) > 0:
            current_audio = current_playlist.get_audio(0)
            current_playlist.insert_audio(current_audio, 0)

        last_channel = voice_client.channel
        await voice_client.disconnect(force=False)

        await console.rp(f"离开语音频道：{last_channel}", ctx.guild)

        await embed_respond(ctx, author_name=f"离开语音频道：<-  {last_channel}", author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename))

    else:
        await embed_respond(ctx, f"{bot_name} 没有连接到任何语音频道", silent=True)

    await current_guild.refresh_list_view()


async def search_audio_callback(ctx: discord.ApplicationContext, query, site=None, query_num=5,
                                response: Union[discord.Interaction, discord.InteractionMessage, None] = None) -> None:
    await guild_lib.check(ctx, audio_lib_main)
    current_guild = guild_lib.get_guild(ctx)

    search_result: Dict[str, list] = {key: None for key in supported_search_sites}

    icon_loading_filename = "hourglass_hover_rotation_animated_1000ms_infinite_30px.gif"
    icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"

    if response is None:
        loading_msg, embed = await embed_respond(ctx, author_name=f"正在搜索：{query}", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename), silent=True)
    else:
        loading_msg, embed = await embed_eos(ctx, response, author_name=f"正在搜索：{query}", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename), silent=True)

    if site is not None and site not in supported_search_sites:
        await embed_eos(ctx, response, author_name="不支持该平台搜索", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
        return
    if site == "哔哩哔哩" or site is None:
        search_result["哔哩哔哩"] = await bilibili.search(query, query_num=query_num)
    if site == "YouTube" or site is None:
        search_result["YouTube"] = await ytdlp.youtube_search(query, query_num=query_num)

    title_str = f""
    address_str = f""
    resource_list = []
    counter = 1
    for key in search_result:
        if search_result[key] is not None:
            title_str += f"{key}\n"
            address_str += f"{key}\n"
            for item in search_result[key]:
                title_str += f"> [{counter}] **{utils.markdown_escape(item['title'])}** [{utils.convert_duration_to_str(item['duration'])}]\n"
                address_str += (
                    f"> [{counter}] **{utils.markdown_escape(item['title'])}** [{utils.convert_duration_to_str(item['duration'])}]\n"
                    f"> {item['id']}\n"
                )
                resource_list.append(item)
                counter += 1

    title_str += "\n**请选择要播放的音频序号**"
    address_str += "\n**请选择要播放的音频序号**"
    menu = SearchedAudioSelectionMenu(ctx, query, title_str, address_str, resource_list)
    await menu.init_eos(loading_msg, silent=True)
    await current_guild.refresh_list_view()


async def play_callback(ctx: discord.ApplicationContext, link, response: Union[discord.Message, discord.Interaction, discord.InteractionMessage, None] = None, function_call: bool = False) -> None:
    """
    使机器人下载目标BV号或Youtube音频后播放并将其标题与文件路径记录进当前服务器的播放列表
    播放结束后调用play_next
    如果当前有歌曲正在播放，则将下载目标音频并将其标题与文件路径记录进当前服务器的播放列表

    :param ctx: 指令原句
    :param link: 目标URL或BV号
    :param response: 用于编辑的加载信息
    :param function_call 该指令是否是由其他函数调用
    :return:
    """
    # 用户记录增加音乐播放计数
    member_lib.play_counter_increment(ctx.user.id)

    await guild_lib.check(ctx, audio_lib_main)
    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    icon_loading_filename = "hourglass_hover_rotation_animated_1000ms_infinite_30px.gif"
    icon_resume_break_filename = "spin_in_reveal_0ms_100px.gif"
    icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"

    if link is None:
        await embed_respond(ctx, "请在/play指令后输入来自哔哩哔哩或者YouTube的链接，也可以直接输入名字进行搜索")
        return

    # 检测机器人是否已经加入语音频道
    if ctx.guild.voice_client is None:
        await console.rp("机器人未在任何语音频道中，尝试加入语音频道", ctx.guild)
        join_result = await join_callback(ctx, command_call=False)
        if join_result:
            # 更新加入频道后的voice_client
            voice_client = ctx.guild.voice_client
        else:
            return

    # voice_client存在，不是正在播放或暂停的状态，且列表中存在音频，自动恢复播放
    if voice_client is not None and not voice_client.is_playing() and not voice_client.is_paused() and not current_playlist.is_empty():

        await embed_respond(ctx, author_name="恢复之前中断的播放", author_icon_url=icon.url(icon_resume_break_filename), files=icon_lib.files(icon_resume_break_filename), silent=True)
        await resume_callback(ctx, command_call=False)

    # 检查输入的URL属于哪个网站
    source = utils.check_url_source(link)

    # 如果指令中包含链接则提取链接
    if source is not None:
        link = utils.get_url_from_str(link, source)

    # Link属于Bilibili
    if source == "bilibili_bvid" or source == "bilibili_url" or source == "bilibili_short_url":
        # 如果是Bilibili短链则获取重定向链接
        if source == "bilibili_short_url":
            try:
                link = utils.get_redirect_url(link)
            except requests.exceptions.InvalidSchema:
                await embed_eos(ctx, response, author_name="链接异常", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
                await console.rp(f"链接重定向失败", ctx.guild, message_type=utils.PrintType.ERROR, print_head=True)
                return

            await console.rp(f"获取的重定向链接为 {link}", ctx.guild)

        if response is None:
            loading_msg, embed = await embed_respond(ctx, author_name="正在加载哔哩哔哩音频信息", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename), silent=True)
        else:
            loading_msg, embed = await embed_eos(ctx, response, author_name="正在加载哔哩哔哩音频信息", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename), silent=True)
        await play_bilibili(ctx, source, link, response=loading_msg)

    # Link属于YouTube
    elif source == "youtube_url" or source == "youtube_short_url":
        # 如果是Youtube短链则获取重定向链接
        if source == "youtube_short_url":
            try:
                link = utils.get_redirect_url(link)
            except requests.exceptions.InvalidSchema:
                await embed_eos(ctx, response, author_name="链接异常", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
                await console.rp(f"链接重定向失败", ctx.guild, message_type=utils.PrintType.ERROR, print_head=True)
                return

            await console.rp(f"获取的重定向链接为 {link}", ctx.guild)

        if response is None:
            loading_msg, embed = await embed_respond(ctx, author_name="正在加载Youtube音频信息", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename), silent=True)
        else:
            loading_msg, embed = await embed_eos(ctx, response, author_name="正在加载Youtube音频信息", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename), silent=True)
        await play_youtube(ctx, link, response=loading_msg)

    # Link属于网易云音乐
    elif source == "netease_url" or source == "netease_short_url":
        # 如果是网易云短链则获取重定向链接
        if source == "netease_short_url":
            try:
                link = utils.get_redirect_url(link)
            except requests.exceptions.InvalidSchema:
                await embed_eos(ctx, response, author_name="链接异常", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
                await console.rp(f"链接重定向失败", ctx.guild, message_type=utils.PrintType.ERROR, print_head=True)
                return

            await console.rp(f"获取的重定向链接为 {link}", ctx.guild)

        if response is None:
            loading_msg, embed = await embed_respond(ctx, author_name="正在加载网易云音频信息", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename), silent=True)
        else:
            loading_msg, embed = await embed_eos(ctx, response, author_name="正在加载网易云音频信息", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename), silent=True)
        await play_netease(ctx, link, response=loading_msg)

    else:
        # await ctx.respond("未能检测到可用的链接或BV号，可使用\"/search_audio\"（搜索音频）指令直接进行搜索")
        # message = f"是否要进行搜索？\n"
        # view = AskForSearchingView(ctx, link, response=response)
        # view_msg = await ctx.send(message, view=view)
        # await view.set_original_msg(view_msg)

        await search_audio_callback(ctx, query=link)

    await current_guild.refresh_list_view()


async def play_audio(ctx: discord.ApplicationContext, target_audio: audio.Audio, response: Union[discord.Interaction, discord.InteractionMessage, None] = None, function_call: bool = False) -> None:
    """
    在<ctx>中的音频端播放音频<target_audio>，如果<single>为True则发送单曲加入成功通知
    <response>为用来编辑的加载信息，如果为None则发送新的通知

    :param ctx: 指令原句
    :param target_audio: 需要播放的音频
    :param response: 用于编辑的加载信息
    :param function_call 该指令是否是由其他函数调用
    """
    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    audio_lib_main.lock_audio(f"{ctx.guild.id}_NOW_PLAYING", target_audio)

    voice_client.play(
        discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                executable=ffmpeg_path, source=target_audio.get_path()
            )
        ),
        after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
    )
    voice_client.source.volume = current_guild.get_voice_volume() / 100.0

    await console.rp(f"开始播放：{target_audio.get_path()} 时长：{target_audio.get_duration_str()}", ctx.guild)
    playing_icon_filename = "vinyl_loop_playing_animated_infinite_100px.gif"
    if function_call:
        message, embed = await embed_respond(ctx, description=f"**{target_audio.get_title()}**", author_name=f"正在播放\u2003[{target_audio.get_duration_str()}]", author_icon_url=icon.url(playing_icon_filename), thumbnail=target_audio.get_cover_url(), files=icon_lib.files(playing_icon_filename), silent=True)
    else:
        message, embed = await embed_eos(ctx, response, description=f"**{target_audio.get_title()}**", author_name=f"正在播放\u2003[{target_audio.get_duration_str()}]", author_icon_url=icon.url(playing_icon_filename), thumbnail=target_audio.get_cover_url(), files=icon_lib.files(playing_icon_filename), silent=True)

    await current_guild.refresh_playing_message(message, embed)
    await current_guild.refresh_list_view()


async def play_next(ctx: discord.ApplicationContext) -> None:
    """
    播放列表中的下一个音频

    :param ctx: 指令原句
    """
    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    await console.rp(f"触发 play_next", ctx.guild)

    # 移除上一个音频
    finished_audio = current_playlist.pop_audio(0)
    # 解锁上一个音频
    audio_lib_main.unlock_audio(f"{ctx.guild.id}_NOW_PLAYING", finished_audio)

    # TODO 制作文件丢失处理方法，当前流程为文件丢失会触发播放Invalid argument，直接触发play_next进入下一个音频
    if len(current_playlist) > 0:
        # 获取下一个音频
        next_audio = current_playlist.get_audio(0)
        await play_audio(ctx, next_audio, response=None)

    else:
        await console.rp("播放队列已结束", ctx.guild)
        finished_icon_filename = "record_button_in_reveal_animated_0ms_100px.gif"
        await embed_send(ctx, author_name="播放队列已结束", author_icon_url=icon.url(finished_icon_filename), files=icon_lib.files(finished_icon_filename))
        await current_guild.refresh_playing_message(None, None)

    await current_guild.refresh_list_view()


async def play_bilibili(ctx: discord.ApplicationContext, source, link, response: Union[discord.Interaction, discord.InteractionMessage, None] = None, maximum_retry: int = 4):
    """
    下载并播放来自Bilibili的视频的音频

    :param ctx: 指令原句
    :param source: 链接类型
    :param link: 链接
    :param response: 用于编辑的加载信息
    :param maximum_retry: 下载失败时的最大重试次数
    """
    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    icon_list_filename = "todo_list_in_reveal_animated_0ms_100px.gif"
    icon_loading_filename = "hourglass_hover_rotation_animated_1000ms_infinite_30px.gif"
    icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"

    # 如果是URl则转换成BV号
    if source == "bilibili_url" or source == "bilibili_short_url":
        bvid = utils.get_bvid_from_url(link)
        if bvid is None:
            await embed_eos(ctx, response, author_name="无效的Bilibili链接", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
            await console.rp(f"{link} 为无效的链接", ctx.guild, message_type=utils.PrintType.ERROR, print_head=True)
            return
    else:
        bvid = link

    # 获取Bilibili视频信息
    info_result = await get_bilibili_info(ctx, bvid)
    info_dict = info_result["info_dict"]
    if info_dict is None:
        warning_description = f"[{bvid}] 信息获取失败：{info_result['message']}"
        if info_result["retryable"]:
            warning_description += "，请稍后再试"
        await embed_eos(ctx, response, author_name=warning_description, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename),  silent=True)
        return

    # 单一视频 bilibili_single 与 合集视频 bilibili_collection
    if info_dict["videos"] == 1:
        new_result = await download_bilibili_audio(ctx, info_dict, "bilibili_single", 0)
        new_audio = new_result["audio"]

        # 如果音频获取成功
        if new_audio is not None:

            # 如果当前播放列表为空
            if current_playlist.is_empty() and not voice_client.is_playing():
                await play_audio(ctx, new_audio, response=response)

            # 如果播放列表不为空
            else:
                await embed_eos(ctx, response, description=f"**{new_audio.get_title()}**", author_name=f"已加入播放列表\u2003[{new_audio.get_duration_str()}]", author_icon_url=icon.url(icon_list_filename), thumbnail=new_audio.get_cover_url(), files=icon_lib.files(icon_list_filename), silent=True)

            current_playlist.append_audio(new_audio)
            await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", ctx.guild)

            await current_guild.refresh_list_view()

        else:
            if isinstance(new_result["exception"], errors.StorageFull):
                await embed_eos(ctx, response, author_name=f"机器人当前处理音频过多，请稍后再试", author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
            elif new_result["retryable"]:
                # 如果不重试直接发送错误与稍后再试
                if maximum_retry < 1:
                    await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"] + "，请稍后再试", author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
                # 如果重试
                else:
                    retry_counter = 0
                    while retry_counter < maximum_retry:
                        retry_counter += 1

                        await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"] + f"：第 {retry_counter} 次重试中", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename))

                        new_result = await download_bilibili_audio(ctx, info_dict, "bilibili_single", 0)
                        new_audio = new_result["audio"]

                        # 如果音频加载成功
                        if new_audio is not None:

                            # 如果当前播放列表为空
                            if current_playlist.is_empty() and not voice_client.is_playing():
                                await play_audio(ctx, new_audio, response=response)

                            # 如果播放列表不为空
                            else:
                                await embed_eos(ctx, response, description=f"**{new_audio.get_title()}**", author_name=f"已加入播放列表\u2003[{new_audio.get_duration_str()}]", author_icon_url=icon.url(icon_list_filename), thumbnail=new_audio.get_cover_url(), files=icon_lib.files(icon_list_filename), silent=True)

                            current_playlist.append_audio(new_audio)
                            await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", ctx.guild)

                            await current_guild.refresh_list_view()
                            break

                    # 如果重试最终没有成功
                    if new_audio is None:
                        await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"] + "，请稍后再试")

            else:
                await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"])

        # 合集视频 bilibili_collection
        if "ugc_season" in info_dict:
            menu = CheckCollectionMenu(ctx, "bilibili_collection", info_dict, response=response)
            await menu.init_respond(ephemeral=True)

    # 分P视频 bilibili_p
    else:
        p_info_list = []
        for item in info_dict["pages"]:
            p_title = item["part"]
            p_time_str = utils.convert_duration_to_str(item["duration"])
            p_info_list.append((p_title, p_time_str))

        menu_list = utils.make_playlist_page(p_info_list, 10, {None: "> "}, {}, escape_markdown=True)
        menu = EpisodeSelectMenu(ctx, "bilibili_p", info_dict, menu_list, "哔哩哔哩分P", list_title=info_dict["title"])
        await menu.init_eos(response=response, silent=True)
        return


async def get_bilibili_info(ctx: discord.ApplicationContext, bvid: str) -> dict:
    try:
        info_dict = await bilibili.get_info(bvid)
    except bilibili_api.ResponseCodeException as e:
        await console.rp(
            f"触发异常bilibili_api.ResponseCodeException，哔哩哔哩无响应，{bvid}可能已失效或存在区域版权限制",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"info_dict": None, "exception": e, "message": "无响应，资源可能已失效或存在区域版权限制", "retryable": False}
    except bilibili_api.ArgsException as e:
        await console.rp(
            f"触发异常bilibili_api.ArgsException，{bvid}信息获取失败，参数异常，可能为bvid错误",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"info_dict": None, "exception": e, "message": "参数错误，请检查链接中的BV号是否正确完整", "retryable": False}
    except aiohttp.ClientResponseError as e:
        await console.rp(
            f"触发异常aiohttp.ClientResponseError，{bvid}信息获取失败，可能为请求繁忙",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"info_dict": None, "exception": e, "message": "请求繁忙", "retryable": True}
    except httpx.ConnectTimeout as e:
        await console.rp(
            f"触发异常httpx.ConnectTimeout，{bvid}信息获取失败，网络主机连接超时",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"info_dict": None, "exception": e, "message": "网络主机连接超时", "retryable": True}
    except httpx.RemoteProtocolError as e:
        await console.rp(
            f"触发异常httpx.RemoteProtocolError，{bvid}信息获取失败，服务器协议错误",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"info_dict": None, "exception": e, "message": "服务器协议错误", "retryable": True}
    else:
        if info_dict is not None:
            return {"info_dict": info_dict, "exception": None, "message": "获取成功", "retryable": False}
        else:
            return {"info_dict": info_dict, "exception": None, "message": "参照错误日志", "retryable": False}



async def download_bilibili_audio(ctx: discord.ApplicationContext, info_dict, audio_type, num_option: int = 0) -> dict:
    """
    下载哔哩哔哩音频
    """
    if audio_type == "bilibili_p":
        title = f"[{info_dict['bvid']}] {info_dict['title']} - {num_option + 1}p"
    elif audio_type == "bilibili_collection":
        title = info_dict["ugc_season"]["sections"][0]["episodes"][num_option]["title"]
    else:
        title = f"[{info_dict['bvid']}] {info_dict['title']}"

    try:
        if audio_type == "bilibili_collection":
            bvid = info_dict["ugc_season"]["sections"][0]["episodes"][num_option]["bvid"]
            info_dict = await bilibili.get_info(bvid)
            num_option = 0  # 在上方完成对应信息提取后，重制num_option为0，因为合集中的视频是独立的，分p序号为0

        new_audio = await audio_lib_main.download_bilibili(info_dict, audio_type, num_option)

    except errors.StorageFull as e:
        await console.rp("库已满，播放列表添加失败", ctx.guild, message_type=utils.PrintType.ERROR, print_head=True)
        return {"audio": None, "exception": e, "message": "当前机器人处理音频过多", "retryable": False}
    except bilibili_api.ResponseCodeException as e:
        await console.rp(
            f"触发异常bilibili_api.ResponseCodeException，哔哩哔哩无响应，{title}可能已失效或存在区域版权限制",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"audio": None, "exception": e, "message": "无响应，资源可能已失效或存在区域版权限制", "retryable": False}
    except bilibili_api.ArgsException as e:
        await console.rp(
            f"触发异常bilibili_api.ArgsException，{title}获取失败，参数异常，可能为bvid错误",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"audio": None, "exception": e, "message": "参数错误，请检查链接中的BV号是否正确完整", "retryable": False}
    except aiohttp.ClientResponseError as e:
        await console.rp(
            f"触发异常aiohttp.ClientResponseError，{title}获取失败，可能为请求繁忙",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"audio": None, "exception": e, "message": "请求繁忙", "retryable": True}
    except httpx.ConnectTimeout as e:
        await console.rp(
            f"触发异常httpx.ConnectTimeout，{title}获取失败，网络主机连接超时",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"audio": None, "exception": e, "message": "网络主机连接超时", "retryable": True}
    except httpx.RemoteProtocolError as e:
        await console.rp(
            f"触发异常httpx.RemoteProtocolError，{title}获取失败，服务器协议错误",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"audio": None, "exception": e, "message": "服务器协议错误", "retryable": True}

    else:
        if new_audio is not None:
            return {"audio": new_audio, "exception": None, "message": "获取成功", "retryable": False}
        else:
            return {"audio": new_audio, "exception": None, "message": "参照错误日志", "retryable": False}


async def play_youtube(ctx: discord.ApplicationContext, link, response=None, maximum_retry: int = 4) -> None:
    """
    下载并播放来自YouTube的视频的音频

    :param ctx: 指令原句
    :param link: 链接
    :param response: 用于编辑的加载信息
    :return: 播放的音频（如果为播放列表或获取失败则返回None）
    :param maximum_retry: 下载失败时的最大重试次数
    """
    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    icon_list_filename = "todo_list_in_reveal_animated_0ms_100px.gif"
    icon_loading_filename = "hourglass_hover_rotation_animated_1000ms_infinite_30px.gif"
    icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"

    # 先提取信息
    info_result = await get_ytdlp_info(ctx, link)
    info_dict = info_result["info_dict"]
    if info_dict is None:
        warning_description = f"[{link}] 信息获取失败：{info_result['message']}"
        if info_result["retryable"]:
            warning_description += "，请稍后再试"
        await embed_eos(ctx, response, author_name=warning_description, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename),  silent=True)
        return

    # 带播放列表信息的独立视频
    if "_type" in info_dict and info_dict["_type"] == "url":
        # 截出播放列表信息
        link_playlist = info_dict["url"]
        info_result_playlist = await get_ytdlp_info(ctx, link_playlist)
        info_dict_playlist = info_result_playlist["info_dict"]
        if info_dict_playlist is None:
            warning_description = f"[{link}] 列表信息获取失败：{info_result_playlist['message']}，无法查看其所在的播放列表"
            if info_result_playlist["retryable"]:
                warning_description += "，请稍后再试"
            await embed_eos(ctx, response, author_name=warning_description, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)

        # 重新获取独立视频信息
        link = link[:link.find("&list")]
        info_result = await get_ytdlp_info(ctx, link)
        info_dict = info_result["info_dict"]
        if info_dict is None:
            warning_description = f"[{link}] 信息获取失败：{info_result['message']}"
            if info_result["retryable"]:
                warning_description += "，请稍后再试"
            await embed_eos(ctx, response, author_name=warning_description, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
            return

        link_type = "youtube_single"

        # 询问是否查看播放列表
        if info_dict_playlist is not None:
            menu = CheckCollectionMenu(ctx, "youtube_playlist", info_dict_playlist, response=response)
            await menu.init_respond(ephemeral=True)

    # 播放列表
    elif "_type" in info_dict and info_dict["_type"] == "playlist":
        link_type = "youtube_playlist"

    # 独立视频
    else:
        link_type = "youtube_single"

    # 独立视频 youtube_single
    if link_type == "youtube_single":
        new_result = await download_ytdlp_audio(ctx, link, info_dict, "youtube_single")
        new_audio = new_result["audio"]

        if new_audio is not None:
            if current_playlist.is_empty() and not voice_client.is_playing():
                await play_audio(ctx, new_audio, response=response)

            # 如果列表为空则会有正在播放提示，否则加入列表提示
            if not current_playlist.is_empty():
                await embed_eos(ctx, response, description=f"**{utils.markdown_escape(new_audio.get_title())}**", author_name=f"已加入播放列表\u2003[{new_audio.get_duration_str()}]", author_icon_url=icon.url(icon_list_filename), thumbnail=new_audio.get_cover_url(), files=icon_lib.files(icon_list_filename), silent=True)

            # 添加至服务器播放列表
            current_playlist.append_audio(new_audio)
            await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", ctx.guild)

            await current_guild.refresh_list_view()

        else:
            if isinstance(new_result["exception"], errors.StorageFull):
                await embed_eos(ctx, response, author_name=f"机器人当前处理音频过多，请稍后再试", author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
            elif new_result["retryable"]:
                # 如果不重试直接发送错误与稍后再试
                if maximum_retry < 1:
                    await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"] + "，请稍后再试", author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
                # 如果重试
                else:
                    retry_counter = 0
                    while retry_counter < maximum_retry:
                        retry_counter += 1

                        await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"] + f"：第 {retry_counter} 次重试中", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename))

                        new_result = await download_ytdlp_audio(ctx, link, info_dict, "youtube_single")
                        new_audio = new_result["audio"]

                        # 如果音频加载成功
                        if new_audio is not None:

                            # 如果当前播放列表为空
                            if current_playlist.is_empty() and not voice_client.is_playing():
                                await play_audio(ctx, new_audio, response=response)

                            # 如果播放列表不为空
                            else:
                                await embed_eos(ctx, response, description=f"**{new_audio.get_title()}**", author_name=f"已加入播放列表\u2003[{new_audio.get_duration_str()}]", author_icon_url=icon.url(icon_list_filename), thumbnail=new_audio.get_cover_url(), files=icon_lib.files(icon_list_filename), silent=True)

                            current_playlist.append_audio(new_audio)
                            await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", ctx.guild)

                            await current_guild.refresh_list_view()
                            break

                    # 如果重试最终没有成功
                    if new_audio is None:
                        await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"] + "，请稍后再试")

            else:
                await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"])

    # 播放列表 youtube_playlist
    elif link_type == "youtube_playlist":
        ep_info_list = []
        for item in info_dict["entries"]:
            ep_title = item["title"]
            ep_time_str = utils.convert_duration_to_str(item["duration"])
            ep_info_list.append((ep_title, ep_time_str))
        playlist_title = info_dict['title']
        menu_list = utils.make_playlist_page(ep_info_list, 10, {None: "> "}, {}, escape_markdown=True)
        menu = EpisodeSelectMenu(ctx, "youtube_playlist", info_dict, menu_list, "YouTube播放列表", playlist_title)
        await menu.init_eos(response=response, silent=True)


async def play_netease(ctx: discord.ApplicationContext, link, response=None, maximum_retry: int = 4) -> None:
    """
    下载并播放来自网易云音乐的音频

    :param ctx: 指令原句
    :param link: 链接
    :param response: 用于编辑的加载信息
    :return: 播放的音频（如果为播放列表或获取失败则返回None）
    :param maximum_retry: 下载失败时的最大重试次数
    """
    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    icon_list_filename = "todo_list_in_reveal_animated_0ms_100px.gif"
    icon_loading_filename = "hourglass_hover_rotation_animated_1000ms_infinite_30px.gif"
    icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"

    # 截取出yt-dlp可读取的部分（目前已知yt-dlp 2024.07.25不能读取包含/my/m/music/的链接）
    link = utils.get_legal_netease_url(link)

    # 先提取信息
    info_result = await get_ytdlp_info(ctx, link)
    info_dict = info_result["info_dict"]
    if info_dict is None:
        warning_description = f"[{link}] 信息获取失败：{info_result['message']}"
        if info_result["retryable"]:
            warning_description += "，请稍后再试"
        await embed_eos(ctx, response, author_name=warning_description, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename),  silent=True)
        return

    # 播放列表
    if "_type" in info_dict and info_dict["_type"] == "playlist":
        link_type = "netease_playlist"

    # 独立音频
    else:
        link_type = "netease_single"

    # 独立音频 netease_single
    if link_type == "netease_single":
        new_result = await download_ytdlp_audio(ctx, link, info_dict, "netease_single")
        new_audio = new_result["audio"]

        if new_audio is not None:
            if current_playlist.is_empty() and not voice_client.is_playing():
                await play_audio(ctx, new_audio, response=response)

            # 如果列表为空则会有正在播放提示，否则加入列表提示
            if not current_playlist.is_empty():
                await embed_eos(ctx, response, description=f"**{utils.markdown_escape(new_audio.get_title())}**", author_name=f"已加入播放列表\u2003[{new_audio.get_duration_str()}]", author_icon_url=icon.url(icon_list_filename), thumbnail=new_audio.get_cover_url(), files=icon_lib.files(icon_list_filename), silent=True)

            # 添加至服务器播放列表
            current_playlist.append_audio(new_audio)
            await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", ctx.guild)

            await current_guild.refresh_list_view()

        else:
            if isinstance(new_result["exception"], errors.StorageFull):
                await embed_eos(ctx, response, author_name=f"机器人当前处理音频过多，请稍后再试", author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
            elif new_result["retryable"]:
                # 如果不重试直接发送错误与稍后再试
                if maximum_retry < 1:
                    await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"] + "，请稍后再试", author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
                # 如果重试
                else:
                    retry_counter = 0
                    while retry_counter < maximum_retry:
                        retry_counter += 1

                        await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"] + f"：第 {retry_counter} 次重试中", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename))

                        new_result = await download_ytdlp_audio(ctx, link, info_dict, "netease_single")
                        new_audio = new_result["audio"]

                        # 如果音频加载成功
                        if new_audio is not None:

                            # 如果当前播放列表为空
                            if current_playlist.is_empty() and not voice_client.is_playing():
                                await play_audio(ctx, new_audio, response=response)

                            # 如果播放列表不为空
                            else:
                                await embed_eos(ctx, response, description=f"**{new_audio.get_title()}**", author_name=f"已加入播放列表\u2003[{new_audio.get_duration_str()}]", author_icon_url=icon.url(icon_list_filename), thumbnail=new_audio.get_cover_url(), files=icon_lib.files(icon_list_filename), silent=True)

                            current_playlist.append_audio(new_audio)
                            await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", ctx.guild)

                            await current_guild.refresh_list_view()
                            break

                    # 如果重试最终没有成功
                    if new_audio is None:
                        await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"] + "，请稍后再试")

            else:
                await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"])

    # 播放列表 netease_playlist
    elif link_type == "netease_playlist":
        ep_info_list = []
        for item in info_dict["entries"]:
            ep_title = item["title"]
            # ep_info_list内的所有元组只包含ep_title一个元素，不要去掉()内的逗号
            ep_info_list.append((ep_title,))
        playlist_title = info_dict['title']
        menu_list = utils.make_playlist_page(ep_info_list, 10, {None: "> "}, {}, escape_markdown=True)
        menu = EpisodeSelectMenu(ctx, "netease_playlist", info_dict, menu_list, "网易云播放列表", playlist_title)
        await menu.init_eos(response=response, silent=True)


async def get_ytdlp_info(ctx: discord.ApplicationContext, link) -> dict:
    try:
        info_dict = await ytdlp.get_info(link)

    except yt_dlp.utils.DownloadError as e:
        await console.rp(
            "触发异常yt_dlp.utils.DownloadError，YT-DLP信息获取失败，该视频/音频可能已失效或存在区域版权限制",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"info_dict": None, "exception": e, "message": "YT-DLP下载失败，该视频/音频可能已失效或存在区域版权限制", "retryable": False}
    except yt_dlp.utils.ExtractorError as e:
        await console.rp(
            "触发异常yt_dlp.utils.ExtractorError，音频不可用",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"info_dict": None, "exception": e, "message": "音频信息获取失败", "retryable": False}
    except yt_dlp.utils.UnavailableVideoError as e:
        await console.rp(
            "触发异常yt_dlp.utils.UnavailableVideoError，音频不可用",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"info_dict": None, "exception": e, "message": "音频信息获取失败", "retryable": False}
    except discord.HTTPException as e:
        await console.rp(
            "触发异常discord.HTTPException，网络错误",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"info_dict": None, "exception": e, "message": "音频信息获取失败", "retryable": False}

    else:
        if info_dict is not None:
            return {"info_dict": info_dict, "exception": None, "message": "获取成功", "retryable": False}
        else:
            return {"info_dict": info_dict, "exception": None, "message": "参照错误日志", "retryable": False}

async def download_ytdlp_audio(ctx: discord.ApplicationContext, link, info_dict, link_type) -> dict:
    try:
        # 开始下载
        new_audio = await audio_lib_main.download_ytdlp(link, info_dict, link_type)

    except errors.StorageFull as e:
        await console.rp("库已满，播放列表添加失败", ctx.guild, message_type=utils.PrintType.ERROR, print_head=True)
        return {"audio": None, "exception": e, "message": "当前机器人处理音频过多", "retryable": False}
    except yt_dlp.utils.DownloadError as e:
        await console.rp(
            "触发异常yt_dlp.utils.DownloadError，YT-DLP下载失败，该视频/音频可能已失效或存在区域版权限制",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"audio": None, "exception": e, "message": "YT-DLP下载失败，该视频/音频可能已失效或存在区域版权限制", "retryable": False}
    except yt_dlp.utils.ExtractorError as e:
        await console.rp(
            "触发异常yt_dlp.utils.ExtractorError，视频/音频不可用",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"audio": None, "exception": e, "message": "视频/音频获取失败", "retryable": False}
    except yt_dlp.utils.UnavailableVideoError as e:
        await console.rp(
            "触发异常yt_dlp.utils.UnavailableVideoError，视频/音频不可用",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"audio": None, "exception": e, "message": "视频/音频获取失败", "retryable": False}
    except discord.HTTPException as e:
        await console.rp(
            "触发异常discord.HTTPException，网络错误",
            ctx.guild,
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        return {"audio": None, "exception": e, "message": "视频/音频获取失败", "retryable": False}

    else:
        if new_audio is not None:
            return {"audio": new_audio, "exception": None, "message": "获取成功", "retryable": False}
        else:
            return {"audio": new_audio, "exception": None, "message": "参照错误日志", "retryable": False}


async def pause_callback(ctx: discord.ApplicationContext, command_call: bool = False):
    """
    暂停播放

    :param ctx: 指令原句
    :param command_call: 该指令是否是由用户指令调用
    :return:
    """
    await guild_lib.check(ctx, audio_lib_main)

    voice_client = ctx.guild.voice_client

    pause_icon_filename = "pause_in_reveal_animated_0ms_100px.gif"
    if voice_client is not None and voice_client.is_playing():
        # if ctx.user.voice and voice_client.channel == ctx.user.voice.channel:
        voice_client.pause()
        await console.rp("暂停播放", ctx.guild)
        if command_call:
            await embed_respond(ctx, author_name="暂停播放", author_icon_url=icon.url(pause_icon_filename), files=icon_lib.files(pause_icon_filename))
        # else:
        #     logger.rp(f"收到pause指令时指令发出者 {ctx.author} 不在机器人所在的频道", ctx.guild)
        #     await ctx.respond(f"您不在{setting.value('bot_name')}所在的频道")

    elif voice_client.is_paused():
        await console.rp("收到pause指令时机器人已经处于暂停状态", ctx.guild)
        if command_call:
            await embed_respond(ctx, "已在暂停中，使用 /resume 指令恢复播放", silent=True)

    else:
        await console.rp("收到pause指令时机器人未在播放任何音乐", ctx.guild)
        if command_call:
            await embed_respond(ctx, "未在播放任何音乐", silent=True)


async def resume_callback(ctx: discord.ApplicationContext, command_call: bool = False):
    """
    恢复播放

    :param ctx: 指令原句
    :param command_call: 该函数是否是由用户指令调用
    :return:
    """
    await guild_lib.check(ctx, audio_lib_main)

    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    resume_icon_filename = "play_button_in_reveal_animated_0ms_100px.gif"

    # 播放列表为空的情况
    # if current_playlist.is_empty():
    #     logger.rp("收到resume指令时服务器主播放列表内没有任何音频", ctx.guild)
    #     await ctx.respond(f"播放列表中没有任何音频，可以使用/play指令来添加来自哔哩哔哩或者YouTube的音频")
    #     return

    # 未加入语音频道的情况
    if voice_client is None:
        await console.rp("机器人未在任何语音频道中，尝试加入语音频道", ctx.guild)
        join_result = await join_callback(ctx, command_call=False)
        if not join_result:
            return
        else:
            voice_client = ctx.guild.voice_client

    # 被暂停播放的情况
    if voice_client.is_paused():
        if ctx.user.voice and voice_client.channel == ctx.user.voice.channel:
            voice_client.resume()
            await console.rp("恢复播放", ctx.guild)
            if command_call:
                await embed_respond(ctx, author_name="恢复播放", author_icon_url=icon.url(resume_icon_filename), files=icon_lib.files(resume_icon_filename))
        else:
            await console.rp(f"收到pause指令时指令发出者 {ctx.author} 不在机器人所在的频道", ctx.guild)
            if command_call:
                await embed_respond(ctx, f"您不在{setting.value('bot_name')}所在的频道", silent=True)

    # 没有被暂停并且正在播放的情况
    elif voice_client.is_playing():
        if command_call:
            await console.rp("收到resume指令时机器人正在播放音频", ctx.guild)
            await embed_respond(ctx, f"{bot_name}正在频道{voice_client.channel}播放音频", silent=True)

    # 没有被暂停，没有正在播放，并且播放列表中存在歌曲的情况
    elif not current_playlist.is_empty():
        current_audio = current_playlist.get_audio(0)

        await play_audio(ctx, current_audio, function_call=True)

        await console.rp("恢复中断的播放列表", ctx.guild)
        if command_call:
            await embed_respond(ctx, author_name=f"恢复上次中断的播放列表", author_icon_url=icon.url(resume_icon_filename), files=icon_lib.files(resume_icon_filename))

    else:
        if command_call:
            await console.rp("收到resume指令时机器人没有任何被暂停的音乐", ctx.guild)
            await embed_respond(ctx, "当前没有任何被暂停的音乐", silent=True)

    await current_guild.refresh_list_view()


# TODO 显示添加人
async def list_callback(ctx: discord.ApplicationContext):
    """
    将当前服务器播放列表发送到服务器文字频道中

    :param ctx: 指令原句
    :return:
    """
    await guild_lib.check(ctx, audio_lib_main)

    current_menu = PlaylistMenu(ctx)
    previous_menu = None

    # 如果有更早的View则让其执行被覆盖程序，active_views替换为当前刚生成的View，为了显示效果先获取之前的View，在发送完毕后再覆盖
    current_guild = guild_lib.get_guild(ctx)
    guild_active_views = current_guild.get_active_views()
    if "playlist_menu_view" in guild_active_views and guild_active_views["playlist_menu_view"] is not None:
        previous_menu = guild_active_views["playlist_menu_view"]

    # 更新为刚生成的View
    guild_active_views["playlist_menu_view"] = current_menu

    # 发送刚刚生成的菜单
    await current_menu.init_respond(silent=True)

    # 让先前的View执行被覆盖程序
    if previous_menu is not None:
        await previous_menu.on_override()


async def skip_callback(ctx, first_index: Union[int, str, None] = None, second_index: Union[int, None] = None, command_call: bool = False, refresh_view: bool = True):
    """
    使机器人跳过指定的歌曲，并删除对应歌曲的文件
    *注意*：此方法输入的index从1开始，不是0

    :param ctx: 指令原句
    :param first_index: 跳过起始曲目的序号（从1开始）
    :param second_index: 跳过最终曲目的序号（包含）
    :param command_call: 该函数是否是由用户指令调用
    :return:
    """
    await guild_lib.check(ctx, audio_lib_main)

    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    icon_skip_filename = "play_forward_hover_pinch_animated_0ms_100px.gif"
    icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"
    
    if not current_playlist.is_empty():
        # 不输入参数的情况
        if first_index is None and second_index is None:
            current_audio = current_playlist.get_audio(0)
            title = current_audio.get_title()
            duration_str = current_audio.get_duration_str()

            if voice_client is not None:
                voice_client_is_paused = voice_client.is_paused()
                voice_client.stop()
                # 如果跳过之前正在暂停状态且准备播放下一个音频，则恢复暂停状态
                if not voice_client.is_playing() and voice_client_is_paused:
                    voice_client.pause()
                    await embed_send(ctx, "播放器已被暂停，使用/resume指令恢复播放", silent=True)
            else:
                current_playlist.remove_audio(0)

            await console.rp(f"第1个音频 {title} 已被用户 {ctx.user} 移出播放列表", ctx.guild)

            if command_call:
                await embed_respond(ctx, description=f"**{utils.markdown_escape(title)}**", author_name=f"已跳过当前音频\u2003[{duration_str}]", author_icon_url=icon.url(icon_skip_filename), files=icon_lib.files(icon_skip_filename))
            else:
                await embed_send(ctx, description=f"**{utils.markdown_escape(title)}**", author_name=f"已跳过当前音频\u2003[{duration_str}]", author_icon_url=icon.url(icon_skip_filename), files=icon_lib.files(icon_skip_filename))

        # 输入1个参数的情况
        elif second_index is None:

            if first_index == "*":
                await clear_callback(ctx)

            elif int(first_index) == 1:
                current_audio = current_playlist.get_audio(0)
                title = current_audio.get_title()
                duration_str = current_audio.get_duration_str()

                # voice_client存在，且是正在播放或者是暂停的状态（为了排除重启后已连接voice_client但未播放的状态）
                if voice_client is not None and (voice_client.is_playing() or voice_client.is_paused()):
                    voice_client.stop()
                else:
                    current_playlist.remove_audio(0)

                await console.rp(f"第1个音频 {title} 已被用户 {ctx.user} 移出播放列表", ctx.guild)
                if command_call:
                    await embed_respond(ctx, description=f"**{utils.markdown_escape(title)}**", author_name=f"已跳过当前音频\u2003[{duration_str}]", author_icon_url=icon.url(icon_skip_filename), files=icon_lib.files(icon_skip_filename))
                else:
                    await embed_send(ctx, description=f"**{utils.markdown_escape(title)}**", author_name=f"已跳过当前音频\u2003[{duration_str}]", author_icon_url=icon.url(icon_skip_filename), files=icon_lib.files(icon_skip_filename))

            elif int(first_index) > len(current_playlist):
                await console.rp(f"用户 {ctx.author} 输入的序号不在范围内", ctx.guild)
                if command_call:
                    await embed_respond(ctx, author_name=f"选择的序号不在范围内", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
                else:
                    await embed_send(ctx, author_name=f"选择的序号不在范围内", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)

            else:
                first_index = int(first_index)
                select_audio = current_playlist.get_audio(first_index - 1)
                title = select_audio.get_title()
                duration_str = select_audio.get_duration_str()
                current_playlist.remove_audio(first_index - 1)

                await console.rp(f"第{first_index}个音频 {title} 已被用户 {ctx.user} 移出播放列表", ctx.guild)
                if command_call:
                    await embed_respond(ctx, description=f"**{utils.markdown_escape(title)}**", author_name=f"第 {first_index} 个音频已被移出播放列表\u2003[{duration_str}]", author_icon_url=icon.url(icon_skip_filename), files=icon_lib.files(icon_skip_filename))
                else:
                    await embed_send(ctx, description=f"**{utils.markdown_escape(title)}**", author_name=f"第 {first_index} 个音频已被移出播放列表\u2003[{duration_str}]", author_icon_url=icon.url(icon_skip_filename), files=icon_lib.files(icon_skip_filename))

        # 输入2个参数的情况
        elif int(first_index) < int(second_index):
            first_index = int(first_index)
            second_index = int(second_index)

            # 如果需要跳过正在播放的歌，则需要先移除除第一首歌以外的歌曲，第一首由stop()触发play_next移除
            if first_index == 1:
                for i in range(second_index, first_index, -1):
                    current_playlist.remove_audio(i - 1)

                if voice_client is not None:
                    voice_client.stop()
                else:
                    current_playlist.remove_audio(0)

                await console.rp(
                    f"第{first_index}到第{second_index}个音频被用户 {ctx.author} 移出播放列表",
                    ctx.guild
                )
                if command_call:
                    await embed_respond(ctx, author_name=f"第 {first_index} 到第 {second_index} 个音频已被移出播放列表", author_url=icon.url(icon_skip_filename), files=icon_lib.files(icon_skip_filename))
                else:
                    await embed_send(ctx, author_name=f"第 {first_index} 到第 {second_index} 个音频已被移出播放列表", author_url=icon.url(icon_skip_filename), files=icon_lib.files(icon_skip_filename))

            elif int(first_index) > len(current_playlist) or int(second_index) > len(current_playlist):
                await console.rp(f"用户 {ctx.author} 输入的序号不在范围内", ctx.guild)
                if command_call:
                    await embed_respond(ctx, author_name=f"选择的序号不在范围内", author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
                else:
                    await embed_send(ctx, author_name=f"选择的序号不在范围内", author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)

            # 不需要跳过正在播放的歌
            else:
                for i in range(second_index, first_index - 1, -1):
                    current_playlist.remove_audio(i - 1)

                await console.rp(f"第{first_index}到第{second_index}个音频被用户 {ctx.author} 移出播放列表", ctx.guild)
                if command_call:
                    await embed_respond(ctx, author_name=f"第{first_index}到第{second_index}个音频已被移出播放列表", author_icon_url=icon.url(icon_skip_filename), files=icon_lib.files(icon_skip_filename))
                else:
                    await embed_send(ctx, author_name=f"第{first_index}到第{second_index}个音频已被移出播放列表", author_icon_url=icon.url(icon_skip_filename), files=icon_lib.files(icon_skip_filename))

        else:
            if command_call:
                await embed_respond(ctx, author_name="参数错误", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
            else:
                await embed_send(ctx, author_name="参数错误", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
            await console.rp(f"用户 {ctx.author} 的skip指令参数错误", ctx.guild)

    else:
        if command_call:
            await embed_respond(ctx, "当前播放列表已为空", silent=True)
        else:
            await embed_send(ctx, "当前播放列表已为空", silent=True)

    if refresh_view:
        await current_guild.refresh_list_view()


async def move_callback(ctx, from_number: Union[int, None] = None, to_number: Union[int, None] = None):
    await guild_lib.check(ctx, audio_lib_main)

    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    icon_filename = "left_right_in_reveal_animated_0ms_100px.gif"

    if from_number is None or to_number is None:
        await embed_respond(ctx, "请输入想要移动的歌曲序号以及想要移动到的位置", silent=True)

    # 两个参数相同的情况
    elif from_number == to_number:
        await embed_respond(ctx, "您搁这儿搁这儿呢（序号相同）", colour=orange, silent=True)

    # 先将音频复制到目的位置，然后通过stop移除正在播放的音频
    # 因为有重复所以stop不会删除本地文件

    # 将第一个音频移走的情况
    elif from_number == 1:
        current_audio = current_playlist.get_audio(0)
        title = current_audio.get_title()
        current_playlist.insert_audio(current_audio, to_number)
        voice_client.stop()

        await console.rp(f"音频 {title} 已被用户 {ctx.author} 移至播放列表第 {to_number} 位", ctx.guild)
        await embed_respond(ctx, description=f"{utils.markdown_escape(title)}", author_name=f"移动至播放列表第 {to_number} 位", author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename))

    # 将音频移到当前位置
    elif to_number == 1:
        current_audio = current_playlist.get_audio(0)
        target_song = current_playlist.get_audio(from_number - 1)
        title = target_song.get_title()
        current_playlist.remove_audio(from_number - 1)
        current_playlist.insert_audio(current_audio, 1)
        current_playlist.insert_audio(target_song, 1)
        voice_client.stop()

        await console.rp(f"音频 {title} 已被用户 {ctx.author} 移至播放列表第 {to_number} 位", ctx.guild)
        await embed_respond(ctx, description=f"{utils.markdown_escape(title)}", author_name=f"移动至播放列表第 {to_number} 位", author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename))

    else:
        target_song = current_playlist.get_audio(from_number - 1)
        title = target_song.get_title()
        if from_number < to_number:
            current_playlist.insert_audio(target_song, to_number)
            current_playlist.remove_audio(from_number - 1)
        else:
            current_playlist.insert_audio(target_song, to_number - 1)
            current_playlist.remove_audio(from_number)

        await console.rp(f"音频 {title} 已被用户 {ctx.author} 移至播放列表第 {to_number} 位", ctx.guild)
        await embed_respond(ctx, description=f"{utils.markdown_escape(title)}", author_name=f"移动至播放列表第 {to_number} 位", author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename))

    await current_guild.refresh_list_view()


async def clear_callback(ctx):
    """
    清空当前服务器的播放列表

    :param ctx: 指令原句
    :return:
    """
    await guild_lib.check(ctx, audio_lib_main)

    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    # voice_client存在，且是正在播放或者是暂停的状态（为了排除重启后已连接voice_client但未播放的状态）
    if voice_client is not None and (voice_client.is_playing() or voice_client.is_paused()):
        # remove_all跳过正在播放的歌曲
        current_playlist.remove_all(skip_first=True)
        # stop触发play_next删除正在播放的歌曲
        voice_client.stop()
    else:
        current_playlist.remove_all()

    await console.rp(f"用户 {ctx.author} 已清空所在服务器的播放列表", ctx.guild)
    clear_icon_filename = "bin_hover_empty_animated_0ms_100px.gif"
    await embed_respond(ctx, author_name="播放列表已清空", author_icon_url=icon.url(clear_icon_filename), files=icon_lib.files(clear_icon_filename))


async def volume_callback(ctx: discord.ApplicationContext, volume_num=None) -> None:
    voice_client = ctx.guild.voice_client
    await guild_lib.check(ctx, audio_lib_main)
    current_volume = guild_lib.get_guild(ctx).get_voice_volume()

    icon_filename = "speaker_hover_pinch_animated_0ms_100px.gif"
    icon_mute_filename = "speaker_hover_mute_animated_0ms_100px.gif"

    if volume_num is None:
        await embed_respond(ctx, author_name=f"当前音量为：{current_volume}%", author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename), silent=True)

    elif volume_num == "up" or volume_num == "u" or volume_num == "+" or volume_num == "＋":
        if current_volume + 20.0 >= 200:
            current_volume = 200.0
        else:
            current_volume += 20.0

        if voice_client is not None and voice_client.is_playing():
            voice_client.source.volume = current_volume / 100.0
        guild_lib.get_guild(ctx).set_voice_volume(current_volume)

        await console.rp(f"用户 {ctx.author} 已将音量设置为 {current_volume}%", ctx.guild)
        await embed_respond(ctx, author_name=f"将音量提升至：{current_volume}%", author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename))

    elif volume_num == "down" or volume_num == "d" or volume_num == "-":
        if current_volume - 20.0 <= 0.0:
            current_volume = 0.0
        else:
            current_volume -= 20.0

        if voice_client is not None and voice_client.is_playing():
            voice_client.source.volume = current_volume / 100.0
        guild_lib.get_guild(ctx).set_voice_volume(current_volume)

        await console.rp(f"用户 {ctx.author} 已将音量设置为 {current_volume}%", ctx.guild)

        if current_volume == 0.0:
            await embed_respond(ctx, author_name=f"将音量降低至：{current_volume}%", author_icon_url=icon.url(icon_mute_filename), files=icon_lib.files(icon_mute_filename))
        else:
            await embed_respond(ctx, author_name=f"将音量降低至：{current_volume}%", author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename))

    else:
        try:
            volume_num = float(int(float(volume_num)))
        except ValueError:
            await embed_respond(ctx, "请输入up或down来提升或降低音量或一个0-200的数字来设置音量", silent=True)
            return

        if volume_num > 200.0 or volume_num < 0.0:
            await embed_respond(ctx, "请输入up或down来提升或降低音量或一个0-200的数字来设置音量", silent=True)

        else:
            current_volume = volume_num

            if voice_client is not None and voice_client.is_playing():
                voice_client.source.volume = current_volume / 100.0
            guild_lib.get_guild(ctx).set_voice_volume(current_volume)

            await console.rp(f"用户 {ctx.author} 已将音量设置为 {current_volume}%", ctx.guild)

            if current_volume == 0.0:
                await embed_respond(ctx, author_name=f"将音量设置为：{current_volume}%", author_icon_url=icon.url(icon_mute_filename), files=icon_lib.files(icon_mute_filename))
            else:
                await embed_respond(ctx, author_name=f"将音量设置为：{current_volume}%", author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename))


async def reboot_callback(ctx):
    """
    重启程序
    """
    await guild_lib.save_all()

    icon_filename = "spin_in_reveal_0ms_100px.gif"
    await embed_respond(ctx, author_name="正在重启", colour=red, author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename))

    os.execl(python_path, python_path, * sys.argv)


async def shutdown_callback(ctx):
    """
    退出程序
    """
    await guild_lib.save_all()

    icon_filename = "logout_hover_pinch_red_animated_0ms_100px.gif"
    await embed_respond(ctx, author_name="正在关闭", colour=red, author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename))
    await bot.close()


class PlaylistMenu(View):

    def __init__(self, ctx, timeout: int = 600):
        """
        *注意*
        - 当前View被创建和发送后需要调用set_original_msg确保以后可被正确主动刷新
        - 如需执行覆盖操作则需要在外部更新guild_active_views中的View（换为新View）
        """
        super().__init__(timeout=timeout)
        self.ctx: discord.ApplicationContext = ctx
        self.guild = guild_lib.get_guild(self.ctx)
        self.playlist = self.guild.get_playlist()

        self.page_num = 0
        self.occur_time = utils.ctime_str()

        self.playlist_pages = None
        self.voice_client = None
        self.voice_client_status = None
        self.voice_client_status_str = None
        self.play_pause_button_label = None
        self.play_mode = None
        self.play_mode_str = None
        self.playlist_duration = None

        self.overrode = False
        self.time_outed = False

        self.icon_filename = "questionnaire_in_reveal_animated_0ms_50px.gif"
        self.embed = discord.Embed(
            colour=discord.Color.dark_teal(),
            title=f"{self.playlist.get_name()}"
        )
        self.embed.set_author(name="播放列表", icon_url=icon.url(self.icon_filename))

        self.original_msg = None

        self.refresh_pages()

    async def init_respond(self, ephemeral: bool = False, silent: bool = False):
        files = icon_lib.files(self.icon_filename)
        original_msg = await self.ctx.respond(content=None, embed=self.embed, view=self, ephemeral=ephemeral, silent=silent, files=files)
        await self.set_original_msg(original_msg)

    async def init_eos(self, response, silent: bool = False):
        files = icon_lib.files(self.icon_filename)
        original_msg = await eos(self.ctx, response, content=None, silent=silent, embed=self.embed, view=self, files=files)
        await self.set_original_msg(original_msg)

    async def refresh_menu(self):
        self.refresh_pages()
        files = icon_lib.files(self.icon_filename)
        await eos(self.ctx, response=self.original_msg, content=None, embed=self.embed, view=self, files=files)

    async def _refresh_menu(self, interaction):
        """
        调用此方法需为view元素操作后的首次回应，使用interaction.response.edit_message
        """
        msg = interaction.response
        self.refresh_pages()

        files = icon_lib.files(self.icon_filename)
        await msg.edit_message(content=None, embed=self.embed, view=self, files=files)

    async def _deferred_refresh_menu(self, interaction):
        """
        如果互动已被defer或者回应过，那么首次回应已被占用，则使用本方法刷新
        """
        self.refresh_pages()

        files = icon_lib.files(self.icon_filename)
        await interaction.message.edit(content=None, embed=self.embed, view=self, files=files)

    def refresh_pages(self):
        # 生成播放列表主体文本
        self.playlist_pages = utils.make_playlist_page(
            self.playlist.get_list_info(),
            10,
            {None: ">       ", 0: "> ▶  **"},
            {0: "**"},
            title_markdown_bold=False,
            escape_markdown=True,
        )

        # 先启用所有可变状态的按钮，稍后根据状态禁用
        variable_states_buttons = {"button_next_audio", "button_previous_page", "button_next_page"}
        for button in self.children:
            if isinstance(button, discord.ui.Button) and button.custom_id in variable_states_buttons:
                button.disabled = False

        # 如果self.playlist_pages长度为0，则插入一个当前播放列表为空，此时长度为1
        if len(self.playlist_pages) == 0:
            self.playlist_pages.append("> **当前播放列表为空**\n")
            # 如果播放列表为空则禁用下一首按钮
            for button in self.children:
                if isinstance(button, discord.ui.Button) and button.custom_id == "button_next_audio":
                    button.disabled = True
                    break

        # 如果当前页码小于范围则跳转至第一页
        if self.page_num < 0:
            self.page_num = 0
        # 如果当前页码大于范围则跳转至最后一页
        if self.page_num > len(self.playlist_pages) - 1:
            self.page_num = len(self.playlist_pages) - 1

        # 更新播放状态文本
        self.voice_client = self.ctx.guild.voice_client
        self.voice_client_status = get_voice_client_status(self.voice_client)
        self.voice_client_status_str = get_voice_client_status_str(self.voice_client_status)

        # 更新播放状态按钮符号
        if self.voice_client_status == 1:
            self.play_pause_button_label = "▌▌"
        else:
            self.play_pause_button_label = "▶"
        for button in self.children:
            if isinstance(button, discord.ui.Button) and button.custom_id == "button_play_pause":
                button.label = self.play_pause_button_label
                break

        # 更新播放模式
        self.play_mode = self.guild.get_play_mode()

        # 更新播放模式文本
        if self.play_mode == 0:
            self.play_mode_str = "顺序播放"
        elif self.play_mode == 1:
            self.play_mode_str = "单曲循环"
        elif self.play_mode == 2:
            self.play_mode_str = "列表循环"
        elif self.play_mode == 3:
            self.play_mode_str = "随机播放"
        elif self.play_mode == 4:
            self.play_mode_str = "随机循环"
        else:
            self.play_mode_str = "播放模式"
        for button in self.children:
            if isinstance(button, discord.ui.Button) and button.custom_id == "button_play_mode":
                button.label = self.play_mode_str
                # TODO 制作播放模式切换
                button.disabled = True
                break

        for button in self.children:
            if isinstance(button, discord.ui.Button) and button.custom_id == "button_previous_audio":
                # TODO 完成历史播放列表
                button.disabled = True
                break

        # 如果在第1页则禁用上一页按钮
        if self.page_num == 0:
            for button in self.children:
                if isinstance(button, discord.ui.Button) and button.custom_id == "button_previous_page":
                    button.disabled = True
                    break

        # 如果在最后1页则禁用下一页按钮
        if self.page_num == len(self.playlist_pages) - 1:
            for button in self.children:
                if isinstance(button, discord.ui.Button) and button.custom_id == "button_next_page":
                    button.disabled = True
                    break

        self.playlist_duration = self.playlist.get_duration_str()

        embed_playlist_length_str = f"列表长度：{len(self.playlist)}"
        embed_playlist_duration_str = f"总时长：{self.playlist.get_duration_str()}"
        embed_voice_client_status_str = f"状态：{self.voice_client_status_str}"

        # 设置嵌套元素
        # 使用\u2003全角空格加宽间距
        self.embed.description = (
            f"{embed_playlist_length_str}\u2003\u2003{embed_playlist_duration_str}\u2003\u2003{embed_voice_client_status_str}\n\n"
            f"{self.playlist_pages[self.page_num]}"
        )
        self.embed.timestamp = utils.ctime_datetime()
        self.embed.set_footer(text=f"第[{self.page_num + 1}]页，共[{len(self.playlist_pages)}]页")

    @discord.ui.button(label="▍◀", style=discord.ButtonStyle.grey, custom_id="button_previous_audio", row=1)
    async def button_previous_audio_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response

        await self._refresh_menu(interaction)

    @discord.ui.button(label="▶▌▌", style=discord.ButtonStyle.grey, custom_id="button_play_pause", row=1)
    async def button_play_pause_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response

        # 由于操作时间可能过长，先defer再操作，如果服务器响应时间长可能导致菜单样式变化延迟较大，defer后的变化需交由self._deferred_refresh_menu()
        await msg.defer()

        if self.voice_client is None:
            await resume_callback(self.ctx, command_call=False)
        elif self.voice_client.is_playing():
            await pause_callback(self.ctx, command_call=False)
        elif self.voice_client.is_paused():
            await resume_callback(self.ctx, command_call=False)
        else:
            await resume_callback(self.ctx, command_call=False)

        # await self._refresh_menu(interaction)
        await self._deferred_refresh_menu(interaction)

    @discord.ui.button(label="▶ ▍", style=discord.ButtonStyle.grey, custom_id="button_next_audio", row=1)
    async def button_next_audio_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response

        # 禁用skip_callback的view刷新，防止重复刷新
        await skip_callback(self.ctx, refresh_view=False)

        await self._refresh_menu(interaction)

    @discord.ui.button(label="播放模式", style=discord.ButtonStyle.grey, custom_id="button_play_mode", row=1)
    async def button_play_mode_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response

        temp_code = self.play_mode + 1
        if temp_code > 4:
            temp_code = 0
        self.guild.set_play_mode(temp_code)

        await self._refresh_menu(interaction)

    @discord.ui.button(label="上一页", style=discord.ButtonStyle.grey, custom_id="button_previous_page", row=2)
    async def button_previous_page_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.refresh_pages()
        # 翻页
        if self.page_num <= 0:
            self.page_num = 0
        else:
            self.page_num -= 1

        await self._refresh_menu(interaction)

    @discord.ui.button(label="下一页", style=discord.ButtonStyle.grey, custom_id="button_next_page", row=2)
    async def button_next_page_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.refresh_pages()
        # 翻页
        if self.page_num >= len(self.playlist_pages) - 1:
            self.page_num = len(self.playlist_pages) - 1
        else:
            self.page_num += 1

        await self._refresh_menu(interaction)

    @discord.ui.button(label="刷新", style=discord.ButtonStyle.grey, custom_id="button_refresh", row=2)
    async def button_refresh_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        await self._refresh_menu(interaction)

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.grey, custom_id="button_close", row=2)
    async def button_close_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response

        # 将此View从guild_active_views中移除
        current_guild = guild_lib.get_guild(self.ctx)
        guild_active_views = current_guild.get_active_views()
        guild_active_views["playlist_menu_view"] = None

        self.clear_items()
        await msg.edit_message(content=f"已关闭", view=self)
        await delete_response(self.original_msg)

    async def set_original_msg(self, response: Union[discord.Message, discord.Interaction, discord.InteractionMessage, None]):
        """
        创建View后调用，传入发送该View的Interaction
        """
        self.original_msg = response

    async def on_override(self):
        """
        当新的View出现时调用，使当前View失效
        将本View从guild_active_views中移除的操作（换为新View）交由调用新View方法的地方实现
        """
        self.overrode = True
        # 覆盖程序，如果已经超时则不再执行
        if not self.time_outed:
            # 将本View从guild_active_views中移除的操作（换为新View）交由调用新View方法的地方实现
            self.refresh_pages()
            self.clear_items()

            # await self.ctx.edit(content=self.first_page, view=self)
            # await eos(self.ctx, response=self.original_msg, content="播放列表菜单已被覆盖", embed=None, view=self)
            # await self.ctx.edit(content="播放列表菜单已被覆盖", view=self)
            # await console.rp(f"{self.occur_time}生成的播放列表菜单已被覆盖", self.ctx.guild)

            await delete_response(self.original_msg)
            await console.rp(f"{self.occur_time}生成的播放列表菜单已删除", self.ctx.guild)

    async def on_timeout(self):
        self.time_outed = True
        # 超时程序，如果已被覆盖则不再执行
        if not self.overrode:
            # 将此View从guild_active_views中移除
            current_guild = guild_lib.get_guild(self.ctx)
            guild_active_views = current_guild.get_active_views()
            guild_active_views["playlist_menu_view"] = None
            self.clear_items()

            # await self.ctx.edit(content=self.first_page, view=self)
            # await eos(self.ctx, response=self.original_msg, content="播放列表菜单已超时", view=self)
            # await self.ctx.edit(content="播放列表菜单已超时", view=self)

            await delete_response(self.original_msg)
            await console.rp(f"{self.occur_time}生成的播放列表菜单已超时(超时时间为{self.timeout}秒)", self.ctx.guild)


class EpisodeSelectMenu(View):

    def __init__(self, ctx, source, info_dict, menu_list, list_type=None, list_title=None, timeout=60):
        """
        初始化分集选择菜单

        :param ctx: 指令原句
        :param source: 播放源的种类（bilibili_p, bilibili_collection, youtube_playlist, netease_playlist)
        :param info_dict: 播放源的信息字典
        :param menu_list: 选择菜单的文本（使用make_playlist_page获取）
        :param timeout: 超时时间（单位：秒）
        :param list_type: 播放列表的类型（展示用）
        :param list_title: 播放列表的标题（展示用）
        :return:
        """
        super().__init__(timeout=timeout)
        self.ctx: discord.ApplicationContext = ctx

        if list_type is not None:
            self.list_type = list_type
        else:
            self.list_type = "播放列表"

        self.list_title = list_title
        self.source = source
        self.info_dict = info_dict
        self.menu_list = menu_list
        self.page_num = 0
        self.result = []
        self.dash_finish = True
        self.occur_time = utils.ctime_str()
        self.voice_client = self.ctx.guild.voice_client
        self.current_playlist = guild_lib.get_guild(self.ctx).get_playlist()

        self.original_msg = None
        self.embed = None
        self.icon_filename = None

        # 标记是否已经操作完选择页面
        self.finish = False

        # 封面设置
        self.cover_path = None
        self.cover_url = None

        if self.source == "bilibili_p" and "pic" in info_dict:
            self.cover_url = info_dict["pic"]
        elif self.source == "bilibili_collection" and "pic" in info_dict:
            self.cover_url = info_dict["pic"]
        elif self.source == "youtube_playlist" and "thumbnails" in info_dict and len(info_dict["thumbnails"]) > 0:
            for thumbnail in reversed(info_dict["thumbnails"]):
                if "url" in thumbnail:
                    self.cover_url = thumbnail["url"]
                    break

        self.refresh_pages()

    async def init_respond(self, ephemeral: bool = False, silent: bool = False):
        original_msg = await self.ctx.respond(content=None, embed=self.embed, view=self, ephemeral=ephemeral, silent=silent)
        await self.set_original_msg(original_msg)

    async def init_eos(self, response, silent: bool = False):
        original_msg = await eos(self.ctx, response, content=None, silent=silent, embed=self.embed, view=self)
        await self.set_original_msg(original_msg)

    async def refresh_menu(self):
        self.refresh_pages()
        await eos(self.ctx, response=self.original_msg, content=None, embed=self.embed, view=self)

    def refresh_pages(self):
        if not self.finish:
            # 先启用所有可变状态的按钮，稍后根据状态禁用
            variable_states_buttons = {"button_previous_page", "button_next_page"}
            for button in self.children:
                if isinstance(button, discord.ui.Button) and button.custom_id in variable_states_buttons:
                    button.disabled = False

            # 如果当前页码小于范围则跳转至第一页
            if self.page_num < 0:
                self.page_num = 0
            # 如果当前页码大于范围则跳转至最后一页
            if self.page_num > len(self.menu_list) - 1:
                self.page_num = len(self.menu_list) - 1

            # 如果在第1页则禁用上一页按钮
            if self.page_num == 0:
                for button in self.children:
                    if isinstance(button, discord.ui.Button) and button.custom_id == "button_previous_page":
                        button.disabled = True
                        break

            # 如果在最后1页则禁用下一页按钮
            if self.page_num == len(self.menu_list) - 1:
                for button in self.children:
                    if isinstance(button, discord.ui.Button) and button.custom_id == "button_next_page":
                        button.disabled = True
                        break

            embed_title = ""
            if self.list_title is not None:
                embed_title = f"{self.list_title}"
            self.embed = discord.Embed(
                colour=discord.Color.dark_teal(),
                title=embed_title,
                description=f"请选择要播放的集数:\n{self.menu_list[self.page_num]}",
                timestamp=utils.ctime_datetime(),
            )
            num = ""
            for i in self.result:
                num += i
            self.embed.add_field(name="", value=f"已输入：{num}")
            self.embed.set_author(name=f"{self.list_type}")
            self.embed.set_footer(text=f"第[{self.page_num + 1}]页，共[{len(self.menu_list)}]页")
            if self.cover_url is not None:
                self.embed.set_thumbnail(url=self.cover_url)

    async def set_original_msg(self, response: Union[discord.Message, discord.InteractionMessage, None]):
        """
        创建View后调用，传入发送该View的Interaction
        """
        self.original_msg = response

    @discord.ui.button(label="1", style=discord.ButtonStyle.grey, custom_id="button_1", row=0)
    async def button_1_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("1")

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="2", style=discord.ButtonStyle.grey, custom_id="button_2", row=0)
    async def button_2_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("2")

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="3", style=discord.ButtonStyle.grey, custom_id="button_3", row=0)
    async def button_3_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("3")

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="退格", style=discord.ButtonStyle.grey, custom_id="button_backspace", row=0)
    async def button_backspace_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        if len(self.result) <= 0:
            pass
        else:
            self.result.pop()

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="清空", style=discord.ButtonStyle.grey, custom_id="button_clear", row=0)
    async def button_clear_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result = []

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="4", style=discord.ButtonStyle.grey, custom_id="button_4", row=1)
    async def button_4_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("4")

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="5", style=discord.ButtonStyle.grey, custom_id="button_5", row=1)
    async def button_5_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("5")

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="6", style=discord.ButtonStyle.grey, custom_id="button_6", row=1)
    async def button_6_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("6")

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="全部", style=discord.ButtonStyle.grey, custom_id="button_all", row=1)
    async def button_all_callback(self, button, interaction):
        button.disabled = False
        self.finish = True
        msg = interaction.response

        total_num = 0
        final_result = []
        if self.source == "bilibili_p":
            total_num = len(self.info_dict["pages"])
        elif self.source == "bilibili_collection":
            total_num = len(
                self.info_dict["ugc_season"]["sections"][0]["episodes"])
        elif self.source == "youtube_playlist" or self.source == "netease_playlist":
            total_num = len(self.info_dict["entries"])

        for num in range(1, total_num + 1):
            final_result.append(num)

        self.clear_items()
        self.embed.description = f"已选择全部[{total_num}]首"
        self.embed.timestamp = utils.ctime_datetime()
        await msg.edit_message(content=None, embed=self.embed, view=self)
        await self.play_select(final_result)

    @discord.ui.button(label="随机", style=discord.ButtonStyle.grey, custom_id="button_random", row=1)
    async def button_random_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response

        max_num = 1
        if self.source == "bilibili_p":
            max_num = len(self.info_dict["pages"])
        elif self.source == "bilibili_collection":
            max_num = len(self.info_dict["ugc_season"]["sections"][0]["episodes"])
        elif self.source == "youtube_playlist":
            max_num = len(self.info_dict["entries"])
        elif self.source == "netease_playlist":
            max_num = len(self.info_dict["entries"])
        if max_num < 1: max_num = 1
        self.result = [str(random.randint(1, max_num))]

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="7", style=discord.ButtonStyle.grey, custom_id="button_7", row=2)
    async def button_7_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("7")

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="8", style=discord.ButtonStyle.grey, custom_id="button_8", row=2)
    async def button_8_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("8")

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="9", style=discord.ButtonStyle.grey, custom_id="button_9", row=2)
    async def button_9_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("9")

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="取消", style=discord.ButtonStyle.red, custom_id="button_cancel", row=2)
    async def button_cancel_callback(self, button, interaction):
        button.disabled = True
        self.finish = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已取消", view=self)
        await delete_response(self.original_msg)
        await console.rp("用户已取消选择界面", self.ctx.guild)

    @discord.ui.button(label="上一页", style=discord.ButtonStyle.grey, custom_id="button_previous_page", row=2)
    async def button_previous_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        # 翻页
        if self.page_num == 0:
            return
        else:
            self.page_num -= 1

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="-", style=discord.ButtonStyle.grey, custom_id="button_dash", row=3)
    async def button_dash_callback(self, button, interaction):
        msg = interaction.response
        button.disabled = False

        if len(self.result) == 0 or not self.result[len(self.result) - 1].isdigit() or not self.dash_finish:
            await msg.edit_message(content=None, embed=self.embed, view=self)
            return

        self.result.append("-")
        self.dash_finish = False

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="0", style=discord.ButtonStyle.grey, custom_id="button_0", row=3)
    async def button_0_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("0")

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label=",", style=discord.ButtonStyle.grey, custom_id="button_comma", row=3)
    async def button_comma_callback(self, button, interaction):
        msg = interaction.response
        button.disabled = False

        if len(self.result) == 0 or not self.result[len(self.result) - 1].isdigit():
            await msg.edit_message(content=None, embed=self.embed, view=self)
            return

        self.result.append(",")
        self.dash_finish = True

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="确定", style=discord.ButtonStyle.green, custom_id="button_confirm", row=3)
    async def button_confirm_callback(self, button, interaction):
        msg = interaction.response

        message = "已选择：第 "
        button.disabled = False
        self.refresh_pages()

        if len(self.result) == 0 or self.result[len(self.result) - 1] == "-":
            return

        num = ""
        final_result = []
        temp = []
        for item in self.result:
            if item == "-":
                temp.append(int(num))
                temp.append("-")
                num = ""
            elif item == ",":
                if not len(temp) == 0 and temp[len(temp) - 1] == "-":
                    temp.pop()
                    start_1 = temp.pop()
                    if int(num) < start_1:
                        start_num = int(num)
                        for i in range(start_1, int(num) - 1, -1):
                            if i == 0:
                                start_num = 1
                            else:
                                final_result.append(i)
                        message += f"{start_num} - {start_1}（倒序），"
                    else:
                        start_num = start_1
                        for i in range(start_1, int(num) + 1):
                            if i == 0:
                                start_num = 1
                            else:
                                final_result.append(i)
                        message += f"{start_num} - {int(num)}，"
                    num = ""
                else:
                    if int(num) == 0:
                        pass
                    else:
                        final_result.append(int(num))
                        message += f"{int(num)}，"
                    num = ""
            else:
                num = num + item
        if num == "":
            pass
        elif not len(temp) == 0 and temp[len(temp) - 1] == "-":
            temp.pop()
            start_1 = temp.pop()
            if int(num) < start_1:
                start_num = int(num)
                for i in range(start_1, int(num) - 1, -1):
                    if i == 0:
                        start_num = 1
                    else:
                        final_result.append(i)
                message += f"{start_num} - {start_1}（倒序），"
            else:
                start_num = start_1
                for i in range(start_1, int(num) + 1):
                    if i == 0:
                        start_num = 1
                    else:
                        final_result.append(i)
                message += f"{start_num} - {int(num)}，"
        else:
            if int(num) == 0:
                pass
            else:
                final_result.append(int(num))
                message += f"{int(num)}，"

        if self.source == "bilibili_p":
            for num in final_result:
                if num > len(self.info_dict["pages"]):
                    self.embed.add_field(name="", value="选择中含有无效分p号", inline=False)
                    await msg.edit_message(content=None, embed=self.embed, view=self)
                    return
        elif self.source == "bilibili_collection":
            for num in final_result:
                if num > len(self.info_dict["ugc_season"]["sections"][0]["episodes"]):
                    self.embed.add_field(name="", value="选择中含有无效集数", inline=False)
                    await msg.edit_message(content=None, embed=self.embed, view=self)
                    return
        elif self.source == "youtube_playlist":
            for num in final_result:
                if num > len(self.info_dict["entries"]):
                    self.embed.add_field(name="", value="选择中含有无效集数", inline=False)
                    await msg.edit_message(content=None, embed=self.embed, view=self)
                    return
        elif self.source == "netease_playlist":
            for num in final_result:
                if num > len(self.info_dict["entries"]):
                    self.embed.add_field(name="", value="选择中含有无效序号", inline=False)
                    await msg.edit_message(content=None, embed=self.embed, view=self)
                    return

        message = message[:-1] + " 首"
        self.finish = True
        self.clear_items()
        self.embed.description = message
        # 删除“已输入：”的输入框
        if len(self.embed.fields) > 0:
            self.embed.remove_field(0)
        self.embed.timestamp = utils.ctime_datetime()
        await msg.edit_message(content=None, embed=self.embed, view=self)

        await self.play_select(final_result)

    @discord.ui.button(label="下一页", style=discord.ButtonStyle.grey, custom_id="button_next_page", row=3)
    async def button_next_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        # 翻页
        if self.page_num == len(self.menu_list) - 1:
            return
        else:
            self.page_num += 1

        self.refresh_pages()
        await msg.edit_message(content=None, embed=self.embed, view=self)

    async def play_select(self, final_result, maximum_retry: int = 4):
        voice_client = self.ctx.guild.voice_client
        current_guild = guild_lib.get_guild(self.ctx)
        current_playlist = current_guild.get_playlist()

        icon_loading_filename = "hourglass_hover_rotation_animated_0ms_30px.gif"
        icon_finish_filename = "check_in_box_in_reveal_animated_0ms_100px.gif"
        icon_failed_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"

        total_num = len(final_result)
        success_num = 0
        total_duration = 0

        # ----- 下载并播放音频 -----
        self.icon_filename = icon_loading_filename
        self.embed.set_author(name=f"{self.list_type}：正在添加", icon_url=icon.url(self.icon_filename))
        embed_append_description(self.embed, f"正在将 {total_num} 个音频添加入播放列表：")
        await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

        # 如果为Bilibili分p音频
        if self.source == "bilibili_p":
            counter = 1
            for item in self.info_dict["pages"]:
                if counter in final_result:
                    total_duration += item["duration"]
                counter += 1
            total_duration = utils.convert_duration_to_str(total_duration)
            self.embed.set_footer(text=f"总时长 -> [{total_duration}]")
            await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

            for num_p in final_result:
                new_result = await download_bilibili_audio(self.ctx, self.info_dict, "bilibili_p", num_p - 1)
                new_audio = new_result["audio"]

                # 如果音频加载成功
                if new_audio is not None:

                    # 如果当前播放列表为空
                    if current_playlist.is_empty() and not voice_client.is_playing():
                        await play_audio(self.ctx, new_audio, response=self.original_msg)

                    current_playlist.append_audio(new_audio)
                    await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", self.ctx.guild)

                    await current_guild.refresh_list_view()

                    embed_append_description(self.embed, f"> [{num_p}] **{new_audio.get_title()}** [{new_audio.get_duration_str()}]")
                    await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))
                    success_num += 1

                else:
                    if isinstance(new_result["exception"], errors.StorageFull):
                        embed_append_description(self.embed, f"**机器人当前处理音频过多，请稍后再试**")
                        await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))
                        return
                    # 如果错误类型可以重试
                    elif new_result["retryable"]:
                        # 如果不重试则直接发送错误与稍后再试
                        if maximum_retry < 1:
                            embed_append_description(self.embed, f"**错误：[{num_p}] 获取失败** " + new_result["message"] + "，请稍后再试")
                            await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

                        # 如果重试
                        else:
                            retry_counter = 0
                            while retry_counter < maximum_retry:
                                retry_counter += 1

                                embed_replace_description_last_line(self.embed, f"**错误：[{num_p}] 获取失败** " + new_result["message"] + f"：第 {retry_counter} 次重试中")
                                await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

                                new_result = await download_bilibili_audio(self.ctx, self.info_dict, "bilibili_p", num_p - 1)
                                new_audio = new_result["audio"]

                                # 如果音频加载成功
                                if new_audio is not None:

                                    # 如果当前播放列表为空
                                    if current_playlist.is_empty() and not voice_client.is_playing():
                                        await play_audio(self.ctx, new_audio, response=self.original_msg)

                                    current_playlist.append_audio(new_audio)
                                    await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", self.ctx.guild)

                                    await current_guild.refresh_list_view()

                                    embed_replace_description_last_line(self.embed, f"> [{num_p}] **{new_audio.get_title()}** [{new_audio.get_duration_str()}]")
                                    await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))
                                    success_num += 1
                                    break

                            # 如果重试最终没有成功
                            if new_audio is None:
                                embed_replace_description_last_line(self.embed, f"**错误：[{num_p}] 获取失败** " + new_result["message"] + "，请稍后再试")
                                await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

                    else:
                        embed_append_description(self.embed, f"**错误：[{num_p}] 获取失败** " + new_result["message"])
                        await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

        # 如果为Bilibili合集音频
        elif self.source == "bilibili_collection":
            counter = 1
            for item in self.info_dict["ugc_season"]["sections"][0]["episodes"]:
                if counter in final_result:
                    total_duration += item["arc"]["duration"]
                counter += 1
            total_duration = utils.convert_duration_to_str(total_duration)
            self.embed.set_footer(text=f"总时长 -> [{total_duration}]")
            await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

            for num in final_result:
                title = self.info_dict["ugc_season"]["sections"][0]["episodes"][num - 1]["title"]
                new_result = await download_bilibili_audio(self.ctx, self.info_dict, "bilibili_collection", num_option=num - 1)
                new_audio = new_result["audio"]

                # 如果音频加载成功
                if new_audio is not None:

                    # 如果当前播放列表为空
                    if current_playlist.is_empty() and not voice_client.is_playing():
                        await play_audio(self.ctx, new_audio, response=self.original_msg)

                    current_playlist.append_audio(new_audio)
                    await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", self.ctx.guild)

                    await current_guild.refresh_list_view()

                    embed_append_description(self.embed, f"> [{num}] **{new_audio.get_title()}** [{new_audio.get_duration_str()}]")
                    await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))
                    success_num += 1

                else:
                    if isinstance(new_result["exception"], errors.StorageFull):
                        embed_append_description(self.embed, f"**机器人当前处理音频过多，请稍后再试**")
                        await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))
                        return
                    # 如果错误类型可以重试
                    elif new_result["retryable"]:
                        # 如果不重试直接发送错误与稍后再试
                        if maximum_retry < 1:
                            embed_append_description(self.embed, f"**错误：[{num}] {title} 获取失败** " + new_result["message"] + "，请稍后再试")
                            await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

                        # 如果重试
                        else:
                            retry_counter = 0
                            while retry_counter < maximum_retry:
                                retry_counter += 1

                                embed_replace_description_last_line(self.embed, f"**错误：[{num}] {title} 获取失败** " + new_result["message"] + f"：第 {retry_counter} 次重试中")
                                await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

                                new_result = await download_bilibili_audio(self.ctx, self.info_dict, "bilibili_collection", num_option=num - 1)
                                new_audio = new_result["audio"]

                                # 如果音频加载成功
                                if new_audio is not None:

                                    # 如果当前播放列表为空
                                    if current_playlist.is_empty() and not voice_client.is_playing():
                                        await play_audio(self.ctx, new_audio, response=self.original_msg)

                                    current_playlist.append_audio(new_audio)
                                    await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", self.ctx.guild)

                                    await current_guild.refresh_list_view()

                                    embed_replace_description_last_line(self.embed, f"> [{num}] **{new_audio.get_title()}** [{new_audio.get_duration_str()}]")
                                    await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))
                                    success_num += 1
                                    break

                            # 如果最终最终没有成功
                            if new_audio is None:
                                embed_replace_description_last_line(self.embed, f"**错误：[{num}] {title} 获取失败** " + new_result["message"] + "，请稍后再试")
                                await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

                    else:
                        embed_append_description(self.embed, f"**错误：[{num}] {title} 获取失败** " + new_result["message"])
                        await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))


        # 如果为YT-DLP类型播放列表（YouTube，网易云）
        elif self.source == "youtube_playlist" or self.source == "netease_playlist":
            if self.source == "youtube_playlist":
                ytdlp_link_type = "youtube_single"

                # 总时长显示
                # 仅限YouTube，yt-dlp下载的网易云播放列表不提供单曲时长信息
                counter = 1
                valid_counter = 0
                for item in self.info_dict["entries"]:
                    # item["duration"] is not None 检测如果列表中含有已被删除的视频
                    if counter in final_result and item["duration"] is not None:
                        total_duration += item["duration"]
                        valid_counter += 1
                    counter += 1
                total_duration = utils.convert_duration_to_str(total_duration)
                self.embed.set_footer(text=f"总时长 -> [{total_duration}]")
                await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

            elif self.source == "netease_playlist":
                ytdlp_link_type = "netease_single"

            else:
                return

            # 循环添加
            for num in final_result:
                title = self.info_dict['entries'][num - 1]['title']

                if self.source == "youtube_playlist":
                    # 跳过已被删除或失效的视频
                    if self.info_dict['entries'][num - 1]['duration'] is None:
                        continue
                    url = f"https://www.youtube.com/watch?v={self.info_dict['entries'][num - 1]['id']}"
                elif self.source == "netease_playlist":
                    url = self.info_dict['entries'][num - 1]['url']
                else:
                    return

                # 单独提取信息
                current_info_result = await get_ytdlp_info(self.ctx, url)
                current_info_dict = current_info_result["info_dict"]
                if current_info_dict is None:
                    warning_description = f"[{url}] 信息获取失败：{current_info_result['message']}"
                    if current_info_result["retryable"]:
                        warning_description += "，请稍后再试"
                    embed_append_description(self.embed, warning_description)
                    await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))
                    continue

                # 每个音频单独添加
                new_result = await download_ytdlp_audio(self.ctx, url, current_info_dict, ytdlp_link_type)
                new_audio = new_result["audio"]

                if new_audio is not None:
                    if current_playlist.is_empty() and not voice_client.is_playing():
                        await play_audio(self.ctx, new_audio, response=self.original_msg)

                    # 添加至服务器播放列表
                    current_playlist.append_audio(new_audio)
                    await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", self.ctx.guild)

                    await current_guild.refresh_list_view()

                    embed_append_description(self.embed, f"> [{num}] **{new_audio.get_title()}** [{new_audio.get_duration_str()}]")
                    await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))
                    success_num += 1

                else:
                    if isinstance(new_result["exception"], errors.StorageFull):
                        embed_append_description(self.embed, f"**机器人当前处理音频过多，无法完成播放列表添加**")
                        await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))
                        return
                    elif new_result["retryable"]:
                        # 如果不重试直接发送错误与稍后再试
                        if maximum_retry < 1:
                            embed_append_description(self.embed, f"**错误：[{num}] {title} 获取失败** " + new_result["message"] + "，请稍后再试")
                            await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))
                        # 如果重试
                        else:
                            retry_counter = 0
                            while retry_counter < maximum_retry:
                                retry_counter += 1

                                embed_replace_description_last_line(self.embed, f"**错误：[{num}] {title} 获取失败** " + new_result["message"] + f"：第 {retry_counter} 次重试中")
                                await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

                                new_result = await download_ytdlp_audio(self.ctx, url, current_info_dict, ytdlp_link_type)
                                new_audio = new_result["audio"]

                                # 如果音频加载成功
                                if new_audio is not None:

                                    # 如果当前播放列表为空
                                    if current_playlist.is_empty() and not voice_client.is_playing():
                                        await play_audio(self.ctx, new_audio, response=self.original_msg)

                                    current_playlist.append_audio(new_audio)
                                    await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", self.ctx.guild)

                                    await current_guild.refresh_list_view()
                                    embed_replace_description_last_line(self.embed, f"> [{num}] **{new_audio.get_title()}** [{new_audio.get_duration_str()}]")
                                    await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))
                                    success_num += 1
                                    break

                            # 如果重试最终没有成功
                            if new_audio is None:
                                embed_replace_description_last_line(self.embed, f"**错误：[{num}] {title} 获取失败** " + new_result["message"] + "，请稍后再试")
                                await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

                    else:
                        embed_append_description(self.embed, f"**错误：[{num}] {title} 获取失败** " + new_result["message"])
                        await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

        # 如果为网易云播放列表
        # elif self.source == "netease_playlist":
        #     # yt-dlp下载的网易云播放列表并不包含单曲时长信息
        #     # counter = 1
        #     # valid_counter = 0
        #     # for item in self.info_dict["entries"]:
        #     #     # item["duration"] is not None 检测如果列表中含有已被删除的视频
        #     #     if counter in final_result and item["duration"] is not None:
        #     #         total_duration += item["duration"]
        #     #         valid_counter += 1
        #     #     counter += 1
        #
        #     # total_duration = utils.convert_duration_to_str(total_duration)
        #
        #     # 循环添加
        #     for num in final_result:
        #         # 跳过已被删除或失效的视频
        #         # if self.info_dict['entries'][num - 1]['duration'] is not None:
        #         url = self.info_dict['entries'][num - 1]['url']
        #         title = self.info_dict['entries'][num - 1]['title']
        #         # 单独提取信息
        #         current_info_dict = ytdlp.get_info(url)
        #         # 每个音频作为“netease_single”单独添加
        #         new_audio = await download_ytdlp_audio(self.ctx, url, current_info_dict, "netease_single", list_add_call=True, response=None)
        #         # 如果音频加载成功
        #         if new_audio is not None:
        #             embed_append_description(self.embed, f"> [{num}] **{new_audio.get_title()}** [{new_audio.get_duration_str()}]")
        #             await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self)

        else:
            await console.rp("未知的播放源", self.ctx.guild)

        # 去掉最开始的 已选择和正在加入 的两行
        if self.embed.description:
            lines = self.embed.description.splitlines()
            if len(lines) >= 2:
                self.embed.description = "\n".join(lines[2:])
            else:
                self.embed.description = None

        if success_num == 0:
            self.icon_filename = icon_failed_filename
            self.embed.set_author(name=f"{self.list_type}：添加失败", icon_url=icon.url(self.icon_filename))
            self.embed.add_field(name="", value="添加失败", inline=False)
            self.embed.timestamp = utils.ctime_datetime()
            await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))
        else:
            self.icon_filename = icon_finish_filename
            self.embed.set_author(name=f"{self.list_type}：添加完成", icon_url=icon.url(self.icon_filename))
            self.embed.add_field(name="", value=f"添加完成：已将 {success_num} 个音频加入播放列表", inline=False)
            self.embed.timestamp = utils.ctime_datetime()
            await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

    async def on_timeout(self):
        self.clear_items()
        if self.finish:
            await self.original_msg.edit(embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))
        else:
            await delete_response(self.original_msg)
        await console.rp(f"{self.occur_time}生成的搜索选择菜单已超时(超时时间为{self.timeout}秒)", self.ctx.guild)


class CheckCollectionMenu(View):

    def __init__(self, ctx, source, info_dict, response: Union[discord.Interaction, discord.InteractionMessage, None] = None, timeout=10):
        """
        提示是否查看合集或播放列表的View
        source:
            - bilibili_collection
            - youtube_playlist
        """
        super().__init__(timeout=timeout)
        self.ctx: discord.ApplicationContext = ctx
        self.source = source
        self.response = response
        self.info_dict = info_dict
        self.occur_time = utils.ctime_str()
        self.finish = False
        self.original_msg = None

        if self.source == "bilibili_collection":
            collection_title = self.info_dict["ugc_season"]["title"]
            message = f"**{utils.markdown_escape(self.info_dict['title'])}** 包含在合集 **{utils.markdown_escape(collection_title)}** 中, 是否要查看此合集？\n"
            title = "发现合集"
        elif self.source == "youtube_playlist":
            playlist_title = self.info_dict['title']
            message = f"**{utils.markdown_escape(info_dict['title'])}** 包含在播放列表 **{utils.markdown_escape(playlist_title)}** 中, 是否要查看此播放列表？\n"
            title = "发现播放列表"
        else:
            message = f"合集信息错误"
            title = f"合集信息错误"

        self.icon_filename = "question_hover_wiggle_animated_1500ms_infinite_100px.gif"
        self.embed = discord.Embed(
            colour=discord.Colour.dark_green(),
            description=message,
        )
        self.embed.set_author(name=title, icon_url=icon.url(self.icon_filename))

    async def init_respond(self, ephemeral: bool = False, silent: bool = False):
        files = icon_lib.files(self.icon_filename)
        original_msg = await self.ctx.respond(content=None, embed=self.embed, view=self, ephemeral=ephemeral, silent=silent, files=files)
        await self.set_original_msg(original_msg)

    async def init_eos(self, response, silent: bool = False):
        files = icon_lib.files(self.icon_filename)
        original_msg = await eos(self.ctx, response, content=None, silent=silent, embed=self.embed, view=self, files=files)
        await self.set_original_msg(original_msg)

    @discord.ui.button(label="确定", style=discord.ButtonStyle.grey, custom_id="button_confirm")
    async def button_confirm_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.finish = True

        self.clear_items()

        if self.source == "bilibili_collection":
            ep_info_list = []
            for item in self.info_dict["ugc_season"]["sections"][0]["episodes"]:
                ep_title = item["title"]
                ep_time_str = utils.convert_duration_to_str(item["arc"]["duration"])
                ep_info_list.append((ep_title, ep_time_str))

            collection_title = self.info_dict["ugc_season"]["title"]
            menu_list = utils.make_playlist_page(ep_info_list, 10, {None: "> "}, {}, escape_markdown=True)
            menu = EpisodeSelectMenu(self.ctx, "bilibili_collection", self.info_dict, menu_list, "哔哩哔哩合集", collection_title)
            await menu.init_eos(response=msg, silent=True)

        elif self.source == "youtube_playlist":
            ep_info_list = []
            for item in self.info_dict["entries"]:
                ep_title = item["title"]
                ep_time_str = utils.convert_duration_to_str(item["duration"])
                ep_info_list.append((ep_title, ep_time_str))
            playlist_title = self.info_dict['title']
            menu_list = utils.make_playlist_page(ep_info_list, 10, {None: "> "}, {}, escape_markdown=True)
            menu = EpisodeSelectMenu(self.ctx, "youtube_playlist", self.info_dict, menu_list, "YouTube播放列表", playlist_title)
            await menu.init_eos(response=msg, silent=True)

        await delete_response(self.original_msg)

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.grey, custom_id="button_cancel")
    async def button_close_callback(self, button, interaction):
        button.disabled = False
        self.finish = True
        self.clear_items()
        if self.original_msg is not None:
            await delete_response(self.original_msg)

    async def set_original_msg(self, response: Union[discord.Message, discord.InteractionMessage, None]):
        """
        创建View后调用，传入发送该View的Interaction
        """
        self.original_msg = response

    async def on_timeout(self):
        if not self.finish and self.original_msg is not None:
            await delete_response(self.original_msg)
        await console.rp(f"{self.occur_time}生成的合集查看选择栏已超时(超时时间为{self.timeout}秒)", self.ctx.guild)


class SearchedAudioSelectionMenu(View):
    def __init__(self, ctx, query: str, title_str: str, address_str: str, resource_list: List[dict], response: Union[discord.Interaction, discord.InteractionMessage, None] = None, timeout=60):
        """
        选择是否播放或者显示搜索到的音频的地址的View
        """
        super().__init__(timeout=timeout)
        self.ctx: discord.ApplicationContext = ctx
        self.response = response
        self.occur_time = utils.ctime_str()
        self.finish = False

        self.show_address = False
        self.query = query
        self.title_str = title_str
        self.address_str = address_str
        self.resource_list = resource_list
        self.original_msg = None

        for i in range(10, len(self.resource_list), -1):
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.custom_id == f"button_{i}":
                    item.disabled = True
                    break

        self.icon_filename = "zoom_in_reveal_animated_0ms_100px.gif"
        self.embed = discord.Embed(
            colour=discord.Colour.dark_teal(),
            description=title_str,
            timestamp=utils.ctime_datetime()
        )
        self.embed.set_author(name=f"搜索：{self.query}", icon_url=icon.url(self.icon_filename))

    async def init_respond(self, ephemeral: bool = False, silent: bool = False):
        files = icon_lib.files(self.icon_filename)
        original_msg = await self.ctx.respond(content=None, embed=self.embed, view=self, ephemeral=ephemeral, silent=silent, files=files)
        await self.set_original_msg(original_msg)

    async def init_eos(self, response, silent: bool = False):
        files = icon_lib.files(self.icon_filename)
        original_msg = await eos(self.ctx, response, content=None, silent=silent, embed=self.embed, view=self, files=files)
        await self.set_original_msg(original_msg)

    async def play(self, index: int, msg):
        selected_item = self.resource_list[index]
        link = selected_item["id"]
        self.finish = True
        self.clear_items()

        # self.embed.description = f"已选择：**{selected_item['title']} [{selected_item['duration_str']}]**"
        # await msg.edit_message(content=None, embed=self.embed, view=self)
        # loading_msg = await self.ctx.send("正在准备播放", silent=True)

        await play_callback(self.ctx, link, response=self.original_msg)

    @discord.ui.button(label="1", style=discord.ButtonStyle.grey, custom_id="button_1", row=1)
    async def button_1_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        await self.play(0, msg)

    @discord.ui.button(label="2", style=discord.ButtonStyle.grey, custom_id="button_2", row=1)
    async def button_2_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        await self.play(1, msg)

    @discord.ui.button(label="3", style=discord.ButtonStyle.grey, custom_id="button_3", row=1)
    async def button_3_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        await self.play(2, msg)

    @discord.ui.button(label="4", style=discord.ButtonStyle.grey, custom_id="button_4", row=1)
    async def button_4_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        await self.play(3, msg)

    @discord.ui.button(label="5", style=discord.ButtonStyle.grey, custom_id="button_5", row=1)
    async def button_5_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        await self.play(4, msg)

    @discord.ui.button(label="6", style=discord.ButtonStyle.grey, custom_id="button_6", row=2)
    async def button_6_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        await self.play(5, msg)

    @discord.ui.button(label="7", style=discord.ButtonStyle.grey, custom_id="button_7", row=2)
    async def button_7_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        await self.play(6, msg)

    @discord.ui.button(label="8", style=discord.ButtonStyle.grey, custom_id="button_8", row=2)
    async def button_8_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        await self.play(7, msg)

    @discord.ui.button(label="9", style=discord.ButtonStyle.grey, custom_id="button_9", row=2)
    async def button_9_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        await self.play(8, msg)

    @discord.ui.button(label="10", style=discord.ButtonStyle.grey, custom_id="button_10", row=2)
    async def button_10_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        await self.play(9, msg)

    @discord.ui.button(label="显示网址", style=discord.ButtonStyle.green, custom_id="button_switch", row=3)
    async def button_switch_callback(self, button, interaction):
        msg = interaction.response

        files = icon_lib.files(self.icon_filename)
        if self.show_address:
            self.show_address = False
            button.label = "显示网址"
            self.embed.description = self.title_str
            await msg.edit_message(content=None, embed=self.embed, view=self, files=files)
        else:
            self.show_address = True
            button.label = "隐藏网址"
            self.embed.description = self.address_str
            await msg.edit_message(content=None, embed=self.embed, view=self, files=files)

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.red, custom_id="button_cancel", row=3)
    async def button_cancel_callback(self, button, interaction):
        button.disabled = True
        self.finish = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已关闭搜索结果选择菜单", view=self)
        await console.rp("用户已关闭搜索选择菜单", self.ctx.guild)

    async def set_original_msg(self, response: Union[discord.Message, discord.InteractionMessage, None]):
        """
        创建View后调用，传入发送该View的Interaction
        """
        self.original_msg = response

    async def on_timeout(self):
        self.clear_items()
        if not self.finish:
            await delete_response(self.original_msg)
        await console.rp(f"{self.occur_time}生成的搜索选择菜单已超时(超时时间为{self.timeout}秒)", self.ctx.guild)


class AskForSearchingMenu(View):
    def __init__(self, ctx, query, response: Union[discord.Interaction, discord.InteractionMessage, None] = None,
                 timeout=30):
        """
        询问是否搜索指定<query>的View
        """
        super().__init__(timeout=timeout)
        self.ctx: discord.ApplicationContext = ctx
        self.response = response
        self.occur_time = utils.ctime_str()
        self.finish = False
        self.original_msg = None
        self.query = query

        self.embed = discord.Embed(
            colour=discord.Colour.dark_teal(),
            description=f"**{utils.markdown_escape(query)}** 获取失败，是否要重新进行搜索？",
            timestamp=utils.ctime_datetime()
        )

    async def init_respond(self, ephemeral: bool = False, silent: bool = False):
        original_msg = await self.ctx.respond(content=None, embed=self.embed, view=self, ephemeral=ephemeral, silent=silent)
        await self.set_original_msg(original_msg)

    async def init_eos(self, response, silent: bool = False):
        original_msg = await eos(self.ctx, response, content=None, silent=silent, embed=self.embed, view=self)
        await self.set_original_msg(original_msg)

    @discord.ui.button(label="确定", style=discord.ButtonStyle.grey, custom_id="button_confirm")
    async def button_confirm_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.finish = True
        self.clear_items()
        await msg.edit_message(view=self)
        await search_audio_callback(self.ctx, self.query, response=self.original_msg, query_num=5)

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.grey, custom_id="button_cancel")
    async def button_close_callback(self, button, interaction):
        button.disabled = False
        self.finish = True
        self.clear_items()
        if self.original_msg is not None:
            await delete_response(self.original_msg)

    async def set_original_msg(self, response: Union[discord.Message, discord.InteractionMessage, None]):
        """
        创建View后调用，传入发送该View的Interaction
        """
        self.original_msg = response

    async def on_timeout(self):
        self.clear_items()
        if not self.finish and self.original_msg is not None:
            await delete_response(self.original_msg)
        await console.rp(f"{self.occur_time}生成的询问搜索选择栏已超时(超时时间为{self.timeout}秒)", self.ctx.guild)
