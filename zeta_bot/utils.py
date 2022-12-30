import datetime
import json


def time() -> str:
    """
    :return: 当前时间的字符串（格式为：年-月-日 时:分:秒）
    """
    return str(datetime.datetime.now())[:19]


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


def json_save(json_path: str, save_dict: dict) -> None:
    """
    将<save_dict>以json格式保存到<json_path>
    """
    with open(json_path, "w", encoding="utf-8") as file:
        file.write(json.dumps(save_dict, default=lambda x: x.encode(),
                              sort_keys=False, indent=4))


def json_load(json_path: str) -> dict:
    """
    读取<json_path>的json文件
    """
    with open(json_path, "r", encoding="utf-8") as file:
        loaded_dict = json.loads(file.read())
    return loaded_dict


def input_yes_no(description: str) -> bool:
    while True:
        input_line = input(description)
        input_option = input_line.lower()
        if input_option == "true" or input_option == "yes" or \
                input_option == "y":
            return True
        elif input_option == "false" or input_option == "no" or \
                input_option == "n":
            return False
        else:
            print("请输入yes或者no")