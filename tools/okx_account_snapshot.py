#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_PROFILE = "demo"
DEFAULT_ENV_FILE = "config/okx.env"
DEFAULT_OUTPUT = "state/snapshots/okx_account_snapshot.latest.json"
DEFAULT_INSTRUMENTS = ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]
DEFAULT_CLI_CMD = "npx okx-trade-cli"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="通过 OKX 官方 CLI 抓取账户只读快照。"
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help="OKX profile 名称，默认 demo",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="强制使用 demo 模式",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="强制使用 live 模式",
    )
    parser.add_argument(
        "--env-file",
        default=DEFAULT_ENV_FILE,
        help=f"可选，本地凭证 env 文件路径，默认 {DEFAULT_ENV_FILE}",
    )
    parser.add_argument(
        "--cli-cmd",
        default=DEFAULT_CLI_CMD,
        help=f"调用 OKX 官方 CLI 的命令，默认 `{DEFAULT_CLI_CMD}`",
    )
    parser.add_argument(
        "--inst-id",
        dest="inst_ids",
        action="append",
        help="需要额外抓取挂单的永续合约，可重复传入；默认 BTC/ETH 永续",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"输出快照文件路径，默认 {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="以更易读的 JSON 格式输出",
    )
    parser.add_argument(
        "--verbose-cli",
        action="store_true",
        help="让底层 OKX CLI 带上 --verbose",
    )
    return parser.parse_args()


def now_ms() -> int:
    return int(time.time() * 1000)


def iso_from_ms(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc).isoformat()


def load_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    env: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip("'").strip('"')
    return env


def build_env(env_file_values: Dict[str, str]) -> Dict[str, str]:
    env = os.environ.copy()
    env.update(env_file_values)

    if not env.get("OKX_SECRET_KEY") and env.get("OKX_API_SECRET"):
        env["OKX_SECRET_KEY"] = env["OKX_API_SECRET"]
    if not env.get("OKX_PASSPHRASE") and env.get("OKX_API_PASSPHRASE"):
        env["OKX_PASSPHRASE"] = env["OKX_API_PASSPHRASE"]

    return env


def okx_base_command(args: argparse.Namespace) -> List[str]:
    command = shlex.split(args.cli_cmd)
    command.extend(["--profile", args.profile, "--json"])
    if args.verbose_cli:
        command.append("--verbose")
    if args.demo and args.live:
        raise RuntimeError("--demo 和 --live 不能同时使用")
    if args.demo:
        command.append("--demo")
    elif args.live:
        command.append("--live")
    return command


def run_okx_json(
    base_command: List[str],
    subcommand: List[str],
    env: Dict[str, str],
) -> Any:
    command = [*base_command, *subcommand]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(stderr or f"OKX CLI 执行失败: {' '.join(command)}")
    stdout = (result.stdout or "").strip()
    if not stdout:
        raise RuntimeError(f"OKX CLI 未返回 JSON: {' '.join(command)}")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OKX CLI 输出不是合法 JSON: {stdout[:300]}") from exc


