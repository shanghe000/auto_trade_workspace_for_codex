# OKX 公共行情链路

## 目标

先把不需要认证的 OKX 公共行情链路接通，为后续策略层、风控层和飞书日报提供统一输入。

当前实现是一个本地 Python 脚本：

- `tools/okx_market_snapshot.py`
- `tools/okx_market_brief.py`
- `tools/okx_market_watch.py`

它会抓取以下公共数据：

- ticker
- order book
- candles
- mark price
- open interest
- funding rate history 最新一条
- recent trades

然后把结果标准化写到：

- `state/snapshots/okx_market_snapshot.latest.json`

并可进一步生成中文 Markdown 摘要：

- `state/reports/okx_market_brief.latest.md`

## 默认覆盖范围

默认只抓两个永续合约：

- `BTC-USDT-SWAP`
- `ETH-USDT-SWAP`

## 运行方式

在仓库根目录执行：

```bash
python3 tools/okx_market_snapshot.py --pretty
python3 tools/okx_market_brief.py --print
```

如果你想一步完成“刷新行情 + 生成摘要”，直接执行：

```bash
python3 tools/okx_market_watch.py --pretty-snapshot --print-brief
```

如果当前就是从 `cc-connect` 会话里触发，并且环境中已有 `CC_PROJECT` / `CC_SESSION_KEY`，可以直接把摘要回传到当前会话：

```bash
python3 tools/okx_market_watch.py \
  --pretty-snapshot \
  --send-cc-connect \
  --send-file
```

如果不是在当前活跃会话里触发，也可以显式指定：

```bash
python3 tools/okx_market_watch.py \
  --pretty-snapshot \
  --send-cc-connect \
  --cc-project okx_trader_agent \
  --cc-session "<session-key>" \
  --send-file
```

如果你想显式指定品种：

```bash
python3 tools/okx_market_snapshot.py \
  --inst-id BTC-USDT-SWAP \
  --inst-id ETH-USDT-SWAP \
  --pretty
```

如果你想调整 K 线粒度和数量：

```bash
python3 tools/okx_market_snapshot.py \
  --bar 15m \
  --candles-limit 96 \
  --book-depth 10 \
  --trade-limit 50 \
  --pretty
```

## 输出结构

输出文件是一个聚合快照，顶层包含：

- 抓取时间
- OKX 系统时间
- 请求的品种列表
- 每个品种的标准化行情快照
- 抓取错误列表

每个品种当前包含：

- `ticker`
- `order_book`
- `mark_price`
- `open_interest`
- `funding_rate_latest`
- `candles`
- `recent_trades`

对应的中文摘要文件当前会输出：

- 抓取时间和时效状态
- BTC / ETH 当前价与 24h 涨跌
- 盘口价差、近场挂单厚度与主要买卖墙
- 未平仓价值（OI）
- 最近一根已收 K 线变化
- 最近一根已收 K 线成交量及相对上一根的变化
- 最近成交偏向
- 一组适合人读的观察标签

这份摘要在分析层的定位不是“只读 K 线简报”，而是最小多面输入：

- K 线
- 成交量
- OI
- 挂单 / 盘口

后续任何正式市场分析，都应以这四类输入为最小集合。

## 当前定位

这条链路的目标是先把“可读行情输入”接通，不是直接进入实盘。

因此第一阶段只保证：

- 数据可拉取
- 结构可复用
- 快照可落盘
- 后续策略层能稳定读取

暂时不保证：

- WebSocket 实时增量
- 多源对账
- 高频低延迟处理

## 与飞书的关系

这条链路现在已经具备三个层次：

1. 直接抓取 OKX 公共行情
2. 生成本地标准化快照
3. 生成中文 Markdown 摘要

如果运行环境里已经接入 `cc-connect`，还可以把摘要直接回传到飞书当前会话。

这意味着在还没有接通私有账户 API 的阶段，你已经可以先把“公共行情观察机器人”跑起来。

## 下一步建议

行情链路接通后，建议马上补两件事：

1. 在策略层定义“读取哪个快照文件、哪些字段是主字段”。
2. 在风控层把 `max_market_data_staleness_secs` 真正接入到快照时间校验。
3. 在 `cc-connect` 侧增加一个定时任务，把 Markdown 摘要推送到飞书。

## 推荐的下一条可执行命令

如果你现在就想把链路跑一遍，优先用这一条：

```bash
python3 tools/okx_market_watch.py --pretty-snapshot --print-brief
```

它会同时更新：

- `state/snapshots/okx_market_snapshot.latest.json`
- `state/reports/okx_market_brief.latest.md`
