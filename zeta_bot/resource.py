from typing import *
from enum import Enum
import re
import os
import utils

import errors
from zeta_bot.decorator import Singleton


RESOURCE_HANDLER_JSON_PATH = "./configs/resource_handler.json"


class MediaPlatform(Enum):
    """
    媒体平台
    """
    BILIBILI = "哔哩哔哩"
    QQ = "QQ音乐"
    NETEASE = "网易云音乐"
    KUGOU = "酷狗音乐"
    KUWO = "酷我音乐"
    MIGU = "咪咕音乐"
    QIANQIAN = "千千音乐"
    SODA = "汽水音乐"
    FIVESING = "5sing"
    JAMENDO = "Jamendo"
    JOOX = "JOOX"
    YOUTUBE = "YouTube"
    UNKNOWN = "未知来源"

    def encode(self) -> str:
        return str(self.name)

    @classmethod
    def decode(cls, name: str) -> "MediaPlatform":
        try:
            return cls[name]
        except KeyError:
            return MediaPlatform.UNKNOWN


class DownloadHandler(Enum):
    """
    下载器
    """
    BILIBILI_API_PYTHON = "bilibili-api"
    GO_MUSIC_API = "go-music-api"
    YT_DLP = "yt-dlp"

    def encode(self) -> str:
        return str(self.name)

    @classmethod
    def decode(cls, name: str) -> "DownloadHandler":
        try:
            return cls[name]
        except KeyError as e:
            raise ValueError("未知下载器") from e


class DownloadType(Enum):
    """
    下载类型
    """
    BILIBILI_SINGLE = ("哔哩哔哩视频", MediaPlatform.BILIBILI)
    BILIBILI_P = ("哔哩哔哩分P视频", MediaPlatform.BILIBILI)
    BILIBILI_COLLECTION = ("哔哩哔哩合集视频", MediaPlatform.BILIBILI)
    QQ_SINGLE = ("QQ音乐单曲", MediaPlatform.QQ)
    QQ_PLAYLIST = ("QQ音乐歌单", MediaPlatform.QQ)
    QQ_ALBUM = ("QQ音乐专辑", MediaPlatform.QQ)
    NETEASE_SINGLE = ("网易云音乐单曲", MediaPlatform.NETEASE)
    NETEASE_PLAYLIST = ("网易云音乐歌单", MediaPlatform.NETEASE)
    NETEASE_ALBUM = ("网易云音乐专辑", MediaPlatform.NETEASE)
    YOUTUBE_SINGLE = ("YouTube标准视频", MediaPlatform.YOUTUBE)
    YOUTUBE_PLAYLIST = ("YouTube播放列表", MediaPlatform.YOUTUBE)
    UNKNOWN = ("未知下载类型", MediaPlatform.UNKNOWN)

    def __init__(self, label: str, platform: MediaPlatform):
        self.label = label
        self.platform = platform

    def encode(self) -> str:
        return str(self.name)

    @classmethod
    def decode(cls, name: str) -> "DownloadType":
        try:
            return cls[name]
        except KeyError as e:
            raise ValueError("不支持的下载类") from e


