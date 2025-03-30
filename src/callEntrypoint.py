# call_entrypoint.py （放在 B 项目目录下）

import sys
import dotenv
import os
from processEvent import process_active_event, process_drop_event
from nodeOperation import claim_incentive

dotenv.load_dotenv(override=True)  # 加载 B 自己的 .env

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python call_entrypoint.py active <blockNumber> <bgtAmount>")
        print("  python call_entrypoint.py drop <blockNumber> <bgtAmount> <account>")
        print("  python call_entrypoint.py claim_incentive")
        return

    action = sys.argv[1]

    if action == "active":
        if len(sys.argv) != 4:
            print("Usage: python call_entrypoint.py active <blockNumber> <bgtAmount>")
            return
        blockNumber = int(sys.argv[2])
        bgtAmount = float(sys.argv[3])
        process_active_event(blockNumber, bgtAmount)
    elif action == "drop":
        if len(sys.argv) != 5:
            print("Usage: python call_entrypoint.py drop <blockNumber> <bgtAmount> <account>")
            return
        blockNumber = int(sys.argv[2])
        bgtAmount = float(sys.argv[3])
        account = sys.argv[4]
        process_drop_event(blockNumber, bgtAmount, account)
    elif action == "claim_incentive":
        if len(sys.argv) != 2:
            print("Usage: python call_entrypoint.py claim_incentive")
            return
        claim_incentive()
    else:
        print(f"Unknown action: {action}")
        print("Available actions: active, drop, claim_incentive")

if __name__ == "__main__":
    main()
