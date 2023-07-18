import discord
import sys
import os
import asyncio
import requests
import platform
from typing import Any, Union
from discord.ui import Button, View
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from zeta_bot import (
    errors,
    language,
    utils,
    setting,
    log,
    playlist,
    member,
    guild,
    help,
    audio,
    file_management,
    bilibili,
    youtube
)

version = "0.10.0"
author = "炤铭Zeta (31Zeta)"
python_path = sys.executable
pycord_version = discord.__version__
update_time = "2023.**.**"

# 系统检测
if platform.system().lower() == "windows":
    ffmpeg_path = "./bin/ffmpeg.exe"
else:
    ffmpeg_path = "./bin/ffmpeg"

# 多语言模块
lang = language.Lang()
_ = lang.get_string
printl = lang.printl

# 初始化机器人设置
intents = discord.Intents.all()
bot = discord.Bot(help_command=None, case_insensitive=True, intents=intents)
startup_time = utils.time()

# 设置配置文件
utils.create_folder("./configs")
lang_setting = setting.Setting("./configs/language_config.json", setting.language_setting_configs)
lang.set_system_language(lang_setting.value("language"))
setting = setting.Setting("./configs/system_config.json", setting.bot_setting_configs, lang_setting.value("language"))
bot_name = setting.value("bot_name")

# 设置日志记录器
utils.create_folder("./logs")
log_name_time = startup_time.replace(":", "_")
error_log_path = f"./logs/{log_name_time}_errors.log"
log_path = f"./logs/{log_name_time}.log"
logger = log.Log(error_log_path, log_path, setting.value("log"))

logger.rp("程序启动", "[系统]")

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
    setting.value("audio_library_storage_size")
)


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
        raise errors.BootModeNotFound


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
    logger.on_error(exception)


@bot.event
async def on_application_command_error(ctx, exception):
    logger.on_application_command_error(ctx, exception)

    # 向用户回复发生错误
    await ctx.respond("发生错误")


async def command_check(ctx: discord.ApplicationContext) -> bool:
    """
    对指令触发进行日志记录，检测用户是否记录在案，检测用户是否有权限使用该条指令
    """
    member_lib.check(ctx)
    user_group = member_lib.get_group(ctx.user.id)
    operation = str(ctx.command)
    # 如果用户是机器人所有者
    if str(ctx.user.id) == setting.value("owner"):
        logger.rp(f"用户 {ctx.user} [用户组: 机器人所有者] 发送指令：<{operation}>", ctx.guild)
        return True
    elif member_lib.allow(ctx.user.id, operation):
        logger.rp(f"用户 {ctx.user} [用户组: {user_group}] 发送指令：<{operation}>", ctx.guild)
        return True
    else:
        logger.rp(f"用户 {ctx.user} [用户组: {user_group}] 发送指令：<{operation}>，权限不足，操作已被拒绝", ctx.guild)
        await ctx.respond("权限不足")
        return False


# 启动就绪时
@bot.event
async def on_ready():
    """
    当机器人启动完成时自动调用
    """

    current_time = utils.time()
    print(f"\n---------- 准备就绪 ----------\n")
    logger.rp(f"登录完成：以{bot.user}的身份登录，登录时间：{current_time}", "[系统]")

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

        logger.rp(
            f"设置自动重启时间为 {ar_time[0]}时{ar_time[1]}分{ar_time[2]}秒", "[系统]"
        )

    # 设置机器人状态
    bot_activity_type = discord.ActivityType.playing
    await bot.change_presence(
        activity=discord.Activity(type=bot_activity_type,
                                  name=setting.value("default_activity")))


# 文字频道中收到信息时
@bot.event
async def on_message(message):
    """
    当检测到消息时调用

    :param message:频道中的消息
    :return:
    """
    if message.author == bot.user:
        return

    if message.content.startswith("test"):
        await message.channel.send(_("custom.reply_1"))


async def auto_reboot():
    """
    用于执行定时重启，如果<auto_reboot_announcement>为True则广播重启消息
    """
    current_time = utils.time()
    logger.rp(f"执行自动定时重启", "[系统]")
    # audio_library.save()
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
    logger.rp(f"发送自动重启通知", "[系统]")
    for current_guild in bot.guilds:
        voice_client = current_guild.voice_client
        if voice_client is not None:
            await current_guild.text_channels[0].send(f"注意：将在{ar_time}时自动重启")


async def send_edit(ctx: discord.ApplicationContext, response, content: str, view=None) -> None:
    """
    如果<response>可以被编辑（类型为discord.InteractionMessage），则将<response>编辑为<content>
    否则使用<ctx>发送<content>
    """
    if isinstance(response, discord.InteractionMessage):
        await response.edit(content, view=view)
    else:
        await ctx.send(content, view=view)


