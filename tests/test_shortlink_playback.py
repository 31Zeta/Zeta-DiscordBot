import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
import unittest
from unittest.mock import AsyncMock, Mock, patch

import discord
import requests
import utils
from zeta_bot.resource import LinkType, MediaPlatform


class ShortlinkPlaybackTests(unittest.IsolatedAsyncioTestCase):
    def test_play_uses_search_or_link_option_instead_of_link(self):
        tree = ast.parse(Path("zeta_bot/core.py").read_text(encoding="utf-8"))
        play = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "play")
        self.assertEqual(play.args.args[-1].arg, "query")
        option = next(
            decorator for decorator in play.decorator_list
            if isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Name)
            and decorator.func.id == "option"
        )
        self.assertEqual(option.args[0].value, "query")
        keywords = {keyword.arg: keyword.value for keyword in option.keywords}
        localizations = ast.literal_eval(keywords["name_localizations"])
        self.assertEqual(localizations["zh-CN"], "搜索或链接")
        self.assertEqual(localizations["en-US"], "search-or-link")
        command = next(
            decorator for decorator in play.decorator_list
            if isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr == "slash_command"
        )
        command_keywords = {keyword.arg: keyword.value for keyword in command.keywords}
        descriptions = ast.literal_eval(command_keywords["description_localizations"])
        self.assertIn("链接或歌曲名称", descriptions["zh-CN"])
        self.assertIn("link or search text", descriptions["en-US"])

    def test_redirect_follows_to_netease_song_and_closes_response(self):
        target = "https://y.music.163.com/m/song?id=2069431446&app_version=9.5.70"
        response = Mock(url=target)
        context = Mock(__enter__=Mock(return_value=response), __exit__=Mock(return_value=False))
        with patch.object(utils.requests, "get", return_value=context) as get:
            resolved = utils.get_redirect_url("https://163cn.tv/example")
        kind, formatted = LinkType.check(resolved)
        self.assertIs(kind.platform, MediaPlatform.NETEASE)
        self.assertFalse(kind.need_redirect)
        self.assertIn("id=2069431446", formatted)
        self.assertEqual(get.call_args.kwargs["timeout"], (5, 10))
        response.raise_for_status.assert_called_once()
        context.__exit__.assert_called_once()

    def test_network_timeout_propagates_as_request_exception(self):
        with patch.object(utils.requests, "get", side_effect=requests.Timeout):
            with self.assertRaises(requests.RequestException):
                utils.get_redirect_url("https://163cn.tv/example")

    async def test_old_webhook_failure_does_not_interrupt_new_playback(self):
        # 单独加载真实方法，避免初始化在线机器人的持久化库。
        tree = ast.parse(Path("zeta_bot/guild.py").read_text(encoding="utf-8"))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Guild")
        method = next(n for n in cls.body if getattr(n, "name", None) == "refresh_playing_message")
        namespace = {
            "discord": discord, "Optional": Optional,
            "icon": SimpleNamespace(url=lambda _: "https://example.com/icon.gif"),
            "icon_lib": SimpleNamespace(files=lambda _: []),
            "console": SimpleNamespace(rp=AsyncMock()),
        }
        exec(compile(ast.Module(body=[method], type_ignores=[]), "zeta_bot/guild.py", "exec"), namespace)
        for status, code in ((401, 50027), (404, 10008), (403, 50013)):
            with self.subTest(status=status):
                error = discord.HTTPException(SimpleNamespace(status=status, reason="test"), {"code": code, "message": "expired or inaccessible"})
                old = SimpleNamespace(edit=AsyncMock(side_effect=error))
                embed = discord.Embed()
                embed.set_author(name="正在播放 03:00")
                state = SimpleNamespace(_playing_message=old, _playing_embed=embed, _guild="test")
                new_message, new_embed = object(), discord.Embed()
                await namespace["refresh_playing_message"](state, new_message, new_embed)
                self.assertIs(state._playing_message, new_message)
                self.assertIs(state._playing_embed, new_embed)
                old.edit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
