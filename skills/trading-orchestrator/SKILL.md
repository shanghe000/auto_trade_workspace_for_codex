---
name: trading-orchestrator
description: >
  本仓库的交易决策主流程。
  把市场状态与账户状态转换成 HOLD、TradeIntent 或 RiskBlocked。
---

# 交易决策编排

## 作用

这个 skill 是主流程层，也是主 agent 的控制面。

它负责：

- 固定本轮 `run_id` 与 `snapshot_id`
- 市场观察顺序
- 账户状态检查顺序
- 当前激活策略的选择顺序
- 子 agent 结果的汇总方式
- 交易判断的组织方式
- 向风险层交接
- 向执行层或 dry-run 报告层交接

它不负责：

- 硬风控 veto 规则
- 交易所 API 细节
- 飞书输出细节

## 形成交易建议前的必备输入

- 最新账户快照
- 最新持仓快照
- 最新挂单快照
- 最新市场快照
- 当前已 `armed` 的策略集合
- 当前运行模式
- 来自 `risk-governor` 的当前风险状态

只要其中任意一项缺失或过期，默认结论就是 `HOLD`。

## 默认决策流程

1. 固定本轮使用的标准化快照。
2. 读取当前已 `armed` 且匹配上下文的策略。
3. 把分析任务分发给相应子 agent。
4. 明确区分“已知事实”和“推断判断”。
5. 只有当市场结构、账户状态和策略约束一致时，才形成一个清晰主判断。
6. 构造一个候选 `TradeIntent`。
7. 把这个 intent 交给 `risk-governor`。
8. 若被阻断，输出 `RiskBlocked`。
9. 若允许但 live 未开启，输出 dry-run 计划。
10. 若允许且 live 已开启，交给 `okx-execution`。

## 输出契约

输出只能是这三类之一：

- `HOLD`
- `RiskBlocked`
- `TradeIntent`

每个 `TradeIntent` 至少要包含：

- symbol
- strategy_id
- side
- intent type：open / add / reduce / close / cancel
- 触发条件
- 仓位依据
- 杠杆
- 失效条件
- 止损逻辑
- 退出逻辑
- 置信度和关键理由
- 生成该意图时所用的 `snapshot_id`

## 硬规则

- 除非用户明确要求比较方案，否则一次只给一个主交易想法。
- 不要隐藏不确定性。
- 绝不能跳过风险审查。
- 不要让多个分析 agent 各自读取不同时间面的市场数据再直接拼接结论。
- 不要把执行细节反向伪装成市场事实。

## Reference 路由

- 流程细节：`references/decision-flow.md`
- 风控规则：`../risk-governor/SKILL.md`
- 交易所契约：`../okx-execution/SKILL.md`
- 报告规范：`../trade-observability/SKILL.md`
