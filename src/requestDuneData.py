import json
import time
from dune_client.types import QueryParameter
from dune_client.client import DuneClient
from dune_client.query import QueryBase
import utils



def query_dune_data(query_id, query_parameters):

    if not utils.DUNE_API_KEY:
        raise ValueError("请在.env文件中设置DUNE_API_KEY")
    
    try:
        dune = DuneClient(utils.DUNE_API_KEY)
        query = QueryBase(
            query_id=query_id,
            params=query_parameters
        )

        if utils.DEBUG_MODE == 'True':
            results = dune.get_latest_result(query_id)
            return results.result.rows

        # 执行查询
        print("开始执行查询...")
        execution_response = dune.execute_query(query=query)
        execution_id = execution_response.execution_id
        
        # 等待结果
        max_attempts = 100  # 最多等待150秒
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
            time.sleep(2)
            
        raise TimeoutError("查询超时")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return None 

def get_commission_rate(staker, amount):
    config = utils.load_config()

    commission_rate = config['commission_rate']
    staker_info = config['staker_info']
    if staker_info[staker]['commission']:
        for key, value in commission_rate.items():
            if amount < int(key):
                return value
    return 0

def init_stake_snapshot():

    config = utils.load_config()

    staker_info = config['staker_info']

    processed_data = {}
    saved_file_prefix = config['save_file_prefix']['stake_snapshot']
    
    query_id = utils.QUERY_STAKE_BY_PUBKEY
    validator_pubkey1 = config['nodeInfo']['pubkey1']
    validator_pubkey2 = config['nodeInfo']['pubkey2']
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


    utils.save_results_to_json(processed_data, saved_file_prefix)

def bgt_rewards_snapshot(validator_pubkey, start_block, end_block):

    query_id = utils.QUERY_BGT_REWARDS_SNAPSHOT
    
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

    config = utils.load_config()
    saved_file_prefix = config['save_file_prefix']['validator_overview']
    query_id = utils.QUERY_VALIDATOR_OVERVIEW
    validator_pubkey1 = config['nodeInfo']['pubkey1']
    validator_pubkey2 = config['nodeInfo']['pubkey2']
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
        utils.save_results_to_json(results, saved_file_prefix)    
    else:
        print("未能获取查询结果")   



