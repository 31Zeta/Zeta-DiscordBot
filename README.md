# Zeta Discord机器人 Discord Bot
一个基于Pycord的Discord机器人  
作者目前业余编程，如有不规范的地方请多多包涵与指教  

A Discord Bot that based on Pycord.
  
**不推荐使用0.6.1或更低版本（这些版本中机器人的相关设置存储在main.py文件中且设置极不完善）**  

**Not recommended to use Ver 0.6.1 or below (The setting in those version is stored in main.py and incomplete)**

核心功能 Core Functions
--------  
- 在Discord音频频道中播放来自Bilibili视频的音频  
- 在Discord音频频道中播放来自Youtube视频的音频  
- Play Youtube video sound in Discord Voice Channel
- Play Bilibili video sound in Discord Voice Channel

安装及使用 Install
----------  
**需要Python3.8或更高版本**  
**Require Python 3.8 or higher**

使用以下指令将本库克隆到本地：  
Use following commands to clone this repo to local
```
git clone https://github.com/31Zeta/Zeta-DiscordBot.git
```  
  
将命令行运行位置移动至库根目录后使用以下指令来安装依赖包：  
Change command line to root dir and use following commands to install dependency
```
 pip install -r requirements.txt
```  
或手动安装以下包：  
Or install these manually

- py-cord (v2.1.1) https://github.com/Pycord-Development/pycord  
- APScheduler https://github.com/agronholm/apscheduler  
- bilibili-api-python https://github.com/Nemo2011/bilibili-api
- PyNaCl https://github.com/pyca/pynacl/
- requests https://github.com/psf/requests  
- yt-dlp https://github.com/yt-dlp/yt-dlp  
- youtube-search-python https://github.com/alexmercerind/youtube-search-python  
  
Windows系统请前往ffmpeg官网 https://ffmpeg.org/download.html 获取ffmpeg.exe  
（或使用 https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z 下载后解压bin文件夹内的ffmpeg.exe）  
  
Windows: please visit https://ffmpeg.org/download.html to get ffmpeg.exe
(or access https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z download and unzip it to get ffmpeg.exe in bin dir） 
  
Linux系统可使用库内bin文件夹内自带的ffmpeg或前往ffmpeg官网 https://ffmpeg.org/download.html 获取最新版ffmpeg  

Linux: Visit https://ffmpeg.org/download.html to get the most recent ffmpeg file

输入以下命令以运行机器人：  
Use following command to start Discord Bot
```
python main.py
```  
根据提示完成设置，保持窗口打开以确保机器人正常运行  
Complete the setting through instruction, keep the window open to ensure the Bot is running correctly

如需更改设置，则使用以下命令启动机器人（0.7.0及更高版本）： 
To change the setting, please use following command (Ver 0.7.0 or higher required)
```
python main.py --mode=setting
```  
  
0.6.1及更低版本注意事项     
P.S. for Ver 0.6.1 and lower version
----------------------  
1. 请将ffmpeg或ffmpeg.exe放入库根目录的bin文件夹中  
2. 打开main.py根据使用的系统将设置中的system_option设为对应数值  
3. 创建一个txt文件并将Discord机器人令牌存储到其中，默认情况下Linux系统将文件重命名为token.txt，Windows系统则重命名为test_token.txt，并将该文件置于库根目录下（请自行搜索如何创建Discord机器人及获得其令牌token）  
4. 根据需求修改main.py中设置内的变量，机器人指令前缀以及令牌文件名称可根据需要搜索变量名command_prefix以及token_name进行修改  


<ol>
<li>Put ffmpeg or ffmpeg.exe to /bin folder
<li>Set the system_option in the settings to the corresponding value according to the system used (in main.py)
<li>Create a txt file and store Discord Bot's token in it. Linux user should rename the file name with "token.txt". Windows user should rename the file name with "test_token.txt". Then put this file in root dir.
<li>Set the var in main.py according to the demand. Change Bot command prefix by edit var command_prefix. Change token filename by edit var token_name.
</ol>
