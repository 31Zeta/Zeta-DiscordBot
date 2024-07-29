import datetime
import os
import json
import re
import requests
from typing import Any, Union, Tuple

from zeta_bot import (
    errors,
    language
)

# 多语言模块
lang = language.Lang()
_ = lang.get_string
printl = lang.printl


def time() -> str:
    """
    :return: 当前时间的字符串（格式为：年-月-日 时:分:秒）
    """
    return str(datetime.datetime.now())[:19]


def time_datetime() -> datetime.datetime:
    """
    :return: 当前时间的datetime
    """
    return datetime.datetime.now()


def create_folder(path: str) -> None:
    """
    检测在指定目录是否存在文件夹，如果不存在则创建
    """
    if not os.path.exists(path):
        name = path[path.rfind("/") + 1:]
        os.mkdir(path)
        print(f"创建{name}文件夹")


def path_exists(path: str) -> bool:
    """
    检测指定目录或者文件是否存在
    重新包装os.path.exists
    """
    return os.path.exists(path)


def json_save(json_path: str, saving_item) -> None:
    """
    将<saving_item>以json格式保存到<json_path>
    **警告**：json格式的键值必须为字符串，否则会被转换为字符串
    """
    with open(json_path, "w", encoding="utf-8") as file:
        file.write(json.dumps(saving_item, default=lambda x: x.encode(),
                              sort_keys=False, indent=4))


