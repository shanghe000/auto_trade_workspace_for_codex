#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import okx_account_brief
import okx_account_snapshot


DEFAULT_SNAPSHOT_OUTPUT = "state/snapshots/okx_account_snapshot.latest.json"
DEFAULT_BRIEF_OUTPUT = "state/reports/okx_account_brief.latest.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="一键刷新 OKX 账户只读快照并生成中文摘要。"
    )
    parser.add_argument("--profile", default="demo")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--env-file", default="config/okx.env")
    parser.add_argument("--cli-cmd", default="npx okx-trade-cli")
    parser.add_argument("--inst-id", dest="inst_ids", action="append")
    parser.add_argument("--snapshot-output", default=DEFAULT_SNAPSHOT_OUTPUT)
    parser.add_argument("--brief-output", default=DEFAULT_BRIEF_OUTPUT)
    parser.add_argument("--pretty-snapshot", action="store_true")
    parser.add_argument("--max-staleness-secs", type=int, default=120)
    parser.add_argument("--print-brief", action="store_true")
    parser.add_argument("--send-cc-connect", action="store_true")
    parser.add_argument("--cc-project", default="")
    parser.add_argument("--cc-session", default="")
    parser.add_argument("--send-file", action="store_true")
    parser.add_argument("--verbose-cli", action="store_true")
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


def main() -> int:
    args = parse_args()

    snapshot_args = argparse.Namespace(
        profile=args.profile,
        demo=args.demo,
        live=args.live,
        env_file=args.env_file,
        cli_cmd=args.cli_cmd,
        inst_ids=args.inst_ids,
        output=args.snapshot_output,
        pretty=args.pretty_snapshot,
        verbose_cli=args.verbose_cli,
    )
    snapshot = okx_account_snapshot.build_snapshot(snapshot_args)
    snapshot_output = Path(args.snapshot_output)
    okx_account_snapshot.write_snapshot(snapshot, snapshot_output, args.pretty_snapshot)

    brief_output = Path(args.brief_output)
    report = okx_account_brief.render_report(
        snapshot,
        max_staleness_secs=args.max_staleness_secs,
    )
    okx_account_brief.write_report(report, brief_output)

    print(f"已写入账户快照: {snapshot_output}")
    print(f"已写入账户摘要: {brief_output}")
    print(
        "抓取结果: "
        f"normalized_keys={len(snapshot.get('normalized', {}))} "
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
