from web3 import Web3
from websockets import connect
from websockets.exceptions import WebSocketException
import json
import os
import asyncio
import ssl
from dotenv import load_dotenv
import logging
from datetime import datetime
import signal
from requestDuneData import update_stake_snapshot
#from nodeOperation import claim_honey_rewards

# 创建日志目录
os.makedirs('logs', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/bera_events_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv(override=True)

class BeraWebSocketListener:
    def __init__(self):
        # Berachain WebSocket URL (使用环境变量)
        self.ws_url = os.getenv('BERA_WS_URL', 'wss://berachain-rpc.publicnode.com')
        self.w3 = None
        self.ws = None
        self.subscription_id = None
        self.running = True
        self.shutdown_event = asyncio.Event()
        self.event_filters = []  # 存储事件过滤条件
        self.contract = None  # 存储合约实例

    def setup_signal_handlers(self):
        """设置信号处理器"""
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """同步信号处理函数"""
        logger.info(f"接收到信号 {signum}，准备关闭...")
        self.running = False
        # 设置关闭事件
        if not self.shutdown_event.is_set():
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(self.shutdown_event.set)

    async def wait_for_shutdown(self):
        """等待关闭信号"""
        await self.shutdown_event.wait()
        await self.close_connection()

    async def close_connection(self):
        """关闭WebSocket连接"""
        try:
            if self.ws:
                await self.ws.close()
            if self.w3 and hasattr(self.w3.provider, 'disconnect'):
                await self.w3.provider.disconnect()
        except Exception as e:
            logger.error(f"关闭连接时出错: {str(e)}")
        
    async def connect(self):
        """建立WebSocket连接"""
        try:
            # 创建SSL上下文
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            self.w3 = Web3()
            # 如果URL以ws://开头，不要提供ssl参数
            if self.ws_url.startswith("ws://"):
                self.ws = await connect(self.ws_url)
            else:  # wss://
                self.ws = await connect(self.ws_url, ssl=ssl_context)
            
            while not self.ws.open and self.running:
                logger.warning("无法连接到Berachain网络，5秒后重试...")
                await asyncio.sleep(5)
                self.ws = await connect(
                    self.ws_url,
                    ssl=ssl_context
                )
            
            if self.running and self.ws.open:
                logger.info("成功连接到Berachain WebSocket")
                return True
            return False
            
        except Exception as e:
            logger.error(f"连接到WebSocket时出错: {str(e)}")
            return False

    async def subscribe_to_events(self, contract_address, contract_abi, event_name):
        """
        订阅合约事件
        
        Args:
            contract_address (str): 合约地址
            contract_abi (list): 合约ABI
            event_name (str): 要监听的事件名称
        """
        try:
            # 创建合约实例
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=contract_abi
            )
            
            # 创建事件过滤器
            event_filter = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": [
                    "logs",
                    {
                        "address": contract_address,
                        "topics": [self.contract.events[event_name].build_filter().topics[0]]
                    }
                ]
            }
            
            await self.ws.send(json.dumps(event_filter))
            response = await self.ws.recv()
            subscription_response = json.loads(response)
            self.subscription_id = subscription_response.get('result')
            
            logger.info(f"开始监听事件 {event_name}")
            
            # 持续监听事件
            while self.running:
                try:
                    message = await self.ws.recv()
                    event_data = json.loads(message)
                    if event_data.get('method') == 'eth_subscription':
                        await self.process_event(event_data['params']['result'])
                    
                except WebSocketException as e:
                    if not self.running:
                        break
                    logger.error(f"WebSocket连接错误: {str(e)}")
                    await self.reconnect()
                    continue
                    
                except Exception as e:
                    if not self.running:
                        break
                    logger.error(f"处理事件时出错: {str(e)}")
                    await asyncio.sleep(5)
                    continue
                    
        except Exception as e:
            logger.error(f"订阅事件时出错: {str(e)}")
            if self.running:
                await self.reconnect()

    def add_event_filter(self, event_signature=None, address=None, data_filters=None):
        """
        添加事件过滤条件
        
        Args:
            event_signature (str): 事件签名，例如 "Deposit(bytes,bytes,uint64,bytes,uint64)"
            address (str): 特定地址
            data_filters (list): data字段的过滤条件列表，每个条件是一个字典，包含：
                - param_name: 参数名称
                - condition: 比较条件 ('eq', 'gt', 'lt', 'gte', 'lte')
                - value: 比较值
        """
        self.event_filters.append({
            'event_signature': event_signature,
            'address': address and Web3.to_checksum_address(address),
            'data_filters': data_filters or []
        })

    def decode_event_data(self, event, event_name):
        """
        解码事件数据
        
        Args:
            event (dict): 原始事件数据
            event_name (str): 事件名称
        
        Returns:
            dict: 解码后的事件数据
        """
        try:
            if not self.contract:
                return None
            
            # 直接使用contract.events解码事件数据
            decoded_data = self.contract.events[event_name]().process_log({
                'topics': event.get('topics', []),
                'data': event.get('data', '0x'),
                'address': event.get('address'),
                'blockNumber': event.get('blockNumber'),
                'transactionHash': event.get('transactionHash'),
                'logIndex': event.get('logIndex', '0x0')
            })
            
            return decoded_data['args'] if decoded_data else None
            
        except Exception as e:
            logger.error(f"解码事件数据时出错: {str(e)}")
            return None

    def check_data_filter(self, decoded_data, filter_condition):
        """
        检查解码后的数据是否满足过滤条件
        
        Args:
            decoded_data (dict): 解码后的事件数据
            filter_condition (dict): 过滤条件
        
        Returns:
            bool: 是否满足过滤条件
        """


        if not decoded_data or not filter_condition.get('data_filters'):
            return True
            
        for data_filter in filter_condition['data_filters']:
            param_name = data_filter.get('param_name')
            condition = data_filter.get('condition', 'eq')
            filter_value = data_filter.get('value')
            
            if param_name not in decoded_data:
                continue
                
            param_value = decoded_data[param_name]
            
            # 对于bytes类型的特殊处理
            if isinstance(param_value, bytes) and isinstance(filter_value, str):
                # 将bytes转换为hex字符串进行比较
                param_value_hex = '0x' + param_value.hex()
                if condition == 'eq':
                    if param_value_hex.lower() != filter_value.lower():
                        return False
                continue
            
            # 对于其他类型的常规处理
            if condition == 'eq':
                if param_value != filter_value:
                    return False
            elif condition == 'gt':
                if not param_value > filter_value:
                    return False
            elif condition == 'lt':
                if not param_value < filter_value:
                    return False
            elif condition == 'gte':
                if not param_value >= filter_value:
                    return False
            elif condition == 'lte':
                if not param_value <= filter_value:
                    return False
                    
        return True

    def should_process_event(self, event):
        """
        检查事件是否满足过滤条件
        
        Args:
            event (dict): 事件数据
        
        Returns:
            bool: 是否应该处理该事件
        """
        if not self.event_filters:
            return True  # 如果没有设置过滤器，处理所有事件
            
        for filter_condition in self.event_filters:
            matches = True
            
            # 检查事件签名（通过topic0）
            if filter_condition['event_signature']:
                event_sig_hash = Web3.keccak(
                    text=filter_condition['event_signature']
                ).hex()
                if not event.get('topics') or event['topics'][0] != event_sig_hash:
                    matches = False
                    
            # 检查地址
            if filter_condition['address']:
                if Web3.to_checksum_address(event.get('address', '')) != filter_condition['address']:
                    matches = False
            
            # 检查data字段的过滤条件
            if matches and filter_condition.get('data_filters'):
                # 获取事件名称
                event_name = None
                if filter_condition['event_signature']:
                    event_name = filter_condition['event_signature'].split('(')[0]
                
                if event_name:
                    decoded_data = self.decode_event_data(event, event_name)
                    if not self.check_data_filter(decoded_data, filter_condition):
                        matches = False
                    
            if matches:
                return True
                
        return False

    async def process_event(self, event):
        """
        处理接收到的事件
        
        Args:
            event: 事件对象
        """
        try:
            # 首先检查是否需要处理该事件
            if not self.should_process_event(event):
                return

            # 解析事件数据
            event_data = {
                'address': event.get('address'),
                'block_number': int(event.get('blockNumber', '0x0'), 16),
                'transaction_hash': event.get('transactionHash'),
                'topics': event.get('topics', []),
                'data': event.get('data'),
                'timestamp': datetime.now().isoformat()
            }
            
            # 保存事件数据到文件
            await self.save_event_to_file(event_data)
            
            # 日志输出
            logger.info(f"接收到新事件: {json.dumps(event_data, indent=2)}")
            
            # 异步调用init_stake_snapshot
            try:
                await asyncio.to_thread(update_stake_snapshot, txId=event.get('transactionHash'))
                logger.info("成功更新质押快照")
            except Exception as e:
                logger.error(f"更新质押快照时出错: {str(e)}")
            
            # # 异步调用claim_honey_rewards
            # try:
            #     await asyncio.to_thread(claim_honey_rewards)
            #     logger.info("成功领取HONEY奖励")
            # except Exception as e:
            #     logger.error(f"领取HONEY奖励时出错: {str(e)}")
            
        except Exception as e:
            logger.error(f"处理事件时出错: {str(e)}")

    async def save_event_to_file(self, event_data):
        """
        将事件数据保存到文件
        
        Args:
            event_data (dict): 事件数据
        """
        try:
            # 确保目录存在
            os.makedirs('data/events', exist_ok=True)
            
            # 使用日期作为文件名
            filename = f'data/events/events_{datetime.now().strftime("%Y%m%d")}.json'
            
            # 读取现有数据
            events = []
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    events = json.load(f)
            
            # 添加新事件
            events.append(event_data)
            
            # 保存到文件
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"保存事件数据时出错: {str(e)}")

    async def reconnect(self):
        """重新连接WebSocket"""
        logger.info("尝试重新连接...")
        await self.close_connection()
        if await self.connect():
            logger.info("重新连接成功")
        else:
            logger.error("重新连接失败")

    async def start(self, contract_address, contract_abi, event_name):
        """
        启动监听器
        
        Args:
            contract_address (str): 合约地址
            contract_abi (list): 合约ABI
            event_name (str): 要监听的事件名称
        """
        # 确保日志和数据目录存在
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data/events', exist_ok=True)
        
        if await self.connect():
            await self.subscribe_to_events(contract_address, contract_abi, event_name)
        else:
            logger.error("无法启动监听器：连接失败")