class LinkType(Enum):
    """
    链接类型
    """
    BILIBILI_URL = ("哔哩哔哩链接", MediaPlatform.BILIBILI, r"bilibili\.com", r"bilibili\.com[^ ]*", "https://", False)
    BILIBILI_SHORT_URL = ("哔哩哔哩短链", MediaPlatform.BILIBILI, r"b23\.tv", r"b23\.tv[^ ]*", "https://", True)
    BILIBILI_BVID = ("哔哩哔哩BV号", MediaPlatform.BILIBILI, r"BV(\d|[a-zA-Z]){10}", r"BV(\d|[a-zA-Z]){10}", "", False)
    QQ_URL = ("QQ音乐链接", MediaPlatform.QQ, r"(?<!c6\.)y\.qq\.com", r"(?<!c6\.)y\.qq\.com[^ ]*", "https://", False)  # 只有y前面的子域名不为c6才被判断为正常链接
    QQ_SHORT_URL = ("QQ音乐短链", MediaPlatform.QQ, r"c6\.y\.qq\.com", r"c6\.y\.qq\.com[^ ]*", "https://", True)
    NETEASE_URL = ("网易云音乐链接", MediaPlatform.NETEASE, r"music\.163\.com", r"music\.163\.com[^ ]*", "https://", False)
    NETEASE_SHORT_URL = ("网易云音乐链接短链", MediaPlatform.NETEASE, r"163cn\.tv", r"163cn\.tv[^ ]*", "https://", True)
    YOUTUBE_URL = ("YouTube链接", MediaPlatform.YOUTUBE, r"youtube\.com", r"youtube\.com[^ ]*", "https://", False)
    YOUTUBE_SHORT_URL = ("YouTube短链", MediaPlatform.YOUTUBE, r"youtu\.be", r"youtu\.be[^ ]*", "https://", True)
    UNKNOWN = ("未知连接", MediaPlatform.UNKNOWN, "", "", "", False)

    def __init__(self, label: str, platform: MediaPlatform, search_pattern: str, format_pattern: str, format_prefix: str, need_redirect: bool):
        self.label = label
        self.platform = platform
        self.search_pattern = search_pattern
        self.format_pattern = format_pattern
        self.format_prefix = format_prefix
        self.need_redirect = need_redirect

    def format_url(self, url: str) -> str:
        """
        返回通过<self.format_pattern>格式化后的URL
        """
        url_position = re.search(self.format_pattern, url)
        if url_position is None:
            return url
        url_position = url_position.span()
        url = self.format_prefix + url[url_position[0]:url_position[1]]
        return url

    @classmethod
    def check(cls, query: str) -> Tuple["LinkType", str]:
        """
        检查输入的字符串属于哪种类型，并按对应的方式进行格式化
        如果未能匹配将会返回LinkType.UNKNOWN以及原字符串
        """
        for member in cls:
            if re.search(member.search_pattern, query) is not None:
                formated_url = member.format_url(query)
                return member, formated_url
        return LinkType.UNKNOWN, query

    def encode(self) -> str:
        return str(self.name)

    @classmethod
    def decode(cls, name: str) -> "LinkType":
        try:
            return cls[name]
        except KeyError as e:
            raise ValueError("不支持的下载类") from e


DEFAULT_DOWNLOAD_HANDLER: Dict[MediaPlatform, DownloadHandler] = {
    MediaPlatform.BILIBILI: DownloadHandler.BILIBILI_API_PYTHON,
    MediaPlatform.QQ: DownloadHandler.GO_MUSIC_API,
    MediaPlatform.NETEASE: DownloadHandler.GO_MUSIC_API,
    MediaPlatform.YOUTUBE: DownloadHandler.YT_DLP,
}


def write_default_download_handler_json(json_path: str):
    converted_dict = {}
    for platform in DEFAULT_DOWNLOAD_HANDLER.keys():
        converted_dict[platform.encode()] = DEFAULT_DOWNLOAD_HANDLER[platform]
    utils.json_save(json_path, converted_dict)


@Singleton
class ResourceClassifier:
    def __init__(self):
        if not os.path.exists(RESOURCE_HANDLER_JSON_PATH):
            write_default_download_handler_json(RESOURCE_HANDLER_JSON_PATH)

        self.handler_map: Dict[MediaPlatform, DownloadHandler] = DEFAULT_DOWNLOAD_HANDLER.copy()

        try:
            raw_handler_map: dict = utils.json_load(RESOURCE_HANDLER_JSON_PATH)
        except errors.JSONFileError:
            write_default_download_handler_json(RESOURCE_HANDLER_JSON_PATH)
        else:
            for platform_str in raw_handler_map.keys():
                platform = MediaPlatform.decode(platform_str)
                if platform is not MediaPlatform.UNKNOWN:
                    try:
                        download_handler = DownloadHandler.decode(raw_handler_map[platform_str])
                    except ValueError:
                        continue
                    else:
                        self.handler_map[platform] = download_handler

    def handler(self, query: Union[str, MediaPlatform, DownloadType, LinkType]) -> Optional[DownloadHandler]:
        """
        返回输入的查询对象对应的下载器
        """
        if isinstance(query, MediaPlatform):
            return self.handler_map.get(query, None)
        elif isinstance(query, DownloadType):
            return self.handler_map.get(query.platform, None)
        elif isinstance(query, LinkType):
            return self.handler_map.get(query.platform, None)

        link_type, formated_url = LinkType.check(query)
        return self.handler_map.get(link_type.platform, None)

    def check(self, query: str) -> Tuple[str, LinkType, Optional[DownloadHandler]]:
        """
        返回查询对象的 (格式化链接, LinkType, DownloadHandler)
        """
        link_type, formated_url = LinkType.check(query)
        return formated_url, link_type, self.handler_map.get(link_type.platform, None)
