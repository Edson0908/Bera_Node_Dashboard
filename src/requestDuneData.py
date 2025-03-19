import dotenv
import os
import json
import time
from datetime import datetime
from dune_client.types import QueryParameter
from dune_client.client import DuneClient
from dune_client.query import QueryBase
from nodeOperation import get_current_block, get_unclaimed_honey_rewards

# 加载环境变量
dotenv.load_dotenv(override=True)

DUNE_API_KEY = os.getenv('DUNE_API_KEY')
DEBUG_MODE = os.getenv('DEBUG_MODE')
BERA_RPC_URL = os.getenv('BERA_RPC_URL')

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


def query_dune_data(query_id, query_parameters):

    if not DUNE_API_KEY:
        raise ValueError("请在.env文件中设置DUNE_API_KEY")
    
    try:
        dune = DuneClient(DUNE_API_KEY)
        query = QueryBase(
            query_id=query_id,
            params=query_parameters
        )

        if DEBUG_MODE == 'True':
            results = dune.get_latest_result(query_id)
            return results.result.rows

        # 执行查询
        print("开始执行查询...")
        execution_response = dune.execute_query(query=query)
        execution_id = execution_response.execution_id
        
        # 等待结果
        max_attempts = 100  # 最多等待60秒
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

def get_commission_rate(staker, amount):
    config = load_config()

    commission_rate = config['commission_rate']
    staker_info = config['staker_info']
    if staker_info[staker]['commission']:
        for key, value in commission_rate.items():
            if amount < int(key):
                return value
    return 0

def init_stake_snapshot():

    config = load_config()

    staker_info = config['staker_info']

    processed_data = {}
    saved_file_prefix = "stake_snapshot"
    
    query_id = os.getenv('QUERY_STAKE_BY_PUBKEY')
    validator_pubkey1 = config['nodeInfo']['private_key1']
    validator_pubkey2 = config['nodeInfo']['private_key2']
    query_parameters = [
        QueryParameter.text_type(
            name="pubkey1",
            value= validator_pubkey1
        )
    ]
    results = query_dune_data(query_id, query_parameters)
    #print(json.dumps(results, indent=2, ensure_ascii=False))

    total_staked = 0
    for item in results:
        total_staked += item['amount']
        if item['staker'] not in processed_data.keys():
            processed_data[item['staker']] = {'Records': []}
            processed_data[item['staker']]['name'] = staker_info[item['staker']]['name']
            processed_data[item['staker']]['Records'].append({
                "BERA Staked": item['amount'],
                "Start Block": item['blockNumber'],
                "Total Staked": total_staked,
                "Weight": item['amount']/total_staked
            })
        
        else:
            amount = processed_data[item['staker']]['Records'][-1]['BERA Staked']
            processed_data[item['staker']]['Records'][-1]["End Block"] = item['blockNumber']
            processed_data[item['staker']]['Records'].append({
                "BERA Staked": item['amount'] + amount,
                "Start Block": item['blockNumber'],
                "Total Staked": total_staked,
                "Weight": (item['amount'] + amount)/total_staked
            })
        
        for key, value in processed_data.items():
            if key != item['staker']:
                value['Records'][-1]['End Block'] = item['blockNumber']
                amount = value['Records'][-1]['BERA Staked']
                value['Records'].append({
                    "BERA Staked": amount,
                    "Start Block": item['blockNumber'],
                    "Total Staked": total_staked,
                    "Weight": amount/total_staked
                })
    
    keys = list(processed_data.keys())
    index = 0
    for index in range(len(keys)):
        if index == 0:
            for item in processed_data[keys[index]]['Records']:
                item['Commission Rate'] = get_commission_rate(keys[index], item['BERA Staked'])
                if item.get('End Block') is not None:
                    start_block = item['Start Block']
                    end_block = item['End Block']
                    bgt_rewards_result = bgt_rewards_snapshot(validator_pubkey2, start_block, end_block)
                    if bgt_rewards_result[0]['bgt_rewards'] is not None:
                        item['Total BGT Rewards'] = bgt_rewards_result[0]['bgt_rewards']
                        item['Staker BGT Rewards'] = item['Total BGT Rewards'] * item['Weight']
                        item['Commission'] = item['Staker BGT Rewards'] * item['Commission Rate']
                        item['BGT Rewards'] = item['Staker BGT Rewards']  * (1 - item['Commission Rate'])
                    else:
                        item['Total BGT Rewards'] = 0
                        item['Staker BGT Rewards'] = 0
                        item['Commission'] = 0
                        item['BGT Rewards'] = 0
        else:
            for item in processed_data[keys[index]]['Records']:
                item['Commission Rate'] = get_commission_rate(keys[index], item['BERA Staked'])
                if item.get('End Block') is not None:
                    for row in processed_data[keys[index-1]]['Records']:
                        if row.get('Start Block') == item['Start Block']:
                            item['Total BGT Rewards'] = row['Total BGT Rewards']
                            item['Staker BGT Rewards'] = item['Total BGT Rewards'] * item['Weight']
                            item['Commission'] = item['Staker BGT Rewards'] * item['Commission Rate']
                            item['BGT Rewards'] = item['Staker BGT Rewards']  * (1 - item['Commission Rate'])
                            break


    save_results_to_json(processed_data, saved_file_prefix)

