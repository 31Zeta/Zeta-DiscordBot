import datetime


def time() -> str:
    return str(datetime.datetime.now())[:19]


