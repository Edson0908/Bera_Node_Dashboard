# call_entrypoint.py （放在 B 项目目录下）

import sys
import dotenv
import os
import time
from processEvent import process_active_event, process_drop_event
from nodeOperation import claim_incentive
from rewardsDistributation import distribute_incentive_V2, distribute_honey

dotenv.load_dotenv(override=True)  # 加载 B 自己的 .env

def retry_operation(operation, *args, max_retries=3, retry_delay=60, operation_name="操作"):
    """
    通用重试函数
    
    参数:
    operation: 要重试的函数
    *args: 传递给函数的参数
    max_retries: 最大重试次数
    retry_delay: 重试等待时间（秒）
    operation_name: 操作名称，用于日志输出
    """
    for attempt in range(max_retries):
        try:
            result = operation(*args)
            if result is not None:
                print(f"{operation_name}成功！")
                return result
            else:
                print(f"{operation_name}失败，{retry_delay}秒后重试...")
                time.sleep(retry_delay)
        except Exception as e:
            print(f"{operation_name}时发生错误: {str(e)}")
            if attempt < max_retries - 1:
                print(f"{retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print("达到最大重试次数，放弃重试")
                return None

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python call_entrypoint.py active <blockNumber> <bgtAmount>")
        print("  python call_entrypoint.py drop <blockNumber> <bgtAmount> <account>")
        print("  python call_entrypoint.py claim_incentive")
        print("  python call_entrypoint.py distribute_incentive")
        print("  python call_entrypoint.py distribute_honey")
        return

    action = sys.argv[1]

    if action == "active":
        if len(sys.argv) != 4:
            print("Usage: python call_entrypoint.py active <blockNumber> <bgtAmount>")
            return
        blockNumber = int(sys.argv[2])
        bgtAmount = float(sys.argv[3])
        retry_operation(process_active_event, blockNumber, bgtAmount, operation_name="处理 active event")
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
    elif action == "distribute_incentive":
        distribute_incentive_V2()
    elif action == "distribute_honey":
        distribute_honey()
    else:
        print(f"Unknown action: {action}")
        print("Available actions: active, drop, claim_incentive, distribute_incentive, distribute_honey")

if __name__ == "__main__":
    main()
