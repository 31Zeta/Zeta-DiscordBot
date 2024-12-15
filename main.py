import sys

from zeta_bot import core

import argparse

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--mode", type=str, default="normal", help="启动模式")
        args = parser.parse_args()
        core.start(args.mode)
    except KeyboardInterrupt:
        sys.exit(0)
