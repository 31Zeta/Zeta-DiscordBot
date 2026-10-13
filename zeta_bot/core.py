from typing import *
import sys
import os
import re
import time
import shutil
import asyncio
import collections
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
from utils import Result, success_result, failed_result

# 底层模块
from zeta_bot import (
    language,
    setting,
    output_console,
    icon,
)
from zeta_bot.resource import MediaPlatform, LinkType, DownloadHandler, DownloadType, ResourceClassifier

startup_time = utils.ctime_str()

version = "0.15.1"
author = "炤融 (31Zeta)"
python_path = sys.executable
pycord_version = discord.__version__
bilibili_api_version = BILIBILI_API_VERSION
yt_dlp_version = yt_dlp_version.__version__
update_time = "2026.09.14"

supported_search_sites = ["哔哩哔哩", "YouTube", "网易云音乐", "QQ音乐"]

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
os.makedirs("./configs", exist_ok=True)
lang_setting = setting.Setting("./configs/language_config.json", setting.language_setting_configs)
lang.set_system_language(lang_setting.value("language"))
system_setting = setting.Setting("./configs/system_config.json", setting.bot_setting_configs, lang_setting.value("language"))
bot_name = system_setting.value("bot_name")

# TODO 添加维护模式

# 设置控制台日志记录器
LOG_DIRECTORY_PATH = "./logs"
os.makedirs(LOG_DIRECTORY_PATH, exist_ok=True)
log_name_time = startup_time.replace(":", "_")
console = output_console.Console(LOG_DIRECTORY_PATH, log_name_time, system_setting.value("log"), version_header)

# 设置图标库
icon_lib = icon.IconLib()
icon_lib.load_icons("./zeta_bot/icons")

# 功能型模块
from zeta_bot import (
    go_music,
    native_music,
    bilibili,
    ytdlp,
    file_management,
    member,
    guild,
    audio,
    playlist,
    playback,
    events,
)
from zeta_bot.help import HelpMenu
from zeta_bot.web import server as web_server

print(f"\nZeta-Bot程序启动\n{logo}\n\n{version_header}\n")

# 系统检测
if platform.system().lower() == "windows":
    ffmpeg_path = "./bin/ffmpeg.exe"
else:
    ffmpeg_path = "./bin/ffmpeg"
# bin文件夹中没有FFmpeg时，使用系统PATH中的FFmpeg
if not os.path.exists(ffmpeg_path) and shutil.which("ffmpeg"):
    ffmpeg_path = shutil.which("ffmpeg")

# 初始化机器人设置
intents = discord.Intents.all()
bot = discord.Bot(help_command=None, case_insensitive=True, intents=intents)

# 设置用户和Discord服务器管理
os.makedirs("./data", exist_ok=True)
member_lib = member.MemberLibrary()
guild_lib = guild.GuildLibrary()

# 设置下载文件管理
os.makedirs("./downloads", exist_ok=True)
audio_lib_main = file_management.AudioFileLibrary(
    "./downloads",
    "./data/audio_lib_main.json",
    "主音频文件库",
    int(float(system_setting.value("audio_library_storage_capacity"))) * 1024 * 1024  # 要求用户输入的单位为MB，转换为字节Byte
)

# 加载资源分类器
resource_classifier = ResourceClassifier()

# 历史播放列表上限
try:
    guild.HISTORY_LIMIT = max(1, int(system_setting.value("guild_past_list_size")))
except (TypeError, ValueError, KeyError):
    guild.HISTORY_LIMIT = 50

# Py-cord 颜色快捷方式
dark_teal = discord.Colour.dark_teal()
orange = discord.Colour.orange()
red = discord.Colour.red()

# go-music-api URL默认值
go_music_url = "http://127.0.0.1:8080"

# 首次启动初始化是否已完成（断线重连时on_ready会被再次调用）
startup_completed = False

# 聊天AI API 效果较差，暂时弃用
# 设置聊天AI
# if system_setting.value("chat_ai"):
#     os.makedirs("./data/ai", exist_ok=True)
#     chat_ai = ai.ChatAI(
#         system_setting.value("chat_ai_base_url"),
#         system_setting.value("chat_ai_api_key"),
#         system_setting.value("chat_ai_model_name"),
#         "./data/ai",
#         bot_name
#     )
# else:
#     chat_ai = None


# Web控制面板的命令行参数覆盖（由main.py传入）
web_overrides: Dict[str, Any] = {}


def start(mode: str, web_options: Optional[Dict[str, Any]] = None) -> None:
    """
    根据模式启动程序
    """
    if web_options:
        web_overrides.update({key: value for key, value in web_options.items() if value is not None})

    if mode == "normal" or mode == "":
        run_bot()
    elif mode == "setting":
        system_setting.modify_mode()
        run_bot()
    elif mode == "reset":
        system_setting.reset_setting()
        run_bot()
    else:
        raise ValueError("未找到指定启动模式")


if __name__ == "__main__":
    start("normal")


def run_bot() -> None:
    """启动机器人"""
    utils.cp("正在登录")
    try:
        bot.run(system_setting.value("token"))
    except errors.LoginFailure:
        print("登录失败，请检查Discord机器人令牌是否正确，在启动指令后添加\" --mode=setting\"来修改设置")
        sys.exit(1)


@bot.event
async def on_error(event_method, *args, **kwargs):
    # Pycord传入的第一个参数是事件名称，异常需要从sys.exc_info()获取
    exception = sys.exc_info()[1]
    if exception is None:
        exception = RuntimeError(f"事件 {event_method} 发生未知错误")
    await console.rp(f"处理事件 {event_method} 时发生错误", "[系统]", message_type=utils.PrintType.ERROR, print_head=True)
    await console.on_error(exception)


@bot.event
async def on_application_command_error(ctx, exception):
    await console.on_application_command_error(ctx, exception)

    # 向用户回复发生错误
    icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"
    await embed_respond(ctx, author_name="发生错误", author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), colour=red, silent=True)


# 指令名称与权限名称不一致时的对应关系
COMMAND_PERMISSION_ALIAS = {
    "webauth": "login_webui",
}


def is_owner(user_id) -> bool:
    return str(user_id) == str(system_setting.value("owner"))


def user_allowed(user_id, operation: str) -> bool:
    """
    检查用户是否有权限进行某项操作（Web控制面板使用）
    """
    if is_owner(user_id):
        return True
    try:
        return member_lib.allow(user_id, operation)
    except (errors.JSONFileError, FileNotFoundError, OSError):
        return False


def user_group(user_id) -> str:
    if is_owner(user_id):
        return "owner"
    try:
        return member_lib.get_group(user_id)
    except (errors.JSONFileError, FileNotFoundError, OSError, KeyError):
        return "unknown"


def invite_url() -> str:
    """
    机器人的邀请链接（包含bot与applications.commands授权以及语音播放所需权限）
    """
    permissions = discord.Permissions(
        view_channel=True, send_messages=True, embed_links=True, attach_files=True,
        read_message_history=True, connect=True, speak=True,
    )
    return discord.utils.oauth_url(bot.user.id, permissions=permissions, scopes=("bot", "applications.commands"))


async def command_check(ctx: discord.ApplicationContext) -> bool:
    """
    对指令触发进行日志记录，检测用户是否记录在案，检测用户是否有权限使用该条指令
    """
    # 在私信中，或在机器人未以Bot身份加入的服务器中使用指令（仅授权了applications.commands或以用户应用安装）
    # 此时机器人无法获取服务器与语音频道信息
    if ctx.guild is None or bot.get_guild(ctx.guild.id) is None:
        await console.rp(f"用户 {ctx.user} 在机器人未加入的服务器或私信中发送指令：<{ctx.command}>", "[系统]", message_type=utils.PrintType.WARNING)
        if ctx.guild is None:
            message = "请在服务器中使用此指令"
        else:
            message = f"{bot_name}尚未以机器人身份加入此服务器，无法加入语音频道\n请服务器管理员通过以下链接邀请：\n{invite_url()}"
        await embed_respond(ctx, message, colour=orange, ephemeral=True)
        return False

    member_lib.check(ctx)
    user_group = member_lib.get_group(ctx.user.id)
    operation = str(ctx.command)
    web_server.monitor.record_command(operation)
    # 如果用户是机器人所有者
    if str(ctx.user.id) == system_setting.value("owner"):
        await console.rp(f"用户 {ctx.user} [用户组: 机器人所有者] 发送指令：<{operation}>", ctx.guild)
        return True
    elif member_lib.allow(ctx.user.id, COMMAND_PERMISSION_ALIAS.get(operation, operation)):
        await console.rp(f"用户 {ctx.user} [用户组: {user_group}] 发送指令：<{operation}>", ctx.guild)
        return True
    else:
        await console.rp(f"用户 {ctx.user} [用户组: {user_group}] 发送指令：<{operation}>，权限不足，操作已被拒绝", ctx.guild)
        await embed_respond(ctx, "权限不足", colour=red, silent=True)
        return False


async def result_check(result: Result) -> Result:
    if not result:
        if result.exception is not None:
            await console.on_error(result.exception)
        elif result.message != "":
            await console.on_error(RuntimeError(result.message))
    return result


# 启动就绪时
@bot.event
async def on_ready():
    """
    当机器人启动完成时自动调用
    """

    current_time = utils.ctime_str()
    await console.rp(f"登录完成：以{bot.user}的身份登录，登录时间：{current_time}", "[系统]")

    if len(bot.guilds) == 0:
        await console.rp(
            f"机器人尚未加入任何服务器，请使用以下链接邀请机器人（需要包含bot授权，否则无法使用语音频道）：\n{invite_url()}",
            "[系统]",
            message_type=utils.PrintType.WARNING,
            print_head=True
        )

    # 断线重连后on_ready会被再次调用，以下初始化只执行一次
    global startup_completed
    if startup_completed:
        # 重新连接后机器人状态可能被重置
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.playing, name=system_setting.value("default_activity"))
        )
        await console.rp("重新连接完成", "[系统]")
        return
    startup_completed = True

    # 启动定时任务框架
    scheduler_ar_1 = AsyncIOScheduler()
    scheduler_ar_2 = AsyncIOScheduler()

    if system_setting.value("auto_reboot"):
        # 设置自动重启
        ar_timezone = "Asia/Shanghai"
        ar_time = utils.time_split(system_setting.value("ar_time"))
        scheduler_ar_1.add_job(
            auto_reboot, CronTrigger(
                timezone=ar_timezone, hour=ar_time[0],
                minute=ar_time[1], second=ar_time[2]
            )
        )

        if system_setting.value("ar_reminder"):
            # 设置自动重启提醒
            ar_r_time = utils.time_split(system_setting.value("ar_reminder_time"))
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
        activity=discord.Activity(type=bot_activity_type, name=system_setting.value("default_activity"))
    )

    # FFmpeg检测
    if not os.path.exists(ffmpeg_path):
        await console.rp(
            "未发现FFmpeg程序，将无法使用音频播放相关功能，请下载FFmpeg并将其放在程序根目录内的bin文件夹内，或将其添加到系统PATH中",
            "[系统]",
            message_type=utils.PrintType.WARNING,
            print_head=True
        )
    else:
        await console.rp(f"使用FFmpeg：{ffmpeg_path}", "[系统]")

    # go-music-api检测（仅当有平台在configs/resource_handler.json中配置为使用go-music-api时）
    global go_music_url
    go_music_url = system_setting.value("go_music_api_url")
    if not resource_classifier.uses(DownloadHandler.GO_MUSIC_API):
        await console.rp(f"音乐平台下载器：{'，'.join(f'{name} -> {handler}' for name, handler in resource_classifier.describe().items())}", "[系统]")
    elif go_music_url is None or go_music_url == "" or not await go_music.is_available(go_music_url, silent=False):
        await console.rp(
            "go-music-api服务连接失败，请检查部署情况以及system_config.json中的go_music_api_url设置",
            "[系统]",
            message_type=utils.PrintType.WARNING,
            print_head=True
        )
        # 改用内置下载器
        for changed_platform, fallback_handler in resource_classifier.apply_fallbacks(go_music_available=False).items():
            await console.rp(
                f"{changed_platform.value}已临时改用内置下载器：{fallback_handler.value}",
                "[系统]",
                message_type=utils.PrintType.WARNING,
                print_head=True
            )
    else:
        audio_lib_main.set_go_music_api_url(go_music_url)

    # 启动Web控制面板
    await web_server.start_from_bot(sys.modules[__name__], web_overrides)

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
        # if system_setting.value("chat_ai") and chat_ai is not None:
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
    if system_setting.value("ar_announcement"):
        for current_guild in bot.guilds:
            voice_client = current_guild.voice_client
            if voice_client is not None:
                await current_guild.text_channels[0].send(f"{current_time} 开始执行自动定时重启")
    os.execl(python_path, python_path, * sys.argv)


async def auto_reboot_reminder():
    """
    向机器人仍在语音频道中的所有服务器的第一个文字频道发送即将重启通知
    """
    ar_time = system_setting.value("ar_time")
    await console.rp(f"发送自动重启通知", "[系统]")
    for current_guild in bot.guilds:
        voice_client = current_guild.voice_client
        if voice_client is not None:
            await current_guild.text_channels[0].send(f"注意：将在{ar_time}时自动重启")


# 记录每条消息当前携带的附件（图标）文件名
# 编辑消息时如果图标没有变化，则不再重新上传，直接沿用消息中已有的附件（重复上传会让每次编辑多花费数百毫秒）
_message_attachments: "collections.OrderedDict[Tuple[str, int], Tuple[str, ...]]" = collections.OrderedDict()
_MESSAGE_ATTACHMENTS_LIMIT = 500


def _attachment_key(target) -> Optional[Tuple[str, int]]:
    if isinstance(target, discord.Interaction):
        return "interaction", target.id
    if isinstance(target, (discord.Message, discord.InteractionMessage)):
        return "message", target.id
    return None


def _remember_attachments(target, files: Optional[List[discord.File]]) -> None:
    key = _attachment_key(target)
    if key is None:
        return
    _message_attachments[key] = tuple(file.filename for file in files) if files else ()
    _message_attachments.move_to_end(key)
    while len(_message_attachments) > _MESSAGE_ATTACHMENTS_LIMIT:
        _message_attachments.popitem(last=False)


def _same_attachments(target, files: Optional[List[discord.File]]) -> bool:
    if not files:
        return False
    key = _attachment_key(target)
    return key is not None and _message_attachments.get(key) == tuple(file.filename for file in files)


