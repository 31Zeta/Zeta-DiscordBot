import discord
import sys
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from zeta_bot import (
    errors,
    language,
    utils,
    setting,
    log,
    member,
    guild,
    help
)

version = "0.10.0"
author = "炤铭Zeta (31Zeta)"
python_path = sys.executable
pycord_version = discord.__version__
update_time = "2023.**.**"

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

# 设置用户和Discord服务器管理
utils.create_folder("./data")
member_lib = member.MemberLibrary()
guild_lib = guild.GuildLibrary()

logger.rp("程序启动", "[系统]")


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
        logger.rp(f"用户 {ctx.user} 发送指令：<{operation}>", f"服务器：{ctx.guild}")
        return True
    elif member_lib.allow(ctx.user.id, operation):
        logger.rp(f"用户 {ctx.user} 发送指令：<{operation}>", f"服务器：{ctx.guild}")
        return True
    else:
        logger.rp(f"用户 {ctx.user} 发送指令：<{operation}>，{ctx.user} 所在用户组 [{user_group}] 权限不足，操作被拒绝",
                  f"服务器：{ctx.guild}")
        await ctx.respond("权限不足")
        return False


# 启动就绪时
@bot.event
async def on_ready():
    """
    当机器人启动完成时调用
    """

    current_time = utils.time()
    print(f"\n---------- 准备就绪 ----------\n")
    logger.rp(f"登录完成：以{bot.user}的身份登录，登录时间：{current_time}", "[系统]")

    # 启动定时清理器
    # cleaner_loop.start()
    # print("定时清理器已启动\n")

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


@bot.command(description="[管理员] 测试指令")
async def debug(ctx: discord.ApplicationContext):
    """
    测试用指令

    :param ctx: 指令原句
    :return:
    """
    if not await command_check(ctx):
        return

    print(ctx.response)
    print(type(ctx.response))
    print(str(ctx.response))

    await ctx.respond("测试结果已打印")


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


@bot.command(description=f"让{bot_name}加入语音频道")
async def join(ctx: discord.ApplicationContext, channel_name=None) -> bool:
    """
    让机器人加入指令发送者所在的语音频道并发送提示\n
    如果机器人已经加入一个频道则转移到新频道并发送提示
    如发送者未加入任何语音频道发送提示

    :param ctx: 指令原句
    :param channel_name: 要加入的频道名称
    :return: 布尔值，是否成功加入频道
    """
    if not await command_check(ctx):
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
        await ctx.respond(f"加入语音频道：-> ***{channel.name}***")
    # 机器人已经在一个频道的情况
    else:
        previous_channel = voice_client.channel
        await voice_client.disconnect(force=False)
        await channel.connect()
        await ctx.respond(f"转移语音频道：***{previous_channel}*** -> ***{channel.name}***")

    logger.rp(f"加入频道 {channel.name}", ctx.guild)
    return True


@bot.command(description=f"让{bot_name}离开语音频道")
async def leave(ctx) -> None:
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

    # 防止因退出频道自动删除正在播放的音频
    if voice_client.is_playing():
        current_audio = current_playlist.get_audio(0)
        current_playlist.insert_audio(current_audio, 0)
        guild_lib.get_guild(ctx).save()

    if voice_client is not None:
        last_channel = voice_client.channel
        await voice_client.disconnect()

        logger.rp(f"离开频道 {last_channel}", ctx.guild)

        await ctx.respond(f"离开语音频道：***{last_channel}***")

    else:
        await ctx.respond(f"{bot_name}没有连接到任何语音频道")


@bot.command(description=f"调整{bot_name}的语音频道音量")
async def volume(ctx, volume_num=None) -> None:
    if not await command_check(ctx):
        return

    guild_lib.check(ctx)
    voice_client = ctx.guild.voice_client
    current_volume = guild_lib.get_guild(ctx).get_voice_volume()

    if volume_num is None:
        await ctx.respond(f"当前音量为 **{current_volume}%**")

    elif volume_num == "up" or volume_num == "u":
        if current_volume + 20.0 >= 200:
            current_volume = 200.0
        else:
            current_volume += 20.0
        if voice_client.is_playing():
            voice_client.source.volume = current_volume / 100.0

        guild_lib.get_guild(ctx).set_voice_volume(current_volume)
        logger.rp(f"用户 {ctx.author} 已将音量设置为 {current_volume}%", ctx.guild)
        await ctx.respond(f"将音量提升至 **{current_volume}%**")

    elif volume_num == "down" or volume_num == "d":
        if current_volume - 20.0 <= 0.0:
            current_volume = 0.0
        else:
            current_volume -= 20.0
        if voice_client.is_playing():
            voice_client.source.volume = current_volume / 100.0

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
            if voice_client.is_playing():
                voice_client.source.volume = current_volume / 100.0
            guild_lib.get_guild(ctx).set_voice_volume(current_volume)
            logger.rp(f"用户 {ctx.author} 已将音量设置为 {current_volume}%", ctx.guild)
            await ctx.respond(f"将音量设置为 **{current_volume}%**")
