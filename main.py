import discord
import sys
from zeta_bot import *

version = "0.9.0"
author = "炤铭Zeta"
python_path = sys.executable
pycord_version = discord.__version__

# 初始化机器人设置
intents = discord.Intents.all()
bot = discord.Bot(help_command=None, case_insensitive=True, intents=intents)
startup_time = utils.time()

# log_name_time = startup_time.replace(":", "_")
# error_log_path = f"./logs/{log_name_time}_errors.log"
# log = log.Log()


@bot.event
async def on_error(exception):
    pass


@bot.event
async def on_application_command_error(ctx, exception):
    pass

if __name__ == "__main__":
    t = setting.Setting("./data/setting.json", setting.bot_setting_configs)
    print(t.list_all())
