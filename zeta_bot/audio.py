from zeta_bot import (
    utils
)


class Audio:

    def __init__(self, title: str, source: str, source_id: str, path: str, duration: int) -> None:
        self.title = title
        self.source = source
        self.source_id = source_id
        self.path = path
        self.duration = duration
        self.time_str = utils.convert_duration_to_time_str(duration)

    def __str__(self) -> str:
        if self.time_str != "N/A":
            return f"{self.title} [{self.time_str}]"
        else:
            return self.title

    def encode(self) -> dict:
        return {
            "title": self.title,
            "source": self.source,
            "source_id": self.source_id,
            "path": self.path,
            "duration": self.duration,
            "time_str": self.time_str
        }


def audio_decoder(info_dict: dict) -> Audio:
    return Audio(
        info_dict["title"],
        info_dict["source"],
        info_dict["source_id"],
        info_dict["path"],
        info_dict["duration"]
    )
