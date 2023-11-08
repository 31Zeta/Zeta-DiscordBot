import discord
import os
from typing import Union

from zeta_bot import (
    errors,
    language,
    decorators,
    utils,
    log,
    file_management,
    member,
    audio,
    playlist
)


class Guild:
    def __init__(self, guild: discord.guild, lib_root: str, audio_file_library: file_management.AudioFileLibrary):
        self._guild = guild
        self._id = self._guild.id
        self._name = self._guild.name
        self._lib_root = lib_root
        self._root = f"{self._lib_root}/{self._guild.id}"
        self._path = f"{self._root}/{self._guild.id}.json"
        self._audio_file_library = audio_file_library
        self._logger = log.Log()
        self._play_mode = 0
        self._active_views = {}

        if not os.path.exists(self._root):
            utils.create_folder(self._root)

        try:
            self.load()
        except FileNotFoundError:
            self.playlist = GuildPlaylist(self, self._audio_file_library)
            self.playedlist = playlist.Playlist(f"{self._name} 历史播放列表")
            self.save()
        except KeyError:
            self.playlist = GuildPlaylist(self, self._audio_file_library)
            self.playedlist = playlist.Playlist(f"{self._name} 历史播放列表")
            self.save()
        except errors.JSONFileError:
            self.playlist = GuildPlaylist(self, self._audio_file_library)
            self.playedlist = playlist.Playlist(f"{self._name} 历史播放列表")
            self.save()

        self.voice_volume = 100.0

        self._logger.rp(f"服务器初始化完成：{self._name}", self._name)

    def __str__(self):
        return self._name

    def get_id(self):
        return self._id

    def get_name(self):
        return self._name

    def get_playlist(self):
        return self.playlist

    def get_playedlist(self) -> playlist.Playlist:
        return self.playedlist

    def get_voice_volume(self) -> float:
        return self.voice_volume

    def get_play_mode(self) -> int:
        """
        返回当前播放模式
        0 - 顺序播放
        1 - 单曲循环
        2 - 列表循环
        3 - 随机播放
        4 - 随机循环
        """
        return self._play_mode

    def get_active_views(self) -> dict:
        return self._active_views

    def set_voice_volume(self, volume: Union[int, float]) -> None:
        self.voice_volume = float(volume)

    def set_play_mode(self, mode_code: int) -> bool:
        """
        设置播放模式
        0 - 顺序播放
        1 - 单曲循环
        2 - 列表循环
        3 - 随机播放
        4 - 随机循环
        """
        if mode_code not in [0, 1, 2, 3, 4]:
            return False
        self._play_mode = mode_code
        return True

    def save(self) -> None:
        utils.json_save(self._path, self)

    def load(self) -> None:
        loaded_dict = utils.json_load(self._path)
        self.playedlist = playlist.playlist_decoder(loaded_dict["playedlist"])
        self.playlist = GuildPlaylist(self, self._audio_file_library)
        guild_playlist_loader(self.playlist, loaded_dict["playlist"])

    def encode(self) -> dict:
        return {
            "id": self._id,
            "name": self._name,
            "playlist": self.playlist,
            "playedlist": self.playedlist
        }


@decorators.Singleton
class GuildLibrary:
    def __init__(self):
        self._root = "./data/guilds"
        utils.create_folder(self._root)
        self._guild_dict = {}
        self._hashtag_file_path = f"{self._root}/#Guilds.json"
        self._logger = log.Log()
        # TODO hashtag文件内名称键重复两遍

        # 检查#Guilds文件
        if not os.path.exists(self._hashtag_file_path):
            utils.json_save(self._hashtag_file_path, {})
        try:
            self.hashtag_file = utils.json_load(self._hashtag_file_path)
        except errors.JSONFileError:
            raise errors.JSONFileError

    def save_hashtag_file(self):
        utils.json_save(self._hashtag_file_path, self.hashtag_file)

    def check(self, ctx: Union[discord.ApplicationContext, discord.AutocompleteContext],
              audio_file_library: file_management.AudioFileLibrary) -> None:
        if isinstance(ctx, discord.ApplicationContext):
            guild_id = ctx.guild.id
            guild_name = ctx.guild.name
        else:
            guild_id = ctx.interaction.guild.id
            guild_name = ctx.interaction.guild.name

        # 如果guild_dict中不存在本Discord服务器
        if guild_id not in self._guild_dict:
            if isinstance(ctx, discord.ApplicationContext):
                self._guild_dict[guild_id] = Guild(ctx.guild, self._root, audio_file_library)
            else:
                self._guild_dict[guild_id] = Guild(ctx.interaction.guild, self._root, audio_file_library)

        # 更新#Guilds文件
        if guild_id not in self.hashtag_file or guild_name != self.hashtag_file[guild_id]:
            self.hashtag_file[guild_id] = guild_name
            self.save_hashtag_file()

    def get_guild(self, ctx: Union[discord.ApplicationContext, discord.AutocompleteContext]) -> Union[Guild, None]:
        if isinstance(ctx, discord.ApplicationContext):
            guild_id = ctx.guild.id
        else:
            # isinstance ctx → discord.AutocompleteContext
            guild_id = ctx.interaction.guild.id

        if guild_id in self._guild_dict:
            return self._guild_dict[guild_id]
        else:
            return None

    def save_all(self) -> None:
        self._logger.rp("开始保存各Discord服务器数据", "[Discord服务器库]")
        for key in self._guild_dict:
            self._guild_dict[key].save()
        self._logger.rp("各Discord服务器数据保存完毕", "[Discord服务器库]")


class GuildPlaylist(playlist.Playlist):
    def __init__(self, guild: Guild, file_library: file_management.AudioFileLibrary,
                 limitation: Union[int, None] = None):
        super().__init__(f"{guild.get_name()} 主播放列表", limitation, None)
        self._guild = guild
        self._file_library = file_library

    def get_guild(self):
        return self._guild

    def get_file_library(self):
        return self._file_library

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
            if target_audio not in self._playlist:
                self._file_library.unlock_audio(self._guild.get_id(), target_audio)
            self._guild.save()
            return target_audio

    def append_audio(self, new_audio: audio.Audio) -> bool:
        """
        向播放列表的末尾添加一个音频，并更新播放列表时长

        :param new_audio: 新增的音频
        :return: 布尔值，是否添加成功
        """
        if self._limitation is None or len(self._playlist) + 1 <= self._limitation:
            self._playlist.append(new_audio)
            self._duration += new_audio.get_duration()
            self._file_library.lock_audio(self._guild.get_id(), new_audio)
            self._guild.save()
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
            self._file_library.lock_audio(self._guild.get_id(), new_audio)
            self._guild.save()
            return True
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
            if target_audio not in self._playlist:
                self._file_library.unlock_audio(self._guild.get_id(), target_audio)
            self._guild.save()


def guild_playlist_loader(guild_playlist: GuildPlaylist, info_dict: dict) -> None:
    """
    GuildPlaylist加载器，传入一个GuildPlaylist以及它的encode()生成的字典，重建并加入字典中的Audio，在AudioFileLibrary锁定这些Audio
    """
    file_library = guild_playlist.get_file_library()
    for item in info_dict["playlist"]:
        current_audio = audio.audio_decoder(item)
        guild_playlist.append_audio(current_audio)
        file_library.lock_audio(guild_playlist.get_guild().get_id(), current_audio)
