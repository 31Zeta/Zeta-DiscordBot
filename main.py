import discord
from discord.ext import commands
from discord.ui import Button, View
from bilibili_dl import *
from ytb_dl import *
from youtubesearchpython import VideosSearch
from audio_control import *
from tools import *

# pip install -U git+https://github.com/Pycord-Development/pycord
# pip install bilibili-api
# pip install yt-dlp
# pip install youtube-search-python

# -------------------- 设置 --------------------
system_option = 1  # Windows - 0 | Linux - 1
bot_activity = "音乐"
bot_activity_type = discord.ActivityType.listening
version = "v0.4.0"
update_time = "2022.03.08"
# ---------------------------------------------

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

# 初始化运行环境
current_time_main = str(datetime.datetime.now())[:19]
print("开始初始化")
if not os.path.exists("./downloads"):
    os.mkdir("downloads")
    print("创建downloads文件夹")
if not os.path.exists("./logs"):
    os.mkdir("downloads")
    print("创建logs文件夹")
if not os.path.exists("./users"):
    os.mkdir("users")
    print("创建users文件夹")
if not os.path.exists("./users/user_group.csv"):
    print("未检测到user_group文件")
# 创建本次运行日志
log_name_time = current_time_main.replace(":", "_")
with open(f"./logs/{log_name_time}.txt", "a", encoding="utf-8"):
    pass
log_path = f"./logs/{log_name_time}.txt"
# 清空下载文件夹
clear_downloads()
# 用于储存不同服务器的播放列表的字典
playlist_dict = {}
print("初始化完成\n")


def write_log(time, line):
    """
    向运行日志写入当前时间与信息

    :param time: 当前时间
    :param line: 要写入的信息
    :return:
    """
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"{time} {line}\n")


def console_message_log(ctx, message):
    """
    在控制台打印一条信息，并记录在运行日志中

    :param ctx: ctx
    :param message: 要写入的信息
    :return:
    """
    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置：{ctx.guild}\n    {message}\n")
    write_log(current_time, f"{ctx.guild} {message}")


def console_message_log_command(ctx):
    """
    在控制台打印出服务器内用户名称和该用户发出的信息，并记录在运行日志中

    :param ctx: ctx
    :return:
    """
    current_time = str(datetime.datetime.now())[:19]
    print(current_time + f" 位置：{ctx.guild}\n    用户 {ctx.author} "
                         f"发送指令 {ctx.message.content}\n")
    write_log(current_time, f"{ctx.guild} 用户 {ctx.author} "
                            f"发送指令 {ctx.message.content}")


def console_message_log_list(ctx):
    """
    在控制台打印出当前服务器的播放列表，并记录在运行日志中

    :param ctx: ctx
    :return:
    """
    # 检测总词典是否有此服务器的播放列表
    if ctx.guild.id not in playlist_dict:
        create_guild_playlist(ctx)

    current_time = str(datetime.datetime.now())[:19]
    current_list = "["
    for audio in playlist_dict[ctx.guild.id]:
        current_list = current_list + f"{audio.title} [{audio.duration_str}], "
    current_list = current_list + "]"
    print(current_time + f" 位置：{ctx.guild}\n    当前播放列表：{current_list}\n")
    write_log(current_time, f"{ctx.guild} 当前播放列表：{current_list}")


# 启动提示
@bot.event
async def on_ready():
    print(f"---------- 准备就绪 ----------\n"
          f"成功以 {bot.user} 的身份登录")
    current_time = str(datetime.datetime.now())[:19]
    print("登录时间：" + current_time + "\n")
    write_log(current_time, f"准备就绪 以{bot.user}的身份登录")

    # 设置机器人状态
    await bot.change_presence(activity=discord.Activity(
        type=bot_activity_type, name=bot_activity))


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

    if message.content.startswith('yee'):
        await message.channel.send('yee')

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
        print(current_time + f" 位置:{ctx.guild}\n    用户 {str(ctx.author)} "
                             f"发送未知指令 {ctx.message.content}\n")
        write_log(current_time, f"{ctx.guild} 用户 {str(ctx.author)} "
                                f"发送未知指令 {ctx.message.content}\n")

        await ctx.send("未知指令\n使用 \\help 查询可用指令")

    else:
        current_time = str(datetime.datetime.now())[:19]
        print(current_time + f" 位置:{ctx.guild}\n    用户 {str(ctx.author)} "
                             f"发送指令 {ctx.message.content}\n发生错误如下：")
        write_log(current_time, f"{ctx.guild} 用户 {str(ctx.author)} "
                                f"发送指令 {ctx.message.content}    "
                                f"发生错误如下：{error}\n")
        await ctx.send("发生未知错误")
        raise error


