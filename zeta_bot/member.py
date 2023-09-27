import discord
import os

from zeta_bot import (
    errors,
    language,
    utils,
    decorators
)

# 多语言模块
lang = language.Lang()
_ = lang.get_string
printl = lang.printl


permissions = {
    "info": False,
    "help": False,
    "play": False,
    "join": False,
    "leave": False,
    "skip": False,
    "move": False,
    "pause": False,
    "resume": False,
    "volume": False,
    "list": False,
    "broadcast": False,
    "reboot": False,
    "shutdown": False,
    "change_member_group_from": {
        "administrator": False,
        "standard": False,
        "restricted": False,
        "banned": False,
        "blocked": False,
    },
    "change_member_group_to": {
        "administrator": False,
        "standard": False,
        "restricted": False,
        "banned": False,
        "blocked": False,
    },
    "debug": False
}

default_permission_config = {
    "administrator": {
        "info": True,
        "help": True,
        "play": True,
        "join": True,
        "leave": True,
        "skip": True,
        "move": True,
        "pause": True,
        "resume": True,
        "volume": True,
        "list": True,
        "broadcast": False,
        "reboot": True,
        "shutdown": False,
        "change_member_group_from": {
            "administrator": False,
            "standard": True,
            "restricted": True,
            "banned": True,
            "blocked": True,
        },
        "change_member_group_to": {
            "administrator": False,
            "standard": True,
            "restricted": True,
            "banned": True,
            "blocked": True,
        },
        "debug": False
    },
    "standard": {
        "info": True,
        "help": True,
        "play": True,
        "join": True,
        "leave": True,
        "skip": True,
        "move": True,
        "pause": True,
        "resume": True,
        "volume": True,
        "list": True,
        "broadcast": False,
        "reboot": False,
        "shutdown": False,
        "change_member_group_from": {
            "administrator": False,
            "standard": False,
            "restricted": False,
            "banned": False,
            "blocked": False,
        },
        "change_member_group_to": {
            "administrator": False,
            "standard": False,
            "restricted": False,
            "banned": False,
            "blocked": False,
        },
        "debug": False
    },
    "restricted": {
        "info": True,
        "help": True,
        "play": True,
        "join": False,
        "leave": False,
        "skip": False,
        "move": False,
        "pause": False,
        "resume": False,
        "volume": False,
        "list": True,
        "broadcast": False,
        "reboot": False,
        "shutdown": False,
        "change_member_group_from": {
            "administrator": False,
            "standard": False,
            "restricted": False,
            "banned": False,
            "blocked": False,
        },
        "change_member_group_to": {
            "administrator": False,
            "standard": False,
            "restricted": False,
            "banned": False,
            "blocked": False,
        },
        "debug": False
    },
    "banned": {
        "info": True,
        "help": False,
        "play": False,
        "join": False,
        "leave": False,
        "skip": False,
        "move": False,
        "pause": False,
        "resume": False,
        "volume": False,
        "list": False,
        "broadcast": False,
        "reboot": False,
        "shutdown": False,
        "change_member_group_from": {
            "administrator": False,
            "standard": False,
            "restricted": False,
            "banned": False,
            "blocked": False,
        },
        "change_member_group_to": {
            "administrator": False,
            "standard": False,
            "restricted": False,
            "banned": False,
            "blocked": False,
        },
        "debug": False
    }
}


@decorators.Singleton
class MemberLibrary:
    """
    用于管理本地用户文件以及#Members文件
    """
    def __init__(self):
        self.root = "./data/members"
        utils.create_folder(self.root)

        self.group_config_path = "./configs/group_permission_config.json"
        # 如组权限文件不存在则创建默认文件
        if not os.path.exists(self.group_config_path):
            utils.json_save(self.group_config_path, default_permission_config)
        try:
            self.group_config = utils.json_load(self.group_config_path)
        except errors.JSONFileError:
            raise errors.InitializationFailed("MemberLibrary", "组权限文件读取错误")

        self.hashtag_file_path = f"{self.root}/#Members.json"
        self.group_list = list(self.group_config.keys())

        if not os.path.exists(self.hashtag_file_path):
            utils.json_save(self.hashtag_file_path, {})
        self.hashtag_file = utils.json_load(self.hashtag_file_path)

    def save_hashtag_file(self):
        utils.json_save(self.hashtag_file_path, self.hashtag_file)

    def check(self, ctx: discord.ApplicationContext) -> None:
        user_id = ctx.user.id
        user_name = ctx.user.name
        path = f"{self.root}/{user_id}.json"

        # 如果用户文件存在
        if os.path.exists(path):
            user_dict = utils.json_load(path)
            # 更新用户名
            if user_name != user_dict["name"]:
                user_dict["name"] = user_name
            # 更新用户服务器数据
            if ctx.guild.id not in user_dict["guilds"]:
                user_dict["guilds"][ctx.guild.id] = {"nickname": ctx.user.nick, "language": lang.system_language}
            # 更新用户此服务器的昵称
            if ctx.user.nick != user_dict["guilds"][ctx.guild.id]["nickname"]:
                user_dict["guilds"][ctx.guild.id]["nickname"] = ctx.user.nick
            # 更新#Members文件
            if user_id not in self.hashtag_file or user_name != self.hashtag_file[user_id]:
                self.hashtag_file[user_id] = user_name
                self.save_hashtag_file()
            # 保存变动
            utils.json_save(path, user_dict)

        # 如果用户文件不存在
        else:
            temp_dict = {
                "id": user_id,
                "name": user_name,
                "group": "standard",
                "language": lang.system_language,
                "guilds": {ctx.guild.id: {
                    "nickname": ctx.user.nick},
                },
                "data": {"first_contact": utils.time(), "play_counter": 0},
                "property": {"playlists": []}
            }
            utils.json_save(path, temp_dict)
            # 更新#Members文件
            self.hashtag_file[user_id] = user_name
            self.save_hashtag_file()

    def allow(self, user_id, operation: str) -> bool:

        path = f"{self.root}/{user_id}.json"
        try:
            user_dict = utils.json_load(path)
            group = user_dict["group"]
            return self.group_config[group][operation]
        except KeyError:
            return False

    def get_lang(self, user_id) -> str:
        path = f"{self.root}/{user_id}.json"
        user_dict = utils.json_load(path)
        return user_dict["language"]

    def get_guild_lang(self, ctx: discord.ApplicationContext) -> str:
        user_id = ctx.user.id
        path = f"{self.root}/{user_id}.json"
        user_dict = utils.json_load(path)
        return user_dict["guilds"][ctx.guild.id]["language"]

    def get_group(self, user_id) -> str:
        path = f"{self.root}/{user_id}.json"
        user_dict = utils.json_load(path)
        return user_dict["group"]

    def play_counter_increment(self, user_id) -> None:
        path = f"{self.root}/{user_id}.json"
        user_dict = utils.json_load(path)
        user_dict["data"]["play_counter"] += 1
        utils.json_save(path, user_dict)
