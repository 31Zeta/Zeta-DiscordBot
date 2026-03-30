from typing import *
import os

import discord

import utils

from zeta_bot import (
    decorator,
    language
)

@decorator.Singleton
class IconLib:
    def __init__(self):
        self.icons = {}

    def load_icons(self, dir_path: str):
        for filename in os.listdir(dir_path):
            file_path = utils.path_slash_formatting(os.path.join(dir_path, filename))
            if os.path.isfile(file_path) and (filename.endswith(".png") or filename.endswith(".gif")):
                self.icons[filename] = file_path

    def get_file(self, filename: str) -> Optional[discord.File]:
        if filename in self.icons:
            return discord.File(self.icons[filename], filename=filename)
        else:
            return None
