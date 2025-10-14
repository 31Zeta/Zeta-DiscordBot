from typing import *
import sys
import os
import time
import datetime
from enum import Enum
import json
import re
import requests
import getpass
import shutil

from zeta_bot import (
    errors,
    language
)

# 多语言模块
lang = language.Lang()
_ = lang.get_string
printl = lang.printl


def ctime_str() -> str:
    """
    当前时间：字符串形式（Current Time String）
    :return: 当前时间的字符串（格式为：年-月-日 时:分:秒）
    """
    return str(datetime.datetime.now())[:19]


def ctime_datetime() -> datetime.datetime:
    """
    当前时间：datetime形式（Current Time datetime）
    :return: 当前时间的datetime
    """
    return datetime.datetime.now()


def create_folder(path: str) -> None:
    """
    检测在指定目录是否存在文件夹，如果不存在则创建
    """
    if not os.path.exists(path):
        os.mkdir(path)


def json_save(json_path: str, saving_item) -> None:
    """
    将<saving_item>以json格式保存到<json_path>
    **警告**：json格式的键值必须为字符串，否则会被转换为字符串
    """
    with open(json_path, "w", encoding="utf-8") as file:
        file.write(
            json.dumps(
                saving_item,
                default=lambda x: x.encode(),
                sort_keys=False,
                indent=4,
                ensure_ascii=False
            )
        )


def json_load(json_path: str) -> Union[dict, list]:
    """
    读取<json_path>的json文件
    **警告**：json格式的键值必须为字符串，否则会被转换为字符串
    """
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            loaded_dict = json.loads(file.read())
        return loaded_dict
    except json.decoder.JSONDecodeError:
        raise errors.JSONFileError(json_path)


def path_slash_formatting(string: str) -> str:
    """
    将字符串内的所有反斜杠统一替换为正斜杠
    """
    result = ""
    for char in string:
        if char == "\\":
            result += "/"
        else:
            result += char

    return result


def path_end_formatting(string: str) -> str:
    """
    如果字符串内最后一个字符为正斜杠或反斜杠则将之删除
    """
    if string.endswith("/"):
        string = string.rstrip("/")
    elif string.endswith("\\"):
        string = string.rstrip("\\")

    return string


def legal_name(name_str: str) -> str:
    """
    将字符串转换为合法的文件名

    :param name_str: 原文件名
    :return: 转换后文件名
    """

    name_str = name_str.replace("\\", "_")
    name_str = name_str.replace("/", "_")
    name_str = name_str.replace(":", "_")
    name_str = name_str.replace("*", "_")
    name_str = name_str.replace("?", "_")
    name_str = name_str.replace("\"", "_")
    name_str = name_str.replace("<", "_")
    name_str = name_str.replace(">", "_")
    name_str = name_str.replace("|", "_")

    return name_str