def update_stake_snapshot(txId):

    if txId is None:
        return None

    config = utils.load_config()

    validator_pubkey2 = config['nodeInfo']['pubkey2']

    saved_file_prefix = config['save_file_prefix']['stake_snapshot']

    try:
        query_id = utils.QUERY_STAKE_BY_TXID
        query_parameters = [
            QueryParameter.text_type(
                name="txid",
                value= txId
            )
        ]

        results = query_dune_data(query_id, query_parameters)
        new_stake = results[0]

        """读取最新的 stake_snapshot 文件并更新数据"""
        # 获取最新的文件
        existing_data = utils.get_file_data(saved_file_prefix)
        existing_data = existing_data['results']

        bgt_rewards = 0

        if new_stake['staker'] in existing_data.keys():
            for key,value in existing_data.items():
                if key == new_stake['staker']:
                    bera_staked = value['Records'][-1]['BERA Staked'] + new_stake['amount']
                else:
                    bera_staked = value['Records'][-1]['BERA Staked']
                start_block = value['Records'][-1]['Start Block']
                total_staked = value['Records'][-1]['Total Staked'] + new_stake['amount']
                weight = bera_staked / total_staked
                if bgt_rewards == 0:
                    bgt_rewards_result = bgt_rewards_snapshot(validator_pubkey2, start_block, new_stake['blockNumber'])
                    bgt_rewards = bgt_rewards_result[0].get('bgt_rewards', 0)
                value['Records'][-1]['End Block'] = new_stake['blockNumber']
                value['Records'][-1]['Total BGT Rewards'] = bgt_rewards
                value['Records'][-1]['Staker BGT Rewards'] = value['Records'][-1]['Total BGT Rewards'] * value['Records'][-1]['Weight']
                value['Records'][-1]['Commission'] = value['Records'][-1]['Staker BGT Rewards'] * value['Records'][-1]['Commission Rate']
                value['Records'][-1]['BGT Rewards'] = value['Records'][-1]['Staker BGT Rewards'] - value['Records'][-1]['Commission']
                value['Records'].append({
                    "BERA Staked": bera_staked,
                    "Start Block": new_stake['blockNumber'],
                    "Total Staked": total_staked,
                    "Weight": weight,
                    "Commission Rate": get_commission_rate(key, bera_staked)
                })       
        else:
            for key,value in existing_data.items():
                start_block = value['Records'][-1]['Start Block']
                bera_staked = value['Records'][-1]['BERA Staked']
                total_staked = value['Records'][-1]['Total Staked'] + new_stake['amount']
                weight = bera_staked / total_staked
                if bgt_rewards == 0:
                    bgt_rewards_result = bgt_rewards_snapshot(validator_pubkey2, start_block, new_stake['blockNumber'])
                    bgt_rewards = bgt_rewards_result[0].get('bgt_rewards', 0)
                value['Records'][-1]['End Block'] = new_stake['blockNumber']
                value['Records'][-1]['Total BGT Rewards'] = bgt_rewards
                value['Records'][-1]['Staker BGT Rewards'] = value['Records'][-1]['Total BGT Rewards'] * value['Records'][-1]['Weight']
                value['Records'][-1]['Commission'] = value['Records'][-1]['Staker BGT Rewards'] * value['Records'][-1]['Commission Rate']
                value['Records'][-1]['BGT Rewards'] = value['Records'][-1]['Staker BGT Rewards'] - value['Records'][-1]['Commission']
                value['Records'].append({
                    "BERA Staked": bera_staked,
                    "Start Block": new_stake['blockNumber'],
                    "Total Staked": total_staked,
                    "Weight": weight,
                    "Commission Rate": get_commission_rate(key, bera_staked)
                })

            existing_data[new_stake['staker']] = {}
            existing_data[new_stake['staker']]['Records'] = []
            existing_data[new_stake['staker']]['Records'].append({
                "BERA Staked": new_stake['amount'],
                "Start Block": new_stake['blockNumber'],
                "Total Staked": total_staked,
                "Weight": new_stake['amount'] / total_staked,
                "Commission Rate": get_commission_rate(new_stake['staker'], new_stake['amount'])
            })

        # 保存更新后的数据
        utils.save_results_to_json(existing_data, saved_file_prefix)
        print("数据已更新并保存")
        return None
        
    except Exception as e:
        print(f"更新数据时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def calculate_honey_rewards():

    config = utils.load_config()

    saved_file_prefix = config['save_file_prefix']['stake_snapshot']
    processed_index_prefix = config['save_file_prefix']['processed_index']

    data = utils.get_file_data(saved_file_prefix)
    data = data['results']

    last_processed_record = utils.get_file_data(processed_index_prefix)
    if last_processed_record is not None:
        last_processed_record = last_processed_record['results']
    else:
        last_processed_record = {}


    for key, value in data.items():
        index = last_processed_record.get(key, None)
        if index is None:
            index = 0
        else:
            index += 1
        
        staker_total_honey_reward = value.get('Total Honey Rewards', 0)

        while index < len(value['Records']):
            record = value['Records'][index]
            if record.get('Total Boosted', None) is None:
                break
            else:
                record['Total Honey Rewards'] = get_total_honey_reward(record.get('End Block')) #节点在该时段获得的总HONEY
                record['Staker Honey Rewards'] = record['Total Honey Rewards'] * record['Boost Weight'] #Staker在该时段获得的HONEY
                record['Honey Commission'] = record['Staker Honey Rewards'] * record['Commission Rate'] #Staker在该时段的HONEY奖励
                record['Honey Rewards'] = record['Staker Honey Rewards'] - record['Honey Commission'] #Staker在该时段扣除commission后的HONEY奖励
                staker_total_honey_reward += record['Honey Rewards'] #Staker lifetime HONEY 奖励
                index += 1

        last_processed_record[key] = index
        value['Total Honey Rewards'] = staker_total_honey_reward
 
     # 保存更新后的数据
    utils.save_results_to_json(data, saved_file_prefix)
    utils.save_results_to_json(last_processed_record, processed_index_prefix)
    print("数据已更新并保存")
    return None

def get_total_honey_reward(end_block):

    config = utils.load_config()

    saved_file_prefix = config['save_file_prefix']['honey_rewards_claimed']

    data = utils.get_file_data(saved_file_prefix)
    if data is not None:
        data = data['results']
        value = data.get(end_block, 0)
    else:
        value = 0

    return value



if __name__ == "__main__":

    validator_overview()
    init_stake_snapshot()
    
    #update_stake_snapshot()
