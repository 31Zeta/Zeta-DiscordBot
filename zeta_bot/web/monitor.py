"""
运行状态监控：日志缓存、指令统计、系统资源与延迟采样
"""
from typing import *
import os
import sys
import time
import shutil
import platform
import collections

import utils

from zeta_bot import events

try:
    import psutil
except ImportError:
    psutil = None

SAMPLE_INTERVAL = 10
# 保存最近1小时的采样
SAMPLE_HISTORY = 360
LOG_BUFFER_SIZE = 1000

LEVEL_NAMES = {
    utils.PrintType.ERROR: "error",
    utils.PrintType.WARNING: "warning",
    utils.PrintType.CAUTION: "warning",
    utils.PrintType.DEBUG: "debug",
}


class Monitor:
    def __init__(self):
        self.started_at = time.time()
        self.logs: Deque[dict] = collections.deque(maxlen=LOG_BUFFER_SIZE)
        self._log_id = 0
        self.counters = {"error": 0, "warning": 0}
        self.commands: Counter = collections.Counter()
        self.command_total = 0
        self.samples: Deque[dict] = collections.deque(maxlen=SAMPLE_HISTORY)
        self._process = psutil.Process() if psutil is not None else None
        if self._process is not None:
            # 首次调用cpu_percent返回0，先调用一次作为基准
            self._process.cpu_percent(None)

    # ---------- 日志 ----------
    def on_log(self, time_str: str, location: str, message_type, content: str) -> None:
        level = LEVEL_NAMES.get(message_type, "info")
        if level in self.counters:
            self.counters[level] += 1
        self._log_id += 1
        entry = {
            "id": self._log_id,
            "time": time_str,
            "location": location.strip("[]") if location else "",
            "level": level,
            "content": content,
        }
        self.logs.append(entry)
        events.publish("log", entry)

    def get_logs(self, after: int = 0, limit: int = 300) -> List[dict]:
        result = [entry for entry in self.logs if entry["id"] > after]
        return result[-limit:]

    # ---------- 指令 ----------
    def record_command(self, name: str) -> None:
        self.commands[str(name)] += 1
        self.command_total += 1

    # ---------- 系统 ----------
    def uptime(self) -> float:
        return time.time() - self.started_at

    def system_info(self, disk_path: str = ".") -> dict:
        info = {
            "python": platform.python_version(),
            "platform": f"{platform.system()} {platform.release()}",
            "pid": os.getpid(),
            "psutil": self._process is not None,
        }
        if self._process is not None:
            with self._process.oneshot():
                memory = self._process.memory_info()
                info.update({
                    "cpu_percent": round(self._process.cpu_percent(None), 1),
                    "memory_rss": memory.rss,
                    "threads": self._process.num_threads(),
                })
            info["system_cpu_percent"] = psutil.cpu_percent(None)
            virtual_memory = psutil.virtual_memory()
            info["system_memory"] = {"total": virtual_memory.total, "used": virtual_memory.used, "percent": virtual_memory.percent}
        try:
            disk = shutil.disk_usage(disk_path)
            info["disk"] = {"total": disk.total, "used": disk.used, "free": disk.free}
        except OSError:
            pass
        return info

    def sample(self, latency_ms: Optional[float], voice_connections: int, playing: int) -> dict:
        point = {
            "t": int(time.time()),
            "latency": latency_ms,
            "voice": voice_connections,
            "playing": playing,
        }
        if self._process is not None:
            point["cpu"] = round(self._process.cpu_percent(None), 1)
            point["rss"] = self._process.memory_info().rss
        self.samples.append(point)
        events.publish("sample", point)
        return point
