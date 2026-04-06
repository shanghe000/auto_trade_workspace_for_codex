---
name: risk-governor
description: >
  OKX BTC/ETH 永续交易的硬风控层。
  负责 live 开关、kill switch、白名单、仓位上限和数据新鲜度闸门。
---

# 风控总闸

## 作用

这个 skill 是 veto 层。

它决定某个交易提议或订单动作属于：

- 允许执行
- 只允许 dry-run
- 直接阻断

## 规则来源

如果存在，使用：

- `../../config/risk-limits.yaml`
- `../../config/strategy-registry.yaml`

如果真实文件不存在，则只把：

- `../../config/risk-limits.example.yaml`
- `../../config/strategy-registry.example.yaml`

当成结构参考，并强制进入 dry-run 模式。

## 必过闸门

进入真实执行前，下面所有条件都必须通过：

- 策略已被人工激活为 `armed`
- 当前运行模式允许执行该策略
- live trading 已启用
- kill switch 关闭
- 品种在白名单内
- 杠杆未超上限
- 总风险暴露未超过账户限制
- 提议仓位未超过单品种限制
- 市场和账户快照足够新鲜
- 不存在未解决的订单对账异常
- 若策略要求止损，则止损逻辑必须存在

## 默认阻断条件

遇到以下任意情况，直接阻断：

- 风控文件缺失
- 策略未激活或当前模式不允许执行
- live trading 未启用
- 品种不在白名单
- 数据过期
- 交易所状态无法对账
- 新交易会让日内回撤或风险暴露超限

## 返回要求

阻断时，必须返回：

- status
- 明确原因
- 失败的是哪一条闸门
- 是否仍允许 dry-run

## 操作哲学

- 先保资金
- 先降复杂度，再提自动化
- 系统不确定时，宁可不交易
- AI 可以提议策略，但不能自行放行策略

## Reference 路由

- 闸门细节：`references/live-gates.md`
- 具体策略值：`../../config/risk-limits.yaml`
