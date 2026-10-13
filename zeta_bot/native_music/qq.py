"""
QQ音乐接口（直接请求QQ音乐，不依赖外部服务）
"""
from typing import *
import re
import json
import random
import asyncio

from zeta_bot.native_music.common import MusicError, USER_AGENT, load_config, load_cookie, parse_cookie, proxy, join_names

SOURCE = "qq"
NAME = "QQ音乐"

MUSICU_URL = "https://u.y.qq.com/cgi-bin/musicu.fcg"
SEARCH_URL = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
PAGE_SIZE = 500

# 音质：(文件名前缀, 扩展名)，按顺序尝试，无法获取时自动降级
QUALITY_LADDER = {
    "320": [("M800", "mp3"), ("M500", "mp3"), ("C400", "m4a")],
    "128": [("M500", "mp3"), ("C400", "m4a")],
    "aac": [("C400", "m4a")],
}


def _login() -> Tuple[str, str, str, bool]:
    """
    返回 (uin, 登录凭证, Cookie字符串, 是否为微信登录)
    """
    cookie = load_cookie(SOURCE)
    values = parse_cookie(cookie)
    wechat = "wxuin" in values and not values.get("uin")
    uin = values.get("uin") or values.get("wxuin") or values.get("p_uin") or "0"
    uin = re.sub(r"^o0*", "", uin) or "0"
    authst = values.get("qm_keyst") or values.get("qqmusic_key") or ""
    return uin, authst, cookie, wechat


