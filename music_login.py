"""
音乐平台账号登录（使用内置接口，不需要go-music-api）

    python music_login.py netease   网易云音乐扫码登录，Cookie保存至 data/cookies/netease.json
    python music_login.py qq        显示QQ音乐Cookie的配置方法

登录后可以播放账号有权限的歌曲（例如会员歌曲），地区版权限制不受登录影响。
"""
import os
import sys
import asyncio

import qrcode

from zeta_bot import output_console

LOG_DIRECTORY_PATH = "./logs"
os.makedirs(LOG_DIRECTORY_PATH, exist_ok=True)
output_console.Console(LOG_DIRECTORY_PATH, "music_login", False)

from zeta_bot.native_music import netease
from zeta_bot.native_music.common import MusicError, new_session, save_cookie, COOKIE_DIRECTORY

QR_IMAGE_PATH = "./netease_login_qr.png"
QR_TIMEOUT_SECONDS = 180


async def netease_login() -> bool:
    async with new_session() as session:
        key, content = await netease.qr_login_create(session)

        qr = qrcode.QRCode(border=1)
        qr.add_data(content)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
        qr.make_image().save(QR_IMAGE_PATH)
        print(f"\n请使用网易云音乐App扫描上方二维码登录（如果二维码显示不完整，可以打开图片 {os.path.abspath(QR_IMAGE_PATH)} 扫描）\n")

        try:
            scanned = False
            for _ in range(QR_TIMEOUT_SECONDS // 2):
                await asyncio.sleep(2)
                code, message, cookies = await netease.qr_login_check(session, key)
                if code == 802 and not scanned:
                    scanned = True
                    print("已扫码，请在手机上确认登录")
                elif code == 800:
                    print("二维码已过期，请重新运行本程序")
                    return False
                elif code == 803:
                    if not cookies.get("MUSIC_U"):
                        print("登录成功，但没有获取到登录凭证（MUSIC_U），请重试")
                        return False
                    path = save_cookie(netease.SOURCE, cookies)
                    print(f"登录成功，Cookie已保存至：{path}\n重启机器人后生效")
                    return True
                elif code not in (801, 802):
                    print(f"登录状态异常：{code} {message}")
            print("等待超时，请重新运行本程序")
            return False
        finally:
            if os.path.exists(QR_IMAGE_PATH):
                os.remove(QR_IMAGE_PATH)


def qq_instructions() -> None:
    print(
        "QQ音乐暂不支持扫码登录，请按以下方法配置Cookie：\n"
        "  1. 在浏览器中打开 https://y.qq.com 并登录\n"
        "  2. 使用Cookie导出插件（例如 Cookie-Editor）导出JSON格式的Cookie\n"
        f"  3. 将内容粘贴到 {COOKIE_DIRECTORY / 'qq.json'} 中并保存\n"
        "  4. 重启机器人\n"
        "也可以直接写入 {\"uin\": \"QQ号\", \"qm_keyst\": \"...\"} 格式的内容"
    )


if __name__ == "__main__":
    platform = sys.argv[1].lower() if len(sys.argv) > 1 else input("请选择要登录的平台（netease / qq）：").strip().lower()
    if platform in ("netease", "163", "网易云", "网易云音乐"):
        try:
            asyncio.run(netease_login())
        except MusicError as e:
            print(f"登录失败：{e.message}")
    elif platform in ("qq", "qq音乐"):
        qq_instructions()
    else:
        print("不支持的平台，请输入 netease 或 qq")