class SGR(Enum):
    """
    ANSI标准转义序列的选择图形呈现（Select Graphic Rendition）的枚举类
    \\033：ESC（Escape）控制字符
    [：CSI（Control Sequence Introducer）
    m：表示设置SGR模式
    SGR的使用方法为 “\033[SGRm 信息 \033[0m”
    其中[之后使用可以使用分号分隔开若干SGR序列
    """
    # 样式
    RESET = 0  # 重置/默认样式
    BOLD = 1  # 粗体/高亮
    FAINT = 2  # 细体/弱化
    ITALIC = 3  # 斜体
    UNDERLINE = 4  # 下划线
    BLINK = 5  # 闪烁
    BLINK_FAST = 6  # 闪烁快速（支持较少）
    NEGATIVE = 7  # 反显/反色
    INVISIBLE = 8  # 隐藏
    STRIKETHROUGH = 9  # 删除线
    OVERLINE = 53  # 上划线

    STYLE_LIST = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 53]
    STYLE_NAME_LIST = ["RESET", "BOLD", "FAINT", "ITALIC", "UNDERLINE", "BLINK", "BLINK_FAST", "NEGATIVE", "INVISIBLE", "STRIKETHROUGH", "OVERLINE"]

    # 关闭样式
    BOLD_OFF = 21  # 关闭粗体/高亮
    FAINT_OFF = 22  # 关闭细体/弱化
    ITALIC_OFF = 23  # 关闭斜体
    UNDERLINE_OFF = 24  # 关闭下划线
    BLINK_OFF = 25  # 关闭闪烁
    BLINK_FAST_OFF = 26  # 关闭闪烁快速（支持较少）
    NEGATIVE_OFF = 27  # 关闭反显/反色
    INVISIBLE_OFF = 28  # 关闭隐藏
    STRIKETHROUGH_OFF = 29  # 关闭删除线
    OVERLINE_OFF = 55  # 关闭上划线

    STYLE_OFF_LIST = [21, 22, 23, 24, 25, 26, 27, 28, 29, 55]
    STYLE_OFF_NAME_LIST = ["RESET_OFF", "BOLD_OFF", "FAINT_OFF", "ITALIC_OFF", "UNDERLINE_OFF", "BLINK_OFF", "BLINK_FAST_OFF", "NEGATIVE_OFF", "INVISIBLE_OFF", "STRIKETHROUGH_OFF", "OVERLINE_OFF"]

    # 颜色
    BLACK = 30  # 黑色
    RED = 31  # 红色
    GREEN = 32  # 绿色
    YELLOW = 33  # 黄色
    BLUE = 34  # 蓝色
    MAGENTA = 35  # 品红色
    CYAN = 36  # 青色
    WHITE = 37  # 白色
    BLACK_BRIGHT = 90  # 亮黑色
    RED_BRIGHT = 91  # 亮红色
    GREEN_BRIGHT = 92  # 亮绿色
    YELLOW_BRIGHT = 93  # 亮黄色
    BLUE_BRIGHT = 94  # 亮蓝色
    MAGENTA_BRIGHT = 95  # 亮品红色
    CYAN_BRIGHT = 96  # 亮青色
    WHITE_BRIGHT = 97  # 亮白色

    COLOR_LIST = [30, 31, 32, 33, 34, 35, 36, 37, 90, 91, 92, 93, 94, 95, 96, 97]
    COLOR_NAME_LIST = [
        "BLACK", "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN", "WHITE",
        "BLACK_BRIGHT", "RED_BRIGHT", "GREEN_BRIGHT", "YELLOW_BRIGHT", "BLUE_BRIGHT", "MAGENTA_BRIGHT", "CYAN_BRIGHT", "WHITE_BRIGHT"
    ]

    # 背景色
    BACKGROUND_BLACK = 40  # 黑色背景
    BACKGROUND_RED = 41  # 红色背景
    BACKGROUND_GREEN = 42  # 绿色背景
    BACKGROUND_YELLOW = 43  # 黄色背景
    BACKGROUND_BLUE = 44  # 蓝色背景
    BACKGROUND_MAGENTA = 45  # 品红色背景
    BACKGROUND_CYAN = 46  # 青色背景
    BACKGROUND_WHITE = 47  # 白色背景
    BACKGROUND_BLACK_BRIGHT = 100  # 亮黑色背景
    BACKGROUND_RED_BRIGHT = 101  # 亮红色背景
    BACKGROUND_GREEN_BRIGHT = 102  # 亮绿色背景
    BACKGROUND_YELLOW_BRIGHT = 103  # 亮黄色背景
    BACKGROUND_BLUE_BRIGHT = 104  # 亮蓝色背景
    BACKGROUND_MAGENTA_BRIGHT = 105  # 亮品红色背景
    BACKGROUND_CYAN_BRIGHT = 106  # 亮青色背景
    BACKGROUND_WHITE_BRIGHT = 107  # 亮白色背景

    BACKGROUND_LIST = [40, 41, 42, 43, 44, 45, 46, 47, 100, 101, 102, 103, 104, 105, 106, 107]
    BACKGROUND_NAME_LIST = [
        "BACKGROUND_BLACK", "BACKGROUND_RED", "BACKGROUND_GREEN", "BACKGROUND_YELLOW", "BACKGROUND_BLUE", "BACKGROUND_MAGENTA", "BACKGROUND_CYAN", "BACKGROUND_WHITE",
        "BACKGROUND_BLACK_BRIGHT", "BACKGROUND_RED_BRIGHT", "BACKGROUND_GREEN_BRIGHT", "BACKGROUND_YELLOW_BRIGHT", "BACKGROUND_BLUE_BRIGHT", "BACKGROUND_MAGENTA_BRIGHT", "BACKGROUND_CYAN_BRIGHT", "BACKGROUND_WHITE_BRIGHT"
    ]

# 使用集合推导式获得所有SGR枚举类下的代码
SGR_CODES = {member.value for member in SGR.__members__.values() if isinstance(member.value, int)}


def sgr_value(sgr: Union["SGR", int, str]) -> int:
    """
    获取SGR的值

    :param sgr: 一个用于查找SGR值的对象，可以为SGR枚举类，SGR值本身，或SGR值名称
    :return: SGR值
    :raise ValueError: 未能找到对应的SGR值
    :raise TypeError: 输入参数的类型不正确
    """
    if isinstance(sgr, SGR):
        if not isinstance(sgr.value, int):
            raise ValueError(f"SGR: {sgr}")
        return sgr.value
    elif isinstance(sgr, int):
        if sgr in SGR_CODES:
            return sgr
        else:
            raise ValueError(f"SGR: {sgr}")
    elif isinstance(sgr, str):
        if sgr not in SGR.__members__:
            raise ValueError(f"SGR: {sgr}")
        target_value = SGR[sgr].value
        if not isinstance(target_value, int):
            raise ValueError(f"SGR: {sgr}")
        return target_value
    raise TypeError(f"SGR: {sgr}, Type: {type(sgr)}")


def sgr_format(input_str: str, sgr: Union[SGR, int, str, List[Union[SGR, int, str]], Tuple[Union[SGR, int, str]]]) -> str:
    """
    为字符串添加ANSI SGR转义

    :param input_str: 要添加转义的字符串
    :param sgr: 要添加的SGR效果的枚举类
    """
    result = f"\033["
    if isinstance(sgr, list) or isinstance(sgr, tuple):
        for sgr_item in sgr:
            result += f"{str(sgr_value(sgr_item))};"
        result = result.rstrip(";")
    else:
        result += str(sgr_value(sgr))
    result += "m"
    result += input_str
    result += f"\033[0m"
    return result


class PrintType(Enum):
    """
    字符串输出类型枚举类
    标准类型value为None
    value为一个元组，第一个元素为类型名称，第二个元素为颜色SGR枚举类
    """
    NORMAL = None
    CAUTION = ("注意", SGR.CYAN_BRIGHT)
    WARNING = ("警告", SGR.YELLOW)
    ERROR = ("错误", SGR.RED)
    TITLE = ("标题", SGR.BLUE_BRIGHT)
    OPTION = ("选项", SGR.BLACK_BRIGHT)
    DEBUG = ("调试", SGR.CYAN)