@bot.command(description="[管理员] 测试指令")
async def debug(ctx: discord.ApplicationContext):
    """
    测试用指令

    :param ctx: 指令原句
    :return:
    """
    if not await command_check(ctx):
        return

    # start_test = await ctx.respond("开始测试")
    # print(type(start_test))
    #
    # new_msg = await start_test.edit_original_response(content="测试回复已被修改")
    # print(type(new_msg))
    #
    # new_msg_2 = await new_msg.edit(content="测试回复已被二次修改")
    # print(type(new_msg_2))
    #
    # end_test = await ctx.send("测试结果已打印")
    # print(type(end_test))

    await ctx.respond("开始测试")
    # print(type(start_test))
    #
    # if isinstance(start_test, discord.Interaction):
    #     print("转换类型")
    #     start_test = await start_test.original_response()
    # print(type(start_test))
    #
    # time.sleep(3)
    #
    # if isinstance(start_test, discord.InteractionMessage):
    #     print("类型符合，开始修改")
    #     new_msg = await start_test.edit(content="测试回复已被修改")
    #     print(type(new_msg))

    await ctx.respond("二次发送")


@bot.command(description="关于Zeta-Discord机器人")
async def info(ctx: discord.ApplicationContext) -> None:
    """
    显示关于信息

    :param ctx: 指令原句
    :return:
    """
    if not await command_check(ctx):
        return

    await ctx.respond(f"**Zeta-Discord机器人 [版本 {version}]**\n"
                      f"   基于 Pycord v{pycord_version} 制作\n"
                      f"   版本更新日期：**{update_time}**\n"
                      f"   作者：炤铭Zeta (31Zeta)")


@bot.command(description="帮助菜单")
async def help(ctx: discord.ApplicationContext) -> None:
    """
    覆盖掉原有help指令, 向频道发送帮助菜单

    :param ctx: 指令原句
    :return:
    """
    if not await command_check(ctx):
        return

    view = help.HelpMenuView(ctx)
    await ctx.respond(content=view.catalog, view=view)


# @bot.command(description="[管理员] 向机器人所在的所有服务器广播消息")
async def broadcast(ctx: discord.ApplicationContext, message) -> None:
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
    await ctx.respond("已发送")


@bot.command(description=f"让 {bot_name} 加入语音频道")
async def join(ctx: discord.ApplicationContext, channel_name=None, function_call: bool = False) -> bool:
    """
    让机器人加入指令发送者所在的语音频道并发送提示\n
    如果机器人已经加入一个频道则转移到新频道并发送提示
    如发送者未加入任何语音频道发送提示

    :param ctx: 指令原句
    :param channel_name: 要加入的频道名称
    :param function_call 该指令是否是由其他函数调用
    :return: 布尔值，是否成功加入频道
    """
    if not function_call and not await command_check(ctx):
        return False

    guild_lib.check(ctx)

    channel = None

    # 未输入参数的情况
    if channel_name is None:
        # 指令发送者未加入频道的情况
        if not ctx.user.voice:
            logger.rp(f"频道加入失败，用户 {ctx.user} 发送指令时未加入任何语音频道", ctx.guild)
            await ctx.respond("您未加入任何语音频道")
            return False

        # 目标频道设定为指令发送者所在的频道
        else:
            channel = ctx.user.voice.channel

    # 输入了频道名称参数的情况
    else:
        for ch in ctx.guild.channels:
            if ch.type is discord.ChannelType.voice and ch.name == channel_name:
                channel = ch
                break

        # 搜索后未找到同名频道的情况
        if channel is None:
            await ctx.respond("无效的语音频道名称")
            return False

    voice_client = ctx.guild.voice_client

    # 机器人未在任何语音频道的情况
    if voice_client is None:
        await channel.connect()
        await ctx.respond(f"加入语音频道：->  ***{channel.name}***")

    # 机器人已经在一个频道的情况
    else:
        previous_channel = voice_client.channel
        await voice_client.move_to(channel)
        await ctx.respond(f"转移语音频道：***{previous_channel}***  ->  ***{channel.name}***")

    logger.rp(f"加入语音频道：{channel.name}", ctx.guild)
    return True


@bot.command(description=f"让 {bot_name} 离开语音频道")
async def leave(ctx: discord.ApplicationContext) -> None:
    """
    让机器人离开语音频道并发送提示

    :param ctx: 指令原句
    :return:
    """
    if not await command_check(ctx):
        return

    guild_lib.check(ctx)

    voice_client = ctx.guild.voice_client
    current_playlist = guild_lib.get_guild(ctx).get_playlist()

    if voice_client is not None:
        # 防止因退出频道自动删除正在播放的音频
        if voice_client.is_playing():
            current_audio = current_playlist.get_audio(0)
            current_playlist.insert_audio(current_audio, 0)
            guild_lib.get_guild(ctx).save()

        last_channel = voice_client.channel
        await voice_client.disconnect(force=False)

        logger.rp(f"离开语音频道：{last_channel}", ctx.guild)

        await ctx.respond(f"离开语音频道：<- ***{last_channel}***")

    else:
        await ctx.respond(f"{bot_name} 没有连接到任何语音频道")


