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
**请使用Python3.9或更高版本**

请使用以下指令将本库克隆到本地：
```
git clone https://github.com/31Zeta/Zeta-DiscordBot.git
```  
  
将命令行运行位置移动至库根目录后使用以下指令来安装依赖包：  
```
 pip install -r requirements.txt
```

或手动安装以下包：  
- py-cord https://github.com/Pycord-Development/pycord  
- APScheduler https://github.com/agronholm/apscheduler  
- bilibili-api-python https://github.com/Nemo2011/bilibili-api
- PyNaCl https://github.com/pyca/pynacl/
- requests https://github.com/psf/requests  
- yt-dlp https://github.com/yt-dlp/yt-dlp  
  
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
**Please use Python 3.9 or higher versions**
  
Please use the following commands to clone this repo to your local:
```
git clone https://github.com/31Zeta/Zeta-DiscordBot.git
```

Change the command line directory to this repo and use the following command to install dependencies:
```
 pip install -r requirements.txt
```

Or install these packages manually:
- py-cord https://github.com/Pycord-Development/pycord  
- APScheduler https://github.com/agronholm/apscheduler  
- bilibili-api-python https://github.com/Nemo2011/bilibili-api
- PyNaCl https://github.com/pyca/pynacl/
- requests https://github.com/psf/requests  
- yt-dlp https://github.com/yt-dlp/yt-dlp  
  
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
