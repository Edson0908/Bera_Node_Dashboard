1. 检查 .env

- 检查环境变量
- DEBUG_MODE 设为 False (DEBUG_MODE 为 True 时只获取 Query 的最后一次运行结果)

2. 检查 config.json

- commission_rate : 根据 Stake 的数量设置 Commission
- nodeInfo：设置为节点信息
- staker_info:
  name：staker 的名称
  commision：为 false 时，commission rate 为 0
  reward_address：发放奖励的地址

3. requestDuneData

- 首次启动前先执行 init_stake_snapshot()和 validator_overview()，初始化数据
- validator_overview()和 update_stake_snapshot()定期运行（1 天）

4. listenEvent 后台运行

- Deposit 事件触发 init_stake_snapshot()和 claim_honey_rewards()
  init_stake_snapshot()：重新计算 staker 的权重
  claim_honey_rewards()：claim 已经获得 HONEY（下一阶段 HONEY 奖励按照新的 BGT Boost 分布计算）
