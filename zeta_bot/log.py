import utils
import traceback
import logging
from errors import *


class Log:
    def __init__(self, error_log_path: str, log_path: str, log: bool) -> None:
        self.__log = log
        self.__log_path = log_path
        self.__error_log_path = error_log_path
        logging.basicConfig(filename=self.__error_log_path, level=logging.WARNING)

    def record(self, ctx, content) -> None:
        record_and_print(self.__log_path, ctx, utils.time(), content)

    def on_error(self, exception) -> None:
        error(self.__error_log_path, exception)

    def on_application_command_error(self, ctx, exception) -> None:
        application_command_error(
            self.__log_path, self.__error_log_path, ctx, exception)


def record(path: str, time: str, content: str) -> None:
    """
    向运行日志写入时间与信息

    :param path: 日志路径
    :param time: 要记录的时间
    :param content: 要写入的信息
    :return:
    """
    with open(path, "a", encoding="utf-8") as log:
        log.write(f"{time} {content}\n")


def record_and_print(path: str, ctx, time: str, content: str) -> None:
    """
    在控制台打印一条信息，并记录在运行日志中

    :param path: 日志路径
    :param ctx: ctx
    :param time: 要记录的时间
    :param content: 要写入的信息
    :return:
    """
    print(time + f" {ctx.guild}\n    {content}\n")
    record(path, time, f"[{ctx.guild}] {content}")


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
    print(current_time + f"\n    \033[0;31m发生错误：{exception}\n    "
                         f"详情请查看错误日志：根目录{error_log_path[1:]}\033[0m\n"
          )
    # 系统活动日志写入错误信息
    record(error_log_path, current_time,
           f"发生错误：{exception}，详情请查看错误日志：根目录{error_log_path[1:]}"
           )


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
    print(current_time + f" {ctx.guild}\n    \033[0;31m发生错误：{exception}\n    "
                         f"详情请查看错误日志：根目录{error_log_path[1:]}\033[0m\n"
          )
    # 系统活动日志写入错误信息
    record(log_path, current_time, f"[{ctx.guild}] 发生错误：{exception}，"
                                   f"详情请查看错误日志：根目录{error_log_path[1:]}"
           )

    # 向用户回复发生错误
    try:
        await ctx.respond("发生错误")
    # 如果回复失败
    except errors.NotFound as exception:
        exception_formatted = traceback.format_exception(
            type(exception), exception, exception.__traceback__
        )
        full_exception = ""
        for line in exception_formatted:
            full_exception += line
        message = f"on_application_command_error内部发生错误"
        logger = logging.getLogger()
        logger.error(f"{current_time}\n{message}\n{full_exception}")
        # 控制台输出错误信息
        print(current_time + f" {ctx.guild}\n    \033[0;31m发生错误：{exception}\n"
                             f"    详情请查看错误日志：根目录{error_log_path[1:]}\033[0m\n"
              )
        # 系统活动日志写入错误信息
        record(log_path, current_time, f"[{ctx.guild}] 无法回复互动，发生错误：{exception}")
