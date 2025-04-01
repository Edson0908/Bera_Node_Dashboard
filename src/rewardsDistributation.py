import utils
import json
import nodeOperation
CONFIG = utils.load_config()

def distribute_incentive():

    staker_info = CONFIG['staker_info']
    filename = CONFIG['save_file_prefix']['incentive_data']
    incentive_data = utils.get_file_data(filename)

    if incentive_data is None:
        print('没有激励数据')
        return
    

    for block_number, data in incentive_data.items():
        if data.get('distributed', False):
            continue
        rewards = data.get('rewards', [])
        if len(rewards) == 0:
            continue
        stakers_boost_weight = get_boost_weight(block_number)
        if stakers_boost_weight is None:
            continue
        
        total_stakers_num = len(stakers_boost_weight)
        total_rewards_num = len(rewards)
        reward_index = 0
        for reward in rewards:
            if reward.get('distributed',False):
                continue
            index = 0
            for staker, boost_weight in stakers_boost_weight.items():
                if reward.get('transfer', {}).get(staker, None) is not None:
                    index += 1
                    continue

                reward_address = staker_info[staker]['reward_address']
                amount = reward.get('amount', 0) * boost_weight
                try:
                    tx_hash = nodeOperation.transfer_erc20_token(reward.get('token'), reward_address, amount)
                except Exception as e:
                    print(e)
                    reward['transfer'][staker] = None
                    continue
                if tx_hash is not None:
                    reward['transfer'][staker] = {
                        'tx_hash': tx_hash,
                        'to': reward_address,
                        'amount': amount
                    }
                    index += 1
                else:
                    reward['transfer'][staker] = None
            
            if index == total_stakers_num:
                reward['distributed'] = True
                reward_index += 1
        
        if reward_index == total_rewards_num:
            data['distributed'] = True
            print(f'block {block_number} 激励数据分发完成')

    utils.update_json_file(filename, incentive_data)


def get_boost_weight(block_number):
    
    stake_snapshot = utils.get_file_data(CONFIG['save_file_prefix']['stake_snapshot'])
    results = stake_snapshot.get('results', {})

    stakers_boost_weight = {}

    for staker, records in results.items():
        for record in records.get('Records', []):
            if record['Start Block'] < block_number <= record.get('End Block', 0):
                if record.get('Boost Weight', 0) != 0:
                    stakers_boost_weight[staker]=record.get('Boost Weight')
                    break
    if len(stakers_boost_weight) != 0:
        print(json.dumps(stakers_boost_weight, indent=2))
        return stakers_boost_weight
    return None
    
#distribute_incentive()
get_boost_weight(2581404)
balance = nodeOperation.get_raw_balance('0x7905e5d80722702b7c1816b3c38b6a893ed809bd', '0x6969696969696969696969696969696969696969')
print(balance)

