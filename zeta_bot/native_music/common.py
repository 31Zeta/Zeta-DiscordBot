"""
内置音乐平台接口的公共部分：配置、Cookie、网络请求
"""
from typing import *
import os
import json
from pathlib import Path

import aiohttp

import errors
import utils

# 配置文件（首次运行自动生成）
#   proxy           代理地址（仅支持HTTP代理），例如 http://127.0.0.1:7890，留空为不使用
#   netease_level   网易云音乐音质：standard（标准）/ higher（较高）/ exhigh（极高）/ lossless（无损）/ hires
#   qq_quality      QQ音乐音质：320 / 128 / aac（无法获取时自动降级）
CONFIG_PATH = "./configs/music_config.json"
DEFAULT_CONFIG = {
    "proxy": "",
    "netease_level": "exhigh",
    "qq_quality": "320",
}

# 与go-music-api模块共用的Cookie目录：data/cookies/<平台>.json
COOKIE_DIRECTORY = Path(__file__).resolve().parent.parent.parent / "data" / "cookies"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

_config: Optional[dict] = None


class MusicError(Exception):
    """
    音乐平台操作失败，message会直接显示给用户
    """
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.retryable = retryable


def load_config() -> dict:
    global _config
    if _config is None:
        config = dict(DEFAULT_CONFIG)
        if os.path.exists(CONFIG_PATH):
            try:
                loaded = utils.json_load(CONFIG_PATH)
                if isinstance(loaded, dict):
                    config.update({key: loaded[key] for key in loaded if key in DEFAULT_CONFIG})
            except errors.JSONFileError:
                pass
        else:
            try:
                os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
                utils.json_save(CONFIG_PATH, config)
            except OSError:
                pass
        _config = config
    return _config


def proxy() -> Optional[str]:
    value = str(load_config().get("proxy") or "").strip()
    return value or None


def load_cookie(source: str) -> str:
    """
    读取data/cookies/<source>.json中的Cookie，返回Cookie请求头字符串（未配置时返回空字符串）
    支持浏览器插件导出的JSON、name=value字符串以及扫码登录保存的格式
    """
    path = COOKIE_DIRECTORY / f"{source}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError):
        return ""
    # 解析逻辑与go-music-api模块保持一致
    from zeta_bot.go_music import extract_cookie
    try:
        return extract_cookie(data, source)
    except (RuntimeError, RecursionError):
        return ""


def parse_cookie(cookie: str) -> Dict[str, str]:
    result = {}
    for part in cookie.split(";"):
        name, separator, value = part.strip().partition("=")
        if separator and name:
            result[name.strip()] = value.strip()
    return result


def save_cookie(source: str, cookies: Dict[str, str]) -> Path:
    COOKIE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    path = COOKIE_DIRECTORY / f"{source}.json"
    utils.json_save(str(path), cookies)
    return path


def new_session(total_timeout: Optional[float] = 20) -> aiohttp.ClientSession:
    timeout = aiohttp.ClientTimeout(total=total_timeout, connect=10, sock_read=30)
    return aiohttp.ClientSession(timeout=timeout)


def join_names(items: Iterable[Any], key: str = "name") -> str:
    names = [str(item.get(key)) for item in items or [] if isinstance(item, dict) and item.get(key)]
    return " / ".join(names)