@bot.command()
async def info(ctx):
    await ctx.send(f"当前版本号为 **{version}**\n"
                   f"最后更新日期为 **{update_time}**\n"
                   f"作者：31Zeta")


@bot.command()
async def help(ctx):
    """
    覆盖掉原有help指令, 向频道发送指令列表

    :param ctx: 指令原句
    :return:
    """
    console_message_log_command(ctx)
    help_menu_page_1 = "**指令列表：**\n" \
                       "前缀符为反斜杠 \\\n" \
                       "    **info**\n            " \
                       "- 查看32Zeta的当前版本号和更新日期\n" \
                       "    **join**\n            " \
                       "- 让32Zeta加入指令发送者所在的语音频道\n" \
                       "    **join** ***A***\n            " \
                       "- 让32Zeta加入语音频道A\n" \
                       "    **leave**\n            " \
                       "- 让32Zeta离开语音频道\n" \
                       "    **play** ***名称***\n            " \
                       "- 如输入名称为Bilibili或Youtube的网页链接，则播放对应网页链接的" \
                       "音频; 如输入的为歌曲名称则将在Youtube上搜索相关前5的视频, 选择一" \
                       "首进行播放; 如不输入任何名称则恢复被暂停的播放\n"
    help_menu_page_2 = ">>>    **skip**\n            " \
                       "- 跳过当前歌曲\n" \
                       "    **skip** ***A***\n            " \
                       "- 跳过第{A}首歌曲\n" \
                       "    **skip** ***A B***\n            " \
                       "- 跳过第{A}首到第{B}首歌曲\n" \
                       "    **skip** ***all***\n            " \
                       "- 清空服务器播放列表（all可用星号代替）" \
                       "    **pause**\n            " \
                       "- 暂停播放\n" \
                       "    **resume**\n            " \
                       "- 恢复播放\n" \
                       "    **list**\n            " \
                       "- 发送当前服务器播放列表\n" \
                       "    **help**\n            " \
                       "- 你这不正看着呢(～￣▽￣)～\n"

    help_menu = [help_menu_page_1, help_menu_page_2]
    view = HelpMenu(ctx, help_menu)
    view.message = await ctx.send(
        content=help_menu_page_1 + f"\n第[1]页，共[{len(help_menu)}]页\n", view=view)


async def say(ctx, *message) -> None:
    """
    让机器人在当前频道发送参数message

    :param ctx: 指令原句
    :param message: 需要发送的信息
    :return:
    """
    console_message_log_command(ctx)
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
    console_message_log_command(ctx)

    # 指令发送者未加入频道的情况
    if channel_name == "-1" and not ctx.author.voice:
        await ctx.reply("您未加入任何语音频道")
        return False

    # 机器人已在一个语音频道的情况
    elif ctx.guild.voice_client is not None:
        # 未输入参数
        if channel_name == "-1":
            channel = ctx.author.voice.channel
        # 寻找与参数名称相同的频道
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

        console_message_log(ctx, f"从频道 {voice_client.channel} "
                                 f"转移到 {channel_name}")

        await ctx.send(f"转移频道：***{voice_client.channel}*** -> "
                       f"***{channel.name}***")
        return True

    # 机器人未在语音频道的情况
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

        console_message_log(ctx, f"加入频道 {channel.name}")

        await ctx.send(f"加入语音频道 -> ***{channel.name}***")
        return True


@bot.command()
async def leave(ctx):
    """
    让机器人离开语音频道并发送提示

    :param ctx: 指令原句
    :return:
    """
    console_message_log_command(ctx)

    if ctx.guild.voice_client is not None:
        voice_client = ctx.guild.voice_client
        last_channel = voice_client.channel
        # await clear(ctx)
        await voice_client.disconnect()

        console_message_log(ctx, f"离开频道 {last_channel}")

        await ctx.send(f"离开语音频道：***{last_channel}***")

    else:
        await ctx.send("32Zeta没有连接到任何语音频道")


def create_guild_playlist(ctx):
    if ctx.guild.id not in playlist_dict:
        temp_list = Playlist(log_path)
        playlist_dict[ctx.guild.id] = temp_list
        console_message_log(ctx, f"创建 {ctx.guild} 的播放列表")


@bot.command()
async def p(ctx, url_1="-1", *url_2):
    """play方法别名"""
    url = url_1 + " ".join(url_2)
    await play(ctx, url)