def json_load(json_path: str) -> Union[dict, list]:
    """
    读取<json_path>的json文件
    **警告**：json格式的键值必须为字符串，否则会被转换为字符串
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


def legal_name(name_str: str) -> str:
    """
    将字符串转换为合法的文件名

    :param name_str: 原文件名
    :return: 转换后文件名
    """

    name_str = name_str.replace("\\", "_")
    name_str = name_str.replace("/", "_")
    name_str = name_str.replace(":", "_")
    name_str = name_str.replace("*", "_")
    name_str = name_str.replace("?", "_")
    name_str = name_str.replace("\"", "_")
    name_str = name_str.replace("<", "_")
    name_str = name_str.replace(">", "_")
    name_str = name_str.replace("|", "_")

    return name_str


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


def convert_duration_to_str(duration: int) -> str:
    """
    将获取的秒数转换为普通时间格式字符串

    :param duration: 时长秒数
    :return:
    """

    if duration is None:
        return f"00:00:00"

    if not isinstance(duration, int):
        try:
            duration = int(duration)
        except ValueError:
            return f"00:00:00"

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


def convert_str_to_duration(input_str: str) -> int:
    """
    将引号分开的时间格式字符串转换为秒数

    :param input_str: 输入的时间字符串
    :return:
    """
    if ":" in input_str:
        num_list = input_str.split(":")
    elif "：" in input_str:
        num_list = input_str.split("：")
    else:
        return 0

    if len(num_list) < 1 or len(num_list) > 3:
        return 0

    try:
        if len(num_list) == 2:
            return int(num_list[0]) * 60 + int(num_list[1])
        elif len(num_list) == 3:
            return int(num_list[0]) * 3600 + int(num_list[1]) * 60 + int(num_list[2])
    except ValueError:
        return 0


def convert_byte(byte: int) -> Tuple[float, str]:
    kb = byte / 1024
    mb = kb / 1024
    gb = mb / 1024

    if gb >= 1.0:
        return round(gb, 2), "GB"
    elif mb >= 1.0:
        return round(mb, 2), "MB"
    elif kb >= 1.0:
        return round(kb, 2), "KB"
    else:
        return byte, "字节"


def check_url_source(url) -> Union[str, None]:

    if re.search("bilibili\.com", url) is not None:
        return "bilibili_url"

    elif re.search("b23\.tv", url) is not None:
        return "bilibili_short_url"

    elif re.search("BV(\d|[a-zA-Z]){10}", url) is not None:
        return "bilibili_bvid"

    elif re.search("youtube\.com", url) is not None:
        return "youtube_url"

    elif re.search("youtu\.be", url) is not None:
        return "youtube_short_url"

    elif re.search("music.163\.com", url) is not None:
        return "netease_url"

    elif re.search("163cn\.tv", url) is not None:
        return "netease_short_url"

    else:
        return None


def get_url_from_str(input_str, url_type) -> Union[str, None]:

    if url_type == "bilibili_url":
        url_position = re.search("bilibili\.com[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    elif url_type == "bilibili_short_url":
        url_position = re.search("b23\.tv[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    elif url_type == "bilibili_bvid":
        bvid_position = re.search("BV(\d|[a-zA-Z]){10}", input_str).span()
        bvid = input_str[bvid_position[0]:bvid_position[1]]
        return bvid

    elif url_type == "youtube_url":
        url_position = re.search("youtube\.com[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    elif url_type == "youtube_short_url":
        url_position = re.search("youtu\.be[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    elif url_type == "netease_url":
        url_position = re.search("music.163\.com[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    elif url_type == "netease_short_url":
        url_position = re.search("163cn\.tv[^ ]*", input_str).span()
        url = "https://" + input_str[url_position[0]:url_position[1]]
        return url

    else:
        return None


def get_legal_netease_url(input_str) -> Union[str, None]:
    if "song?id=" in input_str:
        id_position = re.search("song\?id=\d+", input_str).span()
    elif "playlist?id=" in input_str:
        id_position = re.search("playlist\?id=\d+", input_str).span()
    else:
        return None
    return "https://music.163.com/#/" + input_str[id_position[0]:id_position[1]]


def get_redirect_url(url) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0",
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


def make_playlist_page(
        info_list: list, num_per_page: int, starts_with: dict, ends_with: dict, fill_lines=False) -> list:
    """
    将<info_list>中的信息分割成每<num_per_page>一页
    <info_list>需为一个列表，每个元素是一个元组，元组包含两个元素，第一个将直接显示，第二个将在中括号内显示（如元组只包含一个元素则不显示括号）
    <starts_with>为一个字典，保存了每行开头添加的字符串，键为行数（从0开始），值为要添加的字符串
    键None保存添加到每一行前的字符串，如某行前不想添加字符则将对应行号键的值设为一个空字符串，如不添加任何字符串则向<starts_with>传入空字典{}
    <ends_with>为一个字典，保存了每行结尾添加的字符串，键为行数（从0开始），值为要添加的字符串
    键None保存添加到每一行后的字符串，如某行后不想添加字符则将对应行号键的值设为一个空字符串，如不添加任何字符串则向<starts_with>传入空字典{}
    如果<fill_lines>为True，则将最后一页用空行填齐
    """
    result = []
    counter = 0
    while counter < len(info_list):
        current_page = ""
        for i in range(num_per_page):
            if counter >= len(info_list):
                break
            current_tuple = info_list[counter]

            # 从字典<starts_with>中查找此行是否存在
            if counter in starts_with:
                current_starts_with = starts_with[counter]
            elif None in starts_with:
                current_starts_with = starts_with[None]
            else:
                current_starts_with = ""
            # 从字典<ends_with>中查找此行是否存在
            if counter in ends_with:
                current_ends_with = ends_with[counter]
            elif None in ends_with:
                current_ends_with = ends_with[None]
            else:
                current_ends_with = ""

            if len(current_tuple) <= 1:
                current_page += \
                    f"{current_starts_with}[{counter + 1}] {current_tuple[0]}{current_ends_with}\n"
            else:
                current_page += \
                    f"{current_starts_with}[{counter + 1}] {current_tuple[0]} [{current_tuple[1]}]{current_ends_with}\n"
            counter += 1
        result.append(current_page)

    if fill_lines:
        while counter % num_per_page != 0:
            result[-1] += "\n"
            counter += 1

    return result


class DoubleLinkedNode:
    """
    有自定义键值的双向连接节点
    """
    def __init__(self, item=None, key=None):
        self.key = key
        self.item = item
        self.prev: Union[DoubleLinkedNode, None] = None
        self.next: Union[DoubleLinkedNode, None] = None

    def __str__(self):
        return self.item.__str__()

    def __iter__(self):
        return self


class DoubleLinkedListDict:
    """
    双向链表，包含一个使用节点的键值进行快速检索的字典
    每个节点的键值是唯一的（注意：本类不保存对象本身与键值之间的关系，检索某一对象时需外部提供键值）
    """
    def __init__(self):
        self._head: Union[DoubleLinkedNode, None] = None
        self._tail: Union[DoubleLinkedNode, None] = None
        self._length = 0
        self._node_dict: dict[Any, DoubleLinkedNode] = {}

    def __len__(self):
        return self._length

    def __contains__(self, item):
        return item in self._node_dict

    def __str__(self):
        result = []
        current = self._head
        counter = 0
        while counter != self._length:
            result.append(current.item)
            current = current.next
            counter += 1
        return str(result)

    def __iter__(self):
        self.next = self._head
        return self

    def __next__(self):
        current = self.next
        if current is None:
            raise StopIteration
        self.next = current.next
        return current.item

    def is_empty(self) -> bool:
        """
        返回当前双向链表的长度是否为零
        """
        if self._length == 0:
            return True
        else:
            return False

    def key_get(self, key) -> Any:
        """
        返回<key>键值对应的对象

        :param key: 用于检索对象的键值
        :return: 对应的对象
        """
        if key in self._node_dict:
            result = self._node_dict[key].item
            return result
        else:
            raise errors.KeyNotFound(key)

    def index_get(self, index: int) -> Any:
        """
        使用遍历搜索返回<index>索引值对应的对象

        :param index: 用于检索对象的索引值
        :return: 对应的对象
        """
        if index < 0 or index >= self._length:
            raise IndexError
        else:
            result = self._index_get_node(index).item
            return result

    def key_pop(self, key) -> Any:
        """
        返回<key>键值对应的对象，并删除双向链表中对应的对象

        :param key: 用于检索对象的键值
        :return: 对应的对象
        """
        if key in self._node_dict:
            result = self._node_dict[key].item
            self.key_remove(key)
            return result
        else:
            raise errors.KeyNotFound(key)

    def index_pop(self, index: int) -> Any:
        """
        使用遍历搜索返回<index>索引值对应的对象，并删除双向链表中对应的对象

        :param index: 用于检索对象的索引值
        :return: 对应的对象
        """
        if index < 0 or index >= self._length:
            raise IndexError
        else:
            result_node = self._index_get_node(index)
            result = result_node.item
            target_key = result_node.key
            self.key_remove(target_key)
            return result

    def add(self, item, key, force=False) -> None:
        """
        将一个对象添加到双向链表的开头

        :param item: 添加到双向链表的对象
        :param key: 用于检索对象的键值（注意：检索时需外部提供键值）
        :param force: 如果键值已存在，<force>为True则清除掉原有节点后添加当前节点，默认为False
        """
        new_node = DoubleLinkedNode(item, key)
        self._add_node(new_node, force)

    def append(self, item, key, force=False) -> None:
        """
        将一个对象添加到双向链表的尾部

        :param item: 添加到双向链表的对象
        :param key: 用于检索对象的键值（注意：检索时需外部提供键值）
        :param force: 如果键值已存在，<force>为True则清除掉原有节点后添加当前节点，默认为False
        """
        new_node = DoubleLinkedNode(item, key)
        self._append_node(new_node, force)

    def key_insert_before(self, target_key, item, key, force=False) -> None:
        """
        将一个对象插入到键值<target_key>对应对象的前面

        :param target_key: 目标对象的键值
        :param item: 添加到双向链表的对象
        :param key: 用于检索对象的键值（注意：检索时需外部提供键值）
        :param force: 如果键值已存在，<force>为True则清除掉原有节点后添加当前节点，默认为False
        """
        new_node = DoubleLinkedNode(item, key)
        self._key_insert_node_before(target_key, new_node, force)

    def key_insert_after(self, target_key, item, key, force=False) -> None:
        """
        将一个对象插入到键值<target_key>对应对象的后面

        :param target_key: 目标对象的键值
        :param item: 添加到双向链表的对象
        :param key: 用于检索对象的键值（注意：检索时需外部提供键值）
        :param force: 如果键值已存在，<force>为True则清除掉原有节点后添加当前节点，默认为False
        """
        new_node = DoubleLinkedNode(item, key)
        self._key_insert_node_after(target_key, new_node, force)

    def index_insert(self, index, item, key, force=False) -> None:
        """
        将一个对象插入到索引值<index>的位置

        :param index: 目标索引值
        :param item: 添加到双向链表的对象
        :param key: 用于检索对象的键值（注意：检索时需外部提供键值）
        :param force: 如果键值已存在，<force>为True则清除掉原有节点后添加当前节点，默认为False
        """
        new_node = DoubleLinkedNode(item, key)
        self.index_insert(index, new_node, force)

    def key_remove(self, key) -> None:
        """
        将键值<key>对应对象的节点移出双向链表字典

        :param key: 需要移除的对象对应的键值
        """
        if key in self._node_dict:
            current = self._node_dict[key]
            if self._length == 1:
                self._head = None
                self._tail = None
            elif current == self._head:
                self._head.next.prev = None
                self._head = self._head.next
            elif current == self._tail:
                self._tail.prev.next = None
                self._tail = self._tail.prev
            else:
                prev_node = current.prev
                next_node = current.next
                prev_node.next = next_node
                next_node.prev = prev_node

            self._remove_node_dict(key)
            self._length -= 1
        else:
            raise errors.KeyNotFound(key)

    def index_remove(self, index: int) -> None:
        """
        将索引值<index>对应对象的节点移出双向链表字典

        :param index: 需要移除的对象对应的索引值
        """
        if index < 0:
            raise IndexError
        elif index == 0 and self._length == 1:
            self._remove_node_dict(self._head)
            self._head = None
            self._tail = None
        elif index == 0:
            self._remove_node_dict(self._head)
            self._head.next.prev = None
            self._head = self._head.next
        elif index == self._length - 1:
            self._remove_node_dict(self._tail)
            self._tail.prev.next = None
            self._tail = self._tail.prev
        elif index >= self._length:
            raise IndexError
        else:
            current = self._index_get_node(index)
            prev_node = current.prev
            next_node = current.next
            prev_node.next = next_node
            next_node.prev = prev_node
            self._remove_node_dict(current)

        self._length -= 1

    def key_swap(self, key_1, key_2):
        """
        交换两个节点的位置
        
        :param key_1: 需要移除的对象1对应的键值
        :param key_2: 需要移除的对象2对应的键值
        """
        if key_1 not in self._node_dict:
            raise errors.KeyNotFound(key_1)
        if key_2 not in self._node_dict:
            raise errors.KeyNotFound(key_2)

        node_1 = self._node_dict[key_1]
        node_2 = self._node_dict[key_2]
        self._swap_node(node_1, node_2)

    def index_swap(self, index_1, index_2):
        """
        交换两个节点的位置

        :param index_1: 需要移除的对象1对应的索引值
        :param index_2: 需要移除的对象2对应的索引值
        """
        if index_1 < 0 or index_2 < 0 or index_1 >= self._length or index_2 >= self._length:
            raise IndexError

        node_1 = self._index_get_node(index_1)
        node_2 = self._index_get_node(index_2)
        self._swap_node(node_1, node_2)

    def _add_node_dict(self, new_node: DoubleLinkedNode):
        self._node_dict[new_node.key] = new_node

    def _remove_node_dict(self, key):
        if key in self._node_dict:
            del self._node_dict[key]

    def _key_get_node(self, key) -> DoubleLinkedNode:
        if key in self._node_dict:
            return self._node_dict[key]

    def _index_get_node(self, index: int) -> DoubleLinkedNode:
        if index < 0 or index >= self._length:
            raise IndexError
        mid = (self._length - 1) // 2
        if index <= mid:
            current = self._head
            for i in range(index):
                current = current.next
        else:
            current = self._tail
            for i in range(self._length - 1 - index):
                current = current.prev
        return current

    def _add_node(self, new_node: DoubleLinkedNode, force=False):
        if new_node.key in self._node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        if not self.is_empty():
            self._head.prev = new_node
            new_node.next = self._head
        else:
            self._tail = new_node

        new_node.prev = None
        self._head = new_node
        self._add_node_dict(new_node)
        self._length += 1

    def _append_node(self, new_node: DoubleLinkedNode, force=False):
        if new_node.key in self._node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        if not self.is_empty():
            self._tail.next = new_node
            new_node.prev = self._tail
        else:
            self._head = new_node

        new_node.next = None
        self._tail = new_node
        self._add_node_dict(new_node)
        self._length += 1

    def _key_insert_node_before(self, key, new_node: DoubleLinkedNode, force=False):
        if key not in self._node_dict:
            raise errors.KeyNotFound(key)

        if new_node.key in self._node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        target_node = self._node_dict[key]
        if target_node == self._head:
            new_node.prev = None
            self._head = new_node
        else:
            previous_node = target_node.prev
            previous_node.next = new_node
            new_node.prev = previous_node

        target_node.prev = new_node
        new_node.next = target_node

        self._add_node_dict(new_node)
        self._length += 1

    def _key_insert_node_after(self, key, new_node: DoubleLinkedNode, force=False):
        if key not in self._node_dict:
            raise errors.KeyNotFound(key)

        if new_node.key in self._node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        if key in self._node_dict:
            target_node = self._node_dict[key]
            if target_node == self._tail:
                new_node.next = None
                self._tail = new_node
            else:
                next_node = target_node.next
                next_node.prev = new_node
                new_node.next = next_node

            target_node.next = new_node
            new_node.prev = target_node

            self._add_node_dict(new_node)
            self._length += 1

    def _index_insert_node(self, index: int, new_node: DoubleLinkedNode, force=False):
        if new_node.key in self._node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        if index < 0:
            raise IndexError
        elif index == 0:
            self._add_node(new_node)
        elif index == self._length:
            self._append_node(new_node)
        elif index > self._length:
            raise IndexError
        else:
            counter = 0
            current = self._head
            while index != counter:
                current = current.next
                counter += 1
            previous_node = current.prev

            new_node.next = current
            new_node.prev = previous_node
            previous_node.next = new_node
            current.prev = new_node

            self._add_node_dict(new_node)
            self._length += 1

    def _swap_node(self, node_1, node_2):
        """
        交换两个节点的位置

        :param node_1: 需要移除的节点1
        :param node_2: 需要移除的节点2
        """
        if node_1 == node_2:
            return

        # 交换self.head和self.tail
        if node_1 == self._head:
            self._head = node_2
        elif node_2 == self._head:
            self._head = node_1
        if node_1 == self._tail:
            self._tail = node_2
        elif node_2 == self._tail:
            self._tail = node_1

        # 定义node_1和node_2的前后节点
        prev_1 = node_1.prev
        prev_2 = node_2.prev
        next_1 = node_1.next
        next_2 = node_2.next

        # 如果两节点相邻
        # node_1在前的情况
        if next_1 == node_2 or prev_2 == node_1:
            node_1.prev = node_2
            node_1.next = next_2
            node_2.prev = prev_1
            node_2.next = node_1
            if prev_1 is not None:
                prev_1.next = node_2
            if next_2 is not None:
                next_2.prev = node_1

        # node_2在前的情况
        elif prev_1 == node_2 or next_2 == node_1:
            node_1.prev = prev_2
            node_1.next = node_2
            node_2.prev = node_1
            node_2.next = next_1
            if prev_2 is not None:
                prev_2.next = node_1
            if next_1 is not None:
                next_1.prev = node_2

        # 如果两节点不相邻
        else:
            node_1.prev = prev_2
            node_1.next = next_2
            node_2.prev = prev_1
            node_2.next = next_1
            if prev_1 is not None:
                prev_1.next = node_2
            if prev_2 is not None:
                prev_2.next = node_1
            if next_1 is not None:
                next_1.prev = node_2
            if next_2 is not None:
                next_2.prev = node_1

    def encode(self) -> list:
        linked_list = []
        if self._head is not None:
            current = self._head
            while current is not None:
                linked_list.append({"item": current.item, "key": current.key})
                current = current.next
        return linked_list


def double_linked_list_dict_decoder(info_list: list, force=False) -> DoubleLinkedListDict:
    """
    通过读取到的列表重建双向链表字典，但是节点内部的对象仍需单独重建
    可以通过先读取encode返回的列表，将列表中所有对象重建后放入新的列表，将新的列表传入此方法（列表中每个元素为字典，包含键"item"和"key"）
    """
    new_list_dict = DoubleLinkedListDict()
    for item in info_list:
        new_list_dict.append(item["item"], item["key"], force=force)
    return new_list_dict