def print_format(
    message: str,
    extra_message: Optional[str] = None,
    message_type: Union[PrintType, SGR, int, str, List[Union[SGR, int, str]], Tuple[Union[SGR, int, str]]] = PrintType.NORMAL,
    gap: bool = False,
    print_time: bool = False,
    message_newline: bool = False,
    indent: int = 0,
    indent_newline: int = 4,
    sgr_all: bool = False,
    print_head: bool = False
) -> str:
    """
    格式化字符串

    :param message: 信息
    :param extra_message: 额外信息，显示在信息之前，如果message_newline为True则额外信息显示在信息的上一行
    :param message_type: 信息的字符串输出类型枚举类
    :param gap: 是否与上方信息间隔一行（输出前额外输出一个换行符）
    :param print_time: 是否打印当前时间
    :param message_newline: message是否另起新一行
    :param indent: 缩进空格数
    :param indent_newline: 只在message_newline为True时生效，为message新起一行的相较于indent的“额外”缩进空格数
    :param sgr_all: 是否对全部打印内容进行SGR转义，如果为False将跳过时间和额外信息
    :param print_head: 是否在信息前打印message_type的名称
    """
    ctime = ctime_str()
    final_msg = ""

    message = str(message)

    # 间隔
    if gap:
        final_msg += "\n"
    # 初始缩进
    final_msg += f"{' ' * indent}"
    # 当前时间
    if print_time:
        final_msg += f"{ctime} "
    # 额外信息
    if extra_message is not None:
        final_msg += f"{extra_message} "

    # 信息新起一行
    if message_newline:
        msg_indent = indent + indent_newline
        final_msg = final_msg.rstrip(" ")
        final_msg += f"\n{' ' * msg_indent}"
    else:
        msg_indent = indent

    msg = ""
    # 类型头
    if isinstance(message_type, PrintType) and message_type != PrintType.NORMAL and print_head:
        msg_head, msg_sgr = message_type.value
        msg += f"[{msg_head}] "
    # 信息缩进
    for char in message:
        if char == "\n":
            msg += f"\n{' ' * msg_indent}"
        else:
            msg += char

    # SGR转义
    # 全部转义的情况
    if sgr_all:
        final_msg += msg
        if isinstance(message_type, PrintType):
            if message_type != PrintType.NORMAL:
                msg_head, msg_sgr = message_type.value
                final_msg = sgr_format(final_msg, msg_sgr)
        else:
            final_msg = sgr_format(final_msg, message_type)
    # 跳过时间和额外信息的情况
    else:
        if isinstance(message_type, PrintType):
            if message_type != PrintType.NORMAL:
                msg_head, msg_sgr = message_type.value
                msg = sgr_format(msg, msg_sgr)
        else:
            msg = sgr_format(msg, message_type)
        final_msg += msg

    return final_msg


def cp(
    message: str,
    extra_message: Optional[str] = None,
    message_type: Union[PrintType, SGR, int, str, List[Union[SGR, int, str]], Tuple[Union[SGR, int, str]]] = PrintType.NORMAL,
    gap: bool = False,
    indent: int = 0,
    print_time: bool = False,
    message_newline: bool = False,
    indent_newline: int = 4,
    sgr_all: bool = False,
    print_head: bool = False,
    sleep: int = 0
) -> None:
    """
    向控制台打印一条信息 (Console Print)

    :param message: 信息
    :param extra_message: 额外信息，显示在信息之前，如果message_newline为True则额外信息显示在信息的上一行
    :param message_type: 信息的字符串输出类型枚举类
    :param gap: 是否与上方信息间隔一行（输出前额外输出一个换行符）
    :param indent: 缩进空格数
    :param print_time: 是否打印当前时间
    :param message_newline: message是否另起新一行
    :param indent_newline: 只在message_newline为True时生效，为message新起一行的相较于indent的“额外”缩进空格数
    :param sgr_all: 是否对全部打印内容进行SGR转义，如果为False将跳过时间和额外信息
    :param print_head: 是否在信息前打印message_type的名称
    :param sleep: 打印完信息后程序暂停时长（同步），单位为秒
    """
    final_msg = print_format(
        message,
        extra_message=extra_message,
        message_type=message_type,
        gap=gap,
        indent=indent,
        print_time=print_time,
        message_newline=message_newline,
        indent_newline=indent_newline,
        sgr_all=sgr_all,
        print_head=print_head,
    )
    # 打印输出
    print(final_msg)
    # 暂停
    if sleep != 0:
        time.sleep(sleep)


