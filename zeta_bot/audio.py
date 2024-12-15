from zeta_bot import (
    utils
)

class Audio:

    def __init__(self, title: str, source: str, source_id: str, path: str, duration: int) -> None:
        self._title = title
        self._source = source
        self._source_id = source_id
        self._path = path
        self._duration = duration
        self._duration_str = utils.convert_duration_to_str(duration)

    def __str__(self) -> str:
        return f"{self._title} [{self._duration_str}]"

    def __repr__(self) -> str:
        return f"<Audio对象：{self._title}>"

    def get_title(self) -> str:
        return self._title

    def get_source(self) -> str:
        return self._source

    def get_source_id(self) -> str:
        return self._source_id

    def get_path(self) -> str:
        return self._path

    def get_duration(self) -> int:
        return self._duration

    def get_duration_str(self) -> str:
        return self._duration_str

    def encode(self) -> dict:
        return {
            "title": self._title,
            "source": self._source,
            "source_id": self._source_id,
            "path": self._path,
            "duration": self._duration,
            "duration_str": self._duration_str
        }


def audio_decoder(info_dict: dict) -> Audio:
    return Audio(
        info_dict["title"],
        info_dict["source"],
        info_dict["source_id"],
        info_dict["path"],
        info_dict["duration"]
    )
