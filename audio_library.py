import os
import json
from audio import Audio
from playlists import CustomPlaylist


class AudioLibrary:

    def __init__(self, library_path: str) -> None:

        if library_path.endswith("/"):
            library_path = library_path.rstrip("/")

        # 检查路径文件夹是否存在
        if not os.path.exists(library_path):
            os.mkdir(library_path)
            print(f"在路径 {library_path} 创建音频库文件夹")

        self.path = library_path
        self.json_path = f"{library_path}/audio_library.json"

        # 如audio_library文件不存在则创建
        if not os.path.exists(self.json_path):
            with open(self.json_path, "w", encoding="utf-8") as file:
                file.write(json.dumps({}, indent=4))

        with open(self.json_path, "r", encoding="utf-8") as file:
            self.audio_dict = json.loads(file.read())

    def save(self) -> None:
        """
        在json_path中以json格式写入当前audio_dict
        """
        with open(self.json_path, "w", encoding="utf-8") as file:
            file.write(json.dumps(self.audio_dict, sort_keys=False, indent=4))

    def exist(self, audio_title: str) -> bool:
        """
        检测当前audio_dict中是否存在音频audio，并返回相应的布尔值
        """
        return audio_title in self.audio_dict

    def add_audio(self, audio: Audio, custom_list=None) -> None:
        """
        向库中新添音频audio
        """
        if not self.exist(audio.title):
            if custom_list is None:
                in_lists = []
                num_in_lists = 0
            else:
                in_lists = [custom_list.title]
                num_in_lists = 1

            self.audio_dict[audio.title] = {
                "source": audio.source, "source_id": audio.source_id,
                "title": audio.title, "path": audio.path,
                "duration": audio.duration, "duration_str": audio.duration_str,
                "in_lists": in_lists, "num_in_lists": num_in_lists
            }

        elif custom_list is not None:
            # 如果in_lists中custom_list不是已经存在的
            if self.audio_dict[audio.title]["in_lists"].count(
                    custom_list.title) == 0:
                self.audio_dict[audio.title]["in_lists"].append(
                    custom_list.title)
                self.audio_dict[audio.title]["num_in_lists"] += 1

        self.save()

    def is_repeat(self, audio_title: str) -> bool:
        """
        检测歌曲被引用的次数是否大于1
        """
        return self.exist(audio_title) and self.audio_dict[audio_title][
            "num_in_lists"] > 1

    def remove_select(self, audio_title: str, custom_list=None) -> None:
        if self.exist(audio_title):
            if custom_list is not None:
                if not self.is_repeat(audio_title):
                    file_path = self.audio_dict[audio_title]["path"]
                    del self.audio_dict[audio_title]
                    os.remove(file_path)

    def remove_select_force(self, audio_title: str) -> None:
        if self.exist(audio_title):
            file_path = self.audio_dict[audio_title]["path"]
            del self.audio_dict[audio_title]
            os.remove(file_path)
