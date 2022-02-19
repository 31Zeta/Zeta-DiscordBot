import re
# from bilibili_dl import bili_get_bvid


def convert_duration_to_time(duration):
    """
    将获取的秒数转换为正常时间格式

    :param duration: 时长秒数
    :return:
    """

    if duration <= 0:
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
        return f"[{minutes}:{seconds}]"

    return f"[{hour}:{minutes}:{seconds}]"


def check_url_source(url):
    if re.match("BV(\d|[a-zA-Z]){10}", url) is not None:
        return "bvid"

    elif re.search("www.bilibili.com", url) is not None:
        return "bvid_url"

    elif re.search("www.youtube.com", url) is not None:
        return "ytb_url"

    else:
        return "else"
