from discord.errors import *


class BootModeNotFound(RuntimeError):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "未找到指定启动模式"


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


class MemberGroupNotFound(RuntimeError):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "未能找到该用户组"

