import dotenv
import os
import json
import time
from datetime import datetime
from dune_client.types import QueryParameter
from dune_client.client import DuneClient
from dune_client.query import QueryBase
import copy

# 加载环境变量
dotenv.load_dotenv(override=True)

DUNE_API_KEY = os.getenv('DUNE_API_KEY')


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

        # 执行查询
        print("开始执行查询...")
        execution_response = dune.execute_query(query=query)
        execution_id = execution_response.execution_id
        
        # 等待结果
        max_attempts = 60  # 最多等待60秒
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

def init_stake_snapshot():

    total_stake = 0
    processed_results = {
        "Stakers": {},
        "Snapshot": {},
        "Snapshot2": []
    }
    saved_file_prefix = "stake_snapshot"
    query_id = os.getenv('QUERY_STAKE_BY_PUBKEY')
    validator_pubkey1 = os.getenv('VALIDATOR_PUBKEY1')
    validator_pubkey2 = os.getenv('VALIDATOR_PUBKEY2')

    query_parameters = [
        QueryParameter.text_type(
            name="pubkey1",
            value= validator_pubkey1
        )
    ]

    results = query_dune_data(query_id, query_parameters)
    if results:
        print("查询结果：")
        print(json.dumps(results, indent=2, ensure_ascii=False))

        prev_amount = 0
        prev_records = {}
        index = 0
        prev_staked = 0

        for item in results:
            
            total_stake += item['amount']

            if item['staker'] not in processed_results["Stakers"].keys():
                processed_results["Stakers"][item['staker']] = {
                    "Records": []
                }
                processed_results["Stakers"][item['staker']]["Total Staked"] = item['amount']

                processed_results["Stakers"][item['staker']]["Records"].append({
                    "Date": item['date'],
                    "Amount": item['amount'],
                    "Block Number": item['blockNumber'],
                    "Tx Hash": item['txID']
                })
            else:
                processed_results["Stakers"][item['staker']]["Total Staked"] += item['amount']
                processed_results["Stakers"][item['staker']]["Records"].append({
                    "Date": item['date'],
                    "Amount": item['amount'],
                    "Block Number": item['blockNumber'],
                    "Tx Hash": item['txID']
                })
            prev_records[item['txID']] = item['amount']            
            processed_results["Snapshot"][item['blockNumber']] = {}

            processed_results["Snapshot"][item['blockNumber']]["Total Staked"] = item['amount'] + prev_amount
            processed_results["Snapshot"][item['blockNumber']]["Records"] = prev_records
            
            prev_amount = processed_results["Snapshot"][item['blockNumber']]["Total Staked"]
            
            prev_records = copy.deepcopy(processed_results["Snapshot"][item['blockNumber']]["Records"])

            # ========
            processed_results["Snapshot2"].append({
                "Start Block": item['blockNumber'],
                "Total Staked": item['amount'] + prev_staked,
                "Stakers": []
            })
            prev_staked = processed_results["Snapshot2"][index]["Total Staked"]

            if index < 1:
                processed_results["Snapshot2"][index]["Stakers"].append({
                    item['staker']:{
                        "Amount": item['amount']
                    }
                })
            else:
                processed_results["Snapshot2"][index]["Stakers"]= copy.deepcopy(processed_results["Snapshot2"][index-1]["Stakers"])
                
                found = False
                for staker in processed_results["Snapshot2"][index]["Stakers"]:
                    if item['staker'] in staker.keys():
                        staker[item['staker']]["Amount"] += item['amount']
                        found = True
                        break
                if not found:
                    processed_results["Snapshot2"][index]["Stakers"].append({
                        item['staker']: {
                            "Amount": item['amount']
                        }
                    })

                processed_results["Snapshot2"][index-1]["End Block"] = item['blockNumber']
                bgt_rewards_result = bgt_rewards_snapshot(validator_pubkey2, processed_results["Snapshot2"][index-1]["Start Block"], item['blockNumber'])
               
                if bgt_rewards_result[0]['bgt_rewards'] is not None:
                    processed_results["Snapshot2"][index-1]["BGT Rewards"] = bgt_rewards_result[0]['bgt_rewards']
                else:
                    processed_results["Snapshot2"][index-1]["BGT Rewards"] = 0
            
            for row in processed_results["Snapshot2"][index]["Stakers"]:
                for key, value in row.items():
                    row[key]["Weight"] = value["Amount"] / processed_results["Snapshot2"][index]["Total Staked"]
                
            index += 1


        print(json.dumps(processed_results, indent=2, ensure_ascii=False))     
        save_results_to_json(processed_results, saved_file_prefix)
        
    else:
        print("未能获取查询结果")

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
    saved_file_prefix = "validator_overview"
    query_id = os.getenv('QUERY_VALIDATOR_OVERVIEW')
    validator_pubkey1 = os.getenv('VALIDATOR_PUBKEY1')
    validator_pubkey2 = os.getenv('VALIDATOR_PUBKEY2')
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

if __name__ == "__main__":

    init_stake_snapshot()
    #validator_overview()
