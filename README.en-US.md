# Zeta Discord Bot
A Discord bot based on Pycord.  
The author is currently a hobbyist programmer; please be understanding and feel free to provide guidance if there are any irregularities.

Currently, the bot only supports Chinese.  
The display language currently available for this robot is Chinese only.  

Table of contents
------------------------
- [Core Features](#core-features)
- [How to install and deploy](#how-to-install-and-deploy)

## Core Features
- Play audio from Bilibili videos in Discord voice channels.
- Play audio from YouTube videos in Discord voice channels.
- Play audio from NetEase CloudMusic in Discord voice channels.
- Search and play from Bilibili or YouTube directly within Discord channels.
- Interactive playlists.

## How to install and deploy
**Please use Python version 3.10-3.13**

Please download and unzip the latest version of the source code from the releases.

Move your command line working directory to the root directory of the extracted source code and use the following command to install the dependency packages:  
```
 pip install -r requirements.txt
```

If you need to use the bot's YouTube-related features, it is recommended to enable a JavaScript runtime environment for `yt-dlp-ejs`.
`yt-dlp-ejs` is already included in `yt-dlp[default]` within `requirements.txt` and will be installed automatically during dependency installation. For guidance on selecting and installing the environment, please refer to Step 1 on this page: https://github.com/yt-dlp/yt-dlp/wiki/EJS#step-1-install-a-supported-javascript-runtime

For Windows systems, please go to the [FFmpeg official website](https://ffmpeg.org/download.html) to obtain `ffmpeg.exe`.  
(Or download from https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z and extract `ffmpeg.exe` from the bin folder.)

For Linux systems, you can use the ffmpeg included in the library's bin folder or go to the [FFmpeg official website](https://ffmpeg.org/download.html) to get the latest version of ffmpeg.

Place the extracted ffmpeg file into the `bin` folder of the library.

Linux systems also require the installation of:  
```
sudo apt install libopus0
```

Enter the following command to run the bot:  
```
python main.py
```

Complete the setup according to the prompts, and keep the window open to ensure the bot runs normally.  
To change settings, start the bot using the following command (version 0.7.0 and higher):
```
python main.py --mode=setting
```
