import datetime


def time() -> str:
    """
    :return: 当前时间的字符串（格式为：年-月-日 时:分:秒）
    """
    return str(datetime.datetime.now())[:19]


def path_formatting(string: str) -> str:
    result = ""
    for char in string:
        if char == "\\":
            result += "/"
        else:
            result += char

    return result
