import os
import re
import sys
import time

from zeta_bot import utils, errors


class Setting(dict):
    def __init__(self, path: str, config: dict) -> None:
        super().__init__(self)
        self.path = path
        self.name = self.path[self.path.rfind("/") + 1:]
        self.config = config

        try:
            # 检测设置文件是否存在
            if not os.path.exists(self.path):
                self.initialize_setting()
            else:
                self.load()
        except errors.UserCancelled:
            print("您需要完成设置才可正常运行该程序\n再次启动该程序以完成设置\n正在退出")
            time.sleep(3)
            sys.exit()

    def save(self) -> None:
        utils.json_save(self.path, self)

    def load(self) -> None:
        loaded_dict = utils.json_load(self.path)

        # 读取loaded_dict
        for key in loaded_dict:
            self[key] = loaded_dict[key]

        for key in self.config:
            if key in self:
                # 如果选项中的内容有变化
                if self.check_setting_update(key):
                    name = self.config[key]["name"]
                    description = self.config[key]["description"]
                    original_value = loaded_dict[key]["value"]
                    print("\n设置选项的描述发生变动")
                    print("新的描述如下：")
                    print(f"    {name}\n        - {description}\n")
                    print(f"现在的值为：{original_value}")
                    # 同步最新设置信息
                    self[key] = self.config[key]

                    option = utils.input_yes_no("请问是否要修改此设置？（输入yes为是，输入no为否）\n")
                    if option:
                        self.modify_setting(key)
                    self.save()

                # 读取选项
                else:
                    self[key] = self.config[key]
                    self[key]["value"] = loaded_dict[key]["value"]

            # 新增设置选项
            else:
                print("\n发现新增设置")
                self.modify_setting(key)

    def value(self, key: str) -> any:
        return self[key]["value"]

    def list_all(self) -> str:
        result = ""
        for key in self:
            num = str(self[key]["num"])
            num_str = f"[{num}] "
            # 对齐数字
            if len(num) == 1:
                num_str += " "
            result += num_str + self[key]["name"] + "\n"
        return result

    def initialize_setting(self):
        print("开始进行初始设置\n在任意步骤中输入exit以退出设置：")
        for key in self.config:
            try:
                self.modify_setting(key)
            except errors.UserCancelled:
                raise errors.UserCancelled

        print("\n所有设置已保存\n")

    def modify_setting(self, key) -> None:
        """
        修改一项设置，如果<self.__config>中不包含此项设置则直接返回
        """
        if key not in self.config:
            return

        done = False
        # 保存原始值
        if key in self:
            original_value = self[key]["value"]
        else:
            original_value = self.config[key]["value"]
        # 同步最新设置信息
        self[key] = self.config[key]
        name = self[key]["name"]
        require_type = self[key]["type"]
        description = self[key]["description"]
        input_description = self[key]["input_description"]
        regex = self[key]["regex"]

        if self[key]["dependent"] is not None and self[self[key]["dependent"]]["value"] is False:
            done = True

        while not done:
            input_line = input(
                f"\n{name}\n    - {description}\n{input_description}:\n"
            )

            if input_line.lower() == "exit":
                self[key]["value"] = original_value
                raise errors.UserCancelled

            try:
                if regex is not None:
                    input_line = eval(f"{require_type}(\"{input_line}\")")
                    if re.match(regex, input_line) is None:
                        raise ValueError

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

                else:
                    input_line = eval(f"{require_type}(\"{input_line}\")")

            except ValueError:
                print("\n无效输入，请按说明重新输入")
                time.sleep(1)

            else:
                self[key]["value"] = input_line
                done = True

        self.save()

    def check_setting_update(self, key: str) -> bool:
        """
        如果设置中的信息有变化则返回True
        """
        if self[key]["name"] != self.config[key]["name"]:
            return True
        if self[key]["description"] != self.config[key]["description"]:
            return True
        if self[key]["input_description"] != self.config[key]["input_description"]:
            return True
        return False

    def modify_mode(self):
        num_key = {}
        # 将序号与设置名对应
        for key in bot_setting_configs:
            num_key[bot_setting_configs[key]["num"]] = key

        print("---------- 修改设置 ----------")
        while True:
            print(self.list_all())
            print()
            input_line = input(
                "请输入需要修改的设置序号（输入exit以退出设置）：\n")
            if input_line.lower() == "exit":
                break

            try:
                input_line = int(input_line)
                input_line = num_key[input_line]
            except ValueError:
                print("请输入正确的序号（输入exit以退出设置）\n")
                continue
            except KeyError:
                print("请输入正确的序号（输入exit以退出设置）\n")
                continue

            try:
                self.modify_setting(input_line)
            except errors.UserCancelled:
                print()
        print()

    def reset_setting(self):
        self.clear()
        self.initialize_setting()