@bot.command()
async def play(ctx, url_1="-1", *url_2):
    """
    使机器人下载目标BV号音频后播放并将其标题与文件路径记录进当前服务器的播放列表
    播放结束后调用play_next
    如果当前有歌曲正在播放，则将下载目标音频并将其标题与文件路径记录进当前服务器的播放列表

    :param ctx: 指令原句
    :param url_1: 目标URL
    :return:
    """
    console_message_log_command(ctx)

    url = url_1 + " ".join(url_2)
    voice_client = ctx.guild.voice_client

    # 检测机器人是否已经加入语音频道
    if ctx.guild.voice_client is None:
        result = await join(ctx)
        if not result:
            return

    # 检测总词典是否有此服务器的播放列表
    if ctx.guild.id not in playlist_dict:
        create_guild_playlist(ctx)

    current_playlist = playlist_dict[ctx.guild.id]

    # 机器人在频道中，没有在播放，并且播放列表不为空的情况
    if voice_client is not None and not voice_client.is_playing and \
            not current_playlist.is_empty():
        path = current_playlist.get_path(0)

        voice_client.play(
            discord.FFmpegPCMAudio(
                executable=ffmpeg_path, source=path),
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx), client.loop))

        await ctx.send(f"恢复异常中断的播放列表")
        return

    elif url == "-1":
        await resume(ctx)

    # 检查输入的URL属于哪个网站
    source = check_url_source(url)
    console_message_log(ctx, f"检测输入的参数为类型：{source}")

    # URL属于Bilibili
    if source == "bili_bvid" or source == "bili_url" or \
            source == "bili_short_url":

        # 如果是Bilibili短链则获取重定向链接
        if source == "bili_short_url":
            url = get_redirect_url(url)
            console_message_log(ctx, f"获取的重定向链接为 {url}")

        # 如果是URl则转换成BV号
        if source == "bili_url" or source == "bili_short_url":
            bvid = bili_get_bvid(url)
            if bvid == "error_bvid":
                console_message_log(ctx, f"{ctx.message.content} "
                                         f"为无效的链接")
                await ctx.send("无效的Bilibili链接")
                return
        else:
            bvid = url

        # 获取Bilibili视频信息
        info_dict = await bili_get_info(bvid)

        # 单一视频 bili_single
        if info_dict["videos"] == 1 and "ugc_season" not in info_dict:
            console_message_log(ctx, f"检测 {url} 为类型：bili_single")
            loading_msg = await ctx.send("正在加载Bilibili歌曲")
            await play_bili(ctx, info_dict, "bili_single", 0)
            await loading_msg.delete()

        # 合集视频 bili_collection
        elif "ugc_season" in info_dict:
            console_message_log(ctx, f"检测 {url} 为类型：bili_collection")
            await play_bili(ctx, info_dict, "bili_single", 0)

            collection_title = info_dict["ugc_season"]["title"]
            message = f"此视频包含在合集 **{collection_title}** 中, 是否要查看此合集？\n"
            view = CheckBiliCollectionView(ctx, info_dict)
            view.message = await ctx.send(message, view=view)

        # 分P视频 bili_p
        else:
            console_message_log(ctx, f"检测 {url} 为类型：bili_p")
            message = "这是一个分p视频, 请选择要播放的分p:\n"
            for item in info_dict["pages"]:
                p_num = item["page"]
                p_title = item["part"]
                p_duration = \
                    convert_duration_to_time(item["duration"])
                message = message + f"    **[{p_num}]** {p_title}  " \
                                    f"[{p_duration}]\n"

            menu_list = make_menu_list_10(message)
            view = EpisodeSelectView(ctx, "bili_p", info_dict, menu_list)
            view.message = await ctx.send(f"{menu_list[0]}\n第[1]页，共["
                                          f"{len(menu_list)}]页\n已输入：",
                                          view=view)

    elif source == "ytb_url":

        loading_msg = await ctx.send("正在获取Youtube视频信息")
        url_type, info_dict = ytb_get_info(url)
        await loading_msg.delete()

        # 单一视频 ytb_single
        if url_type == "ytb_single":
            console_message_log(ctx, f"检测 {url} 为类型：ytb_single")
            loading_msg = await ctx.send("正在加载Youtube歌曲")
            await play_ytb(ctx, url, info_dict, "normal")
            await loading_msg.delete()

        # 播放列表 ytb_playlist
        else:
            console_message_log(ctx, f"检测 {url} 为类型：ytb_playlist")
            message = "这是一个播放列表, 请选择要播放的集数:\n"
            counter = 1
            for item in info_dict["entries"]:
                ep_num = counter
                ep_title = item["fulltitle"]
                ep_duration = \
                    convert_duration_to_time(item["duration"])
                message = message + f"    **[{ep_num}]** {ep_title}  " \
                                    f"[{ep_duration}]\n"
                counter += 1

            menu_list = make_menu_list_10(message)
            view = EpisodeSelectView(ctx, "ytb_playlist", info_dict, menu_list)
            view.message = await ctx.send(f"{menu_list[0]}\n第[1]页，共["
                                          f"{len(menu_list)}]页\n已输入：",
                                          view=view)

    else:
        await search_ytb(ctx, url)


