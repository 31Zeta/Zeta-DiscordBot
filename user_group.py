class UserGroup:
    def __init__(self, name: str) -> None:

        self.name = "N/A"
        self.permission = {
            "shutdown": False,
            "reboot": False,
            "change_user_group": False,
            "broadcast": False,
            "blacklist": False,
        }
        self.mutable_user_group = {
            "root": False,
            "admin": False,
            "member": False,
            "blacklist": False
        }

        if name == "root":
            self.name = "root"
            for key in self.permission:
                self.permission[key] = True
            for key in self.mutable_user_group:
                self.mutable_user_group[key] = True

        elif name == "admin":
            self.name = "admin"
            self.permission["reboot"] = True
            self.permission["change_user_group"] = True
            self.permission["blacklist"] = True
            self.mutable_user_group["member"] = True
            self.mutable_user_group["blacklist"] = True

        elif name == "member":
            self.name = "member"

        elif name == "blacklist":
            self.name = "blacklist"

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


def authorized(user, action: str) -> bool:
    return user.user_group.permission[action]
