import os
from typing import Any, Union

from zeta_bot import (
    errors,
    log,
    utils,
    audio,
    bilibili,
    youtube
)


class AudioFileLibrary:
    def __init__(self, root: str, path: str, name: str = "音频文件管理模块", storage_capacity: int = 2097152):
        """
        _storage_size单位为字节（byte）
        """
        self._root = root
        self._path = path
        self._using = {}
        self._storage_capacity = storage_capacity
        self._name = name

        self._logger = log.Log()

        if utils.path_exists(self._path):
            try:
                self._load()
            except errors.JSONFileError:
                self._reset_library()
                self._load()
            except KeyError:
                self._reset_library()
                self._load()
        else:
            self._reset_library()
            self._load()

    # DEBUG ONLY
    def print_info(self):
        converted_capacity = utils.convert_byte(self._storage_capacity)
        converted_used_size = utils.convert_byte(self._used_storage_size)
        available_size = self.get_available_storage_size()
        converted_available_size = utils.convert_byte(available_size)
        print(f"{self._name} 当前状态：\n"
              f"目录：{self._root}\n"
              f"文件路径：{self._path}\n"
              f"库中对象数量：{len(self._dl_list)}\n"
              f"锁定对象：{self._using}\n"
              f"容量上限：{self._storage_capacity} -> {converted_capacity[0]}{converted_capacity[1]}\n"
              f"已用容量：{self._used_storage_size} -> {converted_used_size[0]}{converted_used_size[1]}\n"
              f"可用容量：{available_size} -> {converted_available_size[0]}{converted_available_size[1]}\n"
              f"已用容量百分比：{self.get_used_storage_percentage(2)}%\n"
              f"可用容量百分比：{self.get_available_storage_percentage(2)}%\n")

    def __len__(self):
        return len(self._dl_list)

    def __contains__(self, item):
        return item in self._dl_list

    def save(self) -> None:
        utils.json_save(self._path, self)

    def _load(self) -> None:
        self._used_storage_size = 0
        loaded_list = utils.json_load(self._path)
        temp_list = []

        for node_dict in loaded_list:
            audio_dict = node_dict["item"]
            try:
                file_size = os.path.getsize(node_dict["item"]["path"])
            except FileNotFoundError:
                self._logger.rp(f"库中记录的音频文件丢失：\n"
                                f"标题：{audio_dict['title']}\n"
                                f"来源：[{audio_dict['source']}] {audio_dict['source_id']}\n"
                                f"路径：{audio_dict['path']}\n"
                                f"时长：{audio_dict['duration_str']}",
                                f"[{self._name}]")
                continue
            self._used_storage_size += file_size
            key = node_dict["key"]
            new_audio = audio.audio_decoder(audio_dict)
            temp_list.append({"item": new_audio, "key": key})

        self._dl_list = utils.double_linked_list_dict_decoder(temp_list, force=True)

        if self.storage_full():
            self._logger.rp(f"{self._name}超出容量限制，从最久不使用的文件开始尝试删除", f"[{self._name}]")
            while self.storage_full():
                if not self._delete_least_used_file():
                    self._logger.rp(f"{self._name}容量超出上限且且无法继续清除文件，初始化失败，请检查设置中的音频库缓存容量上限\n"
                                    f"可通过--setting修改设置中的音频库缓存容量上限，"
                                    f"或者手动修改文件./configs/system_config.json中的audio_library_storage_capacity",
                                    f"[{self._name}]", is_error=True)
                    raise errors.InitializationFailed(self._name,
                                                      f"{self._name}容量超出上限且且无法继续清除文件，"
                                                      f"请检查设置中的音频库缓存容量上限。可通过--setting修改设置中的音频库缓存容量上限，"
                                                      f"或者手动修改文件./configs/system_config.json中的audio_library_storage_capacity")

        self._logger.rp(f"成功加载库文件：{self._path}", f"[{self._name}]")

    def _reset_library(self) -> None:
        """
        **警告**
        将会删除目录下所有文件并重新建立双向链表字典
        """
        self._logger.rp(f"开始重置库{self._name}", f"[{self._name}]")
        for name in os.listdir(self._root):
            if os.path.isfile(f"{self._root}/{name}"):
                os.remove(f"{self._root}/{name}")
                self._logger.rp(f"删除文件：{name}", f"[{self._name}]")

        self._dl_list = utils.DoubleLinkedListDict()
        self.save()

    def get_name(self) -> str:
        return self._name

    def get_storage_capacity(self) -> int:
        return self._storage_capacity

    def get_used_storage_size(self) -> int:
        return self._used_storage_size

    def get_available_storage_size(self) -> int:
        available_storage_size = self._storage_capacity - self._used_storage_size
        if available_storage_size < 0:
            return 0
        else:
            return available_storage_size

    def get_used_storage_percentage(self, round_num: int = 2) -> float:
        float_percentage = round(self._used_storage_size / self._storage_capacity, round_num + 2)
        return round(float_percentage * 100, round_num)

    def get_available_storage_percentage(self, round_num: int = 2) -> float:
        float_percentage = round(self.get_available_storage_size() / self._storage_capacity, round_num + 2)
        return round(float_percentage * 100, round_num)

    def storage_full(self) -> bool:
        return self._used_storage_size >= self._storage_capacity

    def storage_will_full(self, new_file_size: int):
        return self._used_storage_size + new_file_size > self._storage_capacity

    def using(self, target: Union[str, audio.Audio]) -> bool:
        """
        返回一个音频或者其文件的路径是否正在被使用
        """
        if isinstance(target, str):
            return target in self._using
        elif isinstance(target, audio.Audio):
            return target.get_path() in self._using
        else:
            return False

    def now_playing(self, target: Union[str, audio.Audio]) -> bool:
        """
        返回一个音频或者其文件的路径是否正在被播放
        """
        if isinstance(target, str):
            pass
        elif isinstance(target, audio.Audio):
            target = target.get_path()
        else:
            return False

        if target in self._using:
            for key in self._using[target]:
                if "NOW_PLAYING" in key:
                    return True

        return False

    def lock_audio(self, key: str, target_audio: audio.Audio) -> None:
        """
        将音频锁定，<key>代表某一部分需要使用该音频，当一个音频不被任何部分使用时才可完全解锁
        :param key: 代表一个部分锁定该音频，统一使用字符串str防止类型不同造成的无法解锁
        :param target_audio: 需要被锁定的音频
        """
        target_path = target_audio.get_path()
        if target_path not in self._using:
            self._using[target_path] = {key: 1}
        elif key not in self._using[target_path]:
            self._using[target_path][key] = 1
        else:
            self._using[target_path][key] += 1

    def unlock_audio(self, key: str, target_audio: audio.Audio) -> None:
        """
        将音频从音频库中解锁，<key>代表某一部分需要使用该音频，当一个音频被解锁的次数等于锁定的次数时才可完全解锁
        :param key: 代表一个部分解锁该音频，统一使用字符串str防止类型不同造成的无法解锁
        :param target_audio: 需要被解锁的音频
        """
        target_path = target_audio.get_path()
        if target_path in self._using:
            if key in self._using[target_path]:
                self._using[target_path][key] -= 1
                if self._using[target_path][key] == 0:
                    del self._using[target_path][key]
            if len(self._using[target_path]) == 0:
                del self._using[target_path]

    def _append_audio(self, new_audio: audio.Audio, repeat_file=False) -> None:
        """
        :param new_audio: 要添加的Audio对象
        :param repeat_file: 文件是否已在库中
        """
        self._dl_list.append(new_audio, new_audio.get_source_id(), force=True)

        if not repeat_file:
            filesize = os.path.getsize(new_audio.get_path())
            converted_file_size = utils.convert_byte(filesize)
            self._used_storage_size += filesize
            converted_used_size = utils.convert_byte(self._used_storage_size)
            converted_capacity = utils.convert_byte(self._storage_capacity)
            self._logger.rp(f"添加文件：{new_audio.get_title()} [{converted_file_size[0]}{converted_file_size[1]}]\n"
                            f"已用容量：{converted_used_size[0]}{converted_used_size[1]}/"
                            f"{converted_capacity[0]}{converted_capacity[1]}"
                            f" -> {self.get_used_storage_percentage(2)}%",
                            f"[{self._name}]")

        self.save()

    def _remove_audio(self, key: str) -> None:
        target_audio = self._dl_list.key_get(key)
        filesize = os.path.getsize(target_audio.get_path())

        try:
            os.remove(target_audio.get_path())
        except FileNotFoundError:
            self._logger.rp(f"尝试删除文件失败：{target_audio.get_path()}，文件已不存在",
                            f"[{self._name}]")
            # 将已不存在的文件移出dl_list
            self._dl_list.key_remove(key)
            raise FileNotFoundError
        except PermissionError:
            self._logger.rp(f"尝试删除文件失败：{target_audio.get_path()}，文件正在使用中或程序权限不足",
                            f"[{self._name}]")
            raise PermissionError
        else:
            self._dl_list.key_remove(key)
            converted_file_size = utils.convert_byte(filesize)
            self._used_storage_size -= filesize
            converted_used_size = utils.convert_byte(self._used_storage_size)
            converted_capacity = utils.convert_byte(self._storage_capacity)
            self._logger.rp(f"删除文件：{target_audio.get_title()} [{converted_file_size[0]}{converted_file_size[1]}]\n"
                            f"已用容量：{converted_used_size[0]}{converted_used_size[1]}/"
                            f"{converted_capacity[0]}{converted_capacity[1]}"
                            f" -> {self.get_used_storage_percentage(2)}%",
                            f"[{self._name}]")

        self.save()

    def _delete_least_used_file(self, depth: int = 0) -> bool:
        """
        从最久不使用的文件开始尝试删除
        由于本方法含有递归调用并且本方法可能会被循环调用，所以将提示语
         - self._logger.rp(f"{self._name}超出容量限制，从最久不使用的文件开始尝试删除", f"[{self._name}]")
        放置在方法外部以减少重复提示
        """
        try:
            target_audio = self._dl_list.index_get(depth)
        except IndexError:
            self._logger.rp(f"{self._name}超出容量限制，尝试删除文件失败，库中已不包含任何可删除的文件", f"[{self._name}]")
            return False
        if not self.using(target_audio):
            try:
                self._remove_audio(target_audio.get_source_id())
            except FileNotFoundError:
                # 删除失败，如果仍满则重试
                if self.storage_full():
                    result = self._delete_least_used_file()
                    return result  # 递归返回
            # 如果是文件正在使用的话此错误大概率不会出现，作为key失效的兜底处理
            except PermissionError:
                # 如果当前尝试删除的文件并不是正在播放的话，继续尝试删除下一最久不使用的文件，
                # 因为唯一一种较旧文件被锁定而较新文件没被锁定的情况就是较旧文件正在播放的情况
                if not self.now_playing(target_audio) or depth + 1 >= len(self._dl_list):
                    return False
                else:
                    result = self._delete_least_used_file(depth + 1)
                    return result  # 递归返回
            else:
                return True
        else:
            self._logger.rp(f"尝试删除文件失败：{target_audio.get_path()}，文件正在使用中", f"[{self._name}]")
            # 如果当前尝试删除的文件并不是正在播放的话，继续尝试删除下一最久不使用的文件，
            # 因为唯一一种较旧文件被锁定而较新文件没被锁定的情况就是较旧文件正在播放的情况
            if not self.now_playing(target_audio) or depth + 1 >= len(self._dl_list):
                return False
            else:
                result = self._delete_least_used_file(depth + 1)
                return result  # 递归返回

    async def download_bilibili(self, info_dict, download_type: str, num_option: int = 0) -> Union[audio.Audio, None]:
        bvid = info_dict["bvid"]
        # 如果文件已经存在
        if bvid in self._dl_list:
            exists_audio = self._dl_list.key_get(bvid)
            filesize = os.path.getsize(exists_audio.get_path())
            converted_file_size = utils.convert_byte(filesize)
            converted_used_size = utils.convert_byte(self._used_storage_size)
            converted_capacity = utils.convert_byte(self._storage_capacity)
            self._logger.rp(f"文件已在库中：{exists_audio.get_title()} [{converted_file_size[0]}{converted_file_size[1]}]\n"
                            f"路径：{exists_audio.get_path()}\n"
                            f"已用容量：{converted_used_size[0]}{converted_used_size[1]}/"
                            f"{converted_capacity[0]}{converted_capacity[1]}"
                            f" -> {self.get_used_storage_percentage(2)}% ",
                            f"[{self._name}]")
            # 将再次使用的音频挪至最新
            self._append_audio(exists_audio, repeat_file=True)
            return exists_audio

        new_file_size = await bilibili.get_filesize(info_dict, num_option)

        # 如果下载此音频库会满，尝试删除最不常使用的文件
        if self.storage_will_full(new_file_size):
            self._logger.rp(f"{self._name}超出容量限制，从最久不使用的文件开始尝试删除", f"[{self._name}]")
            while self.storage_will_full(new_file_size):
                # 现在是一直删文件直到可以下载或者删不了为止，可以改成先计算能删多少文件，空间够了再删，但是潜在问题太多先不改了
                if not self._delete_least_used_file():
                    converted_file_size = utils.convert_byte(new_file_size)
                    available_size = self.get_available_storage_size()
                    converted_available_size = utils.convert_byte(available_size)
                    self._logger.rp(f"下载失败，超出音频库容量上限且无法清理出足够空间，"
                                    f"目标文件大小：{converted_file_size[0]}{converted_file_size[1]}，"
                                    f"音频库可用容量：{converted_available_size[0]}{converted_available_size[1]}",
                                    f"[{self._name}]")
                    raise errors.StorageFull(self._name)

        # 下载
        new_audio = await bilibili.audio_download(info_dict, self._root, download_type, num_option)

        if new_audio is not None:
            self._append_audio(new_audio, repeat_file=False)
            return new_audio
        else:
            return None

    def download_youtube(self, url, info_dict, download_type) -> Union[audio.Audio, None]:
        video_id = info_dict["id"]
        # 如果文件已经存在
        if video_id in self._dl_list:
            exists_audio = self._dl_list.key_get(video_id)
            filesize = os.path.getsize(exists_audio.get_path())
            converted_file_size = utils.convert_byte(filesize)
            converted_used_size = utils.convert_byte(self._used_storage_size)
            converted_capacity = utils.convert_byte(self._storage_capacity)
            self._logger.rp(f"文件已在库中：{exists_audio.get_title()} [{converted_file_size[0]}{converted_file_size[1]}]\n"
                            f"路径：{exists_audio.get_path()}\n"
                            f"已用容量：{converted_used_size[0]}{converted_used_size[1]}/"
                            f"{converted_capacity[0]}{converted_capacity[1]}"
                            f" -> {self.get_used_storage_percentage(2)}%",
                            f"[{self._name}]")
            # 将再次使用的音频挪至最新
            self._append_audio(exists_audio, repeat_file=True)
            return exists_audio

        new_file_size = youtube.get_filesize(info_dict)

        # 如果下载此音频库会满，尝试删除最不常使用的文件
        if self.storage_will_full(new_file_size):
            self._logger.rp(f"{self._name}超出容量限制，从最久不使用的文件开始尝试删除", f"[{self._name}]")
            while self.storage_will_full(new_file_size):
                # 现在是一直删文件直到可以下载或者删不了为止，可以改成先计算能删多少文件，空间够了再删，但是潜在问题太多先不改了
                if not self._delete_least_used_file():
                    converted_file_size = utils.convert_byte(new_file_size)
                    available_size = self.get_available_storage_size()
                    converted_available_size = utils.convert_byte(available_size)
                    self._logger.rp(f"下载失败，超出音频库容量上限且无法清理出足够空间，"
                                    f"目标文件大小：{converted_file_size[0]}{converted_file_size[1]}，"
                                    f"音频库可用容量：{converted_available_size[0]}{converted_available_size[1]}",
                                    f"[{self._name}]")
                    raise errors.StorageFull(self._name)

        new_audio = youtube.audio_download(url, info_dict, self._root, download_type)

        if new_audio is not None:
            self._append_audio(new_audio, repeat_file=False)
            return new_audio
        else:
            return None

    def encode(self) -> list:
        return self._dl_list.encode()
