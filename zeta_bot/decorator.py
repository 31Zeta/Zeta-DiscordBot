from typing import *
from zeta_bot import errors


class Singleton(object):
    def __init__(self, cls):
        self.cls = cls
        self.instance = None

    def __call__(self, *args, **kwargs):
        if self.instance is None:
            self.instance = self.cls(*args, **kwargs)
        return self.instance


def check_initialized(method, name: Optional[str] = None):
    def wrapper(self, *args, **kwargs):
        if not self._initialized:
            # 判断self._name是否存在
            if hasattr(self, '_name') and self._name is not None:
                raise errors.UninitializedError(self._name)
            # 如果self._name不存在，使用name
            else:
                raise errors.UninitializedError(name)
        return method(self, *args, **kwargs)
    return wrapper
