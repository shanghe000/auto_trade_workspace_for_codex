# 决策流程

## 标准回复结构

任何正式交易回复都按这个顺序组织：

1. 已知事实
2. 交易判断
3. 风险状态
4. 执行计划
5. 后续观察点

## 结果规则

### HOLD

以下情况使用 `HOLD`：

- 数据过期或缺失
- 市场结构不清晰
- 风控策略阻断了当前想法
- 用户当前只要求监控，不要求出手

### RiskBlocked

当存在明确交易想法，但被策略层否决时，使用 `RiskBlocked`。

回复里必须包含：

- 阻断原因
- 失败的是哪条策略字段或闸门
- 需要什么变化才能重新考虑该想法

### TradeIntent

只有当交易想法已经具体到足以进入执行层时，才使用 `TradeIntent`。

## 最小意图字段

```json
{
  "symbol": "BTC-USDT-SWAP",
  "side": "buy",
  "intent_type": "open",
  "entry_condition": "breakout above local range high",
  "size_basis": {
    "type": "risk_pct",
    "value": 0.5
  },
  "leverage": 2,
  "invalidation": "lose acceptance back inside prior range",
  "stop_logic": "hard stop below invalidation",
  "exit_logic": "scale out at target or close on thesis failure",
  "confidence": "medium"
}
```

## 分层隔离规则

下面几类信息必须严格分开：

- 交易所事实
- 市场解释
- 风控策略
- 执行结果

不要把执行结果伪装成原始市场判断的一部分。
