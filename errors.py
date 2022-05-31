class UserExit(RuntimeError):
    def __init__(self):
        super().__init__()


class KeyNotFoundError(RuntimeError):
    def __init__(self):
        super().__init__()

