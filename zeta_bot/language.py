import os
from zeta_bot import (
    errors,
    decorators
)

language_code_dict = {
    "zh_cn": "简体中文",
    "en_us": "English"
}

DEFAULT_LANGUAGE = "zh_cn"


@decorators.Singleton
class Lang:
    def __init__(self, lang_code=DEFAULT_LANGUAGE):
        file_path = f"./zeta_bot/lang/{lang_code}.lang"
        if lang_code in language_code_dict and os.path.exists(file_path):
            self.system_language = lang_code
            self.language_dict = {}
            self.load_all_languages()
        else:
            raise errors.InitializationFailed("系统语言", "找不到对应语言或文件")

    def __str__(self) -> str:
        return self.system_language

    def __contains__(self, language_code) -> bool:
        """
        返回language_dict是否包含指定language_code
        """
        return language_code in self.language_dict

    def load_language(self, lang_code: str) -> None:
        """
        如果lang_code存在于language_code_dict中并且对应的.lang文件存在
        则读取.lang文件并加载到self.language_dict中
        """
        file_path = f"./zeta_bot/lang/{lang_code}.lang"

        if lang_code in language_code_dict and os.path.exists(file_path):
            if lang_code not in self.language_dict:
                self.language_dict[lang_code] = {}
            read_lang_file(file_path, self.language_dict[lang_code])
        else:
            raise errors.LanguageNotFound

    def load_all_languages(self) -> None:
        for lang_code in language_code_dict:
            try:
                self.load_language(lang_code)
            except errors.LanguageNotFound:
                continue

    def set_system_language(self, lang_code) -> None:
        if lang_code in language_code_dict and lang_code in self.language_dict:
            self.system_language = lang_code
        else:
            raise errors.LanguageNotFound

    def get_string(self, str_id: str, lang_code=None, slash_n=False) -> str:
        """
        返回对应lang_code中对应str_id的字符串，如lang_code不包含此字符串则尝试系统语言，
        如果系统语言中字符串仍不存在则返回str_id本身
        可使用slash_n来确定是否使用字符内的换行符
        """
        if lang_code is None:
            lang_code = self.system_language

        if lang_code in self.language_dict and str_id in self.language_dict[lang_code]:
            lang_code = lang_code

        elif str_id in self.language_dict[self.system_language]:
            lang_code = self.system_language

        else:
            return str_id

        # 是否使用内置换行符
        if slash_n:
            return self.language_dict[lang_code][str_id].replace('\\n', '\n')
        else:
            return self.language_dict[lang_code][str_id]

    def printl(self, str_id: str, lang_code=None, slash_n=False):
        print(self.get_string(str_id, lang_code, slash_n))


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
    for key in language_code_dict:
        result += f"{indent * space}{key}: {language_code_dict[key]}\n"

    return result


def get_lang_code_list() -> list:
    result = []
    for key in language_code_dict:
        result.append(key)

    return result
