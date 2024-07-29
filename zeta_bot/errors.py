from discord.errors import *

"""
虽然没必要，就是写着玩
"""


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


class JSONFileError(RuntimeError):
    def __init__(self, path):
        super().__init__()
        self.path = path

    def __str__(self):
        return f"Json文件<{self.path}>已损坏"


class KeyAlreadyExists(RuntimeError):
    def __init__(self, key):
        super().__init__()
        self.key = key

    def __str__(self):
        return f"键值<{self.key}>已经存在"


class KeyNotFound(RuntimeError):
    """就是不用KeyError啊哈哈"""
    def __init__(self, key):
        super().__init__()
        self.key = key

    def __str__(self):
        return f"键值<{self.key}>不存在"


class StorageFull(RuntimeError):
    def __init__(self, library_name=None):
        super().__init__()
        self.library_name = library_name

    def __str__(self):
        if self.library_name is not None:
            return f"{self.library_name}已满"
        else:
            return "库已满"


class GetInfoDownloadError(RuntimeError):
    def __init__(self, original_error, info: dict):
        super().__init__()
        self.original_error = original_error
        self.info = info

    def __str__(self):
        if "title" in self.info:
            return f"触发异常：{self.original_error}，尝试对{self.info['title']}的信息获取或下载失败"
        else:
            return f"触发异常：{self.original_error}"