def extract_data_list(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def normalize_balance(payload: Any) -> Dict[str, Any]:
    rows = extract_data_list(payload)
    row = rows[0] if rows else {}
    details = row.get("details", [])
    balances = []
    for item in details:
        if not isinstance(item, dict):
            continue
        balances.append(
            {
                "ccy": item.get("ccy"),
                "cash_bal": item.get("cashBal"),
                "eq": item.get("eq"),
                "eq_usd": item.get("eqUsd"),
                "avail_eq": item.get("availEq"),
                "avail_bal": item.get("availBal"),
                "frozen_bal": item.get("frozenBal"),
                "upl": item.get("upl"),
            }
        )
    return {
        "adj_eq_usd": row.get("adjEq"),
        "total_eq_usd": row.get("totalEq"),
        "imr": row.get("imr"),
        "mmr": row.get("mmr"),
        "notional_usd": row.get("notionalUsd"),
        "balances": balances,
    }


def normalize_asset_balance(payload: Any) -> Dict[str, Any]:
    rows = extract_data_list(payload)
    balances = []
    for item in rows:
        balances.append(
            {
                "ccy": item.get("ccy"),
                "bal": item.get("bal"),
                "avail_bal": item.get("availBal"),
                "frozen_bal": item.get("frozenBal"),
            }
        )
    return {"balances": balances}


def normalize_positions(payload: Any) -> List[Dict[str, Any]]:
    rows = extract_data_list(payload)
    positions = []
    for item in rows:
        positions.append(
            {
                "inst_id": item.get("instId"),
                "inst_type": item.get("instType"),
                "pos_side": item.get("posSide"),
                "pos": item.get("pos"),
                "avg_px": item.get("avgPx"),
                "mark_px": item.get("markPx"),
                "upl": item.get("upl"),
                "upl_ratio": item.get("uplRatio"),
                "liq_px": item.get("liqPx"),
                "lever": item.get("lever"),
                "mgn_mode": item.get("mgnMode"),
                "notional_usd": item.get("notionalUsd"),
                "adl": item.get("adl"),
                "c_time": item.get("cTime"),
                "u_time": item.get("uTime"),
            }
        )
    return positions


def normalize_config(payload: Any) -> Dict[str, Any]:
    rows = extract_data_list(payload)
    row = rows[0] if rows else {}
    return {
        "acct_lv": row.get("acctLv"),
        "pos_mode": row.get("posMode"),
        "greeks_type": row.get("greeksType"),
        "level": row.get("level"),
        "auto_loan": row.get("autoLoan"),
        "ct_iso_mode": row.get("ctIsoMode"),
        "mgn_iso_mode": row.get("mgnIsoMode"),
        "acct_stp_mode": row.get("acctStpMode"),
    }


def normalize_orders(payload: Any) -> List[Dict[str, Any]]:
    rows = extract_data_list(payload)
    orders = []
    for item in rows:
        orders.append(
            {
                "inst_id": item.get("instId"),
                "ord_id": item.get("ordId"),
                "cl_ord_id": item.get("clOrdId"),
                "side": item.get("side"),
                "pos_side": item.get("posSide"),
                "ord_type": item.get("ordType"),
                "state": item.get("state"),
                "px": item.get("px"),
                "sz": item.get("sz"),
                "acc_fill_sz": item.get("accFillSz"),
                "fill_px": item.get("fillPx"),
                "lever": item.get("lever"),
                "td_mode": item.get("tdMode"),
                "tp_trigger_px": item.get("tpTriggerPx"),
                "sl_trigger_px": item.get("slTriggerPx"),
                "c_time": item.get("cTime"),
                "u_time": item.get("uTime"),
            }
        )
    return orders


def detect_setup_hint(error: Exception, env_file: Path) -> str:
    message = str(error)
    if "Private endpoint requires API credentials" in message:
        return (
            "未检测到 OKX 私有接口凭证。"
            f" 请在 `{env_file}` 中填写 demo 凭证，或在 `~/.okx/config.toml` 中配置 `demo` profile。"
        )
    return message


def build_snapshot(args: argparse.Namespace) -> Dict[str, Any]:
    env_file = Path(args.env_file)
    env_values = load_env_file(env_file)
    env = build_env(env_values)
    inst_ids = args.inst_ids or DEFAULT_INSTRUMENTS
    captured_at_ms = now_ms()

    snapshot: Dict[str, Any] = {
        "snapshot_type": "okx_private_account_readonly",
        "version": 1,
        "exchange": "okx",
        "captured_at_ms": captured_at_ms,
        "captured_at_iso": iso_from_ms(captured_at_ms),
        "profile": args.profile,
        "mode": "demo" if args.demo or env.get("OKX_ENV") == "demo" else "live",
        "auth_required": True,
        "env_file_present": env_file.exists(),
        "inst_ids": inst_ids,
        "commands": [],
        "raw": {},
        "normalized": {},
        "errors": [],
    }

    base_command = okx_base_command(args)
    commands = [
        ("trading_balance", ["account", "balance"]),
        ("funding_balance", ["account", "asset-balance"]),
        ("positions", ["account", "positions", "--instType", "SWAP"]),
        ("account_config", ["account", "config"]),
    ]
    for inst_id in inst_ids:
        commands.append((f"open_orders:{inst_id}", ["swap", "orders", "--instId", inst_id]))

    for name, subcommand in commands:
        snapshot["commands"].append(" ".join([*base_command, *subcommand]))
        try:
            payload = run_okx_json(base_command, subcommand, env)
        except Exception as exc:  # noqa: BLE001
            snapshot["errors"].append({"command": name, "error": detect_setup_hint(exc, env_file)})
            continue
        snapshot["raw"][name] = payload

    if "trading_balance" in snapshot["raw"]:
        snapshot["normalized"]["trading_balance"] = normalize_balance(snapshot["raw"]["trading_balance"])
    if "funding_balance" in snapshot["raw"]:
        snapshot["normalized"]["funding_balance"] = normalize_asset_balance(snapshot["raw"]["funding_balance"])
    if "positions" in snapshot["raw"]:
        snapshot["normalized"]["positions"] = normalize_positions(snapshot["raw"]["positions"])
    if "account_config" in snapshot["raw"]:
        snapshot["normalized"]["account_config"] = normalize_config(snapshot["raw"]["account_config"])

    open_orders: Dict[str, Any] = {}
    for inst_id in inst_ids:
        key = f"open_orders:{inst_id}"
        if key in snapshot["raw"]:
            open_orders[inst_id] = normalize_orders(snapshot["raw"][key])
    snapshot["normalized"]["open_orders"] = open_orders

    return snapshot


def write_snapshot(snapshot: Dict[str, Any], output_path: Path, pretty: bool) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(snapshot, file, ensure_ascii=False, indent=2 if pretty else None)
        file.write("\n")


def main() -> int:
    args = parse_args()
    snapshot = build_snapshot(args)
    output_path = Path(args.output)
    write_snapshot(snapshot, output_path=output_path, pretty=args.pretty)

    print(
        "已写入 OKX 账户只读快照: "
        f"{output_path} | normalized_keys={len(snapshot.get('normalized', {}))} | "
        f"errors={len(snapshot.get('errors', []))}"
    )

    if snapshot.get("errors"):
        for error in snapshot["errors"]:
            print(f"[error] {error['command']}: {error['error']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
