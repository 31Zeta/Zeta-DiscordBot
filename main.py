import discord
import os
import asyncio
import datetime
from discord.ext import commands
from discord.ui import Button, View
from playlist_class import Playlist
from bilibili_dl import bili_audio_download, bili_get_bvid
import ytb_dl
from youtubesearchpython import VideosSearch
import tools

# pip install -U git+https://github.com/Pycord-Development/pycord
# pip install bilibili-api
# pip install yt-dlp
# pip install youtube-search-python


system_option = 1  # Windows -0 | Linux -1

client = discord.Client()

if system_option == 1:
    command_prefix = "\\"
    ffmpeg_path = "./bin/ffmpeg"
    token_name = "token.txt"
else:
    command_prefix = "."
    ffmpeg_path = "./bin/ffmpeg.exe"
    token_name = "test_token.txt"


# 设定指令前缀符，关闭默认Help指令
bot = commands.Bot(command_prefix=f'{command_prefix}', help_command=None)

# 检测与创建downloads文件夹
if not os.path.exists('./downloads'):
    os.mkdir('downloads')
    print('创建downloads文件夹')

# 用于储存不同服务器的播放列表的字典
playlist_dict = {}


# 启动提示
@bot.event
async def on_ready():
    print("\n---------- 准备就绪 ----------")
    print(f"成功以 {bot.user} 的身份登录")
    current_time = str(datetime.datetime.now())[:19]
    print("登录时间: " + current_time + "\n")

    # 设置机器人状态
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, name="B站和油管的音乐"))


@bot.event
async def on_message(message):
    """
    当检测到消息时调用

    :param message:频道中的消息
    :return:
    """
    if message.author == bot.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

    if message.content.startswith('32Zeta'):
        await message.channel.send('在!')

    if message.content.startswith('草'):
        await message.channel.send('草')

    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    """
    指令报错时发送提示

    :param ctx: 指令原句
    :param error: 错误
    :return:
    """
    # 指令报错提示
    if isinstance(error, commands.CommandNotFound):
        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f" 位置:{ctx.guild}\n    用户 " +
              str(ctx.author) + " 发送未知指令 " +
              ctx.message.content + "\n")

        await ctx.send("未知指令\n使用 \\help 查询可用指令")

    else:
        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f" 位置:{ctx.guild}\n    用户 " + str(ctx.author) +
              " 发送指令 " + ctx.message.content + "\n发生错误如下: ")
        await ctx.send("发生未知错误")
        raise error


@bot.command()
async def help(ctx):
    """
    覆盖掉原有help指令, 向频道发送指令列表

    :param ctx: 指令原句
    :return:
    """
    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置:{ctx.guild}\n    用户 " + str(ctx.author) +
          " 发送指令 \\help\n")

    await ctx.send(">>> **指令列表：**\n"
                   "前缀符为反斜杠 \\\n "
                   "    **join**\n            "
                   "- 让32Zeta加入指令发送者所在的语音频道\n"
                   "    **leave**\n            "
                   "- 让32Zeta离开语音频道\n"
                   "    **p** ***URL***\n"
                   "    **play** ***URL***\n            "
                   "- 播放对应B站URL视频的音频(不输入URL则恢复播放)\n"
                   "    **skip**\n            "
                   "- 跳过当前歌曲\n"
                   "    **skip** ***A***\n            "
                   "- 跳过第{A}首歌曲 (A为星号或者all时清空播放列表)\n"
                   "    **skip** ***A B***\n            "
                   "- 跳过第{A}首到第{B}首歌曲\n"
                   "    **pause**\n            "
                   "- 暂停播放\n"
                   "    **resume**\n            "
                   "- 恢复播放\n"
                   "    **list**\n            "
                   "- 发送当前服务器播放列表\n"
                   "    **clear**\n            "
                   "- 清空当前服务器播放列表\n"
                   "    **bug**\n            "
                   "- 发送当前已知的问题列表\n"
                   "    **help**\n            "
                   "- 你这不正看着呢(～￣▽￣)～\n")


