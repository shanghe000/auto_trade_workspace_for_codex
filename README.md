# auto_trade_workspace_for_codex

这是一个独立的交易工作空间仓库，用来承载：

- Codex 在该仓库下扮演 BTC / ETH 永续交易主控操作员
- 通过 OKX 的 API / CLI / MCP 与账户交互
- 通过 `cc-connect + 飞书` 提供日常入口、运行回传与可观测性
- 把市场分析、策略治理、风险控制、执行与复盘拆成清晰层次

这个仓库的目标不是做一个“会说交易黑话的聊天机器人”，而是做一个**有控制面、有数据面、有事件回路的交易工作空间**。

## 当前状态

- 已接通 OKX 公共行情链路，可生成标准化快照和中文摘要
- 已接通 OKX demo 账户只读链路，可读取余额、持仓、挂单、账户配置
- 已提供一键 demo 烟雾测试，可同时验证行情链路和账户链路
- 已补策略治理文档与样例配置，但正式执行链路仍未启用
- 当前仍不允许 live 下单

## 适合什么级别的交易

这个工作空间当前更适合两类场景：

- `15m-4H` 级别的日内 / 波段辅助交易
- “先生成计划，再执行”的半自动交易

它当前**不适合**：

- 秒级或亚分钟级超短线
- 把 AI 放在热路径里的高频决策
- 完全无人值守的新仓自动开启

原因很简单：

- 市场分析、汇总、风控、执行确认本身就有链路开销
- 多 agent 并行更适合提升认知质量，不适合抢亚秒级时延
- 真正需要低延迟、可重试、可幂等的动作，应交给确定性工具和服务

## 你在系统里扮演什么角色

### 模式 1：Human-in-the-loop

适用于 `15m-4H` 的日内 / 波段辅助交易。

此时你是：

- 主交易员
- 最终决策人
- 风险预算持有人

系统负责：

- 采集市场和账户数据
- 并行分析
- 生成交易计划
- 做风险预检
- 准备执行动作

你需要进入操作的点：

- 是否允许今天交易
- 是否批准某笔开仓 / 加仓 / 平仓
- 是否继续持仓
- 是否触发 kill switch 或人工接管

### 模式 2：Human-on-the-loop

适用于“先生成计划，再执行”的半自动交易。

此时你是：

- 策略 owner
- 风险 owner
- 异常处理人

系统负责：

- 在你预先批准的策略和预算范围内运行
- 自动刷新数据、生成意图、风控复核、执行、跟踪订单
- 成交后继续回流到主 agent 做复盘和汇报

你需要进入操作的点：

- 启用或暂停某个策略
- 调整策略额度、杠杆、白名单和时间窗
- 处理数据异常、滑点异常、成交异常
- 决定是否继续让系统保持自动运行

一句话说清楚：

- `Human-in-the-loop`：你批准每笔关键动作
- `Human-on-the-loop`：你批准系统边界，系统在边界内执行

## 整体位置

```text
用户
  -> 飞书机器人
  -> cc-connect project
  -> work_dir = 本仓库根目录
  -> 主 agent（control plane）
  -> 确定性工具 / 服务（data plane / execution plane）
  -> 分析 agent / 复盘 agent（analysis plane）
  -> state/ 中的快照、事件、journal、报告
  -> 结果回传飞书
```

这个仓库的核心原则是：

- 对外单入口
- 对内分层
- AI 负责分析与解释
- 工具负责采集、风控、执行、事件跟踪

## 架构设计

### 1. 主 agent：控制面

仓库根目录下运行的默认角色是**主 agent**。

它不是“最懂行情的那个 agent”，而是总控台。它负责：

- 创建 `run_id`
- 固定本轮使用的 `snapshot_id`
- 拉起分析 agent
- 汇总分析结果
- 把结论交给风险层
- 在执行后继续接收事件回流
- 生成最终 journal 和飞书摘要

主 agent 的职责是**推进流程**，不是直接代替所有子模块工作。

### 2. 确定性工具与服务：数据面

这一层处理重复、固定、需要幂等和低延迟的动作。

建议包括：

- `market_collector`
- `account_collector`
- `execution_gateway`
- `order_event_watcher`
- `reconciliation_checker`

