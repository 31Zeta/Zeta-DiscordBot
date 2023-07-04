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
    member,
    audio,
    playlist
)


class Guild:
    def __init__(self, guild: discord.guild, lib_root: str):
        self.guild = guild
        self.id = self.guild.id
        self.name = self.guild.name
        self.lib_root = lib_root
        self.root = f"{self.lib_root}/{self.guild.id}"
        self.path = f"{self.root}/{self.guild.id}.json"
        self.voice_client = self.guild.voice_client

        if not os.path.exists(self.root):
            utils.create_folder(self.root)

        try:
            self.load()
        except FileNotFoundError:
            self.playlist = playlist.Playlist(f"{self.name} 主播放列表")
            self.save()

        self.voice_volume = 100.0

    def get_playlist(self) -> playlist.Playlist:
        return self.playlist

    def get_voice_volume(self) -> float:
        return self.voice_volume

    def set_voice_volume(self, volume: Union[int, float]) -> None:
        self.voice_volume = float(volume)
        if self.voice_client is not None and self.voice_client.is_playing():
            self.voice_client.source.volume = self.voice_volume / 100.0

    def save(self) -> None:
        utils.json_save(self.path, self)

    def load(self) -> None:
        loaded_dict = utils.json_load(self.path)
        self.playlist = playlist.playlist_decoder(loaded_dict["playlist"])

    def encode(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "playlist": self.playlist
        }


@decorators.Singleton
class GuildLibrary:
    def __init__(self):
        self.root = "./data/guilds"
        utils.create_folder(self.root)
        self.guild_dict = {}
        self.hashtag_file_path = f"{self.root}/#Guilds.json"

        # 检查#Guilds文件
        if not os.path.exists(self.hashtag_file_path):
            utils.json_save(self.hashtag_file_path, {})
        try:
            self.hashtag_file = utils.json_load(self.hashtag_file_path)
        except errors.JSONFileError:
            raise errors.JSONFileError

    def save_hashtag_file(self):
        utils.json_save(self.hashtag_file_path, self.hashtag_file)

    def check(self, ctx: discord.ApplicationContext) -> None:
        guild_id = ctx.guild.id
        guild_name = ctx.guild.name

        # 如果guild_dict中不存在本Discord服务器
        if guild_id not in self.guild_dict:
            self.guild_dict[guild_id] = Guild(ctx.guild, self.root)

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