@bot.command(description="播放Bilibili或Youtube的音频", aliases=["p"])
async def play(ctx: discord.ApplicationContext, link=None) -> None:
    """
    使机器人下载目标BV号或Youtube音频后播放并将其标题与文件路径记录进当前服务器的播放列表
    播放结束后调用play_next
    如果当前有歌曲正在播放，则将下载目标音频并将其标题与文件路径记录进当前服务器的播放列表

    :param ctx: 指令原句
    :param link: 目标URL或BV号
    :return:
    """
    if not await command_check(ctx):
        return

    # 用户记录增加音乐播放计数
    member_lib.play_counter_increment(ctx.user.id)

    guild_lib.check(ctx)

    # 检测机器人是否已经加入语音频道
    if ctx.guild.voice_client is None:
        logger.rp("机器人未在任何语音频道中，尝试加入语音频道", ctx.guild)
        join_result = await join(ctx, function_call=True)
        if not join_result:
            return

    # 尝试恢复之前被停止的播放
    await resume(ctx, play_call=True)

    if link is None:
        logger.rp("用户未输入任何参数，指令无效", ctx.guild)
        await ctx.respond("请在在指令后打出您想要播放的链接或想要搜索的名称")
        return

    # 检查输入的URL属于哪个网站
    source = utils.check_url_source(link)

    # 如果指令中包含链接则提取链接
    if source is not None:
        link = utils.get_url_from_str(link, source)

    # URL属于Bilibili
    if source == "bilibili_bvid" or source == "bilibili_url" or source == "bilibili_short_url":
        loading_msg = await ctx.respond("正在加载Bilibili音频信息")
        await play_bilibili(ctx, source, link, response=loading_msg)

    # elif source == "ytb_url":
    #
    #     loading_msg = await ctx.send("正在获取Youtube视频信息")
    #     url_type, info_dict = youtube.get_info(link)
    #     await loading_msg.delete()
    #
    #     # 单一视频 ytb_single
    #     if url_type == "ytb_single":
    #         loading_msg = await ctx.respond("正在加载Youtube歌曲")
    #         await play_ytb(ctx, link, info_dict, url_type)
    #         # await loading_msg.delete()
    #
    #     # 播放列表 ytb_playlist
    #     else:
    #         message = "这是一个播放列表, 请选择要播放的集数:\n"
    #         ep_info_list = []
    #         for item in info_dict["entries"]:
    #             ep_title = item["fulltitle"]
    #             ep_time_str = utils.convert_duration_to_time_str(item["duration"])
    #             ep_info_list.append((ep_title, ep_time_str))
    #
    #         menu_list = utils.make_playlist_page(ep_info_list, 10, indent=4)
    #         view = EpisodeSelectView(ctx, "ytb_playlist", info_dict, menu_list)
    #         await ctx.respond(f"{menu_list[0]}\n第[1]页，共[{len(menu_list)}]页\n已输入：", view=view)

    else:
        if link is not None:
            await search_ytb(ctx, link)


async def play_audio(ctx: discord.ApplicationContext, target_audio: audio.Audio,
                     response: Union[discord.Interaction, discord.InteractionMessage, None] = None,
                     function_call: bool = False) -> None:
    """
    在<ctx>中的音频端播放音频<target_audio>，如果<single>为True则发送单曲加入成功通知
    <response>为用来编辑的加载信息，如果为None则发送新的通知

    :param ctx: 指令原句
    :param target_audio: 需要播放的音频
    :param response: 用于编辑的加载信息
    :param function_call 该指令是否是由其他函数调用
    """
    # 将Interaction转换为InteractionMessage
    if isinstance(response, discord.Interaction):
        response = await response.original_response()

    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)

    voice_client.play(
        discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                executable=ffmpeg_path, source=target_audio.get_path()
            )
        ),
        after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
    )
    voice_client.source.volume = current_guild.get_voice_volume() / 100.0

    if not function_call:
        logger.rp(
            f"开始播放：{target_audio.get_title()} [{target_audio.get_time_str()}] 路径: {target_audio.get_path()}",
            ctx.guild
        )

        await send_edit(ctx, response, f"正在播放：**{target_audio.get_title()} [{target_audio.get_time_str()}]**")


async def play_next(ctx: discord.ApplicationContext) -> None:
    """
    播放列表中的下一个音频

    :param ctx: 指令原句
    """
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    logger.rp(f"触发play_next", ctx.guild)

    if len(current_playlist) > 1:
        # 移除上一个音频
        current_playlist.remove_audio(0)
        # 获取下一个音频
        next_audio = current_playlist.get_audio(0)
        await play_audio(ctx, next_audio, response=None)

    else:
        current_playlist.remove_audio(0)
        logger.rp("播放队列已结束", ctx.guild)
        await ctx.send("播放队列已结束")


