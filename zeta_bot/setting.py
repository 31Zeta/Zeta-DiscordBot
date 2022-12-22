import os
import json
import re
import sys
import time

from errors import *
import utils

# TODO 完善设置，模板保存在本地文件


class Setting(dict):
    def __init__(self, path: str, request: dict) -> None:
        super().__init__(self)
        self.__path = path
        self.name = self.__path[self.__path.rfind("/") + 1:]
        self.request = request

        if not os.path.exists(self.__path):
            try:
                self.initial_setting()
            except errors.UserCancelled:
                print("您需要完成初始设置才可正常运行该程序\n正在退出")
                os.remove(self.__path)
                time.sleep(3)
                sys.exit()

        else:
            try:
                self.load()
                print(f"配置文件{self.name}读取成功")
                for key in self.request:
                    if key not in self or "value" not in self[key]:
                        self[key] = self.request[key]
                        try:
                            self.modify_setting(key, new=True, new_message=True)
                        except errors.UserCancelled:
                            print("您需要完成全部设置才可正常运行该程序\n正在退出")
                            time.sleep(3)
                            sys.exit()

                # 更新设置字典的顺序与内容至最新版本
                temp_dict = {}
                for key in self:
                    temp_dict[key] = self[key]
                self.clear()
                for key in self.request:
                    self[key] = self.request[key]
                    self[key]["value"] = temp_dict[key]["value"]

                self.save()

            except KeyError:
                print("配置文件已损坏，请重新设置")
                self.reset_setting()

    def save(self) -> None:
        with open(self.__path, "w", encoding="utf-8") as file:
            file.write(json.dumps(self, sort_keys=False, indent=4))

    def load(self) -> None:
        with open(self.__path, "r", encoding="utf-8") as file:
            loaded_dict = json.loads(file.read())
            for key in loaded_dict:
                self[key] = loaded_dict[key]

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

    def initial_setting(self):
        print(f"开始进行初始设置")
        print("在任意步骤中输入exit以退出设置（退出不会保存更改）：")
        for key in self.request:
            # self[key] = {}
            # self[key]["value"] = self.request[key]["default"]
            # self[key]["default"] = self.request[key]["default"]

            self[key] = self.request[key]
            self[key]["value"] = self.request[key]["default"]

            try:
                self.modify_setting(key, new=True)
            except errors.UserCancelled:
                raise errors.UserCancelled

        print("\n所有设置已保存\n")

    def modify_setting(self, key, new=False, new_message=False) -> None:
        done = False
        regex = ""
        name = self[key]["name"]
        description = self[key]["description"]
        input_description = self[key]["input_description"]
        require_type = self[key]["type"]
        if "regex" in self[key]:
            regex = self[key]["regex"]
        if "dependent" in self[key] and self[self[key]["dependent"]]["value"] is False:
            done = True
            self[key]["value"] = self[key]["default"]

        while not done:
            if not new:
                input_line = input("\n\n当前值：" + self[key]["value"] + "\n\n" + description + "\n\n" + input_description + ":\n")
            else:
                if new_message:
                    input_line = input("\n\n检测到新增或未完成的设置选项：\n" + name + "\n\n" + description + "\n\n" + input_description + ":\n")
                else:
                    input_line = input("\n\n" + name + "\n\n" + description + "\n\n" + input_description + ":\n")
            if input_line.lower() == "exit":
                raise errors.UserCancelled
            try:
                input_line = legal_str(input_line)

                if regex != "":
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
                time.sleep(2)

            else:
                self[key]["value"] = input_line
                done = True

        self.save()

    def reset_setting(self):
        self.clear()
        self.initial_setting()