@bot.command()
async def say(ctx, *message) -> None:
    """
    让机器人在当前频道发送参数message

    :param ctx: 指令原句
    :param message: 需要发送的信息
    :return:
    """
    await ctx.send(" ".join(message))


@bot.command()
async def join(ctx, channel_name="-1"):
    """
    让机器人加入指令发送者所在的语音频道并发送提示\n
    如果机器人已经加入一个频道则转移到新频道并发送提示
    如发送者未加入任何语音频道则发送提示

    :param ctx: 指令原句
    :param channel_name: 要加入的频道名称
    :return:
    """
    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置:{ctx.guild}\n    用户 " + str(ctx.author) +
          " 发送指令 " + ctx.message.content + "\n")

    if channel_name == "-1" and not ctx.author.voice:
        await ctx.reply("你未加入任何语音频道")
        return False

    elif ctx.guild.voice_client is not None:
        if channel_name == "-1":
            channel = ctx.author.voice.channel
        else:
            channel = "-1"
            for ch in ctx.guild.channels:
                if ch.type is discord.ChannelType.voice and \
                        ch.name == channel_name:
                    channel = ch

            if channel == "-1":
                await ctx.reply("无效的语音频道名称")
                return False

        voice_client = ctx.guild.voice_client
        await ctx.guild.voice_client.move_to(channel)

        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f" 位置:{ctx.guild}\n    32Zeta从频道 "
                             f"{voice_client.channel} 转移到了 "
                             f"{channel.name}")

        await ctx.send(f"转移频道: ***{voice_client.channel}*** -> "
                       f"***{channel.name}***")
        return True

    else:
        if channel_name == "-1":
            channel = ctx.author.voice.channel
        else:
            channel = "-1"
            for ch in ctx.guild.channels:
                if ch.type is discord.ChannelType.voice and \
                        ch.name == channel_name:
                    channel = ch

            if channel == "-1":
                await ctx.reply("无效的语音频道名称")
                return False

        await channel.connect()

        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f" 位置:{ctx.guild}\n    32Zeta加入频道 "
                             f"{channel.name}\n")

        await ctx.send(f"加入语音频道 -> ***{channel.name}***")
        return True


@bot.command()
async def leave(ctx):
    """
    让机器人离开语音频道并发送提示

    :param ctx: 指令原句
    :return:
    """
    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置:{ctx.guild}\n    用户 " + str(ctx.author) +
          " 发送指令 " + ctx.message.content + "\n")

    if ctx.guild.voice_client is not None:
        voice_client = ctx.guild.voice_client
        last_channel = voice_client.channel
        await voice_client.disconnect()

        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f" 位置:{ctx.guild}\n    32Zeta离开频道 "
                             f"{last_channel}\n")

        await ctx.send(f"离开语音频道: ***{last_channel}***")

    else:
        await ctx.send("32Zeta没有连接到任何语音频道")


@bot.command()
async def p(ctx, url_1="-1", *url_2):
    """play方法别名"""
    url = url_1 + " ".join(url_2)
    await play(ctx, url)


