import discord
from discord.ui import View


class HelpMenu:
    def __init__(self):
        self.version = "0.10.0"
        self.catalog = (
            f"## 帮助菜单目录 [版本 {self.version}]\n"
            f">>> [1] 基础操作\n\n"
            f"[2] 音频播放\n\n"
            f"[3] 播放控制\n\n"
            f"可通过下方按钮前往对应页面"
        )
        self.page_1 = (
            f"## 基础操作相关指令\n"
            f"在输入指令时，直接打出原指令名称更简单，Discord菜单会自动调出对应的本地化名称\n\n"
            f">>> **/info**\n"
            f"本地化名称：**/关于**\n"
            f"查看当前机器人的相关信息（版本与更新日期等）\n\n"
            f"**/help**\n"
            f"本地化名称：**/帮助**\n"
            f"显示帮助菜单"
        )
        self.page_2 = (
            f"## 音频播放相关指令\n"
            f"在输入指令时，直接打出原指令名称更简单，Discord菜单会自动调出对应的本地化名称\n\n"
            f">>> **/join <channel>**\n"
            f"本地化名称：**/加入语音频道**\n"
            f"让机器人加入语音频道\n"
            f"说明：如<channel>处留空则让机器人加入指令发出者所在的语音频道，否则让机器人加入选择的<channel>语音频道\n\n"
            f"**/leave**\n"
            f"本地化名称：**/离开语音频道**\n"
            f"让机器人离开所在的语音频道\n\n"
            f"**/play <link>**\n"
            f"本地化名称：**/播放**\n"
            f"让机器人在语音频道中播放音频\n"
            f"说明：<link>可为Youtube或Bilibili的视频链接，如果<link>不为链接则会搜索<link>\n\n"
            f"**/search_audio <query> <site>**\n"
            f"本地化名称：**/搜索音频**\n"
            f"在指定的网站中搜索音频，选择一个进行播放\n"
            f"说明：<query>为要搜索的名称，<site>为搜索的网站，如果<site>留空则在所有支持的网站进行搜索\n\n"
            f"**/list**\n"
            f"本地化名称：**/播放列表**\n"
            f"显示当前服务器的播放列表菜单"
        )
        self.page_3 = (
            f"## 播放控制相关指令\n\n"
            f"在输入指令时，直接打出原指令名称更简单，Discord菜单会自动调出对应的本地化名称\n\n"
            f">>> **/skip <start> <end>**\n"
            f"本地化名称：**/跳过**\n"
            f"跳过指定音频\n"
            f"说明：如果<start>与<end>留空则跳过当前播放列表的第一个音频，只填入<start>或<end>则跳过对应音频，"
            f"填入<start>和<end>则跳过两个对应音频及其之间的全部音频\n\n"
            f"**/move <from_number> <to_number>**\n"
            f"本地化名称：**/移动音频**\n"
            f"移动播放列表中的音频\n"
            f"说明：将第<from_number>个音频移动序号<to_number>的位置\n\n"
            f"**/pause**\n"
            f"本地化名称：**/暂停**\n"
            f"暂停当前播放\n\n"
            f"**/resume**\n"
            f"本地化名称：**/继续播放**\n"
            f"恢复播放\n"
            f"说明：如遇到异常停止的播放可尝试用/resume恢复\n\n"
            f"**/volume <volume_number>**\n"
            f"本地化名称：**/音量**\n"
            f"调整机器人在当前服务器语音频道的音量（音量范围0% - 200%）\n"
            f"说明：如果<volume_number>处留空则显示机器人在当前服务器的音量，"
            f"如果<volume_number>为一个0-200的数字则直接将音量设置为该数字的百分比"
        )


class HelpMenuView(View):
    def __init__(self, ctx):
        super().__init__(timeout=300)
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
