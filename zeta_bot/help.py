import discord
from discord.ui import View


class HelpMenu:
    def __init__(self):
        self.version = "0.10.0"
        self.catalog = f">>> **帮助菜单目录 [版本 {self.version}]**\n\n" \
                       f"[1] 基础操作\n\n" \
                       f"[2] 音频播放\n\n" \
                       f"[3] 播放控制\n\n" \
                       f"可通过下方按钮前往对应页面"
        self.page_1 = f">>> **基础操作相关指令**\n\n" \
                      f"输入指令时使用前缀符“/”\n\n" \
                      f"**/info**\n" \
                      f"查看当前机器人的版本与更新日期\n\n" \
                      f"**/help**\n" \
                      f"调出帮助菜单"
        self.page_2 = f">>> **音频播放相关指令**\n\n" \
                      f"**/join [A]**\n" \
                      f"让机器人加入语音频道\n" \
                      f"说明：如[A]处留空则让机器人加入指令发出者所在的语音频道，" \
                      f"否则让机器人加入名称为[A]的语音频道\n\n" \
                      f"**/leave**\n" \
                      f"让机器人离开所在的语音频道\n\n" \
                      f"**/play [A]**\n" \
                      f"让机器人在语音频道中播放音频\n" \
                      f"说明：[A]可为Youtube或Bilibili的视频链接，" \
                      f"如果[A]不为链接则会在Youtube中搜索[A]\n" \
                      f"指令别名：/p\n\n" \
                      f"**/list**\n" \
                      f"显示当前服务器的播放列表\n" \
                      f"指令别名：/l"
        self.page_3 = f">>> **播放控制相关指令**\n\n" \
                      f"**/volume [A]**\n" \
                      f"调整机器人在当前服务器语音频道的音量（音量范围0% - 200%）\n" \
                      f"说明：如果[A]处留空则显示机器人在当前服务器的音量，" \
                      f"如果[A]为up或u则提升20%音量，如果[A]为down或d则降低20%音量，" \
                      f"如果[A]为一个0-200的数字则直接将音量设置为该数字的百分比\n" \
                      f"指令别名：/v\n\n" \
                      f"**/skip [A] [B]**\n" \
                      f"跳过指定歌曲\n" \
                      f"说明：如果[A]与[B]留空则跳过当前歌曲，只填[A]则跳过第[A]首歌曲，" \
                      f"填入[A]和[B]则跳过第[A]首至第[B]首歌曲\n\n" \
                      f"**/move [A] [B]**\n" \
                      f"移动播放列表中的歌曲\n" \
                      f"说明：将第[A]首歌曲移动序号[B]的位置\n" \
                      f"指令别名：/m\n\n" \
                      f"**/pause**\n" \
                      f"暂停当前播放\n\n" \
                      f"**/resume**\n" \
                      f"恢复播放\n" \
                      f"说明：如遇到异常停止的播放可尝试用resume恢复\n" \
                      f"指令别名：/r，/restart"


class HelpMenuView(View):
    def __init__(self, ctx):
        super().__init__(timeout=180)
        self.content = HelpMenu()
        self.ctx = ctx
        self.message = None
        self.catalog = self.content.catalog

    @discord.ui.button(label="目录", style=discord.ButtonStyle.grey,
                       custom_id="button_catalog", row=1)
    async def button_catalog_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        await msg.edit_message(
            content=self.content.catalog, view=self)

    @discord.ui.button(label="基础操作", style=discord.ButtonStyle.grey,
                       custom_id="button_page_1", row=2)
    async def button_page_1_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        await msg.edit_message(
            content=self.content.page_1, view=self)

    @discord.ui.button(label="音频播放", style=discord.ButtonStyle.grey,
                       custom_id="button_page_2", row=2)
    async def button_page_2_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        await msg.edit_message(
            content=self.content.page_2, view=self)

    @discord.ui.button(label="播放控制", style=discord.ButtonStyle.grey,
                       custom_id="button_page_3", row=2)
    async def button_page_3_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        await msg.edit_message(
            content=self.content.page_3, view=self)

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.grey,
                       custom_id="button_close", row=1)
    async def button_close_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content="已关闭", view=self)
        await self.message.delete()

    async def on_timeout(self):
        self.clear_items()
        await self.ctx.edit(content="帮助菜单已超时，可通过/help再次调出帮助菜单",
                            view=self)