def ci(
    prompt: str,
    prompt_type: Union[PrintType, SGR, int, str, List[Union[SGR, int, str]], Tuple[Union[SGR, int, str]]] = PrintType.NORMAL,
    gap: bool = False,
    indent: int = 0,
    print_head: bool = True,
    prompt_end: str = "：",
    input_type: Type[Union[int, float, str]] = Type[str],
    password: bool = False,
    verify_password: bool = False,
    verify_prompt: str = "请再输入一次",
) -> Optional[Union[str, int, float]]:
    """
    从标准输入读取字符串 (Console Input)
    按下Ctrl+C可以取消操作

    :param prompt: 输入提示
    :param prompt_type: 字符串输出类型枚举类
    :param gap: 是否与上方信息间隔一行（输出前额外输出一个换行符）
    :param indent: 缩进空格数
    :param print_head: 是否打印信息类型头
    :param prompt_end: 输入提示的结尾，用于提示用户在这里输入
    :param input_type: 要求用户输入的类型，如果为str则直接输出，如果为int或者float则会尝试类型转换，如果无法转换则会要求重新输入
    :param password: 是否是密码
    :param verify_password: 是否要再次输入密码并核验两次密码是否一致
    :param verify_prompt: 再次输入密码时的提示
    :return: 读取的字符串
    :raise UserCancelledError: 当用户按下Ctrl+C取消输入时引发
    """
    final_prompt = ""
    final_verify_prompt = ""

    # 间隔
    if gap:
        final_prompt += "\n"
    # 初始缩进
    final_prompt += f"{' ' * indent}"
    if verify_password:
        final_verify_prompt += f"{' ' * indent}"
    # 类型头
    if isinstance(prompt_type, PrintType) and prompt_type != PrintType.NORMAL and print_head:
        prompt_head, prompt_sgr = prompt_type.value
        final_prompt += f"[{prompt_head}] "
    # 缩进
    for char in prompt:
        if char == "\n":
            final_prompt += f"\n{' ' * indent}"
        else:
            final_prompt += char
    if verify_password:
        for char in verify_prompt:
            if char == "\n":
                final_verify_prompt += f"\n{' ' * indent}"
            else:
                final_verify_prompt += char
    # 添加输入提示结尾
    final_prompt += prompt_end
    final_verify_prompt += prompt_end
    # SGR转义
    if isinstance(prompt_type, PrintType):
        if prompt_type != PrintType.NORMAL:
            prompt_head, prompt_sgr = prompt_type.value
            final_prompt = sgr_format(final_prompt, prompt_sgr)
            if verify_password:
                final_verify_prompt = sgr_format(final_verify_prompt, prompt_sgr)
    else:
        final_prompt = sgr_format(final_prompt, prompt_type)
        if verify_password:
            final_verify_prompt = sgr_format(final_verify_prompt, prompt_type)

    while True:
        try:
            # 正常输入
            if not password:
                input_line = input(final_prompt)
            # 密码类型
            else:
                while True:
                    input_line = getpass.getpass(final_prompt)
                    if verify_password:
                        input_verify = getpass.getpass(final_verify_prompt)
                        if input_line != input_verify:
                            cp("两次输入不一致，请重试", message_type=PrintType.ERROR, sleep=2)
                        else:
                            break
                    else:
                        break

            # 类型检测
            if input_type is int:
                try:
                    input_line = int(input_line)
                except ValueError:
                    cp("请输入一个整数", message_type=PrintType.ERROR, sleep=2)
                    continue
            elif input_type is float:
                try:
                    input_line = float(input_line)
                except ValueError:
                    cp("请输入一个数", message_type=PrintType.ERROR, sleep=2)
                    continue

        # 用户取消
        except KeyboardInterrupt:
            raise errors.UserCancelled()
        except EOFError:
            raise errors.UserCancelled()
        # 返回结果
        else:
            return input_line

    return None


def ci_bool(
    prompt: str,
    prompt_type: Union[PrintType, SGR, int, str, List[Union[SGR, int, str]], Tuple[Union[SGR, int, str]]] = PrintType.NORMAL,
    gap: bool = False,
    indent: int = 0,
    print_head: bool = True,
    prompt_end: str = ": ",
) -> bool:
    """
    让用户输入Yes或者No

    :param prompt: 输入提示
    :param prompt_type: 字符串输出类型枚举类
    :param gap: 是否与上方信息间隔一行（输出前额外输出一个换行符）
    :param indent: 缩进空格数
    :param print_head: 是否打印信息类型头
    :param prompt_end: 输入提示的结尾，用于提示用户在这里输入
    :return: 输入Yes返回True，输入No返回False
    :raise UserCancelledError: 当用户按下Ctrl+C取消输入时引发
    """
    while True:
        input_line = ci(prompt, prompt_type=prompt_type, gap=gap, indent=indent, print_head=print_head, prompt_end=prompt_end)
        input_line = input_line.lower()
        if input_line == "yes" or input_line == "y" or input_line == "true":
            return True
        if input_line == "no" or input_line == "n" or input_line == "false":
            return False
        else:
            cp("请输入yes或者no", message_type=PrintType.ERROR, sleep=2)


def ci_select(
    prompt: str,
    options: Set[str],
    ignore_case: bool = True,
    prompt_type: Union[PrintType, SGR, int, str, List[Union[SGR, int, str]], Tuple[Union[SGR, int, str]]] = PrintType.NORMAL,
    gap: bool = False,
    indent: int = 0,
    print_head: bool = True,
    prompt_end: str = ": ",
) -> str:
    """
    让用户输入一个选项
    为确保选型唯一，选项列表为一个只包含字符串的集合

    :param prompt: 输入提示
    :param options: 可以选择的选项
    :param ignore_case: 是否忽略选项的大小写
    :param prompt_type: 字符串输出类型枚举类
    :param gap: 是否与上方信息间隔一行（输出前额外输出一个换行符）
    :param indent: 缩进空格数
    :param print_head: 是否打印信息类型头
    :param prompt_end: 输入提示的结尾，用于提示用户在这里输入
    :return: 用户选择的选项（字符串）
    :raise UserCancelledError: 当用户按下Ctrl+C取消输入时引发
    """
    # 格式化选项
    options_formated = set()
    for item in options:
        item = str(item)
        if ignore_case:
            item = item.lower()
        options_formated.add(item)
    while True:
        input_line = ci(prompt, prompt_type=prompt_type, gap=gap, indent=indent, print_head=print_head, prompt_end=prompt_end)
        if ignore_case:
            input_line = input_line.lower()
        if input_line not in options_formated:
            cp(f"不存在选项：{input_line}", message_type=PrintType.ERROR, sleep=2)
        else:
            return input_line


