# Bera Node Dashboard

这是一个用于Berachain验证节点管理和监控的工具，帮助节点运营者跟踪节点状态、质押情况和奖励分配。

## 项目功能

- 监控验证节点的质押情况和收益
- 自动处理链上事件（如Deposit事件）
- 管理质押者的佣金率和奖励分配
- 提供节点运营数据可视化界面

## 系统架构

- `requestDuneData.py`: 从Dune Analytics获取链上数据并分析
- `listenEvent.py`: 监听Berachain上的事件并触发相应操作
- `nodeOperation.py`: 提供节点操作相关功能（如查询区块、领取奖励）
- `nodeDashboard.py`: Web界面，显示节点数据和统计信息

## 环境配置

1. 检查 .env 文件

- 复制 `.env.example` 为 `.env` 并填写相关配置
- `DUNE_API_KEY`: Dune Analytics API密钥
- `BERA_RPC_URL`: Berachain RPC URL
- `BERA_WS_URL`: Berachain WebSocket URL
- `DEBUG_MODE`: 设为 False (DEBUG_MODE 为 True 时只获取 Query 的最后一次运行结果)

2. 检查 config.json

- `commission_rate`: 根据 Stake 的数量设置 Commission 比率
- `nodeInfo`: 设置节点信息（地址和公钥）
- `staker_info`:
  - `name`: staker 的名称
  - `commision`: 为 false 时，commission rate 为 0
  - `reward_address`: 发放奖励的地址

## 运行流程

### 初始化

首次启动前需要执行以下操作：
```
python src/requestDuneData.py init
```
这将初始化质押快照和验证者概览数据。

### 数据更新

- `validator_overview()`和`update_stake_snapshot()`需定期运行（建议每天）
- 可使用cron作业实现自动化

### 事件监听

通过后台运行listenEvent.py持续监听链上事件：
```
python src/listenEvent.py &
```

- Deposit事件触发时会执行：
  - `init_stake_snapshot()`: 重新计算staker的权重
  - `claim_honey_rewards()`: 领取已获得的HONEY奖励（下一阶段HONEY奖励按照新的BGT Boost分布计算）

### Web界面

启动Web界面查看节点数据：
```
python src/nodeDashboard.py
```

## 相关链接

- [Berachain官网](https://www.berachain.com/)
- [Dune Analytics](https://dune.com/)
