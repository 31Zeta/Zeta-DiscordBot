from discord.errors import *


class InitializationFailed(RuntimeError):
    def __init__(self, name, description):
        super().__init__()
        self.name = name
        self.description = description

    def __str__(self):
        return f"{self.name}初始化失败，描述为：{self.description}"


class InitializationError(RuntimeError):
    def __init__(self, name, description):
        super().__init__()
        self.name = name
        self.description = description

    def __str__(self):
        return f"{self.name}初始化出现错误，描述为：{self.description}"


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


class LanguageNotFound(RuntimeError):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "未能找到此语言"


class SettingChanged(RuntimeError):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "设置不匹配，设置选项可能发生过变更"
