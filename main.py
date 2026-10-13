import sys
import os
import argparse

import utils
from zeta_bot import core

if __name__ == "__main__":
    if os.path.exists("./requirements.txt"):
        utils.cp("开始依赖检查", end="")
        missing_dependencies = utils.check_requirements("./requirements.txt", false_only=True)
        utils.cp("：完成")

        if len(missing_dependencies) > 0:
            utils.cp("以下包未安装或版本不匹配：", message_type=utils.PrintType.WARNING, print_head=True, gap=True)
            message = ""
            for package_name in missing_dependencies:
                message += f"{package_name}{missing_dependencies[package_name]['required_version']}\n"
            print(message)
            utils.cp("程序可能无法运行或在使用中遇到问题\n如发生错误，请手动运行 pip install -r requirements.txt 进行安装", message_type=utils.PrintType.WARNING, print_head=True)

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--mode", type=str, default="normal", help="启动模式")
        parser.add_argument("--web-port", type=int, default=None, help="Web控制面板端口（覆盖configs/web_config.json）")
        parser.add_argument("--web-host", type=str, default=None, help="Web控制面板监听地址，例如 0.0.0.0 或 127.0.0.1")
        parser.add_argument("--web-base-path", type=str, default=None, help="Web控制面板URL前缀（反向代理挂载到子路径时使用），例如 /zeta")
        parser.add_argument("--no-web", action="store_true", help="不启动Web控制面板")
        args = parser.parse_args()
        core.start(args.mode, web_options={
            "port": args.web_port,
            "host": args.web_host,
            "base_path": args.web_base_path,
            "enabled": False if args.no_web else None,
        })
    except KeyboardInterrupt:
        sys.exit(0)
