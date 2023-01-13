from discord.errors import *


class UserCancelled(RuntimeError):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "用户取消了该操作"


class SettingKeyNotFound(RuntimeError):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "未能找到该项设置"
