from typing import *
import os

import discord

import utils

from zeta_bot import (
    decorator
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

    def files(self, filename: Union[str, List[str]]) -> List[discord.File]:
        if isinstance(filename, list):
            result = []
            for name in filename:
                if name in self.icons:
                    result.append(discord.File(self.icons[name], filename=name))
            return result
        else:
            if filename in self.icons:
                return [discord.File(self.icons[filename], filename=filename)]
            else:
                return []

def url(filename: str) -> str:
    return f"attachment://{filename}"