这些能力应该尽量工具化或服务化，而不是交给自由型 AI agent。

### 3. 分析 agent：认知面

这一层处理真正需要推理和解释的部分。

建议包括：

- `market_structure_agent`
- `derivatives_flow_agent`
- `strategy_research_agent`
- `post_trade_review_agent`

它们不应各自直接打交易所，而应读取同一份标准化快照。

### 4. 风控层：硬规则 + 解释层

风控建议拆成两部分：

- `risk_engine`
  - 确定性硬闸门
  - 决定允许、只 dry-run、还是阻断
- `risk_review_agent`
  - 解释阻断原因
  - 给出降仓、降杠杆或延后执行建议

真正拥有 veto 权的是 `risk_engine`，不是解释型 agent。

### 5. 策略层：注册、审核、激活、运行

策略不应散落在聊天记录里，而应进入策略注册表。

建议至少区分：

- `draft`
- `review`
- `armed`
- `paused`
- `retired`

并区分三种运行方式：

- `advisory`
- `manual_confirm`
- `guarded_auto`

策略的生命周期不是“AI 想到一个点子就直接开跑”，而是：

```text
产出草案
  -> 审核
  -> 人工决定是否激活
  -> 主 agent 在运行时选择是否使用
  -> 风控层复核
  -> 执行
  -> 复盘反馈
```

### 6. 可观测层：事件、快照、journal、报告

对应目录：

- `state/snapshots/`
- `state/events/`
- `state/journals/`
- `state/reports/`
- `state/artifacts/`

这里要求每轮运行都可回放，每个重要事件都可解释。

## 当前工作流

### 工作流 1：公共行情观察

入口脚本：

- `tools/okx_market_snapshot.py`
- `tools/okx_market_brief.py`
- `tools/okx_market_watch.py`

控制流：

```text
OKX 公共接口
  -> 拉取 BTC/ETH 永续的 ticker / book / candles / mark price / OI / funding / trades
  -> 标准化写入 state/snapshots/okx_market_snapshot.latest.json
  -> 生成人类可读的 state/reports/okx_market_brief.latest.md
  -> 如有需要，通过 cc-connect send 回传飞书
```

### 工作流 2：demo 账户只读观察

入口脚本：

- `tools/okx_account_snapshot.py`
- `tools/okx_account_brief.py`
- `tools/okx_account_watch.py`

控制流：

```text
本地 demo 凭证
  -> OKX 官方 CLI
  -> 读取 balance / asset-balance / positions / config / open orders
  -> 标准化写入 state/snapshots/okx_account_snapshot.latest.json
  -> 生成人类可读的 state/reports/okx_account_brief.latest.md
  -> 如有需要，通过 cc-connect send 回传飞书
```

### 工作流 3：demo 串联烟雾测试

入口脚本：

- `tools/okx_demo_smoketest.py`

控制流：

```text
先跑公共行情链路
  -> 再跑 demo 账户只读链路
  -> 汇总两条链路状态
  -> 输出 state/reports/okx_demo_smoketest.latest.md
```

### 工作流 4：目标态的多 agent 交易控制流

这条链路是目标态，不是当前已开放能力：

```text
主 agent 创建 run_id
  -> collector 刷新市场 / 账户 / 持仓 / 挂单快照
  -> 固定 snapshot_id
  -> 并行拉起 market_structure_agent / derivatives_flow_agent
  -> 主 agent 汇总成候选 TradeIntent
  -> risk_engine 做确定性审查
  -> 若阻断，写 journal 并回飞书
  -> 若允许，执行前再做一次快照再校验
  -> execution_gateway 执行
  -> order_event_watcher 感知订单和仓位事件
  -> 事件触发主 agent 继续运行
  -> post_trade_review_agent 形成复盘
  -> 输出报告并回飞书
```

这里最重要的一条规则是：

- 分析基于冻结快照
- 执行前必须二次校验
- 信号过期就作废，不强行成交

## 策略由谁产出、谁审核、谁决定生效、如何使用

### 产出

策略可以由三类角色产出草案：

- 你自己
- `strategy_research_agent`
- `post_trade_review_agent`

但 AI 产出的都只能是**草案**，不能自动进入可执行状态。

### 审核

