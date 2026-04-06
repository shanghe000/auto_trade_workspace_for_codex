# OKX Demo 烟雾测试

## 目标

把当前已经接好的两条链路串起来，一次性验证：

- 公共行情链路是否正常
- demo 账户只读链路是否正常
- 本地快照和中文摘要是否能稳定落盘

这个阶段仍然不是执行测试，更不是实盘测试。

## 一键命令

在仓库根目录执行：

```bash
python3 tools/okx_demo_smoketest.py \
  --profile demo \
  --demo \
  --pretty-snapshot \
  --print-summary
```

## 当前依赖

这个烟雾测试会复用两类能力：

- 公共行情脚本：`tools/okx_market_snapshot.py`
- 账户只读脚本：`tools/okx_account_snapshot.py`

账户部分当前依赖 OKX 官方 CLI：

```bash
npx okx-trade-cli
```

## 本地前置条件

如果你只想验证公共行情，不需要任何凭证。

如果你要把 demo 账户链路也跑通，需要在本地补齐 demo 凭证，推荐二选一：

1. 填写 `config/okx.env`
2. 维护 `~/.okx/config.toml` 中的 `demo` profile

建议优先使用 demo 子账户和最小权限。

## 预期结果

运行后会更新这些文件：

- `state/snapshots/okx_market_snapshot.latest.json`
- `state/reports/okx_market_brief.latest.md`
- `state/snapshots/okx_account_snapshot.latest.json`
- `state/reports/okx_account_brief.latest.md`
- `state/reports/okx_demo_smoketest.latest.md`

其中 `okx_demo_smoketest.latest.md` 是本次串联测试的汇总结论。

## 结果判读

### 情况 1：行情通过，账户失败

这通常说明：

- 公共行情链路已经正常
- 账户链路大概率只差 demo 凭证

如果总结里出现：

```text
未检测到 OKX 私有接口凭证
```

说明当前问题不是脚本结构，而是本地还没有可用的 demo 凭证。

### 情况 2：行情通过，账户通过

这说明 demo 第一阶段已经达到目标：

- 行情可读
- 余额可读
- 持仓可读
- 挂单可读
- 账户配置可读

下一步就可以做“页面对账”和“风控联检”。

### 情况 3：行情失败

这时应先修公共行情，再看账户层。

## 与飞书回传

如果当前命令就是从 `cc-connect` 触发，并且环境里已有对应会话上下文，可以直接回传：

```bash
python3 tools/okx_demo_smoketest.py \
  --profile demo \
  --demo \
  --pretty-snapshot \
  --send-cc-connect \
  --send-file
```