async def play_bilibili(ctx: discord.ApplicationContext, source, link,
                        response: Union[discord.Interaction, discord.InteractionMessage, None] = None):
    """
    下载并播放来自Bilibili的视频的音频

    :param ctx: 指令原句
    :param source: 链接类型
    :param link: 链接
    :param response: 用于编辑的加载信息
    :return: 播放的音频
    """
    # 将Interaction转换为InteractionMessage
    if isinstance(response, discord.Interaction):
        response = await response.original_response()

    # 如果是Bilibili短链则获取重定向链接
    if source == "bilibili_short_url":
        try:
            link = utils.get_redirect_url_bilibili(link)
        except requests.exceptions.InvalidSchema:
            await send_edit(ctx, response, "链接异常")
            logger.rp(f"链接重定向失败", ctx.guild)
            return

        logger.rp(f"获取的重定向链接为 {link}", ctx.guild)

    # 如果是URl则转换成BV号
    if source == "bilibili_url" or source == "bilibili_short_url":
        bvid = utils.get_bvid_from_url(link)
        if bvid is None:
            await send_edit(ctx, response, "无效的Bilibili链接")
            logger.rp(f"{link} 为无效的链接", ctx.guild)
            return
    else:
        bvid = link

    # 获取Bilibili视频信息
    info_dict = await bilibili.get_info(bvid)

    # 单一视频 bilibili_single
    if info_dict["videos"] == 1 and "ugc_season" not in info_dict:
        await add_bilibili_audio(ctx, info_dict, "bilibili_single", 0, response=response)

    # 合集视频 bilibili_collection
    elif "ugc_season" in info_dict:
        await add_bilibili_audio(ctx, info_dict, "bilibili_single", 0, response=response)

        collection_title = info_dict["ugc_season"]["title"]
        message = f"此视频包含在合集 **{collection_title}** 中, 是否要查看此合集？\n"
        view = CheckBilibiliCollectionView(ctx, info_dict)
        await ctx.respond(message, view=view)

    # 分P视频 bilibili_p
    else:
        p_info_list = []
        for item in info_dict["pages"]:
            p_title = item["part"]
            p_time_str = utils.convert_duration_to_time_str(item["duration"])
            p_info_list.append((p_title, p_time_str))

        menu_list = utils.make_playlist_page(p_info_list, 10, indent=0)
        view = EpisodeSelectView(ctx, "bilibili_p", info_dict, menu_list)
        await send_edit(ctx, response,
                        f"这是一个分p视频, 请选择要播放的分p:\n{menu_list[0]}\n第[1]页，共[{len(menu_list)}]页\n已输入：",
                        view=view)
        return


async def add_bilibili_audio(ctx, info_dict, audio_type, num_option: int = 0,
                             response: Union[discord.Interaction, discord.InteractionMessage, None] = None):
    # 将Interaction转换为InteractionMessage
    if isinstance(response, discord.Interaction):
        response = await response.original_response()

    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    new_audio = await audio_lib_main.download_bilibili(info_dict, audio_type, num_option)

    if new_audio is not None:

        # 如果当前播放列表为空
        if current_playlist.is_empty() and not voice_client.is_playing():
            await play_audio(ctx, new_audio, response=response)

        # 如果播放列表不为空
        elif audio_type == "bilibili_single":
            await send_edit(ctx, response, f"已加入播放列表：**{new_audio.get_title()} [{new_audio.get_time_str()}]**")

        current_playlist.append_audio(new_audio)
        logger.rp(f"音频 {new_audio.get_title()} [{new_audio.get_time_str()}] 已加入播放列表", ctx.guild)

    return audio


async def play_ytb(ctx, url, info_dict, download_type="ytb_single",
                   response: Union[discord.Interaction, discord.InteractionMessage, None] = None):
    """
    下载并播放来自Youtube的视频的音频

    :param ctx: 指令原句
    :param url: 目标URL
    :param info_dict: 目标的信息字典（使用ytb_get_info提取）
    :param download_type: 下载模式（"ytb_single"或"ytb_playlist"）
    :param response: 用于编辑的加载信息
    :return: （歌曲标题，歌曲时长）
    """
    # 将Interaction转换为InteractionMessage
    if isinstance(response, discord.Interaction):
        response = await response.original_response()

    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    new_audio = youtube.audio_download(url, info_dict, "./downloads/", download_type)

    duration_str = new_audio.get_time_str()

    # 如果当前播放列表为空
    if current_playlist.is_empty() and not voice_client.is_playing():

        voice_client.play(
            discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    executable=ffmpeg_path, source=new_audio.get_path()
                )
            ), after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx), bot.loop)
        )
        # voice_client.source.volume = volume_dict[ctx.guild.id] / 100.0

        logger.rp(f"开始播放：{new_audio.get_title()} [{duration_str}] {new_audio.get_path()}", ctx.guild)
        await ctx.send(f"正在播放：**{new_audio.get_title()} [{duration_str}]**")

    # 如果播放列表不为空
    elif download_type == "ytb_single":
        await ctx.send(f"已加入播放列表：**{new_audio.get_title()} [{duration_str}]**")

    current_playlist.append_audio(new_audio)
    logger.rp(f"歌曲 {new_audio.get_title()} [{duration_str}] 已加入播放列表", ctx.guild)

    return new_audio


