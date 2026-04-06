# 策略治理

## 为什么要单独治理策略

在这个工作空间里，策略不是聊天时随口说出的一个想法，而是要进入系统生命周期管理的对象。

如果不把策略治理单独定义清楚，会出现三个问题：

- AI 提出的想法和真正允许执行的策略混在一起
- 风控层不知道该审查哪一版规则
- 复盘无法回溯“当时到底按哪条策略在运行”

## 策略对象的最小定义

一条策略至少应包含：

- `id`
- `name`
- `timeframe`
- `instruments`
- `status`
- `execution_mode`
- `thesis`
- `trigger`
- `invalidation`
- `sizing`
- `leverage_cap`
- `stop_loss`
- `exit_logic`
- `produced_by`
- `reviewed_by`
- `approved_by`

## 策略状态

建议使用这五个状态：

- `draft`
  - 草案
  - 只能讨论，不能执行
- `review`
  - 审核中
  - 可以进入结构和风险审查
- `armed`
  - 已激活
  - 运行时可以被主 agent 读取
- `paused`
  - 暂停
  - 保留记录，但当前不能触发
- `retired`
  - 退役
  - 只用于回放和复盘

## 策略由谁产出

允许三类来源产出策略草案：

- 你自己
- `strategy_research_agent`
- `post_trade_review_agent`

这里的关键约束是：

- AI 只能产出 `draft`
- AI 不能直接产出 `armed`

## 策略由谁审核

审核建议至少分三层：

### 1. 结构审核

检查：

- 字段是否完整
- 方向与触发条件是否清晰
- 仓位、杠杆、止损、退出逻辑是否存在
- 时间级别与品种范围是否明确

这一步可以由主 agent 或专门的 `strategy_review_agent` 完成。

### 2. 风险审核

检查：

- 是否与 `risk-limits.yaml` 冲突
- 是否超出允许的杠杆或风险预算
- 是否要求系统当前没有的能力
- 是否属于当前工作空间不适合的时间级别

这一步应由 `risk_engine` 做确定性检查，必要时由 `risk_review_agent` 补解释。

### 3. 人工复核

最终需要人工确认：

- 这条策略是否值得进入可运行状态
- 它适合 `manual_confirm` 还是 `guarded_auto`
- 它是否应该纳入当前交易日的候选集

## 谁决定策略生效

只有**人工操作员**可以把策略从：

- `draft` -> `review`
- `review` -> `armed`
- `armed` -> `paused`
- `armed` -> `retired`

也就是说：

- AI 可以提出
- AI 可以评论
- AI 可以复盘
- AI 不能自行激活

## 策略如何在运行时被使用

运行时流程应是：

1. 主 agent 读取 `config/strategy-registry.yaml`
2. 只筛选：
   - `status = armed`
   - 当前品种匹配
   - 当前时间级别匹配
   - 当前运行模式允许
3. 把候选策略交给分析 agent 判断是否满足触发条件
4. 主 agent 形成候选 `TradeIntent`
5. `risk_engine` 再次做硬审查
6. 通过后才允许进入执行准备

因此策略的定位是：

- 它是“生成交易意图的模板和边界”
- 它不是直接下单的命令

## 执行模式

建议支持三种执行模式：

- `advisory`
  - 只生成计划，不可执行
- `manual_confirm`
  - 通过风控后，仍要求人工确认
- `guarded_auto`
  - 在明确预算和时间窗内，允许系统低频自动执行

默认建议：

- 新策略先从 `advisory` 开始
- 验证稳定后再切到 `manual_confirm`
- 长期稳定后才考虑 `guarded_auto`

## 策略修改如何进入系统

任何策略修改都应视为新版本，而不是静默覆盖。

建议做法：

- 保留原策略 `id`
- 增加 `version`
- 记录：
  - 谁提议修改
  - 为什么修改
  - 哪些字段变了
  - 是否重新审核

AI 可以提出参数调整建议，但不能自动替换线上版本。

## 复盘如何反馈到策略

复盘 agent 的作用是：

- 产出策略改进建议
- 更新软风险状态
- 提醒某类信号近期表现下降

它不能直接：

- 修改 `max_leverage`
- 修改 `max_daily_drawdown`
- 开启 live
- 把策略自动切到 `armed`

硬风控和策略激活必须保持人工控制。

## 最小落地建议

第一版可以先不做复杂的策略服务，先用：

- `config/strategy-registry.yaml`

作为主配置入口。

只要把以下四件事做严谨，系统就已经比“聊天式策略”强很多：

- 策略有状态
- 策略有 owner
- 策略有审核记录
- 策略有运行模式
