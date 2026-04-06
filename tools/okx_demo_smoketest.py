#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import okx_account_brief
import okx_account_snapshot
import okx_market_brief
import okx_market_snapshot


DEFAULT_MARKET_SNAPSHOT_OUTPUT = "state/snapshots/okx_market_snapshot.latest.json"
DEFAULT_MARKET_BRIEF_OUTPUT = "state/reports/okx_market_brief.latest.md"
DEFAULT_ACCOUNT_SNAPSHOT_OUTPUT = "state/snapshots/okx_account_snapshot.latest.json"
DEFAULT_ACCOUNT_BRIEF_OUTPUT = "state/reports/okx_account_brief.latest.md"
DEFAULT_SUMMARY_OUTPUT = "state/reports/okx_demo_smoketest.latest.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="串行执行 OKX demo 行情链路与账户只读链路的烟雾测试。"
    )
    parser.add_argument("--profile", default="demo")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--env-file", default="config/okx.env")
    parser.add_argument("--cli-cmd", default="npx okx-trade-cli")
    parser.add_argument("--inst-id", dest="inst_ids", action="append")
    parser.add_argument(
        "--market-snapshot-output",
        default=DEFAULT_MARKET_SNAPSHOT_OUTPUT,
    )
    parser.add_argument(
        "--market-brief-output",
        default=DEFAULT_MARKET_BRIEF_OUTPUT,
    )
    parser.add_argument(
        "--account-snapshot-output",
        default=DEFAULT_ACCOUNT_SNAPSHOT_OUTPUT,
    )
    parser.add_argument(
        "--account-brief-output",
        default=DEFAULT_ACCOUNT_BRIEF_OUTPUT,
    )
    parser.add_argument(
        "--summary-output",
        default=DEFAULT_SUMMARY_OUTPUT,
    )
    parser.add_argument("--pretty-snapshot", action="store_true")
    parser.add_argument("--max-staleness-secs", type=int, default=120)
    parser.add_argument("--print-summary", action="store_true")
    parser.add_argument("--send-cc-connect", action="store_true")
    parser.add_argument("--cc-project", default="")
    parser.add_argument("--cc-session", default="")
    parser.add_argument("--send-file", action="store_true")
    parser.add_argument("--verbose-cli", action="store_true")
    return parser.parse_args()


def send_via_cc_connect(
    report: str,
    attachments: List[Path],
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
        for path in attachments:
            command.extend(["--file", str(path)])

    try:
        subprocess.run(
            command,
            input=report,
            text=True,
            check=True,
            env=os.environ.copy(),
        )
    except FileNotFoundError as exc:
        raise RuntimeError("未找到 cc-connect 可执行文件，无法回传到会话。") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"cc-connect send 执行失败，退出码 {exc.returncode}") from exc


def status_emoji(errors: List[Dict[str, Any]]) -> str:
    return "通过" if not errors else "失败"