async def search_ytb(ctx, input_name):
    await ctx.respond("搜索功能暂未开放")
    # name = input_name.strip()
    #
    # if name == "":
    #     ctx.respond("请输入要搜索的名称")
    #     return
    #
    # options = []
    # search_result = VideosSearch(name, limit=5)
    # info_dict = dict(search_result.result())['result']
    #
    # message = f"Youtube搜索 **{name}** 结果为:\n"
    #
    # counter = 1
    # for result_video in info_dict:
    #
    #     title = result_video["title"]
    #     video_id = result_video["id"]
    #     duration = result_video["duration"]
    #
    #     options.append([title, video_id, duration])
    #     message = message + f"**[{counter}]** {title}  [{duration}]\n"
    #
    #     counter += 1
    #
    # logger.rp(ctx, f"搜索结果为：{options}")
    #
    # message = message + "\n请选择："
    #
    # if len(info_dict) == 0:
    #     await ctx.respond("没有搜索到任何结果")
    #     return
    #
    # view = SearchSelectView(ctx, options)
    # await ctx.respond(message, view=view)


@bot.command(description="暂停正在播放的音频")
async def pause(ctx):
    """
    暂停播放

    :param ctx: 指令原句
    :return:
    """
    if not await command_check(ctx):
        return

    guild_lib.check(ctx)

    voice_client = ctx.guild.voice_client

    if voice_client is not None and voice_client.is_playing():
        if ctx.author.voice and voice_client.channel == ctx.author.voice.channel:
            voice_client.pause()
            logger.rp("暂停播放", ctx.guild)
            await ctx.respond("暂停播放")
        else:
            logger.rp(f"收到pause指令时指令发出者 {ctx.author} 不在机器人所在的频道", ctx.guild)
            await ctx.respond(f"您不在{setting.value('bot_name')}所在的频道")

    else:
        logger.rp("收到pause指令时机器人未在播放任何音乐", ctx.guild)
        await ctx.respond("未在播放任何音乐")


@bot.command(description="继续播放暂停的或被意外中断的音频", aliases=["restart"])
async def resume(ctx, play_call=False):
    """
    恢复播放

    :param ctx: 指令原句
    :param play_call: 是否是由play指令调用来尝试恢复播放
    :return:
    """
    if not await command_check(ctx):
        return

    guild_lib.check(ctx)

    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    # 未加入语音频道的情况
    if voice_client is None:
        if not play_call:
            logger.rp("收到resume指令时机器人没有加入任何语音频道", ctx.guild)
            await ctx.respond(f"{setting.value('bot_name')}尚未加入任何语音频道")

    # 被暂停播放的情况
    elif voice_client.is_paused():
        if ctx.author.voice and voice_client.channel == ctx.author.voice.channel:
            voice_client.resume()
            logger.rp("恢复播放", ctx.guild)
            await ctx.respond("恢复播放")
        else:
            logger.rp(f"收到pause指令时指令发出者 {ctx.author} 不在机器人所在的频道", ctx.guild)
            await ctx.respond(f"您不在{setting.value('bot_name')}所在的频道")

    # 没有被暂停并且正在播放的情况
    elif voice_client.is_playing():
        if not play_call:
            logger.rp("收到resume指令时机器人正在播放音乐", ctx.guild)
            await ctx.respond("当前正在播放音乐")

    # 没有被暂停，没有正在播放，并且播放列表中存在歌曲的情况
    elif not current_playlist.is_empty():
        current_audio = current_playlist.get_audio(0)

        await play_audio(ctx, current_audio, function_call=True)

        logger.rp("恢复中断的播放列表", ctx.guild)
        await ctx.respond(f"恢复上次中断的播放列表")

    else:
        if not play_call:
            logger.rp("收到resume指令时机器人没有任何被暂停的音乐", ctx.guild)
            await ctx.respond("当前没有任何被暂停的音乐")


@bot.command(description="显示当前播放列表")
async def list(ctx):
    """
    将当前服务器播放列表发送到服务器文字频道中

    :param ctx: 指令原句
    :return:
    """
    if not await command_check(ctx):
        return

    guild_lib.check(ctx)

    current_guild = guild_lib.get_guild(ctx)
    current_playlist = current_guild.get_playlist()

    if current_playlist.is_empty():
        await ctx.respond("当前播放列表为空")
    else:
        playlist_list = utils.make_playlist_page(current_playlist.get_list_info(), 10, indent=2)

        view = PlaylistMenu(ctx, current_playlist)
        await ctx.respond(
            content=">>> **播放列表**\n\n" + playlist_list[0] + f"\n第[1]页，共[{len(playlist_list)}]页\n",
            view=view
        )


