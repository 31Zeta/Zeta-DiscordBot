from utils import convert_duration_to_time


class Audio:

    def __init__(self, title: str) -> None:
        self.title = title
        self.source = "N/A"
        self.source_id = "N/A"
        self.path = "N/A"
        self.duration = 0
        self.duration_str = "N/A"
        self.user_command = "N/A"

    def __repr__(self) -> str:
        if self.duration_str != "N/A":
            return f"{self.title} [{self.duration_str}]"
        else:
            return self.title

    def __str__(self) -> str:
        if self.duration_str != "N/A":
            return f"{self.title} [{self.duration_str}]"
        else:
            return self.title

    def download_init(self, source, source_id, path, duration) -> None:
        self.source = source
        self.source_id = source_id
        self.path = path
        self.duration = duration
        self.duration_str = convert_duration_to_time(duration)

    def encode(self) -> dict:
        info_dict = {
            "title": self.title, "source": self.source,
            "source_id": self.source_id, "path": self.path,
            "duration": self.duration, "duration_str": self.duration_str
        }
        return info_dict
