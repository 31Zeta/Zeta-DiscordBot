# Zeta Discord 机器人
中文 | [English](docs/README_en.md)  

一个基于Pycord的Discord机器人  
作者目前业余编程，如有不规范的地方请多多包涵与指教  

目前机器人只有中文可用  

目录 Table of contents
------------------------
- [核心功能](#核心功能)
- [运行](#运行)
- [为 go-music-api 配置 Cookie](#为-go-music-api-配置-Cookie)

## 核心功能
- 在Discord音频频道中使用 [go-music-api](https://github.com/guohuiyuan/go-music-api) 作为后端下载并播放来自多个平台的音乐或音频（哔哩哔哩、网易云音乐、QQ音乐 等等）
- 在Discord音频频道中播放来自YouTube的音频
- 直接在Discord频道内进行哔哩哔哩或YouTube搜索并播放
- 可交互的播放列表

![Demo_Play](docs/Demo_Play.gif)

![Demo_Playlist](docs/Demo_Playlist.gif)
![Demo_List](docs/Demo_List.gif)

## 运行
**请使用Python 3.10-3.13版本**

### 源码下载与依赖安装
请从 **[release](https://github.com/31Zeta/Zeta-DiscordBot/releases)** 中下载最新版本源码解压
  
在解压后的源码根目录下使用以下指令来安装依赖包：  
```
 pip install -r requirements.txt
```

Linux系统还需要安装：  
```
sudo apt install libopus0
```

### 部署 go-music-api
请参考 [go-music-api](https://github.com/guohuiyuan/go-music-api#快速开始) 部署go-music-api，并在稍后启动机器人时在设置内填入部署完毕后的URL，通常来讲为默认的 http://localhost:8080

### 安装或链接 FFmpeg
Windows系统请前往 [FFmpeg官网](https://ffmpeg.org/download.html) 获取ffmpeg.exe 或 [直接下载](https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z) 后解压bin文件夹内的ffmpeg.exe  
  
Linux系统可使用bin文件夹内自带的ffmpeg或前往 [FFmpeg官网](https://ffmpeg.org/download.html) 获取最新版ffmpeg  

将解压出的ffmpeg文件放入库中的bin文件夹内

### 启动
输入以下命令以运行机器人：  
```
python main.py
```

根据提示完成设置，保持窗口打开以确保机器人正常运行  
考虑使用守护进程避免机器人意外关闭  

### 修改设置
如需修改设置，则使用以下命令启动机器人（0.7.0及更高版本）：
```
python main.py --mode=setting
```  

### [额外] yt-dlp 配置
如果需要使用机器人的YouTube相关功能推荐为`yt-dlp-ejs`启用JavaScript运行环境。
`yt-dlp-ejs`已经包含在了`requirements.txt`的`yt-dlp[default]`中，会在安装依赖包时自动安装。环境的选择与安装可以参考此页面：[Step 1: Install a supported JavaScript Runtime](https://github.com/yt-dlp/yt-dlp/wiki/EJS#step-1-install-a-supported-javascript-runtime)  


## 为 go-music-api 配置 Cookie
**注意：配置 Cookie 后，无论对机器人发出指令的用户是谁，所有由 go-music-api 负责的音频下载都会使用对应的登录账户进行请求，请自行斟酌并承担可能带来的账户风险**

绝大部分平台都需要登录后才能访问大部分资源，可以为 go-music-api 配置 Cookie 来达成此效果，有以下几种方式
- 直接为 go-music-api 服务配置 Cookie，参考 [Cookie配置](https://github.com/guohuiyuan/go-music-api#cookie-配置)
- 为浏览器安装 Cookie 获取插件，登录对应平台后，从插件处复制JSON格式的 Cookie 粘贴到 ``本项目根目录/data/cookies/对应平台.json`` 文件中（如果没有目录请先启动一次机器人）  
机器人会将 Cookie 传到 go-music-api 部署根目下的 ``cookies.json`` 中
- 使用 ``python go_music_qr_login.py``，根据提示扫描登录，登录后的 Cookie会保存在 ``本项目根目录/data/cookies/对应平台.json`` 文件中，并传到 go-music-api 部署根目下的 ``cookies.json`` 中