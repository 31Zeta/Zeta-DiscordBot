"""跨平台流式预缓冲的离线回归测试。"""
import ast
import asyncio
import io
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from unittest.mock import Mock, patch


class FakeResponse:
    def __init__(self, payload: bytes):
        self.raw = io.BytesIO(payload)
        self.closed = False

    def raise_for_status(self):
        return None

    def close(self):
        self.closed = True
        self.raw.close()


class StreamPrebufferTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse(Path("zeta_bot/core.py").read_text(encoding="utf-8"))
        wanted = {
            "_safe_stream_headers",
            "_PrebufferedHTTPStream",
            "_open_prebuffered_http_stream",
        }
        nodes = [node for node in tree.body if getattr(node, "name", None) in wanted]
        cls.requests = SimpleNamespace(Response=object, get=Mock())
        cls.ns = {
            "Optional": Optional,
            "io": io,
            "asyncio": asyncio,
            "requests": cls.requests,
            "STREAM_PREBUFFER_BYTES": 1024 * 1024,
            "STREAM_CONNECT_TIMEOUT": 10,
            "STREAM_READ_TIMEOUT": 20,
        }
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "zeta_bot/core.py", "exec"), cls.ns)

    def test_headers_keep_media_fields_without_credentials(self):
        result = self.ns["_safe_stream_headers"]({
            "User-Agent": "Zeta Test",
            "Referer": "https://www.bilibili.com/",
            "Cookie": "SESSDATA=secret",
            "Authorization": "Bearer secret",
        })
        self.assertEqual(result["User-Agent"], "Zeta Test")
        self.assertEqual(result["Accept-Encoding"], "identity")
        self.assertNotIn("Cookie", result)
        self.assertNotIn("Authorization", result)

    def test_buffered_stream_preserves_byte_order_and_closes_response(self):
        response = FakeResponse(b"tail")
        stream = self.ns["_PrebufferedHTTPStream"](response, b"head")
        self.assertEqual(stream.read(2), b"he")
        self.assertEqual(stream.read(4), b"adta")
        self.assertEqual(stream.read(), b"il")
        stream.close()
        self.assertTrue(response.closed)

    async def test_open_stream_prefetches_without_blocking_event_loop(self):
        response = FakeResponse(b"abcdefgh")
        self.requests.get.reset_mock()
        self.requests.get.return_value = response
        stream = await self.ns["_open_prebuffered_http_stream"](
            "https://cdn.example/audio", {"User-Agent": "Zeta"}, prebuffer_bytes=4,
        )
        self.assertEqual(stream.read(8), b"abcdefgh")
        _, kwargs = self.requests.get.call_args
        self.assertTrue(kwargs["stream"])
        self.assertEqual(kwargs["headers"]["Accept-Encoding"], "identity")
        stream.close()


if __name__ == "__main__":
    unittest.main()