@bot.command(description=f"调整 {bot_name} 的语音频道音量")
async def volume(ctx: discord.ApplicationContext, volume_num=None) -> None:
    if not await command_check(ctx):
        return

    guild_lib.check(ctx)
    current_volume = guild_lib.get_guild(ctx).get_voice_volume()

    if volume_num is None:
        await ctx.respond(f"当前音量为 **{current_volume}%**")

    elif volume_num == "up" or volume_num == "u":
        if current_volume + 20.0 >= 200:
            current_volume = 200.0
        else:
            current_volume += 20.0
        # if voice_client.is_playing():
        #     voice_client.source.volume = current_volume / 100.0

        guild_lib.get_guild(ctx).set_voice_volume(current_volume)
        logger.rp(f"用户 {ctx.author} 已将音量设置为 {current_volume}%", ctx.guild)
        await ctx.respond(f"将音量提升至 **{current_volume}%**")

    elif volume_num == "down" or volume_num == "d":
        if current_volume - 20.0 <= 0.0:
            current_volume = 0.0
        else:
            current_volume -= 20.0
        # if voice_client.is_playing():
        #     voice_client.source.volume = current_volume / 100.0

        guild_lib.get_guild(ctx).set_voice_volume(current_volume)
        logger.rp(f"用户 {ctx.author} 已将音量设置为 {current_volume}%", ctx.guild)
        await ctx.respond(f"将音量降低至 **{current_volume}%**")

    else:
        try:
            volume_num = float(int(float(volume_num)))
        except ValueError:
            await ctx.respond("请输入up或down来提升或降低音量或一个0-200的数字来设置音量")
            return

        if volume_num > 200.0 or volume_num < 0.0:
            await ctx.respond("请输入up或down来提升或降低音量或一个0-200的数字来设置音量")

        else:
            current_volume = volume_num
            # if voice_client.is_playing():
            #     voice_client.source.volume = current_volume / 100.0
            guild_lib.get_guild(ctx).set_voice_volume(current_volume)
            logger.rp(f"用户 {ctx.author} 已将音量设置为 {current_volume}%", ctx.guild)
            await ctx.respond(f"将音量设置为 **{current_volume}%**")


# TODO 添加列表总时长显示
class PlaylistMenu(View):

    def __init__(self, ctx, playlist_1: playlist.Playlist, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.playlist = playlist_1
        self.playlist_pages = utils.make_playlist_page(self.playlist.get_list_info(), 10, indent=2)
        self.page_num = 0
        self.occur_time = utils.time()
        # 保留当前第一页作为超时后显示的内容
        self.first_page = f">>> **{self.playlist.get_name()}**\n\n{self.playlist_pages[0]}\n" \
                          f"第[1]页，共[{len(self.playlist_pages)}]页\n"

    def refresh_pages(self):
        self.playlist_pages = utils.make_playlist_page(self.playlist.get_list_info(), 10, indent=2)
        self.first_page = f">>> **{self.playlist.get_name()}**\n\n{self.playlist_pages[0]}\n" \
                          f"第[1]页，共[{len(self.playlist_pages)}]页\n"

    @discord.ui.button(label="上一页", style=discord.ButtonStyle.grey,
                       custom_id="button_previous")
    async def button_previous_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.refresh_pages()
        # 翻页
        if self.page_num == 0:
            pass
        else:
            self.page_num -= 1
        await msg.edit_message(
            content=f">>> **{self.playlist.get_name()}**\n\n{self.playlist_pages[self.page_num]}\n"
                    f"第[{self.page_num + 1}]页，"
                    f"共[{len(self.playlist_pages)}]页\n", view=self
        )

    @discord.ui.button(label="下一页", style=discord.ButtonStyle.grey,
                       custom_id="button_next")
    async def button_next_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.refresh_pages()
        # 翻页
        if self.page_num == len(self.playlist_pages) - 1:
            pass
        else:
            self.page_num += 1
        await msg.edit_message(
            content=f">>> **{self.playlist.get_name()}**\n\n{self.playlist_pages[self.page_num]}\n"
                    f"第[{self.page_num + 1}]页，"
                    f"共[{len(self.playlist_pages)}]页\n", view=self
        )

    @discord.ui.button(label="刷新", style=discord.ButtonStyle.grey,
                       custom_id="button_refresh")
    async def button_refresh_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.refresh_pages()

        await msg.edit_message(
            content=f">>> **{self.playlist.get_name()}**\n\n{self.playlist_pages[self.page_num]}\n"
                    f"第[{self.page_num + 1}]页，"
                    f"共[{len(self.playlist_pages)}]页\n", view=self
        )

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.grey,
                       custom_id="button_close")
    async def button_close_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content="已关闭", view=self)
        await self.ctx.delete()

    async def on_timeout(self):
        self.clear_items()
        await self.ctx.edit(content=self.first_page, view=self)
        logger.rp(f"{self.occur_time}生成的播放列表菜单已超时(超时时间为{self.timeout}秒)", self.ctx.guild)


