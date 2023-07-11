import datetime
import os
import json
import re
import requests
from typing import Any, Union

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


def json_load(json_path: str) -> Union[dict, list]:
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


class DoubleLinkedListDict:
    """
    双向链表，包含一个使用节点的键值进行快速检索的字典
    每个节点的键值是唯一的（注意：本类不保存对象本身与键值之间的关系，检索某一对象时需外部提供键值）
    """
    def __init__(self):
        self.head: Union[DoubleLinkedNode, None] = None
        self.tail: Union[DoubleLinkedNode, None] = None
        self.length = 0
        self.node_dict: dict[Any, DoubleLinkedNode] = {}

    def __len__(self):
        return self.length

    def __contains__(self, item):
        return item in self.node_dict

    def __str__(self):
        result = []
        current = self.head
        counter = 0
        while counter != self.length:
            result.append(current.item)
            current = current.next
            counter += 1
        return str(result)

    def is_empty(self) -> bool:
        """
        返回当前双向链表的长度是否为零
        """
        if self.length == 0:
            return True
        else:
            return False

    def key_get(self, key) -> Any:
        """
        返回<key>键值对应的对象

        :param key: 用于检索对象的键值
        :return: 对应的对象
        """
        if key in self.node_dict:
            result = self.node_dict[key].item
            return result
        else:
            raise errors.KeyNotFound(key)

    def index_get(self, index: int) -> Any:
        """
        使用遍历搜索返回<index>索引值对应的对象

        :param index: 用于检索对象的索引值
        :return: 对应的对象
        """
        if index < 0 or index >= self.length:
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
        if key in self.node_dict:
            result = self.node_dict[key].item
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
        if index < 0 or index >= self.length:
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
        if key in self.node_dict:
            current = self.node_dict[key]
            if self.length == 1:
                self.head = None
                self.tail = None
            elif current == self.head:
                self.head.next.prev = None
                self.head = self.head.next
            elif current == self.tail:
                self.tail.prev.next = None
                self.tail = self.tail.prev
            else:
                prev_node = current.prev
                next_node = current.next
                prev_node.next = next_node
                next_node.prev = prev_node

            self._remove_node_dict(key)
            self.length -= 1
        else:
            raise errors.KeyNotFound(key)

    def index_remove(self, index: int) -> None:
        """
        将索引值<index>对应对象的节点移出双向链表字典

        :param index: 需要移除的对象对应的索引值
        """
        if index < 0:
            raise IndexError
        elif index == 0 and self.length == 1:
            self._remove_node_dict(self.head)
            self.head = None
            self.tail = None
        elif index == 0:
            self._remove_node_dict(self.head)
            self.head.next.prev = None
            self.head = self.head.next
        elif index == self.length - 1:
            self._remove_node_dict(self.tail)
            self.tail.prev.next = None
            self.tail = self.tail.prev
        elif index >= self.length:
            raise IndexError
        else:
            current = self._index_get_node(index)
            prev_node = current.prev
            next_node = current.next
            prev_node.next = next_node
            next_node.prev = prev_node
            self._remove_node_dict(current)

        self.length -= 1

    def key_swap(self, key_1, key_2):
        """
        交换两个节点的位置
        
        :param key_1: 需要移除的对象1对应的键值
        :param key_2: 需要移除的对象2对应的键值
        """
        if key_1 not in self.node_dict:
            raise errors.KeyNotFound(key_1)
        if key_2 not in self.node_dict:
            raise errors.KeyNotFound(key_2)

        node_1 = self.node_dict[key_1]
        node_2 = self.node_dict[key_2]
        self._swap_node(node_1, node_2)

    def index_swap(self, index_1, index_2):
        """
        交换两个节点的位置

        :param index_1: 需要移除的对象1对应的索引值
        :param index_2: 需要移除的对象2对应的索引值
        """
        if index_1 < 0 or index_2 < 0 or index_1 >= self.length or index_2 >= self.length:
            raise IndexError

        node_1 = self._index_get_node(index_1)
        node_2 = self._index_get_node(index_2)
        self._swap_node(node_1, node_2)

    def _add_node_dict(self, new_node: DoubleLinkedNode):
        self.node_dict[new_node.key] = new_node

    def _remove_node_dict(self, key):
        if key in self.node_dict:
            del self.node_dict[key]

    def _key_get_node(self, key) -> DoubleLinkedNode:
        if key in self.node_dict:
            return self.node_dict[key]

    def _index_get_node(self, index: int) -> DoubleLinkedNode:
        if index < 0 or index >= self.length:
            raise IndexError
        mid = (self.length - 1) // 2
        if index <= mid:
            current = self.head
            for i in range(index):
                current = current.next
        else:
            current = self.tail
            for i in range(self.length-1 - index):
                current = current.prev
        return current

    def _add_node(self, new_node: DoubleLinkedNode, force=False):
        if new_node.key in self.node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        if not self.is_empty():
            self.head.prev = new_node
            new_node.next = self.head
        else:
            self.tail = new_node

        new_node.prev = None
        self.head = new_node
        self._add_node_dict(new_node)
        self.length += 1

    def _append_node(self, new_node: DoubleLinkedNode, force=False):
        if new_node.key in self.node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        if not self.is_empty():
            self.tail.next = new_node
            new_node.prev = self.tail
        else:
            self.head = new_node

        new_node.next = None
        self.tail = new_node
        self._add_node_dict(new_node)
        self.length += 1

    def _key_insert_node_before(self, key, new_node: DoubleLinkedNode, force=False):
        if key not in self.node_dict:
            raise errors.KeyNotFound(key)

        if new_node.key in self.node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        target_node = self.node_dict[key]
        if target_node == self.head:
            new_node.prev = None
            self.head = new_node
        else:
            previous_node = target_node.prev
            previous_node.next = new_node
            new_node.prev = previous_node

        target_node.prev = new_node
        new_node.next = target_node

        self._add_node_dict(new_node)
        self.length += 1

    def _key_insert_node_after(self, key, new_node: DoubleLinkedNode, force=False):
        if key not in self.node_dict:
            raise errors.KeyNotFound(key)

        if new_node.key in self.node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        if key in self.node_dict:
            target_node = self.node_dict[key]
            if target_node == self.tail:
                new_node.next = None
                self.tail = new_node
            else:
                next_node = target_node.next
                next_node.prev = new_node
                new_node.next = next_node

            target_node.next = new_node
            new_node.prev = target_node

            self._add_node_dict(new_node)
            self.length += 1

    def _index_insert_node(self, index: int, new_node: DoubleLinkedNode, force=False):
        if new_node.key in self.node_dict:
            if force:
                self.key_remove(new_node.key)
            else:
                raise errors.KeyAlreadyExists(new_node.key)

        if index < 0:
            raise IndexError
        elif index == 0:
            self._add_node(new_node)
        elif index == self.length:
            self._append_node(new_node)
        elif index > self.length:
            raise IndexError
        else:
            counter = 0
            current = self.head
            while index != counter:
                current = current.next
                counter += 1
            previous_node = current.prev

            new_node.next = current
            new_node.prev = previous_node
            previous_node.next = new_node
            current.prev = new_node

            self._add_node_dict(new_node)
            self.length += 1

    def _swap_node(self, node_1, node_2):
        """
        交换两个节点的位置

        :param node_1: 需要移除的节点1
        :param node_2: 需要移除的节点2
        """
        if node_1 == node_2:
            return

        # 交换self.head和self.tail
        if node_1 == self.head:
            self.head = node_2
        elif node_2 == self.head:
            self.head = node_1
        if node_1 == self.tail:
            self.tail = node_2
        elif node_2 == self.tail:
            self.tail = node_1

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
        if self.head is not None:
            current = self.head
            while current is not None:
                linked_list.append({"item": current.item, "key": current.key})
                current = current.next
        return linked_list


def double_linked_list_dict_decoder(info_list: list) -> DoubleLinkedListDict:
    """
    通过读取到的列表重建双向链表字典，但是节点内部的对象仍需单独重建
    """
    new_list_dict = DoubleLinkedListDict()
    for item in info_list:
        new_list_dict.append(item["item"], item["key"])
    return new_list_dict