def detect_next_action(account_errors: List[Dict[str, Any]]) -> str:
    if not account_errors:
        return "demo 账户链路已打通，下一步可以核对 OKX 页面上的余额、持仓、挂单与本地摘要是否一致。"
    if all("未检测到 OKX 私有接口凭证" in str(item.get("error", "")) for item in account_errors):
        return "当前只差 demo 凭证。请在 `config/okx.env` 或 `~/.okx/config.toml` 中补齐 demo 凭证后重跑。"
    return "账户链路存在非凭证类错误。建议先查看 `state/snapshots/okx_account_snapshot.latest.json` 中的 `errors`。"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render_summary(
    market_snapshot: Dict[str, Any],
    account_snapshot: Dict[str, Any],
    market_report_path: Path,
    account_report_path: Path,
) -> str:
    market_errors = market_snapshot.get("errors", []) or []
    account_errors = account_snapshot.get("errors", []) or []
    market_inst_count = len(market_snapshot.get("instruments", []) or [])
    account_keys = len(account_snapshot.get("normalized", {}) or {})

    lines: List[str] = []
    lines.append("# OKX Demo 烟雾测试")
    lines.append("")
    lines.append(f"- 行情链路: `{status_emoji(market_errors)}`")
    lines.append(f"- 账户只读链路: `{status_emoji(account_errors)}`")
    lines.append(f"- 行情覆盖品种数: `{market_inst_count}`")
    lines.append(f"- 账户标准化键数: `{account_keys}`")
    lines.append("")

    lines.append("## 本次结论")
    lines.append("")
    if not market_errors and not account_errors:
        lines.append("- 公共行情和 demo 账户只读链路都已通过。")
    elif not market_errors and account_errors:
        lines.append("- 公共行情链路已通过，账户只读链路未完全通过。")
    else:
        lines.append("- 当前至少有一条核心链路未通过，需要先修复后再进入策略或执行层。")
    lines.append(f"- 下一步建议: {detect_next_action(account_errors)}")
    lines.append("")

    lines.append("## 产物")
    lines.append("")
    lines.append(f"- 行情摘要: `{market_report_path}`")
    lines.append(f"- 账户摘要: `{account_report_path}`")
    lines.append("")

    if market_errors:
        lines.append("## 行情错误")
        lines.append("")
        for error in market_errors:
            lines.append(f"- `{error.get('source', 'unknown')}`: {error.get('error', 'unknown error')}")
        lines.append("")

    if account_errors:
        lines.append("## 账户错误")
        lines.append("")
        for error in account_errors:
            lines.append(f"- `{error.get('command', 'unknown')}`: {error.get('error', 'unknown error')}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    market_args = argparse.Namespace(
        base_url=okx_market_snapshot.DEFAULT_BASE_URL,
        inst_ids=args.inst_ids,
        bar="1H",
        candles_limit=24,
        book_depth=5,
        trade_limit=20,
        timeout_secs=10.0,
        request_delay_ms=100,
        output=args.market_snapshot_output,
        pretty=args.pretty_snapshot,
    )
    market_snapshot = okx_market_snapshot.build_snapshot(market_args)
    market_snapshot_output = Path(args.market_snapshot_output)
    okx_market_snapshot.write_snapshot(
        market_snapshot,
        output_path=market_snapshot_output,
        pretty=args.pretty_snapshot,
    )
    market_report = okx_market_brief.render_report(
        market_snapshot,
        max_staleness_secs=args.max_staleness_secs,
    )
    market_report_output = Path(args.market_brief_output)
    okx_market_brief.write_report(market_report, market_report_output)

    account_args = argparse.Namespace(
        profile=args.profile,
        demo=args.demo,
        live=args.live,
        env_file=args.env_file,
        cli_cmd=args.cli_cmd,
        inst_ids=args.inst_ids,
        output=args.account_snapshot_output,
        pretty=args.pretty_snapshot,
        verbose_cli=args.verbose_cli,
    )
    account_snapshot = okx_account_snapshot.build_snapshot(account_args)
    account_snapshot_output = Path(args.account_snapshot_output)
    okx_account_snapshot.write_snapshot(
        account_snapshot,
        output_path=account_snapshot_output,
        pretty=args.pretty_snapshot,
    )
    account_report = okx_account_brief.render_report(
        account_snapshot,
        max_staleness_secs=args.max_staleness_secs,
    )
    account_report_output = Path(args.account_brief_output)
    okx_account_brief.write_report(account_report, account_report_output)

    summary = render_summary(
        market_snapshot=market_snapshot,
        account_snapshot=account_snapshot,
        market_report_path=market_report_output,
        account_report_path=account_report_output,
    )
    summary_output = Path(args.summary_output)
    write_text(summary_output, summary)

    print(f"已写入行情快照: {market_snapshot_output}")
    print(f"已写入行情摘要: {market_report_output}")
    print(f"已写入账户快照: {account_snapshot_output}")
    print(f"已写入账户摘要: {account_report_output}")
    print(f"已写入 demo 测试总结: {summary_output}")
    print(
        "测试结果: "
        f"market_errors={len(market_snapshot.get('errors', []))} "
        f"account_errors={len(account_snapshot.get('errors', []))}"
    )

    if args.print_summary:
        print("")
        print(summary)

    if args.send_cc_connect:
        send_via_cc_connect(
            report=summary,
            attachments=[summary_output, market_report_output, account_report_output],
            cc_project=args.cc_project,
            cc_session=args.cc_session,
            send_file=args.send_file,
        )
        print("已通过 cc-connect send 发回会话。")

    return 0 if not market_snapshot.get("errors") and not account_snapshot.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
