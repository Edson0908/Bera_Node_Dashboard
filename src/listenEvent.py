from web3 import Web3
import json
import os
from dotenv import load_dotenv
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class BeraEventListener:
    def __init__(self):
        # Berachain RPC URL (使用环境变量)
        self.rpc_url = os.getenv('BERA_RPC_URL', 'https://rpc.berachain.com')
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # 检查连接
        if not self.w3.is_connected():
            raise Exception("无法连接到Berachain网络")
        
        logger.info(f"成功连接到Berachain网络")
        
    def get_latest_block(self):
        """获取最新区块号"""
        try:
            return self.w3.eth.block_number
        except Exception as e:
            logger.error(f"获取最新区块失败: {str(e)}")
            return None

    def listen_to_events(self, contract_address, contract_abi, event_name):
        """
        监听特定合约的特定事件
        
        Args:
            contract_address (str): 合约地址
            contract_abi (list): 合约ABI
            event_name (str): 要监听的事件名称
        """
        try:
            # 创建合约实例
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=contract_abi
            )
            
            # 获取最新区块
            latest_block = self.get_latest_block()
            if latest_block is None:
                return
            
            logger.info(f"开始监听事件 {event_name} 从区块 {latest_block}")
            
            # 创建事件过滤器
            event_filter = contract.events[event_name].create_filter(
                fromBlock=latest_block
            )
            
            # 持续监听新事件
            while True:
                try:
                    for event in event_filter.get_new_entries():
                        logger.info(f"检测到新事件: {event}")
                        # 在这里处理事件数据
                        self.process_event(event)
                    
                    time.sleep(2)  # 每2秒轮询一次
                    
                except Exception as e:
                    logger.error(f"处理事件时出错: {str(e)}")
                    time.sleep(5)  # 出错时等待更长时间
                    continue
                    
        except Exception as e:
            logger.error(f"设置事件监听器时出错: {str(e)}")
    
    def process_event(self, event):
        """
        处理接收到的事件
        
        Args:
            event: 事件对象
        """
        # 这里添加具体的事件处理逻辑
        event_data = {
            'event_type': event['event'],
            'transaction_hash': event['transactionHash'].hex(),
            'block_number': event['blockNumber'],
            'args': dict(event['args'])
        }
        
        # 将事件数据保存到文件或数据库
        logger.info(f"事件数据: {json.dumps(event_data, indent=2)}")

def main():
    try:
        listener = BeraEventListener()
        
        # 这里添加你要监听的合约地址和ABI
        contract_address = "YOUR_CONTRACT_ADDRESS"
        contract_abi = []  # 从文件加载或直接粘贴ABI
        event_name = "YOUR_EVENT_NAME"
        
        listener.listen_to_events(contract_address, contract_abi, event_name)
        
    except Exception as e:
        logger.error(f"主程序出错: {str(e)}")

if __name__ == "__main__":
    main() 