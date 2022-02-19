class Playlist(list):

    def __init__(self):
        list.__init__(self)

    # def __str__(self):
    #     result = ""
    #     for i in range(1, len(self) + 1):
    #         result = result + f"    [{i}] " + self[i - 1][0] + "\n"
    #     return result

    def print_list(self):
        result = ""
        if self.is_empty():
            return "-1"
        else:
            total = convert_duration_to_time(self.total_duration())
            for i in range(1, len(self) + 1):
                result = result + f"    **[{i}]**  " + self[i - 1][0] + "  " + \
                        convert_duration_to_time(self[i - 1][2]) + "\n"
            result = result + "\n    播放列表总时长 -> " + total
            return result

    def total_duration(self):
        total = 0
        for song in self:
            total += song[2]
        return total

    def add_song(self, title, path, duration=-1):
        self.append([title, path, duration])

    def is_empty(self):
        return len(self) == 0

    def size(self):
        return len(self)

    def next_song(self):
        if self.is_empty():
            return -1
        else:
            del self[0]
            return self[0]

    def peek(self, index=0):
        if self.is_empty():
            return -1
        else:
            return self[index - 1]

    def peek_title(self, index=1):
        if self.peek(index) == -1:
            return -1
        else:
            return self.peek(index)[0]

    def peek_path(self, index=1):
        if self.peek(index) == -1:
            return -1
        else:
            return self.peek(index)[1]

    def remove_current(self):
        del self[0]

    def remove_select(self, index: int):
        del self[index - 1]

    def remove_all(self, exception="-1"):
        for i in range(self.size() - 1, -1, -1):
            if self[i][0] == exception:
                pass
            else:
                del self[i]


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
        return f"[{minutes}:{seconds}]"

    return f"[{hour}:{minutes}:{seconds}]"
