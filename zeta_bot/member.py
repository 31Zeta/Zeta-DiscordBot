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
            self.name = ctx.author.name
            self.guilds[ctx.guild.id] = {"nickname": ctx.author.nick}
            self.save()

            self.update_members_library()

        # 如果用户不存在则新建用户档案
        else:
            self.name = ctx.author.name
            self.group = Normal
            self.guilds = {}
            self.data = {"first_contact": current_time, "play_counter": 0}
            self.property = {"playlist": []}

            # 储存该用户在此服务器的信息
            self.guilds[ctx.guild.id] = {"nickname": ctx.author.nick}

            self.update_members_library()

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

    def update_members_library(self):
        """
        更新记录名称的总字典
        """
        path = "./data/member/.Members"
        if not os.path.exists(path):
            utils.json_save(path, {})

        loaded_dict = utils.json_load(path)
        loaded_dict[self.id] = self.name
        utils.json_save(path, loaded_dict)

    def set_group(self):
        pass


class Owner(Enum):
    name = "Owner"


class Admin(Enum):
    name = "Admin"


class Normal(Enum):
    name = "Normal"


class Banned(Enum):
    name = "Banned"

