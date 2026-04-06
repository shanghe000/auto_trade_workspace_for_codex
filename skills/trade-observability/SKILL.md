---
name: trade-observability
description: >
  交易工作空间中的日志、报表、快照与飞书输出规范。
  让每一个交易动作都能被人类操作员回看和追责。
---

# 交易可观测性

## 作用

这个 skill 负责让系统保持“可理解”。

它负责：

- 决策 journal
- 执行 journal
- snapshot 存储约定
- 报表模板
- 通过 `cc-connect` 输出到飞书的规范

## 运行时目录

- `../../state/journals/`
- `../../state/reports/`
- `../../state/snapshots/`
- `../../state/events/`
- `../../state/artifacts/`

## 写入要求

以下任意事件发生时，都要写 journal：

- 新交易判断
- 风控阻断
- 提交订单
- 修改订单
- 撤销订单
- 成交或平仓
- 交易所或适配层报错

以下事件发生时，应写事件流：

- 新订单创建
- 订单状态变化
- 仓位数量变化
- 账户权益显著变化

## 报告要求

对于任何重要操作员更新：

- 正文要简洁
- 必须包含最新状态、原因和下一步
- 只有在确实增加信息量时才附加文件或图表

## 飞书使用规则

当本工作空间跑在 `cc-connect` 下时，优先：

- 用普通 Markdown 回复输出主结论
- 用 `cc-connect send --file` 或 `--image` 回传额外产物

## 建议报表类型

- 盘前市场观察
- 当前账户和风险状态
- 订单生命周期摘要
- 日终对账

## Reference 路由

- 报表结构：`references/feishu-report-template.md`
