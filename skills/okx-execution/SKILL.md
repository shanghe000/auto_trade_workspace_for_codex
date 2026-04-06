---
name: okx-execution
description: >
  OKX 执行适配契约。
  底层可以是官方 MCP，也可以是将来的直连 API 实现，但对上层始终暴露同一套标准接口。
---

# OKX 执行适配

## 作用

这个 skill 定义了工作空间如何与 OKX 交互，同时避免策略层和某个具体传输方式强耦合。

底层适配可以采用：

- 直连 OKX API
- MCP 工具或 MCP Server

对工作空间其他部分来说，关键不是底层用哪种方式，而是标准化契约是否保持一致。

## 必备能力

选定的适配层至少应支持这些标准动作：

- 获取账户快照
- 获取持仓快照
- 获取当前挂单
- 获取合约元数据
- 下单
- 改单
- 撤单
- 获取执行结果或成交状态
- 订阅或同步订单 / 仓位 / 账户事件

## 适配层选择规则

- 如果官方 MCP 路径已经能满足需求，优先使用 MCP。
- 如果 MCP 路径不存在或能力不完整，再使用直连 API 包装层。
- 如果两者都没有准备好，执行层只能停留在 dry-run。

## 硬规则

- 不要把密钥直接写进源码。
- 不要把原始交易所回包当作唯一持久化记录，必须归一化到本地 journal 和 snapshot。
- 每笔订单都必须带稳定的 client order id，便于回放与对账。
- 执行层不能自己发明交易理由，它只能执行已批准的 intent。
- `order_event_watcher` 应视为确定性服务，而不是自由型 AI agent。

## 下单前的必要输入

- 标准化的 `TradeIntent`
- 风控允许结果
- 适配层健康状态
- 当前品种元数据

## 执行后的必要输出

- 标准化执行结果
- journal 记录
- 若可获得，则更新本地 snapshot
- 若可获得，则写入标准化 `OrderEvent`
- 一段给可观测层使用的简洁操作员消息

## Reference 路由

- 接口细节：`references/interface-contract.md`
- 风控前提：`../risk-governor/SKILL.md`
- 报告规范：`../trade-observability/SKILL.md`