def cmenu(
    title: str,
    message: str,
    options: List[Tuple[str, str]],
    none_option: str = "0",
    none_option_prompt: str = "返回",
    input_prompt: str = "请输入选项",
    ignore_case: bool = True,
    gap: bool = False,
    title_indent: int = 0,
    message_indent: int = 0,
    option_indent: int = 2,
    input_prompt_end: str = ": ",
) -> Optional[str]:
    """
    向控制台打印菜单并请求输入选项（Console Menu）

    :param title: 菜单的标题
    :param message: 菜单的信息
    :param options: 菜单的选项，一个列表，其中每个元素为一个元组，元组第一个元素为选项，第二个元素为选项描述
    :param none_option: 返回None的选项，通常作为返回或者退出用的选项
    :param none_option_prompt: 返回None的选项的提示
    :param input_prompt: 输入时的提示
    :param ignore_case: 是否忽略选项的大小写
    :param gap: 是否与上方信息间隔一行（输出前额外输出一个换行符）
    :param title_indent: 标题缩进空格数
    :param message_indent: 信息缩进空格数
    :param option_indent: 选项缩进空格数
    :param input_prompt_end: 输入提示的结尾，用于提示用户在这里输入
    :return: 用户选择的选项（字符串）
    :raise UserCancelledError: 当用户按下Ctrl+C取消输入时引发
    """
    option_set = {option[0] for option in options}
    if none_option in option_set:
        raise ValueError(f"None选项{none_option}与Options中的选项重复，请单独设置None选项")

    menu_str = ""
    # 间隔
    if gap:
        menu_str += "\n"
    # 标题缩进
    menu_str += f"{' ' * title_indent}"
    # 标题
    menu_str += sgr_format(title, PrintType.TITLE.value[1]) + "\n"
    # 菜单信息
    menu_str += f"{' ' * message_indent}"
    for char in message:
        if char == "\n":
            menu_str += f"\n{' ' * message_indent}"
        else:
            menu_str += char
    menu_str += "\n"
    # 选项列表
    for option in options:
        option_str = sgr_format(f"[{option[0]}]", PrintType.OPTION.value[1])
        option_description = option[1]
        menu_str += f"{' ' * option_indent}{option_str} {option_description}\n"
    # None选项
    none_option_str = sgr_format(f"[{none_option}]", PrintType.OPTION.value[1])
    menu_str += f"{' ' * option_indent}{none_option_str} {none_option_prompt}\n"
    option_set.add(none_option)

    print(menu_str)
    result = ci_select(input_prompt, option_set, ignore_case=ignore_case, prompt_end=input_prompt_end)
    if result == none_option:
        return None
    return result


def time_split(time_str: str) -> list:

    time_str_list = time_str.split(":")
    for i in range(3):
        time_str_list.append("00")

    time_list = []
    for i in range(3):
        time_list.append(int(time_str_list[i]))

    for i in range(2, -1, -1):
        if i != 0 and time_list[i] > 60:
            time_list[i - 1] += time_list[i] // 60
            time_list[i] = time_list[i] % 60

    return time_list


def convert_duration_to_str(duration: int) -> str:
    """
    将获取的秒数转换为普通时间格式字符串

    :param duration: 时长秒数
    :return:
    """

    if duration is None:
        return f"00:00:00"

    if not isinstance(duration, int):
        try:
            duration = int(duration)
        except ValueError:
            return f"00:00:00"

    if duration <= 0:
        return f"00:00:00"

    total_min = duration // 60
    hour = total_min // 60
    minutes = total_min % 60
    seconds = duration % 60

    if 0 < hour < 10:
        hour = f"0{hour}"

    if minutes == 0:
        minutes = "00"
    elif minutes < 10:
        minutes = f"0{minutes}"

    if seconds == 0:
        seconds = "00"
    elif seconds < 10:
        seconds = f"0{seconds}"

    if hour == 0:
        return f"{minutes}:{seconds}"

    return f"{hour}:{minutes}:{seconds}"


def convert_str_to_duration(input_str: str) -> int:
    """
    将引号分开的时间格式字符串转换为秒数

    :param input_str: 输入的时间字符串
    :return:
    """
    if ":" in input_str:
        num_list = input_str.split(":")
    elif "：" in input_str:
        num_list = input_str.split("：")
    else:
        return 0

    if len(num_list) < 1 or len(num_list) > 3:
        return 0

    try:
        if len(num_list) == 2:
            return int(num_list[0]) * 60 + int(num_list[1])
        elif len(num_list) == 3:
            return int(num_list[0]) * 3600 + int(num_list[1]) * 60 + int(num_list[2])
        else:
            return int(num_list[0])
    except ValueError:
        return 0


def convert_byte(byte: int) -> Tuple[float, str]:
    kib = byte / 1024
    mib = kib / 1024
    gib = mib / 1024

    if gib >= 1.0:
        return round(gib, 2), "GiB"
    elif mib >= 1.0:
        return round(mib, 2), "MiB"
    elif kib >= 1.0:
        return round(kib, 2), "KiB"
    else:
        return byte, "字节"


def check_url_source(url) -> Union[str, None]:

    if re.search("bilibili\.com", url) is not None:
        return "bilibili_url"

    elif re.search("b23\.tv", url) is not None:
        return "bilibili_short_url"

    elif re.search("BV(\d|[a-zA-Z]){10}", url) is not None:
        return "bilibili_bvid"

    elif re.search("youtube\.com", url) is not None:
        return "youtube_url"

    elif re.search("youtu\.be", url) is not None:
        return "youtube_short_url"

    elif re.search("music.163\.com", url) is not None:
        return "netease_url"

    elif re.search("163cn\.tv", url) is not None:
        return "netease_short_url"

    else:
        return None


