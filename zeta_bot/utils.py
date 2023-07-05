import datetime
import os
import json
import re
import requests
from typing import Union

from zeta_bot import (
    errors
)


def time() -> str:
    """
    :return: 当前时间的字符串（格式为：年-月-日 时:分:秒）
    """
    return str(datetime.datetime.now())[:19]


def create_folder(path: str):
    """
    检测在指定目录是否存在文件夹，如果不存在则创建
    """
    if not os.path.exists(path):
        name = path[path.rfind("/") + 1:]
        os.mkdir(path)
        print(f"创建{name}文件夹")


def json_save(json_path: str, saving_item) -> None:
    """
    将<saving_item>以json格式保存到<json_path>
    """
    with open(json_path, "w", encoding="utf-8") as file:
        file.write(json.dumps(saving_item, default=lambda x: x.encode(),
                              sort_keys=False, indent=4))


def json_load(json_path: str) -> dict:
    """
    读取<json_path>的json文件
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


def convert_duration_to_time_str(duration: int) -> str:
    """
    将获取的秒数转换为普通时间格式字符串

    :param duration: 时长秒数
    :return:
    """

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


def check_url_source(url) -> Union[str, None]:

    if re.search("bilibili\.com", url) is not None:
        return "bili_url"

    elif re.search("b23\.tv", url) is not None:
        return "bili_short_url"

    elif re.search("BV(\d|[a-zA-Z]){10}", url) is not None:
        return "bili_bvid"

    elif re.search("youtube\.com", url) is not None:
        return "ytb_url"

    else:
        return None


def get_url_from_str(input_str, url_type) -> Union[str, None]:

    if url_type == "bili_url":
        url_position = re.search("bilibili\.com[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    elif url_type == "bili_short_url":
        url_position = re.search("b23\.tv[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    elif url_type == "bili_bvid":
        bvid_position = re.search("BV(\d|[a-zA-Z]){10}", input_str).span()
        bvid = input_str[bvid_position[0]:bvid_position[1]]
        return bvid

    elif url_type == "ytb_url":
        url_position = re.search("youtube\.com[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    else:
        return None


def get_redirect_url(url) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bilibili.com/"
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


def make_playlist_page(list_info: list, num_per_page: int, indent: int = 0) -> list:
    """
    将<list_info>中的信息分割成每<num_per_page>一页
    <indent>为每行字符串前缩进位数
    """
    result = []
    counter = 0
    while counter < len(list_info):
        current_page = ""
        for i in range(num_per_page):
            current_tuple = list_info[counter]
            current_page += f"{' ' * indent}[{counter + 1}] {current_tuple[0]} [{current_tuple[1]}]\n"
            counter += 1
        result.append(current_page)
    return result
