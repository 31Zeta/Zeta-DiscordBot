from typing import Any, Union, List

from zeta_bot import (
    errors,
    language,
    utils,
    console,
    audio,
)

# TODO 完成自建歌单

class Playlist:

    def __init__(self, name: str, limitation: Union[int, None] = None, owner=None):
        self._name = name
        self._playlist: list[audio.Audio] = []
        self._duration = 0
        self._limitation: Union[int, None] = limitation
        self._owner = owner

    def __str__(self):
        return self._name + ": " + str(self._playlist)

    def __len__(self) -> int:
        return len(self._playlist)

    def get_name(self) -> str:
        """
        返回当前播放列表的名称
        """
        return self._name

    def set_name(self, new_name: str) -> None:
        """
        修改当前播放列表的名称
        """
        self._name = new_name

    def get_list_info(self) -> List[tuple]:
        """
        返回一个包含当前播放列表音频信息的元组的列表
        """
        result = []
        for item in self._playlist:
            result.append((item.get_title(), item.get_duration_str()))
        return result

    def get_audio_str_list(self, index_start: bool = False) -> List[str]:
        temp_list = []
        if not index_start:
            for audio_item in self._playlist:
                temp_list.append(audio_item.__str__())
        else:
            counter = 1
            for audio_item in self._playlist:
                temp_list.append(f"[{counter}] {audio_item.__str__()}")
                counter += 1
        return temp_list

    def get_audio(self, index=0) -> Union[audio.Audio, None]:
        """
        返回一个音频（类Audio），默认为列表中的第一个音频\n
        如音频不存在则返回None

        :param index: 要返回的音频的索引
        :return: 类Audio
        """
        if self.is_empty() or index > len(self._playlist) - 1:
            return None
        else:
            return self._playlist[index]

    def pop_audio(self, index=0) -> Union[audio.Audio, None]:
        """
        返回一个音频（类Audio），默认为列表中的第一个音频\n
        如音频不存在则返回None

        :param index: 要返回的音频的索引
        :return: 类Audio
        """
        if self.is_empty() or index > len(self._playlist) - 1:
            return None
        else:
            target_audio = self._playlist.pop(index)
            self._duration -= target_audio.get_duration()
            return target_audio

    # TODO 记录添加人
    def append_audio(self, new_audio: audio.Audio) -> bool:
        """
        向播放列表的末尾添加一个音频，并更新播放列表时长

        :param new_audio: 新增的音频
        :return: 布尔值，是否添加成功
        """
        if self._limitation is None or len(self._playlist) + 1 <= self._limitation:
            self._playlist.append(new_audio)
            self._duration += new_audio.get_duration()
            return True
        else:
            return False

    def insert_audio(self, new_audio: audio.Audio, index: int) -> bool:
        """
        在播放列表中索引<index>之前插入一个音频，并更新播放列表时长

        :param new_audio: 新增的音频
        :param index: 加入音频的位置索引
        :return: 布尔值，是否添加成功
        """
        if self._limitation is None or len(self._playlist) + 1 <= self._limitation:
            self._playlist.insert(index, new_audio)
            self._duration += new_audio.get_duration()
            return True
        else:
            return False

    def move_audio(self, from_index: int, to_index: int) -> None:
        """
        将<from_index>索引的音频移动到<to_index>的索引位置

        :param from_index: 被移动音频的位置索引
        :param to_index: 目的地位置索引
        :return:
        """
        target_audio = self._playlist.pop(from_index)
        self._playlist.insert(to_index, target_audio)

    def swap_audio(self, index_1: int, index_2: int) -> None:
        """
        将<index_1>索引的音频与<index_2>索引的音频交换位置

        :param index_1: 被移动音频的位置索引
        :param index_2: 目的地位置索引
        :return:
        """
        self._playlist[index_1], self._playlist[index_2] = self._playlist[index_2], self._playlist[index_1]

    def is_repeat(self, index=0) -> bool:
        """
        检测一个音频在列表中是否重复出现，如重复返回True，反之返回False，默认为当前歌曲
        （通过检索是否有相同路径）

        :param index: 要检查的音频的索引
        :return: 布尔值，被检查的音频是否重复
        """
        target_audio = self.get_audio(index)
        if target_audio is not None:
            target_path = target_audio.get_path()
            counter = 0
            for item in self._playlist:
                if item.get_path() == target_path:
                    counter += 1
                    if counter > 1:
                        return True
            return False
        else:
            return False

    def remove_audio(self, index) -> None:
        """
        将一个音频移出播放列表

        :param index: 要移除的音频的索引
        :return:
        """
        target_audio = self.get_audio(index)
        if target_audio is not None:
            self._duration -= self.get_audio(index).get_duration()
            del self._playlist[index]

    def remove_all(self, skip_first=False) -> None:
        """
        将播放列表中的全部音频移出播放列表

        :return:
        """
        if not skip_first:
            for i in range(len(self._playlist) - 1, -1, -1):
                self.remove_audio(i)
        else:
            for i in range(len(self._playlist) - 1, 0, -1):
                self.remove_audio(i)

    def get_duration(self) -> int:
        """
        返回当前播放列表中剩余的音频的总时长，单位为秒
        """
        return self._duration

    def get_duration_str(self) -> str:
        """
        返回当前播放列表中剩余的音频的总时长，格式为字符串
        """
        return utils.convert_duration_to_str(self._duration)

    def get_owner(self) -> str:
        """
        返回当前播放列表的所有者
        """
        return self._owner

    def is_empty(self) -> bool:
        """
        如果列表为空返回True，反之返回False

        :return: 列表是否为空
        """
        return len(self._playlist) == 0

    def encode(self) -> dict:
        return {
            "name": self._name,
            "owner": self._owner,
            "limitation": self._limitation,
            "duration": self._duration,
            "playlist": self._playlist
        }


def playlist_decoder(info_dict: dict) -> Playlist:
    new_playlist = Playlist(info_dict["name"], info_dict["limitation"], info_dict["owner"])
    for item in info_dict["playlist"]:
        new_playlist.append_audio(audio.audio_decoder(item))
    return new_playlist
