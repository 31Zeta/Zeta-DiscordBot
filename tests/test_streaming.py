"""流式播放的离线回归测试。"""
import ast
import shlex
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock, patch

import discord
from zeta_bot import audio, output_console, resource
from zeta_bot.resource import DownloadHandler, DownloadType

def handler_for(download_type):
    if download_type.name.startswith(("YOUTUBE", "BILIBILI")):
        return DownloadHandler.YT_DLP
    return DownloadHandler.GO_MUSIC_API


with (
    patch.object(output_console, "Console", return_value=SimpleNamespace(rp=AsyncMock())),
    patch.object(resource, "ResourceClassifier", return_value=SimpleNamespace(handler=handler_for)),
):
    from zeta_bot import file_management, go_music, ytdlp


class StreamingAudioTests(unittest.IsolatedAsyncioTestCase):
    async def test_file_library_returns_stream_without_size_probe_or_download(self):
        library = file_management.AudioFileLibrary("downloads", "unused.json")
        library._initialized = True
        info = {
            "id": "abc", "title": "测试", "duration": 12, "ext": "m4a",
            "url": "https://cdn.example/audio", "filesize": 100,
        }
        with (
            patch.object(library, "_cached_audio_by_uid", new=AsyncMock(return_value=None)),
            patch.object(ytdlp, "get_filesize", new=AsyncMock()) as size_probe,
            patch.object(ytdlp, "audio_download", new=AsyncMock()) as downloader,
        ):
            result = await library.download_ytdlp(
                "https://example.com/watch?v=abc", info, DownloadType.YOUTUBE_SINGLE,
            )
        self.assertTrue(result)
        self.assertTrue(result.result.is_stream())
        size_probe.assert_not_awaited()
        downloader.assert_not_awaited()

    def test_audio_stream_state_survives_queue_serialization(self):
        item = audio.Audio(
            "测试歌曲", "youtube_abc", "youtube", "abc",
            DownloadType.YOUTUBE_SINGLE, "stream://youtube_abc", 123,
            stream=True, stream_origin="https://example.com/watch?v=abc",
            stream_data={"info": {"url": "https://cdn.example/audio"}, "resolved_at": 42},
        )
        decoded = audio.audio_decoder(item.encode())
        self.assertTrue(decoded.is_stream())
        self.assertEqual(decoded.get_stream_origin(), item.get_stream_origin())
        self.assertEqual(decoded.get_stream_data(), item.get_stream_data())

    def test_ytdlp_stream_object_does_not_store_full_format_list(self):
        info = {
            "id": "abc", "title": "测试", "duration": 12,
            "url": "https://cdn.example/audio", "thumbnail": "https://example/cover.jpg",
            "formats": [{"url": "large-and-temporary"}],
        }
        item = ytdlp.create_stream_audio(
            "https://example.com/watch?v=abc", info, DownloadType.YOUTUBE_SINGLE,
        )
        self.assertTrue(item.is_stream())
        self.assertTrue(item.get_path().startswith("stream://"))
        self.assertNotIn("formats", item.get_stream_data()["info"])
        self.assertLessEqual(time.time() - item.get_stream_data()["resolved_at"], 2)

    async def test_go_music_stream_url_uses_local_proxy_and_encoded_params(self):
        info = {"source": "netease", "id": "21162695", "name": "歌", "artist": "歌手"}
        with patch.object(go_music, "use_local_cookie", new=AsyncMock()) as sync_cookie:
            url = await go_music.get_stream_url("http://127.0.0.1:8080", info)
        self.assertTrue(url.startswith("http://127.0.0.1:8080/api/v1/music/stream?"))
        self.assertIn("source=netease", url)
        self.assertIn("id=21162695", url)
        sync_cookie.assert_awaited_once()


class StreamingCoreTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse(Path("zeta_bot/core.py").read_text(encoding="utf-8"))
        wanted = {"_ffmpeg_stream_before_options", "_handle_playback_after"}
        nodes = [node for node in tree.body if getattr(node, "name", None) in wanted]
        cls.ns = {
            "Optional": Optional,
            "shlex": shlex,
            "discord": discord,
            "audio": audio,
            "play_next": AsyncMock(),
            "_fallback_and_replay": AsyncMock(),
        }
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "zeta_bot/core.py", "exec"), cls.ns)

    def test_ffmpeg_options_reconnect_without_forwarding_credentials(self):
        value = self.ns["_ffmpeg_stream_before_options"]({
            "User-Agent": "Zeta Test",
            "Referer": "https://www.bilibili.com/",
            "Cookie": "session=fake-test-value",
            "Authorization": "Bearer fake-test-value",
        })
        args = shlex.split(value)
        self.assertIn("-reconnect", args)
        self.assertIn("User-Agent: Zeta Test", value)
        self.assertNotIn("fake-test-value", value)
        self.assertNotIn("Bearer", value)

    async def test_nonzero_stream_exit_falls_back_but_manual_stop_advances(self):
        fallback = self.ns["_fallback_and_replay"]
        next_track = self.ns["play_next"]
        stream = SimpleNamespace(is_stream=lambda: True)
        ctx = object()

        fallback.reset_mock()
        next_track.reset_mock()
        fallback.return_value = True
        await self.ns["_handle_playback_after"](ctx, stream, 1)
        fallback.assert_awaited_once()
        next_track.assert_not_awaited()

        fallback.reset_mock()
        next_track.reset_mock()
        await self.ns["_handle_playback_after"](ctx, stream, None)
        fallback.assert_not_awaited()
        next_track.assert_awaited_once_with(ctx)


if __name__ == "__main__":
    unittest.main()
