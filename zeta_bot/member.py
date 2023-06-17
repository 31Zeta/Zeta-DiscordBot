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


class Member:
    def __init__(self, ctx: discord.ApplicationContext):
        current_time = utils.time()
        self.id = ctx.user.id
        self.path = f"./data/member/{self.id}"

        # 如果用户已存在
        if os.path.exists(self.path):
            self.load()
            # 更新用户信息
            self.update(ctx)

        # 如果用户不存在则新建用户档案
        else:
            self.name = ctx.author.name  # .name / .global_name
            # self.group = Normal
            self.guilds = {}
            self.data = {"first_contact": current_time, "play_counter": 0}
            self.property = {"playlist": []}

            # 储存该用户在此服务器的信息
            self.guilds[ctx.guild.id] = {"nickname": ctx.author.nick}

    def encode(self) -> dict:
        info_dict = {
            "id": self.id,
            "name": self.name,
            "group": self.group.name.value,
            "guilds": self.guilds,
            "data": self.data,
            "property": self.property
        }
        return info_dict

    def save(self):
        utils.json_save(self.path, self.encode())

    def load(self):
        loaded_dict = utils.json_load(self.path)
        self.id = loaded_dict["id"]
        self.name = loaded_dict["name"]
        self.guilds = loaded_dict["guilds"]
        self.data = loaded_dict["data"]
        self.property = loaded_dict["property"]

    def update(self, ctx: discord.ApplicationContext):
        """
        更新用户信息
        """
        if ctx.author.id == self.id:
            self.name = ctx.author.name
            self.guilds[ctx.guild.id]["nickname"] = ctx.author.nick
            self.save()

    def set_group(self):
        pass


@decorators.Singleton
class MemberLibrary:
    """
    用于管理本地用户文件以及#Members文件
    """
    def __init__(self):
        self.group_config_path = "./zeta_bot/group_permission_config.json"
        if not os.path.exists(self.group_config_path):
            utils.json_save(self.group_config_path, default_permission_config)
        try:
            self.group_config = utils.json_load(self.group_config_path)
        except errors.JsonFileError:
            raise errors.InitializationFailed("MemberLibrary", "权限组文件读取错误")

        utils.create_folder("./data/members")
        self.root = "./data/members/"
        self.members_file_path = f"{self.root}#Members.json"
        self.group_list = list(self.group_config.keys())

        if not os.path.exists(self.members_file_path):
            utils.json_save(self.members_file_path, {})
        try:
            self.members_file = utils.json_load(self.members_file_path)
        except errors.JsonFileError:
            pass

    def save_members(self):
        utils.json_save(self.members_file_path, self.members_file)

    def check(self, ctx: discord.ApplicationContext) -> None:
        user_id = ctx.user.id
        user_name = ctx.user.name
        path = f"{self.root}{user_id}.json"

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
            if user_id not in self.members_file or user_name != self.members_file[user_id]:
                self.members_file[user_id] = user_name
                self.save_members()
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
                    "language": lang.system_language
                },
                "data": {"first_contact": utils.time(), "play_counter": 0},
                "property": {"playlists": []}
            }
            utils.json_save(path, temp_dict)
            # 更新#Members文件
            self.members_file[user_id] = user_name
            self.save_members()

    def allow(self, user_id, action: str) -> bool:
        path = f"{self.root}{user_id}.json"
        try:
            user_dict = utils.json_load(path)
            group = user_dict["group"]
            return self.group_config[group][action]
        except KeyError:
            return False

    def get_lang(self, ctx: discord.ApplicationContext) -> str:
        user_id = ctx.user.id
        path = f"{self.root}{user_id}.json"
        user_dict = utils.json_load(path)
        return user_dict["guilds"][ctx.guild.id]["language"]

    def play_counter_increment(self, user_id) -> None:
        path = f"{self.root}{user_id}.json"
        user_dict = utils.json_load(path)
        user_dict["data"]["play_counter"] += 1
        utils.json_save(path, user_dict)


permissions = {
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
