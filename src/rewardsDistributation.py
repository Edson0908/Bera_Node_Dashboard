import utils
import json
import nodeOperation
import time
import os
from datetime import datetime

CONFIG = utils.load_config()
DEBUG = False

def distribute_incentive():
    # 没有计算commission，单独transfer

    staker_info = CONFIG['staker_info']
    file_prefix = CONFIG['save_file_prefix']['incentive_data']
    data_dir = 'data/incentive'

    try:
        json_files = [f for f in os.listdir(data_dir) if f.startswith(file_prefix) and f.endswith('.json')]

        if len(json_files) == 0:
            print('没有激励数据')
            return
        # 记录处理状态
        processing_status = {
            'total_incentive_file': len(json_files),
            'processed_with_success': 0,
            'processed_with_failed': 0,
            'failed_incentive_file': [],
            'start_time': time.time()
        }
        
        for file in json_files:
            file_path = os.path.join(data_dir, file)
            print(f"正在处理文件: {file}")

            with open(file_path, 'r', encoding='utf-8') as f:
                incentive_data = json.load(f)
                incentive_data = incentive_data.get('results')
                print(json.dumps(incentive_data, indent=2))

                block_number = list(incentive_data.keys())[0]
                reward = incentive_data.get(block_number)
                
                stakers_boost_weight = get_boost_weight(block_number)

                if stakers_boost_weight is None:
                    print(f"区块 {block_number} 没有找到质押者权重数据")
                    continue

                total_stakers_num = len(stakers_boost_weight)
                index = 0
                for staker, boost_weight in stakers_boost_weight.items():

                    if reward.get('transfer', {}).get(staker, None) is not None:
                        index += 1
                        continue

                    if 'transfer' not in reward:
                        reward['transfer'] = {}
                    
                    reward_address = staker_info[staker]['swap_address']
                    amount = int(float(reward.get('amount', 0)) * float(boost_weight))
                    
                    print(f"正在处理区块 {block_number} 的奖励，Token: {reward.get('token')}, 接收者: {reward_address}, 金额: {amount}")
                    
                    max_retry = 3
                    while max_retry > 0:
                        try:
                            if not DEBUG:
                                tx_hash = nodeOperation.transfer_erc20_token(reward.get('token'), reward_address, amount)
                            else:
                                tx_hash = '0x1234567890abcdef'

                            if tx_hash is not None:
                                reward['transfer'][staker] = {
                                    'tx_hash': tx_hash,
                                    'to': reward_address,
                                    'amount': amount,
                                }
                                index += 1
                                break
                            else:
                                print(f"交易失败，将在15秒后重试...")
                                time.sleep(15)
                                max_retry -= 1
                        except Exception as e:
                            print(f"转账失败: {e}")
                            print("将在15秒后重试...")
                            time.sleep(15)
                            max_retry -= 1

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': datetime.now().isoformat(),
                        'results': incentive_data
                    }, f, ensure_ascii=False, indent=2)

                if index == total_stakers_num:
                    print(f'区块 {block_number} 激励数据分发完成')
                    new_file = f'processed_{file}'
                    utils.rename_file(file, new_file, data_dir)
                    processing_status['processed_with_success'] += 1
                else:
                    processing_status['processed_with_failed'] += 1
                    processing_status['failed_incentive_file'].append(file)
        
        # 打印最终处理报告
        end_time = time.time()
        duration = end_time - processing_status['start_time']
        print("\n=== 处理完成报告 ===")
        print(f"总处理时间: {duration:.2f} 秒")
        print(f"总文件数: {processing_status['total_incentive_file']}")
        print(f"成功处理文件数: {processing_status['processed_with_success']}")
        print(f"失败文件数: {len(processing_status['failed_incentive_file'])}")
    
        if processing_status['failed_incentive_file']:
            print("\n失败详情:")
            for fail in processing_status['failed_incentive_file']:
                print(f"文件: {fail}")

    except Exception as e:
        print(f"处理incentive数据失败: {e}")
        return


