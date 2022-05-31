import os
import json
import re
from errors import *


class Setting(dict):
    def __init__(self, path: str, request: dict) -> None:
        super().__init__(self)
        self.path = path
        self.name = self.path[self.path.rfind("/") + 1:]
        self.request = request

        if not os.path.exists(self.path):
            print(f"未找到设置文件{self.name}，开始进行初始设置")
            print("在任意步骤中输入exit以退出设置（退出不会做出任何更改）")
            for key in self.request:
                self[key] = {}
                self[key]["value"] = self.request[key]["default"]
                self[key]["default"] = self.request[key]["default"]
                try:
                    self.modify_setting(key)
                except UserExit:
                    raise UserExit
            print("\n所有设置已保存\n")

        else:
            self.load(silent=False)
            for key in self.request:
                if key not in self:
                    print("检测到新增设置选项")
                    try:
                        self.modify_setting(key)
                    except UserExit:
                        raise UserExit

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as file:
            file.write(json.dumps(self, sort_keys=False, indent=4))

    def load(self, silent=True) -> None:
        with open(self.path, "r", encoding="utf-8") as file:
            loaded_dict = json.loads(file.read())
            for key in loaded_dict:
                self[key] = loaded_dict[key]
        if not silent:
            print(f"配置文件{self.name}读取成功\n")

    def value(self, key: str) -> any:
        return self[key]["value"]

    def list_all(self) -> str:
        result = ""
        max_length_key = max(map(len, self.keys())) + 2
        for key in self:
            result += key.ljust(max_length_key) + str(self[key]["value"]) + "\n"
        return result

    def modify_setting(self, key) -> None:
        done = False
        regex = ""

        if key in self.request:
            description = self.request[key]["description"]
            self[key]["description"] = description
            require_type = self.request[key]["type"]
            self[key]["type"] = require_type
            if "regex" in self.request[key]:
                regex = self.request[key]["regex"]
                self[key]["regex"] = regex
            if "dependent" in self.request[key]:
                self[key]["dependent"] = self.request[key]["dependent"]
                if self[self.request[key]["dependent"]]["value"] is False:
                    done = True

        elif key in self:
            description = self[key]["description"]
            require_type = self[key]["type"]
            if "regex" in self[key]:
                regex = self[key]["regex"]
            if "dependent" in self[key]:
                if self[self[key]["dependent"]]["value"] is False:
                    done = True

        else:
            raise KeyNotFoundError

        while not done:
            input_line = input("\n" + description + ":\n")
            if input_line.lower() == "exit":
                raise UserExit
            try:
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
                print("无效输入，请按说明重新输入")

            else:
                self[key] = {}
                self[key]["value"] = input_line
                self[key]["type"] = require_type
                self[key]["description"] = description
                done = True

        self.save()