async def _edit_or_send(
        ctx: discord.ApplicationContext,
        response,
        content: Optional[str],
        embed: Optional[discord.Embed],
        files: Optional[List[discord.File]],
        view: Optional[discord.ui.View],
        silent: bool
) -> Union[discord.InteractionMessage, discord.Message]:
    """
    如果<response>可以被编辑则编辑，否则发送新消息
    """
    if files is not None and len(files) < 1:
        files = None

    if not isinstance(response, (discord.Interaction, discord.InteractionMessage, discord.Message)):
        message = await ctx.send(content=content, embed=embed, files=files, view=view, silent=silent)
        _remember_attachments(message, files)
        return message

    kwargs = {"content": content, "embed": embed, "view": view}
    if _same_attachments(response, files):
        # 图标未变化：不传入files与attachments，Discord会保留消息中已有的附件
        pass
    elif files is None:
        # 如files为空需要清除附件，确保附件不会被传到修改后的信息中
        kwargs["attachments"] = []
    else:
        kwargs["files"] = files

    try:
        if isinstance(response, discord.Interaction):
            message = await response.edit_original_response(**kwargs)
        else:
            message = await response.edit(**kwargs)
    except discord.NotFound:
        # 消息已被删除
        return response
    except discord.HTTPException as e:
        # 交互令牌在15分钟后失效（50027 Invalid Webhook Token），改为通过频道编辑消息
        channel = getattr(response, "channel", None)
        if e.code in (50027, 10015) and channel is not None and hasattr(channel, "get_partial_message"):
            if "files" in kwargs:
                kwargs["files"] = [discord.File(icon_lib.icons[file.filename], filename=file.filename) for file in files if file.filename in icon_lib.icons]
            try:
                message = await channel.get_partial_message(response.id).edit(**kwargs)
            except discord.HTTPException as fallback_exception:
                await console.rp(f"消息编辑失败：{fallback_exception}", ctx.guild, message_type=utils.PrintType.WARNING)
                return response
            if message is None:
                return response
        else:
            await console.rp(f"消息编辑失败：{e}", ctx.guild, message_type=utils.PrintType.WARNING)
            return response

    _remember_attachments(response, files)
    if message is not None:
        _remember_attachments(message, files)
        return message
    return response


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
) -> Tuple[Union[discord.Interaction, discord.WebhookMessage], discord.Embed]:
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
    _remember_attachments(message, files)

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
) -> Tuple[Union[discord.Interaction, discord.WebhookMessage], discord.Embed]:
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
    _remember_attachments(message, files)

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

    return await _edit_or_send(ctx, response, content, embed, files, view, silent)


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

    return await _edit_or_send(ctx, response, None, embed, files, view, silent), embed


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
    if not await command_check(ctx):
        return
    await info_callback(ctx)


@bot.slash_command(name_localizations=lang.get_command_name("help"), description="召唤帮助菜单")
async def help(ctx: discord.ApplicationContext) -> None:
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


@bot.slash_command(name_localizations=lang.get_command_name("search_audio"), description="搜索并播放来自哔哩哔哩，YouTube，网易云音乐，QQ音乐的音频")
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


@bot.slash_command(name_localizations=lang.get_command_name("play"), description="播放来自哔哩哔哩，YouTube，网易云音乐，QQ音乐的音频")
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
    if not await command_check(ctx):
        return
    await list_callback(ctx)


playlist_operation = ["create", "add", "remove", "delete"]

@bot.slash_command(name_localizations=lang.get_command_name("playlist"), description="自定播放列表操作")
@option(
    "operation",
    description="要进行的播放列表操作",
    required=True,
    choices=playlist_operation
)
async def playlist(ctx: discord.ApplicationContext):
    await ctx.defer()
    if not await command_check(ctx):
        return
    await playlist_callback(ctx)


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
    if not await command_check(ctx):
        return
    await move_callback(ctx, move, to)


@bot.slash_command(name_localizations=lang.get_command_name("clear"), description="清空主播放列表中的所有音频")
async def clear(ctx: discord.ApplicationContext):
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
    if not await command_check(ctx):
        return
    await volume_callback(ctx, volume_number)


@bot.slash_command(name_localizations=lang.get_command_name("radio"), description="电台模式")
async def radio(ctx: discord.ApplicationContext):
    await ctx.defer()
    if not await command_check(ctx):
        return
    await radio_callback(ctx)


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


@bot.slash_command(name_localizations=lang.get_command_name("webauth"), description="获取Web控制面板的登录验证码")
@option(
    "days", int,
    description="登录有效天数（默认3天）",
    required=False,
    min_value=1,
    max_value=30,
)
async def webauth(ctx: discord.ApplicationContext, days: int = 3):
    if not await command_check(ctx):
        return
    if not web_server.is_running():
        await embed_respond(ctx, "Web控制面板未启用或启动失败，请联系机器人管理员", colour=orange, ephemeral=True)
        return
    code, validity_minutes = web_server.auth.generate_code(ctx.user.id, str(ctx.user), days)
    await ctx.respond(
        f"🔐 **Web控制面板登录验证码**\n"
        f"```\n{code}\n```\n"
        f"控制面板地址：{web_server.public_url()}\n"
        f"验证码将在 **{validity_minutes}分钟** 内有效且只能使用一次，登录后保持 **{days}天**\n"
        f"⚠️ 请勿将此验证码分享给他人",
        ephemeral=True
    )


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
        # 退出频道会停止推流，保留正在播放的音频，下次可以继续播放
        if is_streaming(ctx.guild):
            current_guild.playback.request("hold")

        last_channel = voice_client.channel
        await voice_client.disconnect(force=False)

        await console.rp(f"离开语音频道：{last_channel}", ctx.guild)

        await embed_respond(ctx, author_name=f"离开语音频道：<-  {last_channel}", author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename))

    else:
        await embed_respond(ctx, f"{bot_name} 没有连接到任何语音频道", silent=True)

    await current_guild.refresh_list_view()


