import traceback
import logging
import os

from zeta_bot import (
    errors,
    decorators,
    language,
    utils
)

# 多语言模块
lang = language.Lang()
_ = lang.get_string
printl = lang.printl


@decorators.Singleton
class Log:
    def __init__(self, error_log_path: str, log_path: str, running_log: bool, header: str = "") -> None:
        self._running_log = running_log
        self._log_path = log_path
        self._error_log_path = error_log_path

        with open(self._error_log_path, "a", encoding="utf-8") as log:
            log.write(f"文件生成时间：{utils.time()}\n")
            if header != "":
                log.write(f"{header}\n")

        if self._running_log:
            with open(self._log_path, "a", encoding="utf-8") as log:
                log.write(f"文件生成时间：{utils.time()}\n")
                if header != "":
                    log.write(f"{header}\n")

        if os.path.exists(self._error_log_path):
            self.rp(f"生成初始日志文件：{self._error_log_path}", "[日志记录器]")
        if self._running_log and os.path.exists(self._log_path):
            self.rp(f"生成初始日志文件：{self._log_path}", "[日志记录器]")

        logging.basicConfig(
            filename=self._error_log_path, level=logging.WARNING
        )

    def rec(self, content: str, level="") -> None:
        """
        Record
        记录运行日志
        """
        if self._running_log:
            write_log(self._log_path, utils.time(), content, level)

    def rp(self, content: str, level="", is_error=False):
        """
        Record and print
        记录运行日志，并打印到控制台
        """
        current_time = utils.time()
        print_log(current_time, content, level, is_error)
        if self._running_log:
            write_log(self._log_path, current_time, content, level)

    def on_error(self, exception) -> None:
        error(self._error_log_path, exception)

    def on_application_command_error(self, ctx, exception) -> None:
        application_command_error(self._log_path, self._error_log_path, ctx, exception)


def write_log(path: str, time: str, content: str, level="") -> None:
    """
    向运行日志写入时间与信息

    :param path: 日志路径
    :param time: 要记录的时间
    :param content: 要写入的信息
    :param level: 位置信息
    :return:
    """
    content = content.replace("\n", " ")
    with open(path, "a", encoding="utf-8") as log:
        log.write(f"{time} {level} {content}\n")


def print_log(time: str, content: str, level="", is_error=False) -> None:
    """
    在控制台打印一条包含位置的信息，并记录在运行日志中

    :param time: 要记录的时间
    :param content: 要写入的信息
    :param level: 位置信息
    :param is_error: 此条日志是否是一个报错信息
    :return:
    """
    formatted_content = ""
    for character in content:
        formatted_content += character
        if character == "\n":
            formatted_content += "    "

    if not is_error:
        print(f"{time} {level}\n    {formatted_content}\n")
    else:
        print(f"{time} {level}\n\033[0;31m    {formatted_content}\033[0m\n")


def error(error_log_path, exception) -> None:
    """
    发生程序错误时调用
    """
    current_time = utils.time()
    exception_formatted = traceback.format_exception(
        type(exception), exception, exception.__traceback__
    )
    full_exception = ""
    for line in exception_formatted:
        full_exception += line

    # 错误日志写入错误信息
    message = f"发生错误"
    logger = logging.getLogger()
    logger.error(f"{current_time}\n{message}\n{full_exception}")

    # 控制台输出错误信息
    print_log(current_time, f"\033[0;31m发生错误：{exception}\n    详情请查看错误日志：根目录{error_log_path[1:]}\033[0m\n")
    # 系统活动日志写入错误信息
    write_log(error_log_path, current_time, f"发生错误：{exception}，详情请查看错误日志：根目录{error_log_path[1:]}", "[系统]")


def application_command_error(log_path, error_log_path, ctx, exception) -> None:
    """
    发生程序指令错误时调用
    """

    current_time = utils.time()
    exception_formatted = traceback.format_exception(
        type(exception), exception, exception.__traceback__
    )
    full_exception = ""
    for line in exception_formatted:
        full_exception += line

    # 错误日志写入错误信息
    message = f"用户发送指令：{ctx.command} 造成错误"
    logger = logging.getLogger()
    logger.error(f"{current_time}\n{message}\n{full_exception}")

    # 控制台输出错误信息
    print_log(current_time,
              f"\033[0;31m发生错误：{exception}\n    详情请查看错误日志：根目录{error_log_path[1:]}\033[0m", f"{ctx.guild}")
    # 系统活动日志写入错误信息
    write_log(log_path, current_time, f"发生错误：{exception}，详情请查看错误日志：根目录{error_log_path[1:]}", f"{ctx.guild}")
