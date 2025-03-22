import dotenv
import os
import json
import copy
import asyncio
from requestDuneData import save_results_to_json, bgt_rewards_snapshot
from nodeOperation import claim_honey_rewards, get_boosted_amount, get_honey_balance
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

def process_active_event(blockNumber, bgtAmount):

    config = load_config()
    pubkey = config['nodeInfo']['pubkey2']
    operator_address = config['nodeInfo']['operator_address']

    current_boosted = get_boosted_amount(operator_address)

    stake_file_prefix = "stake_snapshot"
    honey_file_prefix = "honey_rewards_claimed"

    data_dir = 'data'
    json_files = [f for f in os.listdir(data_dir) if f.startswith(stake_file_prefix) and f.endswith('.json')]

    latest_file = max(json_files, key=lambda x: os.path.getmtime(os.path.join(data_dir, x)))
    file_path = os.path.join(data_dir, latest_file)
    
    # 读取现有数据
    with open(file_path, 'r', encoding='utf-8') as f:
        snapshotData = json.load(f)
        print(f"成功读取文件: {file_path}")
        snapshotData = snapshotData['results']

    json_files = [f for f in os.listdir(data_dir) if f.startswith(honey_file_prefix) and f.endswith('.json')]
    if len(json_files) > 0:
        latest_file = max(json_files, key=lambda x: os.path.getmtime(os.path.join(data_dir, x)))
        file_path = os.path.join(data_dir, latest_file)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            honeyData = json.load(f)
            print(f"成功读取文件: {file_path}")
            honeyData = honeyData['results']
    else:
        honeyData = {}

    # claim honey rewards

    honeyBalance0 = get_honey_balance(operator_address)
    try:
        receipt = asyncio.run(claim_honey_rewards())
        if receipt is None:
            raise Exception("claim honey rewards 失败")
    except Exception as e:
        print(f"claim honey rewards 失败: {str(e)}")
        return None

    honeyBalance1 = get_honey_balance(operator_address)
    honeyClaimed = honeyBalance1 - honeyBalance0

    firstActive = True
    index = 0

    for key, value in snapshotData.items():
        total_bgt_earned = 0
        for record in value['Records']:
            total_bgt_earned += record.get('Staker BGT Rewards',0)
            if record.get('Total Boosted', None) is not None:
                firstActive = False
                break

        if firstActive:
            if index == 0:
                last_bgt_rewards = bgt_rewards_snapshot(pubkey, value['Records'][-1]['Start Block'], blockNumber)
            value['Records'][-1]['Total BGT Rewards'] = last_bgt_rewards
            value['Records'][-1]['Staker BGT Rewards'] = value['Records'][-1]['Total BGT Rewards'] * value['Records'][-1]['Weight']
            value['Records'][-1]['Staker Boosted'] = total_bgt_earned + value['Records'][-1]['Staker BGT Rewards']

        else:
            value['Records'][-1]['Total BGT Rewards'] = bgtAmount
            value['Records'][-1]['Staker BGT Rewards'] = value['Records'][-1]['Total BGT Rewards'] * value['Records'][-1]['Weight']
            if len(value['Records']) > 1:
                value['Records'][-1]['Staker Boosted'] = value['Records'][-2]['Staker Boosted'] + value['Records'][-1]['Staker BGT Rewards']
            else:
                value['Records'][-1]['Staker Boosted'] = value['Records'][-1]['Staker BGT Rewards']
        
        value['Records'][-1]['End Block'] = blockNumber
        value['Records'][-1]['Commission'] = value['Records'][-1]['Staker BGT Rewards'] * value['Records'][-1]['Commission Rate']
        value['Records'][-1]['BGT Rewards'] = value['Records'][-1]['Staker BGT Rewards'] - value['Records'][-1]['Commission']
        value['Records'][-1]['Total Boosted'] = current_boosted
        value['Records'][-1]['Boost Weight'] = value['Records'][-1]['Staker Boosted'] / value['Records'][-1]['Total Boosted']
        
        index += 1

    honeyData[blockNumber] = honeyClaimed

    save_results_to_json(snapshotData, stake_file_prefix)
    save_results_to_json(honeyData, honey_file_prefix)

    print("数据已更新并保存")
    return None


def process_drop_event(blockNumber, bgtAmount, account):

    config = load_config()

    operator_address = config['nodeInfo']['operator_address']
    current_boosted = get_boosted_amount(operator_address)

    stakerAccount = None
    
    staker_info = config['staker_info']
    for key, value in staker_info.items():
        if value['reward_address'] == account:
            stakerAccount = key
            break
    
    stake_file_prefix = "stake_snapshot"

    data_dir = 'data'
    json_files = [f for f in os.listdir(data_dir) if f.startswith(stake_file_prefix) and f.endswith('.json')]

    latest_file = max(json_files, key=lambda x: os.path.getmtime(os.path.join(data_dir, x)))
    file_path = os.path.join(data_dir, latest_file)
    
    # 读取现有数据
    with open(file_path, 'r', encoding='utf-8') as f:
        snapshotData = json.load(f)
        print(f"成功读取文件: {file_path}")
        snapshotData = snapshotData['results']

    for key, value in snapshotData.items():
        new_record = copy.copy(value['Records'][-1])
        if key == stakerAccount:
            value['Records'][-1]['End Block'] = blockNumber
            value['Records'][-1]['Total BGT Rewards'] = 0
            value['Records'][-1]['Staker BGT Rewards'] = 0
            value['Records'][-1]['Commission'] = 0
            value['Records'][-1]['BGT Rewards'] = 0
            value['Records'][-1]['Staker Boosted'] -= bgtAmount
            value['Records'][-1]['Total Boosted'] = current_boosted
            value['Records'][-1]['Boost Weight'] = value['Records'][-1]['Staker Boosted'] / value['Records'][-1]['Total Boosted']
        else:
            if len(value['Records']) > 1:
                value['Records'][-1]['End Block'] = blockNumber
                value['Records'][-1]['Total BGT Rewards'] = 0
                value['Records'][-1]['Staker BGT Rewards'] = 0
                value['Records'][-1]['Commission'] = 0
                value['Records'][-1]['BGT Rewards'] = 0
                value['Records'][-1]['Staker Boosted'] = value['Records'][-2]['Staker Boosted']
                value['Records'][-1]['Total Boosted'] = current_boosted
                value['Records'][-1]['Boost Weight'] = value['Records'][-1]['Staker Boosted'] / value['Records'][-1]['Total Boosted']
            else:
                value['Records'][-1]['End Block'] = blockNumber
                value['Records'][-1]['Total BGT Rewards'] = 0
                value['Records'][-1]['Staker BGT Rewards'] = 0
                value['Records'][-1]['Commission'] = 0
                value['Records'][-1]['BGT Rewards'] = 0
                value['Records'][-1]['Staker Boosted'] = 0
                value['Records'][-1]['Total Boosted'] = current_boosted
                value['Records'][-1]['Boost Weight'] = 0
        new_record['Start Block'] = blockNumber
        value['Records'].append(new_record)

    save_results_to_json(snapshotData, stake_file_prefix)

    print("数据已更新并保存")
    return None
