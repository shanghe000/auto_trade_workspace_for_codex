# 飞书报表模板

## 短状态更新

```text
Status: <HOLD | RiskBlocked | OrderSubmitted | Filled | Error>
Symbol: <symbol or n/a>
View: <one-line market view>
Risk: <one-line risk state>
Action: <what was done or why nothing was done>
Next: <next watch item>
```

## 日终摘要

```text
Date: <YYYY-MM-DD>
Net PnL: <value>
Trades: <count>
Best Idea: <one-line summary>
Worst Mistake: <one-line summary>
Open Risk: <summary>
Incidents: <summary or none>
Next Session Focus: <summary>
Artifacts: <file or chart names if attached>
```

## 附件规则

只有在附件能帮助回答下面问题时才发送：

- 发生了什么
- 当前还有什么未平风险
- 还剩下哪些风险

不要把没有操作员价值的原始文件堆到聊天里。
