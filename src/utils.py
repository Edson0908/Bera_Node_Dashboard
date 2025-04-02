import dotenv
import os
import json
from datetime import datetime
import shutil

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
DEBANK_ACCESS_KEY = os.getenv('DEBANK_ACCESS_KEY')


def load_config():
    config_dir = 'config'
    config_file = os.path.join(config_dir, 'config.json')
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config

def save_results_to_json(results, file_prefix, file_path = None):
    """将结果保存到JSON文件"""
    # 创建文件名（使用当前日期）
    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    if file_path is None:
        filename = f"data/{file_prefix}_{date_str}.json"
    else:
        filename = f"data/{file_path}/{file_prefix}_{date_str}.json"
    
    # 确保data目录存在
    os.makedirs('data', exist_ok=True)
    if file_path is not None:
        os.makedirs(f"data/{file_path}", exist_ok=True)
    
    # 保存结果到文件
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存到: {filename}")
    return filename


def get_file_data(file_prefix, dir = None):

    try:
        if dir is None:
            data_dir = 'data'
        else:
            data_dir = f'data/{dir}'
        json_files = [f for f in os.listdir(data_dir) if f.startswith(file_prefix) and f.endswith('.json')]
        latest_file = max(json_files, key=lambda x: os.path.getmtime(os.path.join(data_dir, x)))
        file_path = os.path.join(data_dir, latest_file)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"获取文件数据失败: {e}")
        return None


def update_json_file(filename, data):   

    os.makedirs('data', exist_ok=True)
    file_path = os.path.join('data', filename)
    
    existing_data = {}
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    
    existing_data.update(data)       

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存到: {file_path}")
    return file_path



def rename_file(old_name, new_name, path):
    """
    重命名文件
    
    Args:
        old_name (str): 原文件名
        new_name (str): 新文件名
    
    Returns:
        bool: 重命名是否成功
    """
    try:
        old_name = os.path.join(path, old_name)
        new_name = os.path.join(path, new_name)
        # 检查源文件是否存在
        if not os.path.exists(old_name):
            print(f"错误: 文件 {old_name} 不存在")
            return False
            
        # 检查目标文件名是否已存在
        if os.path.exists(new_name):
            print(f"错误: 文件 {new_name} 已存在")
            return False
            
        # 重命名文件
        os.rename(old_name, new_name)
        print(f"文件已成功重命名为: {new_name}")
        return True
    except Exception as e:
        print(f"重命名文件时出错: {str(e)}")
        return False



