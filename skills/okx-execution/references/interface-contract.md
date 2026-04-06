# 接口契约

## TradeIntent

策略层向执行层交付一个标准化 intent。

示例：

```json
{
  "symbol": "ETH-USDT-SWAP",
  "side": "sell",
  "intent_type": "open",
  "entry_condition": "retest failure at prior breakdown level",
  "size_basis": {
    "type": "risk_pct",
    "value": 0.5
  },
  "leverage": 2,
  "order_type": "limit",
  "time_in_force": "gtc",
  "max_slippage_bps": 8,
  "invalidation": "close back above invalidation level",
  "stop_logic": "hard stop above invalidation",
  "exit_logic": "cover at target or if thesis fails",
  "client_order_context": {
    "strategy_id": "manual-operator",
    "decision_id": "2026-04-05T160000Z-001"
  }
}
```

## ExecutionResult

执行层应返回：

```json
{
  "status": "accepted",
  "client_order_id": "manual-operator-20260405-001",
  "exchange_order_id": "1234567890",
  "symbol": "ETH-USDT-SWAP",
  "side": "sell",
  "order_type": "limit",
  "submitted_price": "1800.5",
  "submitted_size": "100",
  "message": "accepted by exchange"
}
```

## 对账规则

订单提交后，系统至少应对账以下内容：

- 计划下单数量与实际接受数量
- 计划价格与实际接受价格
- 当前挂单状态
- 任何交易所拒单或改单信息

如果对账失败，必须抛出对操作员可见的错误，并在理解差异来源前停止进一步自动化。