class EpisodeSelectView(View):

    def __init__(self, ctx, source, info_dict, menu_list, timeout=60):
        """
        初始化分集选择菜单

        :param ctx: 指令原句
        :param source: 播放源的种类（bilibili_p, bilibili_collection, youtube_playlist)
        :param info_dict: 播放源的信息字典
        :param menu_list: 选择菜单的文本（使用make_menu_list获取）
        :param timeout: 超时时间（单位：秒）
        :return:
        """
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.source = source
        self.info_dict = info_dict
        self.menu_list = menu_list
        self.page_num = 0
        self.result = []
        self.dash_finish = True
        self.occur_time = utils.time()
        self.voice_client = self.ctx.guild.voice_client
        self.current_playlist = guild_lib.get_guild(self.ctx).get_playlist()

        self.finish = False

    @discord.ui.button(label="1", style=discord.ButtonStyle.grey,
                       custom_id="button_1", row=1)
    async def button_1_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("1")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="2", style=discord.ButtonStyle.grey,
                       custom_id="button_2", row=1)
    async def button_2_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("2")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="3", style=discord.ButtonStyle.grey,
                       custom_id="button_3", row=1)
    async def button_3_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("3")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="4", style=discord.ButtonStyle.grey,
                       custom_id="button_4", row=2)
    async def button_4_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("4")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="5", style=discord.ButtonStyle.grey,
                       custom_id="button_5", row=2)
    async def button_5_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("5")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="6", style=discord.ButtonStyle.grey,
                       custom_id="button_6", row=2)
    async def button_6_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("6")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="7", style=discord.ButtonStyle.grey,
                       custom_id="button_7", row=3)
    async def button_7_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("7")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="8", style=discord.ButtonStyle.grey,
                       custom_id="button_8", row=3)
    async def button_8_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("8")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="9", style=discord.ButtonStyle.grey,
                       custom_id="button_9", row=3)
    async def button_9_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("9")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="-", style=discord.ButtonStyle.grey,
                       custom_id="button_dash", row=4)
    async def button_dash_callback(self, button, interaction):
        button.disabled = False

        if len(self.result) == 0 or not \
                self.result[len(self.result) - 1].isdigit() or not \
                self.dash_finish:
            return

        msg = interaction.response
        self.result.append("-")
        self.dash_finish = False
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="0", style=discord.ButtonStyle.grey,
                       custom_id="button_0", row=4)
    async def button_0_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("0")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label=",", style=discord.ButtonStyle.grey,
                       custom_id="button_comma", row=4)
    async def button_comma_callback(self, button, interaction):
        button.disabled = False

        if len(self.result) == 0 or not \
                self.result[len(self.result) - 1].isdigit():
            return

        msg = interaction.response
        self.result.append(",")
        self.dash_finish = True
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="<-", style=discord.ButtonStyle.grey,
                       custom_id="button_backspace", row=1)
    async def button_backspace_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        if len(self.result) <= 0:
            pass
        else:
            self.result.pop()
            num = ""
            for i in self.result:
                num = num + i
            await msg.edit_message(
                content=f"{self.menu_list[self.page_num]}\n第"
                        f"[{self.page_num + 1}]页，共[{len(self.menu_list)}]页\n"
                        f"已输入：" + num, view=self)

    @discord.ui.button(label="取消", style=discord.ButtonStyle.red,
                       custom_id="button_cancel", row=3)
    async def button_cancel_callback(self, button, interaction):
        button.disabled = True
        self.finish = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已取消", view=self)

    @discord.ui.button(label="确定", style=discord.ButtonStyle.green,
                       custom_id="button_confirm", row=4)
    async def button_confirm_callback(self, button, interaction):
        message = "已选择"
        button.disabled = False
        self.finish = True

        if len(self.result) == 0 or self.result[len(self.result) - 1] == "-":
            return

        msg = interaction.response
        self.clear_items()
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
                        message = message + f"第[{start_num}]首至第[{start_1}]首(倒序)，"
                    else:
                        start_num = start_1
                        for i in range(start_1, int(num) + 1):
                            if i == 0:
                                start_num = 1
                            else:
                                final_result.append(i)
                        message = message + f"第[{start_num}]首至第[{int(num)}]首，"
                    num = ""
                else:
                    if int(num) == 0:
                        pass
                    else:
                        final_result.append(int(num))
                        message = message + f"第[{int(num)}]首，"
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
                message = message + f"第[{start_num}]首至第[{start_1}]首(倒序)，"
            else:
                start_num = start_1
                for i in range(start_1, int(num) + 1):
                    if i == 0:
                        start_num = 1
                    else:
                        final_result.append(i)
                message = message + f"第[{start_num}]首至第[{int(num)}]首，"
        else:
            if int(num) == 0:
                pass
            else:
                final_result.append(int(num))
                message = message + f"第[{int(num)}]首，"

        if self.source == "bilibili_p":
            for num in final_result:
                if num > len(self.info_dict["pages"]):
                    self.clear_items()
                    await msg.edit_message(content="选择中含有无效分p号", view=self)
                    return
        elif self.source == "bilibili_collection":
            for num in final_result:
                if num > len(self.info_dict["ugc_season"]["sections"][0][
                                 "episodes"]):
                    self.clear_items()
                    await msg.edit_message(content="选择中含有无效集数", view=self)
                    return
        elif self.source == "ytb_playlist":
            for num in final_result:
                if num > len(self.info_dict["entries"]):
                    self.clear_items()
                    await msg.edit_message(content="选择中含有无效集数", view=self)
                    return

        message = message[:-1]
        self.clear_items()
        await msg.edit_message(content=message, view=self)

        await self.play_select(final_result)

    @discord.ui.button(label="上一页", style=discord.ButtonStyle.blurple,
                       custom_id="button_previous", row=3)
    async def button_previous_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        num = ""
        for i in self.result:
            num = num + i
        # 翻页
        if self.page_num == 0:
            return
        else:
            self.page_num -= 1
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="下一页", style=discord.ButtonStyle.blurple,
                       custom_id="button_next", row=4)
    async def button_next_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        num = ""
        for i in self.result:
            num = num + i
        # 翻页
        if self.page_num == len(self.menu_list) - 1:
            return
        else:
            self.page_num += 1
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="全部", style=discord.ButtonStyle.blurple,
                       custom_id="button_all", row=2)
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
        elif self.source == "ytb_playlist":
            total_num = len(self.info_dict["entries"])

        for num in range(1, total_num + 1):
            final_result.append(num)

        self.clear_items()
        await msg.edit_message(content=f"已选择全部[{total_num}]首", view=self)
        await self.play_select(final_result)

    async def play_select(self, final_result):
        total_num = len(final_result)
        total_duration = 0

        # ----- 下载并播放视频 -----

        # 如果为Bilibili分p视频
        if self.source == "bilibili_p":
            counter = 1
            for item in self.info_dict["pages"]:
                if counter in final_result:
                    total_duration += item["duration"]
                counter += 1
            total_duration = utils.convert_duration_to_time_str(total_duration)
            loading_msg = await self.ctx.send(f"正在将{total_num}首歌曲加入播放列表  总时长 -> [{total_duration}]")

            for num_p in final_result:
                await add_bilibili_audio(self.ctx, self.info_dict, "bilibili_p", num_p - 1)

            await loading_msg.delete()
            await self.ctx.send(f"已将{total_num}首歌曲加入播放列表  "
                                f"总时长 -> [{total_duration}]")

        # 如果为Bilibili合集视频
        elif self.source == "bilibili_collection":
            counter = 1
            for item in self.info_dict["ugc_season"]["sections"][0]["episodes"]:
                if counter in final_result:
                    total_duration += item["arc"]["duration"]
                counter += 1
            total_duration = utils.convert_duration_to_time_str(total_duration)
            loading_msg = await self.ctx.send(f"正在将{total_num}首歌曲加入播放"
                                              f"列表  总时长 -> [{total_duration}]")

            for num in final_result:
                bvid = self.info_dict["ugc_season"]["sections"][0]["episodes"][
                    num - 1]["bvid"]
                info_dict = await bilibili.get_info(bvid)
                await add_bilibili_audio(self.ctx, info_dict, "bilibili_collection")

            await loading_msg.delete()
            await self.ctx.send(f"已将{total_num}首歌曲加入播放列表  "
                                f"总时长 -> [{total_duration}]")

        # # 如果为Youtube播放列表
        # elif self.source == "ytb_playlist":
        #     counter = 1
        #     for item in self.info_dict["entries"]:
        #         if counter in final_result:
        #             total_duration += item["duration"]
        #         counter += 1
        #     total_duration = utils.convert_duration_to_time_str(total_duration)
        #     loading_msg = await self.ctx.send(f"正在将{total_num}首歌曲加入播放"
        #                                       f"列表  总时长 -> [{total_duration}]")
        #
        #     for num in final_result:
        #         url = f"https://www.youtube.com/watch?v=" \
        #               f"{self.info_dict['entries'][num - 1]['id']}"
        #         download_type, info_dict = ytb_get_info(url)
        #         await play_ytb(self.ctx, url, info_dict, "ytb_playlist")
        #
        #     await loading_msg.delete()
        #     await self.ctx.send(f"已将{total_num}首歌曲加入播放列表  "
        #                         f"总时长 -> [{total_duration}]")

        else:
            logger.rp("未知的播放源", self.ctx.guild)

    async def on_timeout(self):
        self.clear_items()
        if self.finish:
            await self.ctx.edit(view=self)
        else:
            await self.ctx.edit(content="分集选择菜单已超时", view=self)
        logger.rp(f"{self.occur_time}生成的搜索选择菜单已超时(超时时间为{self.timeout}秒)", self.ctx.guild)