def bgt_rewards_snapshot(validator_pubkey, start_block, end_block):

    query_id = os.getenv('QUERY_BGT_REWARDS_SNAPSHOT')
    
    query_parameters = [
        QueryParameter.text_type(
            name="pubkey2",
            value= validator_pubkey
        ),
        QueryParameter.text_type(
            name="startBlock",
            value= start_block
        ),
        QueryParameter.text_type(
            name="endBlock",
            value= end_block
        )
    ]

    results = query_dune_data(query_id, query_parameters)
    if results:
        print("查询结果：")
        print(json.dumps(results, indent=2, ensure_ascii=False)) 
        return results  
    else:
        print("未能获取查询结果")   
        return None


def validator_overview():

    config = load_config()
    saved_file_prefix = "validator_overview"
    query_id = os.getenv('QUERY_VALIDATOR_OVERVIEW')
    validator_pubkey1 = config['nodeInfo']['private_key1']
    validator_pubkey2 = config['nodeInfo']['private_key2']
    query_parameters = [
        QueryParameter.text_type(
            name="pubkey1",
            value= validator_pubkey1
        ),
        QueryParameter.text_type(
            name="pubkey2",
            value= validator_pubkey2
        )
    ]   

    results = query_dune_data(query_id, query_parameters)
    if results:
        print("查询结果：")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        save_results_to_json(results, saved_file_prefix)    
    else:
        print("未能获取查询结果")   