async def play_next(ctx):
    """
    播放下一首歌曲

    :param ctx: 指令原句
    :return:
    """
    voice_client = ctx.guild.voice_client
    current_playlist = playlist_dict[ctx.guild.id]

    console_message_log(ctx, f"触发play_next")

    if current_playlist.size() > 1:
        # 从播放列表中删除当前歌曲，返回下一歌曲
        # next_song = current_playlist.next_song()
        # title = next_song[0]
        # path = next_song[1]
        # duration = convert_duration_to_time(next_song[2])

        # 删除上一首歌的缓存文件
        # await delete_temp(ctx, last_title, last_path)

        # 移除上一首歌曲
        current_playlist.remove_select(0)
        # 获取下一首歌曲
        next_song = current_playlist.get(0)
        title = next_song[0]
        path = next_song[1]
        duration = next_song[2]

        voice_client.play(
            discord.FFmpegPCMAudio(
                executable=ffmpeg_path, source=path),
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx), client.loop))

        duration = convert_duration_to_time(duration)
        console_message_log(ctx, f"开始播放：{title} [{duration}] {path}")
        console_message_log_list(ctx)

        await ctx.send(f"正在播放：**{title} [{duration}]**")

    else:
        current_playlist.remove_select(0)

        console_message_log(ctx, "播放队列已结束")

        await ctx.send("播放队列已结束")


async def play_bili(ctx, info_dict, download_type="bili_single", num_option=0):
    """
    下载并播放来自Bilibili的视频的音频

    :param ctx: 指令原句
    :param info_dict: 目标的信息字典（使用bili_getinfo提取）
    :param download_type: 下载模式（"bili_single"或"bili_p"）
    :param num_option: 下载分集号（从0开始，默认为0即合集第1视频或者第1p）
    :return: （歌曲标题，歌曲时长）
    """

    voice_client = ctx.guild.voice_client

    # 检测总词典是否有此服务器的播放列表
    if ctx.guild.id not in playlist_dict:
        create_guild_playlist(ctx)

    current_playlist = playlist_dict[ctx.guild.id]

    bvid = info_dict["bvid"]

    title, path, duration = await bili_audio_download(
        bvid, info_dict, download_type, num_option)

    duration_str = convert_duration_to_time(duration)

    # 如果当前播放列表为空
    if current_playlist.is_empty() and not voice_client.is_playing():

        voice_client.play(
            discord.FFmpegPCMAudio(
                executable=ffmpeg_path, source=path),
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx), client.loop))

        console_message_log(ctx, f"开始播放：{title} [{duration_str}] {path}")
        await ctx.send(f"正在播放：**{title} [{duration_str}]**")

    # 如果播放列表不为空
    elif download_type == "bili_single":
        await ctx.send(f"已加入播放列表：**{title} [{duration_str}]**")

    new_audio = Audio(title)
    new_audio.download_init(download_type, bvid, path, duration)
    current_playlist.add_audio(new_audio)
    console_message_log(ctx, f"歌曲 {title} [{duration_str}] 已加入播放列表")

    return title, duration


async def play_ytb(ctx, url, info_dict, download_type="ytb_single"):
    """
    下载并播放来自Youtube的视频的音频

    :param ctx: 指令原句
    :param url: 目标URL
    :param info_dict: 目标的信息字典（使用ytb_get_info提取）
    :param download_type: 下载模式（"ytb_single"或"ytb_playlist"）
    :return: （歌曲标题，歌曲时长）
    """

    voice_client = ctx.guild.voice_client

    # 检测总词典是否有此服务器的播放列表
    if ctx.guild.id not in playlist_dict:
        create_guild_playlist(ctx)

    current_playlist = playlist_dict[ctx.guild.id]

    title, path, duration = \
        ytb_audio_download(url, info_dict)

    duration_str = convert_duration_to_time(duration)

    # 如果当前播放列表为空
    if current_playlist.is_empty() and not voice_client.is_playing():

        voice_client.play(
            discord.FFmpegPCMAudio(
                executable=ffmpeg_path, source=path),
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx), client.loop))

        console_message_log(ctx, f"开始播放：{title} [{duration_str}] {path}")
        await ctx.send(f"正在播放：**{title} [{duration_str}]**")

    # 如果播放列表不为空
    elif download_type == "ytb_single":
        await ctx.send(f"已加入播放列表：**{title} [{duration_str}]**")

    new_audio = Audio(title)
    new_audio.download_init(download_type, url, path, duration)
    current_playlist.add_audio(new_audio)
    console_message_log(ctx, f"歌曲 {title} [{duration_str}] 已加入播放列表")

    return title, duration


