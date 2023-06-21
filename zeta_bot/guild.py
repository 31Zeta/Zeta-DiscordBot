import discord
import os

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
    def __init__(self, guild_id, guild_name):
        self.id = guild_id
        self.name = guild_name
        self.playlist = playlist.Playlist(f"{self.name} 主播放列表")
        self.voice_volume = 100

    def get_playlist(self) -> playlist.Playlist:
        return self.playlist

    def get_voice_volume(self) -> int:
        return self.voice_volume

    def set_voice_volume(self, volume: int) -> None:
        self.voice_volume = volume

    def encode(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "playlist": self.playlist
        }


def guild_decoder(info_dict: dict) -> Guild:
    new_guild = Guild(info_dict["id"], info_dict["name"])
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

        # 如果服务器目录不存在
        if not os.path.exists(guild_root):
            utils.create_folder(guild_root)

        # 如果服务器主文件存在
        if not os.path.exists(file_path):
            guild_dict = utils.json_load(file_path)
            # 更新服务器名
            if guild_name != guild_dict["name"]:
                guild_dict["name"] = guild_name
            # 保存变动，将服务器加入guild_dict
            new_guild = guild_decoder(guild_dict)
            guild_dict[guild_id] = new_guild
            utils.json_save(file_path, new_guild)

            # 更新#Guilds文件
            if guild_id not in self.hashtag_file or guild_name != self.hashtag_file[guild_id]:
                self.hashtag_file[guild_id] = guild_name
                self.save_hashtag_file()

        # 如果服务器主文件不存在
        else:
            new_guild = Guild(guild_id, guild_name)
            utils.json_save(file_path, new_guild)

            # 更新#Guilds文件
            self.hashtag_file[guild_id] = guild_name
            self.save_hashtag_file()
