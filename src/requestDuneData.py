import dotenv
import os
import json
import time
from datetime import datetime
from dune_client.types import QueryParameter
from dune_client.client import DuneClient
from dune_client.query import QueryBase

# 加载环境变量
dotenv.load_dotenv(override=True)

# 打印环境变量
print(f"DUNE_API_KEY: {'*' * len(os.getenv('DUNE_API_KEY') or '')}")
print(f"DUNE_QUERY_ID: {os.getenv('DUNE_QUERY_ID')}")

DUNE_API_KEY = os.getenv('DUNE_API_KEY')
DUNE_QUERY_ID = os.getenv('DUNE_QUERY_ID')

def save_results_to_json(results):
    """将结果保存到JSON文件"""
    # 创建文件名（使用当前日期）
    date_str = datetime.now().strftime('%Y%m%d')
    filename = f"data/node_overview_{date_str}.json"
    
    # 确保data目录存在
    os.makedirs('data', exist_ok=True)
    
    # 保存结果到文件
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'query_id': DUNE_QUERY_ID,
            'timestamp': datetime.now().isoformat(),
            'results': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存到: {filename}")
    return filename

def query_node_overview():
    if not DUNE_API_KEY:
        raise ValueError("请在.env文件中设置DUNE_API_KEY")
    if not DUNE_QUERY_ID:
        raise ValueError("请在.env文件中设置DUNE_QUERY_ID")

    try:
        dune = DuneClient(DUNE_API_KEY)
        query_parameters =[
            QueryParameter.text_type(
                name="pubkey1",
                value="0xa0c673180d97213c1c35fe3bf4e684dd3534baab235a106d1f71b9c8a37e4d37a056d47546964fd075501dff7f76aeaf"
            ),
            QueryParameter.text_type(
                name="pubkey2",
                value="0x68b58f24be0e7c16df3852402e8475e8b3cc53a64cfaf45da3dbc148cdc05d30"
            )
        ]
        query = QueryBase(
            query_id=DUNE_QUERY_ID,
            params=query_parameters
        )
        
        # 执行查询
        print("开始执行查询...")
        execution_response = dune.execute_query(query=query)
        execution_id = execution_response.execution_id

        # 等待结果
        max_attempts = 60  # 最多等待60秒
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            status = dune.get_execution_status(execution_id)
            
            if status.state.value == 'QUERY_STATE_COMPLETED':
                results = dune.get_execution_results(execution_id)
                return results.result.rows
            elif status.state.value in ['QUERY_STATE_FAILED', 'QUERY_STATE_CANCELLED', 'QUERY_STATE_EXPIRED']:
                raise Exception(f'查询失败: {status.state.value}')
            
            print(f"等待查询结果... ({attempt}/{max_attempts})")
            time.sleep(1)
            
        raise TimeoutError("查询超时")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return None

if __name__ == "__main__":
    results = query_node_overview()
    if results:
        print("查询结果：")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
        # 保存结果到文件
        saved_file = save_results_to_json(results)
        print(f"结果已保存到文件: {saved_file}")
    else:
        print("未能获取查询结果")