bot_setting_configs = {
    "token": {
        "num": 1,
        "name": "Discord机器人令牌",
        "type": "str",
        "description": "用于连接到对应Discord账户的认证秘钥，可以从Discord Developer Portal (https://discord.com/developers/applications) → 对应的Application → Bot → Token 处生成",
        "input_description": "请输入Discord机器人令牌",
        "dependent": None,
        "regex": None,
        "value": "None"
    },
    "owner": {
        "num": 2,
        "name": "所有者用户ID",
        "type": "str",
        "description": "本机器人的所有者的纯数字ID，将获得全部权限，纯数字ID可以通过打开Discord开发者模式（位于 用户设置 → 高级设置 → 开发者模式）后，右键用户选择\"复制ID\"获得",
        "input_description": "请输入给予本机器人最高管理权限的Discord用户的用户ID（纯数字ID）",
        "dependent": None,
        "regex": "\d+",
        "value": "000000000000000000"
    },
    "log": {
        "num": 3,
        "name": "系统活动日志",
        "type": "bool",
        "description": "用于记录将各种活动（例如触发指令，添加音频）记录在本地的日志",
        "input_description": "请设置是否开启系统活动日志记录功能（错误日志始终开启）（输入yes为开启，输入no为关闭）",
        "dependent": None,
        "regex": None,
        "value": True
    },
    "audio_library_max_cache": {
        "num": 4,
        "name": "音频库缓存上限",
        "type": "int",
        "description": "允许缓存在本地的音频数量上限，该上限为总上限（无论该机器人加入多少服务器），请根据您部署该机器人的设备的可用本地空间估算，当缓存数量超过该上限时将自动删除最久没有使用的音频",
        "input_description": "请设置服务器允许在本地音频库缓存的音频的数量上限",
        "dependent": None,
        "regex": None,
        "value": "200"
    },
    "guild_past_list_max_cache": {
        "num": 5,
        "name": "历史播放列表上限",
        "type": "int",
        "description": "每个服务器记录历史播放音频的数量上限",
        "input_description": "请设置每个服务器历史播放音频列表记录上限",
        "dependent": None,
        "regex": None,
        "value": "50"
    },
    "bot_name": {
        "num": 6,
        "name": "机器人名称",
        "type": "str",
        "description": "该机器人的名称（当前版本暂无太多作用，机器人在Discord的用户名实际上为您在Discord Developer Portal设置的名称）",
        "input_description": "请设置机器人的名称",
        "dependent": None,
        "regex": None,
        "value": "机器人"
    },
    "default_activity": {
        "num": 7,
        "name": "机器人状态",
        "type": "str",
        "description": "机器人启动后显示在用户栏内机器人用户名下方的状态，显示格式为中文版：\"正在玩 <状态>\" 或英文版：\"Playing <状态>\"",
        "input_description": "请设置机器人启动时的默认状态",
        "dependent": None,
        "regex": None,
        "value": "Nothing"
    },
    "auto_reboot": {
        "num": 8,
        "name": "自动重启",
        "type": "bool",
        "description": "自动重启功能，在不方便管理机器人时确保不会因某些BUG卡死机器人（希望不会发生）",
        "input_description": "请设置是否开启自动重启功能（输入y为开启，输入n为关闭）",
        "dependent": None,
        "regex": None,
        "value": False
    },
    "ar_time": {
        "num": 9,
        "name": "自动重启时间",
        "type": "str",
        "description": "每日自动重启的时间",
        "input_description": "请设置自动重启时间（输入格式为\"小时:分钟:秒\"，示例：04:30:00）",
        "dependent": "auto_reboot",
        "regex": "([01]\d|2[0123]|\d):([012345]\d|\d):([012345]\d|\d)",
        "value": "00:00:00"
    },
    "ar_announcement": {
        "num": 10,
        "name": "自动重启通知",
        "type": "bool",
        "description": "在机器人准备重启时向所有机器人仍处于该服务器任意语音频道的服务器的第一个文字频道发送准备自动重启的通知（好长的句子）",
        "input_description": "请设置是否开启自动重启通知功能（输入y为开启，输入n为关闭）",
        "dependent": "auto_reboot",
        "regex": None,
        "value": False
    },
    "ar_reminder": {
        "num": 11,
        "name": "自动重启前通知",
        "type": "bool",
        "description": "在重启前任意时间提醒机器人将于何时重启，向所有机器人仍处于该服务器任意语音频道的服务器的第一个文字频道发送",
        "input_description": "请设置是否开启在自动重启前通知的功能（输入y为开启，输入n为关闭）",
        "dependent": "auto_reboot",
        "regex": None,
        "value": False
    },
    "ar_reminder_time": {
        "num": 12,
        "name": "自动重启前通知时间",
        "type": "str",
        "description": "每日自动重启前通知的时间",
        "input_description": "请设置自动重启提前通知时间（输入格式为\"小时:分钟:秒\"，示例：04:25:00）",
        "dependent": "ar_reminder",
        "regex": "([01]\d|2[0123]|\d):([012345]\d|\d):([012345]\d|\d)",
        "value": "23:55:00"
    },
}