@bot.command()
async def play(ctx, url_1="-1", *url_2):
    """
    使机器人下载目标BV号音频后播放并将其标题与文件路径记录进当前服务器的播放列表\n
    播放结束后调用play_next\n
    如果当前有歌曲正在播放，则将下载目标音频并将其标题与文件路径记录进当前服务器的播放列表

    :param ctx: 指令原句
    :param url_1: 目标URL
    :return:
    """
    url = url_1 + " ".join(url_2)
    voice_client = ctx.guild.voice_client

    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置:{ctx.guild}\n    用户 " + str(ctx.author) +
          " 发送指令 " + ctx.message.content + "\n")

    if ctx.guild.id not in playlist_dict:
        temp_list = Playlist()
        playlist_dict[ctx.guild.id] = temp_list
        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f"\n    创建 {ctx.guild} 的播放列表\n")
        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f"\n    开始初始化downloads文件夹\n")
        await delete_all_temps(ctx)
        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f"\n    初始化downloads文件夹完成\n")

    if ctx.guild.voice_client is None:
        result = await join(ctx)
        if not result:
            return
        await play(ctx, url)

    elif url == "-1":
        await resume(ctx)

    # 没有歌曲正在播放的情况
    elif playlist_dict[ctx.guild.id].is_empty():

        loading_msg = ctx.message

        # 检查输入的URL属于哪个网站
        source = tools.check_url_source(url)
        title = "-1"
        path = "-1"
        duration = "-1"

        if source == "else":
            await search(ctx, url)

        else:
            if source == "bvid":
                bvid = url
                loading_msg = await ctx.send("正在加载Bilibili歌曲")
                title, path, duration = await bili_audio_download(bvid)
                playlist_dict[ctx.guild.id].add_song(title, path, duration)

            elif source == "bvid_url":
                loading_msg = await ctx.send("正在加载Bilibili歌曲")
                bvid = bili_get_bvid(url)

                if bvid == "error_bvid":
                    await ctx.send("无效的Bilibili链接")
                    return

                title, path, duration = await bili_audio_download(bvid)
                playlist_dict[ctx.guild.id].add_song(title, path, duration)

            elif source == "ytb_url":
                loading_msg = await ctx.send("正在加载Youtube歌曲")
                url_type, info_dict = ytb_dl.ytb_get_info(url)

                if url_type == "single":
                    title, path, duration = \
                        ytb_dl.ytb_audio_download(url, info_dict)
                    playlist_dict[ctx.guild.id].add_song(title, path, duration)

                else:
                    loading_msg_2 = await ctx.send("加载Youtube播放列表所需时间较长，请稍等")
                    title_list, path_list, duration_list = \
                        ytb_dl.ytb_audio_download_list(url, info_dict)

                    total_duration = 0
                    for i in range(len(title_list)):
                        playlist_dict[ctx.guild.id].add_song(
                            title_list[i], path_list[i], duration_list[i])
                        total_duration += duration_list[i]

                    total_duration = \
                        tools.convert_duration_to_time(total_duration)
                    await ctx.send(f"**{len(title_list)}** 首歌已加入播放列表\n"
                                   f"总时长 -> {total_duration}")
                    await loading_msg_2.delete()

                    title = title_list[0]
                    path = path_list[0]
                    duration = duration_list[0]

            duration = tools.convert_duration_to_time(duration)

            voice_client.play(
                discord.FFmpegPCMAudio(
                    executable=ffmpeg_path, source=path),
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    play_next(ctx, title, path), client.loop))

            current_time = str(datetime.datetime.now())[:19]
            print(current_time + f" 位置:{ctx.guild}\n    "
                                 f"开始播放: {title}  {duration}\n"
                                 f"    播放路径: {path}\n")

            await ctx.send(f"正在播放: **{title}  {duration}**")
            await loading_msg.delete()

    # 有歌曲正在播放的情况
    else:

        loading_msg = ctx.message

        # 检查输入的URL属于哪个网站
        source = tools.check_url_source(url)
        title = "-1"
        path = "-1"
        duration = "-1"

        # 下载目标歌曲
        if source == "else":
            await search(ctx, url)

        else:
            if source == "bvid":
                bvid = url
                loading_msg = await ctx.send("正在加载Bilibili歌曲")
                title, path, duration = await bili_audio_download(bvid)
                playlist_dict[ctx.guild.id].add_song(title, path, duration)

            elif source == "bvid_url":
                loading_msg = await ctx.send("正在加载Bilibili歌曲")
                bvid = bili_get_bvid(url)

                if bvid == "error_bvid":
                    await ctx.send("无效的Bilibili链接")
                    return

                title, path, duration = await bili_audio_download(bvid)
                playlist_dict[ctx.guild.id].add_song(title, path, duration)

            elif source == "ytb_url":
                loading_msg = await ctx.send("正在加载Youtube歌曲")
                url_type, info_dict = ytb_dl.ytb_get_info(url)

                if url_type == "single":
                    title, path, duration = \
                        ytb_dl.ytb_audio_download(url, info_dict)
                    playlist_dict[ctx.guild.id].add_song(title, path, duration)

                else:
                    loading_msg_2 = await ctx.send("加载Youtube播放列表所需时间较长，请稍等")
                    title_list, path_list, duration_list = \
                        ytb_dl.ytb_audio_download_list(url, info_dict)

                    total_duration = 0
                    for i in range(len(title_list)):
                        playlist_dict[ctx.guild.id].add_song(
                            title_list[i], path_list[i], duration_list[i])
                        total_duration += duration_list[i]

                    total_duration = \
                        tools.convert_duration_to_time(total_duration)
                    await ctx.send(f"**{len(title_list)}** 首歌已加入播放列表\n"
                                   f"总时长 -> {total_duration}")
                    await loading_msg_2.delete()
                    return

            duration = tools.convert_duration_to_time(duration)

            await ctx.send(f"已加入播放列表: **{title}  {duration}**")
            await loading_msg.delete()


