import discord
from discord.ui import Button, View
from zeta_bot import (
    errors,
    language,
    log,
    utils,
    playlist
)

# 多语言模块
lang = language.Lang()
_ = lang.get_string
printl = lang.printl


# TODO 添加列表总时长显示
class PlaylistMenu(View):

    def __init__(self, ctx, playlist_1: playlist.Playlist, logger: log.Log = None, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.playlist = playlist_1
        self.playlist_pages = utils.make_playlist_page(self.playlist.get_list_info(), 10, indent=2)
        self.page_num = 0
        self.occur_time = utils.time()
        # 保留当前第一页作为超时后显示的内容
        self.first_page = f">>> **{self.playlist.get_name()}**\n\n{self.playlist_pages[0]}\n" \
                          f"第[1]页，共[{len(self.playlist_pages)}]页\n"
        self.logger = logger

    def refresh_pages(self):
        self.playlist_pages = utils.make_playlist_page(self.playlist.get_list_info(), 10, indent=2)
        self.first_page = f">>> **{self.playlist.get_name()}**\n\n{self.playlist_pages[0]}\n" \
                          f"第[1]页，共[{len(self.playlist_pages)}]页\n"

    @discord.ui.button(label="上一页", style=discord.ButtonStyle.grey,
                       custom_id="button_previous")
    async def button_previous_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.refresh_pages()
        # 翻页
        if self.page_num == 0:
            return
        else:
            self.page_num -= 1
        await msg.edit_message(
            content=f">>> **{self.playlist.get_name()}**\n\n{self.playlist_pages[self.page_num]}\n"
                    f"第[{self.page_num + 1}]页，"
                    f"共[{len(self.playlist_pages)}]页\n", view=self
        )

    @discord.ui.button(label="下一页", style=discord.ButtonStyle.grey,
                       custom_id="button_next")
    async def button_next_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.refresh_pages()
        # 翻页
        if self.page_num == len(self.playlist_pages) - 1:
            return
        else:
            self.page_num += 1
        await msg.edit_message(
            content=f">>> **{self.playlist.get_name()}**\n\n{self.playlist_pages[self.page_num]}\n"
                    f"第[{self.page_num + 1}]页，"
                    f"共[{len(self.playlist_pages)}]页\n", view=self
        )

    @discord.ui.button(label="刷新", style=discord.ButtonStyle.grey,
                       custom_id="button_refresh")
    async def button_refresh_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.refresh_pages()

        await msg.edit_message(
            content=f">>> **{self.playlist.get_name()}**\n\n{self.playlist_pages[self.page_num]}\n"
                    f"第[{self.page_num + 1}]页，"
                    f"共[{len(self.playlist_pages)}]页\n", view=self
        )

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.grey,
                       custom_id="button_close")
    async def button_close_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content="已关闭", view=self)
        await self.ctx.delete()

    async def on_timeout(self):
        self.clear_items()
        await self.ctx.edit(content=self.first_page, view=self)
        if self.logger is not None:
            self.logger.rp(f"{self.occur_time}生成的播放列表菜单已超时(超时时间为{self.timeout}秒)", self.ctx.guild)


