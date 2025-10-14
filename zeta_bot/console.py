from typing import *
import sys
import os
import asyncio
import traceback
import logging

from zeta_bot import (
    errors,
    decorator,
    language,
    utils
)

# 多语言模块
lang = language.Lang()
_ = lang.get_string
printl = lang.printl


async def spinner():
    """
    一个旋转加载图标
    """
    icon_cycle = ["/", "—", "\\", "|"]
    counter = 0
    print("  ", end="", flush=True)
    while True:
        icon = icon_cycle[counter]
        print(f"\b{icon}", end="", flush=True)
        counter += 1
        if counter > 3: counter = 0
        await asyncio.sleep(0.3)


@decorator.Singleton
class Console:
    """
    [单例] 负责统一的控制台输出和日志记录
    """
    def __init__(self, log_directory_path: str, log_name_time: str, running_log: bool, header: str = "") -> None:
        self._running_log = running_log
        self._log_path = f"{log_directory_path}/{log_name_time}.log"
        self._error_log_path = f"{log_directory_path}/{log_name_time}_errors.log"
        self._debug_log_path = f"{log_directory_path}/#DEBUG.log"
        self._current_line = None
        self._spinner_task = None

        with open(self._error_log_path, "a", encoding="UTF-8") as log:
            log.write(f"文件生成时间：{utils.ctime_str()}\n")
            if header != "":
                log.write(f"{header}\n")

        if self._running_log:
            with open(self._log_path, "a", encoding="UTF-8") as log:
                log.write(f"文件生成时间：{utils.ctime_str()}\n")
                if header != "":
                    log.write(f"{header}\n")

        if os.path.exists(self._error_log_path):
            print(f"生成初始日志文件：{self._error_log_path}")
        if self._running_log and os.path.exists(self._log_path):
            print(f"生成初始日志文件：{self._log_path}")

        logging.basicConfig(
            filename=self._error_log_path, level=logging.WARNING
        )

    async def print(self, message: str, end: str = "\n"):
        """
        打印信息，同时维护控制台底部信息和加载图标
        :param message: 要打印的信息
        :param end: 同python库原print方法
        """
        # 先保存状态信息和加载图标状态
        reprint = self._current_line
        spinner_status = self._spinner_task is not None
        # 清除当前状态信息并打印新信息
        await self.current_erase()
        print(message, end=end, flush=True)
        # 如果之前有状态信息则重新打印，有加载图标则重新启动
        if reprint is not None:
            await self.current(reprint, loading=spinner_status)
        elif spinner_status:
            await self.start_loading_spinner()

    async def current(self, message: str, loading: bool = False) -> None:
        """
        打印当前状态信息，始终保持在控制台底部，同时只能存在一条信息，自动删除上一条
        :param message: 要显示的信息
        :param loading: 是否要显示加载符号
        """
        # 删除上一条状态信息
        await self.current_erase()
        self._current_line = message
        print(f"{message}", end="", flush=True)
        if loading:
            await self.start_loading_spinner()

    async def current_erase(self) -> None:
        """
        删除当前状态信息
        """
        if self._spinner_task is not None:
            await self.end_loading_spinner()
        if self._current_line is not None:
            current_len = 0
            for char in self._current_line:
                # 如果是中文字符，则在控制台上占用两个字符位置
                if "\u4e00" <= char <= "\u9fff":
                    current_len += 2
                else:
                    current_len += 1
            print(f"\r{current_len * ' '}\r", end="", flush=True)
        self._current_line = None

    async def start_loading_spinner(self) -> None:
        """
        显示加载图标
        """
        self._spinner_task = asyncio.create_task(spinner())

    async def end_loading_spinner(self) -> None:
        """
        停止加载图标
        """
        if self._spinner_task is not None:
            self._spinner_task.cancel()
            # 结束时删除图标和其自带的一个空格
            print(f"\b\b  \b\b", end="", flush=True)
        self._spinner_task = None

    async def rec(self, content: str, level="") -> None:
        """
        Record
        记录运行日志
        """
        if self._running_log:
            await self.write_log(self._log_path, utils.ctime_str(), content, level)

    async def rp(self, content: str, level="", message_type: utils.PrintType = utils.PrintType.NORMAL, print_head: bool = False) -> None:
        """
        Record and print
        记录运行日志，并打印到控制台
        """
        current_time = utils.ctime_str()
        await self.print_log(content, level, message_type=message_type, print_head=print_head)
        if self._running_log:
            await self.write_log(self._log_path, current_time, content, level)

    async def debug(self, content: str) -> None:
        """
        记录调试信息，并打印到控制台
        """
        current_time = utils.ctime_str()
        await self.print_log(content, level="[DEBUG]", message_type=utils.PrintType.DEBUG, print_head=True)
        if self._running_log:
            await self.debug_log(self._debug_log_path, current_time, content)

    async def console_input(self, prompt: str) -> str:
        """
        让用户输入一行内容

        :param prompt: 输入提示
        :return: 用户输入的字符串
        """
        try:
            await self.current_erase()
            input_line = input(f"{prompt}\n>> ")
        except KeyboardInterrupt:
            await self.print("\n程序退出")
            sys.exit(0)
        except EOFError:
            await self.print("\n程序退出")
            sys.exit(0)
        return input_line

    async def console_input_multiline(self, prompt: str) -> list:
        """
        让用户输入多行内容，每换行一次视为一行，连续两行空白视为结束输入

        :param prompt: 输入提示
        :return: 包含用户每行输入的字符串的列表
        """
        try:
            await self.current_erase()
            last_line_empty = False
            result = []
            print(f"{prompt}\n>> ", end="")
            while True:
                current_line = input()
                if len(current_line) == 0:
                    if last_line_empty:
                        return result
                    else:
                        last_line_empty = True
                else:
                    last_line_empty = False
                    result.append(current_line)
        except KeyboardInterrupt:
            await self.print("\n程序退出")
            sys.exit(0)
        except EOFError:
            await self.print("\n程序退出")
            sys.exit(0)

    async def print_log(
        self,
        content: str,
        level="",
        message_type: utils.PrintType = utils.PrintType.NORMAL,
        gap: bool = True,
        print_time: bool = True,
        message_newline: bool = True,
        indent: int = 0,
        indent_newline: int = 4,
        sgr_all: bool = False,
        print_head: bool = False
    ) -> None:
        """
        在控制台打印一条包含位置的信息，并记录在运行日志中

        :param content: 要写入的信息
        :param level: 位置信息
        :param message_type: 信息的字符串输出类型枚举类
        :param gap: 是否与上方信息间隔一行（输出前额外输出一个换行符）
        :param print_time: 是否打印当前时间
        :param message_newline: message是否另起新一行
        :param indent: 缩进空格数
        :param indent_newline: 只在message_newline为True时生效，为message新起一行的相较于indent的“额外”缩进空格数
        :param sgr_all: 是否对全部打印内容进行SGR转义，如果为False将跳过时间和额外信息
        :param print_head: 是否在信息前打印message_type的名称
        """
        await self.print(
            utils.print_format(
                content,
                extra_message=level,
                message_type=message_type,
                gap=gap,
                print_time=print_time,
                message_newline=message_newline,
                indent=indent,
                indent_newline=indent_newline,
                sgr_all=sgr_all,
                print_head=print_head
            )
        )

    async def write_log(self, path: str, time: str, content: str, level="") -> None:
        """
        向运行日志写入时间与信息

        :param path: 日志路径
        :param time: 要记录的时间
        :param content: 要写入的信息
        :param level: 位置信息
        :return:
        """
        content = content.replace("\n", " ")
        with open(path, "a", encoding="UTF-8") as log:
            log.write(f"{time} {level} {content}\n")

    async def debug_log(self, path: str, time: str, content: str) -> None:
        """
        向运行日志写入时间与调试信息

        :param path: 日志路径
        :param time: 要记录的时间
        :param content: 要写入的信息
        :return:
        """
        content = content.replace("\n", " ")
        with open(path, "a", encoding="UTF-8") as log:
            log.write(f"{time} {content}\n")

    async def on_error(self, exception) -> None:
        """
        发生程序错误时调用
        """
        current_time = utils.ctime_str()
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
        await self.print_log(
            f"{exception}\n详情请查看错误日志：根目录{self._error_log_path[1:]}",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        # 系统活动日志写入错误信息
        await self.write_log(
            self._error_log_path,
            current_time,
            f"发生错误：{exception}，详情请查看错误日志：根目录{self._error_log_path[1:]}",
            "[系统]"
        )

    async def on_application_command_error(self, ctx, exception) -> None:
        """
        发生程序指令错误时调用
        """

        current_time = utils.ctime_str()
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
        await self.print_log(
            f"{exception}\n详情请查看错误日志：根目录{self._error_log_path[1:]}",
            f"{ctx.guild}",
            message_type=utils.PrintType.ERROR,
            print_head=True
        )
        # 系统活动日志写入错误信息
        await self.write_log(
            self._log_path,
            current_time,
            f"发生错误：{exception}，详情请查看错误日志：根目录{self._error_log_path[1:]}",
            f"{ctx.guild}"
        )
