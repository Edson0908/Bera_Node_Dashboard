import utils
import json
import nodeOperation
import time
CONFIG = utils.load_config()

def distribute_incentive():
    staker_info = CONFIG['staker_info']
    filename = CONFIG['save_file_prefix']['incentive_data']
    incentive_data = utils.get_file_data(filename)

    if incentive_data is None:
        print('没有激励数据')
        return
    
    # 记录处理状态
    processing_status = {
        'total_blocks': len(incentive_data),
        'processed_blocks': 0,
        'failed_transactions': [],
        'start_time': time.time()
    }

    for block_number, data in incentive_data.items():
        if data.get('distributed', False):
            processing_status['processed_blocks'] += 1
            continue
            
        rewards = data.get('rewards', [])
        if len(rewards) == 0:
            processing_status['processed_blocks'] += 1
            continue
            
        stakers_boost_weight = get_boost_weight(block_number)
        if stakers_boost_weight is None:
            print(f"区块 {block_number} 没有找到质押者权重数据")
            processing_status['processed_blocks'] += 1
            continue
        
        total_stakers_num = len(stakers_boost_weight)
        total_rewards_num = len(rewards)
        reward_index = 0
        
        for reward in rewards:
            if reward.get('distributed', False):
                continue
                
            index = 0
            failed_stakers = []
            
            for staker, boost_weight in stakers_boost_weight.items():
                if reward.get('transfer', {}).get(staker, None) is not None:
                    index += 1
                    continue

                if 'transfer' not in reward:
                    reward['transfer'] = {}
                    
                reward_address = staker_info[staker]['reward_address']
                amount = int(float(reward.get('amount', 0)) * float(boost_weight))
                
                if amount <= 0:
                    print(f"跳过金额为0的转账: {staker}")
                    index += 1
                    continue
                    
                print(f"正在处理区块 {block_number} 的奖励，接收者: {staker}, 金额: {amount}")
                
                while True:
                    try:
                        tx_hash = nodeOperation.transfer_erc20_token(reward.get('token'), reward_address, amount)
                        if tx_hash is not None:
                            reward['transfer'][staker] = {
                                'tx_hash': tx_hash,
                                'to': reward_address,
                                'amount': amount,
                                'status': 'success'
                            }
                            index += 1
                            break
                        else:
                            print(f"交易失败，将在30秒后重试...")
                            time.sleep(30)
                    except Exception as e:
                        print(f"转账失败: {e}")
                        print("将在30秒后重试...")
                        time.sleep(30)
                        continue
            
            # 记录失败情况
            if failed_stakers:
                processing_status['failed_transactions'].append({
                    'block_number': block_number,
                    'reward_index': reward_index,
                    'failed_stakers': failed_stakers
                })
            
            if index == total_stakers_num:
                reward['distributed'] = True
                reward_index += 1
        
        if reward_index == total_rewards_num:
            data['distributed'] = True
            print(f'区块 {block_number} 激励数据分发完成')
            
        processing_status['processed_blocks'] += 1
        
        # 打印处理进度
        progress = (processing_status['processed_blocks'] / processing_status['total_blocks']) * 100
        print(f"处理进度: {progress:.2f}% ({processing_status['processed_blocks']}/{processing_status['total_blocks']})")
    
    # 打印最终处理报告
    end_time = time.time()
    duration = end_time - processing_status['start_time']
    print("\n=== 处理完成报告 ===")
    print(f"总处理时间: {duration:.2f} 秒")
    print(f"总区块数: {processing_status['total_blocks']}")
    print(f"成功处理区块数: {processing_status['processed_blocks']}")
    print(f"失败交易数: {len(processing_status['failed_transactions'])}")
    
    if processing_status['failed_transactions']:
        print("\n失败交易详情:")
        for fail in processing_status['failed_transactions']:
            print(f"区块 {fail['block_number']} 的奖励 {fail['reward_index']}:")
            for staker in fail['failed_stakers']:
                print(f"  - {staker['staker']}: {staker['error']}")

    utils.update_json_file(filename, incentive_data)

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

