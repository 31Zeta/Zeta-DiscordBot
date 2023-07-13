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

logger = log.Log()


class AudioFileManagement:
    def __init__(self, root: str, name: str = "音频文件管理模块", storage_size: int = 100):
        self._root = root
        self._dl_list = utils.DoubleLinkedListDict()
        self._using = set()
        self._storage_size = storage_size
        self._name = name

    def __len__(self):
        return len(self._dl_list)

    def get_storage_size(self) -> int:
        return self._storage_size

    def storage_full(self) -> bool:
        return len(self._dl_list) >= self._storage_size

    def lock_audio(self, target_audio: audio.Audio) -> None:
        self._using.add(target_audio)

    def unlock_audio(self, target_audio: audio.Audio) -> None:
        if target_audio in self._using:
            self._using.remove(target_audio)

    def _delete_least_used_file(self) -> bool:
        target_audio = self._dl_list.index_pop(0)
        if target_audio not in self._using:
            os.remove(target_audio.get_path())
            logger.rp(f"超出容量限制，删除文件：{target_audio.get_path}", f"[{self._name}]")
            return True
        else:
            logger.rp(f"文件正在使用中，无法删除文件：{target_audio.get_path}", f"[{self._name}]")
            return False

    async def audio_download_bilibili(self, bvid, info_dict, download_type, num_option) -> Union[audio.Audio, None]:
        
        if self.storage_full():
            # 如果库满，尝试删除最不常使用的文件
            if not self._delete_least_used_file():
                logger.rp(f"{self._name}已满且无法清除文件，下载失败", f"[{self._name}]")
                return None

        new_audio = await bilibili.audio_download(bvid, info_dict, self._root, download_type, num_option)

        if new_audio is not None:
            self._dl_list.append(new_audio, new_audio.get_path(), force=True)
            return new_audio
        else:
            return None

    def audio_download_youtube(self, url, info_dict, download_type) -> Union[audio.Audio, None]:

        if self.storage_full():
            # 如果库满，尝试删除最不常使用的文件
            if not self._delete_least_used_file():
                logger.rp(f"{self._name}已满且无法清除文件，下载失败", f"[{self._name}]")
                return None

        new_audio = youtube.audio_download(url, info_dict, self._root, download_type)

        if new_audio is not None:
            self._dl_list.append(new_audio, new_audio.get_path(), force=True)
            return new_audio
        else:
            return None
