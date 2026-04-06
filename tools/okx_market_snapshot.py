#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_BASE_URL = "https://www.okx.com"
DEFAULT_INSTRUMENTS = ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]
DEFAULT_OUTPUT = "state/snapshots/okx_market_snapshot.latest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="抓取 OKX 公共行情快照并写入本地 JSON 文件。"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="OKX API Base URL，默认 https://www.okx.com",
    )
    parser.add_argument(
        "--inst-id",
        dest="inst_ids",
        action="append",
        help="要抓取的合约，例如 BTC-USDT-SWAP。可重复传入；不传时默认 BTC/ETH 永续。",
    )
    parser.add_argument(
        "--bar",
        default="1H",
        help="K 线周期，默认 1H",
    )
    parser.add_argument(
        "--candles-limit",
        type=int,
        default=24,
        help="每个品种抓取的 K 线数量，默认 24",
    )
    parser.add_argument(
        "--book-depth",
        type=int,
        default=5,
        help="盘口深度，默认每边 5 档",
    )
    parser.add_argument(
        "--trade-limit",
        type=int,
        default=20,
        help="最近成交条数，默认 20",
    )
    parser.add_argument(
        "--timeout-secs",
        type=float,
        default=10.0,
        help="单次 HTTP 请求超时秒数，默认 10",
    )
    parser.add_argument(
        "--request-delay-ms",
        type=int,
        default=100,
        help="请求之间的最小间隔毫秒数，默认 100",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"输出文件路径，默认 {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="以更易读的 JSON 格式输出",
    )
    return parser.parse_args()


