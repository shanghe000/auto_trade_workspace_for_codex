#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_INPUT = "state/snapshots/okx_market_snapshot.latest.json"
DEFAULT_OUTPUT = "state/reports/okx_market_brief.latest.md"
SHANGHAI_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把 OKX 公共行情快照转换为中文 Markdown 摘要。"
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help=f"输入快照文件路径，默认 {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"输出 Markdown 文件路径，默认 {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--max-staleness-secs",
        type=int,
        default=120,
        help="行情快照超过多少秒视为过期，默认 120 秒",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        dest="print_stdout",
        help="同时把摘要打印到标准输出",
    )
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


def fmt_bps(value: Optional[Decimal], places: int = 2) -> str:
    return fmt_decimal(value, places=places, suffix=" bps")


def fmt_int_like(value: Optional[Decimal]) -> str:
    if value is None:
        return "n/a"
    return format(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP), "f")


def iso_to_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@dataclass
class InstrumentBrief:
    inst_id: str
    last: Optional[Decimal]
    change_24h_pct: Optional[Decimal]
    range_position_pct: Optional[Decimal]
    spread_bps: Optional[Decimal]
    funding_bps: Optional[Decimal]
    oi_usd: Optional[Decimal]
    last_closed_change_pct: Optional[Decimal]
    buy_trade_count: int
    sell_trade_count: int
    view_tags: List[str]