def update_stake_snapshot(new_staker=False):

    config = load_config()
    validator_pubkey2 = config['nodeInfo']['private_key2']

    current_block = get_current_block()

    saved_file_prefix = "stake_snapshot"

 
    try:
        if new_staker:
            init_stake_snapshot()

        """读取最新的 stake_snapshot 文件并更新数据"""
        # 获取最新的文件
        data_dir = 'data'
        json_files = [f for f in os.listdir(data_dir) if f.startswith(saved_file_prefix) and f.endswith('.json')]
    
        latest_file = max(json_files, key=lambda x: os.path.getmtime(os.path.join(data_dir, x)))
        file_path = os.path.join(data_dir, latest_file)
        # 读取现有数据
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            print(f"成功读取文件: {file_path}")
        
        existing_data = existing_data['results']
        
        n = 0
        bgt_rewards_result = 0
        for key, value in existing_data.items():
            value['Records'][-1]['Commission Rate'] = get_commission_rate(key,value['Records'][-1]['BERA Staked'])
            value['Records'][-1]['End Block'] = current_block
            if n == 0:
                bgt_rewards_result = bgt_rewards_snapshot(validator_pubkey2, value['Records'][-1]['Start Block'], current_block)
            value['Records'][-1]['Total BGT Rewards'] = bgt_rewards_result[0]['bgt_rewards']
            value['Records'][-1]['Staker BGT Rewards'] = value['Records'][-1]['Total BGT Rewards'] * value['Records'][-1]['Weight']             
            value['Records'][-1]['Commission'] = value['Records'][-1]['Staker BGT Rewards'] * value['Records'][-1]['Commission Rate']
            value['Records'][-1]['BGT Rewards'] = value['Records'][-1]['Staker BGT Rewards']  * (1 - value['Records'][-1]['Commission Rate'])
            n += 1
        # 保存更新后的数据
        save_results_to_json(existing_data, saved_file_prefix)
        print("数据已更新并保存")
        return None
        
    except Exception as e:
        print(f"更新数据时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def calculate_honey_rewards(data):

    saved_file_prefix = "honey_rewards"

    data_dir = 'data'
    json_files = [f for f in os.listdir(data_dir) if f.startswith(saved_file_prefix) and f.endswith('.json')]
    if json_files:
        latest_file = max(json_files, key=lambda x: os.path.getmtime(os.path.join(data_dir, x)))
        file_path = os.path.join(data_dir, latest_file)
        # 读取现有数据
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            print(f"成功读取文件: {file_path}")
            existing_data = existing_data['results']
    else:
        existing_data={}

    total_bgt_boosted = 0

    for key, value in data.items():

        total_bgt_rewards = 0
        for item in value['Records']:
            total_bgt_rewards += item['Staker BGT Rewards']
        bgt_distributed = get_bgt_distributed(key)
        bgt_boosted = total_bgt_rewards - bgt_distributed
        total_bgt_boosted += bgt_boosted

        last_record = value['Records'][-1]
        
        if key not in existing_data.keys():
            existing_data[key] = {}
            existing_data[key]['Rewards'] = []
            start_block = last_record['Start Block']
            end_block = last_record['End Block']
            existing_data[key]['Rewards'].append({
                "Start Block": start_block,
                "End Block": end_block
            })
        else:
            if existing_data[key]['Rewards'][-1]['Start Block'] == last_record['Start Block']:
                start_block = existing_data[key]['Rewards'][-1]['Start Block']
                end_block = last_record['End Block']
                existing_data[key]['Rewards'][-1]['End Block'] = end_block
            else:
                start_block = last_record['Start Block']
                end_block = last_record['End Block']
                existing_data[key]['Rewards'].append({
                    "Start Block": start_block,
                    "End Block": end_block
                })
        
        existing_data[key]['Rewards'][-1]['BGT Boosted'] = bgt_boosted
        total_honey_reward = get_total_honey_reward(last_record['Start Block'])


     # 保存更新后的数据
    save_results_to_json(existing_data, saved_file_prefix)
    print("数据已更新并保存")
    return None

def get_total_honey_reward(start_bolck):

    unclaimed_honey_rewards = get_unclaimed_honey_rewards()
    
    claimed_honey_rewards = 0 # 需要从dune获取, 大于start_block的honey_rewards，并去掉第一条记录

    return unclaimed_honey_rewards + claimed_honey_rewards

def get_bgt_distributed(address):

    return 0

def test():
    
    data_dir = 'data'
    json_files = [f for f in os.listdir(data_dir) if f.startswith('stake_snapshot_') and f.endswith('.json')]
    
    latest_file = max(json_files, key=lambda x: os.path.getmtime(os.path.join(data_dir, x)))
    file_path = os.path.join(data_dir, latest_file)
    # 读取现有数据
    with open(file_path, 'r', encoding='utf-8') as f:
        existing_data = json.load(f)
        print(f"成功读取文件: {file_path}")
        
    existing_data = existing_data['results']

    calculate_honey_rewards(existing_data)

if __name__ == "__main__":

    init_stake_snapshot()
    #validator_overview()
    #update_stake_snapshot()
    #test()