class OkxPublicClient:
    def __init__(self, base_url: str, timeout_secs: float, request_delay_ms: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_secs = timeout_secs
        self.request_delay_secs = max(request_delay_ms, 0) / 1000.0
        self.last_request_at = 0.0

    def get(self, path: str, params: Dict[str, Any]) -> List[Any]:
        self._respect_delay()
        query = urllib.parse.urlencode(
            {key: value for key, value in params.items() if value is not None}
        )
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"

        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "auto-trade-workspace/0.1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_secs) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} 请求失败: {url} -> {details}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"网络请求失败: {url} -> {exc}") from exc

        self.last_request_at = time.monotonic()
        payload = json.loads(body.decode("utf-8"))
        code = payload.get("code")
        if code not in (None, 0, "0"):
            raise RuntimeError(f"OKX 返回错误: path={path} code={code} msg={payload.get('msg')}")
        data = payload.get("data")
        if not isinstance(data, list):
            raise RuntimeError(f"OKX 返回格式异常: path={path} data={data!r}")
        return data

    def _respect_delay(self) -> None:
        if self.last_request_at <= 0 or self.request_delay_secs <= 0:
            return
        elapsed = time.monotonic() - self.last_request_at
        if elapsed < self.request_delay_secs:
            time.sleep(self.request_delay_secs - elapsed)


def decimal_or_none(value: Optional[str]) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def decimal_to_str(value: Optional[Decimal], places: Optional[int] = None) -> Optional[str]:
    if value is None:
        return None
    if places is not None:
        quant = Decimal("1").scaleb(-places)
        value = value.quantize(quant, rounding=ROUND_HALF_UP)
    return format(value, "f")


def now_ms() -> int:
    return int(time.time() * 1000)


def iso_from_ms(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc).isoformat()


def single_row(rows: List[Any], endpoint: str) -> Dict[str, Any]:
    if not rows:
        raise RuntimeError(f"{endpoint} 返回空数据")
    row = rows[0]
    if not isinstance(row, dict):
        raise RuntimeError(f"{endpoint} 返回格式异常: {row!r}")
    return row


def normalize_book_side(rows: List[Any]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, list) or len(item) < 4:
            continue
        normalized.append(
            {
                "price": item[0],
                "size": item[1],
                "deprecated_field": item[2],
                "order_count": item[3],
            }
        )
    return normalized


def normalize_candles(rows: List[Any]) -> List[Dict[str, Any]]:
    candles: List[Dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, list) or len(item) < 9:
            continue
        ts = str(item[0])
        candles.append(
            {
                "ts": ts,
                "ts_iso": iso_from_ms(int(ts)),
                "open": item[1],
                "high": item[2],
                "low": item[3],
                "close": item[4],
                "vol": item[5],
                "vol_ccy": item[6],
                "vol_ccy_quote": item[7],
                "confirm": item[8],
            }
        )
    return candles


def normalize_trades(rows: List[Any]) -> List[Dict[str, Any]]:
    trades: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ts = row.get("ts", "")
        trades.append(
            {
                "trade_id": row.get("tradeId"),
                "price": row.get("px"),
                "size": row.get("sz"),
                "side": row.get("side"),
                "ts": ts,
                "ts_iso": iso_from_ms(int(ts)) if str(ts).isdigit() else None,
            }
        )
    return trades


def normalize_ticker(row: Dict[str, Any]) -> Dict[str, Any]:
    bid = decimal_or_none(row.get("bidPx"))
    ask = decimal_or_none(row.get("askPx"))
    last = decimal_or_none(row.get("last"))
    spread = ask - bid if ask is not None and bid is not None else None
    mid = (ask + bid) / Decimal("2") if ask is not None and bid is not None else None
    spread_bps = (
        (spread / mid) * Decimal("10000")
        if spread is not None and mid not in (None, Decimal("0"))
        else None
    )
    return {
        "inst_id": row.get("instId"),
        "inst_type": row.get("instType"),
        "last": row.get("last"),
        "last_size": row.get("lastSz"),
        "bid_px": row.get("bidPx"),
        "bid_sz": row.get("bidSz"),
        "ask_px": row.get("askPx"),
        "ask_sz": row.get("askSz"),
        "open_24h": row.get("open24h"),
        "high_24h": row.get("high24h"),
        "low_24h": row.get("low24h"),
        "vol_24h_contracts": row.get("vol24h"),
        "vol_24h_base_ccy": row.get("volCcy24h"),
        "ts": row.get("ts"),
        "spread_px": decimal_to_str(spread),
        "spread_bps": decimal_to_str(spread_bps, places=4),
        "mid_px": decimal_to_str(mid),
        "last_vs_mid_px": decimal_to_str(last - mid if last is not None and mid is not None else None),
    }


def normalize_order_book(row: Dict[str, Any], depth: int) -> Dict[str, Any]:
    bids = normalize_book_side(row.get("bids", []))
    asks = normalize_book_side(row.get("asks", []))
    best_bid = decimal_or_none(bids[0]["price"]) if bids else None
    best_ask = decimal_or_none(asks[0]["price"]) if asks else None
    spread = best_ask - best_bid if best_ask is not None and best_bid is not None else None
    mid = (
        (best_ask + best_bid) / Decimal("2")
        if best_ask is not None and best_bid is not None
        else None
    )
    spread_bps = (
        (spread / mid) * Decimal("10000")
        if spread is not None and mid not in (None, Decimal("0"))
        else None
    )
    return {
        "depth": depth,
        "ts": row.get("ts"),
        "seq_id": row.get("seqId"),
        "best_bid_px": decimal_to_str(best_bid),
        "best_ask_px": decimal_to_str(best_ask),
        "spread_px": decimal_to_str(spread),
        "spread_bps": decimal_to_str(spread_bps, places=4),
        "bids": bids,
        "asks": asks,
    }


def normalize_mark_price(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "inst_id": row.get("instId"),
        "inst_type": row.get("instType"),
        "mark_px": row.get("markPx"),
        "ts": row.get("ts"),
    }


def normalize_open_interest(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "inst_id": row.get("instId"),
        "inst_type": row.get("instType"),
        "open_interest_contracts": row.get("oi"),
        "open_interest_base_ccy": row.get("oiCcy"),
        "open_interest_usd": row.get("oiUsd"),
        "ts": row.get("ts"),
    }


def normalize_funding(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {
        "inst_id": row.get("instId"),
        "funding_rate": row.get("fundingRate"),
        "realized_rate": row.get("realizedRate"),
        "funding_time": row.get("fundingTime"),
        "funding_time_iso": (
            iso_from_ms(int(row["fundingTime"]))
            if str(row.get("fundingTime", "")).isdigit()
            else None
        ),
        "method": row.get("method"),
        "formula_type": row.get("formulaType"),
    }


def fetch_system_time(client: OkxPublicClient) -> Dict[str, Any]:
    row = single_row(client.get("/api/v5/public/time", {}), "/api/v5/public/time")
    ts = row.get("ts")
    return {
        "ts": ts,
        "ts_iso": iso_from_ms(int(ts)) if str(ts).isdigit() else None,
    }


def fetch_instrument_snapshot(
    client: OkxPublicClient,
    inst_id: str,
    bar: str,
    candles_limit: int,
    trade_limit: int,
    book_depth: int,
) -> Dict[str, Any]:
    ticker = single_row(
        client.get("/api/v5/market/ticker", {"instId": inst_id}),
        "/api/v5/market/ticker",
    )
    order_book = single_row(
        client.get("/api/v5/market/books", {"instId": inst_id, "sz": str(book_depth)}),
        "/api/v5/market/books",
    )
    candles = client.get(
        "/api/v5/market/candles",
        {"instId": inst_id, "bar": bar, "limit": str(candles_limit)},
    )
    mark_price = single_row(
        client.get(
            "/api/v5/public/mark-price",
            {"instType": "SWAP", "instId": inst_id},
        ),
        "/api/v5/public/mark-price",
    )
    open_interest = single_row(
        client.get(
            "/api/v5/public/open-interest",
            {"instType": "SWAP", "instId": inst_id},
        ),
        "/api/v5/public/open-interest",
    )
    funding_rows = client.get(
        "/api/v5/public/funding-rate-history",
        {"instId": inst_id, "limit": "1"},
    )
    recent_trades = client.get(
        "/api/v5/market/trades",
        {"instId": inst_id, "limit": str(trade_limit)},
    )
    return {
        "inst_id": inst_id,
        "ticker": normalize_ticker(ticker),
        "order_book": normalize_order_book(order_book, depth=book_depth),
        "mark_price": normalize_mark_price(mark_price),
        "open_interest": normalize_open_interest(open_interest),
        "funding_rate_latest": normalize_funding(funding_rows[0] if funding_rows else None),
        "candles": {
            "bar": bar,
            "limit": candles_limit,
            "items": normalize_candles(candles),
        },
        "recent_trades": {
            "limit": trade_limit,
            "items": normalize_trades(recent_trades),
        },
    }


def build_snapshot(args: argparse.Namespace) -> Dict[str, Any]:
    inst_ids = args.inst_ids or DEFAULT_INSTRUMENTS
    client = OkxPublicClient(
        base_url=args.base_url,
        timeout_secs=args.timeout_secs,
        request_delay_ms=args.request_delay_ms,
    )
    captured_at = now_ms()
    snapshot: Dict[str, Any] = {
        "snapshot_type": "okx_public_market",
        "version": 1,
        "exchange": "okx",
        "base_url": client.base_url,
        "auth_required": False,
        "captured_at_ms": captured_at,
        "captured_at_iso": iso_from_ms(captured_at),
        "system_time": fetch_system_time(client),
        "requested_instruments": inst_ids,
        "instruments": [],
        "errors": [],
    }

    for inst_id in inst_ids:
        try:
            instrument_snapshot = fetch_instrument_snapshot(
                client=client,
                inst_id=inst_id,
                bar=args.bar,
                candles_limit=args.candles_limit,
                trade_limit=args.trade_limit,
                book_depth=args.book_depth,
            )
        except Exception as exc:  # noqa: BLE001
            snapshot["errors"].append({"inst_id": inst_id, "error": str(exc)})
            continue
        snapshot["instruments"].append(instrument_snapshot)

    return snapshot


def write_snapshot(snapshot: Dict[str, Any], output_path: Path, pretty: bool) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            snapshot,
            file,
            ensure_ascii=False,
            indent=2 if pretty else None,
            sort_keys=False,
        )
        file.write("\n")


def main() -> int:
    args = parse_args()
    snapshot = build_snapshot(args)
    output_path = Path(args.output)
    write_snapshot(snapshot, output_path=output_path, pretty=args.pretty)

    instrument_count = len(snapshot["instruments"])
    error_count = len(snapshot["errors"])
    print(
        f"已写入 OKX 公共行情快照: {output_path} | instruments={instrument_count} | errors={error_count}"
    )
    if error_count:
        for error in snapshot["errors"]:
            print(
                f"[error] {error['inst_id']}: {error['error']}",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
