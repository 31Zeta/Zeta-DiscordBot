"""
网易云音乐接口（直接请求网易云音乐，不依赖外部服务）

普通请求使用桌面客户端的eapi接口（网页版的部分接口会被风控拦截），扫码登录使用网页版weapi接口。
"""
from typing import *
import re
import json
import base64
import hashlib
import binascii
import secrets
import string

from Cryptodome.Cipher import AES

from zeta_bot.native_music.common import MusicError, USER_AGENT, load_config, load_cookie, parse_cookie, proxy, join_names

SOURCE = "netease"
NAME = "网易云音乐"

EAPI_HOST = "https://interface3.music.163.com/eapi"
EAPI_KEY = b"e82ckenh8dichen8"
CLIENT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 NeteaseMusicDesktop/3.0.18.203152"
CLIENT_COOKIE = "os=pc; appver=3.0.18.203152; osver=Microsoft-Windows-10; channel=netease"

WEAPI_HOST = "https://music.163.com/weapi"
WEAPI_PRESET_KEY = b"0CoJUm6Qyw8W8jud"
WEAPI_IV = b"0102030405060708"
WEAPI_PUBLIC_EXPONENT = 0x010001
WEAPI_MODULUS = int(
    "00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7",
    16,
)

LEVELS = ("standard", "higher", "exhigh", "lossless", "hires")


def _pkcs7(data: bytes) -> bytes:
    padding = 16 - len(data) % 16
    return data + bytes([padding]) * padding


def eapi_params(path: str, data: dict) -> dict:
    text = json.dumps(data, separators=(",", ":"))
    digest = hashlib.md5(f"nobody{path}use{text}md5forencrypt".encode("utf-8")).hexdigest()
    payload = f"{path}-36cd479b6b5-{text}-36cd479b6b5-{digest}".encode("utf-8")
    encrypted = AES.new(EAPI_KEY, AES.MODE_ECB).encrypt(_pkcs7(payload))
    return {"params": binascii.hexlify(encrypted).decode("ascii").upper()}


def weapi_params(data: dict) -> dict:
    def aes_cbc(text: bytes, key: bytes) -> bytes:
        return base64.b64encode(AES.new(key, AES.MODE_CBC, WEAPI_IV).encrypt(_pkcs7(text)))
    secret_key = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16)).encode("ascii")
    params = aes_cbc(aes_cbc(json.dumps(data, separators=(",", ":")).encode("utf-8"), WEAPI_PRESET_KEY), secret_key)
    encrypted_key = pow(int(binascii.hexlify(secret_key[::-1]), 16), WEAPI_PUBLIC_EXPONENT, WEAPI_MODULUS)
    return {"params": params.decode("ascii"), "encSecKey": format(encrypted_key, "x").zfill(256)}


async def request(session, path: str, data: dict) -> dict:
    """
    请求eapi接口，<path>以/api开头，例如 /api/v3/song/detail
    """
    cookie = CLIENT_COOKIE
    user_cookie = load_cookie(SOURCE)
    if user_cookie:
        cookie = f"{cookie}; {user_cookie}"
    headers = {"User-Agent": CLIENT_USER_AGENT, "Content-Type": "application/x-www-form-urlencoded", "Cookie": cookie}
    async with session.post(EAPI_HOST + path[len("/api"):], data=eapi_params(path, data), headers=headers, proxy=proxy()) as response:
        body = await response.read()
    try:
        result = json.loads(body)
    except ValueError:
        raise MusicError(f"网易云音乐接口返回了无效内容（HTTP {response.status}）", retryable=True)
    code = result.get("code")
    if code != 200:
        message = result.get("message") or result.get("msg") or ""
        raise MusicError(f"网易云音乐接口返回错误：{code} {message}".strip(), retryable=code in (-460, 503, 509))
    return result


async def request_weapi(session, path: str, data: dict) -> Tuple[dict, Dict[str, str]]:
    """
    请求网页版weapi接口，返回 (结果, 响应设置的Cookie)
    """
    headers = {"User-Agent": USER_AGENT, "Referer": "https://music.163.com/", "Content-Type": "application/x-www-form-urlencoded"}
    async with session.post(WEAPI_HOST + path, data=weapi_params(data), headers=headers, proxy=proxy()) as response:
        body = await response.read()
        cookies = {key: morsel.value for key, morsel in response.cookies.items()}
    try:
        return json.loads(body), cookies
    except ValueError:
        raise MusicError(f"网易云音乐接口返回了无效内容（HTTP {response.status}）", retryable=True)


# ---------------------------------------- 链接解析 ----------------------------------------
def parse_url(url: str) -> Tuple[str, str]:
    """
    返回 (类型, ID)，类型为 song / playlist / album
    """
    # 支持 song?id=1、song?userid=2&id=1、song/1/、#/my/m/music/playlist?id=1 等格式
    url = str(url)
    for kind in ("song", "playlist", "album"):
        match = re.search(rf"\b{kind}(?:\?(?:[^#\s]*&)?id=|/)(\d+)", url)
        if match:
            return kind, match.group(1)
    raise MusicError("无法识别的网易云音乐链接（支持单曲、歌单与专辑）")