# TODO 未完成
class EpisodeSelectView(View):

    def __init__(self, ctx, source, info_dict, menu_list, timeout=60):
        """
        初始化分集选择菜单

        :param ctx: 指令原句
        :param source: 播放源的种类（bili_p, bili_collection, ytb_playlist)
        :param info_dict: 播放源的信息字典
        :param menu_list: 选择菜单的文本（使用make_menu_list获取）
        :param timeout: 超时时间（单位：秒）
        :return:
        """
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.source = source
        self.info_dict = info_dict
        self.menu_list = menu_list
        self.page_num = 0
        self.result = []
        self.dash_finish = True
        self.occur_time = utils.time()
        self.voice_client = self.ctx.guild.voice_client
        self.current_playlist = playlist_dict[ctx.guild.id]

        self.finish = False

    @discord.ui.button(label="1", style=discord.ButtonStyle.grey,
                       custom_id="button_1", row=1)
    async def button_1_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("1")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="2", style=discord.ButtonStyle.grey,
                       custom_id="button_2", row=1)
    async def button_2_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("2")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="3", style=discord.ButtonStyle.grey,
                       custom_id="button_3", row=1)
    async def button_3_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("3")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="4", style=discord.ButtonStyle.grey,
                       custom_id="button_4", row=2)
    async def button_4_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("4")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="5", style=discord.ButtonStyle.grey,
                       custom_id="button_5", row=2)
    async def button_5_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("5")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="6", style=discord.ButtonStyle.grey,
                       custom_id="button_6", row=2)
    async def button_6_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("6")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="7", style=discord.ButtonStyle.grey,
                       custom_id="button_7", row=3)
    async def button_7_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("7")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="8", style=discord.ButtonStyle.grey,
                       custom_id="button_8", row=3)
    async def button_8_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("8")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="9", style=discord.ButtonStyle.grey,
                       custom_id="button_9", row=3)
    async def button_9_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("9")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="-", style=discord.ButtonStyle.grey,
                       custom_id="button_dash", row=4)
    async def button_dash_callback(self, button, interaction):
        button.disabled = False

        if len(self.result) == 0 or not \
                self.result[len(self.result) - 1].isdigit() or not \
                self.dash_finish:
            return

        msg = interaction.response
        self.result.append("-")
        self.dash_finish = False
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="0", style=discord.ButtonStyle.grey,
                       custom_id="button_0", row=4)
    async def button_0_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.result.append("0")
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label=",", style=discord.ButtonStyle.grey,
                       custom_id="button_comma", row=4)
    async def button_comma_callback(self, button, interaction):
        button.disabled = False

        if len(self.result) == 0 or not \
                self.result[len(self.result) - 1].isdigit():
            return

        msg = interaction.response
        self.result.append(",")
        self.dash_finish = True
        num = ""
        for i in self.result:
            num = num + i
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="<-", style=discord.ButtonStyle.grey,
                       custom_id="button_backspace", row=1)
    async def button_backspace_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        if len(self.result) <= 0:
            pass
        else:
            self.result.pop()
            num = ""
            for i in self.result:
                num = num + i
            await msg.edit_message(
                content=f"{self.menu_list[self.page_num]}\n第"
                        f"[{self.page_num + 1}]页，共[{len(self.menu_list)}]页\n"
                        f"已输入：" + num, view=self)

    @discord.ui.button(label="取消", style=discord.ButtonStyle.red,
                       custom_id="button_cancel", row=3)
    async def button_cancel_callback(self, button, interaction):
        button.disabled = True
        self.finish = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已取消", view=self)

    @discord.ui.button(label="确定", style=discord.ButtonStyle.green,
                       custom_id="button_confirm", row=4)
    async def button_confirm_callback(self, button, interaction):
        message = "已选择"
        button.disabled = False
        self.finish = True

        if len(self.result) == 0 or self.result[len(self.result) - 1] == "-":
            return

        msg = interaction.response
        self.clear_items()
        num = ""
        final_result = []
        temp = []
        for item in self.result:
            if item == "-":
                temp.append(int(num))
                temp.append("-")
                num = ""
            elif item == ",":
                if not len(temp) == 0 and temp[len(temp) - 1] == "-":
                    temp.pop()
                    start = temp.pop()
                    if int(num) < start:
                        start_num = int(num)
                        for i in range(start, int(num) - 1, -1):
                            if i == 0:
                                start_num = 1
                            else:
                                final_result.append(i)
                        message = message + f"第[{start_num}]首至第[{start}]首(倒序)，"
                    else:
                        start_num = start
                        for i in range(start, int(num) + 1):
                            if i == 0:
                                start_num = 1
                            else:
                                final_result.append(i)
                        message = message + f"第[{start_num}]首至第[{int(num)}]首，"
                    num = ""
                else:
                    if int(num) == 0:
                        pass
                    else:
                        final_result.append(int(num))
                        message = message + f"第[{int(num)}]首，"
                    num = ""
            else:
                num = num + item
        if num == "":
            pass
        elif not len(temp) == 0 and temp[len(temp) - 1] == "-":
            temp.pop()
            start = temp.pop()
            if int(num) < start:
                start_num = int(num)
                for i in range(start, int(num) - 1, -1):
                    if i == 0:
                        start_num = 1
                    else:
                        final_result.append(i)
                message = message + f"第[{start_num}]首至第[{start}]首(倒序)，"
            else:
                start_num = start
                for i in range(start, int(num) + 1):
                    if i == 0:
                        start_num = 1
                    else:
                        final_result.append(i)
                message = message + f"第[{start_num}]首至第[{int(num)}]首，"
        else:
            if int(num) == 0:
                pass
            else:
                final_result.append(int(num))
                message = message + f"第[{int(num)}]首，"

        if self.source == "bili_p":
            for num in final_result:
                if num > len(self.info_dict["pages"]):
                    self.clear_items()
                    await msg.edit_message(content="选择中含有无效分p号", view=self)
                    return
        elif self.source == "bili_collection":
            for num in final_result:
                if num > len(self.info_dict["ugc_season"]["sections"][0][
                                 "episodes"]):
                    self.clear_items()
                    await msg.edit_message(content="选择中含有无效集数", view=self)
                    return
        elif self.source == "ytb_playlist":
            for num in final_result:
                if num > len(self.info_dict["entries"]):
                    self.clear_items()
                    await msg.edit_message(content="选择中含有无效集数", view=self)
                    return

        message = message[:-1]
        self.clear_items()
        await msg.edit_message(content=message, view=self)

        await self.play_select(final_result)

    @discord.ui.button(label="上一页", style=discord.ButtonStyle.blurple,
                       custom_id="button_previous", row=3)
    async def button_previous_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        num = ""
        for i in self.result:
            num = num + i
        # 翻页
        if self.page_num == 0:
            return
        else:
            self.page_num -= 1
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="下一页", style=discord.ButtonStyle.blurple,
                       custom_id="button_next", row=4)
    async def button_next_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        num = ""
        for i in self.result:
            num = num + i
        # 翻页
        if self.page_num == len(self.menu_list) - 1:
            return
        else:
            self.page_num += 1
        await msg.edit_message(
            content=f"{self.menu_list[self.page_num]}\n第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n已输入：" + num, view=self)

    @discord.ui.button(label="全部", style=discord.ButtonStyle.blurple,
                       custom_id="button_all", row=2)
    async def button_all_callback(self, button, interaction):
        button.disabled = False
        self.finish = True
        msg = interaction.response

        total_num = 0
        final_result = []
        if self.source == "bili_p":
            total_num = len(self.info_dict["pages"])
        elif self.source == "bili_collection":
            total_num = len(
                self.info_dict["ugc_season"]["sections"][0]["episodes"])
        elif self.source == "ytb_playlist":
            total_num = len(self.info_dict["entries"])

        for num in range(1, total_num + 1):
            final_result.append(num)

        self.clear_items()
        await msg.edit_message(content=f"已选择全部[{total_num}]首", view=self)
        await self.play_select(final_result)

    async def play_select(self, final_result):
        total_num = len(final_result)
        total_duration = 0

        # ----- 下载并播放视频 -----

        # 如果为Bilibili分p视频
        if self.source == "bili_p":
            counter = 1
            for item in self.info_dict["pages"]:
                if counter in final_result:
                    total_duration += item["duration"]
                counter += 1
            total_duration = convert_duration_to_time(total_duration)
            loading_msg = await self.ctx.send(f"正在将{total_num}首歌曲加入播放"
                                              f"列表  总时长 -> [{total_duration}]")

            for num_p in final_result:
                await play_bili(self.ctx, self.info_dict, "bili_p", num_p - 1)

            await loading_msg.delete()
            await self.ctx.send(f"已将{total_num}首歌曲加入播放列表  "
                                f"总时长 -> [{total_duration}]")

        # 如果为Bilibili合集视频
        elif self.source == "bili_collection":
            counter = 1
            for item in self.info_dict["ugc_season"]["sections"][0]["episodes"]:
                if counter in final_result:
                    total_duration += item["arc"]["duration"]
                counter += 1
            total_duration = convert_duration_to_time(total_duration)
            loading_msg = await self.ctx.send(f"正在将{total_num}首歌曲加入播放"
                                              f"列表  总时长 -> [{total_duration}]")

            for num in final_result:
                bvid = self.info_dict["ugc_season"]["sections"][0]["episodes"][
                    num - 1]["bvid"]
                info_dict = await bili_get_info(bvid)
                await play_bili(self.ctx, info_dict, "bili_collection")

            await loading_msg.delete()
            await self.ctx.send(f"已将{total_num}首歌曲加入播放列表  "
                                f"总时长 -> [{total_duration}]")

        # 如果为Youtube播放列表
        elif self.source == "ytb_playlist":
            counter = 1
            for item in self.info_dict["entries"]:
                if counter in final_result:
                    total_duration += item["duration"]
                counter += 1
            total_duration = convert_duration_to_time(total_duration)
            loading_msg = await self.ctx.send(f"正在将{total_num}首歌曲加入播放"
                                              f"列表  总时长 -> [{total_duration}]")

            for num in final_result:
                url = f"https://www.youtube.com/watch?v=" \
                      f"{self.info_dict['entries'][num - 1]['id']}"
                download_type, info_dict = ytb_get_info(url)
                await play_ytb(self.ctx, url, info_dict, "ytb_playlist")

            await loading_msg.delete()
            await self.ctx.send(f"已将{total_num}首歌曲加入播放列表  "
                                f"总时长 -> [{total_duration}]")

        else:
            console_message_log(self.ctx, "未知的播放源")

    async def on_timeout(self):
        self.clear_items()
        if self.finish:
            await self.ctx.edit(view=self)
        else:
            await self.ctx.edit(content="分集选择菜单已超时", view=self)
        console_message_log(self.ctx, f"{self.occur_time}生成的搜索选择菜单已超时"
                                      f"(超时时间为{self.timeout}秒)")


