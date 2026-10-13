"""
服务器播放状态

记录当前正在推流的音频、播放进度，以及停止推流时需要执行的操作。
VoiceClient.stop()会触发播放结束回调，回调根据pending_action决定后续行为：
    None      正常播放结束：按播放模式前进到下一个音频
    "skip"    用户跳过：前进到下一个音频（单曲循环模式下也会前进）
    "seek"    跳转进度：不移除当前音频，从value秒处重新开始播放
    "restart" 重新播放列表首位音频（例如移动了正在播放的音频、播放上一首）
    "hold"    保持列表不变，不继续播放（例如离开语音频道、清空列表）
"""
from typing import *
import time
import asyncio

PLAY_MODE_NAMES = {
    0: "顺序播放",
    1: "单曲循环",
    2: "列表循环",
    3: "随机播放",
    4: "随机循环",
}


class PlaybackState:
    def __init__(self):
        self.audio = None
        self._started_at: Optional[float] = None
        self._offset: float = 0.0
        self._paused_at: Optional[float] = None
        self.pending_action: Optional[str] = None
        self.pending_value: Any = None
        self.pause_after_start = False
        self._end_waiters: List[asyncio.Future] = []

    def add_end_waiter(self) -> asyncio.Future:
        """
        返回一个在下一次播放结束处理完成后完成的Future（用于让界面在切换完成后再刷新）
        """
        waiter = asyncio.get_running_loop().create_future()
        self._end_waiters.append(waiter)
        return waiter

    def resolve_end_waiters(self) -> None:
        waiters, self._end_waiters = self._end_waiters, []
        for waiter in waiters:
            if not waiter.done():
                waiter.set_result(True)

    def start(self, target_audio, offset: float = 0.0) -> None:
        self.audio = target_audio
        self._started_at = time.monotonic()
        self._offset = max(0.0, float(offset))
        self._paused_at = None

    def pause(self) -> None:
        if self._started_at is not None and self._paused_at is None:
            self._paused_at = time.monotonic()

    def resume(self) -> None:
        if self._started_at is not None and self._paused_at is not None:
            self._started_at += time.monotonic() - self._paused_at
            self._paused_at = None

    def stop(self) -> None:
        self.audio = None
        self._started_at = None
        self._offset = 0.0
        self._paused_at = None

    def is_active(self) -> bool:
        return self.audio is not None

    def is_paused(self) -> bool:
        return self._paused_at is not None

    def position(self) -> float:
        """
        当前播放进度（秒）
        """
        if self._started_at is None:
            return 0.0
        end = self._paused_at if self._paused_at is not None else time.monotonic()
        position = end - self._started_at + self._offset
        if self.audio is not None and self.audio.get_duration() > 0:
            position = min(position, float(self.audio.get_duration()))
        return max(0.0, position)

    def remaining(self) -> float:
        if self.audio is None:
            return 0.0
        return max(0.0, self.audio.get_duration() - self.position())

    def request(self, action: Optional[str], value: Any = None) -> None:
        self.pending_action = action
        self.pending_value = value

    def consume_request(self) -> Tuple[Optional[str], Any]:
        action, value = self.pending_action, self.pending_value
        self.pending_action = None
        self.pending_value = None
        return action, value


def progress_bar(position: float, duration: float, width: int = 14) -> str:
    """
    生成文本进度条，例如 ▬▬▬▬🔘▬▬▬▬▬▬▬▬▬
    """
    if duration <= 0:
        return "▬" * width
    filled = int(round(min(1.0, max(0.0, position / duration)) * (width - 1)))
    return "▬" * filled + "🔘" + "▬" * (width - 1 - filled)
