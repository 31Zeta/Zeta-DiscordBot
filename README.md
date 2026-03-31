# Zeta Discord 机器人
一个基于Pycord的Discord机器人  
作者目前业余编程，如有不规范的地方请多多包涵与指教  

目前机器人只有中文可用  
The display language currently available for this robot is Chinese only.  

目录 Table of contents
------------------------
- [核心功能](#核心功能)
- [如何安装并部署](#如何安装并部署)
- [Core Features](#core-features)
- [How to install and deploy](#how-to-install-and-deploy)

## 核心功能
- 在Discord音频频道中播放来自哔哩哔哩视频的声音
- 在Discord音频频道中播放来自YouTube视频的声音
- 在Discord音频频道中播放来自网易云音乐的音频
- 直接在Discord频道内进行哔哩哔哩或YouTube搜索并播放
- 可交互的播放列表

## 如何安装并部署
**请使用Python 3.10-3.13版本**

请从release中下载最新版本源码解压
  
将命令行运行目录移动至解压后的源码根目录后使用以下指令来安装依赖包：  
```
 pip install -r requirements.txt
```

如果需要使用机器人的YouTube相关功能推荐为`yt-dlp-ejs`启用JavaScript运行环境。
`yt-dlp-ejs`已经包含在了`requirements.txt`的`yt-dlp[default]`中，会在安装依赖包时自动安装。环境的选择与安装可以参考此页面中的Step 1：
https://github.com/yt-dlp/yt-dlp/wiki/EJS#step-2-install-ejs-challenge-solver-scripts
  
Windows系统请前往ffmpeg官网 https://ffmpeg.org/download.html 获取ffmpeg.exe  
（或使用 https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z 下载后解压bin文件夹内的ffmpeg.exe）  
  
Linux系统可使用库内bin文件夹内自带的ffmpeg或前往ffmpeg官网 https://ffmpeg.org/download.html 获取最新版ffmpeg  

将解压出的ffmpeg文件放入库中的bin文件夹内  

Linux系统还需要安装：  
```
sudo apt install libopus0
```

输入以下命令以运行机器人：  
```
python main.py
```

根据提示完成设置，保持窗口打开以确保机器人正常运行  
如需更改设置，则使用以下命令启动机器人（0.7.0及更高版本）：
```
python main.py --mode=setting
```  

# Zeta Discord Bot
A Discord Bot that is based on Pycord.

## Core Features
- Play Bilibili's video sound on the Discord Voice Channels
- Play YouTube's video sound on the Discord Voice Channels
- Play NetEase CloudMusic's audio on the Discord Voice Channels
- Search and play directly within the Discord channel
- Interactive playlists

## How to install and deploy
**Please use Python 3.10 - 3.13**
  
Please download the latest version of the source code from the release page and unzip it.

Change the command line working directory to the root directory and use the following command to install dependencies:
```
 pip install -r requirements.txt
```

If you need to use the bot's YouTube-related features, you should enabling the JavaScript runtime for `yt-dlp-ejs`.
`yt-dlp-ejs` is already included in `yt-dlp[default]` in the `requirements.txt` and will be installed automatically when you install the dependencies. For information on selecting and setting up the environment, refer to Step 1 on this page:
https://github.com/yt-dlp/yt-dlp/wiki/EJS#step-2-install-ejs-challenge-solver-scripts
  
Windows: please visit https://ffmpeg.org/download.html to get ffmpeg.exe
(or access https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z download and unzip it to get ffmpeg.exe in bin dir） 

Linux: Visit https://ffmpeg.org/download.html to get the most recent ffmpeg file  

Put the unzipped ffmpeg file into the bin folder.  

Linux also require：  
```
sudo apt install libopus0
```

Use the following command to start the Discord Bot:  
```
python main.py
```

Complete the setting through instructions, and keep the window open to ensure the Bot is running.
 
To change the setting, please use the following command: 
```
python main.py --mode=setting
```
