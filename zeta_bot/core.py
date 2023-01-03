import discord
import sys
from zeta_bot import errors, utils, setting, log

version = "0.10.0"
author = "炤铭Zeta"
python_path = sys.executable
pycord_version = discord.__version__

# 初始化机器人设置
intents = discord.Intents.all()
bot = discord.Bot(help_command=None, case_insensitive=True, intents=intents)
startup_time = utils.time()

utils.create_folder("./data")
setting = setting.Setting("./data/setting.json", setting.bot_setting_configs)

utils.create_folder("./log")
log_name_time = startup_time.replace(":", "_")
error_log_path = f"./logs/{log_name_time}_errors.log"
log_path = f"./logs/{log_name_time}.log"
logger = log.Log(error_log_path, log_path, setting.value("log"))


def start(mode: str) -> None:
    """
    根据模式启动程序
    """
    if mode == "normal":
        run()
    elif mode == "setting":
        pass
    elif mode == "reset":
        pass


def run() -> None:
    """启动机器人"""
    try:
        bot.run(setting.value("token"))
    except discord.errors.LoginFailure:
        print("登录失败，请检查Discord机器人令牌是否正确，在启动指令后添加\" --mode=setting\"来修改设置")


@bot.event
async def on_error(exception):
    logger.on_error(exception)


@bot.event
async def on_application_command_error(ctx, exception):
    logger.on_application_command_error(ctx, exception)
