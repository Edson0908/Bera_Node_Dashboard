# call_entrypoint.py （放在 B 项目目录下）

import sys
import dotenv
import os
from processEvent import process_active_event, process_drop_event  # 替换为 B 中定义函数的模块名

dotenv.load_dotenv(override=True)  # 加载 B 自己的 .env

def main():
    if len(sys.argv) < 4:
        print("Usage: python call_entrypoint.py [active|drop] blockNumber bgtAmount [account]")
        return

    action = sys.argv[1]
    blockNumber = int(sys.argv[2])
    bgtAmount = float(sys.argv[3])

    if action == "active":
        process_active_event(blockNumber, bgtAmount)
    elif action == "drop":
        if len(sys.argv) < 5:
            print("Account address required for drop event")
            return
        account = sys.argv[4]
        process_drop_event(blockNumber, bgtAmount, account)
    else:
        print(f"Unknown action: {action}")

if __name__ == "__main__":
    main()
