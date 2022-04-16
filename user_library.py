import json
import os
from user import User


class UserLibrary:
    def __init__(self, library_path) -> None:
        if library_path.endswith("/"):
            library_path = library_path.rstrip("/")

        # 检查路径文件夹是否存在
        if not os.path.exists(library_path):
            os.mkdir(library_path)
            print(f"在路径 {library_path} 创建用户库文件夹")

        self.path = library_path
        self.json_path = f"{library_path}/user_library.json"

        # 如user_library文件不存在则创建
        if not os.path.exists(self.json_path):
            new_library = {
                "total_user": 0, "users": {}
            }
            with open(self.json_path, "w", encoding="utf-8") as file:
                file.write(json.dumps(new_library, indent=4))

        with open(self.json_path, "r", encoding="utf-8") as file:
            self.library = json.loads(file.read())

    def save(self) -> None:
        """
        在json_path中以json格式写入当前user_dict
        """
        with open(self.json_path, "w", encoding="utf-8") as file:
            file.write(json.dumps(self.library, sort_keys=False, indent=4))

    def load(self) -> None:
        with open(self.json_path, "r", encoding="utf-8") as file:
            self.library = json.loads(file.read())

    def exist(self, user_id) -> bool:
        """
        检测当前user_library中是否存在用户ID为user_id的用户json文件，并返回相应的布尔值
        """
        return os.path.exists(f"{self.path}/{user_id}.json")

    def add_user(self, user: User) -> None:
        """
        向库中新添用户user
        """
        user.save()
        self.library["users"][int(user.id)] = user.name
        self.library["total_user"] += 1
        self.save()