@bot.command()
async def skip(ctx, num1="-1", num2="-1"):
    """
    使机器人跳过指定的歌曲，并删除对应歌曲的文件

    :param ctx: 指令原句
    :param num1: 跳过起始曲目的序号
    :param num2: 跳过最终曲目的序号
    :return:
    """
    console_message_log_command(ctx)

    # 检测总词典是否有此服务器的播放列表
    if ctx.guild.id not in playlist_dict:
        create_guild_playlist(ctx)

    voice_client = ctx.guild.voice_client
    current_playlist = playlist_dict[ctx.guild.id]

    if not current_playlist.is_empty():
        # 不输入参数的情况
        if num1 == "-1" and num2 == "-1":
            current_song = current_playlist.get(0)
            title = current_song[0]
            voice_client.stop()

            console_message_log(ctx, f"第1首歌曲 {title} 已被用户 {ctx.author} 移出播放队列")
            await ctx.send(f"已跳过当前歌曲  **{title}**")

        # 输入1个参数的情况
        elif num2 == "-1":

            if num1 == "*" or num1 == "all" or num1 == "All" or num1 == "ALL":
                await clear(ctx)

            elif int(num1) == 1:
                current_song = current_playlist.get(0)
                title = current_song[0]
                voice_client.stop()

                console_message_log(ctx, f"第1首歌曲 {title} "
                                         f"已被用户 {ctx.author} 移出播放队列")
                await ctx.send(f"已跳过当前歌曲  **{title}**")

            else:
                num1 = int(num1)
                select_song = current_playlist.get(num1)
                title = select_song[0]
                current_playlist.remove_select(num1)

                console_message_log(ctx, f"第{num1}首歌曲 {title} "
                                         f"已被用户 {ctx.author} 移出播放队列")
                await ctx.send(f"第{num1}首歌曲 **{title}** 已被移出播放列表")

        # 输入2个参数的情况
        elif int(num1) < int(num2):
            num1 = int(num1)
            num2 = int(num2)

            # 如果需要跳过正在播放的歌，则需要先移除除第一首歌以外的歌曲，第一首由stop()触发play_next移除
            if num1 == 1:
                for i in range(num2, num1, -1):
                    current_playlist.remove_select(i)
                voice_client.stop()

                console_message_log(ctx, f"歌曲第{num1}到第{num2}首被用户 "
                                         f"{ctx.author} 移出播放队列")
                await ctx.send(f"歌曲第{num1}到第{num2}首已被移出播放队列")

            # 不需要跳过正在播放的歌
            else:
                for i in range(num2, num1 - 1, -1):
                    current_playlist.remove_select(i)

                console_message_log(ctx, f"歌曲第{num1}到第{num2}首被用户 "
                                         f"{ctx.author} 移出播放队列")
                await ctx.send(f"歌曲第{num1}到第{num2}首已被移出播放队列")

        else:
            await ctx.send("参数错误")
            console_message_log(ctx, f"用户 {ctx.author} 的skip指令参数错误")

    else:
        await ctx.send("当前播放列表已为空")


async def search_ytb(ctx, *input_name):
    name = " ".join(input_name)
    name = name.strip()

    if name == "":
        ctx.reply("请输入要搜索的名称")
        return

    options = []
    search_result = VideosSearch(name, limit=5)
    info_dict = dict(search_result.result())['result']

    message = f"Youtube搜索 **{name}** 结果为:\n"

    counter = 1
    for result_video in info_dict:

        title = result_video["title"]
        video_id = result_video["id"]
        duration = result_video["duration"]

        options.append([title, video_id, duration])
        message = message + f"**[{counter}]** {title}  [{duration}]\n"

        counter += 1

    console_message_log(ctx, f"搜索结果为：{options}")

    message = message + "\n请选择："

    if len(info_dict) == 0:
        await ctx.send("没有搜索到任何结果")
        return

    view = SearchSelectView(ctx, options)
    view.message = await ctx.send(message, view=view)


