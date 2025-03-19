import json
import os
from web3 import Web3
from dotenv import load_dotenv

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

def claim_honey_rewards():
    config = load_config()
    
    contract_address = config.get('contracts', {}).get('BGT Staker', {}).get('address')
    contract_abi = config.get('contracts', {}).get('BGT Staker', {}).get('abi')
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)

    tx = contract.functions.getReward().buildTransaction()
    tx['from'] = config['nodeInfo']['operator_address']
    tx['gas'] = 200000
    tx['gasPrice'] = web3.eth.gas_price
    tx['nonce'] = web3.eth.get_transaction_count(tx['from'])
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"交易哈希: {tx_hash.hex()}")
    # 获取当前区块

if __name__ == "__main__":
    #claim_honey_rewards()
    get_unclaimed_honey_rewards()



