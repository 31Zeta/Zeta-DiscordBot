import os
import datetime
import json
from typing import Union

from utils import convert_duration_to_time
from audio import Audio


class Playlist(list):

    def __init__(self) -> None:
        list.__init__(self)

    def get_playlist_str(self) -> Union[tuple, str]:
        """
        返回当前播放列表字符串与总时长的元组
        如果列表为空则返回-1
        """
        result = ""
        if self.is_empty():
            return "-1"
        else:
            total_duration = convert_duration_to_time(self.total_duration())
            for i in range(1, len(self) + 1):
                duration = convert_duration_to_time(self[i - 1].duration)
                result = result + f"    **[{i}]**  {self[i - 1].title}  " \
                                  f"[{duration}]\n"
            # f"\n    播放列表总时长 -> [{total}]"
            return result, total_duration

    def total_duration(self) -> int:
        """
        返回当前播放列表中剩余的音频的总时长，单位为秒
        """
        total = 0
        for audio in self:
            total += audio.duration
        return total

    def total_duration_str(self) -> str:
        """
        返回当前播放列表中剩余的音频的总时长，单位为秒
        """
        total = self.total_duration()
        result = convert_duration_to_time(total)
        return result

    def add_audio(self, new_audio: Audio, index: int) -> None:
        """
        在播放列表中索引<index>之前插入一个音频

        :param new_audio: 新增的音频
        :param index: 加入音频的位置索引
        :return:
        """
        self.insert(index, new_audio)

    def append_audio(self, new_audio: Audio) -> None:
        """
        向播放列表的末尾添加一个音频

        :param new_audio: 新增的音频
        :return:
        """
        self.append(new_audio)

    def move_audio(self, from_index: int, to_index: int) -> None:
        """
        将<from_index>索引的音频移动到<to_index>的索引位置

        :param from_index: 被移动音频的位置索引
        :param to_index: 目的地位置索引
        :return:
        """
        target_audio = self.pop(from_index)
        self.insert(to_index, target_audio)

    def swap_audio(self, index_1: int, index_2: int) -> None:
        """
        将<index_1>索引的音频与<index_2>索引的音频交换位置

        :param index_1: 被移动音频的位置索引
        :param index_2: 目的地位置索引
        :return:
        """
        self[index_1], self[index_2] = self[index_2], self[index_1]

    def is_empty(self) -> bool:
        """
        如果列表为空返回True，反之返回False

        :return: 列表是否为空
        """
        return len(self) == 0

    def size(self) -> int:
        """
        :return: 当前播放列表的长度
        """
        return len(self)

    def get(self, index=0) -> Union[Audio, str]:
        """
        返回一个音频（类Audio），默认为列表中的第一个音频\n
        如音频不存在则返回-1

        :param index: 要返回的音频的索引
        :return: 类Audio
        """
        if self.is_empty() or index > self.size() - 1:
            return "-1"
        else:
            return self[index]

    def get_title(self, index=0) -> str:
        """
        返回一个音频的标题，默认为列表中的第一个音频\n
        如音频不存在则返回-1

        :param index: 要返回的音频的索引
        :return: 音频的标题
        """
        if self.is_empty() or index > self.size() - 1:
            return "-1"
        else:
            return self.get(index).title

    def get_path(self, index=0) -> str:
        """
        返回一个音频的文件存储路径，默认为列表中的第一个音频\n
        如音频不存在则返回-1

        :param index: 要返回的音频的索引
        :return: 音频的文件存储路径
        """
        if self.is_empty() or index > self.size() - 1:
            return "-1"
        else:
            return self.get(index).path

    def get_duration(self, index=0) -> int:
        """
        返回一个音频的时长，单位为秒，默认为列表中的第一个音频\n
        如音频不存在则返回-1

        :param index: 要返回的音频的索引
        :return: 音频的长度
        """
        if self.is_empty() or index > self.size() - 1:
            return -1
        else:
            return self.get(index).duration

    def get_duration_str(self, index=0) -> str:
        """
        返回一个音频的时长，类型为字符串形式的时间格式，默认为列表中的第一个音频\n
        如音频不存在则返回-1

        :param index: 要返回的音频的索引
        :return: 音频的长度
        """
        if self.is_empty() or index > self.size() - 1:
            return "-1"
        else:
            return self.get(index).duration_str

    def is_repeat(self, index=0) -> bool:
        """
        检测一个音频在列表中是否重复出现，如重复返回True，反之返回False，默认为当前歌曲
        （通过检索是否有相同路径）

        :param index: 要检查的音频的索引
        :return: 布尔值，被检查的音频是否重复
        """
        target_path = self.get_path(index)
        counter = 0
        for audio in self:
            if audio.path == target_path:
                counter += 1
        if counter > 1:
            return True
        else:
            return False

    def remove_select(self, index) -> None:
        """
        将一个音频移出播放列表

        :param index: 要移除的音频的索引
        :return:
        """
        # 获取要移除的歌曲的信息
        del self[index]

    def remove_all(self) -> None:
        """
        将播放列表中的全部音频移出播放列表

        :return:
        """
        for i in range(self.size() - 1, -1, -1):
            self.remove_select(i)