策略至少需要经过两层审核：

- 结构审核
  - 字段是否完整
  - 风险预算是否明确
  - 退出逻辑是否存在
- 风险审核
  - 是否与当前 `risk-limits.yaml` 冲突
  - 是否超出允许的时间级别、杠杆或品种边界

审核既可以由 AI 做初筛，也必须保留人工复核。

### 生效

策略进入 `armed` 只能由**人工操作员**决定。

也就是说：

- AI 可以提议
- AI 可以评论
- AI 可以复盘
- AI 不能自行激活策略
- AI 不能自行把 `draft` 改成 `armed`

### 使用

运行时，主 agent 只读取：

- 已 `armed` 的策略
- 当前时间级别匹配的策略
- 当前品种匹配的策略
- 当前运行模式允许的策略

之后由分析 agent 判断“当前市场是否满足该策略的触发条件”，由主 agent 形成候选 `TradeIntent`，再交给 `risk_engine`。

因此策略在系统里的定位是：

- 它不是直接下单的命令
- 它是约束主 agent 生成 `TradeIntent` 的模板和边界

## 仓库结构

```text
.
|-- AGENTS.md
|-- README.md
|-- config/
|   |-- cc-connect.project.example.toml
|   |-- okx.config.toml.example
|   |-- okx.env.example
|   |-- risk-limits.example.yaml
|   `-- strategy-registry.example.yaml
|-- docs/
|   |-- architecture.md
|   |-- cc-connect-integration.md
|   |-- okx-account-data.md
|   |-- okx-agent-kit-integration.md
|   |-- okx-demo-test.md
|   |-- okx-market-data.md
|   |-- rollout-plan.md
|   `-- strategy-governance.md
|-- skills/
|   |-- okx-execution/
|   |   |-- SKILL.md
|   |   `-- references/interface-contract.md
|   |-- risk-governor/
|   |   |-- SKILL.md
|   |   `-- references/live-gates.md
|   |-- trade-observability/
|   |   |-- SKILL.md
|   |   `-- references/feishu-report-template.md
|   `-- trading-orchestrator/
|       |-- SKILL.md
|       `-- references/decision-flow.md
|-- tools/
|   |-- okx_account_brief.py
|   |-- okx_account_snapshot.py
|   |-- okx_account_watch.py
|   |-- okx_demo_smoketest.py
|   |-- okx_market_watch.py
|   |-- okx_market_brief.py
|   `-- okx_market_snapshot.py
`-- state/
    |-- artifacts/
    |-- events/
    |-- journals/
    |-- reports/
    `-- snapshots/
```

## 推荐使用顺序

1. 先确认 `AGENTS.md` 中的角色边界、主 agent 责任和 live 限制。
2. 先确定运行模式，是 `manual_confirm` 还是 `guarded_auto`。
3. 先补策略注册表，再补真实的 `risk-limits.yaml`。
4. 跑公共行情链路，确认 `okx_market_watch.py` 输出稳定。
5. 在本地补齐 demo 凭证后，跑账户只读链路。
6. 跑 `okx_demo_smoketest.py`，确认两条链路能一起工作。
7. 补订单事件监听和对账能力，再考虑 demo 执行。
8. 只有在策略治理、风控闸门、事件回路和 journal 都稳定后，才考虑最小仓位 live。

## 当前不应该做的事情

- 不要把真实 API Key、Secret、Passphrase 提交到仓库
- 不要跳过 demo 和只读阶段直接接实盘
- 不要让 AI 自行激活新策略
- 不要让执行层绕开风险层
- 不要把聊天记录当成唯一审计记录
- 不要在没有 journal、快照和事件记录的情况下做正式交易动作

## 进一步阅读

- 架构展开说明：`docs/architecture.md`
- 策略治理：`docs/strategy-governance.md`
- OKX 公共行情链路：`docs/okx-market-data.md`
- OKX 账户只读链路：`docs/okx-account-data.md`
- demo 串联测试：`docs/okx-demo-test.md`
- OKX Agent Trade Kit 接入说明：`docs/okx-agent-kit-integration.md`
- `cc-connect + 飞书` 接入：`docs/cc-connect-integration.md`
- 渐进式上线计划：`docs/rollout-plan.md`
