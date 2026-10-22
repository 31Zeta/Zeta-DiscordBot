"""离线回归：执行真实菜单代码，隔离core导入时的登录、配置和日志副作用。"""
import ast
import random
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Optional, Union
from unittest.mock import AsyncMock, Mock, patch

import discord
import errors
import utils
from zeta_bot import output_console
from zeta_bot.resource import DownloadType, DownloadHandler, MediaPlatform, LinkType, ResourceClassifier

with patch.object(output_console, "Console", return_value=SimpleNamespace(rp=AsyncMock())):
    from zeta_bot import ytdlp


def playlist(count=3):
    return ytdlp.normalize_bilibili_parts({
        "_type": "playlist", "id": "BV139pxeGENb", "title": "测试合集",
        "entries": [{"_type": "url", "url": f"https://www.bilibili.com/video/BV139pxeGENb?p={p}"}
                    for p in range(1, count + 1)],
    })


class PartsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.queue = Mock()
        self.queue.is_empty.return_value = False
        self.guild = SimpleNamespace(get_playlist=lambda: self.queue, refresh_list_view=AsyncMock())
        self.ctx = SimpleNamespace(guild=SimpleNamespace(voice_client=Mock()))
        self.audio_lib = SimpleNamespace(download_ytdlp=AsyncMock(), download_bilibili=AsyncMock())
        self.get_info = AsyncMock()
        async def get_info_with_fallback(url, platform=None):
            return await self.get_info(url)
        self.ns = {
            "discord": discord, "errors": errors, "View": discord.ui.View, "Optional": Optional, "Union": Union,
            "utils": utils, "random": random, "DownloadType": DownloadType,
            "DownloadHandler": DownloadHandler, "MediaPlatform": MediaPlatform,
            "resource_classifier": SimpleNamespace(handler=lambda _: DownloadHandler.YT_DLP),
            "guild_lib": SimpleNamespace(get_guild=lambda _: self.guild),
            "console": SimpleNamespace(rp=AsyncMock()), "audio_lib_main": self.audio_lib,
            "ytdlp": SimpleNamespace(get_info=self.get_info), "result_check": AsyncMock(side_effect=lambda r: r),
            "_get_ytdlp_info_with_bilibili_fallback": get_info_with_fallback,
            "eos": AsyncMock(), "embed_eos": AsyncMock(), "play_audio": AsyncMock(),
            "icon": SimpleNamespace(url=lambda _: "https://example.com/icon.gif"),
            "icon_lib": SimpleNamespace(files=lambda _: []), "delete_response": AsyncMock(),
            "orange": discord.Color.orange(),
            "embed_append_description": lambda embed, line: setattr(embed, "description", (embed.description or "") + "\n" + line),
        }
        source = Path("zeta_bot/core.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        nodes = [n for n in tree.body if getattr(n, "name", None) in ("EpisodeSelectMenu", "play_ytdlp")]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "zeta_bot/core.py", "exec"), self.ns)
        # core的/list命令会覆盖内置list，菜单不可依赖该名字。
        self.ns["list"] = AsyncMock()

    def menu(self, count=3):
        info = playlist(count)
        menu = self.ns["EpisodeSelectMenu"](self.ctx, DownloadType.BILIBILI_P, info, ["分集目录"])
        menu.original_msg = SimpleNamespace(edit=AsyncMock())
        return menu

    async def test_playlist_shows_selection_without_downloading(self):
        self.get_info.return_value = utils.success_result(playlist(140))
        await self.ns["play_ytdlp"](self.ctx, "https://www.bilibili.com/video/BV139pxeGENb", platform=MediaPlatform.BILIBILI)
        menu = self.ns["eos"].call_args.kwargs["view"]
        self.assertEqual(len(menu.menu_list), 14)
        self.assertEqual(menu.timeout, 180)
        self.assertTrue(menu.ytdlp_bilibili_parts)
        self.audio_lib.download_ytdlp.assert_not_awaited()

    async def test_selected_parts_keep_order_and_bilibili_downloader(self):
        menu = self.menu()
        audio = Mock()
        audio.get_title.return_value = "选中的歌曲"
        audio.get_duration_str.return_value = "03:00"
        self.get_info.side_effect = lambda url: utils.success_result({"id": "BV139pxeGENb_p" + url.split("p=")[-1]})
        self.audio_lib.download_ytdlp.return_value = utils.success_result(audio)
        await menu.play_select([3, 1])
        self.assertEqual([c.args[0] for c in self.get_info.await_args_list], [
            "https://www.bilibili.com/video/BV139pxeGENb?p=3",
            "https://www.bilibili.com/video/BV139pxeGENb?p=1",
        ])
        self.assertEqual([c.args[1]["id"] for c in self.audio_lib.download_ytdlp.await_args_list],
                         ["BV139pxeGENb_p3", "BV139pxeGENb_p1"])
        self.assertTrue(all(c.args[2] is DownloadType.BILIBILI_P for c in self.audio_lib.download_ytdlp.await_args_list))
        self.audio_lib.download_bilibili.assert_not_awaited()
        self.assertEqual(self.queue.append_audio.call_count, 2)
        self.assertFalse(menu.children)

    async def test_cancel_between_parts_stops_remaining_requests(self):
        menu = self.menu()
        async def cancel_during_info(url):
            menu.cancel_requested = True
            return utils.success_result({"id": "BV139pxeGENb_p1"})
        self.get_info.side_effect = cancel_during_info
        await menu.play_select([1, 2])
        self.get_info.assert_awaited_once()
        self.audio_lib.download_ytdlp.assert_not_awaited()

    async def test_buttons_validate_range_and_bulk_limit(self):
        menu = self.menu(140)
        interaction = SimpleNamespace(response=SimpleNamespace(edit_message=AsyncMock(), defer=AsyncMock()))
        menu.play_select = AsyncMock()
        await menu.button_all_callback.callback(interaction)
        menu.play_select.assert_not_awaited()
        for selection in ("0", "141", "1-11", "1,", "1-"):
            menu.result = list(selection)
            await menu.button_confirm_callback.callback(interaction)
            menu.play_select.assert_not_awaited()
        menu.result = list("3,1")
        await menu.button_confirm_callback.callback(interaction)
        menu.play_select.assert_awaited_once_with([3, 1])
        await menu.button_confirm_callback.callback(interaction)
        menu.play_select.assert_awaited_once()

    async def test_titles_and_duration_with_api_and_fallback(self):
        info = playlist()
        self.assertIsNone(info["entries"][0]["duration"])
        enriched = ytdlp.normalize_bilibili_parts(info, [{"page": 1, "part": "Love Song", "duration": 289}])
        self.assertEqual(enriched["entries"][0]["title"], "Love Song")
        self.assertEqual(enriched["entries"][0]["duration"], 289)
        self.assertEqual(len(enriched["entries"]), 3)

    async def test_bare_bvid_preserves_explicit_part(self):
        kind, url = LinkType.check("BV139pxeGENb?p=3&from=search")
        self.assertIs(kind, LinkType.BILIBILI_BVID)
        self.assertEqual(ytdlp.bilibili_part_number(url), 3)
        for part in ("0", "-1", "", "abc"):
            with self.assertRaises(ValueError):
                ytdlp.bilibili_part_number("https://www.bilibili.com/video/BV139pxeGENb?p=" + part)
        self.assertNotEqual(ytdlp.construct_uid("BV139pxeGENb_p1", DownloadType.BILIBILI_P),
                            ytdlp.construct_uid("BV139pxeGENb_p2", DownloadType.BILIBILI_P))

    async def test_explicit_part_uses_single_download_path(self):
        info = {"id": "BV139pxeGENb_p2", "title": "第2P"}
        self.get_info.return_value = utils.success_result(info)
        audio = Mock()
        self.audio_lib.download_ytdlp.return_value = utils.success_result(audio)
        url = "https://www.bilibili.com/video/BV139pxeGENb?p=2"
        await self.ns["play_ytdlp"](self.ctx, url, platform=MediaPlatform.BILIBILI)
        self.audio_lib.download_ytdlp.assert_awaited_once_with(url, info, DownloadType.BILIBILI_SINGLE)

    async def test_failed_part_does_not_block_next_selected_part(self):
        menu = self.menu()
        self.get_info.return_value = utils.success_result({"id": "part"})
        self.audio_lib.download_ytdlp.side_effect = [
            utils.failed_result(None, "临时下载失败", False),
            utils.success_result(Mock()),
        ]
        await menu.play_select([1, 2])
        self.assertEqual(self.audio_lib.download_ytdlp.await_count, 2)
        self.queue.append_audio.assert_called_once()
        self.assertFalse(menu.processing)

    async def test_youtube_playlist_still_uses_youtube_urls(self):
        info = {"title": "YT", "entries": [{"id": "abcdefghijk", "title": "song", "duration": 120}]}
        menu = self.ns["EpisodeSelectMenu"](self.ctx, DownloadType.YOUTUBE_PLAYLIST, info, ["目录"])
        self.get_info.return_value = utils.success_result({"id": "abcdefghijk"})
        self.audio_lib.download_ytdlp.return_value = utils.success_result(Mock())
        await menu.play_select([1])
        self.get_info.assert_awaited_once_with("https://www.youtube.com/watch?v=abcdefghijk")
        self.assertIs(self.audio_lib.download_ytdlp.call_args.args[2], DownloadType.YOUTUBE_PLAYLIST)


if __name__ == "__main__":
    unittest.main()
