import utils
from zeta_bot.resource import DownloadType


class Audio:
    def __init__(self, title: str, uid: str, source: str, source_id: str, download_type: DownloadType, path: str, duration: int) -> None:
        self._title = title
        self._uid = uid
        self._source = source
        self._source_id = source_id
        self._download_type = download_type
        self._path = path
        self._duration = duration
        self._duration_str = utils.convert_duration_to_str(duration)
        self._cover_path = None
        self._cover_url = None

    def __str__(self) -> str:
        return f"{self._title} [{self._duration_str}]"

    def __repr__(self) -> str:
        return f"<Audio对象：{self._title}>"

    def get_title(self) -> str:
        return self._title

    def get_uid(self) -> str:
        return self._uid

    def get_source(self) -> str:
        return self._source

    def get_source_id(self) -> str:
        return self._source_id

    def get_download_type(self) -> DownloadType:
        return self._download_type

    def get_path(self) -> str:
        return self._path

    def get_duration(self) -> int:
        return self._duration

    def get_duration_str(self) -> str:
        return self._duration_str

    def get_cover_path(self) -> str:
        return self._cover_path

    def get_cover_url(self) -> str:
        return self._cover_url

    def set_cover_path(self, cover_path: str) -> None:
        self._cover_path = cover_path

    def set_cover_url(self, cover_url: str) -> None:
        self._cover_url = cover_url

    def encode(self) -> dict:
        return {
            "title": self._title,
            "uid": self._uid,
            "source": self._source,
            "source_id": self._source_id,
            "download_type": self._download_type,
            "path": self._path,
            "duration": self._duration,
            "duration_str": self._duration_str,
            "cover_path": self._cover_path,
            "cover_url": self._cover_url
        }


def audio_decoder(info_dict: dict) -> Audio:
    try:
        download_type = DownloadType.decode(info_dict["download_type"])
    except ValueError:
        download_type = DownloadType.UNKNOWN

    decoded_audio = Audio(
        title=info_dict["title"],
        uid=info_dict["uid"],
        source=info_dict["source"],
        source_id=info_dict["source_id"],
        download_type=download_type,
        path=info_dict["path"],
        duration=info_dict["duration"],
    )

    if info_dict["cover_path"] is not None:
        decoded_audio.set_cover_path(info_dict["cover_path"])
    if info_dict["cover_url"] is not None:
        decoded_audio.set_cover_url(info_dict["cover_url"])
    return decoded_audio
