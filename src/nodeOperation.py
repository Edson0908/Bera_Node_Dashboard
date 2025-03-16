import json
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv(override=True)

BERA_RPC_URL = os.getenv('BERA_RPC_URL')
web3 = Web3(Web3.HTTPProvider(BERA_RPC_URL))


def load_config():
    config_dir = 'config'
    config_file = os.path.join(config_dir, 'config.json')
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config

def claim_honey_rewards():
    config = load_config()
    
    contract_address = config.get('contracts', {}).get('BGT Staker', {}).get('address')
    contract_abi = config.get('contracts', {}).get('BGT Staker', {}).get('abi')
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)

    # 获取当前区块
    current_block = web3.eth.block_number
    print(f"当前区块: {current_block}")

if __name__ == "__main__":
    claim_honey_rewards()



