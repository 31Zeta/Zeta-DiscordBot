from typing import *
from discord.errors import *

"""
虽然没必要，就是写着玩
"""

class UninitializedError(Exception):
    def __init__(self, name: Optional[str]):
        super().__init__()
        self.name = name

    def __str__(self):
        if self.name is None:
            return "模块未初始化"
        else:
            return f"{self.name}未初始化"


class InitializationError(Exception):
    def __init__(self, name: str, description: str):
        super().__init__()
        self.name = name
        self.description = description

    def __str__(self):
        return f"{self.name}初始化失败：{self.description}"


class UserCancelled(Exception):
    def __init__(self, description: Optional[str] = None):
        super().__init__()
        self.description = description

    def __str__(self):
        if self.description is None:
            return "用户取消操作"
        else:
            return f"用户取消操作：{self.description}"


class LanguageNotFound(Exception):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "未能找到此语言"


class JSONFileError(Exception):
    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def __str__(self):
        return f"Json文件<{self.path}>已损坏"


class KeyAlreadyExists(KeyError):
    def __init__(self, key: str):
        super().__init__()
        self.key = key

    def __str__(self):
        return f"键值<{self.key}>已经存在"


class NoResponse(Exception):
    def __init__(self, name: Optional[str]):
        super().__init__()
        self.name = name

    def __str__(self):
        if self.name is None:
            return f"无响应"
        else:
            return f"<{self.name}>无响应"


class StorageFull(Exception):
    def __init__(self, library_name=None):
        super().__init__()
        self.library_name = library_name

    def __str__(self):
        if self.library_name is not None:
            return f"{self.library_name}已满"
        else:
            return "库已满"


class GetInfoDownloadError(Exception):
    def __init__(self, original_error, info: dict):
        super().__init__()
        self.original_error = original_error
        self.info = info

    def __str__(self):
        if "title" in self.info:
            return f"触发异常：{self.original_error}，尝试对{self.info['title']}的信息获取或下载失败"
        else:
            return f"触发异常：{self.original_error}"