async def play_next(ctx, last_title, last_path):
    """
    播放下一首歌曲

    :param ctx: 指令原句
    :param last_title: 上一首歌曲的标题
    :param last_path: 上一首歌曲的路径
    :return:
    """
    voice_client = ctx.guild.voice_client

    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置:{ctx.guild}\n    触发调用 play_next\n"
                         f"    剩余歌曲数:{playlist_dict[ctx.guild.id].size()}\n")

    if playlist_dict[ctx.guild.id].size() > 1:
        # 从播放列表中删除当前歌曲，返回下一歌曲
        next_song = playlist_dict[ctx.guild.id].next_song()
        title = next_song[0]
        path = next_song[1]
        duration = tools.convert_duration_to_time(next_song[2])

        # 删除上一首歌的缓存文件
        await delete_temp(ctx, last_title, last_path)

        voice_client.play(
            discord.FFmpegPCMAudio(
                executable=ffmpeg_path, source=path),
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx, title, path), client.loop))

        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f" 位置:{ctx.guild}\n    开始播放: {title}\n"
                             f"    播放路径: {path}\n")

        await ctx.send(f"正在播放: **{title}  {duration}**")

    else:
        playlist_dict[ctx.guild.id].remove_current()
        await delete_temp(ctx, last_title, last_path)

        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f" 位置:{ctx.guild}\n    {ctx.guild} 播放队列已结束\n")

        await ctx.send("播放队列已结束")


