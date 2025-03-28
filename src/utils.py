import dotenv
import os
import json
import time
from datetime import datetime

dotenv.load_dotenv(override=True)

BERA_RPC_URL = os.getenv('BERA_RPC_URL')
BERA_WS_URL = os.getenv('BERA_WS_URL')
DUNE_API_KEY = os.getenv('DUNE_API_KEY')
DEBUG_MODE = os.getenv('DEBUG_MODE')
QUERY_VALIDATOR_OVERVIEW = os.getenv('QUERY_VALIDATOR_OVERVIEW')
QUERY_STAKE_BY_PUBKEY = os.getenv('QUERY_STAKE_BY_PUBKEY')
QUERY_STAKE_BY_TXID = os.getenv('QUERY_STAKE_BY_TXID')
QUERY_BGT_REWARDS_SNAPSHOT = os.getenv('QUERY_BGT_REWARDS_SNAPSHOT')
QUERY_HONEY_TRANSFER = os.getenv('QUERY_HONEY_TRANSFER')

PRIVATE_KEY = os.getenv('PRIVATE_KEY')


def load_config():
    config_dir = 'config'
    config_file = os.path.join(config_dir, 'config.json')
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config

def save_results_to_json(results, file_prefix):
    """将结果保存到JSON文件"""
    # 创建文件名（使用当前日期）
    date_str = datetime.now().strftime('%Y%m%d')
    filename = f"data/{file_prefix}_{date_str}.json"
    
    # 确保data目录存在
    os.makedirs('data', exist_ok=True)
    
    # 保存结果到文件
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存到: {filename}")
    return filename


def get_file_data(file_prefix):

    try:
        data_dir = 'data'
        json_files = [f for f in os.listdir(data_dir) if f.startswith(file_prefix) and f.endswith('.json')]
        latest_file = max(json_files, key=lambda x: os.path.getmtime(os.path.join(data_dir, x)))
        file_path = os.path.join(data_dir, latest_file)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"获取文件数据失败: {e}")
        return None
    