async def search_audio_callback(
        ctx: discord.ApplicationContext,
        query,
        site=None,
        query_num=5,
        response = None
) -> None:
    await guild_lib.check(ctx, audio_lib_main)
    current_guild = guild_lib.get_guild(ctx)

    search_result: Dict[str, Optional[List]] = {key: None for key in supported_search_sites}

    icon_loading_filename = "hourglass_hover_rotation_animated_1000ms_infinite_30px.gif"
    icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"

    if response is None:
        loading_msg, embed = await embed_respond(ctx, author_name=f"正在搜索：{query}", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename), silent=True)
    else:
        loading_msg, embed = await embed_eos(ctx, response, author_name=f"正在搜索：{query}", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename), silent=True)

    if site is not None and site not in supported_search_sites:
        await embed_eos(ctx, response, author_name="不支持该平台搜索", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
        return
    # 同时在各平台搜索（未指定平台时每个平台3个结果）
    per_site = query_num if site is not None else 3
    search_factories = {
        "哔哩哔哩": lambda: bilibili.search(query, query_num=per_site),
        "YouTube": lambda: ytdlp.youtube_search(query, query_num=per_site),
        "网易云音乐": lambda: native_music.search(query, "netease", per_site),
        "QQ音乐": lambda: native_music.search(query, "qq", per_site),
    }
    search_jobs = {key: factory() for key, factory in search_factories.items() if site is None or site == key}
    for key, value in zip(search_jobs.keys(), await asyncio.gather(*search_jobs.values(), return_exceptions=True)):
        if isinstance(value, Exception):
            await console.on_error(value)
            value = []
        search_result[key] = value

    if all(not value for value in search_result.values()):
        await embed_eos(ctx, loading_msg, author_name=f"没有找到与「{query}」相关的结果", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
        return

    title_str = f""
    address_str = f""
    resource_list = []
    counter = 1
    for key in search_result:
        if search_result[key]:
            title_str += f"{key}\n"
            address_str += f"{key}\n"
            for item in search_result[key]:
                # 选择菜单最多可容纳20个结果
                if counter > SearchedAudioSelectionMenu.MAX_RESULTS:
                    break
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
    formatted_url, link_type, handler = resource_classifier.check(link)

    # 如果是短链，则重定向后继续处理
    if link_type.need_redirect:
        try:
            formatted_url = await utils.get_redirect_url_async(formatted_url)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            await embed_eos(ctx, response, author_name="短链接重定向失败", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
            await console.rp(f"短链接重定向失败", ctx.guild, message_type=utils.PrintType.ERROR, print_head=True)
            return
        else:
            await console.rp(f"获取的重定向链接为 {formatted_url}", ctx.guild)

    if link_type is not LinkType.UNKNOWN:
        if response is None:
            loading_msg, embed = await embed_respond(ctx, author_name=f"正在加载{link_type.label}信息", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename), silent=True)
        else:
            loading_msg, embed = await embed_eos(ctx, response, author_name=f"正在加载{link_type.label}信息", author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename), silent=True)

        # 交由bilibili-api-python处理
        if handler is DownloadHandler.BILIBILI_API_PYTHON:
            await play_bilibili(ctx, link_type, formatted_url, response=loading_msg)

        # 交由go-music-api处理
        elif handler in (DownloadHandler.GO_MUSIC_API, DownloadHandler.NATIVE):
            await play_go_music(ctx, link_type, formatted_url, response=loading_msg, handler=handler)

        # 交由YT-DLP处理
        elif handler is DownloadHandler.YT_DLP:
            await play_ytdlp(ctx, formatted_url, response=loading_msg)

        # 链接不由任何处理器处理
        else:
            await search_audio_callback(ctx, query=link, response=loading_msg)

    # 无法检测链接来源
    else:
        await search_audio_callback(ctx, query=link)

    await current_guild.refresh_list_view()


# ---------------------------------------- 播放引擎 ----------------------------------------
# Discord指令与Web控制面板共用同一套播放逻辑：
#   start_stream     开始推流一个音频
#   request_stop     停止当前推流并指定停止后的操作（跳过/跳转进度/重新播放/保持）
#   on_track_end     推流结束回调，根据停止原因与播放模式决定下一个音频

PLAYING_ICON_FILENAME = "vinyl_loop_playing_animated_infinite_100px.gif"
FINISHED_ICON_FILENAME = "record_button_in_reveal_animated_0ms_100px.gif"

# 每个服务器的播放结束处理锁，确保同一服务器的结束回调按顺序执行
_track_end_locks: Dict[int, asyncio.Lock] = {}


def _make_audio_source(target_audio: audio.Audio, volume: float, offset: float = 0.0) -> discord.PCMVolumeTransformer:
    before_options = f"-ss {offset:.2f}" if offset > 0 else None
    # -vn：不解码视频流（部分来源下载的是音视频合流文件）
    source = discord.FFmpegPCMAudio(source=target_audio.get_path(), executable=ffmpeg_path, before_options=before_options, options="-vn")
    return discord.PCMVolumeTransformer(source, volume=volume / 100.0)


def start_stream(discord_guild: discord.Guild, current_guild: guild.Guild, target_audio: audio.Audio, offset: float = 0.0) -> bool:
    """
    在<discord_guild>的语音频道中开始推流<target_audio>，<offset>为开始播放的位置（秒）
    返回是否成功开始推流
    """
    voice_client = discord_guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        return False
    if voice_client.is_playing() or voice_client.is_paused():
        return False

    lock_key = f"{discord_guild.id}_NOW_PLAYING"
    playback_state = current_guild.playback
    if playback_state.audio is not None:
        audio_lib_main.unlock_audio(lock_key, playback_state.audio)
    audio_lib_main.lock_audio(lock_key, target_audio)

    guild_id = discord_guild.id
    try:
        voice_client.play(
            _make_audio_source(target_audio, current_guild.get_voice_volume(), offset),
            after=lambda error: asyncio.run_coroutine_threadsafe(on_track_end(guild_id, error), bot.loop)
        )
    except (discord.ClientException, OSError) as e:
        audio_lib_main.unlock_audio(lock_key, target_audio)
        playback_state.stop()
        bot.loop.create_task(console.on_error(e))
        return False

    playback_state.start(target_audio, offset)
    events.publish("guild", guild_id)
    return True


def is_streaming(discord_guild: discord.Guild) -> bool:
    voice_client = discord_guild.voice_client
    return voice_client is not None and (voice_client.is_playing() or voice_client.is_paused())


def request_stop(discord_guild: discord.Guild, current_guild: guild.Guild, action: Optional[str] = None, value: Any = None) -> bool:
    """
    停止当前推流，停止后由on_track_end根据<action>执行后续操作（见playback模块说明）
    返回是否存在正在推流的音频
    """
    if not is_streaming(discord_guild):
        return False
    current_guild.playback.request(action, value)
    discord_guild.voice_client.stop()
    return True


async def on_track_end(guild_id: int, error: Optional[Exception] = None) -> None:
    """
    推流结束时调用（正常结束、被跳过、被停止）
    """
    lock = _track_end_locks.setdefault(guild_id, asyncio.Lock())
    async with lock:
        try:
            await _handle_track_end(guild_id, error)
        except Exception as e:
            await console.on_error(e)
        finally:
            current_guild = guild_lib.get_guild_by_id(guild_id)
            if current_guild is not None:
                current_guild.playback.resolve_end_waiters()


async def _handle_track_end(guild_id: int, error: Optional[Exception]) -> None:
    discord_guild = bot.get_guild(guild_id)
    current_guild = guild_lib.get_guild_by_id(guild_id)
    if discord_guild is None or current_guild is None:
        return

    current_playlist = current_guild.get_playlist()
    playback_state = current_guild.playback
    action, value = playback_state.consume_request()
    keep_paused = playback_state.pause_after_start
    playback_state.pause_after_start = False

    finished_audio = playback_state.audio
    played_seconds = playback_state.position()
    if finished_audio is not None:
        audio_lib_main.unlock_audio(f"{guild_id}_NOW_PLAYING", finished_audio)
    playback_state.stop()

    await console.rp(f"触发 play_next（{action or '播放结束'}）", discord_guild)
    if error is not None:
        await console.rp(f"播放时发生错误：{error}", discord_guild, message_type=utils.PrintType.ERROR, print_head=True)

    voice_client = discord_guild.voice_client
    connected = voice_client is not None and voice_client.is_connected()

    # 被要求保持，或已不在语音频道中（离开频道、被踢出频道）：保留播放列表，不继续播放
    if action == "hold" or not connected:
        await current_guild.refresh_list_view()
        return

    # 跳转进度与重新播放：不移除列表首位音频
    if action in ("seek", "restart"):
        if not current_playlist.is_empty():
            target_audio = current_playlist.get_audio(0)
            offset = float(value or 0) if action == "seek" else 0.0
            if start_stream(discord_guild, current_guild, target_audio, offset):
                if keep_paused:
                    voice_client.pause()
                    playback_state.pause()
                if action == "restart" and target_audio is not finished_audio:
                    await announce_now_playing(current_guild, target_audio)
        await current_guild.refresh_list_view()
        return

    # 正常结束或跳过：按播放模式决定下一个音频
    play_mode = current_guild.get_play_mode()
    # 刚开始播放就结束，通常是文件损坏，不再循环该音频
    broken = (action is None and finished_audio is not None and played_seconds < 1.0 and finished_audio.get_duration() > 3)
    if broken:
        await console.rp(f"音频 {finished_audio.get_title()} 播放异常结束，文件可能已损坏", discord_guild, message_type=utils.PrintType.WARNING, print_head=True)

    head = current_playlist.get_audio(0)
    if play_mode == 1 and action is None and not broken and head is not None and head is finished_audio:
        # 单曲循环：保留当前音频
        pass
    elif head is not None and (finished_audio is None or head is finished_audio):
        done_audio = current_playlist.pop_audio(0)
        current_guild.add_history(done_audio)
        # 列表循环与随机循环：将播放完的音频放回列表末尾
        if play_mode in (2, 4) and done_audio is not None and not broken:
            current_playlist.append_audio(done_audio)
        # 随机播放与随机循环：随机选择下一个音频（随机循环时避免立即重复刚放回末尾的音频）
        if play_mode in (3, 4) and len(current_playlist) > 1:
            upper = len(current_playlist) - 1 if play_mode == 4 else len(current_playlist)
            choice = random.randrange(0, max(1, upper))
            if choice != 0:
                current_playlist.move_audio(choice, 0)

    # 跳过文件已丢失的音频
    while not current_playlist.is_empty() and not os.path.exists(current_playlist.get_audio(0).get_path()):
        missing_audio = current_playlist.pop_audio(0)
        await console.rp(f"音频文件已丢失，跳过：{missing_audio.get_title()}", discord_guild, message_type=utils.PrintType.WARNING, print_head=True)

    if current_playlist.is_empty():
        await console.rp("播放队列已结束", discord_guild)
        await announce_queue_end(current_guild)
        await current_guild.refresh_list_view()
        return

    next_audio = current_playlist.get_audio(0)
    if start_stream(discord_guild, current_guild, next_audio):
        await console.rp(f"开始播放：{next_audio.get_path()} 时长：{next_audio.get_duration_str()}", discord_guild)
        if keep_paused:
            voice_client.pause()
            playback_state.pause()
        # 单曲循环重复播放时不再重复发送通知
        if next_audio is not finished_audio:
            await announce_now_playing(current_guild, next_audio)
        if keep_paused:
            await send_to_guild_channel(current_guild, description="播放器已被暂停，使用 /resume 指令恢复播放")

    await current_guild.refresh_list_view()


def build_now_playing_embed(target_audio: audio.Audio, icon_filename: str = PLAYING_ICON_FILENAME) -> discord.Embed:
    embed = discord.Embed(colour=dark_teal, description=f"**{utils.markdown_escape(target_audio.get_title())}**")
    embed.set_author(name=f"正在播放 [{target_audio.get_duration_str()}]", icon_url=icon.url(icon_filename))
    if target_audio.get_cover_url():
        embed.set_thumbnail(url=target_audio.get_cover_url())
    return embed


async def send_to_guild_channel(current_guild: guild.Guild, embed: Optional[discord.Embed] = None, description: Optional[str] = None, icon_filename: Optional[str] = None) -> Optional[discord.Message]:
    """
    向服务器最近使用指令的文字频道发送消息（用于没有指令上下文的通知，例如自动播放下一首、Web控制面板操作）
    """
    channel = current_guild.get_text_channel()
    if channel is None:
        return None
    if embed is None:
        embed = discord.Embed(colour=dark_teal, description=description)
    files = icon_lib.files(icon_filename) if icon_filename else None
    try:
        message = await channel.send(embed=embed, files=files or None, silent=True)
    except discord.HTTPException as e:
        await console.rp(f"频道消息发送失败：{e}", current_guild.get_name(), message_type=utils.PrintType.WARNING)
        return None
    _remember_attachments(message, files)
    return message


async def announce_now_playing(current_guild: guild.Guild, target_audio: audio.Audio) -> None:
    embed = build_now_playing_embed(target_audio)
    message = await send_to_guild_channel(current_guild, embed=embed, icon_filename=PLAYING_ICON_FILENAME)
    if message is not None:
        await current_guild.refresh_playing_message(message, embed)


async def announce_queue_end(current_guild: guild.Guild) -> None:
    embed = discord.Embed(colour=dark_teal)
    embed.set_author(name="播放队列已结束", icon_url=icon.url(FINISHED_ICON_FILENAME))
    await send_to_guild_channel(current_guild, embed=embed, icon_filename=FINISHED_ICON_FILENAME)
    await current_guild.refresh_playing_message(None, None)


async def play_audio(ctx: discord.ApplicationContext, target_audio: audio.Audio, response: Union[discord.Interaction, discord.InteractionMessage, None] = None, function_call: bool = False) -> None:
    """
    在<ctx>中的音频端播放音频<target_audio>
    <response>为用来编辑的加载信息，如果为None则发送新的通知

    :param ctx: 指令原句
    :param target_audio: 需要播放的音频
    :param response: 用于编辑的加载信息
    :param function_call 该指令是否是由其他函数调用
    """
    current_guild = guild_lib.get_guild(ctx)

    if not start_stream(ctx.guild, current_guild, target_audio):
        await console.rp(f"无法开始播放：{target_audio.get_title()}（未连接语音频道或已在播放）", ctx.guild, message_type=utils.PrintType.WARNING)
        return

    await console.rp(f"开始播放：{target_audio.get_path()} 时长：{target_audio.get_duration_str()}", ctx.guild)
    embed = build_now_playing_embed(target_audio)
    files = icon_lib.files(PLAYING_ICON_FILENAME)
    if function_call or response is None:
        try:
            message = await ctx.send(embed=embed, files=files, silent=True)
            _remember_attachments(message, files)
        except discord.HTTPException as e:
            await console.rp(f"频道消息发送失败：{e}", ctx.guild, message_type=utils.PrintType.WARNING)
            message = None
    else:
        message = await eos(ctx, response, content=None, embed=embed, files=files, silent=True)

    await current_guild.refresh_playing_message(message, embed)
    await current_guild.refresh_list_view()


async def enqueue_audio(discord_guild: discord.Guild, current_guild: guild.Guild, new_audio: audio.Audio, announce: bool = True) -> bool:
    """
    将音频加入播放列表，如果当前没有在播放则立即开始播放
    返回是否立即开始播放
    """
    current_playlist = current_guild.get_playlist()
    started = False
    if current_playlist.is_empty() and not is_streaming(discord_guild):
        started = start_stream(discord_guild, current_guild, new_audio)
    current_playlist.append_audio(new_audio)
    await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", discord_guild)
    if started and announce:
        await announce_now_playing(current_guild, new_audio)
    await current_guild.refresh_list_view()
    return started


# ---------------------------------------- Web控制接口 ----------------------------------------
# 供Web控制面板调用（在机器人事件循环中执行），与Discord指令共用播放引擎


class PlayerError(Exception):
    """
    Web控制操作失败（错误信息会直接显示给用户）
    """
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def audio_to_dict(target_audio: Optional[audio.Audio]) -> Optional[dict]:
    if target_audio is None:
        return None
    return {
        "uid": target_audio.get_uid(),
        "title": target_audio.get_title(),
        "duration": target_audio.get_duration(),
        "duration_str": target_audio.get_duration_str(),
        "source": target_audio.get_source(),
        "cover": target_audio.get_cover_url(),
        "type": target_audio.get_download_type().label,
    }


async def get_guild_pair(guild_id) -> Tuple[discord.Guild, guild.Guild]:
    try:
        discord_guild = bot.get_guild(int(guild_id))
    except (TypeError, ValueError):
        discord_guild = None
    if discord_guild is None:
        raise PlayerError("找不到该服务器", 404)
    await guild_lib.check_by_guild_obj(discord_guild, audio_lib_main)
    return discord_guild, guild_lib.get_guild_by_id(discord_guild.id)


def guild_summary(discord_guild: discord.Guild) -> dict:
    """
    服务器概要（用于服务器列表与监控面板）
    """
    voice_client = discord_guild.voice_client
    current_guild = guild_lib.get_guild_by_id(discord_guild.id)
    status_code = get_voice_client_status(voice_client)
    summary = {
        "id": str(discord_guild.id),
        "name": discord_guild.name,
        "icon": discord_guild.icon.url if discord_guild.icon else None,
        "member_count": discord_guild.member_count,
        "voice_channel": voice_client.channel.name if voice_client is not None and voice_client.channel else None,
        "status": status_code,
        "status_str": get_voice_client_status_str(status_code),
        "latency_ms": round(voice_client.latency * 1000) if voice_client is not None and voice_client.latency != float("inf") else None,
        "queue_length": 0,
        "now_playing": None,
    }
    if current_guild is not None:
        current_playlist = current_guild.get_playlist()
        summary["queue_length"] = len(current_playlist)
        summary["queue_duration"] = current_playlist.get_duration_str()
        if current_guild.playback.is_active():
            summary["now_playing"] = audio_to_dict(current_guild.playback.audio)
            summary["position"] = round(current_guild.playback.position(), 1)
    return summary


def guild_state(discord_guild: discord.Guild, current_guild: guild.Guild) -> dict:
    """
    服务器完整播放状态（用于Web播放器）
    """
    voice_client = discord_guild.voice_client
    current_playlist = current_guild.get_playlist()
    playback_state = current_guild.playback
    status_code = get_voice_client_status(voice_client)
    queue = []
    for index in range(len(current_playlist)):
        item = audio_to_dict(current_playlist.get_audio(index))
        item["index"] = index + 1
        queue.append(item)
    history = []
    playedlist = current_guild.get_playedlist()
    for index in range(len(playedlist) - 1, max(-1, len(playedlist) - 21), -1):
        history.append(audio_to_dict(playedlist.get_audio(index)))
    voice_channels = [
        {"id": str(channel.id), "name": channel.name, "members": len(channel.members)}
        for channel in discord_guild.voice_channels
    ]
    return {
        "id": str(discord_guild.id),
        "name": discord_guild.name,
        "status": status_code,
        "status_str": get_voice_client_status_str(status_code),
        "connected": voice_client is not None and voice_client.is_connected(),
        "voice_channel": {"id": str(voice_client.channel.id), "name": voice_client.channel.name} if voice_client is not None and voice_client.channel else None,
        "voice_channels": voice_channels,
        "text_channel": getattr(current_guild.get_text_channel(), "name", None),
        "volume": current_guild.get_voice_volume(),
        "play_mode": current_guild.get_play_mode(),
        "play_modes": playback.PLAY_MODE_NAMES,
        "now_playing": audio_to_dict(playback_state.audio) if playback_state.is_active() else None,
        "position": round(playback_state.position(), 2),
        "paused": voice_client is not None and voice_client.is_paused(),
        "queue": queue,
        "queue_duration": current_playlist.get_duration_str(),
        "history": history,
    }


async def _log_web_action(discord_guild: discord.Guild, user_name: str, action: str) -> None:
    await console.rp(f"Web用户 {user_name} {action}", discord_guild)


async def player_toggle_pause(guild_id, user_name: str) -> dict:
    discord_guild, current_guild = await get_guild_pair(guild_id)
    voice_client = discord_guild.voice_client
    if voice_client is not None and voice_client.is_playing():
        voice_client.pause()
        current_guild.playback.pause()
        await _log_web_action(discord_guild, user_name, "暂停播放")
    elif voice_client is not None and voice_client.is_paused():
        voice_client.resume()
        current_guild.playback.resume()
        await _log_web_action(discord_guild, user_name, "恢复播放")
    elif voice_client is not None and voice_client.is_connected() and not current_guild.get_playlist().is_empty():
        # 恢复被中断的播放列表
        target_audio = current_guild.get_playlist().get_audio(0)
        if not os.path.exists(target_audio.get_path()):
            current_guild.get_playlist().pop_audio(0)
            raise PlayerError("音频文件已丢失，已从列表中移除")
        if start_stream(discord_guild, current_guild, target_audio):
            await announce_now_playing(current_guild, target_audio)
            await _log_web_action(discord_guild, user_name, f"开始播放：{target_audio.get_title()}")
    elif voice_client is None:
        raise PlayerError("机器人不在语音频道中，请先选择语音频道加入")
    else:
        raise PlayerError("播放列表为空")
    await current_guild.refresh_list_view()
    return guild_state(discord_guild, current_guild)


async def player_skip(guild_id, user_name: str, index: Optional[int] = None) -> dict:
    """
    <index>为None或1时跳过当前音频，否则移除第<index>个音频（从1开始）
    """
    discord_guild, current_guild = await get_guild_pair(guild_id)
    current_playlist = current_guild.get_playlist()
    if current_playlist.is_empty():
        raise PlayerError("播放列表为空")
    index = 1 if index is None else int(index)
    if not 1 <= index <= len(current_playlist):
        raise PlayerError("序号不在范围内")

    target_audio = current_playlist.get_audio(index - 1)
    if index == 1:
        waiter = current_guild.playback.add_end_waiter() if is_streaming(discord_guild) else None
        skip_current(discord_guild, current_guild)
        await wait_for_track_switch(current_guild, waiter)
        await _log_web_action(discord_guild, user_name, f"跳过：{target_audio.get_title()}")
    else:
        current_playlist.remove_audio(index - 1)
        await _log_web_action(discord_guild, user_name, f"移除第{index}个音频：{target_audio.get_title()}")
    await current_guild.refresh_list_view()
    return guild_state(discord_guild, current_guild)


async def player_previous(guild_id, user_name: str) -> dict:
    discord_guild, current_guild = await get_guild_pair(guild_id)
    previous_audio = current_guild.pop_history()
    if previous_audio is None:
        raise PlayerError("没有可播放的历史音频")
    current_guild.get_playlist().insert_audio(previous_audio, 0)
    if is_streaming(discord_guild):
        waiter = current_guild.playback.add_end_waiter()
        request_stop(discord_guild, current_guild, "restart")
        await wait_for_track_switch(current_guild, waiter)
    elif start_stream(discord_guild, current_guild, previous_audio):
        await announce_now_playing(current_guild, previous_audio)
    await _log_web_action(discord_guild, user_name, f"播放上一首：{previous_audio.get_title()}")
    await current_guild.refresh_list_view()
    return guild_state(discord_guild, current_guild)


async def player_seek(guild_id, user_name: str, position: float) -> dict:
    discord_guild, current_guild = await get_guild_pair(guild_id)
    playback_state = current_guild.playback
    if not is_streaming(discord_guild) or not playback_state.is_active():
        raise PlayerError("当前没有正在播放的音频")
    duration = playback_state.audio.get_duration()
    position = max(0.0, min(float(position), max(0.0, duration - 1)))
    playback_state.pause_after_start = discord_guild.voice_client.is_paused()
    waiter = playback_state.add_end_waiter()
    request_stop(discord_guild, current_guild, "seek", position)
    await wait_for_track_switch(current_guild, waiter)
    await _log_web_action(discord_guild, user_name, f"跳转至 {utils.convert_duration_to_str(int(position))}")
    await current_guild.refresh_list_view()
    return guild_state(discord_guild, current_guild)


async def player_move(guild_id, user_name: str, from_index: int, to_index: int) -> dict:
    """
    移动音频，序号从1开始
    """
    discord_guild, current_guild = await get_guild_pair(guild_id)
    current_playlist = current_guild.get_playlist()
    from_index, to_index = int(from_index), int(to_index)
    if not 1 <= from_index <= len(current_playlist) or not 1 <= to_index <= len(current_playlist):
        raise PlayerError("序号不在范围内")
    if from_index == to_index:
        return guild_state(discord_guild, current_guild)

    title = current_playlist.get_audio(from_index - 1).get_title()
    current_playlist.move_audio(from_index - 1, to_index - 1)
    if (from_index == 1 or to_index == 1) and is_streaming(discord_guild):
        current_guild.playback.pause_after_start = discord_guild.voice_client.is_paused()
        waiter = current_guild.playback.add_end_waiter()
        request_stop(discord_guild, current_guild, "restart")
        await wait_for_track_switch(current_guild, waiter)
    await _log_web_action(discord_guild, user_name, f"将 {title} 移至第{to_index}位")
    await current_guild.refresh_list_view()
    return guild_state(discord_guild, current_guild)


async def player_set_volume(guild_id, user_name: str, volume: float) -> dict:
    discord_guild, current_guild = await get_guild_pair(guild_id)
    new_volume = apply_volume(discord_guild, current_guild, float(volume))
    await _log_web_action(discord_guild, user_name, f"将音量设置为 {new_volume}%")
    await current_guild.refresh_list_view()
    return guild_state(discord_guild, current_guild)


async def player_set_mode(guild_id, user_name: str, mode: int) -> dict:
    discord_guild, current_guild = await get_guild_pair(guild_id)
    if not current_guild.set_play_mode(int(mode)):
        raise PlayerError("无效的播放模式")
    await _log_web_action(discord_guild, user_name, f"将播放模式设置为 {playback.PLAY_MODE_NAMES[int(mode)]}")
    await current_guild.refresh_list_view()
    return guild_state(discord_guild, current_guild)


async def player_clear(guild_id, user_name: str) -> dict:
    discord_guild, current_guild = await get_guild_pair(guild_id)
    current_guild.get_playlist().remove_all()
    request_stop(discord_guild, current_guild, "hold")
    await _log_web_action(discord_guild, user_name, "清空播放列表")
    await current_guild.refresh_list_view()
    return guild_state(discord_guild, current_guild)


async def player_join(guild_id, user_name: str, channel_id) -> dict:
    discord_guild, current_guild = await get_guild_pair(guild_id)
    channel = discord_guild.get_channel(int(channel_id))
    if not isinstance(channel, discord.VoiceChannel):
        raise PlayerError("找不到该语音频道")
    voice_client = discord_guild.voice_client
    try:
        if voice_client is None:
            await channel.connect()
        else:
            await voice_client.move_to(channel)
    except (discord.ClientException, asyncio.TimeoutError) as e:
        raise PlayerError(f"加入语音频道失败：{e}")
    await _log_web_action(discord_guild, user_name, f"让机器人加入语音频道：{channel.name}")
    await current_guild.refresh_list_view()
    return guild_state(discord_guild, current_guild)


async def player_leave(guild_id, user_name: str) -> dict:
    discord_guild, current_guild = await get_guild_pair(guild_id)
    voice_client = discord_guild.voice_client
    if voice_client is None:
        raise PlayerError("机器人不在语音频道中")
    if is_streaming(discord_guild):
        current_guild.playback.request("hold")
    channel_name = voice_client.channel.name if voice_client.channel else ""
    await voice_client.disconnect(force=False)
    await _log_web_action(discord_guild, user_name, f"让机器人离开语音频道：{channel_name}")
    await current_guild.refresh_list_view()
    return guild_state(discord_guild, current_guild)


async def download_single(url: str) -> audio.Audio:
    """
    下载链接对应的单个音频（Web控制面板使用），播放列表/专辑等需要选择的内容请在Discord中使用/play
    """
    formatted_url, link_type, handler = resource_classifier.check(url)
    if link_type is LinkType.UNKNOWN or handler is None:
        raise PlayerError("无法识别的链接，请使用搜索功能")

    if link_type.need_redirect:
        try:
            formatted_url = await utils.get_redirect_url_async(formatted_url)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            raise PlayerError("短链接重定向失败")
        formatted_url, link_type, handler = resource_classifier.check(formatted_url)

    if handler is DownloadHandler.BILIBILI_API_PYTHON:
        bvid = formatted_url if link_type is LinkType.BILIBILI_BVID else utils.get_bvid_from_url(formatted_url)
        if bvid is None:
            raise PlayerError("无效的哔哩哔哩链接")
        info_result = await result_check(await bilibili.get_info(bvid))
        if not info_result:
            raise PlayerError(f"信息获取失败：{info_result.message}")
        download_type = DownloadType.BILIBILI_SINGLE if info_result.result["videos"] == 1 else DownloadType.BILIBILI_P
        new_result = await result_check(await audio_lib_main.download_bilibili(info_result.result, download_type, 0))

    elif handler in (DownloadHandler.GO_MUSIC_API, DownloadHandler.NATIVE):
        if link_type.platform is MediaPlatform.BILIBILI:
            formatted_url = utils.get_bvid_from_url(formatted_url) or formatted_url
        info_result = await result_check(await music_service_info(handler, link_type, formatted_url))
        if not info_result or info_result.result is None:
            raise PlayerError(f"信息获取失败：{info_result.message}")
        if (info_result.extra or {}).get("type") != "song":
            raise PlayerError("歌单与专辑请在Discord中使用 /play 选择要播放的歌曲")
        try:
            download_type = DownloadType[f"{link_type.platform.name}_SINGLE"]
        except KeyError:
            raise PlayerError("不支持此下载类型")
        new_result = await result_check(await music_service_download(handler, info_result.result["songs"][0], download_type))

    elif handler is DownloadHandler.YT_DLP:
        info_result = await result_check(await ytdlp.get_info(formatted_url))
        if not info_result:
            raise PlayerError(info_result.message)
        info_dict = info_result.result
        if info_dict.get("_type") == "url" and "&list" in formatted_url:
            formatted_url = formatted_url[:formatted_url.find("&list")]
            info_result = await result_check(await ytdlp.get_info(formatted_url))
            if not info_result:
                raise PlayerError(info_result.message)
            info_dict = info_result.result
        if info_dict.get("_type") == "playlist":
            raise PlayerError("播放列表请在Discord中使用 /play 选择要播放的视频")
        new_result = await result_check(await audio_lib_main.download_ytdlp(formatted_url, info_dict, DownloadType.YOUTUBE_SINGLE))

    else:
        raise PlayerError("不支持的链接类型")

    if not new_result:
        raise PlayerError(f"音频获取失败：{new_result.message}")
    return new_result.result


async def player_add_url(guild_id, user_name: str, url: str) -> dict:
    discord_guild, current_guild = await get_guild_pair(guild_id)
    new_audio = await download_single(url)
    started = await enqueue_audio(discord_guild, current_guild, new_audio)
    await _log_web_action(discord_guild, user_name, f"添加音频：{new_audio.get_title()}")
    return {"ok": True, "started": started, "audio": audio_to_dict(new_audio), "state": guild_state(discord_guild, current_guild)}


async def player_add_cached(guild_id, user_name: str, uid: str) -> dict:
    """
    将音频库中已缓存的音频加入播放列表（无需重新下载）
    """
    discord_guild, current_guild = await get_guild_pair(guild_id)
    cached_audio = audio_lib_main.get_audio_by_uid(uid)
    if cached_audio is None or not os.path.exists(cached_audio.get_path()):
        raise PlayerError("该音频已不在缓存中", 404)
    started = await enqueue_audio(discord_guild, current_guild, cached_audio)
    await _log_web_action(discord_guild, user_name, f"添加缓存音频：{cached_audio.get_title()}")
    return {"ok": True, "started": started, "audio": audio_to_dict(cached_audio), "state": guild_state(discord_guild, current_guild)}


async def search_all(query: str, source: str = "all", query_num: int = 6) -> List[dict]:
    """
    在支持的平台同时搜索
    """
    jobs = []
    per_site = query_num if source != "all" else max(3, query_num // 2)
    if source in ("all", "bilibili"):
        jobs.append(bilibili.search(query, query_num=per_site))
    if source in ("all", "youtube"):
        jobs.append(ytdlp.youtube_search(query, query_num=per_site))
    if source in ("all", "netease"):
        jobs.append(native_music.search(query, "netease", per_site))
    if source in ("all", "qq"):
        jobs.append(native_music.search(query, "qq", per_site))
    results = []
    for result in await asyncio.gather(*jobs, return_exceptions=True):
        if isinstance(result, Exception):
            await console.on_error(result)
            continue
        results.extend(result)
    return results


async def play_bilibili(ctx: discord.ApplicationContext, link_type: LinkType, url, response = None, maximum_retry: int = 4):
    """
    下载并播放来自Bilibili的视频的音频

    :param ctx: 指令原句
    :param link_type: 链接类型
    :param url: 链接
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
    if link_type is not LinkType.BILIBILI_BVID:
        bvid = utils.get_bvid_from_url(url)
        if bvid is None:
            await embed_eos(ctx, response, author_name=f"无效的{link_type.label}", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
            await console.rp(f"{url} 为无效的{link_type.label}", ctx.guild, message_type=utils.PrintType.ERROR, print_head=True)
            return
    else:
        bvid = url

    # 获取Bilibili视频信息
    info_result = await result_check(await bilibili.get_info(bvid))
    info_dict = info_result.result
    if not info_result or info_dict is None:
        warning_description = f"信息获取失败：{info_result.message}"
        if info_result.retryable:
            warning_description += "，请稍后再试"
        await embed_eos(ctx, response, author_name=warning_description, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
        return

    # 单一视频 bilibili_single 与 合集视频 bilibili_collection
    if info_dict["videos"] == 1:
        new_result = await result_check(await audio_lib_main.download_bilibili(info_dict, DownloadType.BILIBILI_SINGLE, 0))
        new_audio = new_result.result

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
            if isinstance(new_result.exception, errors.StorageFull):
                await embed_eos(ctx, response, author_name=f"机器人当前处理音频过多，请稍后再试", author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
            elif new_result.retryable:
                # 如果不重试直接发送错误与稍后再试
                if maximum_retry < 1:
                    await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result.message + "，请稍后再试", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
                # 如果重试
                else:
                    retry_counter = 0
                    while retry_counter < maximum_retry:
                        retry_counter += 1

                        await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result.message + f"：第 {retry_counter} 次重试中", colour=orange, author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename))

                        new_result = await result_check(await audio_lib_main.download_bilibili(info_dict, DownloadType.BILIBILI_SINGLE, 0))
                        new_audio = new_result.result

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
                        await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result.message + "，请稍后再试", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))

            else:
                await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result.message, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))

        # 合集视频 bilibili_collection
        if "ugc_season" in info_dict:
            menu = CheckCollectionMenu(ctx, DownloadType.BILIBILI_COLLECTION, info_dict, response=response)
            await menu.init_respond(ephemeral=True)

    # 分P视频 bilibili_p
    else:
        p_info_list = []
        for item in info_dict["pages"]:
            p_title = item["part"]
            p_time_str = utils.convert_duration_to_str(item["duration"])
            p_info_list.append((p_title, p_time_str))

        menu_list = utils.make_playlist_page(p_info_list, 10, {None: "> "}, {}, escape_markdown=True)
        menu = EpisodeSelectMenu(ctx, DownloadType.BILIBILI_P, info_dict, menu_list, "哔哩哔哩分P", list_title=info_dict["title"])
        await menu.init_eos(response=response, silent=True)
        return


async def music_service_info(handler: DownloadHandler, link_type: LinkType, url: str) -> Result:
    """
    获取音乐平台链接的信息（内置接口或go-music-api），两者返回的结构一致
    """
    if handler is DownloadHandler.NATIVE:
        return await native_music.get_info(url, link_type.platform)
    return await go_music.get_info(go_music_url, url, sources=go_music.PLATFORM_SOURCE_MAP[link_type.platform])


async def music_service_download(handler: DownloadHandler, song: dict, download_type: DownloadType) -> Result:
    if handler is DownloadHandler.NATIVE:
        return await audio_lib_main.download_native(song, download_type)
    return await audio_lib_main.download_go_music(song, download_type)


async def play_go_music(ctx: discord.ApplicationContext, link_type: LinkType, url, response = None, maximum_retry: int = 4, handler: DownloadHandler = DownloadHandler.GO_MUSIC_API):
    """
    下载并播放音乐平台的音频（内置接口或go-music-api）

    :param ctx: 指令原句
    :param link_type: 链接类型
    :param url: 链接
    :param response: 用于编辑的加载信息
    :param maximum_retry: 下载失败时的最大重试次数
    :param handler: 使用的下载器（DownloadHandler.NATIVE 或 DownloadHandler.GO_MUSIC_API）
    :return: 播放的音频（如果为播放列表或获取失败则返回None）
    """
    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    icon_list_filename = "todo_list_in_reveal_animated_0ms_100px.gif"
    icon_loading_filename = "hourglass_hover_rotation_animated_1000ms_infinite_30px.gif"
    icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"

    # 如处理哔哩哔哩内容，则提取为BV号
    if link_type.platform is MediaPlatform.BILIBILI:
        url = utils.get_bvid_from_url(url)

    # 提取信息
    info_result = await result_check(await music_service_info(handler, link_type, url))
    info_dict = info_result.result
    if info_dict is None:
        warning_description = f"信息获取失败：{info_result.message}"
        if info_result.retryable:
            warning_description += "，请稍后再试"
        await embed_eos(ctx, response, author_name=warning_description, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
        return

    # 单曲 SINGLE
    if info_result.extra["type"] == "song":
        try:
            download_type = DownloadType[f"{str(link_type.platform.name)}_SINGLE"]
        except KeyError as e:
            await embed_eos(ctx, response, author_name="不支持此下载类型", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
            return
        new_result = await result_check(await music_service_download(handler, info_dict["songs"][0], download_type))
        new_audio = new_result.result

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
            if isinstance(new_result.exception, errors.StorageFull):
                await embed_eos(ctx, response, author_name=f"机器人当前处理音频过多，请稍后再试", author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
            elif new_result.retryable:
                # 如果不重试直接发送错误与稍后再试
                if maximum_retry < 1:
                    await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result.message + "，请稍后再试", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
                # 如果重试
                else:
                    retry_counter = 0
                    while retry_counter < maximum_retry:
                        retry_counter += 1

                        await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result.message + f"：第 {retry_counter} 次重试中", colour=orange, author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename))

                        new_result = await result_check(await music_service_download(handler, info_dict["songs"][0], download_type))
                        new_audio = new_result.result

                        # 如果音频加载成功
                        if new_audio is not None:
                            # 如果当前播放列表为空
                            if current_playlist.is_empty() and not voice_client.is_playing():
                                await play_audio(ctx, new_audio, response=response)
                            # 如果播放列表不为空
                            else:
                                await embed_eos(ctx, response, description=f"**{new_audio.get_title()}**", author_name=f"已加入播放列表\u2003[{new_audio.get_duration_str()}]", author_icon_url=icon.url(icon_list_filename), thumbnail=new_audio.get_cover_url(), files=icon_lib.files(icon_list_filename), silent=True)

                            current_playlist.append_audio(new_audio)
                            await console.rp(
                                f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", ctx.guild)

                            await current_guild.refresh_list_view()
                            break

                    # 如果重试最终没有成功
                    if new_audio is None:
                        await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result.message + "，请稍后再试", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))

            else:
                await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result.message, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))

    # 播放列表或专辑 PLAYLIST/ALBUM
    else:
        info_list = []
        for item in info_dict["songs"]:
            current_title = item["name"]
            current_time_str = utils.convert_duration_to_str(item["duration"])
            info_list.append((current_title, current_time_str))

        cover_url = None
        if info_result.extra["playlist_info_dict"] is not None:
            playlist_info_dict = info_result.extra["playlist_info_dict"]
            playlist_title = playlist_info_dict["playlists"][0]["name"]
            cover_url = playlist_info_dict["playlists"][0].get("cover")
            if link_type.platform is MediaPlatform.BILIBILI:
                download_type = DownloadType[f"BILIBILI_COLLECTION"]
            else:
                download_type = DownloadType[f"{link_type.platform.name}_PLAYLIST"]
        elif info_result.extra["album_info_dict"] is not None:
            album_info_dict = info_result.extra["album_info_dict"]
            playlist_title = album_info_dict["albums"][0]["name"]
            cover_url = album_info_dict["albums"][0].get("cover")
            if link_type.platform is MediaPlatform.BILIBILI:
                download_type = DownloadType[f"BILIBILI_COLLECTION"]
            else:
                download_type = DownloadType[f"{link_type.platform.name}_ALBUM"]
        else:
            playlist_title = "播放列表"
            download_type = DownloadType[f"{link_type.platform.name}_SINGLE"]

        menu_list = utils.make_playlist_page(info_list, 10, {None: "> "}, {}, escape_markdown=True)
        menu = EpisodeSelectMenu(ctx, download_type, info_dict, menu_list, list_type=download_type.label, list_title=playlist_title, cover_url=cover_url)
        await menu.init_eos(response=response, silent=True)


async def play_ytdlp(ctx: discord.ApplicationContext, url, response=None, maximum_retry: int = 4) -> None:
    """
    下载并播放来自YouTube的视频的音频

    :param ctx: 指令原句
    :param url: 链接
    :param response: 用于编辑的加载信息
    :param maximum_retry: 下载失败时的最大重试次数
    :return: 播放的音频（如果为播放列表或获取失败则返回None）
    """
    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    icon_list_filename = "todo_list_in_reveal_animated_0ms_100px.gif"
    icon_loading_filename = "hourglass_hover_rotation_animated_1000ms_infinite_30px.gif"
    icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"

    # 提取信息
    info_result = await result_check(await ytdlp.get_info(url))
    info_dict = info_result.result
    if info_dict is None:
        warning_description = f"信息获取失败：{info_result.message}"
        if info_result.retryable:
            warning_description += "，请稍后再试"
        await embed_eos(ctx, response, author_name=warning_description, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
        return

    # 带播放列表信息的独立视频
    if "_type" in info_dict and info_dict["_type"] == "url":
        # 截出播放列表信息
        link_playlist = info_dict["url"]
        info_result_playlist = await result_check(await ytdlp.get_info(link_playlist))
        info_dict_playlist = info_result_playlist.result
        if info_dict_playlist is None:
            warning_description = f"列表信息获取失败：{info_result_playlist.message}，无法查看其所在的播放列表"
            if info_result_playlist.retryable:
                warning_description += "，请稍后再试"
            await embed_eos(ctx, response, author_name=warning_description, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)

        # 重新获取独立视频信息
        url = url[:url.find("&list")]
        info_result = await result_check(await ytdlp.get_info(url))
        info_dict = info_result.result
        if info_dict is None:
            warning_description = f"信息获取失败：{info_result.message}"
            if info_result.retryable:
                warning_description += "，请稍后再试"
            await embed_eos(ctx, response, author_name=warning_description, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
            return

        link_type = DownloadType.YOUTUBE_SINGLE

        # 询问是否查看播放列表
        if info_dict_playlist is not None:
            menu = CheckCollectionMenu(ctx, DownloadType.YOUTUBE_PLAYLIST, info_dict_playlist, response=response)
            await menu.init_respond(ephemeral=True)

    # 播放列表
    elif "_type" in info_dict and info_dict["_type"] == "playlist":
        link_type = DownloadType.YOUTUBE_PLAYLIST

    # 独立视频
    else:
        link_type = DownloadType.YOUTUBE_SINGLE

    # 独立视频 youtube_single
    if link_type is DownloadType.YOUTUBE_SINGLE:
        new_result = await result_check(await audio_lib_main.download_ytdlp(url, info_dict, DownloadType.YOUTUBE_SINGLE))
        new_audio = new_result.result

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
            if isinstance(new_result.exception, errors.StorageFull):
                await embed_eos(ctx, response, author_name=f"机器人当前处理音频过多，请稍后再试", author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
            elif new_result.retryable:
                # 如果不重试直接发送错误与稍后再试
                if maximum_retry < 1:
                    await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result.message + "，请稍后再试", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
                # 如果重试
                else:
                    retry_counter = 0
                    while retry_counter < maximum_retry:
                        retry_counter += 1

                        await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result.message + f"：第 {retry_counter} 次重试中", colour=orange, author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename))

                        new_result = await result_check(await audio_lib_main.download_ytdlp(url, info_dict, DownloadType.YOUTUBE_SINGLE))
                        new_audio = new_result.result

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
                        await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result.message + "，请稍后再试", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))

            else:
                await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result.message, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))

    # 播放列表 youtube_playlist
    elif link_type is DownloadType.YOUTUBE_PLAYLIST:
        ep_info_list = []
        for item in info_dict["entries"]:
            ep_title = item["title"]
            ep_time_str = utils.convert_duration_to_str(item["duration"])
            ep_info_list.append((ep_title, ep_time_str))
        playlist_title = info_dict['title']
        menu_list = utils.make_playlist_page(ep_info_list, 10, {None: "> "}, {}, escape_markdown=True)
        menu = EpisodeSelectMenu(ctx, DownloadType.YOUTUBE_PLAYLIST, info_dict, menu_list, "YouTube播放列表", playlist_title)
        await menu.init_eos(response=response, silent=True)


async def play_netease(ctx: discord.ApplicationContext, link, response=None, maximum_retry: int = 4) -> None:
    """
    下载并播放来自网易云音乐的音频

    :param ctx: 指令原句
    :param link: 链接
    :param response: 用于编辑的加载信息
    :param maximum_retry: 下载失败时的最大重试次数
    :return: 播放的音频（如果为播放列表或获取失败则返回None）
    """
    pass
    # voice_client = ctx.guild.voice_client
    # current_guild = guild_lib.get_guild(ctx)
    # current_playlist = current_guild.get_playlist()
    #
    # icon_list_filename = "todo_list_in_reveal_animated_0ms_100px.gif"
    # icon_loading_filename = "hourglass_hover_rotation_animated_1000ms_infinite_30px.gif"
    # icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"
    #
    # # 截取出yt-dlp可读取的部分（目前已知yt-dlp 2024.07.25不能读取包含/my/m/music/的链接）
    # link = utils.get_legal_netease_url(link)
    #
    # # 先提取信息
    # info_result = await ytdlp.get_info(ctx, link)
    # info_dict = info_result["result"]
    # if info_dict is None:
    #     warning_description = f"[{link}] 信息获取失败：{info_result['message']}"
    #     if info_result["retryable"]:
    #         warning_description += "，请稍后再试"
    #     await embed_eos(ctx, response, author_name=warning_description, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)
    #     return
    #
    # # 播放列表
    # if "_type" in info_dict and info_dict["_type"] == "playlist":
    #     link_type = "netease_playlist"
    #
    # # 独立音频
    # else:
    #     link_type = "netease_single"
    #
    # # 独立音频 netease_single
    # if link_type == "netease_single":
    #     new_result = await audio_lib_main.download_ytdlp(link, info_dict, "netease_single")
    #     new_audio = new_result["result"]
    #
    #     if new_audio is not None:
    #         if current_playlist.is_empty() and not voice_client.is_playing():
    #             await play_audio(ctx, new_audio, response=response)
    #
    #         # 如果列表为空则会有正在播放提示，否则加入列表提示
    #         if not current_playlist.is_empty():
    #             await embed_eos(ctx, response, description=f"**{utils.markdown_escape(new_audio.get_title())}**", author_name=f"已加入播放列表\u2003[{new_audio.get_duration_str()}]", author_icon_url=icon.url(icon_list_filename), thumbnail=new_audio.get_cover_url(), files=icon_lib.files(icon_list_filename), silent=True)
    #
    #         # 添加至服务器播放列表
    #         current_playlist.append_audio(new_audio)
    #         await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", ctx.guild)
    #
    #         await current_guild.refresh_list_view()
    #
    #     else:
    #         if isinstance(new_result["exception"], errors.StorageFull):
    #             await embed_eos(ctx, response, author_name=f"机器人当前处理音频过多，请稍后再试", author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
    #         elif new_result["retryable"]:
    #             # 如果不重试直接发送错误与稍后再试
    #             if maximum_retry < 1:
    #                 await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"] + "，请稍后再试", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
    #             # 如果重试
    #             else:
    #                 retry_counter = 0
    #                 while retry_counter < maximum_retry:
    #                     retry_counter += 1
    #
    #                     await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"] + f"：第 {retry_counter} 次重试中", colour=orange, author_icon_url=icon.url(icon_loading_filename), files=icon_lib.files(icon_loading_filename))
    #
    #                     new_result = await audio_lib_main.download_ytdlp(link, info_dict, "netease_single")
    #                     new_audio = new_result["result"]
    #
    #                     # 如果音频加载成功
    #                     if new_audio is not None:
    #
    #                         # 如果当前播放列表为空
    #                         if current_playlist.is_empty() and not voice_client.is_playing():
    #                             await play_audio(ctx, new_audio, response=response)
    #
    #                         # 如果播放列表不为空
    #                         else:
    #                             await embed_eos(ctx, response, description=f"**{new_audio.get_title()}**", author_name=f"已加入播放列表\u2003[{new_audio.get_duration_str()}]", author_icon_url=icon.url(icon_list_filename), thumbnail=new_audio.get_cover_url(), files=icon_lib.files(icon_list_filename), silent=True)
    #
    #                         current_playlist.append_audio(new_audio)
    #                         await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", ctx.guild)
    #
    #                         await current_guild.refresh_list_view()
    #                         break
    #
    #                 # 如果重试最终没有成功
    #                 if new_audio is None:
    #                     await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"] + "，请稍后再试", colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
    #
    #         else:
    #             await embed_eos(ctx, response, author_name=f"错误：音频获取失败 " + new_result["message"], colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename))
    #
    # # 播放列表 netease_playlist
    # elif link_type == "netease_playlist":
    #     ep_info_list = []
    #     for item in info_dict["entries"]:
    #         ep_title = item["title"]
    #         # ep_info_list内的所有元组只包含ep_title一个元素，不要去掉()内的逗号
    #         ep_info_list.append((ep_title,))
    #     playlist_title = info_dict['title']
    #     menu_list = utils.make_playlist_page(ep_info_list, 10, {None: "> "}, {}, escape_markdown=True)
    #     menu = EpisodeSelectMenu(ctx, "netease_playlist", info_dict, menu_list, "网易云播放列表", playlist_title)
    #     await menu.init_eos(response=response, silent=True)


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
        guild_lib.get_guild(ctx).playback.pause()
        await guild_lib.get_guild(ctx).refresh_list_view()
        await console.rp("暂停播放", ctx.guild)
        if command_call:
            await embed_respond(ctx, author_name="暂停播放", author_icon_url=icon.url(pause_icon_filename), files=icon_lib.files(pause_icon_filename))
        # else:
        #     logger.rp(f"收到pause指令时指令发出者 {ctx.author} 不在机器人所在的频道", ctx.guild)
        #     await ctx.respond(f"您不在{system_setting.value('bot_name')}所在的频道")

    elif voice_client is not None and voice_client.is_paused():
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
            current_guild.playback.resume()
            await console.rp("恢复播放", ctx.guild)
            if command_call:
                await embed_respond(ctx, author_name="恢复播放", author_icon_url=icon.url(resume_icon_filename), files=icon_lib.files(resume_icon_filename))
        else:
            await console.rp(f"收到pause指令时指令发出者 {ctx.author} 不在机器人所在的频道", ctx.guild)
            if command_call:
                await embed_respond(ctx, f"您不在{system_setting.value('bot_name')}所在的频道", silent=True)

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


async def playlist_callback(ctx: discord.ApplicationContext):
    """
    进行自定播放列表的相关的操作
    """
    await guild_lib.check(ctx, audio_lib_main)

    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    await ctx.respond("指令已注册")


def skip_current(discord_guild: discord.Guild, current_guild: guild.Guild) -> None:
    """
    跳过列表首位（正在播放）的音频，如果跳过前处于暂停状态，则下一个音频开始后保持暂停
    """
    if is_streaming(discord_guild):
        current_guild.playback.pause_after_start = discord_guild.voice_client.is_paused()
        request_stop(discord_guild, current_guild, "skip")
    else:
        current_guild.add_history(current_guild.get_playlist().pop_audio(0))


def apply_volume(discord_guild: discord.Guild, current_guild: guild.Guild, volume: float) -> float:
    """
    设置服务器音量并立即应用到正在播放（包括暂停中）的音频
    """
    current_guild.set_voice_volume(volume)
    voice_client = discord_guild.voice_client
    if voice_client is not None and isinstance(voice_client.source, discord.PCMVolumeTransformer):
        voice_client.source.volume = current_guild.get_voice_volume() / 100.0
    return current_guild.get_voice_volume()


async def skip_callback(ctx, first_index: Union[int, str, None] = None, second_index: Union[int, None] = None, command_call: bool = False, refresh_view: bool = True):
    """
    使机器人跳过指定的歌曲
    *注意*：此方法输入的index从1开始，不是0

    :param ctx: 指令原句
    :param first_index: 跳过起始曲目的序号（从1开始）
    :param second_index: 跳过最终曲目的序号（包含）
    :param command_call: 该函数是否是由用户指令调用
    :param refresh_view: 是否刷新播放列表菜单
    :return:
    """
    await guild_lib.check(ctx, audio_lib_main)

    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    icon_skip_filename = "play_forward_hover_pinch_animated_0ms_100px.gif"
    icon_error_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"

    async def reply(**kwargs):
        if command_call:
            await embed_respond(ctx, **kwargs)
        else:
            await embed_send(ctx, **kwargs)

    async def reply_error(message: str):
        await console.rp(f"用户 {ctx.author} 的skip指令参数错误：{message}", ctx.guild)
        await reply(author_name=message, colour=orange, author_icon_url=icon.url(icon_error_filename), files=icon_lib.files(icon_error_filename), silent=True)

    try:
        first_number = None if first_index is None or first_index == "*" else int(first_index)
        second_number = None if second_index is None else int(second_index)
    except (TypeError, ValueError):
        await reply_error("参数错误")
        return

    if current_playlist.is_empty():
        await reply(description="当前播放列表已为空", silent=True)

    elif first_index == "*":
        await clear_callback(ctx)
        return

    # 跳过当前音频（不输入参数，或只跳过第1个）
    elif second_number is None and (first_number is None or first_number == 1):
        current_audio = current_playlist.get_audio(0)
        title = current_audio.get_title()
        duration_str = current_audio.get_duration_str()
        skip_current(ctx.guild, current_guild)

        await console.rp(f"第1个音频 {title} 已被用户 {ctx.user} 移出播放列表", ctx.guild)
        await reply(description=f"**{utils.markdown_escape(title)}**", author_name=f"已跳过当前音频 [{duration_str}]", author_icon_url=icon.url(icon_skip_filename), files=icon_lib.files(icon_skip_filename))

    # 输入1个参数的情况
    elif second_number is None:
        if not 1 <= first_number <= len(current_playlist):
            await reply_error("选择的序号不在范围内")
        else:
            select_audio = current_playlist.get_audio(first_number - 1)
            title = select_audio.get_title()
            duration_str = select_audio.get_duration_str()
            current_playlist.remove_audio(first_number - 1)

            await console.rp(f"第{first_number}个音频 {title} 已被用户 {ctx.user} 移出播放列表", ctx.guild)
            await reply(description=f"**{utils.markdown_escape(title)}**", author_name=f"第 {first_number} 个音频已被移出播放列表 [{duration_str}]", author_icon_url=icon.url(icon_skip_filename), files=icon_lib.files(icon_skip_filename))

    # 输入2个参数的情况
    elif first_number is not None and first_number < second_number:
        if first_number < 1 or second_number > len(current_playlist):
            await reply_error("选择的序号不在范围内")
        else:
            # 先从后往前移除，如果包含正在播放的音频，最后再跳过
            for i in range(second_number, max(first_number, 2) - 1, -1):
                current_playlist.remove_audio(i - 1)
            if first_number == 1:
                skip_current(ctx.guild, current_guild)

            await console.rp(f"第{first_number}到第{second_number}个音频被用户 {ctx.author} 移出播放列表", ctx.guild)
            await reply(author_name=f"第 {first_number} 到第 {second_number} 个音频已被移出播放列表", author_icon_url=icon.url(icon_skip_filename), files=icon_lib.files(icon_skip_filename))

    else:
        await reply_error("参数错误")

    if refresh_view:
        await current_guild.refresh_list_view()


async def move_callback(ctx, from_number: Union[int, None] = None, to_number: Union[int, None] = None):
    await guild_lib.check(ctx, audio_lib_main)

    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    icon_filename = "left_right_in_reveal_animated_0ms_100px.gif"

    if from_number is None or to_number is None:
        await embed_respond(ctx, "请输入想要移动的歌曲序号以及想要移动到的位置", silent=True)

    # 两个参数相同的情况
    elif from_number == to_number:
        await embed_respond(ctx, "您搁这儿搁这儿呢（序号相同）", colour=orange, silent=True)

    elif not 1 <= from_number <= len(current_playlist) or not 1 <= to_number <= len(current_playlist):
        await embed_respond(ctx, "选择的序号不在范围内", colour=orange, silent=True)

    else:
        title = current_playlist.get_audio(from_number - 1).get_title()
        current_playlist.move_audio(from_number - 1, to_number - 1)

        # 移动了正在播放的音频，或将音频移动到了首位：从新的首位音频开始播放
        if from_number == 1 or to_number == 1:
            if is_streaming(ctx.guild):
                current_guild.playback.pause_after_start = ctx.guild.voice_client.is_paused()
                request_stop(ctx.guild, current_guild, "restart")

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

    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    current_playlist.remove_all()
    request_stop(ctx.guild, current_guild, "hold")

    await console.rp(f"用户 {ctx.author} 已清空所在服务器的播放列表", ctx.guild)
    clear_icon_filename = "bin_hover_empty_animated_0ms_100px.gif"
    await embed_respond(ctx, author_name="播放列表已清空", author_icon_url=icon.url(clear_icon_filename), files=icon_lib.files(clear_icon_filename))
    await current_guild.refresh_list_view()


async def volume_callback(ctx: discord.ApplicationContext, volume_num=None) -> None:
    await guild_lib.check(ctx, audio_lib_main)
    current_guild = guild_lib.get_guild(ctx)
    current_volume = current_guild.get_voice_volume()

    icon_filename = "speaker_hover_pinch_animated_0ms_100px.gif"
    icon_mute_filename = "speaker_hover_mute_animated_0ms_100px.gif"

    if volume_num is None:
        await embed_respond(ctx, author_name=f"当前音量为：{current_volume}%", author_icon_url=icon.url(icon_filename), files=icon_lib.files(icon_filename), silent=True)
        return

    if volume_num in ("up", "u", "+", "＋"):
        new_volume = min(200.0, current_volume + 20.0)
        action = "提升至"
    elif volume_num in ("down", "d", "-"):
        new_volume = max(0.0, current_volume - 20.0)
        action = "降低至"
    else:
        try:
            new_volume = float(int(float(volume_num)))
        except ValueError:
            new_volume = -1.0
        if new_volume > 200.0 or new_volume < 0.0:
            await embed_respond(ctx, "请输入up或down来提升或降低音量或一个0-200的数字来设置音量", silent=True)
            return
        action = "设置为"

    new_volume = apply_volume(ctx.guild, current_guild, new_volume)
    await console.rp(f"用户 {ctx.author} 已将音量设置为 {new_volume}%", ctx.guild)

    target_icon = icon_mute_filename if new_volume == 0.0 else icon_filename
    await embed_respond(ctx, author_name=f"将音量{action}：{new_volume}%", author_icon_url=icon.url(target_icon), files=icon_lib.files(target_icon))
    await current_guild.refresh_list_view()


async def radio_callback(ctx: discord.ApplicationContext):
    """
    电台模式
    """
    await guild_lib.check(ctx, audio_lib_main)

    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    await ctx.respond("指令已注册")


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


def parse_index_expression(text: str, maximum: int) -> Tuple[List[int], List[str]]:
    """
    解析序号表达式，例如 "1-5, 8, 12-10" -> [1, 2, 3, 4, 5, 8, 12, 11, 10]
    分隔符：英文/中文逗号、顿号、分号、空格；范围符号：- ~ ～ — – 到（起点大于终点时为倒序）
    返回 (按输入顺序去重后的序号列表, 无效的片段列表)，序号从1开始
    """
    text = re.sub(r"\s*(-|~|～|—|–|到)\s*", r"\1", str(text or "").strip())
    result: List[int] = []
    seen: Set[int] = set()
    invalid: List[str] = []
    for token in re.split(r"[,，、;；\s]+", text):
        if token == "":
            continue
        range_match = re.fullmatch(r"(\d+)(?:-|~|～|—|–|到)(\d+)", token)
        if range_match:
            start_num, end_num = int(range_match.group(1)), int(range_match.group(2))
            step = 1 if end_num >= start_num else -1
            numbers = range(start_num, end_num + step, step)
        elif token.isdigit():
            numbers = [int(token)]
        else:
            invalid.append(token)
            continue
        out_of_range = False
        for number in numbers:
            if 1 <= number <= maximum:
                if number not in seen:
                    seen.add(number)
                    result.append(number)
            else:
                out_of_range = True
        if out_of_range:
            invalid.append(token)
    return result, invalid


def compress_indexes(numbers: List[int], limit: int = 300) -> str:
    """
    将序号列表压缩为范围文本，例如 [1, 2, 3, 7, 10, 9] -> "1-3, 7, 10-9"
    """
    parts: List[str] = []
    i = 0
    while i < len(numbers):
        j = i
        step = 0
        if i + 1 < len(numbers) and abs(numbers[i + 1] - numbers[i]) == 1:
            step = numbers[i + 1] - numbers[i]
            while j + 1 < len(numbers) and numbers[j + 1] - numbers[j] == step:
                j += 1
        parts.append(f"{numbers[i]}-{numbers[j]}" if j > i else f"{numbers[i]}")
        i = j + 1
    text = ", ".join(parts)
    if len(text) > limit:
        text = text[:limit].rsplit(",", 1)[0] + ", …"
    return text


async def _respond_ephemeral(interaction: discord.Interaction, message: str) -> None:
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException:
        pass


async def wait_for_track_switch(current_guild: guild.Guild, waiter: Optional[asyncio.Future], timeout: float = 1.5) -> None:
    """
    等待播放结束回调处理完毕（通常只需几十毫秒），使界面在一次刷新中就显示新的播放状态
    """
    if waiter is None:
        return
    try:
        await asyncio.wait_for(asyncio.shield(waiter), timeout)
    except asyncio.TimeoutError:
        pass


class PlaylistMenu(View):

    PAGE_SIZE = 10

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
        self.page_count = 1
        self.occur_time = utils.ctime_str()

        self.overrode = False
        self.time_outed = False

        self.icon_filename = "questionnaire_in_reveal_animated_0ms_50px.gif"
        self.embed = discord.Embed(
            colour=discord.Color.dark_teal(),
            title=f"{self.playlist.get_name()}"
        )
        self.embed.set_author(name="播放列表", icon_url=icon.url(self.icon_filename))

        self.original_msg = None
        self._last_signature = None

        self.refresh_pages()

    def _button(self, custom_id: str) -> Optional[discord.ui.Button]:
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == custom_id:
                return item
        return None

    async def init_respond(self, ephemeral: bool = False, silent: bool = False):
        files = icon_lib.files(self.icon_filename)
        original_msg = await self.ctx.respond(content=None, embed=self.embed, view=self, ephemeral=ephemeral, silent=silent, files=files)
        _remember_attachments(original_msg, files)
        self._last_signature = self._signature()
        await self.set_original_msg(original_msg)

    async def init_eos(self, response, silent: bool = False):
        files = icon_lib.files(self.icon_filename)
        original_msg = await eos(self.ctx, response, content=None, silent=silent, embed=self.embed, view=self, files=files)
        self._last_signature = self._signature()
        await self.set_original_msg(original_msg)

    async def refresh_menu(self):
        """
        由服务器的合并刷新调用，内容没有变化时不编辑消息
        """
        if self.overrode or self.time_outed or self.original_msg is None:
            return
        self.refresh_pages()
        signature = self._signature()
        if signature == self._last_signature:
            return
        self._last_signature = signature
        files = icon_lib.files(self.icon_filename)
        await eos(self.ctx, response=self.original_msg, content=None, embed=self.embed, view=self, files=files)

    async def _respond(self, interaction: discord.Interaction):
        """
        使用交互的首次回应直接编辑菜单（一次请求完成，图标附件保持不变无需重新上传）
        """
        self.refresh_pages()
        self._last_signature = self._signature()
        if interaction.response.is_done():
            await interaction.message.edit(content=None, embed=self.embed, view=self)
        else:
            await interaction.response.edit_message(content=None, embed=self.embed, view=self)

    def _signature(self) -> tuple:
        description = re.sub(r"<t:\d+:R>", "", self.embed.description or "")
        buttons = tuple((item.custom_id, item.label, item.disabled) for item in self.children if isinstance(item, discord.ui.Button))
        return description, self.embed.footer.text if self.embed.footer else None, buttons

    def _now_playing_line(self, voice_client) -> str:
        playback_state = self.guild.playback
        current_audio = self.playlist.get_audio(0)
        if voice_client is None:
            return "⏹ 不在语音频道中"
        if current_audio is None or not playback_state.is_active():
            return "⏹ 待机中"
        position = playback_state.position()
        duration = current_audio.get_duration()
        bar = playback.progress_bar(position, duration)
        time_str = f"{utils.convert_duration_to_str(int(position))} / {current_audio.get_duration_str()}"
        if voice_client.is_paused():
            return f"⏸ 已暂停\u2003{bar}\u2003{time_str}"
        end_timestamp = int(time.time() + playback_state.remaining())
        return f"▶ 正在播放\u2003{bar}\u2003{time_str}\u2003（<t:{end_timestamp}:R>结束）"

    def refresh_pages(self):
        info_list = self.playlist.get_list_info()
        self.page_count = max(1, (len(info_list) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.page_num = max(0, min(self.page_num, self.page_count - 1))

        # 生成播放列表主体文本
        pages = utils.make_playlist_page(
            info_list,
            self.PAGE_SIZE,
            {None: ">       ", 0: "> ▶  **"},
            {0: "**"},
            title_markdown_bold=False,
            escape_markdown=True,
        )
        page_text = pages[self.page_num] if len(pages) > 0 else "> **当前播放列表为空**\n"

        voice_client = self.ctx.guild.voice_client
        voice_client_status = get_voice_client_status(voice_client)
        play_mode = self.guild.get_play_mode()

        # 更新按钮状态
        self._button("button_play_pause").label = "▌▌" if voice_client_status == 1 else "▶"
        self._button("button_next_audio").disabled = self.playlist.is_empty()
        self._button("button_previous_audio").disabled = len(self.guild.get_playedlist()) == 0
        self._button("button_play_mode").label = playback.PLAY_MODE_NAMES.get(play_mode, "播放模式")
        self._button("button_previous_page").disabled = self.page_num == 0
        self._button("button_next_page").disabled = self.page_num >= self.page_count - 1

        # 设置嵌套元素
        # 使用\u2003全角空格加宽间距
        self.embed.description = (
            f"{self._now_playing_line(voice_client)}\n"
            f"列表长度：{len(self.playlist)}\u2003\u2003总时长：{self.playlist.get_duration_str()}\u2003\u2003"
            f"音量：{int(self.guild.get_voice_volume())}%\u2003\u2003状态：{get_voice_client_status_str(voice_client_status)}\n\n"
            f"{page_text}"
        )
        self.embed.timestamp = utils.ctime_datetime()
        self.embed.set_footer(text=f"第[{self.page_num + 1}]页，共[{self.page_count}]页")

    @discord.ui.button(label="▍◀", style=discord.ButtonStyle.grey, custom_id="button_previous_audio", row=1)
    async def button_previous_audio_callback(self, button, interaction):
        discord_guild = self.ctx.guild
        previous_audio = self.guild.pop_history()
        if previous_audio is None:
            await self._respond(interaction)
            return

        self.playlist.insert_audio(previous_audio, 0)
        waiter = self.guild.playback.add_end_waiter() if is_streaming(discord_guild) else None
        if waiter is not None:
            request_stop(discord_guild, self.guild, "restart")
        elif start_stream(discord_guild, self.guild, previous_audio):
            bot.loop.create_task(announce_now_playing(self.guild, previous_audio))
        await console.rp(f"用户 {interaction.user} 播放上一首：{previous_audio.get_title()}", discord_guild)

        await wait_for_track_switch(self.guild, waiter)
        await self._respond(interaction)

    @discord.ui.button(label="▶▌▌", style=discord.ButtonStyle.grey, custom_id="button_play_pause", row=1)
    async def button_play_pause_callback(self, button, interaction):
        voice_client = self.ctx.guild.voice_client

        # 暂停与继续为即时操作，直接在首次回应中刷新菜单
        if voice_client is not None and voice_client.is_playing():
            voice_client.pause()
            self.guild.playback.pause()
            await console.rp(f"用户 {interaction.user} 暂停播放", self.ctx.guild)
            await self._respond(interaction)
        elif voice_client is not None and voice_client.is_paused():
            voice_client.resume()
            self.guild.playback.resume()
            await console.rp(f"用户 {interaction.user} 恢复播放", self.ctx.guild)
            await self._respond(interaction)
        else:
            # 需要加入频道或启动播放，耗时可能较长，先回应交互，完成后由刷新机制更新菜单
            await interaction.response.defer()
            await resume_callback(self.ctx, command_call=False)
            await self.guild.refresh_list_view()

    @discord.ui.button(label="▶ ▍", style=discord.ButtonStyle.grey, custom_id="button_next_audio", row=1)
    async def button_next_audio_callback(self, button, interaction):
        discord_guild = self.ctx.guild
        if self.playlist.is_empty():
            await self._respond(interaction)
            return

        current_audio = self.playlist.get_audio(0)
        waiter = self.guild.playback.add_end_waiter() if is_streaming(discord_guild) else None
        skip_current(discord_guild, self.guild)
        await console.rp(f"第1个音频 {current_audio.get_title()} 已被用户 {interaction.user} 跳过", discord_guild)

        await wait_for_track_switch(self.guild, waiter)
        await self._respond(interaction)

    @discord.ui.button(label="播放模式", style=discord.ButtonStyle.grey, custom_id="button_play_mode", row=1)
    async def button_play_mode_callback(self, button, interaction):
        new_mode = (self.guild.get_play_mode() + 1) % len(playback.PLAY_MODE_NAMES)
        self.guild.set_play_mode(new_mode)
        await console.rp(f"用户 {interaction.user} 将播放模式设置为：{playback.PLAY_MODE_NAMES[new_mode]}", self.ctx.guild)
        await self._respond(interaction)

    @discord.ui.button(label="上一页", style=discord.ButtonStyle.grey, custom_id="button_previous_page", row=2)
    async def button_previous_page_callback(self, button, interaction):
        self.page_num = max(0, self.page_num - 1)
        await self._respond(interaction)

    @discord.ui.button(label="下一页", style=discord.ButtonStyle.grey, custom_id="button_next_page", row=2)
    async def button_next_page_callback(self, button, interaction):
        self.page_num = min(self.page_count - 1, self.page_num + 1)
        await self._respond(interaction)

    @discord.ui.button(label="刷新", style=discord.ButtonStyle.grey, custom_id="button_refresh", row=2)
    async def button_refresh_callback(self, button, interaction):
        await self._respond(interaction)

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.grey, custom_id="button_close", row=2)
    async def button_close_callback(self, button, interaction):
        # 将此View从guild_active_views中移除
        guild_active_views = self.guild.get_active_views()
        if guild_active_views.get("playlist_menu_view") is self:
            guild_active_views["playlist_menu_view"] = None

        self.overrode = True
        self.stop()
        await interaction.response.defer()
        if not await delete_response(self.original_msg):
            await delete_response(interaction.message)

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
            self.stop()
            await delete_response(self.original_msg)
            await console.rp(f"{self.occur_time}生成的播放列表菜单已删除", self.ctx.guild)

    async def on_timeout(self):
        self.time_outed = True
        # 超时程序，如果已被覆盖则不再执行
        if not self.overrode:
            # 将此View从guild_active_views中移除
            guild_active_views = self.guild.get_active_views()
            if guild_active_views.get("playlist_menu_view") is self:
                guild_active_views["playlist_menu_view"] = None

            await delete_response(self.original_msg)
            await console.rp(f"{self.occur_time}生成的播放列表菜单已超时(超时时间为{self.timeout}秒)", self.ctx.guild)


class IndexInputModal(discord.ui.Modal):
    def __init__(self, menu: "EpisodeSelectMenu"):
        self.menu = menu
        total = len(menu.entries)
        super().__init__(
            discord.ui.InputText(
                label=f"要播放的序号（共{total}个，提交后立即开始添加）"[:45],
                placeholder="例如：1-5, 8, 12-10（起点大于终点为倒序）",
                value=compress_indexes(menu.ordered_selection(), limit=200) or None,
                max_length=400,
                required=True,
            ),
            title="输入序号",
            timeout=600,
        )

    async def callback(self, interaction: discord.Interaction):
        if self.menu.finish:
            await _respond_ephemeral(interaction, "该选择菜单已结束")
            return
        numbers, invalid = parse_index_expression(self.children[0].value, len(self.menu.entries))
        if len(numbers) == 0:
            hint = f"：{', '.join(invalid[:5])}" if invalid else ""
            await _respond_ephemeral(interaction, f"没有识别到有效的序号{hint}（有效范围：1 - {len(self.menu.entries)}）")
            return
        self.menu.selected = numbers
        self.menu.custom_order = True
        if invalid:
            await console.rp(f"序号输入中的无效部分已被忽略：{', '.join(invalid)}", self.menu.ctx.guild)
        await self.menu.confirm(interaction)


class EpisodeSelectMenu(View):

    PAGE_SIZE = 10

    def __init__(self, ctx, download_type: DownloadType, info_dict, menu_list=None, list_type=None, list_title=None, cover_url: Optional[str] = None, timeout=300):
        """
        初始化分集选择菜单

        :param ctx: 指令原句
        :param download_type: 播放源的下载类型
        :param info_dict: 播放源的信息字典
        :param menu_list: （已不再使用，保留以兼容旧调用）
        :param timeout: 超时时间（单位：秒）
        :param list_type: 播放列表的类型（展示用）
        :param list_title: 播放列表的标题（展示用）
        :return:
        """
        super().__init__(timeout=timeout)
        self.ctx: discord.ApplicationContext = ctx

        self.list_type = list_type if list_type is not None else "播放列表"
        self.list_title = list_title
        self.download_type = download_type
        self.handler = resource_classifier.handler(download_type)
        self.info_dict = info_dict
        self.page_num = 0
        self.occur_time = utils.ctime_str()

        # 已选择的序号（从1开始），custom_order为True时按输入顺序播放，否则按序号顺序播放
        self.selected: List[int] = []
        self.custom_order = False

        self.original_msg = None
        self.embed = None
        self.icon_filename = None

        # 标记是否已经操作完选择页面
        self.finish = False
        self._last_progress_edit = 0.0

        self.entries = self._build_entries()
        self.page_count = max(1, (len(self.entries) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)

        # 封面设置
        self.cover_url = cover_url
        if self.cover_url is None:
            if self.download_type in (DownloadType.BILIBILI_P, DownloadType.BILIBILI_COLLECTION) and "pic" in info_dict:
                self.cover_url = info_dict["pic"]
            elif self.download_type is DownloadType.YOUTUBE_PLAYLIST and len(info_dict.get("thumbnails") or []) > 0:
                for thumbnail in reversed(info_dict["thumbnails"]):
                    if "url" in thumbnail:
                        self.cover_url = thumbnail["url"]
                        break

        # 当前页的多选下拉菜单
        self.select_menu = discord.ui.Select(placeholder="选择要播放的音频（可多选）", min_values=0, max_values=1, options=[discord.SelectOption(label="-")], row=0)
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

        self.refresh_pages()

    def _build_entries(self) -> List[Tuple[str, Optional[int]]]:
        """
        返回 (标题, 时长秒数) 列表
        """
        if self.handler in (DownloadHandler.GO_MUSIC_API, DownloadHandler.NATIVE):
            items = [(item.get("name"), item.get("duration")) for item in self.info_dict.get("songs") or []]
        elif self.handler is DownloadHandler.BILIBILI_API_PYTHON and self.download_type is DownloadType.BILIBILI_P:
            items = [(item.get("part"), item.get("duration")) for item in self.info_dict.get("pages") or []]
        elif self.handler is DownloadHandler.BILIBILI_API_PYTHON and self.download_type is DownloadType.BILIBILI_COLLECTION:
            episodes = self.info_dict["ugc_season"]["sections"][0]["episodes"]
            items = [(item.get("title"), (item.get("arc") or {}).get("duration")) for item in episodes]
        elif self.handler is DownloadHandler.YT_DLP:
            items = [((item or {}).get("title"), (item or {}).get("duration")) for item in self.info_dict.get("entries") or []]
        else:
            items = []
        return [(str(title) if title else "未知标题", int(duration) if duration else None) for title, duration in items]

    def ordered_selection(self) -> List[int]:
        # 注意：本模块中的 /list 指令函数覆盖了内置的list()，此处使用切片复制
        return self.selected[:] if self.custom_order else sorted(self.selected)

    def _button(self, custom_id: str) -> Optional[discord.ui.Button]:
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == custom_id:
                return item
        return None

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
        if self.finish:
            return

        self.page_num = max(0, min(self.page_num, self.page_count - 1))
        start = self.page_num * self.PAGE_SIZE
        end = min(start + self.PAGE_SIZE, len(self.entries))
        selected_set = set(self.selected)

        # 下拉菜单：当前页的音频
        options = []
        for number in range(start + 1, end + 1):
            title, duration = self.entries[number - 1]
            options.append(discord.SelectOption(
                label=f"[{number}] {title}"[:100],
                value=str(number),
                description=utils.convert_duration_to_str(duration) if duration else None,
                default=number in selected_set,
            ))
        if len(options) == 0:
            options = [discord.SelectOption(label="（空）", value="0")]
            self.select_menu.disabled = True
        self.select_menu.options = options
        self.select_menu.max_values = len(options)
        self.select_menu.placeholder = f"选择第 {self.page_num + 1} 页中要播放的音频（可多选）"

        # 按钮状态
        self._button("button_previous_page").disabled = self.page_num == 0
        self._button("button_next_page").disabled = self.page_num >= self.page_count - 1
        self._button("button_confirm").label = f"确定（{len(self.selected)}）" if len(self.selected) > 0 else "确定"
        self._button("button_confirm").disabled = len(self.selected) == 0
        self._button("button_clear").disabled = len(self.selected) == 0

        lines = []
        for number in range(start + 1, end + 1):
            title, duration = self.entries[number - 1]
            mark = "✅" if number in selected_set else "▫️"
            duration_str = f" [{utils.convert_duration_to_str(duration)}]" if duration else ""
            lines.append(f"{mark} `{number:>3}` {utils.markdown_escape(title)}{duration_str}")

        self.embed = discord.Embed(
            colour=discord.Color.dark_teal(),
            title=self.list_title or "",
            description="\n".join(lines) if lines else "> 列表为空",
            timestamp=utils.ctime_datetime(),
        )
        if len(self.selected) > 0:
            selected_value = f"{len(self.selected)} 个：{compress_indexes(self.ordered_selection())}"
        else:
            selected_value = "在下拉菜单中选择（翻页后选择会保留），或点击「⌨ 输入序号」直接输入范围"
        self.embed.add_field(name="已选择", value=selected_value[:1024], inline=False)
        self.embed.set_author(name=f"{self.list_type}")
        self.embed.set_footer(text=f"第[{self.page_num + 1}]页，共[{self.page_count}]页 · 共 {len(self.entries)} 个")
        if self.cover_url is not None:
            self.embed.set_thumbnail(url=self.cover_url)

    async def _respond(self, interaction: discord.Interaction):
        self.refresh_pages()
        await interaction.response.edit_message(content=None, embed=self.embed, view=self)

    async def set_original_msg(self, response: Union[discord.Message, discord.InteractionMessage, None]):
        """
        创建View后调用，传入发送该View的Interaction
        """
        self.original_msg = response

    async def select_callback(self, interaction: discord.Interaction):
        start = self.page_num * self.PAGE_SIZE
        page_numbers = set(range(start + 1, min(start + self.PAGE_SIZE, len(self.entries)) + 1))
        chosen = [int(value) for value in (self.select_menu.values or []) if value.isdigit() and int(value) in page_numbers]
        # 保留其他页的选择，替换当前页的选择
        self.selected = [number for number in self.selected if number not in page_numbers] + sorted(chosen)
        await self._respond(interaction)

    @discord.ui.button(label="◀ 上一页", style=discord.ButtonStyle.grey, custom_id="button_previous_page", row=1)
    async def button_previous_callback(self, button, interaction):
        self.page_num = max(0, self.page_num - 1)
        await self._respond(interaction)

    @discord.ui.button(label="下一页 ▶", style=discord.ButtonStyle.grey, custom_id="button_next_page", row=1)
    async def button_next_callback(self, button, interaction):
        self.page_num = min(self.page_count - 1, self.page_num + 1)
        await self._respond(interaction)

    @discord.ui.button(label="⌨ 输入序号", style=discord.ButtonStyle.blurple, custom_id="button_input", row=1)
    async def button_input_callback(self, button, interaction):
        await interaction.response.send_modal(IndexInputModal(self))

    @discord.ui.button(label="全选本页", style=discord.ButtonStyle.grey, custom_id="button_select_page", row=1)
    async def button_select_page_callback(self, button, interaction):
        start = self.page_num * self.PAGE_SIZE
        for number in range(start + 1, min(start + self.PAGE_SIZE, len(self.entries)) + 1):
            if number not in self.selected:
                self.selected.append(number)
        await self._respond(interaction)

    @discord.ui.button(label="▶ 播放全部", style=discord.ButtonStyle.green, custom_id="button_all", row=2)
    async def button_all_callback(self, button, interaction):
        self.selected = [*range(1, len(self.entries) + 1)]
        self.custom_order = False
        await self.confirm(interaction)

    @discord.ui.button(label="🎲 随机一首", style=discord.ButtonStyle.grey, custom_id="button_random", row=2)
    async def button_random_callback(self, button, interaction):
        if len(self.entries) > 0:
            number = random.randint(1, len(self.entries))
            self.selected = [number]
            self.custom_order = False
            self.page_num = (number - 1) // self.PAGE_SIZE
        await self._respond(interaction)

    @discord.ui.button(label="确定", style=discord.ButtonStyle.green, custom_id="button_confirm", row=2)
    async def button_confirm_callback(self, button, interaction):
        await self.confirm(interaction)

    @discord.ui.button(label="清空", style=discord.ButtonStyle.grey, custom_id="button_clear", row=2)
    async def button_clear_callback(self, button, interaction):
        self.selected = []
        self.custom_order = False
        await self._respond(interaction)

    @discord.ui.button(label="取消", style=discord.ButtonStyle.red, custom_id="button_cancel", row=2)
    async def button_cancel_callback(self, button, interaction):
        self.finish = True
        self.stop()
        await interaction.response.defer()
        if not await delete_response(self.original_msg):
            await delete_response(interaction.message)
        await console.rp("用户已取消选择界面", self.ctx.guild)

    async def confirm(self, interaction: discord.Interaction):
        final_result = self.ordered_selection()
        if len(final_result) == 0:
            await _respond_ephemeral(interaction, "请先在下拉菜单中选择要播放的音频，或点击「⌨ 输入序号」")
            return
        if self.finish:
            await _respond_ephemeral(interaction, "该选择菜单已结束")
            return

        self.finish = True
        self.stop()
        self.clear_items()
        self.embed.clear_fields()
        self.embed.description = f"已选择：第 {compress_indexes(final_result)} 个（共 {len(final_result)} 个）"
        self.embed.timestamp = utils.ctime_datetime()
        await interaction.response.edit_message(content=None, embed=self.embed, view=self)
        await self.play_select(final_result)

    async def _download_one(self, number: int) -> Result:
        index = number - 1
        if self.handler in (DownloadHandler.GO_MUSIC_API, DownloadHandler.NATIVE):
            return await result_check(await music_service_download(self.handler, self.info_dict["songs"][index], self.download_type))

        if self.handler is DownloadHandler.BILIBILI_API_PYTHON:
            if self.download_type is DownloadType.BILIBILI_P:
                return await result_check(await audio_lib_main.download_bilibili(self.info_dict, DownloadType.BILIBILI_P, index))
            return await result_check(await audio_lib_main.download_bilibili(self.info_dict, DownloadType.BILIBILI_COLLECTION, num_option=index))

        if self.handler is DownloadHandler.YT_DLP:
            entry = self.info_dict["entries"][index] or {}
            if self.download_type is DownloadType.YOUTUBE_PLAYLIST:
                # 已被删除或失效的视频没有时长信息
                if entry.get("duration") is None or not entry.get("id"):
                    return failed_result(exception=None, message="视频已失效或不可用", retryable=False)
                url = f"https://www.youtube.com/watch?v={entry['id']}"
            else:
                url = entry.get("url")
            info_result = await result_check(await ytdlp.get_info(url))
            if not info_result:
                return info_result
            return await result_check(await audio_lib_main.download_ytdlp(url, info_result.result, self.download_type))

        return failed_result(exception=None, message="未知的播放源", retryable=False)

    async def _download_with_retry(self, number: int, maximum_retry: int) -> Result:
        result = failed_result(exception=None, message="未开始下载", retryable=False)
        for attempt in range(maximum_retry + 1):
            try:
                result = await self._download_one(number)
            except Exception as e:
                await console.on_error(e)
                return failed_result(exception=e, message=f"{type(e).__name__}", retryable=False)
            if result or not result.retryable or isinstance(result.exception, errors.StorageFull):
                return result
            await asyncio.sleep(min(2 ** attempt, 8))
        return result

    async def _update_progress(self, force: bool = False) -> None:
        """
        更新添加进度（限制编辑频率，避免触发Discord速率限制）
        """
        now = time.monotonic()
        if not force and now - self._last_progress_edit < 1.5:
            return
        self._last_progress_edit = now
        await eos(self.ctx, self.original_msg, content=None, embed=self.embed, view=self, files=icon_lib.files(self.icon_filename))

    async def play_select(self, final_result: List[int], maximum_retry: int = 3, concurrency: int = 2):
        """
        并发下载选择的音频（最多同时<concurrency>个），并按选择的顺序加入播放列表
        """
        current_guild = guild_lib.get_guild(self.ctx)
        current_playlist = current_guild.get_playlist()

        icon_loading_filename = "hourglass_hover_rotation_animated_0ms_30px.gif"
        icon_finish_filename = "check_in_box_in_reveal_animated_0ms_100px.gif"
        icon_failed_filename = "error_cross_hover_pinch_orange_animated_0ms_100px.gif"

        total_num = len(final_result)
        total_duration = sum((self.entries[number - 1][1] or 0) for number in final_result if number <= len(self.entries))
        success_num = 0
        failed_num = 0
        result_lines: List[str] = []

        def render(status: str):
            shown = result_lines[-12:]
            hidden = len(result_lines) - len(shown)
            body = (f"…（省略 {hidden} 条）\n" if hidden > 0 else "") + "\n".join(shown)
            self.embed.description = f"{status}\n{body}".strip()
            self.embed.timestamp = utils.ctime_datetime()

        # ----- 下载并播放音频 -----
        self.icon_filename = icon_loading_filename
        self.embed.set_author(name=f"{self.list_type}：正在添加", icon_url=icon.url(self.icon_filename))
        self.embed.set_footer(text=f"总时长 -> [{utils.convert_duration_to_str(total_duration)}]")
        render(f"正在将 {total_num} 个音频添加入播放列表：")
        await self._update_progress(force=True)

        semaphore = asyncio.Semaphore(max(1, concurrency))

        async def fetch(number: int) -> Result:
            async with semaphore:
                return await self._download_with_retry(number, maximum_retry)

        tasks = [asyncio.create_task(fetch(number)) for number in final_result]
        try:
            for number, task in zip(final_result, tasks):
                title = self.entries[number - 1][0] if number <= len(self.entries) else str(number)
                new_result = await task
                new_audio = new_result.result

                if new_audio is not None:
                    # 当前没有播放时立即开始播放，并按选择顺序加入播放列表
                    if current_playlist.is_empty() and not is_streaming(self.ctx.guild):
                        await play_audio(self.ctx, new_audio, function_call=True)
                    current_playlist.append_audio(new_audio)
                    await console.rp(f"音频 {new_audio.get_title()} [{new_audio.get_duration_str()}] 已加入播放列表", self.ctx.guild)
                    await current_guild.refresh_list_view()
                    success_num += 1
                    result_lines.append(f"> ✅ [{number}] **{utils.markdown_escape(new_audio.get_title())}** [{new_audio.get_duration_str()}]")
                else:
                    failed_num += 1
                    message = new_result.message or "未知错误"
                    if new_result.retryable:
                        message += "，请稍后再试"
                    result_lines.append(f"> ❌ [{number}] {utils.markdown_escape(title)}：{message}")
                    if isinstance(new_result.exception, errors.StorageFull):
                        result_lines.append("**机器人当前处理音频过多，无法完成添加，请稍后再试**")
                        break

                render(f"进度：{success_num + failed_num} / {total_num}（成功 {success_num}，失败 {failed_num}）")
                await self._update_progress()
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()

        render(f"共 {total_num} 个：成功 {success_num}，失败 {failed_num}")
        if success_num == 0:
            self.icon_filename = icon_failed_filename
            self.embed.set_author(name=f"{self.list_type}：添加失败", icon_url=icon.url(self.icon_filename))
        else:
            self.icon_filename = icon_finish_filename
            self.embed.set_author(name=f"{self.list_type}：添加完成", icon_url=icon.url(self.icon_filename))
            self.embed.add_field(name="", value=f"添加完成：已将 {success_num} 个音频加入播放列表", inline=False)
        await self._update_progress(force=True)

    async def on_timeout(self):
        if not self.finish:
            self.finish = True
            await delete_response(self.original_msg)
        await console.rp(f"{self.occur_time}生成的选择菜单已超时(超时时间为{self.timeout}秒)", self.ctx.guild)


class CheckCollectionMenu(View):

    def __init__(self, ctx, download_type: DownloadType, info_dict, response: Union[discord.Interaction, discord.InteractionMessage, None] = None, timeout=60):
        """
        提示是否查看合集或播放列表的View
        """
        super().__init__(timeout=timeout)
        self.ctx: discord.ApplicationContext = ctx
        self.download_type = download_type
        self.response = response
        self.info_dict = info_dict
        self.occur_time = utils.ctime_str()
        self.finish = False
        self.original_msg = None

        if self.download_type is DownloadType.BILIBILI_COLLECTION:
            collection_title = self.info_dict["ugc_season"]["title"]
            message = f"**{utils.markdown_escape(self.info_dict['title'])}** 包含在合集 **{utils.markdown_escape(collection_title)}** 中, 是否要查看此合集？\n"
            title = "发现合集"
        elif self.download_type is DownloadType.YOUTUBE_PLAYLIST:
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

    @discord.ui.button(label="查看", style=discord.ButtonStyle.green, custom_id="button_confirm")
    async def button_confirm_callback(self, button, interaction):
        self.finish = True
        self.stop()
        await interaction.response.edit_message(content="已在频道中打开选择菜单", embed=None, view=None, attachments=[])

        if self.download_type is DownloadType.BILIBILI_COLLECTION:
            collection_title = self.info_dict["ugc_season"]["title"]
            menu = EpisodeSelectMenu(self.ctx, DownloadType.BILIBILI_COLLECTION, self.info_dict, list_type="哔哩哔哩合集", list_title=collection_title)
            await menu.init_eos(response=None, silent=True)

        elif self.download_type is DownloadType.YOUTUBE_PLAYLIST:
            menu = EpisodeSelectMenu(self.ctx, DownloadType.YOUTUBE_PLAYLIST, self.info_dict, list_type="YouTube播放列表", list_title=self.info_dict['title'])
            await menu.init_eos(response=None, silent=True)

        await delete_response(self.original_msg)

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.grey, custom_id="button_cancel")
    async def button_close_callback(self, button, interaction):
        self.finish = True
        self.stop()
        await interaction.response.edit_message(content="已关闭", embed=None, view=None, attachments=[])
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

    MAX_RESULTS = 20

    def __init__(self, ctx, query: str, title_str: str, address_str: str, resource_list: List[dict], response: Union[discord.Interaction, discord.InteractionMessage, None] = None, timeout=120):
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

        # 按结果数量生成序号按钮（每行5个，最多4行），点击即播放
        for index in range(min(len(self.resource_list), self.MAX_RESULTS)):
            button = discord.ui.Button(label=str(index + 1), style=discord.ButtonStyle.grey, custom_id=f"button_{index + 1}", row=index // 5)
            button.callback = self._make_play_callback(index)
            self.add_item(button)

        # 嵌入内容的长度上限为4096
        if len(self.title_str) > 4000:
            self.title_str = self.title_str[:4000] + "…"
        if len(self.address_str) > 4000:
            self.address_str = self.address_str[:4000] + "…"
        title_str = self.title_str

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
        _remember_attachments(original_msg, files)
        await self.set_original_msg(original_msg)

    async def init_eos(self, response, silent: bool = False):
        files = icon_lib.files(self.icon_filename)
        original_msg = await eos(self.ctx, response, content=None, silent=silent, embed=self.embed, view=self, files=files)
        await self.set_original_msg(original_msg)

    async def play(self, index: int, interaction: discord.Interaction):
        if self.finish or index >= len(self.resource_list):
            await _respond_ephemeral(interaction, "该搜索菜单已结束")
            return
        selected_item = self.resource_list[index]
        self.finish = True
        self.stop()
        self.clear_items()

        # 立即回应交互，显示已选择的音频，随后在同一条消息中显示加载进度
        self.embed.description = f"已选择：**{utils.markdown_escape(selected_item['title'])}** [{utils.convert_duration_to_str(selected_item['duration'])}]"
        await interaction.response.edit_message(content=None, embed=self.embed, view=self)
        await play_callback(self.ctx, selected_item["id"], response=self.original_msg)

    def _make_play_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            await self.play(index, interaction)
        return callback

    @discord.ui.button(label="显示网址", style=discord.ButtonStyle.green, custom_id="button_switch", row=4)
    async def button_switch_callback(self, button, interaction):
        self.show_address = not self.show_address
        button.label = "隐藏网址" if self.show_address else "显示网址"
        self.embed.description = self.address_str if self.show_address else self.title_str
        # 图标附件保持不变，无需重新上传
        await interaction.response.edit_message(content=None, embed=self.embed, view=self)

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.red, custom_id="button_cancel", row=4)
    async def button_cancel_callback(self, button, interaction):
        self.finish = True
        self.stop()
        await interaction.response.edit_message(content=f"已关闭搜索结果选择菜单", embed=None, attachments=[], view=None)
        await console.rp("用户已关闭搜索选择菜单", self.ctx.guild)

    async def set_original_msg(self, response: Union[discord.Message, discord.InteractionMessage, None]):
        """
        创建View后调用，传入发送该View的Interaction
        """
        self.original_msg = response

    async def on_timeout(self):
        if not self.finish:
            await delete_response(self.original_msg)
        await console.rp(f"{self.occur_time}生成的搜索选择菜单已超时(超时时间为{self.timeout}秒)", self.ctx.guild)


class AskForSearchingMenu(View):
    def __init__(self, ctx, query, response: Union[discord.Interaction, discord.InteractionMessage, None] = None,
                 timeout=60):
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
        self.finish = True
        self.stop()
        self.clear_items()
        await interaction.response.edit_message(view=self)
        await search_audio_callback(self.ctx, self.query, response=self.original_msg, query_num=5)

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.grey, custom_id="button_cancel")
    async def button_close_callback(self, button, interaction):
        self.finish = True
        self.stop()
        await interaction.response.defer()
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
        await console.rp(f"{self.occur_time}生成的询问搜索选择栏已超时(超时时间为{self.timeout}秒)", self.ctx.guild)