def get_url_from_str(input_str, url_type) -> Union[str, None]:

    if url_type == "bilibili_url":
        url_position = re.search("bilibili\.com[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    elif url_type == "bilibili_short_url":
        url_position = re.search("b23\.tv[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    elif url_type == "bilibili_bvid":
        bvid_position = re.search("BV(\d|[a-zA-Z]){10}", input_str).span()
        bvid = input_str[bvid_position[0]:bvid_position[1]]
        return bvid

    elif url_type == "youtube_url":
        url_position = re.search("youtube\.com[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    elif url_type == "youtube_short_url":
        url_position = re.search("youtu\.be[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    elif url_type == "netease_url":
        url_position = re.search("music.163\.com[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    elif url_type == "netease_short_url":
        url_position = re.search("163cn\.tv[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    else:
        return None


def get_legal_netease_url(input_str) -> Union[str, None]:
    if "song?id=" in input_str:
        id_position = re.search("song\?id=\d+", input_str).span()
    elif "playlist?id=" in input_str:
        id_position = re.search("playlist\?id=\d+", input_str).span()
    else:
        return None
    return "https://music.163.com/#/" + input_str[id_position[0]:id_position[1]]


def get_redirect_url(url) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0",
    }

    # 请求网页
    response = requests.get(url, headers=headers)

    # print(response.status_code)  # 打印响应的状态码
    # print(response.url)  # 打印重定向后的网址

    # 返回重定向后的网址
    return str(response.url)


def get_bvid_from_url(url):
    """
    提取目标地址对应的BV号

    :param url: 目标地址
    :return:
    """
    re_result = re.search("BV(\d|[a-zA-Z]){10}", url)

    if re_result is None:
        return None

    bvid_start = re_result.span()[0]
    bvid_end = re_result.span()[1]
    result = url[bvid_start:bvid_end]

    return result


def make_playlist_page(
        info_list: list, num_per_page: int, starts_with: dict, ends_with: dict, fill_lines=False) -> list:
    """
    将<info_list>中的信息分割成每<num_per_page>一页
    <info_list>需为一个列表，每个元素是一个元组，元组包含两个元素，第一个将直接显示，第二个将在中括号内显示（如元组只包含一个元素则不显示括号）
    <starts_with>为一个字典，保存了每行开头添加的字符串，键为行数（从0开始），值为要添加的字符串
    键None保存添加到每一行前的字符串，如某行前不想添加字符则将对应行号键的值设为一个空字符串，如不添加任何字符串则向<starts_with>传入空字典{}
    <ends_with>为一个字典，保存了每行结尾添加的字符串，键为行数（从0开始），值为要添加的字符串
    键None保存添加到每一行后的字符串，如某行后不想添加字符则将对应行号键的值设为一个空字符串，如不添加任何字符串则向<starts_with>传入空字典{}
    如果<fill_lines>为True，则将最后一页用空行填齐
    """
    result = []
    counter = 0
    while counter < len(info_list):
        current_page = ""
        for i in range(num_per_page):
            if counter >= len(info_list):
                break
            current_tuple = info_list[counter]

            # 从字典<starts_with>中查找此行是否存在
            if counter in starts_with:
                current_starts_with = starts_with[counter]
            elif None in starts_with:
                current_starts_with = starts_with[None]
            else:
                current_starts_with = ""
            # 从字典<ends_with>中查找此行是否存在
            if counter in ends_with:
                current_ends_with = ends_with[counter]
            elif None in ends_with:
                current_ends_with = ends_with[None]
            else:
                current_ends_with = ""

            if len(current_tuple) <= 1:
                current_page += \
                    f"{current_starts_with}[{counter + 1}] {current_tuple[0]}{current_ends_with}\n"
            else:
                current_page += \
                    f"{current_starts_with}[{counter + 1}] {current_tuple[0]} [{current_tuple[1]}]{current_ends_with}\n"
            counter += 1
        result.append(current_page)

    if fill_lines:
        while counter % num_per_page != 0:
            result[-1] += "\n"
            counter += 1

    return result


class DoubleLinkedNode:
    """
    有自定义键值的双向连接节点
    """
    def __init__(self, item=None, key=None):
        self.key = key
        self.item = item
        self.prev: Union[DoubleLinkedNode, None] = None
        self.next: Union[DoubleLinkedNode, None] = None

    def __str__(self):
        return self.item.__str__()

    def __iter__(self):
        return self


class DoubleLinkedListDict:
    """
    双向链表，包含一个使用节点的键值进行快速检索的字典
    每个节点的键值是唯一的（注意：本类不保存对象本身与键值之间的关系，检索某一对象时需外部提供键值）
    """
    def __init__(self):
        self._head: Union[DoubleLinkedNode, None] = None
        self._tail: Union[DoubleLinkedNode, None] = None
        self._length = 0
        self._node_dict: dict[Any, DoubleLinkedNode] = {}

    def __len__(self):
        return self._length

    def __contains__(self, item):
        return item in self._node_dict

    def __str__(self):
        result = []
        current = self._head
        counter = 0
        while counter != self._length:
            result.append(current.item)
            current = current.next
            counter += 1
        return str(result)

    def __iter__(self):
        self.next = self._head
        return self

    def __next__(self):
        current = self.next
        if current is None:
            raise StopIteration
        self.next = current.next
        return current.item

    def is_empty(self) -> bool:
        """
        返回当前双向链表的长度是否为零
        """
        if self._length == 0:
            return True
        else:
            return False

    def key_get(self, key) -> Any:
        """
        返回<key>键值对应的对象

        :param key: 用于检索对象的键值
        :return: 对应的对象
        """
        if key in self._node_dict:
            result = self._node_dict[key].item
            return result
        else:
            raise KeyError(key)

    def index_get(self, index: int) -> Any:
        """
        使用遍历搜索返回<index>索引值对应的对象

        :param index: 用于检索对象的索引值
        :return: 对应的对象
        """
        if index < 0 or index >= self._length:
            raise IndexError
        else:
            result = self._index_get_node(index).item
            return result

    def key_pop(self, key) -> Any:
        """
        返回<key>键值对应的对象，并删除双向链表中对应的对象

        :param key: 用于检索对象的键值
        :return: 对应的对象
        """
        if key in self._node_dict:
            result = self._node_dict[key].item
            self.key_remove(key)
            return result
        else:
            raise KeyError(key)

    def index_pop(self, index: int) -> Any:
        """
        使用遍历搜索返回<index>索引值对应的对象，并删除双向链表中对应的对象

        :param index: 用于检索对象的索引值
        :return: 对应的对象
        """
        if index < 0 or index >= self._length:
            raise IndexError
        else:
            result_node = self._index_get_node(index)
            result = result_node.item
            target_key = result_node.key
            self.key_remove(target_key)
            return result

    def add(self, item, key, force=False) -> None:
        """
        将一个对象添加到双向链表的开头

        :param item: 添加到双向链表的对象
        :param key: 用于检索对象的键值（注意：检索时需外部提供键值）
        :param force: 如果键值已存在，<force>为True则清除掉原有节点后添加当前节点，默认为False
        """
        new_node = DoubleLinkedNode(item, key)
        self._add_node(new_node, force)

    def append(self, item, key, force=False) -> None:
        """
        将一个对象添加到双向链表的尾部

        :param item: 添加到双向链表的对象
        :param key: 用于检索对象的键值（注意：检索时需外部提供键值）
        :param force: 如果键值已存在，<force>为True则清除掉原有节点后添加当前节点，默认为False
        """
        new_node = DoubleLinkedNode(item, key)
        self._append_node(new_node, force)

    def key_insert_before(self, target_key, item, key, force=False) -> None:
        """
        将一个对象插入到键值<target_key>对应对象的前面

        :param target_key: 目标对象的键值
        :param item: 添加到双向链表的对象
        :param key: 用于检索对象的键值（注意：检索时需外部提供键值）
        :param force: 如果键值已存在，<force>为True则清除掉原有节点后添加当前节点，默认为False
        """
        new_node = DoubleLinkedNode(item, key)
        self._key_insert_node_before(target_key, new_node, force)

    def key_insert_after(self, target_key, item, key, force=False) -> None:
        """
        将一个对象插入到键值<target_key>对应对象的后面

        :param target_key: 目标对象的键值
        :param item: 添加到双向链表的对象
        :param key: 用于检索对象的键值（注意：检索时需外部提供键值）
        :param force: 如果键值已存在，<force>为True则清除掉原有节点后添加当前节点，默认为False
        """
        new_node = DoubleLinkedNode(item, key)
        self._key_insert_node_after(target_key, new_node, force)

    def index_insert(self, index, item, key, force=False) -> None:
        """
        将一个对象插入到索引值<index>的位置

        :param index: 目标索引值
        :param item: 添加到双向链表的对象
        :param key: 用于检索对象的键值（注意：检索时需外部提供键值）
        :param force: 如果键值已存在，<force>为True则清除掉原有节点后添加当前节点，默认为False
        """
        new_node = DoubleLinkedNode(item, key)
        self.index_insert(index, new_node, force)

    def key_remove(self, key) -> None:
        """
        将键值<key>对应对象的节点移出双向链表字典

        :param key: 需要移除的对象对应的键值
        """
        if key in self._node_dict:
            current = self._node_dict[key]
            if self._length == 1:
                self._head = None
                self._tail = None
            elif current == self._head:
                self._head.next.prev = None
                self._head = self._head.next
            elif current == self._tail:
                self._tail.prev.next = None
                self._tail = self._tail.prev
            else:
                prev_node = current.prev
                next_node = current.next
                prev_node.next = next_node
                next_node.prev = prev_node

            self._remove_node_dict(key)
            self._length -= 1
        else:
            raise KeyError(key)

    def index_remove(self, index: int) -> None:
        """
        将索引值<index>对应对象的节点移出双向链表字典

        :param index: 需要移除的对象对应的索引值
        """
        if index < 0:
            raise IndexError
        elif index == 0 and self._length == 1:
            self._remove_node_dict(self._head)
            self._head = None
            self._tail = None
        elif index == 0:
            self._remove_node_dict(self._head)
            self._head.next.prev = None
            self._head = self._head.next
        elif index == self._length - 1:
            self._remove_node_dict(self._tail)
            self._tail.prev.next = None
            self._tail = self._tail.prev
        elif index >= self._length:
            raise IndexError
        else:
            current = self._index_get_node(index)
            prev_node = current.prev
            next_node = current.next
            prev_node.next = next_node
            next_node.prev = prev_node
            self._remove_node_dict(current)

        self._length -= 1

    def key_swap(self, key_1, key_2):
        """
        交换两个节点的位置
        
        :param key_1: 需要移除的对象1对应的键值
        :param key_2: 需要移除的对象2对应的键值
        """
        if key_1 not in self._node_dict:
            raise KeyError(key_1)
        if key_2 not in self._node_dict:
            raise KeyError(key_2)

        node_1 = self._node_dict[key_1]
        node_2 = self._node_dict[key_2]
        self._swap_node(node_1, node_2)

    def index_swap(self, index_1, index_2):
        """
        交换两个节点的位置

        :param index_1: 需要移除的对象1对应的索引值
        :param index_2: 需要移除的对象2对应的索引值
        """
        if index_1 < 0 or index_2 < 0 or index_1 >= self._length or index_2 >= self._length:
            raise IndexError

        node_1 = self._index_get_node(index_1)
        node_2 = self._index_get_node(index_2)
        self._swap_node(node_1, node_2)

    def _add_node_dict(self, new_node: DoubleLinkedNode):
        self._node_dict[new_node.key] = new_node

    def _remove_node_dict(self, key):
        if key in self._node_dict:
            del self._node_dict[key]

    def _key_get_node(self, key) -> DoubleLinkedNode:
        if key in self._node_dict:
            return self._node_dict[key]
        else:
            raise KeyError(key)

    def _index_get_node(self, index: int) -> DoubleLinkedNode:
        if index < 0 or index >= self._length:
            raise IndexError
        mid = (self._length - 1) // 2
        if index <= mid:
            current = self._head
            for i in range(index):
                current = current.next
        else:
            current = self._tail
            for i in range(self._length - 1 - index):
                current = current.prev
        return current

    def _add_node(self, new_node: DoubleLinkedNode, force=False):
        if new_node.key in self._node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        if not self.is_empty():
            self._head.prev = new_node
            new_node.next = self._head
        else:
            self._tail = new_node

        new_node.prev = None
        self._head = new_node
        self._add_node_dict(new_node)
        self._length += 1

    def _append_node(self, new_node: DoubleLinkedNode, force=False):
        if new_node.key in self._node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        if not self.is_empty():
            self._tail.next = new_node
            new_node.prev = self._tail
        else:
            self._head = new_node

        new_node.next = None
        self._tail = new_node
        self._add_node_dict(new_node)
        self._length += 1

    def _key_insert_node_before(self, key, new_node: DoubleLinkedNode, force=False):
        if key not in self._node_dict:
            raise KeyError(key)

        if new_node.key in self._node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        target_node = self._node_dict[key]
        if target_node == self._head:
            new_node.prev = None
            self._head = new_node
        else:
            previous_node = target_node.prev
            previous_node.next = new_node
            new_node.prev = previous_node

        target_node.prev = new_node
        new_node.next = target_node

        self._add_node_dict(new_node)
        self._length += 1

    def _key_insert_node_after(self, key, new_node: DoubleLinkedNode, force=False):
        if key not in self._node_dict:
            raise KeyError(key)

        if new_node.key in self._node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        if key in self._node_dict:
            target_node = self._node_dict[key]
            if target_node == self._tail:
                new_node.next = None
                self._tail = new_node
            else:
                next_node = target_node.next
                next_node.prev = new_node
                new_node.next = next_node

            target_node.next = new_node
            new_node.prev = target_node

            self._add_node_dict(new_node)
            self._length += 1

    def _index_insert_node(self, index: int, new_node: DoubleLinkedNode, force=False):
        if new_node.key in self._node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        if index < 0:
            raise IndexError
        elif index == 0:
            self._add_node(new_node)
        elif index == self._length:
            self._append_node(new_node)
        elif index > self._length:
            raise IndexError
        else:
            counter = 0
            current = self._head
            while index != counter:
                current = current.next
                counter += 1
            previous_node = current.prev

            new_node.next = current
            new_node.prev = previous_node
            previous_node.next = new_node
            current.prev = new_node

            self._add_node_dict(new_node)
            self._length += 1

    def _swap_node(self, node_1, node_2):
        """
        交换两个节点的位置

        :param node_1: 需要移除的节点1
        :param node_2: 需要移除的节点2
        """
        if node_1 == node_2:
            return

        # 交换self.head和self.tail
        if node_1 == self._head:
            self._head = node_2
        elif node_2 == self._head:
            self._head = node_1
        if node_1 == self._tail:
            self._tail = node_2
        elif node_2 == self._tail:
            self._tail = node_1

        # 定义node_1和node_2的前后节点
        prev_1 = node_1.prev
        prev_2 = node_2.prev
        next_1 = node_1.next
        next_2 = node_2.next

        # 如果两节点相邻
        # node_1在前的情况
        if next_1 == node_2 or prev_2 == node_1:
            node_1.prev = node_2
            node_1.next = next_2
            node_2.prev = prev_1
            node_2.next = node_1
            if prev_1 is not None:
                prev_1.next = node_2
            if next_2 is not None:
                next_2.prev = node_1

        # node_2在前的情况
        elif prev_1 == node_2 or next_2 == node_1:
            node_1.prev = prev_2
            node_1.next = node_2
            node_2.prev = node_1
            node_2.next = next_1
            if prev_2 is not None:
                prev_2.next = node_1
            if next_1 is not None:
                next_1.prev = node_2

        # 如果两节点不相邻
        else:
            node_1.prev = prev_2
            node_1.next = next_2
            node_2.prev = prev_1
            node_2.next = next_1
            if prev_1 is not None:
                prev_1.next = node_2
            if prev_2 is not None:
                prev_2.next = node_1
            if next_1 is not None:
                next_1.prev = node_2
            if next_2 is not None:
                next_2.prev = node_1

    def encode(self) -> list:
        linked_list = []
        if self._head is not None:
            current = self._head
            while current is not None:
                linked_list.append({"item": current.item, "key": current.key})
                current = current.next
        return linked_list


def double_linked_list_dict_decoder(info_list: list, force=False) -> DoubleLinkedListDict:
    """
    通过读取到的列表重建双向链表字典，但是节点内部的对象仍需单独重建
    可以通过先读取encode返回的列表，将列表中所有对象重建后放入新的列表，将新的列表传入此方法（列表中每个元素为字典，包含键"item"和"key"）
    """
    new_list_dict = DoubleLinkedListDict()
    for item in info_list:
        new_list_dict.append(item["item"], item["key"], force=force)
    return new_list_dict