def load_snapshot(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def first_closed_pair(candles: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    closed = [item for item in candles if str(item.get("confirm")) == "1"]
    if len(closed) >= 2:
        return closed[0], closed[1]
    if len(closed) == 1:
        return closed[0], None
    return None, None


def build_tags(
    change_24h_pct: Optional[Decimal],
    range_position_pct: Optional[Decimal],
    funding_bps: Optional[Decimal],
    last_closed_change_pct: Optional[Decimal],
    buy_trade_count: int,
    sell_trade_count: int,
) -> List[str]:
    tags: List[str] = []

    if change_24h_pct is not None:
        if change_24h_pct >= Decimal("1.5"):
            tags.append("24h 偏强")
        elif change_24h_pct <= Decimal("-1.5"):
            tags.append("24h 偏弱")
        else:
            tags.append("24h 中性")

    if range_position_pct is not None:
        if range_position_pct >= Decimal("80"):
            tags.append("靠近 24h 高位")
        elif range_position_pct <= Decimal("20"):
            tags.append("靠近 24h 低位")
        else:
            tags.append("位于日内中段")

    if funding_bps is not None:
        if funding_bps >= Decimal("3"):
            tags.append("资金费率偏热")
        elif funding_bps <= Decimal("-3"):
            tags.append("资金费率偏冷")
        else:
            tags.append("资金费率中性")

    if last_closed_change_pct is not None:
        if last_closed_change_pct >= Decimal("0.5"):
            tags.append("最近一根收盘上行")
        elif last_closed_change_pct <= Decimal("-0.5"):
            tags.append("最近一根收盘走弱")
        else:
            tags.append("最近一根收盘震荡")

    trade_delta = buy_trade_count - sell_trade_count
    if trade_delta >= 4:
        tags.append("最近成交偏买方")
    elif trade_delta <= -4:
        tags.append("最近成交偏卖方")
    else:
        tags.append("最近成交方向均衡")

    return tags


def summarize_instrument(item: Dict[str, Any]) -> InstrumentBrief:
    ticker = item.get("ticker", {})
    order_book = item.get("order_book", {})
    funding = item.get("funding_rate_latest") or {}
    open_interest = item.get("open_interest", {})
    candles = (item.get("candles") or {}).get("items", [])
    recent_trades = (item.get("recent_trades") or {}).get("items", [])

    last = dec(ticker.get("last"))
    open_24h = dec(ticker.get("open_24h"))
    low_24h = dec(ticker.get("low_24h"))
    high_24h = dec(ticker.get("high_24h"))
    spread_bps = dec(order_book.get("spread_bps"))
    funding_rate = dec(funding.get("funding_rate"))
    funding_bps = funding_rate * Decimal("10000") if funding_rate is not None else None
    oi_usd = dec(open_interest.get("open_interest_usd"))

    change_24h_pct = None
    if last not in (None, Decimal("0")) and open_24h not in (None, Decimal("0")):
        change_24h_pct = (last / open_24h - Decimal("1")) * Decimal("100")

    range_position_pct = None
    if (
        last is not None
        and low_24h is not None
        and high_24h is not None
        and high_24h != low_24h
    ):
        range_position_pct = ((last - low_24h) / (high_24h - low_24h)) * Decimal("100")

    latest_closed, prev_closed = first_closed_pair(candles)
    last_closed_change_pct = None
    if latest_closed and prev_closed:
        latest_close = dec(latest_closed.get("close"))
        prev_close = dec(prev_closed.get("close"))
        if latest_close is not None and prev_close not in (None, Decimal("0")):
            last_closed_change_pct = (latest_close / prev_close - Decimal("1")) * Decimal("100")

    buy_trade_count = 0
    sell_trade_count = 0
    for trade in recent_trades:
        side = str(trade.get("side", "")).lower()
        if side == "buy":
            buy_trade_count += 1
        elif side == "sell":
            sell_trade_count += 1

    tags = build_tags(
        change_24h_pct=change_24h_pct,
        range_position_pct=range_position_pct,
        funding_bps=funding_bps,
        last_closed_change_pct=last_closed_change_pct,
        buy_trade_count=buy_trade_count,
        sell_trade_count=sell_trade_count,
    )

    return InstrumentBrief(
        inst_id=str(item.get("inst_id")),
        last=last,
        change_24h_pct=change_24h_pct,
        range_position_pct=range_position_pct,
        spread_bps=spread_bps,
        funding_bps=funding_bps,
        oi_usd=oi_usd,
        last_closed_change_pct=last_closed_change_pct,
        buy_trade_count=buy_trade_count,
        sell_trade_count=sell_trade_count,
        view_tags=tags,
    )


def render_report(snapshot: Dict[str, Any], max_staleness_secs: int) -> str:
    captured_at_ms = int(snapshot.get("captured_at_ms", 0))
    captured_at_dt = (
        datetime.fromtimestamp(captured_at_ms / 1000.0, tz=timezone.utc)
        if captured_at_ms
        else None
    )
    now_dt = datetime.now(tz=timezone.utc)
    age_secs = (now_dt - captured_at_dt).total_seconds() if captured_at_dt else None
    stale = age_secs is None or age_secs > max_staleness_secs

    system_time = snapshot.get("system_time", {})
    system_time_dt = iso_to_dt(system_time.get("ts_iso"))
    briefs = [summarize_instrument(item) for item in snapshot.get("instruments", [])]

    lines: List[str] = []
    lines.append("# OKX 公共行情摘要")
    lines.append("")
    if captured_at_dt:
        lines.append(
            f"- 抓取时间（UTC）: `{captured_at_dt.isoformat()}`"
        )
        lines.append(
            f"- 抓取时间（Asia/Shanghai）: `{captured_at_dt.astimezone(SHANGHAI_TZ).isoformat()}`"
        )
    if system_time_dt:
        lines.append(f"- OKX 系统时间（UTC）: `{system_time_dt.isoformat()}`")
    if age_secs is not None:
        lines.append(f"- 快照时效: `{int(age_secs)} 秒`")
    lines.append(f"- 时效状态: `{'过期' if stale else '新鲜'}`")
    lines.append(f"- 覆盖品种数: `{len(briefs)}`")
    if snapshot.get("errors"):
        lines.append(f"- 抓取错误数: `{len(snapshot['errors'])}`")
    lines.append("")

    lines.append("## 总览")
    lines.append("")
    for brief in briefs:
        lines.append(
            f"- `{brief.inst_id}` 当前价 `{fmt_decimal(brief.last, 2)}`，24h 涨跌 `{fmt_pct(brief.change_24h_pct, 2)}`，"
            f"盘口价差 `{fmt_bps(brief.spread_bps, 2)}`，资金费率 `{fmt_bps(brief.funding_bps, 3)}`，"
            f"未平仓名义价值 `{fmt_int_like(brief.oi_usd)} USD`。"
        )
    lines.append("")

    for brief in briefs:
        lines.append(f"## {brief.inst_id}")
        lines.append("")
        lines.append(
            f"- 24h 位置: `{fmt_pct(brief.range_position_pct, 2)}`，最近一根已收 K 线涨跌: `{fmt_pct(brief.last_closed_change_pct, 2)}`。"
        )
        lines.append(
            f"- 最近成交方向: `buy {brief.buy_trade_count} / sell {brief.sell_trade_count}`。"
        )
        lines.append(f"- 观察标签: `{' | '.join(brief.view_tags)}`")
        lines.append("")

    if snapshot.get("errors"):
        lines.append("## 抓取错误")
        lines.append("")
        for error in snapshot["errors"]:
            lines.append(f"- `{error.get('inst_id', 'unknown')}`: {error.get('error', 'unknown error')}")
        lines.append("")

    lines.append("## 使用建议")
    lines.append("")
    if stale:
        lines.append("- 当前快照已经过期，不要直接把它作为下单依据；先刷新行情。")
    else:
        lines.append("- 当前快照时效尚可，可以作为策略层初筛输入，但仍不等于可直接下单。")
    lines.append("- 真正进入风控与执行前，还需要接入账户、挂单和持仓快照。")
    lines.append("- 如果要发飞书，优先把这份 Markdown 当成正文或附件内容。")
    lines.append("")

    return "\n".join(lines)


def write_report(content: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    snapshot = load_snapshot(input_path)
    report = render_report(snapshot, max_staleness_secs=args.max_staleness_secs)
    write_report(report, output_path)
    print(f"已写入 OKX 行情摘要: {output_path}")
    if args.print_stdout:
        print("")
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
