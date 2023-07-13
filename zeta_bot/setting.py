import os
import re
import sys
import time

from zeta_bot import (
    errors,
    log,
    language,
    utils
)

# 多语言模块
lang = language.Lang()
_ = lang.get_string
printl = lang.printl


class Setting:
    def __init__(self, path: str, config: dict, required=False) -> None:
        self._path = path
        self._setting = {}
        self._config = config

        # 加载配置
        self._name = self._config[0]["config_name"]
        self._version = self._config[0]["version"]
        self._setting["config_name"] = self._name
        self._setting["version"] = self._version
        for i in range(1, len(self._config)):
            self._setting[self._config[i]["id"]] = self._config[i]["value"]

        try:
            # 检测设置文件是否存在
            if not os.path.exists(self._path):
                self.initialize_setting()
            else:
                self.load()
        except KeyError:
            print("设置文件已损坏")
            self.initialize_setting()
        except errors.JSONFileError:
            print("设置文件已损坏")
            self.initialize_setting()
        except errors.UserCancelled:
            if required:
                print("您需要完成设置才可正常运行该程序\n再次启动该程序以完成设置\n正在退出")
                time.sleep(3)
                sys.exit()

    def save(self) -> None:
        utils.json_save(self._path, self._setting)

    def load(self):
        """
        读取self.path的文件，并将其中的设置选项加入到self.setting中
        """
        loaded_dict = utils.json_load(self._path)

        # 读取loaded_dict
        loaded_name = loaded_dict["config_name"]
        loaded_version = loaded_dict["version"]
        for key in self._setting:
            if key in loaded_dict:
                self._setting[key] = loaded_dict[key]
            else:
                print("发现新增设置")
                try:
                    self.change_setting(self.find_index(key))
                except errors.UserCancelled:
                    raise errors.UserCancelled

        if loaded_version != self._version:
            print("版本变更导致以前已有的设置内容可能发生变动，请问您是否要重新检查所有的设置选项？")
            input_line = input("（输入yes为是，输入skip为暂时跳过，输入no为否且下次不再提醒）\n")
            input_option = input_line.lower()
            if input_option == "true" or input_option == "yes" or \
                    input_option == "y":
                self._setting["version"] = self._version
                self.save()
                self.modify_mode()
            elif input_option == "false" or input_option == "no" or \
                    input_option == "n":
                self._setting["version"] = self._version
                self.save()
            elif input_option == "skip":
                pass
            else:
                print("请输入yes，skip或者no")

    def value(self, key: str) -> any:
        return self._setting[key]

    def list_all(self) -> str:
        result = self._name + "\n"
        for i in range(1, len(self._config)):
            num_str = f"[{i}] "
            # 对齐数字
            if i < 10:
                num_str += " "
            result += num_str + self._config[i]["name"] + "\n"
        return result

    def initialize_setting(self):
        print(f"开始进行{self._name}的初始设置\n在任意步骤中输入exit以退出设置：")
        print(self._name)
        for i in range(1, len(self._config)):
            try:
                self.change_setting(i)
            except errors.UserCancelled:
                raise errors.UserCancelled

        print("\n所有设置已保存\n")

    def find_index(self, key) -> int:
        for i in range(1, len(self._config)):
            if key == self._config[i]["id"]:
                return i
        return -1

    def change_setting(self, index) -> None:
        """
        修改一项设置，如果<self.__config>中不包含此项设置则直接返回
        """
        if index < 1 or index > len(self._config) - 1:
            return

        done = False
        # 保存原始值
        original_value = self._setting[self._config[index]["id"]]

        # 检查依赖项
        if self._config[index]["dependent"] is not None and self._setting[self._config[index]["dependent"]] is False:
            done = True

        name = self._config[index]["name"]
        description = self._config[index]["description"]
        input_description = self._config[index]["input_description"]
        regex = self._config[index]["regex"]
        require_type = self._config[index]["type"]
        options = self._config[index]["options"]
        while not done:
            input_line = input(
                f"\n{name}\n    - {description}\n{input_description}:\n"
            )

            if input_line.lower() == "exit":
                self._setting[self._config[index]["id"]] = original_value
                raise errors.UserCancelled

            try:
                # 正则表达式检测
                if regex is not None:
                    input_line = eval(f"{require_type}(\"{input_line}\")")
                    re_result = re.match(regex, input_line)
                    if re_result is None:
                        raise ValueError
                    else:
                        start, end = re_result.span()
                        input_line = input_line[start:end]

                # 布尔值检测
                if require_type == "bool":
                    input_option = input_line.lower()
                    if input_option == "true" or input_option == "yes" or \
                            input_option == "y":
                        input_line = True
                    elif input_option == "false" or input_option == "no" or \
                            input_option == "n":
                        input_line = False
                    else:
                        raise ValueError

                elif input_line == "\\":
                    pass

                # 类型转换
                else:
                    input_line = eval(f"{require_type}(\"{input_line}\")")

                # 选项检测
                if options is not None:
                    if input_line not in options:
                        raise ValueError

            except ValueError:
                print("\n无效输入，请按说明重新输入")
                time.sleep(1)

            else:
                self._setting[self._config[index]["id"]] = input_line
                done = True

        self.save()

    def modify_mode(self):
        print("---------- 修改设置 ----------")
        while True:
            print(self.list_all())
            input_line = input(
                "请输入需要修改的设置序号（输入exit以退出设置）：\n")
            if input_line.lower() == "exit":
                break

            try:
                input_line = int(input_line)
            except ValueError:
                print("请输入正确的序号（输入exit以退出设置）\n")
                continue
            except KeyError:
                print("请输入正确的序号（输入exit以退出设置）\n")
                continue
            if input_line < 1 or input_line > len(self._config):
                print("请输入正确的序号（输入exit以退出设置）\n")
                continue

            try:
                self.change_setting(input_line)
            except errors.UserCancelled:
                print()
        print()

    def change_settings_list(self, keys: list) -> None:
        for i in range(1, len(self._config)):
            if self._config[i]["id"] in keys:
                try:
                    self.change_setting(i)
                except errors.UserCancelled:
                    continue

    def reset_setting(self):
        self._setting.clear()
        self.initialize_setting()


