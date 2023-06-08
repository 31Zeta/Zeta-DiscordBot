import discord
import sys
import os
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from zeta_bot import (
    errors,
    language,
    utils,
    setting,
    log,
    member
)

version = "0.10.0"
author = "炤铭Zeta"
python_path = sys.executable
pycord_version = discord.__version__

# 多语言模块
lang = language.Lang()
_ = lang.get_string
printl = lang.printl

# 初始化机器人设置
intents = discord.Intents.all()
bot = discord.Bot(help_command=None, case_insensitive=True, intents=intents)
startup_time = utils.time()
utils.create_folder("./data")
lang_setting = setting.Setting("./data/language.json", setting.language_setting_configs)
lang.set_system_language(lang_setting.value("language"))
setting = setting.Setting("./data/settings.json", setting.bot_setting_configs, lang_setting.value("language"))

utils.create_folder("./logs")
log_name_time = startup_time.replace(":", "_")
error_log_path = f"./logs/{log_name_time}_errors.log"
log_path = f"./logs/{log_name_time}.log"
logger = log.Log(error_log_path, log_path, setting.value("log"))
logger.rec_p("程序启动", "[系统]")

utils.create_folder("./data/member")
# member_library = member.MemberLibrary()


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


# 启动就绪时
@bot.event
async def on_ready():
    """
    当机器人启动完成时调用
    """

    current_time = utils.time()
    print(f"---------- 准备就绪 ----------\n")
    logger.rec_p(f"准备就绪 以{bot.user}的身份登录，登录时间：{current_time}", "[系统]")

    # 启动定时清理器
    # cleaner_loop.start()
    # print("定时清理器已启动\n")

    # 启动定时任务框架
    scheduler_1 = AsyncIOScheduler()
    scheduler_2 = AsyncIOScheduler()

    if setting.value("auto_reboot"):
        # 设置自动重启
        ar_timezone = "Asia/Shanghai"
        ar_time = utils.time_split(setting.value("ar_time"))
        scheduler_1.add_job(
            auto_reboot_function, CronTrigger(
                timezone=ar_timezone, hour=ar_time[0],
                minute=ar_time[1], second=ar_time[2]
            )
        )

        if setting.value("ar_reminder"):
            # 设置自动重启提醒
            ar_r_time = utils.time_split(setting.value("ar_reminder_time"))
            scheduler_2.add_job(
                auto_reboot_reminder_function, CronTrigger(
                    timezone=ar_timezone, hour=ar_r_time[0],
                    minute=ar_r_time[1], second=ar_r_time[2]
                )
            )

        scheduler_1.start()
        scheduler_2.start()

        logger.rec_p(
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


async def auto_reboot_function():
    """
    用于执行定时重启，如果<auto_reboot_announcement>为True则广播重启消息
    """
    current_time = utils.time()
    # audio_library.save()
    # user_library.save()
    if setting.value("ar_announcement"):
        for guild in bot.guilds:
            voice_client = guild.voice_client
            if voice_client is not None:
                await guild.text_channels[0].send(f"{current_time} 开始执行自动定时重启")
    os.execl(python_path, python_path, * sys.argv)


async def auto_reboot_reminder_function():
    """
    向机器人仍在语音频道中的所有服务器的第一个文字频道发送即将重启通知
    """
    ar_time = setting.value("ar_time")
    for guild in bot.guilds:
        voice_client = guild.voice_client
        if voice_client is not None:
            await guild.text_channels[0].send(f"注意：将在{ar_time}时自动重启")
