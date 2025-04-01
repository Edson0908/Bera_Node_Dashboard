import copy
import utils
from requestDuneData import bgt_rewards_snapshot
from nodeOperation import claim_honey_rewards, get_boosted_amount, get_honey_balance


def process_active_event(blockNumber, bgtAmount):

    config = utils.load_config()
    pubkey = config['nodeInfo']['pubkey2']
    operator_address = config['nodeInfo']['operator_address']

    current_boosted = get_boosted_amount(operator_address)

    stake_file_prefix = config['save_file_prefix']['stake_snapshot']
    honey_file_prefix = config['save_file_prefix']['honey_rewards_claimed']
    
    # 读取现有数据
    snapshotData = utils.get_file_data(stake_file_prefix)
    snapshotData = snapshotData['results']

    honeyData = utils.get_file_data(honey_file_prefix)
    if honeyData is not None:
        honeyData = honeyData['results']
    else:
        honeyData = {}

    # claim honey rewards

    honeyBalance0 = get_honey_balance(operator_address)
    try:
        receipt = claim_honey_rewards()
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
            value['Records'][-1]['Total BGT Rewards'] = last_bgt_rewards[0].get('bgt_rewards', 0)
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

        new_record = {
            "BERA Staked": value['Records'][-1]['BERA Staked'],
            "Start Block": blockNumber,
            "Total Staked": value['Records'][-1]['Total Staked'],
            "Weight": value['Records'][-1]['Weight'],
            "Commission Rate": value['Records'][-1]['Commission Rate']
        }
        value['Records'].append(new_record)
        
        index += 1

    honeyData[blockNumber] = honeyClaimed

    utils.save_results_to_json(snapshotData, stake_file_prefix)
    utils.save_results_to_json(honeyData, honey_file_prefix)

    print("数据已更新并保存")
    return honeyClaimed


def process_drop_event(blockNumber, bgtAmount, account):

    config = utils.load_config()

    operator_address = config['nodeInfo']['operator_address']
    current_boosted = get_boosted_amount(operator_address)

    stakerAccount = None
    
    staker_info = config['staker_info']
    for key, value in staker_info.items():
        if value['reward_address'] == account:
            stakerAccount = key
            break
    
    stake_file_prefix = config['save_file_prefix']['stake_snapshot']

    snapshotData = utils.get_file_data(stake_file_prefix)
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

    utils.save_results_to_json(snapshotData, stake_file_prefix)

    print("数据已更新并保存")
    return None
