import re
import os
import requests


def convert_duration_to_time(duration):
    """
    将获取的秒数转换为正常时间格式

    :param duration: 时长秒数
    :return:
    """

    if int(duration) <= 0:
        return "-1"

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


def check_url_source(url):
    if re.match("BV(\d|[a-zA-Z]){10}", url) is not None:
        return "bili_bvid"

    elif re.search("bilibili.com", url) is not None:
        return "bili_url"

    elif re.search("b23.tv", url) is not None:
        return "bili_short_url"

    elif re.search("youtube.com", url) is not None:
        return "ytb_url"

    else:
        return "else"


def find_by_appear_times(in_str, target, times):
    """
    返回第times次target出现在in_str中的位置
    """
    counter = 0
    start = 0
    while counter != times:
        target_index = in_str.find(target, start)
        if target_index == -1:
            return -1
        else:
            counter += 1
            start = target_index + len(target)
    start -= len(target)
    return start


def make_menu_list_line(menu, line_num):
    """
    检测输入的字符串menu，每经过line_num行时，分割字符串并加入列表
    返回一个每页行数为line_num的选项列表
    """
    menu_list = []
    start = 0
    while not len(menu[start:]) == 0:
        index = find_by_appear_times(menu, "\n", line_num)
        if index == -1:
            menu_list.append(menu)
            return menu_list
        menu_list.append(menu[:index + 1])
        menu = menu[index + 1:]

    return menu_list


def make_menu_list_10(menu):
    """
    检测输入的字符串menu，每出现第“[10]”或10的倍数的选项时，分割字符串并加入列表
    返回一个每个元素为10的倍数的选项的列表
    """
    menu_list = []
    i = 1
    start = 0
    while not len(menu[start:]) == 0:
        ten_index = menu.find(f"[{i * 10}]")
        n_index = menu.find("\n", ten_index)
        menu_list.append(menu[start:n_index + 1])
        start = n_index + 1
        i += 1
    return menu_list


def clear_downloads():
    for folder, sub_folder, files in os.walk('./downloads/'):
        for file in files:
            os.remove(f"./downloads/{file}")


def clear_logs():
    for folder, sub_folder, files in os.walk('./logs/'):
        for file in files:
            if not (file == "bugs.txt" or file == "reported.txt"):
                os.remove(f"./downloads/{file}")


def get_redirect_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bilibili.com/"
    }

    # 请求网页
    response = requests.get(url, headers=headers)

    # print(response.status_code)  # 打印响应的状态码
    # print(response.url)  # 打印重定向后的网址

    # 返回重定向后的网址
    return response.url
