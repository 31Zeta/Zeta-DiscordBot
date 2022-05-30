# Zeta Discord机器人
一个基于Pycord的Discord机器人  
作者目前业余编程，如有不规范的地方请多多包涵与指教  
  
**不推荐使用0.6.1或更早版本（这些版本中机器人将以32Zeta自称并且机器人相关设置在main.py文件中）**  
  
**0.7.0版本将于近日推出**
  
核心功能
--------
- 在Discord音频频道中播放来自Bilibili视频的音频  
- 在Discord音频频道中播放来自Youtube视频的音频  
  
安装及使用
----------
**需要Python3.8或更高版本**  
  
使用以下指令来安装依赖包：  
 ```
 pip install -r requirements.txt
 ```  
或手动安装以下包：  
- py-cord (2.0或更高版本) https://github.com/Pycord-Development/pycord  
- APScheduler https://github.com/agronholm/apscheduler  
- bilibili-api https://github.com/MoyuScript/bilibili-api  
- requests https://github.com/psf/requests  
- yt-dlp https://github.com/yt-dlp/yt-dlp  
- youtube-search-python https://github.com/alexmercerind/youtube-search-python  
  
使用以下指令将本库克隆到本地：  
```
git clone https://github.com/31Zeta/Zeta-DiscordBot.git
```  
  
Windows系统请前往ffmpeg官网 https://ffmpeg.org/download.html 获取ffmpeg.exe  
（或使用 https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z 下载后解压bin文件夹内的ffmpeg.exe）  
  
Linux系统可使用库内bin文件夹内自带的ffmpeg或前往ffmpeg官网 https://ffmpeg.org/download.html 获取最新版ffmpeg  
  
**0.6.1及更早版本**请将ffmpeg或ffmpeg.exe放入库根目录的bin文件夹中  
打开main.py根据使用的系统将设置中的system_option设为对应数值  
  
使用python运行**main.py**以运行机器人  
根据提示完成设置，保持窗口打开以确保机器人正常运行  
