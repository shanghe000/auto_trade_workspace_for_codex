# OKX Agent Trade Kit 接入说明

## 为什么要单独写这份文档

这个仓库需要同时满足三件事：

- Codex 能理解并操作交易工作流
- 接入 OKX 时尽量复用官方现成能力
- 风险边界和可观测性不能被第三方工具模糊掉

因此，这里把 OKX 官方 Agent Trade Kit 与本仓库如何对齐单独说明。

## 官方能力概览

OKX 官方 Agent Trade Kit 当前提供三种主要接入方式：

- MCP Server：`okx-trade-mcp`
- CLI：`okx-trade-cli`
- Skills：适配支持 Skills 协议的 AI 客户端

对本仓库来说，推荐顺序是：

1. MCP
2. CLI
3. 自研直连 API 包装层

不建议第一版直接围绕外部 Skills 体系来组织整个仓库，因为本仓库已经有自己的角色契约与 skill 分层。

## 第一版推荐路径：MCP 优先

原因：

- 官方工具本地运行，凭证不出本机
- 支持只读模式
- 支持按模块过滤
- 已经覆盖了 `market`、`swap`、`account` 等你最需要的永续交易能力
- 比起一上来自己包整套 OKX API，MCP 的接入成本和维护成本更低

## 对本仓库最合适的模块组合

本仓库专注 BTC / ETH 永续，推荐显式指定模块，而不是吃默认值：

- `market`
- `swap`
- `account`

不建议默认开放：

- `spot`
- `bot`
- `earn`
- `option`
- `futures`

除非你的仓库范围真的扩展到这些能力。

## 推荐落地顺序

### 1. 先做无凭证行情验证

```bash
okx-trade-mcp --modules market
```

用于确认：

- MCP 进程能正常启动
- Codex 侧能拿到行情工具
- 本仓库的行情分析链路能跑通

### 2. 再做模拟盘只读验证

```bash
okx-trade-mcp --profile demo --modules market,swap,account --read-only
```

用于确认：

- 模拟盘凭证配置正确
- 账户、持仓、挂单、资金费率等查询能力正常
- 风控层能基于真实快照工作

### 3. 再做模拟盘可写验证

```bash
okx-trade-mcp --profile demo --modules market,swap,account
```

用于确认：

- 下单、改单、撤单链路完整
- 本地 journal 与交易所状态可对齐
- 执行层的标准化结果映射合理

### 4. 最后才考虑实盘

```bash
okx-trade-mcp --profile live --modules market,swap,account
```

前提必须是：

- 本仓库已有真实风控文件
- kill switch 可用
- 模拟盘对账稳定
- 飞书摘要和异常告警已经跑通

## 凭证与配置放哪里

如果走官方 MCP / CLI 路径，优先遵循官方约定，把 OKX 凭证放在：

- `~/.okx/config.toml`

而不是写进本仓库源码里。

本仓库里的 `config/okx.config.toml.example` 只是一个样例，用来提示你如何组织本地配置，不应该直接提交真实值。

## Codex 在这里怎么接 MCP

本仓库的设计假设是：

- OKX MCP 作为本地 stdio 服务器存在
- Codex 通过 MCP 能力访问 OKX 工具

如果自动 `setup` 脚本没有直接覆盖你的客户端，就按 MCP 通用方式手动注册 stdio 服务。仓库设计不依赖某个特定客户端向导是否存在。

## CLI 在本仓库里的定位

`okx-trade-cli` 更适合：

- 手工验证某个接口
- 做诊断和排障
- 做对账辅助
- 在 cron 中跑一些简单采集

它不应该成为策略层唯一依赖的执行规范。

## 自研 API 包装层何时需要

只有在这些条件成立时才考虑：

- 官方 MCP 缺少你必须的交易能力
- 你需要更细的重试、幂等或批量行为控制
- 你需要更稳定的自定义回包结构
- 你需要对某些执行流程做更严格的内部审计封装

否则第一版继续使用官方 MCP 会更稳。

