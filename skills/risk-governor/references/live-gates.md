# Live 闸门

## 闸门顺序

按下面顺序执行闸门：

1. 风控文件存在
2. live 开关开启
3. kill switch 关闭
4. 品种白名单通过
5. 市场和账户数据新鲜度通过
6. 挂单对账通过
7. 杠杆通过
8. 仓位大小通过
9. 总风险暴露通过
10. 止损要求通过

## 为什么按这个顺序

前面的闸门便宜且绝对。

如果下面这些条件都没过，就没必要继续算完美仓位：

- live trading 没开
- 品种不允许
- 交易所状态过期

## 阻断输出模板

```text
RiskBlocked
gate: <gate-name>
reason: <human-readable reason>
dry_run_allowed: <true|false>
next_action: <what must change>
```

## Dry-run 规则

如果某个策略值缺失，或者 live 开关关闭，在以下条件成立时系统仍可产出 dry-run 计划：

- 用户明确要分析
- 回复清楚标记为模拟或演练

绝不能把 dry-run 伪装成真实订单。