def distribute_incentive_V2():
    # 计算commission，合并transfer

    distribute_commission = False

    staker_info = CONFIG['staker_info']
    file_prefix = CONFIG['save_file_prefix']['incentive_data']
    incentive_transfer_data_file = CONFIG['save_file_prefix']['incentive_transfer_data']
    commission_address = CONFIG['nodeInfo']['commission_address']
    operator_address = CONFIG['nodeInfo']['operator_address']
    data_dir = 'data/incentive'

    try:
        json_files = [f for f in os.listdir(data_dir) if f.startswith(file_prefix) and f.endswith('.json')]

        if len(json_files) == 0:
            print('没有激励数据')
            return
        # 记录处理状态
        processing_status = {
            'total_incentive_file': len(json_files),
            'processed_with_success': 0,
            'processed_with_failed': 0,
            'start_time': time.time()
        }

        transfer_data = {}
        
        for file in json_files:
            file_path = os.path.join(data_dir, file)
            print(f"正在处理文件: {file}")

            with open(file_path, 'r', encoding='utf-8') as f:
                incentive_data = json.load(f)
                incentive_data = incentive_data.get('results')
                #print(json.dumps(incentive_data, indent=2))

                block_number = list(incentive_data.keys())[0]
                reward = incentive_data.get(block_number)
                token = reward.get('token')
                
                stakers_boost_weight = get_boost_weight(block_number)

                if stakers_boost_weight is None:
                    print(f"区块 {block_number} 没有找到质押者权重数据")
                    continue

                #total_stakers_num = len(stakers_boost_weight)
                #index = 0
                total_commission_amount = 0
                for staker, staker_value in stakers_boost_weight.items():

                    if 'transfer' not in reward:
                        reward['transfer'] = {}

                    if reward.get('transfer').get(staker, None) is not None:
                        amount = reward.get('transfer').get(staker).get('amount', 0)
                        commission_amount = reward.get('transfer').get(staker).get('commission', 0)
                    else:
                        amount = int(float(reward.get('amount', 0)) * float(staker_value.get('boost_weight')))
                        
                        if distribute_commission:
                            commission_amount = int(float(amount) * float(staker_value.get('commission_rate')))
                            amount -= commission_amount
                        else:
                            commission_amount = 0
                        
                        reward['transfer'][staker] = {
                            'to': staker_info[staker]['swap_address'],
                            'amount': amount,
                            'commission': commission_amount
                        }
                    total_commission_amount += commission_amount

                    if reward.get('transfer').get(staker).get('tx_hash', None) is None:
                        
                        if transfer_data.get(staker, None) is not None:
                            if transfer_data[staker].get('rewards', None) is not None:
                                if transfer_data[staker]['rewards'].get(token, None) is not None:
                                    transfer_data[staker]['rewards'][token]['amount'] += amount
                                else:
                                    transfer_data[staker]['rewards'][token] = {
                                        'amount': amount,
                                    }
                            else:
                                transfer_data[staker]['rewards'] = {
                                    token : {
                                        'amount': amount,
                                    }
                                }
                        else:
                            transfer_data[staker] = {
                                'to': staker_info[staker]['swap_address'],
                                'rewards': {
                                    token: {
                                        'amount': amount,
                                    }
                                }
                            }

                        if transfer_data.get(staker).get('rewards').get(token).get('source', None) is None:
                            transfer_data[staker]['rewards'][token]['source'] = []
                        transfer_data[staker]['rewards'][token]['source'].append(file)
                
                if distribute_commission:

                    if reward.get('transfer').get(operator_address, None) is None:
                        reward['transfer'][operator_address] = {
                            'to': commission_address,
                            'amount': total_commission_amount,
                        }   
                    if reward.get('transfer').get(operator_address).get('tx_hash', None) is None:
                        if transfer_data.get(operator_address, None) is not None:
                            if transfer_data[operator_address].get('rewards', None) is not None:
                                if transfer_data[operator_address]['rewards'].get(token, None) is not None:
                                    transfer_data[operator_address]['rewards'][token]['amount'] += total_commission_amount
                                else:
                                    transfer_data[operator_address]['rewards'][token] = {
                                        'amount': total_commission_amount,
                                    }
                            else:
                                transfer_data[operator_address]['rewards'] = {
                                    token: {
                                        'amount': total_commission_amount,
                                    }
                                }
                        else:
                            transfer_data[operator_address] = {
                                'to': commission_address,
                                'rewards': {
                                    token: {
                                        'amount': total_commission_amount,
                                    }
                                }
                            }
                        if transfer_data.get(operator_address).get('rewards').get(token).get('source', None) is None:
                            transfer_data[operator_address]['rewards'][token]['source'] = []
                        transfer_data[operator_address]['rewards'][token]['source'].append(file)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': datetime.now().isoformat(),
                        'results': incentive_data
                    }, f, ensure_ascii=False, indent=2)
                    
        for staker, data in transfer_data.items():
            reward_address = data['to']

            for token, token_data in data['rewards'].items():
                amount = token_data['amount']

                max_retry = 3
                while max_retry > 0:
                    try:
                        if not DEBUG:
                            tx_hash = nodeOperation.transfer_erc20_token(token, reward_address, amount)
                        else:
                            tx_hash = '0x1234567890abcdef'
                        
                        if tx_hash is not None:
                            token_data['tx_hash'] = tx_hash
                            
                            for file in token_data['source']:
                                file_path = os.path.join(data_dir, file)
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    incentive_data = json.load(f)
                                    incentive_data = incentive_data.get('results')
                                    block_number = list(incentive_data.keys())[0]
                                    reward = incentive_data.get(block_number)
                                    reward['transfer'][staker]['tx_hash'] = tx_hash

                                with open(file_path, 'w', encoding='utf-8') as f:
                                    json.dump({
                                        'timestamp': datetime.now().isoformat(),
                                        'results': incentive_data
                                    }, f, ensure_ascii=False, indent=2)
                            break
                        else:
                            print(f"交易失败，将在15秒后重试...")
                            time.sleep(15)
                            max_retry -= 1
                    except Exception as e:
                        print(f"转账失败: {e}")
                        print("将在15秒后重试...")
                        time.sleep(15)
                        max_retry -= 1
        utils.save_results_to_json(transfer_data, incentive_transfer_data_file, 'incentive')

        for file in json_files:
            file_path = os.path.join(data_dir, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                incentive_data = json.load(f)
                incentive_data = incentive_data.get('results')
                block_number = list(incentive_data.keys())[0]
                reward = incentive_data.get(block_number)   

                not_completed = False
                for staker, data in reward['transfer'].items():
                    if data.get('tx_hash', None) is None:
                        not_completed = True
                        processing_status['processed_with_failed'] += 1
                        break
                if not not_completed:
                    processing_status['processed_with_success'] += 1
                    new_file = f'processed_{file}'
                    utils.rename_file(file, new_file, data_dir)
        
        # 打印最终处理报告
        end_time = time.time()
        duration = end_time - processing_status['start_time']
        print("\n=== 处理完成报告 ===")
        print(f"总处理时间: {duration:.2f} 秒")
        print(f"总文件数: {processing_status['total_incentive_file']}")
        print(f"成功处理文件数: {processing_status['processed_with_success']}")
        print(f"失败文件数: {processing_status['processed_with_failed']}")

    

    except Exception as e:
        print(f"处理incentive数据失败: {e}")
        return


def distribute_honey():

    distribute_commission = False

    staker_info = CONFIG['staker_info']
    file_prefix = CONFIG['save_file_prefix']['honey_rewards_claimed']
    honey_transfer_data_file = CONFIG['save_file_prefix']['honey_transfer_data']
    honey_token = CONFIG['contracts']['HONEY Token']['address']
    commission_address = CONFIG['nodeInfo']['commission_address']
    operator_address = CONFIG['nodeInfo']['operator_address']
    data_dir = 'data/honey'

    try:
        json_files = [f for f in os.listdir(data_dir) if f.startswith(file_prefix) and f.endswith('.json')]

        if len(json_files) == 0:
            print('没有Honey Rewards数据')
            return
        
        transfer_data = {}

        for file in json_files:
            file_path = os.path.join(data_dir, file)
            print(f"正在处理文件: {file}")

            with open(file_path, 'r', encoding='utf-8') as f:
                honey_data = json.load(f)
                honey_data = honey_data.get('results')

                block_number = list(honey_data.keys())[0]
                reward = honey_data.get(block_number)
                
                stakers_boost_weight = get_boost_weight(block_number)

                if stakers_boost_weight is None:
                    print(f"区块 {block_number} 没有找到质押者权重数据")
                    continue

                total_commission_amount = 0

                for staker, staker_value in stakers_boost_weight.items():

                    if 'transfer' not in reward:
                        reward['transfer'] = {}

                    if reward.get('transfer').get(staker, None) is not None:
                        amount = reward.get('transfer').get(staker).get('amount', 0)
                        commission_amount = reward.get('transfer').get(staker).get('commission', 0)
                    else:
                        amount = int(float(reward.get('amount', 0)) * float(staker_value.get('boost_weight')))
                        commission_rate = staker_value.get('commission_rate')
                        if distribute_commission:
                            commission_amount = int(float(amount) * float(commission_rate))
                            amount -= commission_amount
                        else:
                            commission_amount = 0
                            
                        reward['transfer'][staker] = {
                            'to': staker_info[staker]['swap_address'],
                            'amount': amount,
                            'commission': commission_amount
                        }
                    total_commission_amount += commission_amount
                    if reward.get('transfer').get(staker).get('tx_hash', None) is None:
                        if transfer_data.get(staker, None) is not None:
                            transfer_data[staker]['amount'] += amount
                        else:
                            transfer_data[staker] = {
                                'to': staker_info[staker]['swap_address'],
                                'amount': amount,
                            }
                        if transfer_data.get(staker).get('source', None) is None:
                            transfer_data[staker]['source'] = []
                        transfer_data[staker]['source'].append(file)

                if distribute_commission:
                    if reward.get('transfer').get(operator_address, None) is None:
                        reward['transfer'][operator_address] = {
                            'to': commission_address,
                            'amount': total_commission_amount,
                        }
                    if reward.get('transfer').get(operator_address).get('tx_hash', None) is None:
                        if transfer_data.get(operator_address, None) is not None:
                            transfer_data[operator_address]['amount'] += total_commission_amount
                        else:
                            transfer_data[operator_address] = {
                                'to': commission_address,
                                'amount': total_commission_amount,
                            }
                        if transfer_data.get(operator_address).get('source', None) is None:
                            transfer_data[operator_address]['source'] = []
                        transfer_data[operator_address]['source'].append(file)
                    
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': datetime.now().isoformat(),
                        'results': honey_data
                    }, f, ensure_ascii=False, indent=2)

        for staker, data in transfer_data.items():
            reward_address = data['to']
            amount = data['amount']
            print(f"正在处理 {staker} 的HONEY奖励，接收地址: {reward_address}, 金额: {amount}")

            max_retry = 3
            while max_retry > 0:
                try:
                    tx_hash = nodeOperation.transfer_erc20_token(honey_token, reward_address, amount)
                    if tx_hash is not None:
                        data['tx_hash'] = tx_hash

                        for file in data['source']:
                            file_path = os.path.join(data_dir, file)
                            print(f"回写TxHash: {tx_hash} 到文件: {file}")
                            with open(file_path, 'r', encoding='utf-8') as f:
                                honey_data = json.load(f)
                                honey_data = honey_data.get('results')
                                block_number = list(honey_data.keys())[0]
                                reward = honey_data.get(block_number)
                                reward['transfer'][staker]['tx_hash'] = tx_hash

                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump({
                                    'timestamp': datetime.now().isoformat(),
                                    'results': honey_data
                                }, f, ensure_ascii=False, indent=2)
                        break
                    else:
                        print(f"交易失败，将在15秒后重试...")
                        time.sleep(15)
                        max_retry -= 1
                except Exception as e:
                    print(f"转账失败: {e}")
                    print("将在15秒后重试...")
                    time.sleep(15)
                    max_retry -= 1

        #转账记录
        utils.save_results_to_json(transfer_data, honey_transfer_data_file, 'honey')
        #更新honey_rewards_claimed
        for file in json_files:
            file_path = os.path.join(data_dir, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                honey_data = json.load(f)
                honey_data = honey_data.get('results')
                block_number = list(honey_data.keys())[0]
                reward = honey_data.get(block_number)

            not_completed = False
            for staker, data in reward['transfer'].items():
                if data.get('tx_hash', None) is None:
                    not_completed = True
                    break
            if not not_completed:
                new_file = f'processed_{file}'
                utils.rename_file(file, new_file, data_dir)

    except Exception as e:
        print(f"处理honey数据失败: {e}")
        return        

def get_boost_weight(block_number):
    
    stake_snapshot = utils.get_file_data(CONFIG['save_file_prefix']['stake_snapshot'])
    results = stake_snapshot.get('results', {})

    stakers_boost_weight = {}
    block_number = int(block_number)  # 确保 block_number 是整数类型

    for staker, records in results.items():
        for record in records.get('Records', []):
            if record['Start Block'] < block_number <= record.get('End Block', 0):
                if record.get('Boost Weight', 0) != 0:
                    stakers_boost_weight[staker] = {
                        'boost_weight': record.get('Boost Weight'),
                        'commission_rate': record.get('Commission Rate')
                    }
                    break
    if len(stakers_boost_weight) != 0:
        print(json.dumps(stakers_boost_weight, indent=2))
        return stakers_boost_weight
    return None


if __name__ == "__main__":

    distribute_incentive_V2()

