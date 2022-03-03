import os
import datetime


class Playlist(list):

    def __init__(self, log_path):
        list.__init__(self)
        self.log_path = log_path

    def playlist_console_message_log(self, message):
        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f"\n    {message}\n")
        with open(self.log_path, "a", encoding="utf-8") as log:
            log.write(f"{current_time} {message}\n")

    def print_list(self):
        """
        打印出当前播放列表
        """
        result = ""
        if self.is_empty():
            return "-1"
        else:
            total = convert_duration_to_time(self.total_duration())
            for i in range(1, len(self) + 1):
                result = result + f"    **[{i}]**  {self[i - 1][0]}  " \
                                  f"[{convert_duration_to_time(self[i - 1][2])}" \
                                  f"]\n"
            result = result + f"\n    播放列表总时长 -> [{total}]"
            return result

    def total_duration(self):
        """
        返回当前播放列表中剩余的歌的总时长，单位为秒
        """
        total = 0
        for song in self:
            total += song[2]
        return total

    def add_song(self, title, path, duration=-1):
        """
        向播放列表中新增一首歌曲

        :param title: 新增歌曲的标题
        :param path: 新增歌曲的文件存储路径
        :param duration: 新增歌曲的时长（单位：秒）
        :return:
        """
        self.append([title, path, int(duration)])

    def is_empty(self):
        """
        如果列表为空返回True，反之返回False

        :return: 列表是否为空
        """
        return len(self) == 0

    def size(self):
        """
        :return: 当前播放列表的长度
        """
        return len(self)

    def get(self, index=0):
        """
        返回一首歌曲的信息列表，默认为当前歌曲\n
        如歌曲不存在则返回-1

        :param index: 要返回的歌曲的索引
        :return: 歌曲的信息列表
        """
        if self.is_empty() or index > self.size() - 1:
            return -1
        else:
            return self[index]

    def get_title(self, index=0):
        """
        返回一首歌曲的标题，默认为当前歌曲\n
        如歌曲不存在则返回-1

        :param index: 要返回的歌曲的索引
        :return: 歌曲的标题
        """
        if self.is_empty() or index > self.size() - 1:
            return -1
        else:
            return self.get(index)[0]

    def get_path(self, index=0):
        """
        返回一首歌曲的文件存储路径，默认为当前歌曲\n
        如歌曲不存在则返回-1

        :param index: 要返回的歌曲的索引
        :return: 歌曲的文件存储路径
        """
        if self.is_empty() or index > self.size() - 1:
            return -1
        else:
            return self.get(index)[1]

    def get_duration(self, index=0):
        """
        返回一首歌曲的长度，单位为秒，默认为当前歌曲\n
        如歌曲不存在则返回-1

        :param index: 要返回的歌曲的索引
        :return: 歌曲的长度
        """
        if self.is_empty() or index > self.size() - 1:
            return -1
        else:
            return self.get(index)[2]

    def is_repeat(self, index=0):
        """
        检测一首歌曲在列表中是否重复出现，如重复返回True，反之返回False，默认为当前歌曲
        （通过检索是否有相同路径）

        :param index: 要检查的歌曲的索引
        :return: 被检查的歌曲是否重复
        """
        target_path = self.get_path(index)
        counter = 0
        for song in self:
            if song[1] == target_path:
                counter += 1
        if counter > 1:
            return True
        else:
            return False

    def remove_select(self, index):
        """
        将一首歌移出播放列表，如果播放列表后没有再出现这首歌曲，则删除其文件

        :param index: 要移除的歌曲的索引
        :return:
        """
        # 获取要移除的歌曲的信息
        info = self.get(index)
        # 在移出列表前检测是否有重复的歌曲
        is_repeat = self.is_repeat(index)

        del self[index]
        self.playlist_console_message_log(f"歌曲 {info[0]} 已被移出播放列表")

        if not is_repeat:
            try:
                os.remove(info[1])
                self.playlist_console_message_log(f"文件 {info[0]} 已被删除")
            except FileNotFoundError:
                self.playlist_console_message_log(f"删除失败，文件 {info[1]} 未找到")

        else:
            self.playlist_console_message_log(f"歌曲 {info[0]} 发现重复，跳过文件删除")

    def remove_all(self, exception="-1"):
        """
        将播放列表中的全部歌曲移出播放清单，并删除其文件\n
        跳过exception的文件不进行删除

        :param exception: 跳过不删除的文件名称
        :return:
        """
        for i in range(self.size() - 1, -1, -1):
            if self[i][0] == exception:
                self.playlist_console_message_log(f"发现需跳过的文件 {self[i][0]} 不进行删除")
            else:
                self.remove_select(i)


def convert_duration_to_time(duration):
    """
    将获取的秒数转换为正常时间格式

    :param duration: 时长秒数
    :return:
    """
    duration = int(duration)

    if duration <= 0:
        return "-1"

    total_min = duration // 60
    hour = total_min // 60
    minutes = total_min % 60
    seconds = duration % 60

    if 0 < hour < 10:
        hour = f"0{hour}"

    if minutes == 0:
        minutes = "00"
    elif minutes < 10:
        minutes = f"0{minutes}"

    if seconds == 0:
        seconds = "00"
    elif seconds < 10:
        seconds = f"0{seconds}"

    if hour == 0:
        return f"{minutes}:{seconds}"

    return f"{hour}:{minutes}:{seconds}"
