import json
import os
import datetime
from user_group import UserGroup


class User:
    def __init__(self, discord_id, name, library_path) -> None:
        self.id = discord_id
        self.user_group = UserGroup("member")
        self.name = name
        self.nicknames = {}
        self.user_data = {"first_contact": "", "play_counter": 0}
        self.user_property = {}

        if library_path.endswith("/"):
            library_path = library_path.rstrip("/")
        self.path = f"{library_path}/{self.id}.json"

        if os.path.exists(self.path):
            self.load()

    def __repr__(self) -> str:
        return f"{self.id}: {self.name}"

    def __str__(self) -> str:
        return f"{self.id}: {self.name}"

    def save(self) -> str:
        with open(self.path, "w", encoding="utf-8") as file:
            file.write(json.dumps(self.encode(), sort_keys=False, indent=4))
        return self.path

    def load(self) -> None:
        with open(self.path, "r", encoding="utf-8") as file:
            load_dict = json.loads(file.read())
        self.user_group = UserGroup(load_dict["user_group"])
        self.nicknames = load_dict["nicknames"]
        self.user_data = load_dict["user_data"]
        self.user_property = load_dict["user_property"]
        self.save()

    def change_user_group(self, group: str) -> None:
        self.user_group = UserGroup(group)

    def authorized(self, action: str) -> bool:
        """
        返回一个布尔值代表用户是否有<action>指令的权限
        """
        return self.user_group.permission[action]

    def first_contact(self) -> None:
        self.user_data["first_contact"] = str(datetime.datetime.now())

    def play_counter(self) -> None:
        self.user_data["play_counter"] += 1
        self.save()

    def change_name(self, new_name) -> None:
        self.name = new_name
        self.save()

    def change_current_guild_nickname(self, ctx, new_nickname: str) -> None:
        self.nicknames[ctx.guild.id] = new_nickname
        self.save()

    def create_custom_playlist(self, name) -> bool:
        if "custom_playlist" not in self.user_property:
            self.user_property["custom_playlist"] = {}

        if name in self.user_property["custom_playlist"]:
            return False

        else:
            pass

    def encode(self) -> dict:
        info_dict = {
            "id": self.id, "user_group": self.user_group.name,
            "name": self.name, "nicknames": self.nicknames,
            "user_data": self.user_data, "user_property": self.user_property
        }
        return info_dict
