import utils
import json
import nodeOperation
import time
import os
from datetime import datetime

CONFIG = utils.load_config()

def distribute_incentive():
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
                    
                    reward_address = staker_info[staker]['reward_address']
                    amount = int(float(reward.get('amount', 0)) * float(boost_weight))
                    
                    print(f"正在处理区块 {block_number} 的奖励，Token: {reward.get('token')}, 接收者: {reward_address}, 金额: {amount}")
                    
                    max_retry = 3
                    while max_retry > 0:
                        try:
                            tx_hash = nodeOperation.transfer_erc20_token(reward.get('token'), reward_address, amount)
                            
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


def distribute_honey():
    staker_info = CONFIG['staker_info']
    file_prefix = CONFIG['save_file_prefix']['honey_rewards_claimed']
    honey_transfer_data_file = CONFIG['save_file_prefix']['honey_transfer_data']
    honey_token = CONFIG['contracts']['HONEY Token']['address']
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


                for staker, boost_weight in stakers_boost_weight.items():

                    if 'transfer' not in reward:
                        reward['transfer'] = {}

                    if reward.get('transfer').get(staker, None) is not None:
                        amount = reward.get('transfer').get(staker).get('amount', 0)
                    else:
                        amount = int(float(reward.get('amount', 0)) * float(boost_weight))
                        reward['transfer'][staker] = {
                            'to': staker_info[staker]['reward_address'],
                            'amount': amount,
                        }
                    if reward.get('transfer').get(staker).get('tx_hash', None) is None:
                        if transfer_data.get(staker, None) is not None:
                            transfer_data[staker]['amount'] += amount
                        else:
                            transfer_data[staker] = {
                                'to': staker_info[staker]['reward_address'],
                                'amount': amount,
                            }
                        if transfer_data.get(staker).get('source', None) is None:
                            transfer_data[staker]['source'] = []
                        transfer_data[staker]['source'].append(file)
                
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
                    stakers_boost_weight[staker]=record.get('Boost Weight')
                    break
    if len(stakers_boost_weight) != 0:
        print(json.dumps(stakers_boost_weight, indent=2))
        return stakers_boost_weight
    return None


if __name__ == "__main__":

    distribute_incentive()

