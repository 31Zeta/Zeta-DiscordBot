"""B站API回退的离线结构测试。"""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock, patch

import utils
from zeta_bot import output_console
from zeta_bot.resource import MediaPlatform

with patch.object(output_console, "Console", return_value=SimpleNamespace(rp=AsyncMock())):
    from zeta_bot import bilibili


class BilibiliApiFallbackTests(unittest.TestCase):
    def setUp(self):
        self.metadata = {
            "title": "测试合集",
            "pic": "https://example.com/cover.jpg",
            "pages": [
                {"page": 1, "cid": 101, "part": "第一集", "duration": 60},
                {"page": 2, "cid": 102, "part": "第二集", "duration": 90},
            ],
        }

    def test_playlist_preserves_part_number_url_and_duration(self):
        result = bilibili._fallback_playlist(self.metadata, "BV1234567890")
        self.assertEqual(result["_type"], "playlist")
        self.assertEqual(result["entries"][1]["id"], "BV1234567890_p2")
        self.assertEqual(result["entries"][1]["duration"], 90)
        self.assertTrue(result["entries"][1]["url"].endswith("?p=2"))

    def test_stream_chooses_highest_bandwidth_audio(self):
        download = {"dash": {"audio": [
            {"id": 30216, "bandwidth": 64000, "baseUrl": "https://cdn/low.m4s", "codecs": "mp4a.40.2"},
            {"id": 30280, "bandwidth": 192000, "baseUrl": "https://cdn/high.m4s", "codecs": "mp4a.40.2"},
        ]}}
        result = bilibili._fallback_stream_info(
            self.metadata, download, "BV1234567890", 2,
        )
        self.assertEqual(result["url"], "https://cdn/high.m4s")
        self.assertEqual(result["id"], "BV1234567890_p2")
        self.assertEqual(result["duration"], 90)
        self.assertEqual(result["http_headers"]["Referer"],
                         "https://www.bilibili.com/video/BV1234567890")

    def test_invalid_part_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "共 2 P"):
            bilibili._fallback_stream_info(self.metadata, {}, "BV1234567890", 3)
        for value in ("0", "-1", "abc", ""):
            with self.assertRaises(ValueError):
                bilibili._part_number(f"https://www.bilibili.com/video/BV1234567890?p={value}")


class BilibiliCoreFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_ytdlp_failure_reaches_bilibili_api_without_name_error(self):
        primary = utils.failed_result(RuntimeError("yt-dlp failed"), "解析失败", False)
        fallback = utils.success_result({"id": "BV1234567890", "url": "https://cdn/audio.m4s"})
        ytdlp_mock = SimpleNamespace(get_info=AsyncMock(return_value=primary))
        bilibili_mock = SimpleNamespace(get_ytdlp_fallback_info=AsyncMock(return_value=fallback))
        console_mock = SimpleNamespace(rp=AsyncMock())
        namespace = {
            "Optional": Optional, "MediaPlatform": MediaPlatform, "utils": utils,
            "Result": utils.Result, "failed_result": utils.failed_result,
            "ytdlp": ytdlp_mock, "bilibili": bilibili_mock, "console": console_mock,
        }
        tree = ast.parse(Path("zeta_bot/core.py").read_text(encoding="utf-8"))
        node = next(n for n in tree.body
                    if getattr(n, "name", None) == "_get_ytdlp_info_with_bilibili_fallback")
        exec(compile(ast.Module(body=[node], type_ignores=[]), "zeta_bot/core.py", "exec"), namespace)

        result = await namespace["_get_ytdlp_info_with_bilibili_fallback"](
            "https://www.bilibili.com/video/BV1234567890", MediaPlatform.BILIBILI,
        )

        self.assertIs(result, fallback)
        bilibili_mock.get_ytdlp_fallback_info.assert_awaited_once()
        console_mock.rp.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