class CheckBilibiliCollectionView(View):

    def __init__(self, ctx, info_dict, timeout=10):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.info_dict = info_dict
        self.occur_time = utils.time()
        self.finish = False

    @discord.ui.button(label="确定", style=discord.ButtonStyle.grey,
                       custom_id="button_confirm")
    async def button_confirm_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.finish = True
        message = "这是一个合集, 请选择要播放的视频:\n"
        ep_info_list = []
        for item in self.info_dict["ugc_season"]["sections"][0]["episodes"]:
            ep_title = item["title"]
            ep_time_str = utils.convert_duration_to_time_str(item["arc"]["duration"])
            ep_info_list.append((ep_title, ep_time_str))

        menu_list = utils.make_playlist_page(ep_info_list, 10, indent=0)
        view = EpisodeSelectView(self.ctx, "bilibili_collection", self.info_dict, menu_list)
        await self.ctx.send(f"{menu_list[0]}\n第[1]页，共["
                            f"{len(menu_list)}]页\n已输入：",
                            view=view)

        await msg.edit_message(view=self)
        await self.ctx.delete()

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.grey,
                       custom_id="button_cancel")
    async def button_close_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.finish = True
        self.clear_items()
        await msg.edit_message(content="", view=self)

    async def on_timeout(self):
        if not self.finish:
            await self.ctx.delete()
        logger.rp(f"{self.occur_time}生成的合集查看选择栏已超时(超时时间为{self.timeout}秒)", self.ctx.guild)
