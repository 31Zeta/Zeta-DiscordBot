import discord
import os
from typing import Union

from zeta_bot import (
    errors,
    language,
    decorators,
    utils,
    setting,
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
        self._voice_client = self._guild.voice_client

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

    def __str__(self):
        return self._name

    def get_name(self):
        return self._name

    def get_playlist(self):
        return self.playlist

    def get_playedlist(self) -> playlist.Playlist:
        return self.playedlist

    def get_voice_client(self) -> discord.VoiceClient:
        return self._voice_client

    def get_voice_volume(self) -> float:
        return self.voice_volume

    def set_voice_volume(self, volume: Union[int, float]) -> None:
        self.voice_volume = float(volume)

    def save(self) -> None:
        utils.json_save(self._path, self)

    def load(self) -> None:
        loaded_dict = utils.json_load(self._path)
        self.playlist = guild_playlist_decoder(self, self._audio_file_library, loaded_dict["playlist"])
        self.playedlist = playlist.playlist_decoder(loaded_dict["playedlist"])

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
        self.root = "./data/guilds"
        utils.create_folder(self.root)
        self.guild_dict = {}
        self.hashtag_file_path = f"{self.root}/#Guilds.json"
        # TODO hashtag文件内名称键重复两遍

        # 检查#Guilds文件
        if not os.path.exists(self.hashtag_file_path):
            utils.json_save(self.hashtag_file_path, {})
        try:
            self.hashtag_file = utils.json_load(self.hashtag_file_path)
        except errors.JSONFileError:
            raise errors.JSONFileError

    def save_hashtag_file(self):
        utils.json_save(self.hashtag_file_path, self.hashtag_file)

    def check(self, ctx: discord.ApplicationContext, audio_file_library: file_management.AudioFileLibrary) -> None:
        guild_id = ctx.guild.id
        guild_name = ctx.guild.name

        # 如果guild_dict中不存在本Discord服务器
        if guild_id not in self.guild_dict:
            self.guild_dict[guild_id] = Guild(ctx.guild, self.root, audio_file_library)

        # 更新#Guilds文件
        if guild_id not in self.hashtag_file or guild_name != self.hashtag_file[guild_id]:
            self.hashtag_file[guild_id] = guild_name
            self.save_hashtag_file()

    def get_guild(self, ctx: discord.ApplicationContext) -> Union[Guild, None]:
        guild_id = ctx.guild.id
        if guild_id in self.guild_dict:
            return self.guild_dict[guild_id]
        else:
            return None

    def save_all(self) -> None:
        for key in self.guild_dict:
            self.guild_dict[key].save()


class GuildPlaylist(playlist.Playlist):
    def __init__(self, guild: Guild, file_library: file_management.AudioFileLibrary,
                 limitation: Union[int, None] = None):
        super().__init__(f"{guild.get_name()} 主播放列表", limitation, None)
        self._guild = guild
        self._file_library = file_library

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
            self._file_library.unlock_audio(target_audio)
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
            self._file_library.lock_audio(new_audio)
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
            self._file_library.lock_audio(new_audio)
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
            self._file_library.unlock_audio(target_audio)
            self._guild.save()


def guild_playlist_decoder(
        guild: Guild, file_library: file_management.AudioFileLibrary, info_dict: dict) -> GuildPlaylist:
    new_playlist = GuildPlaylist(guild, file_library, info_dict["limitation"])
    for item in info_dict["playlist"]:
        current_audio = audio.audio_decoder(item)
        new_playlist.append_audio(current_audio)
        file_library.lock_audio(current_audio)
    return new_playlist
