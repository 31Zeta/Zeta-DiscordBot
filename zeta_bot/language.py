import os
from typing import Union, List, Tuple
from zeta_bot import (
    errors,
    decorators
)

locale_dict = {
    "zh-CN": "中文",
    "en-US": "English",
}
# Discord 官方地区代码文档
# https://discord.com/developers/docs/reference#locales

DEFAULT_LANGUAGE = "zh-CN"


@decorators.Singleton
class Lang:
    def __init__(self, default_lang_code=DEFAULT_LANGUAGE):
        file_path = f"./zeta_bot/lang/{default_lang_code}.lang"

        if default_lang_code not in locale_dict or not os.path.exists(file_path):
            raise errors.InitializationFailed("系统语言", "找不到对应语言或文件")

        self.system_language = default_lang_code
        self.command_names = {}
        self.language_dict = {}
        self.load_all_languages()

    def __str__(self) -> str:
        return self.system_language

    def __contains__(self, language_code) -> bool:
        """
        返回language_dict是否包含指定language_code
        """
        return language_code in self.language_dict

    def load_command_names(self, locale_code: str) -> None:
        """
        如果locale_code存在于locale_dict中并且对应的.lang文件存在
        则读取.lang文件并加载到self.command_names中
        """
        file_path = f"./zeta_bot/lang/{locale_code}_commands.lang"

        if locale_code in locale_dict and os.path.exists(file_path):
            loaded_list = read_commands_lang_file(file_path)
            for name_tuple in loaded_list:
                if name_tuple[0] not in self.command_names:
                    self.command_names[name_tuple[0]] = {}
                self.command_names[name_tuple[0]][locale_code] = name_tuple[1]

    def load_language(self, locale_code: str) -> None:
        """
        如果locale_code存在于locale_dict中并且对应的.lang文件存在
        则读取.lang文件并加载到self.language_dict中
        """
        file_path = f"./zeta_bot/lang/{locale_code}.lang"

        if locale_code in locale_dict and os.path.exists(file_path):
            if locale_code not in self.language_dict:
                self.language_dict[locale_code] = {}
            read_lang_file(file_path, self.language_dict[locale_code])
        else:
            raise errors.LanguageNotFound

    def load_all_languages(self) -> None:
        for locale_code in locale_dict:
            try:
                self.load_command_names(locale_code)
                self.load_language(locale_code)
            except errors.LanguageNotFound:
                continue

    def set_system_language(self, locale_code) -> None:
        locale_code = legal_locale_code(locale_code)
        if locale_code in locale_dict and locale_code in self.language_dict:
            self.system_language = locale_code
        else:
            raise errors.LanguageNotFound

    def get_string(self, str_id: str, locale_code=None, slash_n=False) -> str:
        """
        返回对应lang_code中对应str_id的字符串，如lang_code不包含此字符串则尝试系统语言，
        如果系统语言中字符串仍不存在则返回str_id本身
        可使用slash_n来确定是否使用字符内的换行符
        """
        if locale_code is None:
            locale_code = self.system_language

        if locale_code in self.language_dict and str_id in self.language_dict[locale_code]:
            locale_code = locale_code

        elif str_id in self.language_dict[self.system_language]:
            locale_code = self.system_language

        else:
            return str_id

        # 是否使用内置换行符
        if slash_n:
            return self.language_dict[locale_code][str_id].replace('\\n', '\n')
        else:
            return self.language_dict[locale_code][str_id]

    def printl(self, str_id: str, locale_code=None, slash_n=False):
        print(self.get_string(str_id, locale_code, slash_n))

    def get_command_name(self, name: str) -> dict:
        if name in self.command_names:
            return self.command_names[name]
        else:
            return {}


def read_commands_lang_file(file_path: str) -> List[Tuple[str, str]]:
    """
    读取指令名称.lang文件并返回一个包含所有指令对应的本地化名称的列表
    """
    with open(file_path, "r", encoding="utf-8") as file:
        result = []
        for line in file.readlines():
            equal_index = line.find('=')
            if equal_index < 1 or line.startswith('#'):
                continue
            else:
                result.append((line[:equal_index], line[equal_index + 1:].strip('\n')))
    return result


def read_lang_file(file_path: str, target_dict: dict) -> None:
    """
    读取.lang文件并加载到target_dict中
    """
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file.readlines():
            equal_index = line.find('=')
            if equal_index < 1 or line.startswith('#'):
                continue
            else:
                target_dict[line[:equal_index]] = line[equal_index + 1:].strip('\n')


def list_lang_code(indent=0) -> str:
    result = ""
    space = " "
    for key in locale_dict:
        result += f"{indent * space}{key}: {locale_dict[key]}\n"

    return result


def get_lang_code_list() -> list:
    result = []
    for key in locale_dict:
        result.append(key)

    return result


def legal_locale_code(locale_code) -> str:
    if "-" in locale_code:
        split_index = locale_code.find("-")
        return locale_code[:split_index].lower() + "-" + locale_code[split_index + 1:].upper()
    elif "_" in locale_code:
        split_index = locale_code.find("_")
        return locale_code[:split_index].lower() + "-" + locale_code[split_index + 1:].upper()
    else:
        return locale_code
