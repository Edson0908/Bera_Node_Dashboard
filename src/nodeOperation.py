from web3 import Web3
import utils
import requests
import json


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


def claim_incentive():
    
    config = utils.load_config()
    
    # 获取合约地址和ABI
    contract_address = config.get('contracts', {}).get('Incentive Distribution', {}).get('address')
    contract_abi = config.get('contracts', {}).get('Incentive Distribution', {}).get('abi')
    filename = f"{config['save_file_prefix']['incentive_data']}.json"
    
    if not contract_address or not contract_abi:
        print("错误：未找到Incentive Distribution合约配置")
        return None
    
    # 获取操作者地址
    operator_address = config['nodeInfo']['operator_address']
    
    try:

        proof_data = fetch_proof()
        if proof_data is None:
            print("未找到奖励数据")
            return None
        # 提取rewards数据，格式化为claim结构
        claims = []
        for reward in proof_data:
            
            claim = (
                Web3.to_bytes(hexstr=reward.get('dist_id')),  # identifier (bytes32)
                Web3.to_checksum_address(reward.get('recipient')),  # account (address) - 确保使用校验和地址
                int(reward.get('amount')),                     # amount (uint256)
                [Web3.to_bytes(hexstr=proof) for proof in reward.get('merkle_proof', [])]  # merkleProof (bytes32[])
            )
            claims.append(claim)
        
        print(f"找到 {len(claims)} 个奖励数据可领取")
        
        # 创建合约实例
        contract = web3.eth.contract(address=contract_address, abi=contract_abi)
        
        # 构建交易参数
        tx_params = {
            'from': operator_address,
            'gas': 3000000,  # 设置较高的gas限制，因为包含大量数据
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(operator_address)
        }
        
        # 构建交易
        tx = contract.functions.claim(claims).build_transaction(tx_params)
        
        # 签名交易
        signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        
        # 发送交易
        # 处理不同版本的web3.py
        try:
            # 新版本web3.py
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        except AttributeError:
            # 旧版本web3.py
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
        print(f"交易已发送，交易哈希: {tx_hash.hex()}")
        print("等待交易确认中...")
        
        # 等待交易确认
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)  # 300秒超时
        
        if receipt['status'] == 1:
            print(f"交易确认成功！区块号: {receipt['blockNumber']}")
            print(f"Gas使用量: {receipt['gasUsed']}")
            print("奖励已成功领取")
            incentive_data = {receipt['blockNumber']: proof_data}
            # 保存incentive数据到文件
            utils.update_json_file(filename, incentive_data)
            return receipt
        else:
            print("交易执行失败，请检查合约状态")
            return None
            
    except Exception as e:
        print(f"发送交易时出错: {str(e)}")
        return None


def fetch_proof(account=None, validator=None):
    """
    从Berachain Hub API获取proof数据并保存到本地文件
    
    参数:
    account (str): 账户地址，默认为None，将使用配置文件中的操作者地址
    validator (str): 验证者地址，默认为None，将使用配置文件中的验证者地址
    
    返回:
    dict: 获取的proof数据
    """
    
    config = utils.load_config()
    
    # 如果未提供账户地址，使用配置文件中的操作者地址
    if not account:
        account = config['nodeInfo']['operator_address']
    # 确保账户地址是校验和格式
    account = Web3.to_checksum_address(account)
    
    # 如果未提供验证者地址，使用配置文件中的验证者地址
    if not validator:
        validator = config['nodeInfo'].get('pubkey1')
    
    # 构建API URL
    base_url = "https://hub.berachain.com/api/portfolio/proofs/"
    params = {"account": account}
    params["validator"] = validator
    
    try:
        print(f"正在获取账户 {account} 的proof数据...")
        # 发送GET请求
        response = requests.get(base_url, params=params)
        
        # 检查响应状态码
        if response.status_code == 200:
            proof_data = response.json()
            if proof_data.get('rewards') is not None:
                proof_data = proof_data.get('rewards')
                print(json.dumps(proof_data, indent=2))
                print(f"找到 {len(proof_data)} 个奖励数据")
                return proof_data
            else:
                print("未找到奖励数据")
                return None
        else:
            print(f"获取proof数据失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
    except Exception as e:
        print(f"获取proof数据时出错: {str(e)}")
        return None


if __name__ == "__main__":
    #claim_honey_rewards()
    #get_unclaimed_honey_rewards()

    #get_boosted_amount('0x')
    #fetch_proof()
    #claim_incentive_test()
    pass