async def request(session, module: str, method: str, param: dict, client: Tuple[int, int] = (24, 0)) -> dict:
    """
    <client>为客户端类型与版本 (ct, cv)，部分接口（例如搜索）只响应桌面客户端
    """
    uin, authst, cookie, wechat = _login()
    comm = {"ct": client[0], "cv": client[1], "uin": uin}
    if authst:
        comm["authst"] = authst
        comm["tmeLoginType"] = 1 if wechat else 2
    payload = {"comm": comm, "req": {"module": module, "method": method, "param": param}}
    headers = {"User-Agent": USER_AGENT, "Referer": "https://y.qq.com/", "Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    async with session.post(MUSICU_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers=headers, proxy=proxy()) as response:
        body = await response.read()
    try:
        result = json.loads(body)
    except ValueError:
        raise MusicError(f"QQ音乐接口返回了无效内容（HTTP {response.status}）", retryable=True)
    req = result.get("req") or {}
    if result.get("code") != 0 or req.get("code") != 0:
        code = req.get("code", result.get("code"))
        if code == 404:
            raise MusicError("找不到该资源，可能已下架或链接有误")
        raise MusicError(f"QQ音乐接口返回错误：{code}", retryable=True)
    return req.get("data") or {}


# ---------------------------------------- 链接解析 ----------------------------------------
def parse_url(url: str) -> Tuple[str, str, str]:
    """
    返回 (类型, ID, ID类型)，类型为 song / playlist / album，ID类型为 mid / id
    """
    url = str(url)
    patterns = [
        ("song", "mid", r"songDetail/(\w+)"),
        ("song", "mid", r"/song/(\w+)\.html"),
        ("song", "mid", r"\bsongmid=(\w+)"),
        ("song", "id", r"\bsongid=(\d+)"),
        ("playlist", "id", r"/playlist/(\d+)"),
        ("playlist", "id", r"\bdisstid=(\d+)"),
        ("playlist", "id", r"(?:taoge|playlist)\.html\?(?:[^#\s]*&)?id=(\d+)"),
        ("album", "mid", r"albumDetail/(\w+)"),
        ("album", "mid", r"/album/(\w+)\.html"),
        ("album", "mid", r"\balbummid=(\w+)"),
    ]
    for kind, id_type, pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return kind, match.group(1), id_type
    raise MusicError("无法识别的QQ音乐链接（支持单曲、歌单与专辑）")


# ---------------------------------------- 数据转换 ----------------------------------------
def to_song(track: dict) -> dict:
    album = track.get("album") or {}
    album_mid = album.get("mid") or ""
    file_info = track.get("file") or {}
    return {
        "id": track.get("mid"),
        "song_id": track.get("id"),
        "media_mid": file_info.get("media_mid") or track.get("mid"),
        "name": track.get("name") or track.get("title") or "未知歌曲",
        "artist": join_names(track.get("singer")) or "未知歌手",
        "album": album.get("name") or "",
        "duration": int(track.get("interval") or 0),
        "source": SOURCE,
        "cover": f"https://y.qq.com/music/photo_new/T002R300x300M000{album_mid}.jpg" if album_mid else "",
        "pay_play": (track.get("pay") or {}).get("pay_play"),
    }


def song_url(mid: str) -> str:
    return f"https://y.qq.com/n/ryqq/songDetail/{mid}"


# ---------------------------------------- 接口 ----------------------------------------
async def _search_web(session, query: str, num: int) -> List[dict]:
    params = {"w": query, "format": "json", "p": 1, "n": num, "cr": 1, "new_json": 1}
    headers = {"User-Agent": USER_AGENT, "Referer": "https://y.qq.com/"}
    async with session.get(SEARCH_URL, params=params, headers=headers, proxy=proxy()) as response:
        body = await response.read()
    try:
        result = json.loads(body)
    except ValueError:
        return []
    return ((result.get("data") or {}).get("song") or {}).get("list") or []


async def search(session, query: str, num: int = 5) -> List[dict]:
    # 优先使用网页搜索接口；桌面客户端搜索接口频率限制较严格（错误码2001），作为备用
    tracks = await _search_web(session, query, num)
    if not tracks:
        for attempt in range(2):
            try:
                data = await request(session, "music.search.SearchCgiService", "DoSearchForQQMusicDesktop",
                                     {"query": query, "search_type": 0, "num_per_page": num, "page_num": 1}, client=(19, 1859))
                tracks = ((data.get("body") or {}).get("song") or {}).get("list") or []
            except MusicError:
                if attempt == 1:
                    raise
            if tracks:
                break
            await asyncio.sleep(1.5)
    return [to_song(track) for track in tracks if track.get("mid")]


async def get_info(session, url: str) -> Tuple[str, str, str, List[dict]]:
    """
    返回 (类型, 标题, 封面, 歌曲列表)
    """
    kind, item_id, id_type = parse_url(url)

    if kind == "song":
        if id_type == "mid":
            data = await request(session, "music.pf_song_detail_svr", "get_song_detail_yqq", {"song_mid": item_id})
            tracks = [data.get("track_info")] if data.get("track_info") else []
        else:
            data = await request(session, "music.trackInfo.UniformRuleCtrl", "CgiGetTrackInfo", {"ids": [int(item_id)], "types": [0]})
            tracks = data.get("tracks") or []
        songs = [to_song(track) for track in tracks if track and track.get("mid")]
        if not songs:
            raise MusicError("找不到该歌曲，可能已下架")
        return kind, songs[0]["name"], songs[0]["cover"], songs

    if kind == "playlist":
        songs, title, cover, begin = [], "QQ音乐歌单", "", 0
        while True:
            data = await request(session, "music.srfDissInfo.aiDissInfo", "uniform_get_Dissinfo",
                                 {"disstid": int(item_id), "enc_host_uin": "", "tag": 1, "userinfo": 1, "song_begin": begin, "song_num": PAGE_SIZE})
            info = data.get("dirinfo") or {}
            title, cover = info.get("title") or title, info.get("picurl") or cover
            page = data.get("songlist") or []
            songs.extend(to_song(track) for track in page if track.get("mid"))
            begin += len(page)
            if not page or begin >= int(data.get("total_song_num") or 0):
                break
        if not songs:
            raise MusicError("歌单为空或无法访问（私密歌单需要登录）")
        return kind, title, cover, songs

    detail = await request(session, "music.musichallAlbum.AlbumInfoServer", "GetAlbumDetail", {"albumMid": item_id})
    title = (detail.get("basicInfo") or {}).get("albumName") or "QQ音乐专辑"
    songs, begin = [], 0
    while True:
        data = await request(session, "music.musichallAlbum.AlbumSongList", "GetAlbumSongList",
                             {"albumMid": item_id, "begin": begin, "num": 100, "order": 2})
        page = data.get("songList") or []
        songs.extend(to_song(item.get("songInfo") or {}) for item in page if (item.get("songInfo") or {}).get("mid"))
        begin += len(page)
        if not page or begin >= int(data.get("totalNum") or 0):
            break
    cover = f"https://y.qq.com/music/photo_new/T002R300x300M000{item_id}.jpg"
    return kind, title, cover, songs


async def get_stream(session, song: dict) -> Tuple[List[str], Optional[int], str]:
    """
    返回 (音频地址列表（多个CDN）, 文件大小, 扩展名)
    """
    quality = str(load_config().get("qq_quality") or "320").lower()
    ladder = QUALITY_LADDER.get(quality, QUALITY_LADDER["320"])
    uin, _, _, _ = _login()
    media_mid = song.get("media_mid") or song["id"]
    filenames = [f"{prefix}{media_mid}.{extension}" for prefix, extension in ladder]
    data = await request(session, "vkey.GetVkeyServer", "CgiGetVkey", {
        "guid": str(random.randint(10 ** 9, 10 ** 10 - 1)),
        "songmid": [song["id"]] * len(filenames),
        "songtype": [0] * len(filenames),
        "filename": filenames,
        "uin": uin,
        "loginflag": 1,
        "platform": "20",
    })
    servers = [server for server in data.get("sip") or [] if server] or ["https://isure.stream.qqmusic.qq.com/"]
    for (prefix, extension), info in zip(ladder, data.get("midurlinfo") or []):
        purl = info.get("purl")
        if purl:
            return [server + purl for server in servers], None, extension

    if song.get("pay_play") == 1:
        raise MusicError("该歌曲需要QQ音乐会员，请配置已登录的Cookie（data/cookies/qq.json）")
    if uin == "0":
        raise MusicError("无法获取该歌曲的播放地址，该歌曲可能需要登录QQ音乐账号（data/cookies/qq.json）或存在版权限制")
    raise MusicError("无法获取该歌曲的播放地址，可能存在版权或地区限制")
