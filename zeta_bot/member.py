import discord
import os
from enum import Enum

from zeta_bot import utils


class Member:
    def __init__(self, ctx: discord.ApplicationContext):
        current_time = utils.time()
        self.id = ctx.author.id
        self.path = f"./data/member/{self.id}"

        # 如果用户已存在
        if os.path.exists(self.path):
            self.load()
            # 更新用户信息
            self.update(ctx)

        # 如果用户不存在则新建用户档案
        else:
            self.name = ctx.author.name
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
        self.group = eval(loaded_dict["group"])
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


class MemberLibrary(dict):
    """
    类本身用于储存活跃的用户类，self.local用于管理本地.Members文件
    """
    def __init__(self):
        super().__init__()

        self.path = "./data/member/.Members.json"
        if not os.path.exists(self.path):
            utils.json_save(self.path, {})
        self.local = {}
        self.load_local()

    def update_local(self, member: Member):
        self.local[member.id] = member.name
        self.save_local()

    def save_local(self):
        utils.json_save(self.path, self.local)

    def load_local(self):
        loaded_dict = utils.json_load(self.path)
        for key in loaded_dict:
            self.local[key] = loaded_dict[key]

    def get_member(self, ctx: discord.ApplicationContext) -> Member:
        if ctx.author.id not in self:
            member = Member(ctx)
            self[ctx.author.id] = member
        # 更新用户信息
        self[ctx.author.id].update(ctx)
        # 更新库本地文件
        self.update_local(self[ctx.author.id])
        return self[ctx.author.id]


group_permission_configs = {
    "shutdown": False,
    "reboot": False,
    "change_user_group": False,
    "broadcast": False,
    "blacklist": False,
    "debug": False
}

class MemberGroup:

    def __init__(self):
        pass

    def permission(self, action: str):
        raise NotImplementedError


