"""
进程内事件总线

机器人各模块通过publish发布状态变化（播放列表变动、播放状态变化、日志等），
Web控制面板通过subscribe获取一个队列，用于向浏览器实时推送（SSE），避免轮询。
所有方法均需在机器人的事件循环线程中调用。
"""
from typing import *
import asyncio

_subscribers: Set[asyncio.Queue] = set()


def subscribe(max_size: int = 256) -> asyncio.Queue:
    queue = asyncio.Queue(maxsize=max_size)
    _subscribers.add(queue)
    return queue


def unsubscribe(queue: asyncio.Queue) -> None:
    _subscribers.discard(queue)


def publish(kind: str, data: Any = None) -> None:
    """
    向所有订阅者发布事件，订阅者队列已满时丢弃该事件（慢速客户端不会拖慢机器人）
    """
    for queue in tuple(_subscribers):
        try:
            queue.put_nowait((kind, data))
        except asyncio.QueueFull:
            pass


def subscriber_count() -> int:
    return len(_subscribers)
