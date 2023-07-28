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
    def __init__(self, root: str, path: str, name: str = "音频文件管理模块", storage_size: int = 100):
        self._root = root
        self._path = path
        self._using = set()
        self._storage_size = storage_size
        self._name = name

        self._logger = log.Log()

        if utils.path_exists(self._path):
            try:
                self._load()
            except errors.JSONFileError:
                self._reset_library()
            except KeyError:
                self._reset_library()
        else:
            self._reset_library()

    def __len__(self):
        return len(self._dl_list)

    def __contains__(self, item):
        return item in self._dl_list

    def save(self) -> None:
        utils.json_save(self._path, self)

    def _load(self) -> None:
        loaded_list = utils.json_load(self._path)
        temp_list = []
        for node_dict in loaded_list:
            audio_dict = node_dict["item"]
            key = node_dict["key"]
            new_audio = audio.audio_decoder(audio_dict)
            temp_list.append({"item": new_audio, "key": key})
        self._dl_list = utils.double_linked_list_dict_decoder(temp_list, force=True)
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

    def get_storage_size(self) -> int:
        return self._storage_size

    def storage_full(self) -> bool:
        return len(self._dl_list) >= self._storage_size

    def lock_audio(self, target_audio: audio.Audio) -> None:
        self._using.add(target_audio)

    def unlock_audio(self, target_audio: audio.Audio) -> None:
        if target_audio in self._using:
            self._using.remove(target_audio)

    def _append_audio(self, new_audio: audio.Audio) -> None:
        self._dl_list.append(new_audio, new_audio.get_source_id(), force=True)
        self.save()

    def _delete_least_used_file(self) -> bool:
        target_audio = self._dl_list.index_pop(0)
        if target_audio not in self._using:
            os.remove(target_audio.get_path())
            self._logger.rp(f"超出{self._name}容量限制，删除文件：{target_audio.get_path()}", f"[{self._name}]")
            return True
        else:
            self._logger.rp(f"文件正在使用中，无法删除文件：{target_audio.get_path()}", f"[{self._name}]")
            return False

    async def download_bilibili(self, info_dict, download_type: str, num_option: int = 0) -> Union[audio.Audio, None]:
        bvid = info_dict["bvid"]
        # 如果文件已经存在
        if bvid in self._dl_list:
            exists_audio = self._dl_list.key_get(bvid)
            self._logger.rp(f"音频已存在：{exists_audio.get_title()}\n路径：{exists_audio.get_path()}", f"[{self._name}]")
            self._append_audio(exists_audio)
            return exists_audio

        # 如果库满，尝试删除最不常使用的文件
        if self.storage_full():
            if not self._delete_least_used_file():
                self._logger.rp(f"{self._name}已满且无法清除文件，下载失败", f"[{self._name}]", is_error=True)
                raise errors.StorageFull(self._name)

        # 下载
        new_audio = await bilibili.audio_download(info_dict, self._root, download_type, num_option)

        if new_audio is not None:
            self._append_audio(new_audio)
            return new_audio
        else:
            return None

    def download_youtube(self, url, info_dict, download_type) -> Union[audio.Audio, None]:

        if self.storage_full():
            # 如果库满，尝试删除最不常使用的文件
            if not self._delete_least_used_file():
                self._logger.rp(f"{self._name}已满且无法清除文件，下载失败", f"[{self._name}]", is_error=True)
                raise errors.StorageFull(self._name)

        new_audio = youtube.audio_download(url, info_dict, self._root, download_type)

        if new_audio is not None:
            self._dl_list.append(new_audio, new_audio.get_source_id(), force=True)
            self.save()
            return new_audio
        else:
            return None

    def encode(self) -> list:
        return self._dl_list.encode()
