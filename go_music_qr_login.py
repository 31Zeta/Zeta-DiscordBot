from typing import *
import asyncio
import os
import errors
import utils
from zeta_bot import setting, output_console

# 读取设置
system_setting = setting.Setting("./configs/system_config.json", setting.bot_setting_configs)
go_music_url = system_setting.value("go_music_api_url")

# 设置控制台日志记录器
LOG_DIRECTORY_PATH = "./logs"
os.makedirs(LOG_DIRECTORY_PATH, exist_ok=True)
console = output_console.Console(LOG_DIRECTORY_PATH, "QR_Login", system_setting.value("log"))

async def main(target_source):
    try:
        from zeta_bot.go_music import qr_login
        qr_login_result = await qr_login(target_source, go_music_url, raise_exception=True)
        if qr_login_result:
            await console.rp(f"登录成功，Cookies 已保存至：{qr_login_result.result['cookie_path']}", message_type=utils.PrintType.CAUTION)
        else:
            await console.rp(f"{qr_login_result.message}\n返回：{qr_login_result.result}", message_type=utils.PrintType.ERROR)
    except Exception as e:
        await console.on_error(e)

if __name__ == "__main__":
    utils.cp("请选择要登录的平台", message_type=utils.PrintType.TITLE, gap=True)
    source = utils.ci_select("选项：netease, qq, qq_wx, kugou, bilibili\n请输入", options={"netease", "qq", "qq_wx", "kugou", "bilibili"})
    asyncio.run(main(source))