@bot.command()
async def skip(ctx, num1="-1", num2="-1"):
    """
    使机器人跳过指定的歌曲，并删除对应歌曲的文件

    :param ctx: 指令原句
    :param num1: 跳过起始曲目的序号
    :param num2: 跳过最终曲目的序号
    :return:
    """
    voice_client = ctx.guild.voice_client

    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置:{ctx.guild}\n    用户 " + str(ctx.author) +
          " 发送指令 " + ctx.message.content + "\n")

    # 不输入参数的情况
    if num1 == "-1" and num2 == "-1":
        title = playlist_dict[ctx.guild.id].peek_title()
        current_time = str(datetime.datetime.now())[:19]
        print(current_time +
              f" 位置:{ctx.guild}\n    第1首歌曲 {title} 已被移出播放队列\n")
        voice_client.stop()
        await ctx.send(f"已跳过当前歌曲  **{title}**")

    # 不输入第2个参数的情况
    elif num2 == "-1":

        if num1 == "*" or num1 == "all" or num1 == "All" or num1 == "ALL":
            await clear(ctx)

        elif int(num1) == 1:
            title = playlist_dict[ctx.guild.id].peek_title()
            current_time = str(datetime.datetime.now())[:19]
            print(current_time +
                  f" 位置:{ctx.guild}\n    第1首歌曲 {title} 已被移出播放队列\n")
            voice_client.stop()
            await ctx.send(f"已跳过当前歌曲  **{title}**")

        else:
            num1 = int(num1)
            title = playlist_dict[ctx.guild.id].peek_title(num1)
            path = playlist_dict[ctx.guild.id].peek_path(num1)
            playlist_dict[ctx.guild.id].remove_select(num1)
            await ctx.send(f"第{num1}首歌曲 **{title}** 已被移出播放列表")
            current_time = str(datetime.datetime.now())[:19]
            print(current_time +
                  f" 位置:{ctx.guild}\n    第{num1}首歌曲 {title} 已被移出播放队列\n")
            await delete_temp(ctx, title, path)

    # 两个参数都输入的情况
    elif int(num1) < int(num2):
        num1 = int(num1)
        num2 = int(num2)
        if num1 == 1:
            message = f"以下歌曲(第{num1}首至第{num2}首)已被移出播放列表: \n" \
                      f"        - **" + \
                      playlist_dict[ctx.guild.id].peek_title(num1) + "**\n"
            for i in range(num2, num1, -1):
                message = message + "       - **" + \
                          playlist_dict[ctx.guild.id].peek_title(num1 + 1) + \
                          "**\n"
                current_title = playlist_dict[ctx.guild.id].peek_title()
                title = playlist_dict[ctx.guild.id].peek_title(num2)
                path = playlist_dict[ctx.guild.id].peek_path(num2)
                playlist_dict[ctx.guild.id].remove_select(num2)
                current_time = str(datetime.datetime.now())[:19]
                print(current_time +
                      f" 位置:{ctx.guild}\n    第{num1}首歌曲 {title} 已被移出播放队列\n")
                await delete_temp(ctx, title, path, current_title)

            title = playlist_dict[ctx.guild.id].peek_title()
            current_time = str(datetime.datetime.now())[:19]
            print(current_time +
                  f" 位置:{ctx.guild}\n    第1首歌曲 {title} 已被移出播放队列\n")
            voice_client.stop()
            await ctx.send(message)

        else:
            message = f"以下歌曲(第{num1}首至第{num2}首)已被移出播放列表: \n"
            for i in range(num1 - 1, num2):
                message = message + "        - **" + \
                          playlist_dict[ctx.guild.id].peek_title(num1) + "**\n"
                title = playlist_dict[ctx.guild.id].peek_title(num1)
                path = playlist_dict[ctx.guild.id].peek_path(num1)
                playlist_dict[ctx.guild.id].remove_select(num1)
                current_time = str(datetime.datetime.now())[:19]
                print(current_time +
                      f" 位置:{ctx.guild}\n    第{num1}首歌曲 {title} 已被移出播放队列\n")
                await delete_temp(ctx, title, path)
            await ctx.send(message)

    else:
        await ctx.send("参数错误")


@bot.command()
async def search(ctx, *input_name):

    name = " ".join(input_name)
    options = []
    search_result = VideosSearch(name, limit=5)
    info_dict = dict(search_result.result())['result']

    message = f"Youtube搜索 **{name}** 结果为:\n"

    counter = 1
    for video in info_dict:

        title = video["title"]
        video_id = video["id"]
        duration = video["duration"]

        options.append([title, video_id, duration])
        message = message + f"**[{counter}]** {title}  [{duration}]\n"

        counter += 1

    message = message + "\n请选择: "
    print(options)

    await ctx.send(message, view=SongSelectView(ctx, options))


class SongSelectView(View):

    def __init__(self, ctx, options):
        super().__init__()
        self.ctx = ctx
        self.options = options

    @discord.ui.button(label="1", style=discord.ButtonStyle.grey,
                       custom_id="button_1")
    async def button_1_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已选择[1]", view=self)
        await play(
            self.ctx, f"https://www.youtube.com/watch?v={self.options[0][1]}")

    @discord.ui.button(label="2", style=discord.ButtonStyle.grey,
                       custom_id="button_2")
    async def button_2_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已选择[2]", view=self)
        await play(
            self.ctx, f"https://www.youtube.com/watch?v={self.options[1][1]}")

    @discord.ui.button(label="3", style=discord.ButtonStyle.grey,
                       custom_id="button_3")
    async def button_3_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已选择[3]", view=self)
        await play(
            self.ctx, f"https://www.youtube.com/watch?v={self.options[2][1]}")

    @discord.ui.button(label="4", style=discord.ButtonStyle.grey,
                       custom_id="button_4")
    async def button_4_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已选择[4]", view=self)
        await play(
            self.ctx, f"https://www.youtube.com/watch?v={self.options[3][1]}")

    @discord.ui.button(label="5", style=discord.ButtonStyle.grey,
                       custom_id="button_5")
    async def button_5_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已选择[5]", view=self)
        await play(
            self.ctx, f"https://www.youtube.com/watch?v={self.options[4][1]}")


