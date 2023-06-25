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
    def __init__(self, guild_id, guild_name, lib_root: str):
        self.id = guild_id
        self.name = guild_name
        self.lib_root = lib_root
        self.playlist = playlist.Playlist(f"{self.name} 主播放列表")
        self.voice_volume = 100.0

    def get_playlist(self) -> playlist.Playlist:
        return self.playlist

    def get_voice_volume(self) -> float:
        return self.voice_volume

    def set_voice_volume(self, volume: Union[int, float]) -> None:
        self.voice_volume = float(volume)

    def save(self) -> None:
        utils.json_save(f"{self.lib_root}/{self.id}/{self.id}.json", self)

    def load(self) -> None:
        loaded_dict = utils.json_load(f"{self.lib_root}/{self.id}/{self.id}.json")
        self.name = loaded_dict["name"]
        self.playlist = playlist.playlist_decoder(loaded_dict["playlist"])

    def encode(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "lib_root": self.lib_root,
            "playlist": self.playlist
        }


def guild_decoder(info_dict: dict) -> Guild:
    new_guild = Guild(info_dict["id"], info_dict["name"], info_dict["lib_root"])
    new_guild.playlist = playlist.playlist_decoder(info_dict["playlist"])
    return new_guild


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
        guild_root = f"{self.root}/{guild_id}"
        file_path = f"{guild_root}/{guild_id}.json"

        # TODO 读取方式有问题，名称变动可能导致播放列表重新读取，需重写

        # 如果服务器目录不存在
        if not os.path.exists(guild_root):
            utils.create_folder(guild_root)

        # 如果服务器主文件存在
        if os.path.exists(file_path):
            loaded_dict = utils.json_load(file_path)
            # 更新服务器名
            if guild_name != loaded_dict["name"]:
                loaded_dict["name"] = guild_name
                # 保存变动
                utils.json_save(file_path, loaded_dict)

        # 如果服务器主文件不存在
        else:
            loaded_dict = {
                "id": guild_id,
                "name": guild_name,
                "lib_root": self.root,
                "playlist": playlist.Playlist(f"{guild_name} 主播放列表")
            }
            utils.json_save(file_path, loaded_dict)

        # 如果guild_dict中不存在本Discord服务器
        if guild_id not in self.guild_dict:
            self.guild_dict[guild_id] = guild_decoder(loaded_dict)
        # 如果guild_dict中存在本Discord服务器
        else:
            self.guild_dict[guild_id].load()

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
