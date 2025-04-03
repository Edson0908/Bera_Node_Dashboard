from web3 import Web3
import utils
import requests
import json
import time

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
    contract_address = Web3.to_checksum_address(contract_address)
    contract_abi = config.get('contracts', {}).get('BGT Staker', {}).get('abi')
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    balance = contract.functions.earned(address).call() / (10 ** 18)
    print(f"未领取的honey奖励: {balance}")
    return balance

def claim_honey_rewards():
    config = utils.load_config()
    
    contract_address = config.get('contracts', {}).get('BGT Staker', {}).get('address')
    contract_address = Web3.to_checksum_address(contract_address)
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
    node_address = Web3.to_checksum_address(node_address)
    config = utils.load_config()
    contract_address = config.get('contracts', {}).get('BGT Token', {}).get('address')
    contract_abi = config.get('contracts', {}).get('BGT Token', {}).get('abi')
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    amount = contract.functions.boosts(node_address).call() / (10 ** 18)
    print(f"节点{node_address}的boosted amount: {amount}")

    return amount


def get_honey_balance(address):
    address = Web3.to_checksum_address(address)
    config = utils.load_config()
    contract_address = config.get('contracts', {}).get('HONEY Token', {}).get('address')
    contract_address = Web3.to_checksum_address(contract_address)
    contract_abi = config.get('contracts', {}).get('HONEY Token', {}).get('abi')
    contract = web3.eth.contract(address=contract_address, abi=contract_abi)
    balance = contract.functions.balanceOf(address).call() / (10 ** 18)
    
    return balance

def get_raw_balance(address, token_address):
    address = Web3.to_checksum_address(address)
    token_address = Web3.to_checksum_address(token_address)
    config = utils.load_config()
    contract_abi = config.get('contracts', {}).get('HONEY Token', {}).get('abi')
    contract = web3.eth.contract(address=token_address, abi=contract_abi)
    balance = contract.functions.balanceOf(address).call()
    return balance

def claim_incentive(operator_address = None, pubkey = None, private_key = PRIVATE_KEY):
    
    config = utils.load_config()
    
    # 获取合约地址和ABI
    contract_address = config.get('contracts', {}).get('Incentive Distribution', {}).get('address')
    contract_address = Web3.to_checksum_address(contract_address)
    contract_abi = config.get('contracts', {}).get('Incentive Distribution', {}).get('abi')
    filename = config['save_file_prefix']['incentive_data']
    
    if not contract_address or not contract_abi:
        print("错误：未找到Incentive Distribution合约配置")
        return None
    
    # 获取操作者地址
    if operator_address is None:
        operator_address = config['nodeInfo']['operator_address']
    operator_address = Web3.to_checksum_address(operator_address)
    if pubkey is None:
        pubkey = config['nodeInfo'].get('pubkey1')
    try:

        proof_data = fetch_proof(operator_address, pubkey)
        if proof_data is None:
            print("未找到奖励数据")
            return None
        # 创建合约实例
        contract = web3.eth.contract(address=contract_address, abi=contract_abi)
        
        # 构建交易参数
        tx_params = {
            'from': operator_address,
            'gas': 3000000,  # 设置较高的gas限制，因为包含大量数据
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(operator_address)
        }

        # 提取rewards数据，格式化为claim结构
        receipts = []
        claims = []
        init_batch = proof_data[0].get('available_at')

        send_tx = False
        index = 0
        reward_data = []
        for reward in proof_data:
            
            index += 1

            claim = (
                Web3.to_bytes(hexstr=reward.get('dist_id')),  # identifier (bytes32)
                Web3.to_checksum_address(reward.get('recipient')),  # account (address) - 确保使用校验和地址
                int(reward.get('amount')),                     # amount (uint256)
                [Web3.to_bytes(hexstr=proof) for proof in reward.get('merkle_proof', [])]  # merkleProof (bytes32[])
            )

            current_batch = reward.get('available_at')

            if current_batch != init_batch:
                init_batch = current_batch
                send_tx = True
            if index == len(proof_data):
                send_tx = True
                claims.append(claim)
                reward_data.append(reward)
          
            if send_tx:
                # 构建交易
                tx = contract.functions.claim(claims).build_transaction(tx_params)
                # 签名交易
                signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        
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
                    for item in reward_data:
                        incentive_data = {receipt['blockNumber']: item}
                        utils.save_results_to_json(incentive_data, filename, 'incentive')
                        time.sleep(1)
                else:
                    print("交易执行失败，请检查合约状态")   
                receipts.append(receipt)

                # 重置数组和状态
                claims = []
                reward_data = []
                send_tx = False
 
            claims.append(claim)
            reward_data.append(reward)
            
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

def transfer_erc20_token(token_address, to_address, amount):


    config = utils.load_config()
    
    # 确保地址是校验和格式
    token_address = Web3.to_checksum_address(token_address)
    to_address = Web3.to_checksum_address(to_address)
    
    # 获取ABI
    contract_abi = config.get('contracts', {}).get('HONEY Token', {}).get('abi')
    
    if not contract_abi:
        print("错误：未找到ERC20代币合约ABI")
        return None
    
    # 获取操作者地址
    operator_address = config['nodeInfo']['operator_address']
    operator_address = Web3.to_checksum_address(operator_address)
    
    try:
        # 创建合约实例
        contract = web3.eth.contract(address=token_address, abi=contract_abi)
        
        # 构建交易参数
        tx_params = {
            'from': operator_address,
            'gas': 100000,  # 设置gas限制
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(operator_address)
        }

        balance = get_raw_balance(operator_address, token_address)
        if balance < amount:
            print(f"余额不足，当前余额: {balance}")
            amount = balance
        
        # 构建交易
        tx = contract.functions.transfer(to_address, amount).build_transaction(tx_params)
        
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
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)  # 120秒超时
        
        if receipt['status'] == 1:
            print(f"交易确认成功！区块号: {receipt['blockNumber']}")
            print(f"Gas使用量: {receipt['gasUsed']}")
            print("代币转账成功")
            return tx_hash.hex()
        else:
            print("交易执行失败，请检查合约状态")
            return None
            
    except Exception as e:
        print(f"发送交易时出错: {str(e)}")
        return None


if __name__ == "__main__":
    #claim_honey_rewards()
    #get_unclaimed_honey_rewards()

    #get_boosted_amount('0x')
    #claim_incentive_test()
    # 测试加载钱包
    pass