class GuildPlaylist(Playlist):

    def __init__(self, log_path) -> None:
        super().__init__()
        self.log_path = log_path

    def playlist_console_message_log(self, message) -> None:
        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f"\n    {message}\n")
        with open(self.log_path, "a", encoding="utf-8") as log:
            log.write(f"{current_time} {message}\n")

    def delete_select(self, index) -> None:
        """
        将一个音频移出播放列表，如果播放列表后没有再出现这个音频，则删除其文件

        :param index: 要移除的歌曲的索引
        :return:
        """
        # 获取要移除的歌曲的信息
        audio = self.get(index)
        # 在移出列表前检测是否有重复的歌曲
        is_repeat = self.is_repeat(index)

        del self[index]
        self.playlist_console_message_log(f"歌曲 {audio.title} 已被移出播放列表")

        if not is_repeat:
            try:
                os.remove(audio.path)
                self.playlist_console_message_log(f"文件 {audio.title} 已被删除")
            except FileNotFoundError:
                self.playlist_console_message_log(f"删除失败，文件 {audio.title} 未找到")

        else:
            self.playlist_console_message_log(f"歌曲 {audio.title} 发现重复，跳过文件删除")

    def delete_all(self, exception="-1") -> None:
        """
        将播放列表中的全部音频移出播放列表，并删除其文件\n
        跳过exception的文件不进行删除

        :param exception: 跳过不删除的文件名称
        :return:
        """
        for i in range(self.size() - 1, -1, -1):
            if self[i].title == exception:
                self.playlist_console_message_log(f"发现需跳过的文件 {self[i].title} "
                                                  f"不进行删除")
            else:
                self.delete_select(i)


class CustomPlaylist(Playlist):

    def __init__(self, title) -> None:
        super().__init__()
        self.title = title
        self.save_path = f"./playlists/{self.title}_playlist.json"
        self.audio_json_path = "./audios/audios_library.json"
        if os.path.exists(self.save_path):
            with open(self.save_path, "r") as file:
                lines = file.read()
            input_list = json.loads(lines)
            for item in input_list:
                self.append(item)

    def save(self):
        with open(f"{self.save_path}", "w") as file:
            file.write(
                json.dumps(self, default=lambda x: x.encode(),
                           sort_keys=False, indent=4)
            )

    def delete_select(self, index) -> None:
        """
        将一个音频移出播放列表，如果播放列表后没有再出现这个音频，则删除其文件

        :param index: 要移除的歌曲的索引
        :return:
        """
        pass

    def delete_all(self, exception="-1") -> None:
        """
        将播放列表中的全部音频移出播放列表，并删除其文件\n
        跳过exception的文件不进行删除

        :param exception: 跳过不删除的文件名称
        :return:
        """
        pass
