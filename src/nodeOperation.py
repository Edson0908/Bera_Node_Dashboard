import json
import os
from web3 import Web3
from dotenv import load_dotenv
import asyncio

load_dotenv(override=True)

BERA_RPC_URL = os.getenv('BERA_RPC_URL')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')

web3 = Web3(Web3.HTTPProvider(BERA_RPC_URL))


def load_config():
    config_dir = 'config'
    config_file = os.path.join(config_dir, 'config.json')
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config

def get_current_block():
    
    current_block = web3.eth.block_number
    print(f"当前区块: {current_block}")

    return current_block

def get_unclaimed_honey_rewards():
    config = load_config()
    address = config['nodeInfo']['operator_address']
   
    contract_address = config.get('contracts', {}).get('BGT Staker', {}).get('address')
    contract_abi = config.get('contracts', {}).get('BGT Staker', {}).get('abi')
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    balance = contract.functions.earned(address).call() / (10 ** 18)
    print(f"未领取的honey奖励: {balance}")
    return balance

async def claim_honey_rewards():
    config = load_config()
    
    contract_address = config.get('contracts', {}).get('BGT Staker', {}).get('address')
    contract_abi = config.get('contracts', {}).get('BGT Staker', {}).get('abi')
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)

    tx_params = {
        'from': config['nodeInfo']['operator_address'],
        'gas': 200000,
        'gasPrice': web3.eth.gas_price,
        'nonce': web3.eth.get_transaction_count(config['nodeInfo']['operator_address'])
    }
    tx = contract.functions.getReward().buildTransaction(tx_params)
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    # 等待交易确认
    try:
        receipt = await web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)  # 120秒超时
        if receipt['status'] == 1:
            print(f"交易确认成功，区块号: {receipt['blockNumber']}")
            return receipt
        else:
            print("交易执行失败")
            return None
    except Exception as e:
        print(f"等待交易确认时出错: {str(e)}")
        return None


def get_boosted_amount(address):
    config = load_config()
    contract_address = config.get('contracts', {}).get('BGT Token', {}).get('address')
    contract_abi = config.get('contracts', {}).get('BGT Token', {}).get('abi')
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    amount = contract.functions.boosts(address).call() / (10 ** 18)
    print(f"节点{address}的boosted amount: {amount}")

    return amount


def get_honey_balance(address):
    config = load_config()
    contract_address = config.get('contracts', {}).get('HONEY Token', {}).get('address')
    contract_abi = config.get('contracts', {}).get('HONEY Token', {}).get('abi')
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    balance = contract.functions.balanceOf(address).call() / (10 ** 18)
    
    return balance

if __name__ == "__main__":
    #claim_honey_rewards()
    #get_unclaimed_honey_rewards()

    get_boosted_amount('0x40692724326503b8Fdc8472Df7Ee658F4BdbFC89')