@bot.command()
async def pause(ctx):
    """
    暂停播放

    :param ctx: 指令原句
    :return:
    """
    voice_client = ctx.guild.voice_client

    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置:{ctx.guild}\n    用户 " + str(ctx.author) +
          " 发送指令 " + ctx.message.content + "\n")

    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send("暂停播放")

    else:
        await ctx.send("未在播放任何音乐")


@bot.command()
async def stop(ctx):
    """pause方法别名"""
    voice_client = ctx.guild.voice_client
    voice_client.stop()


@bot.command()
async def resume(ctx):
    """
    恢复播放

    :param ctx: 指令原句
    :return:
    """
    voice_client = ctx.guild.voice_client

    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置:{ctx.guild}\n    用户 " + str(ctx.author) +
          " 发送指令 " + ctx.message.content + "\n")

    if voice_client.is_paused():
        voice_client.resume()
        await ctx.send("恢复播放")

    else:
        await ctx.send("当前没有任何被暂停的音乐")


@bot.command()
async def list(ctx):
    """
    将当前服务器播放列表发送到服务器文字频道中

    :param ctx: 指令原句
    :return:
    """
    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置:{ctx.guild}\n    用户 " + str(ctx.author) +
          " 发送指令 " + ctx.message.content + "\n")

    if ctx.guild.id not in playlist_dict:
        await ctx.send("当前播放列表为空")
    elif playlist_dict[ctx.guild.id].is_empty():
        await ctx.send("当前播放列表为空")
    else:
        await ctx.send(">>> **播放列表**\n\n" +
                       playlist_dict[ctx.guild.id].print_list())


@bot.command()
async def clear(ctx):
    """
    清空当前服务器的播放列表

    :param ctx: 指令原句
    :return:
    """
    voice_client = ctx.guild.voice_client

    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置:{ctx.guild}\n    用户 " + str(ctx.author) +
          " 发送指令 " + ctx.message.content + "\n")

    current_title = playlist_dict[ctx.guild.id].peek_title()
    # 先删除除正在播放的歌以外的歌，正在播放的歌由stop触发play_next删除
    playlist_dict[ctx.guild.id].remove_all(current_title)
    await delete_all_temps(ctx, current_title + ".mp3")
    voice_client.stop()
    await ctx.send("播放列表已清空")


async def shutdown(ctx):
    """
    登出机器人

    :param ctx: 指令原句
    :return:
    """
    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置:{ctx.guild}\n    用户 " + str(ctx.author) +
          " 发送指令 " + ctx.message.content + "\n")

    await ctx.send("32Zeta已登出")
    await ctx.bot.logout()


@bot.command()
async def test_ctx(ctx, target=-1):
    print(f'用户 {ctx.author} 尝试发送 {target}')
    print("ctx: ", ctx)
    print("ctx.guild: ", ctx.guild)
    print("ctx.author: ", ctx.author)
    print("ctx.message.content: ", ctx.message.content)
    print("ctx.message: ", ctx.message)