language_setting_configs = [
    {
        "config_name": "系统语言设定",
        "version": "0.10.0"
    },
    {
        "id": "language",
        "name": "系统语言设定",
        "type": "str",
        "description": f"请选择系统的语言：\n{language.list_lang_code(indent=6)}",
        "input_description": "请输入语言代码（示例：zh_cn）",
        "dependent": None,
        "regex": None,
        "options": language.get_lang_code_list(),
        "value": "None"
    },
]

bot_setting_configs = [
    {
        "config_name": "系统设定",
        "version": "0.10.0"
    },
    {
        "id": "token",
        "name": "Discord机器人令牌",
        "type": "str",
        "description": "用于连接到对应Discord账户的认证秘钥，可以从Discord Developer Portal (https://discord.com/developers/applications) → 对应的Application → Bot → Token 处生成",
        "input_description": "请输入Discord机器人令牌",
        "dependent": None,
        "regex": None,
        "options": None,
        "value": "None"
    },
    {
        "id": "owner",
        "name": "所有者用户ID",
        "type": "str",
        "description": "本机器人的所有者（最高管理员）的纯数字ID，将获得全部权限，纯数字ID可以通过打开Discord开发者模式（位于 用户设置 → 高级设置 → 开发者模式）后，右键用户选择\"复制ID\"获得",
        "input_description": "请输入给予本机器人最高管理权限的Discord用户的用户ID（纯数字ID）",
        "dependent": None,
        "regex": "\d+",
        "options": None,
        "value": "000000000000000000"
    },
    {
        "id": "log",
        "name": "系统活动日志",
        "type": "bool",
        "description": "用于记录将各种活动（例如触发指令，添加音频）记录在本地的日志",
        "input_description": "请设置是否开启系统活动日志记录功能（错误日志始终开启）（输入yes为开启，输入no为关闭）",
        "dependent": None,
        "regex": None,
        "options": None,
        "value": True
    },
    {
        "id": "audio_library_storage_size",
        "name": "音频库缓存上限",
        "type": "int",
        "description": "允许缓存在本地的音频数量上限，该上限为总上限（无论该机器人加入多少服务器），请根据您部署该机器人的设备的可用本地空间估算，当缓存数量超过该上限时将自动删除最久没有使用的音频",
        "input_description": "请设置服务器允许在本地音频库缓存的音频的数量上限",
        "dependent": None,
        "regex": None,
        "options": None,
        "value": "200"
    },
    {
        "id": "guild_past_list_size",
        "name": "历史播放列表上限",
        "type": "int",
        "description": "每个服务器记录历史播放音频的数量上限",
        "input_description": "请设置每个服务器历史播放音频列表记录上限",
        "dependent": None,
        "regex": None,
        "options": None,
        "value": "50"
    },
    {
        "id": "bot_name",
        "name": "机器人名称",
        "type": "str",
        "description": "该机器人的名称（当前版本暂无太多作用，机器人在Discord的用户名实际上为您在Discord Developer Portal设置的名称）",
        "input_description": "请设置机器人的名称",
        "dependent": None,
        "regex": None,
        "options": None,
        "value": "机器人"
    },
    {
        "id": "default_activity",
        "name": "机器人状态",
        "type": "str",
        "description": "机器人启动后显示在用户栏内机器人用户名下方的状态，显示格式为中文版：\"正在玩 <状态>\" 或英文版：\"Playing <状态>\"",
        "input_description": "请设置机器人启动时的默认状态",
        "dependent": None,
        "regex": None,
        "options": None,
        "value": "Nothing"
    },
    {
        "id": "auto_reboot",
        "name": "自动重启",
        "type": "bool",
        "description": "自动重启功能，在不方便管理机器人时确保不会因某些BUG卡死机器人（希望不会发生）",
        "input_description": "请设置是否开启自动重启功能（输入y为开启，输入n为关闭）",
        "dependent": None,
        "regex": None,
        "options": None,
        "value": False
    },
    {
        "id": "ar_time",
        "name": "自动重启时间",
        "type": "str",
        "description": "每日自动重启的时间",
        "input_description": "请设置自动重启时间（输入格式为\"小时:分钟:秒\"，示例：04:30:00）",
        "dependent": "auto_reboot",
        "regex": "([01]\d|2[0123]|\d):([012345]\d|\d):([012345]\d|\d)",
        "options": None,
        "value": "00:00:00"
    },
    {
        "id": "ar_announcement",
        "name": "自动重启通知",
        "type": "bool",
        "description": "在机器人准备重启时向所有机器人仍处于该服务器任意语音频道的服务器的第一个文字频道发送准备自动重启的通知（好长的句子）",
        "input_description": "请设置是否开启自动重启通知功能（输入y为开启，输入n为关闭）",
        "dependent": "auto_reboot",
        "regex": None,
        "options": None,
        "value": False
    },
    {
        "id": "ar_reminder",
        "name": "自动重启前通知",
        "type": "bool",
        "description": "在重启前任意时间提醒机器人将于何时重启，向所有机器人仍处于该服务器任意语音频道的服务器的第一个文字频道发送",
        "input_description": "请设置是否开启在自动重启前通知的功能（输入y为开启，输入n为关闭）",
        "dependent": "auto_reboot",
        "regex": None,
        "options": None,
        "value": False
    },
    {
        "id": "ar_reminder_time",
        "name": "自动重启前通知时间",
        "type": "str",
        "description": "每日自动重启前通知的时间",
        "input_description": "请设置自动重启提前通知时间（输入格式为\"小时:分钟:秒\"，示例：04:25:00）",
        "dependent": "ar_reminder",
        "regex": "([01]\d|2[0123]|\d):([012345]\d|\d):([012345]\d|\d)",
        "options": None,
        "value": "23:55:00"
    },
]