class SearchSelectView(View):

    def __init__(self, ctx, options, timeout=30):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.options = options
        self.timeout = timeout
        self.occur_time = str(datetime.datetime.now())[11:19]

        self.finish = False

    @discord.ui.button(label="1", style=discord.ButtonStyle.grey,
                       custom_id="button_1")
    async def button_1_callback(self, button, interaction):
        button.disabled = True
        self.finish = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已选择[1]", view=self)
        console_message_log(self.ctx, "用户已选择[1]")
        download_type, info_dict = ytb_get_info(f"https://www.youtube.com/"
                                                f"watch?v={self.options[0][1]}")
        await play_ytb(
            self.ctx, f"https://www.youtube.com/watch?v={self.options[0][1]}",
            info_dict, "normal")

    @discord.ui.button(label="2", style=discord.ButtonStyle.grey,
                       custom_id="button_2")
    async def button_2_callback(self, button, interaction):
        button.disabled = True
        self.finish = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已选择[2]", view=self)
        console_message_log(self.ctx, "用户已选择[2]")
        download_type, info_dict = ytb_get_info(f"https://www.youtube.com/"
                                                f"watch?v={self.options[1][1]}")
        await play_ytb(
            self.ctx, f"https://www.youtube.com/watch?v={self.options[1][1]}",
            info_dict, "normal")

    @discord.ui.button(label="3", style=discord.ButtonStyle.grey,
                       custom_id="button_3")
    async def button_3_callback(self, button, interaction):
        button.disabled = True
        self.finish = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已选择[3]", view=self)
        console_message_log(self.ctx, "用户已选择[3]")
        download_type, info_dict = ytb_get_info(f"https://www.youtube.com/"
                                                f"watch?v={self.options[2][1]}")
        await play_ytb(
            self.ctx, f"https://www.youtube.com/watch?v={self.options[2][1]}",
            info_dict, "normal")

    @discord.ui.button(label="4", style=discord.ButtonStyle.grey,
                       custom_id="button_4")
    async def button_4_callback(self, button, interaction):
        button.disabled = True
        self.finish = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已选择[4]", view=self)
        console_message_log(self.ctx, "用户已选择[4]")
        download_type, info_dict = ytb_get_info(f"https://www.youtube.com/"
                                                f"watch?v={self.options[3][1]}")
        await play_ytb(
            self.ctx, f"https://www.youtube.com/watch?v={self.options[3][1]}",
            info_dict, "normal")

    @discord.ui.button(label="5", style=discord.ButtonStyle.grey,
                       custom_id="button_5")
    async def button_5_callback(self, button, interaction):
        button.disabled = True
        self.finish = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已选择[5]", view=self)
        console_message_log(self.ctx, "用户已选择[5]")
        download_type, info_dict = ytb_get_info(f"https://www.youtube.com/"
                                                f"watch?v={self.options[4][1]}")
        await play_ytb(
            self.ctx, f"https://www.youtube.com/watch?v={self.options[4][1]}",
            info_dict, "normal")

    @discord.ui.button(label="取消", style=discord.ButtonStyle.red,
                       custom_id="button_cancel")
    async def button_cancel_callback(self, button, interaction):
        button.disabled = True
        self.finish = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content=f"已取消", view=self)

    async def on_timeout(self):
        self.clear_items()
        if self.finish:
            await self.message.edit(view=self)
        else:
            await self.message.edit(content="已超时", view=self)
        console_message_log(self.ctx, f"{self.occur_time}生成的搜索选择栏已超时"
                                      f"(超时时间为{self.timeout}秒)")


@bot.command()
async def pause(ctx):
    """
    暂停播放

    :param ctx: 指令原句
    :return:
    """
    console_message_log_command(ctx)

    voice_client = ctx.guild.voice_client

    if voice_client is not None and voice_client.is_playing():
        if ctx.author.voice and \
                voice_client.channel == ctx.author.voice.channel:
            voice_client.pause()
            console_message_log(ctx, "暂停播放")
            await ctx.send("暂停播放")
        else:
            console_message_log(ctx, f"收到pause指令时指令发出者 {ctx.author} 不在机器人所在的频道")
            await ctx.reply("您不在32Zeta所在的频道")

    else:
        console_message_log(ctx, "收到pause指令时机器人未在播放任何音乐")
        await ctx.send("未在播放任何音乐")


@bot.command()
async def stop(ctx):
    # """pause方法别名"""
    voice_client = ctx.guild.voice_client
    voice_client.stop()


