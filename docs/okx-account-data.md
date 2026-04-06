# OKX 账户只读链路

## 目标

先在 demo 环境下，把账户相关的只读数据接通，而不是直接进入交易执行。

当前链路覆盖：

- 交易账户余额
- 资金账户余额
- 永续持仓
- 账户配置
- BTC / ETH 永续当前挂单

## 依赖

当前实现复用了 OKX 官方 CLI：

- `okx-trade-cli`

本仓库脚本默认通过：

```bash
npx okx-trade-cli
```

来调用它。

## 凭证来源

当前支持两种本地凭证来源：

1. `config/okx.env`
2. `~/.okx/config.toml`

如果你还没有任何本地凭证文件，先把：

```text
config/okx.env.example
```

复制为：

```text
config/okx.env
```

然后只填 demo 凭证。

## 当前脚本

- `tools/okx_account_snapshot.py`
- `tools/okx_account_brief.py`
- `tools/okx_account_watch.py`

## 推荐运行方式

### 1. 一键刷新账户快照并生成摘要

```bash
python3 tools/okx_account_watch.py \
  --profile demo \
  --demo \
  --pretty-snapshot \
  --print-brief
```

如果你想把“公共行情 + demo 账户只读”一起验证，优先直接跑：

```bash
python3 tools/okx_demo_smoketest.py \
  --profile demo \
  --demo \
  --pretty-snapshot \
  --print-summary
```

### 2. 如果当前就在 cc-connect 会话中，直接回传飞书

```bash
python3 tools/okx_account_watch.py \
  --profile demo \
  --demo \
  --pretty-snapshot \
  --send-cc-connect \
  --send-file
```

## 输出文件

脚本会更新：

- `state/snapshots/okx_account_snapshot.latest.json`
- `state/reports/okx_account_brief.latest.md`

## 当前定位

这条链路当前是“账户可观测性”链路，不是“执行链路”。

第一阶段目标只有三个：

- 能稳定读取 demo 账户数据
- 能把字段落成可复用快照
- 能生成人看得懂的摘要

## 推荐下一步

当这条链路跑通后，再做两件事：

1. 把账户快照与公共行情快照在风控层做联合校验。
2. 只有在 demo 的余额、持仓、挂单、配置都反复验证无误后，再考虑补执行层。