async def main():
    config_dir = 'config'
    config_file = os.path.join(config_dir, 'config.json')
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error(f"配置文件不存在: {config_file}")
        return
    except json.JSONDecodeError:
        logger.error(f"配置文件格式错误: {config_file}")
        return
    
    beconDeposit_address = config.get('contracts', {}).get('Beacon Deposit', {}).get('address')
    beconDeposit_abi = config.get('contracts', {}).get('Beacon Deposit', {}).get('abi')
    pubkey1 = config.get('nodeInfo', {}).get('pubkey1')


    listener = None
    try:
        # 创建监听器实例
        listener = BeraWebSocketListener()
        listener.setup_signal_handlers()
        
        # 添加事件过滤器
        
        listener.add_event_filter(
            event_signature="Deposit(bytes,bytes,uint64,bytes,uint64)",
            address=beconDeposit_address,
            data_filters=[
                {
                    'param_name': 'pubkey',
                    'condition': 'eq',
                    'value': pubkey1
                }
            ]
        )
        
            
        event_name = "Deposit"
        
        # 创建监听任务和关闭等待任务
        listen_task = asyncio.create_task(listener.start(beconDeposit_address, beconDeposit_abi, event_name))
        shutdown_task = asyncio.create_task(listener.wait_for_shutdown())
        
        # 等待任意一个任务完成
        done, pending = await asyncio.wait(
            [listen_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # 取消未完成的任务
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
    except Exception as e:
        logger.error(f"主程序出错: {str(e)}")
    finally:
        if listener:
            await listener.close_connection()
        logger.info("程序已终止")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # 主程序已经处理了信号，这里不需要额外处理 