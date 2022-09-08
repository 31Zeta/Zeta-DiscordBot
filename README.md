# Zeta Discord机器人
一个基于Pycord的Discord机器人  
作者目前业余编程，如有不规范的地方请多多包涵与指教  
  
**不推荐使用0.6.1或更低版本（这些版本中机器人的相关设置存储在main.py文件中且设置极不完善）**  
  
核心功能
--------  
- 在Discord音频频道中播放来自Bilibili视频的音频  
- 在Discord音频频道中播放来自Youtube视频的音频  
  
安装及使用
----------  
**需要Python3.8或更高版本**  
  
使用以下指令将本库克隆到本地：  
```
git clone https://github.com/31Zeta/Zeta-DiscordBot.git
```  
  
将命令行运行位置移动至库根目录后使用以下指令来安装依赖包：  
```
 pip install -r requirements.txt
```  
或手动安装以下包：  
- py-cord (v2.1.1) https://github.com/Pycord-Development/pycord  
- APScheduler https://github.com/agronholm/apscheduler  
- bilibili-api https://github.com/MoyuScript/bilibili-api  
- PyNaCl https://github.com/pyca/pynacl/
- requests https://github.com/psf/requests  
- yt-dlp https://github.com/yt-dlp/yt-dlp  
- youtube-search-python https://github.com/alexmercerind/youtube-search-python  
  
Windows系统请前往ffmpeg官网 https://ffmpeg.org/download.html 获取ffmpeg.exe  
（或使用 https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z 下载后解压bin文件夹内的ffmpeg.exe）  
  
Linux系统可使用库内bin文件夹内自带的ffmpeg或前往ffmpeg官网 https://ffmpeg.org/download.html 获取最新版ffmpeg  
  
输入以下命令以运行机器人：  
```
python main.py
```  
根据提示完成设置，保持窗口打开以确保机器人正常运行  

如需更改设置，则使用以下命令启动机器人（0.7.0及更高版本）： 
```
python main.py --mode=setting
```  
  
0.6.1及更低版本注意事项
----------------------  
如果使用**0.6.1及更低版本**需进行如下操作：  
1. 请将ffmpeg或ffmpeg.exe放入库根目录的bin文件夹中  
2. 打开main.py根据使用的系统将设置中的system_option设为对应数值  
3. 创建一个txt文件并将Discord机器人令牌存储到其中，默认情况下Linux系统将文件重命名为token.txt，Windows系统则重命名为test_token.txt，并将该文件置于库根目录下（请自行搜索如何创建Discord机器人及获得其令牌token）  
4. 根据需求修改main.py中设置内的变量，机器人指令前缀以及令牌文件名称可根据需要搜索变量名command_prefix以及token_name进行修改  
