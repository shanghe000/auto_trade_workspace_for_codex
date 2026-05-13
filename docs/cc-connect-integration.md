# cc-connect 接入说明

## 推荐项目形态

为这个交易仓库单独配置一个 `cc-connect project`，并让 `work_dir` 指向本仓库。

示例：

```toml
attachment_send = "on"

[[projects]]
name = "okx_trader_agent"
disabled_commands = ["shell", "dir", "restart", "upgrade", "config"]

[projects.agent]
type = "codex"

[projects.agent.options]
mode = "yolo"
work_dir = "/path/to/auto_trade_workspace_for_codex"

[[projects.platforms]]
type = "feishu"

[projects.platforms.options]
app_id = "cli_xxx"
app_secret = "sec_xxx"
allow_from = "ou_xxx"
thread_isolation = true
enable_feishu_card = true
```

这个结构与当前 `cc-connect` 的推荐范式一致：

- 一个 project
- 一个固定角色目录
- 一个 `AGENTS.md`
- 一个飞书机器人作为入口

## 这些配置为什么这样设

- `allow_from`
  - 交易机器人不应该对所有人开放
- `disabled_commands`
  - 默认关掉高风险管理命令
- `thread_isolation = true`
  - 群里每个主线程可以保持独立会话
- `enable_feishu_card = true`
  - 未来方便发结构化状态摘要

如果你的飞书卡片能力还不稳定，先把 `enable_feishu_card = false`，先用普通富文本跑通。

## 推荐操作流程

1. 启动 `cc-connect`。
2. 用 `cc-connect feishu setup --project okx_trader_agent` 绑定或创建飞书机器人。
3. 在飞书聊天里先发一次 `/cron setup`，确保运行时能力说明被刷新到位。
4. 验证普通文本回复。
5. 验证 Markdown 富文本效果。
6. 验证 `cc-connect send --file` / `--image` 的附件回传。
7. 在只读或 dry-run 模式下先发一份交易日报。
8. 只在整条链路都稳定后，再接入真实执行层。

## 建议的定时任务

这些任务不要一开始就开，等手动模式稳定后再加：

- 每 15 或 30 分钟：刷新市场、账户和风险摘要
- 每天开盘前或固定早晨：生成盘前观察
- 每天收盘前或固定时间：生成对账和 journal 摘要

如果你不希望定时任务继承太多旧会话上下文，优先使用 `new-per-run`。

## 飞书输出约定

优先使用普通 Markdown 文本，让 `cc-connect` 自己做渲染。

重要报告建议采用两段式：

- 正文回复里放简洁结论
- 图表、Markdown 导出或明细文件用 `cc-connect send` 作为附件回传

## 后续拆分建议

如果后面真的要拆 `risk_guard_agent` 或 `okx_executor_agent`，也建议先保留这个仓库作为第一入口，再逐步拆 project，不要一开始就把系统复杂化。