class CheckBiliCollectionView(View):

    def __init__(self, ctx, info_dict, timeout=10):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.info_dict = info_dict
        self.occur_time = str(datetime.datetime.now())[11:19]
        self.finish = False

    @discord.ui.button(label="确定", style=discord.ButtonStyle.grey,
                       custom_id="button_confirm")
    async def button_confirm_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.finish = True
        message = "这是一个合集, 请选择要播放的视频:\n"
        counter = 1
        for item in self.info_dict["ugc_season"]["sections"][0]["episodes"]:
            ep_num = counter
            ep_title = item["title"]
            ep_duration = \
                convert_duration_to_time(item["arc"]["duration"])
            message = message + f"    **[{ep_num}]** {ep_title}  " \
                                f"[{ep_duration}]\n"
            counter += 1

        menu_list = make_menu_list_10(message)
        view = EpisodeSelectView(self.ctx, "bili_collection", self.info_dict,
                                 menu_list)
        await self.ctx.send(f"{menu_list[0]}\n第[1]页，共["
                            f"{len(menu_list)}]页\n已输入：",
                            view=view)

        await msg.edit_message(view=self)
        await self.ctx.delete()

    @discord.ui.button(label="取消", style=discord.ButtonStyle.grey,
                       custom_id="button_cancel")
    async def button_cancel_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.finish = True
        self.clear_items()
        await msg.edit_message(view=self)
        await self.ctx.delete()

    async def on_timeout(self):
        if not self.finish:
            await self.ctx.delete()
        console_message_log(self.ctx, f"{self.occur_time}生成的合集查看选择栏已超时"
                                      f"(超时时间为{self.timeout}秒)")