@bot.command()
async def resume(ctx):
    """
    恢复播放

    :param ctx: 指令原句
    :return:
    """
    console_message_log_command(ctx)

    voice_client = ctx.guild.voice_client
    current_playlist = playlist_dict[ctx.guild.id]

    if voice_client is not None:

        # 被暂停播放的情况
        if voice_client.is_paused():
            if ctx.author.voice and \
                    voice_client.channel == ctx.author.voice.channel:
                voice_client.resume()
                console_message_log(ctx, "恢复播放")
                await ctx.send("恢复播放")
            else:
                console_message_log(ctx, f"收到pause指令时指令发出者 {ctx.author} "
                                         f"不在机器人所在的频道")
                await ctx.reply("您不在32Zeta所在的频道")

        # 没有被暂停并且正在播放的情况
        elif voice_client.is_playing():
            console_message_log(ctx, "收到resume指令时机器人正在播放音乐")
            await ctx.send("当前正在播放音乐")

        # 没有被暂停，没有正在播放，并且播放列表中存在歌曲的情况
        elif not current_playlist.is_empty():
            path = current_playlist.get_path(0)

            voice_client.play(
                discord.FFmpegPCMAudio(
                    executable=ffmpeg_path, source=path),
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    play_next(ctx), client.loop))

            await ctx.send(f"恢复上次异常中断的播放列表")

        else:
            console_message_log(ctx, "收到resume指令时机器人没有任何被暂停的音乐")
            await ctx.send("当前没有任何被暂停的音乐")


@bot.command()
async def list(ctx):
    """
    将当前服务器播放列表发送到服务器文字频道中

    :param ctx: 指令原句
    :return:
    """
    console_message_log_command(ctx)
    console_message_log_list(ctx)

    # 检测总词典是否有此服务器的播放列表
    if ctx.guild.id not in playlist_dict:
        create_guild_playlist(ctx)

    if ctx.guild.id not in playlist_dict:
        await ctx.send("当前播放列表为空")
    elif playlist_dict[ctx.guild.id].is_empty():
        await ctx.send("当前播放列表为空")
    else:
        playlist_str, duration = playlist_dict[ctx.guild.id].get_playlist_str()
        playlist_list = make_menu_list_10(playlist_str)

        view = PlaylistMenu(ctx, playlist_list)
        view.message = await ctx.send(
            content=">>> **播放列表**\n\n" + playlist_list[0] +
                    f"\n第[1]页，共[{len(playlist_list)}]页\n", view=view)

        # await ctx.send(">>> **播放列表**\n\n" +
        #                playlist_dict[ctx.guild.id].print_list())


async def clear(ctx):
    """
    清空当前服务器的播放列表

    :param ctx: 指令原句
    :return:
    """

    # 检测总词典是否有此服务器的播放列表
    if ctx.guild.id not in playlist_dict:
        create_guild_playlist(ctx)

    voice_client = ctx.guild.voice_client
    current_playlist = playlist_dict[ctx.guild.id]

    current_song = current_playlist.get(0)
    current_song_title = current_song[0]
    # remove_all跳过正在播放的歌曲
    current_playlist.remove_all(current_song_title)
    # stop触发play_next删除正在播放的歌曲
    voice_client.stop()

    console_message_log(ctx, f"用户 {ctx.author} 已清空所在服务器的播放列表")
    await ctx.send("播放列表已清空")


async def shutdown(ctx):
    """
    登出机器人

    :param ctx: 指令原句
    :return:
    """
    console_message_log_command(ctx)

    await ctx.send("32Zeta已登出")
    await ctx.bot.logout()


@bot.command()
async def print_dict(ctx):
    console_message_log_command(ctx)
    print(playlist_dict)
    print()


class Menu(View):

    def __init__(self, ctx, menu_list, title, timeout):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.message = None
        self.menu_list = menu_list
        self.title = title
        self.page_num = 0
        self.result = []
        self.occur_time = str(datetime.datetime.now())[11:19]

    @discord.ui.button(label="上一页", style=discord.ButtonStyle.grey,
                       custom_id="button_previous")
    async def button_previous_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        # 翻页
        if self.page_num == 0:
            return
        else:
            self.page_num -= 1
        await msg.edit_message(
            content=f">>> **{self.title}**\n\n{self.menu_list[self.page_num]}\n"
                    f"第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n", view=self)

    @discord.ui.button(label="下一页", style=discord.ButtonStyle.grey,
                       custom_id="button_next")
    async def button_next_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        # 翻页
        if self.page_num == len(self.menu_list) - 1:
            return
        else:
            self.page_num += 1
        await msg.edit_message(
            content=f">>> **{self.title}**\n\n{self.menu_list[self.page_num]}\n"
                    f"第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n", view=self)

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.grey,
                       custom_id="button_close")
    async def button_close_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content="已关闭", view=self)
        await self.message.delete()

    async def on_timeout(self):
        self.clear_items()

        await self.message.delete()
        console_message_log(self.ctx, f"{self.occur_time}生成的菜单已超时"
                                      f"(超时时间为{self.timeout}秒)")