@bot.command()
async def is_repeat(ctx, title) -> bool:
    """
    检查playlist中是否有与path相同路径的歌曲

    :param ctx: 指令原句
    :param title: 被检测歌曲文件的标题
    :return:
    """
    counter = 1
    for guild_id in playlist_dict:
        for song_info in playlist_dict[guild_id]:
            if song_info[0] == title:
                counter += 1

    if counter > 1:
        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f" 位置:{ctx.guild}\n    触发歌曲重复检测, 目标:{title}"
                             f"\n    计数器:{counter}  结论: 有重复\n")
        return True
    else:
        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f" 位置:{ctx.guild}\n    触发歌曲重复检测, 目标:{title}"
                             f"\n    计数器:{counter}  结论: 无重复\n")
        return False


@bot.command()
async def bug(ctx):
    """
    向当前频道发送已知的BUG

    :param ctx: 指令原句
    :return:
    """
    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置:{ctx.guild}\n    用户 " + str(ctx.author) +
          " 发送指令 " + ctx.message.content + "\n")

    try:
        with open("./logs/bugs.txt", encoding="utf-8", mode="r") as bugs_file:
            lines = bugs_file.readlines()
            message = ""
            for line in lines:
                message = message + line
            if message == "" or message == "\n":
                message = "    无"
            await ctx.send("```目前已知的问题: \n\n" + message + "```")
    except FileNotFoundError:
        await ctx.send("```目前已知的问题: \n\n    无```")


@bot.command()
async def print_dict(ctx):
    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置:{ctx.guild}\n    用户 " + str(ctx.author) +
          " 发送指令 " + ctx.message.content)
    print(playlist_dict)
    print()


async def delete_temp(ctx, title, path, exception="-1"):
    """
    如果没有重复则删除指定文件\n
    调用is_repeat检测全部播放列表中是否有相同的歌曲\n

    exception是为正在播放的音乐准备的，因为正在播放的音乐由play_next触发进行删除\n

    *注意*: 一定先将歌曲从播放队列中移出后再删除文件，因为移出队列后is_repeat才能检测出正确的结果\n

    :param ctx: 指令原句
    :param title: 指定文件的标题
    :param path: 指定文件的路径
    :param exception: 不删除的文件名称
    :return:
    """
    # print("title:", title)
    # print("exception:", exception)
    # print("file == exception:", title == exception, "\n")
    if not await is_repeat(ctx, title) and not title == exception:
        os.remove(path)
        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f" 位置:{ctx.guild}\n    文件 {title} 已被删除\n")
    else:
        pass


async def delete_all_temps(ctx, exception="-1"):
    """
    删除downloads文件夹下全部没有重复的mp3文件\n
    调用is_repeat检测全部播放列表中是否有相同的歌曲\n

    exception是为正在播放的音乐准备的，因为正在播放的音乐由play_next触发进行删除\n

    *注意*: 一定先将歌曲从播放队列中移出后再删除文件，因为移出队列后is_repeat才能检测出正确的结果\n

    :param ctx: 指令原句
    :param exception: 不删除的文件名称
    :return:
    """

    message = f" 位置:{ctx.guild}\n    所有mp3文件已被删除\n"
    for folder, sub_folder, files in os.walk('./downloads/'):
        for file in files:
            # print("file:", file)
            # print("exception:", exception)
            # print("file == exception:", file == exception, "\n")
            if (file.endswith(".mp3") or file.endswith(".webm")) and \
                    not await is_repeat(ctx, file) and not file == exception:
                message = message + f"        - {file}\n"
                os.remove(f'./downloads/{file}')

    current_time = str(datetime.datetime.now())[:19]
    message = current_time + message
    print(message)


# -------------------- 测试区域 --------------------

# -------------------------------------------------

# ------------------ 代码保留区域 ------------------
class SongOptionButton(Button):

    def __init__(self, ctx, song_id, row):

        super().__init__(
            label=f"[{row}]", style=discord.ButtonStyle.grey)
        self.ctx = ctx
        self.song_id = song_id

    async def callback(self, interaction):
        await play(self.ctx, f"https://www.youtube.com/watch?v={self.song_id}")
# -------------------------------------------------


try:
    with open(f'./{token_name}', 'r') as token_file:
        token = token_file.readline()
except FileNotFoundError:
    print("未能找到机器人令牌文件")

bot.run(token)
print(f"----------程序结束----------")
