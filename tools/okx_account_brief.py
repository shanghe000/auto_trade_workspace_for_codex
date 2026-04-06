#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_INPUT = "state/snapshots/okx_account_snapshot.latest.json"
DEFAULT_OUTPUT = "state/reports/okx_account_brief.latest.md"
SHANGHAI_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把 OKX 账户只读快照转换为中文 Markdown 摘要。"
    )
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--max-staleness-secs", type=int, default=120)
    parser.add_argument("--print", action="store_true", dest="print_stdout")
    return parser.parse_args()


def dec(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def fmt_decimal(value: Optional[Decimal], places: int = 2, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    quant = Decimal("1").scaleb(-places)
    value = value.quantize(quant, rounding=ROUND_HALF_UP)
    return f"{format(value, 'f')}{suffix}"


def fmt_pct(value: Optional[Decimal], places: int = 2) -> str:
    return fmt_decimal(value, places=places, suffix="%")


def load_snapshot(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_report(content: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def render_report(snapshot: Dict[str, Any], max_staleness_secs: int) -> str:
    captured_at_ms = int(snapshot.get("captured_at_ms", 0))
    captured_at = (
        datetime.fromtimestamp(captured_at_ms / 1000.0, tz=timezone.utc)
        if captured_at_ms
        else None
    )
    now_dt = datetime.now(tz=timezone.utc)
    age_secs = int((now_dt - captured_at).total_seconds()) if captured_at else None
    stale = age_secs is None or age_secs > max_staleness_secs

    normalized = snapshot.get("normalized", {})
    trading_balance = normalized.get("trading_balance", {})
    funding_balance = normalized.get("funding_balance", {})
    positions = normalized.get("positions", []) or []
    open_orders = normalized.get("open_orders", {}) or {}
    account_config = normalized.get("account_config", {}) or {}
    errors = snapshot.get("errors", []) or []

    trading_balances = trading_balance.get("balances", []) or []
    funding_balances = funding_balance.get("balances", []) or []

    tracked_trading = [
        item for item in trading_balances if item.get("ccy") in {"USDT", "BTC", "ETH"}
    ]
    tracked_funding = [
        item for item in funding_balances if item.get("ccy") in {"USDT", "BTC", "ETH"}
    ]

    lines: List[str] = []
    lines.append("# OKX 账户只读摘要")
    lines.append("")
    if captured_at:
        lines.append(f"- 抓取时间（UTC）: `{captured_at.isoformat()}`")
        lines.append(f"- 抓取时间（Asia/Shanghai）: `{captured_at.astimezone(SHANGHAI_TZ).isoformat()}`")
    if age_secs is not None:
        lines.append(f"- 快照时效: `{age_secs} 秒`")
    lines.append(f"- 时效状态: `{'过期' if stale else '新鲜'}`")
    lines.append(f"- profile: `{snapshot.get('profile', 'unknown')}`")
    lines.append(f"- 模式: `{snapshot.get('mode', 'unknown')}`")
    lines.append("")

    lines.append("## 账户总览")
    lines.append("")
    lines.append(f"- 交易账户总权益（USD）: `{trading_balance.get('total_eq_usd', 'n/a')}`")
    lines.append(f"- 调整后权益（USD）: `{trading_balance.get('adj_eq_usd', 'n/a')}`")
    lines.append(f"- 当前持仓数: `{len(positions)}`")
    lines.append(f"- 当前挂单数: `{sum(len(items) for items in open_orders.values())}`")
    lines.append(f"- 账户模式: `acctLv={account_config.get('acct_lv', 'n/a')}` / `posMode={account_config.get('pos_mode', 'n/a')}`")
    lines.append("")

    lines.append("## 交易账户余额")
    lines.append("")
    if tracked_trading:
        for item in tracked_trading:
            lines.append(
                f"- `{item.get('ccy', 'unknown')}`: "
                f"权益 `{item.get('eq', 'n/a')}` / 可用 `{item.get('avail_eq', 'n/a')}` / UPL `{item.get('upl', 'n/a')}`"
            )
    else:
        lines.append("- 未读取到重点币种余额。")
    lines.append("")

    lines.append("## 资金账户余额")
    lines.append("")
    if tracked_funding:
        for item in tracked_funding:
            lines.append(
                f"- `{item.get('ccy', 'unknown')}`: "
                f"余额 `{item.get('bal', 'n/a')}` / 可用 `{item.get('avail_bal', 'n/a')}`"
            )
    else:
        lines.append("- 未读取到重点币种资金余额。")
    lines.append("")

    lines.append("## 当前持仓")
    lines.append("")
    if positions:
        for item in positions:
            lines.append(
                f"- `{item.get('inst_id', 'unknown')}` "
                f"`{item.get('pos_side', 'n/a')}` "
                f"仓位 `{item.get('pos', 'n/a')}`，"
                f"开仓均价 `{item.get('avg_px', 'n/a')}`，"
                f"标记价格 `{item.get('mark_px', 'n/a')}`，"
                f"未实现盈亏 `{item.get('upl', 'n/a')}`，"
                f"收益率 `{item.get('upl_ratio', 'n/a')}`，"
                f"杠杆 `{item.get('lever', 'n/a')}`，"
                f"强平价 `{item.get('liq_px', 'n/a')}`。"
            )
    else:
        lines.append("- 当前没有未平仓持仓，或还未成功读到持仓数据。")
    lines.append("")

    lines.append("## 当前挂单")
    lines.append("")
    total_open_orders = 0
    for inst_id, items in open_orders.items():
        if not items:
            continue
        total_open_orders += len(items)
        lines.append(f"### {inst_id}")
        lines.append("")
        for item in items:
            lines.append(
                f"- `ordId={item.get('ord_id', 'n/a')}` "
                f"`{item.get('side', 'n/a')}` "
                f"`{item.get('ord_type', 'n/a')}` "
                f"状态 `{item.get('state', 'n/a')}`，"
                f"价格 `{item.get('px', 'n/a')}`，"
                f"数量 `{item.get('sz', 'n/a')}`，"
                f"已成交 `{item.get('acc_fill_sz', 'n/a')}`。"
            )
        lines.append("")
    if total_open_orders == 0:
        lines.append("- 当前没有 BTC/ETH 永续挂单，或还未成功读到挂单数据。")
        lines.append("")

    if errors:
        lines.append("## 抓取错误")
        lines.append("")
        for error in errors:
            lines.append(f"- `{error.get('command', 'unknown')}`: {error.get('error', 'unknown error')}")
        lines.append("")

    lines.append("## 使用建议")
    lines.append("")
    if stale:
        lines.append("- 当前账户快照已过期，进入任何风控或执行前应先刷新。")
    else:
        lines.append("- 当前账户快照时效尚可，可以作为风控前输入。")
    lines.append("- 这是只读链路，目标是先验证余额、持仓、挂单与账户配置能稳定读取。")
    lines.append("- 如果你后面要接执行层，先确保 demo 环境下这些字段和 OKX 页面完全对得上。")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    snapshot = load_snapshot(Path(args.input))
    report = render_report(snapshot, max_staleness_secs=args.max_staleness_secs)
    write_report(report, Path(args.output))
    print(f"已写入 OKX 账户摘要: {args.output}")
    if args.print_stdout:
        print("")
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