class HelpMenu(Menu):

    def __init__(self, ctx, menu_list):
        super().__init__(ctx, menu_list, "帮助菜单", 60)


class PlaylistMenu(View):

    def __init__(self, ctx, menu_list, timeout=60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.message = None
        self.menu_list = menu_list
        self.page_num = 0
        self.result = []
        self.occur_time = str(datetime.datetime.now())[11:19]

    @discord.ui.button(label="上一页", style=discord.ButtonStyle.grey,
                       custom_id="button_previous")
    async def button_previous_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        playlist_str, duration = playlist_dict[self.ctx.guild.id]. \
            get_playlist_str()
        playlist_list = make_menu_list_10(playlist_str)
        self.menu_list = playlist_list
        # 翻页
        if self.page_num == 0:
            return
        else:
            self.page_num -= 1
        await msg.edit_message(
            content=f">>> **当前播放列表**\n\n{self.menu_list[self.page_num]}\n"
                    f"第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n", view=self)

    @discord.ui.button(label="下一页", style=discord.ButtonStyle.grey,
                       custom_id="button_next")
    async def button_next_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        playlist_str, duration = playlist_dict[self.ctx.guild.id]. \
            get_playlist_str()
        playlist_list = make_menu_list_10(playlist_str)
        self.menu_list = playlist_list
        # 翻页
        if self.page_num == len(self.menu_list) - 1:
            return
        else:
            self.page_num += 1
        await msg.edit_message(
            content=f">>> **当前播放列表**\n\n{self.menu_list[self.page_num]}\n"
                    f"第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n", view=self)

    @discord.ui.button(label="刷新", style=discord.ButtonStyle.grey,
                       custom_id="button_refresh")
    async def button_refresh_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        playlist_str, duration = playlist_dict[self.ctx.guild.id].\
            get_playlist_str()
        playlist_list = make_menu_list_10(playlist_str)
        self.menu_list = playlist_list

        await msg.edit_message(
            content=f">>> **当前播放列表**\n\n{self.menu_list[self.page_num]}\n"
                    f"第[{self.page_num + 1}]页，"
                    f"共[{len(self.menu_list)}]页\n", view=self)

    @discord.ui.button(label="关闭", style=discord.ButtonStyle.grey,
                       custom_id="button_close")
    async def button_close_callback(self, button, interaction):
        button.disabled = True
        msg = interaction.response
        self.clear_items()
        await msg.edit_message(content="已关闭", view=self)
        await self.message.delete()

    async def on_timeout(self):
        self.clear_items()

        await self.message.delete()
        console_message_log(self.ctx, f"{self.occur_time}生成的播放列表菜单已超时"
                                      f"(超时时间为{self.timeout}秒)")


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
        self.message = None
        self.source = source
        self.info_dict = info_dict
        self.menu_list = menu_list
        self.page_num = 0
        self.result = []
        self.dash_finish = True
        self.occur_time = str(datetime.datetime.now())[11:19]
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
        if len(self.result) == 0:
            return
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
            await self.message.edit(view=self)
        else:
            await self.message.edit(content="已超时", view=self)
        console_message_log(self.ctx, f"{self.occur_time}生成的搜索选择栏已超时"
                                      f"(超时时间为{self.timeout}秒)")


class CheckBiliCollectionView(View):

    def __init__(self, ctx, info_dict, timeout=10):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.message = None
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
        view.message = await self.ctx.send(f"{menu_list[0]}\n第[1]页，共["
                                           f"{len(menu_list)}]页\n已输入：",
                                           view=view)

        await msg.edit_message(view=self)
        await self.message.delete()

    @discord.ui.button(label="取消", style=discord.ButtonStyle.grey,
                       custom_id="button_cancel")
    async def button_cancel_callback(self, button, interaction):
        button.disabled = False
        msg = interaction.response
        self.finish = True
        self.clear_items()
        await msg.edit_message(view=self)
        await self.message.delete()

    async def on_timeout(self):
        if not self.finish:
            await self.message.delete()
        console_message_log(self.ctx, f"{self.occur_time}生成的合集查看选择栏已超时"
                                      f"(超时时间为{self.timeout}秒)")


# -------------------- 测试区域 --------------------
@bot.command()
async def ip(ctx):
    await ctx.send(f"y or n")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        message = await bot.wait_for("message", timeout=3, check=check)
    except asyncio.TimeoutError:
        await ctx.send("timeout")
    else:
        if message.content.lower() == "y":
            await ctx.send("You said yes!")
        else:
            await ctx.send("You said no!")


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