# ---------------------------------------- 数据转换 ----------------------------------------
def to_song(track: dict, privilege: Optional[dict] = None) -> dict:
    album = track.get("al") or track.get("album") or {}
    privilege = privilege or track.get("privilege") or {}
    duration = track.get("dt") or track.get("duration") or 0
    return {
        "id": str(track.get("id")),
        "name": track.get("name") or "未知歌曲",
        "artist": join_names(track.get("ar") or track.get("artists")) or "未知歌手",
        "album": album.get("name") or "",
        "duration": int(duration) // 1000,
        "source": SOURCE,
        "cover": album.get("picUrl") or "",
        "fee": track.get("fee"),
        "status": privilege.get("st"),
    }


def song_url(song_id) -> str:
    return f"https://music.163.com/song?id={song_id}"


# ---------------------------------------- 接口 ----------------------------------------
async def search(session, query: str, num: int = 5) -> List[dict]:
    result = await request(session, "/api/cloudsearch/pc", {"s": query, "type": 1, "limit": num, "offset": 0, "total": True})
    return [to_song(track) for track in (result.get("result") or {}).get("songs") or []]


async def get_songs(session, song_ids: List[str]) -> List[dict]:
    songs = []
    for start in range(0, len(song_ids), 500):
        batch = song_ids[start:start + 500]
        result = await request(session, "/api/v3/song/detail", {"c": json.dumps([{"id": int(song_id)} for song_id in batch])})
        privileges = {str(item.get("id")): item for item in result.get("privileges") or []}
        songs.extend(to_song(track, privileges.get(str(track.get("id")))) for track in result.get("songs") or [])
    return songs


async def get_info(session, url: str) -> Tuple[str, str, str, List[dict]]:
    """
    返回 (类型, 标题, 封面, 歌曲列表)
    """
    kind, item_id = parse_url(url)
    if kind == "song":
        songs = await get_songs(session, [item_id])
        if not songs:
            raise MusicError("找不到该歌曲，可能已下架")
        return kind, songs[0]["name"], songs[0]["cover"], songs

    if kind == "playlist":
        result = await request(session, "/api/v6/playlist/detail", {"id": item_id, "n": 100000, "s": 8})
        playlist = result.get("playlist") or {}
        privileges = {str(item.get("id")): item for item in result.get("privileges") or []}
        tracks = {str(track.get("id")): to_song(track, privileges.get(str(track.get("id")))) for track in playlist.get("tracks") or []}
        track_ids = [str(item.get("id")) for item in playlist.get("trackIds") or []] or list(tracks.keys())
        # 歌单较长时接口只返回部分歌曲详情，其余按ID补全
        missing = [song_id for song_id in track_ids if song_id not in tracks]
        if missing:
            for song in await get_songs(session, missing):
                tracks[song["id"]] = song
        songs = [tracks[song_id] for song_id in track_ids if song_id in tracks]
        return kind, playlist.get("name") or "网易云音乐歌单", playlist.get("coverImgUrl") or "", songs

    result = await request(session, f"/api/v1/album/{item_id}", {})
    album = result.get("album") or {}
    songs = [to_song(track) for track in result.get("songs") or []]
    for song in songs:
        song["cover"] = song["cover"] or album.get("picUrl") or ""
    return kind, album.get("name") or "网易云音乐专辑", album.get("picUrl") or "", songs


async def get_stream(session, song: dict) -> Tuple[List[str], Optional[int], str]:
    """
    返回 (音频地址列表, 文件大小, 扩展名)
    """
    level = str(load_config().get("netease_level") or "exhigh").lower()
    if level not in LEVELS:
        level = "exhigh"
    encode_type = "flac" if level in ("lossless", "hires") else "mp3"
    result = await request(session, "/api/song/enhance/player/url/v1", {"ids": json.dumps([int(song["id"])]), "level": level, "encodeType": encode_type})
    data = (result.get("data") or [{}])[0]

    if data.get("url") and data.get("freeTrialInfo"):
        raise MusicError("该歌曲仅可试听，需要登录网易云音乐会员账号（data/cookies/netease.json）")
    if not data.get("url"):
        if song.get("status") == -100:
            raise MusicError("该歌曲在当前地区不可播放（网易云音乐版权地区限制），可在configs/music_config.json中设置代理")
        if song.get("fee") in (1, 4):
            raise MusicError("该歌曲需要网易云音乐会员或单独购买，请配置已登录的Cookie（data/cookies/netease.json）")
        raise MusicError("无法获取该歌曲的播放地址，歌曲可能已下架或存在版权限制")

    extension = str(data.get("type") or encode_type).lower()
    if extension not in ("mp3", "flac", "m4a", "aac", "ogg"):
        extension = "mp3"
    return [data["url"]], data.get("size") or None, extension


# ---------------------------------------- 扫码登录 ----------------------------------------
async def qr_login_create(session) -> Tuple[str, str]:
    """
    返回 (key, 二维码内容)
    """
    result, _ = await request_weapi(session, "/login/qrcode/unikey", {"type": 1})
    key = result.get("unikey")
    if not key:
        raise MusicError(f"获取登录二维码失败：{result.get('code')} {result.get('message') or ''}".strip())
    return key, f"https://music.163.com/login?codekey={key}"


async def qr_login_check(session, key: str) -> Tuple[int, str, Dict[str, str]]:
    """
    返回 (状态码, 说明, Cookie)
    状态码：800 二维码已过期，801 等待扫码，802 已扫码待确认，803 登录成功
    """
    result, cookies = await request_weapi(session, "/login/qrcode/client/login", {"key": key, "type": 1})
    code = int(result.get("code") or 0)
    if code == 803 and result.get("cookie"):
        cookies.update(parse_cookie(str(result["cookie"])))
    return code, str(result.get("message") or ""), cookies
