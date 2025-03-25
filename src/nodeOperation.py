from web3 import Web3
import utils

PRIVATE_KEY = utils.PRIVATE_KEY

web3 = Web3(Web3.HTTPProvider(utils.BERA_RPC_URL))


def get_current_block():
    
    current_block = web3.eth.block_number
    print(f"当前区块: {current_block}")

    return current_block

def get_unclaimed_honey_rewards():
    config = utils.load_config()
    address = config['nodeInfo']['operator_address']
   
    contract_address = config.get('contracts', {}).get('BGT Staker', {}).get('address')
    contract_abi = config.get('contracts', {}).get('BGT Staker', {}).get('abi')
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    balance = contract.functions.earned(address).call() / (10 ** 18)
    print(f"未领取的honey奖励: {balance}")
    return balance

def claim_honey_rewards():
    config = utils.load_config()
    
    contract_address = config.get('contracts', {}).get('BGT Staker', {}).get('address')
    contract_abi = config.get('contracts', {}).get('BGT Staker', {}).get('abi')
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)

    tx_params = {
        'from': config['nodeInfo']['operator_address'],
        'gas': 200000,
        'gasPrice': web3.eth.gas_price,
        'nonce': web3.eth.get_transaction_count(config['nodeInfo']['operator_address'])
    }
    tx = contract.functions.getReward().build_transaction(tx_params)
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"交易已发送，交易哈希: {tx_hash.hex()}")
    print("等待交易确认中...")

    # 等待交易确认
    try:
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)  # 120秒超时
        if receipt['status'] == 1:
            print(f"交易确认成功！区块号: {receipt['blockNumber']}")
            print(f"Gas使用量: {receipt['gasUsed']}")
            print("奖励已成功领取")
            return receipt
        else:
            print("交易执行失败，请检查合约状态")
            return None
    except Exception as e:
        print(f"等待交易确认时出错: {str(e)}")
        return None


def get_boosted_amount(node_address):
    config = utils.load_config()
    contract_address = config.get('contracts', {}).get('BGT Token', {}).get('address')
    contract_abi = config.get('contracts', {}).get('BGT Token', {}).get('abi')
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    amount = contract.functions.boosts(node_address).call() / (10 ** 18)
    print(f"节点{node_address}的boosted amount: {amount}")

    return amount


def get_honey_balance(address):
    config = utils.load_config()
    contract_address = config.get('contracts', {}).get('HONEY Token', {}).get('address')
    contract_abi = config.get('contracts', {}).get('HONEY Token', {}).get('abi')
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    balance = contract.functions.balanceOf(address).call() / (10 ** 18)
    
    return balance

if __name__ == "__main__":
    #claim_honey_rewards()
    #get_unclaimed_honey_rewards()

    get_boosted_amount('0x')



