#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import okx_market_brief
import okx_market_snapshot


DEFAULT_SNAPSHOT_OUTPUT = "state/snapshots/okx_market_snapshot.latest.json"
DEFAULT_BRIEF_OUTPUT = "state/reports/okx_market_brief.latest.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="一键刷新 OKX 公共行情快照并生成中文摘要。"
    )
    parser.add_argument(
        "--base-url",
        default=okx_market_snapshot.DEFAULT_BASE_URL,
        help="OKX API Base URL，默认 https://www.okx.com",
    )
    parser.add_argument(
        "--inst-id",
        dest="inst_ids",
        action="append",
        help="要抓取的合约，可重复传入；不传时默认 BTC/ETH 永续。",
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
        "--snapshot-output",
        default=DEFAULT_SNAPSHOT_OUTPUT,
        help=f"快照输出路径，默认 {DEFAULT_SNAPSHOT_OUTPUT}",
    )
    parser.add_argument(
        "--brief-output",
        default=DEFAULT_BRIEF_OUTPUT,
        help=f"摘要输出路径，默认 {DEFAULT_BRIEF_OUTPUT}",
    )
    parser.add_argument(
        "--max-staleness-secs",
        type=int,
        default=120,
        help="摘要中判定行情是否过期的阈值，默认 120 秒",
    )
    parser.add_argument(
        "--pretty-snapshot",
        action="store_true",
        help="快照 JSON 使用更易读的格式写出",
    )
    parser.add_argument(
        "--print-brief",
        action="store_true",
        help="把生成的 Markdown 摘要同时打印到标准输出",
    )
    parser.add_argument(
        "--send-cc-connect",
        action="store_true",
        help="通过 cc-connect send 把摘要发回当前会话或指定会话",
    )
    parser.add_argument(
        "--cc-project",
        default="",
        help="可选，显式指定 cc-connect 的 project 名称",
    )
    parser.add_argument(
        "--cc-session",
        default="",
        help="可选，显式指定 cc-connect 的 session key",
    )
    parser.add_argument(
        "--send-file",
        action="store_true",
        help="通过 cc-connect 发送正文时，同时附带 Markdown 摘要文件",
    )
    return parser.parse_args()


def send_via_cc_connect(
    report: str,
    brief_output: Path,
    cc_project: str,
    cc_session: str,
    send_file: bool,
) -> None:
    command = ["cc-connect", "send", "--stdin"]
    if cc_project:
        command.extend(["--project", cc_project])
    if cc_session:
        command.extend(["--session", cc_session])
    if send_file:
        command.extend(["--file", str(brief_output)])

    env = os.environ.copy()
    try:
        subprocess.run(
            command,
            input=report,
            text=True,
            check=True,
            env=env,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("未找到 cc-connect 可执行文件，无法回传到会话。") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"cc-connect send 执行失败，退出码 {exc.returncode}") from exc


def main() -> int:
    args = parse_args()

    snapshot_args = argparse.Namespace(
        base_url=args.base_url,
        inst_ids=args.inst_ids,
        bar=args.bar,
        candles_limit=args.candles_limit,
        book_depth=args.book_depth,
        trade_limit=args.trade_limit,
        timeout_secs=args.timeout_secs,
        request_delay_ms=args.request_delay_ms,
        output=args.snapshot_output,
        pretty=args.pretty_snapshot,
    )

    snapshot = okx_market_snapshot.build_snapshot(snapshot_args)
    snapshot_output = Path(args.snapshot_output)
    okx_market_snapshot.write_snapshot(
        snapshot,
        output_path=snapshot_output,
        pretty=args.pretty_snapshot,
    )

    brief_output = Path(args.brief_output)
    report = okx_market_brief.render_report(
        snapshot,
        max_staleness_secs=args.max_staleness_secs,
    )
    okx_market_brief.write_report(report, brief_output)

    print(f"已写入快照: {snapshot_output}")
    print(f"已写入摘要: {brief_output}")
    print(
        "抓取结果: "
        f"instruments={len(snapshot.get('instruments', []))} "
        f"errors={len(snapshot.get('errors', []))}"
    )

    if args.print_brief:
        print("")
        print(report)

    if args.send_cc_connect:
        send_via_cc_connect(
            report=report,
            brief_output=brief_output,
            cc_project=args.cc_project,
            cc_session=args.cc_session,
            send_file=args.send_file,
        )
        print("已通过 cc-connect send 发回会话。")

    return 0 if not snapshot.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
