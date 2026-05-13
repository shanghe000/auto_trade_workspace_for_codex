# V2 实施 Backlog

## 当前状态评估（2026-04-06）

### 已有资产
- ✅ **数据采集**：`tools/okx_market_snapshot.py`、`tools/okx_account_snapshot.py`
- ✅ **基础处理**：`tools/okx_market_brief.py`、`tools/okx_account_brief.py`
- ✅ **架构文档**：`docs/architecture.md` 定义了清晰的层次边界
- ✅ **角色定义**：`AGENTS.md` 明确了主agent职责与限制
- ✅ **可观测基础**：`state/` 目录结构（snapshots, journals, reports）
- ✅ **配置模板**：`config/` 包含风险、策略注册表样例

### 关键缺口
- ❌ **无Python工程结构**：缺少 `pyproject.toml`、`src/`、规范测试
- ❌ **脚本态实现**：所有功能都在 `tools/` 脚本中，无法复用
- ❌ **无统一数据契约**：各脚本使用自由格式JSON，没有 `MarketSnapshot`、`AccountSnapshot` 等类型
- ❌ **分析能力碎片化**：依赖Claude通用推理，没有可复用的技术分析库
- ❌ **无运行时组件**：`risk_engine`、`execution_gateway`、`order_event_watcher` 仅有概念

## 实施原则

### 1. 渐进式重构
- V1脚本保持不动，继续服务现有cc-connect项目
- V2新建工程结构，逐步迁移能力
- 关键路径：先做本地CLI验证，再做远程集成

### 2. 契约驱动
- 先定义核心数据类型的Python类
- 所有模块围绕这些契约实现
- 输入输出必须类型化

### 3. 测试先行
- 使用现有 `state/` 真实数据作为测试夹具
- 每个模块必须有单元测试
- 核心算法必须有验证用例

### 4. 运行时与分析解耦
- 分析引擎是纯函数库，不处理连接、重试、事件监听
- 运行时组件（连接管理、事件循环）单独设计
- 避免分析逻辑被IO、网络、状态管理污染

## Backlog 结构

### 必做（P0）— 工程化底座
**目标**：建立可维护的Python包结构，为后续所有工作提供基础

#### P0.1：创建Python工程骨架
```
├── pyproject.toml          # 项目配置、依赖、构建
├── src/
│   └── auto_trade/        # 主包
│       ├── __init__.py
│       └── _version.py
├── tests/
│   ├── __init__.py
│   ├── fixtures/          # 测试数据
│   │   ├── market_snapshot_btc_20260405.json
│   │   ├── account_snapshot_demo_20260405.json
│   │   └── README.md
│   └── unit/
│       └── test_data_types.py
└── scripts/               # 包装现有tools
    ├── okx_market_snapshot.py
    └── okx_account_snapshot.py
```

**具体任务**：
1. 创建 `pyproject.toml`（poetry或setuptools）
2. 创建 `src/auto_trade/` 包结构
3. 复制 `state/` 最新快照到 `tests/fixtures/`
4. 创建基础测试验证导入和类型

#### P0.2：定义核心数据类型
```
src/auto_trade/types/
├── __init__.py
├── market.py          # MarketSnapshot, Ticker, OrderBook, Candle
├── account.py         # AccountSnapshot, Position, Order, Balance
├── analysis.py        # AnalysisResult, TechnicalIndicators, MarketRegime
├── trading.py         # TradeIntent, RiskDecision, ExecutionPlan
└── events.py          # OrderEvent, PositionEvent, AccountEvent
```

**契约示例**：
```python
# src/auto_trade/types/market.py
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

@dataclass
class Ticker:
    inst_id: str
    last: Optional[Decimal]
    bid_px: Optional[Decimal]
    ask_px: Optional[Decimal]
    open_24h: Optional[Decimal]
    high_24h: Optional[Decimal]
    low_24h: Optional[Decimal]
    vol_ccy_24h: Optional[Decimal]
    ts: datetime

@dataclass
class Candle:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[Decimal]
    confirm: bool  # 是否已收线

@dataclass
class MarketSnapshot:
    """统一的市场快照类型"""
    snapshot_type: str = "market"
    captured_at: datetime
    instruments: List[str]  # 如 ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]
    tickers: Dict[str, Ticker]
    candles: Dict[str, List[Candle]]  # inst_id -> 对应K线
    order_books: Dict[str, Dict]  # 简化表示
    funding_rates: Dict[str, Decimal]
    open_interests: Dict[str, Decimal]

    @classmethod
    def from_okx_json(cls, data: Dict) -> "MarketSnapshot":
        """从现有JSON格式解析"""
        # 实现转换逻辑
```

#### P0.3：创建数据适配层
```
src/auto_trade/data/
├── __init__.py
├── okx/
│   ├── __init__.py
│   ├── public_client.py    # 行情API客户端
│   └── private_client.py   # 账户API客户端（只读）
├── adapters.py             # JSON -> 类型转换
└── snapshot_manager.py     # 快照读写、缓存、时效检查
```

**目标**：将 `tools/okx_market_snapshot.py` 的核心逻辑移到 `public_client.py`，脚本只保留CLI包装。

### 应做（P1）— 数据层重构
**目标**：将现有脚本能力迁移到可复用库，保持向后兼容

#### P1.1：重构行情采集
1. 提取 `OkxPublicClient` 到 `src/auto_trade/data/okx/public_client.py`
2. 保持原有脚本接口不变，内部调用新客户端
3. 添加 `MarketSnapshot` 序列化/反序列化
4. 添加数据新鲜度检查逻辑

#### P1.2：重构账户采集
1. 提取账户读取逻辑到 `private_client.py`
2. 定义 `AccountSnapshot` 类型
3. 实现 `okx_account_snapshot.py` 到新库的迁移

#### P1.3：创建状态管理
```
src/auto_trade/state/
├── __init__.py
├── snapshot_store.py      # 快照读写、版本管理
├── journal_writer.py      # 交易日志记录
├── event_log.py           # 事件流记录
└── report_generator.py    # 报告生成（Markdown格式）
```

**目标**：统一 `state/` 目录的读写操作，提供类型安全接口。

#### P1.4：创建CLI包装层
```
scripts/
├── okx_market_snapshot.py    # 调用 src.auto_trade.data.okx.public_client
├── okx_account_snapshot.py
├── okx_market_brief.py       # 调用 src.auto_trade.state.report_generator
└── okx_account_brief.py
```

**原则**：脚本文件应 <100行，只做参数解析和简单调用。

### 必做（P2）— 最小分析引擎
**目标**：实现15m-4H波段交易所需的核心技术分析能力

#### P2.1：技术分析基础库
```
src/auto_trade/analysis/
├── __init__.py
├── technical/
│   ├── __init__.py
│   ├── indicators.py        # RSI, MACD, 布林带, ATR
│   ├── trend.py             # 移动平均线, 趋势方向
│   ├── volatility.py        # 波动率计算, 市场regime判断
│   └── structure.py         # 支撑阻力识别
├── flow/                    # 暂留空位
└── core.py                  # 分析编排入口
```

**核心指标**（按优先级）：
1. **EMA**：9, 21, 50, 200周期（多时间框架）
2. **RSI**：14周期，超买超卖区域
3. **ATR**：真实波幅，用于止损和波动评估
4. **布林带**：20周期，2倍标准差
5. **MACD**：12/26/9 基础配置

#### P2.2：市场结构分析
```python
# src/auto_trade/analysis/technical/structure.py
def find_support_resistance(
    candles: List[Candle],
    window: int = 20,
    threshold_pct: float = 1.0
) -> List[SupportResistanceLevel]:
    """
    识别支撑阻力位

    算法：
    1. 寻找局部高点和低点
    2. 过滤幅度（最小波动要求）
    3. 合并相近价位
    4. 计算强度（触碰次数、成交量）
    """
```

#### P2.3：分析结果类型
```python
# src/auto_trade/types/analysis.py
@dataclass
class TechnicalAnalysis:
    trend: TrendDirection  # UPTREND, DOWNTREND, RANGE
    trend_strength: float  # 0-1
    key_levels: List[Level]
    indicators: Dict[str, IndicatorValue]
    volatility_regime: VolatilityRegime  # LOW, MEDIUM, HIGH, EXPANDING

@dataclass
class AnalysisResult:
    instrument: str
    timeframe: str
    captured_at: datetime
    technical: TechnicalAnalysis
    flow: Optional[FlowAnalysis] = None
    composite_score: Optional[CompositeScore] = None
    trade_context: Optional[TradeContext] = None
```

#### P2.4：分析编排器（最小版本）
```python
# src/auto_trade/analysis/core.py
class AnalysisOrchestrator:
    """协调各类分析，生成统一结果"""

    def analyze_market(
        self,
        snapshot: MarketSnapshot,
        instrument: str,
        timeframes: List[str] = ["15m", "1H", "4H"]
    ) -> AnalysisResult:
        # 1. 提取该品种数据
        # 2. 多时间框架技术分析
        # 3. 综合评分
        # 4. 生成交易上下文
```

### 应做（P3）— 分析编排与主agent升级
**目标**：让主agent能够使用结构化分析结果

#### P3.1：分析技能封装
```
skills/enhanced-analysis/
├── SKILL.md
├── prompt.txt            # Claude调用提示词
└── references/
    └── data_schema.md    # 输入输出格式说明
```

**SKILL.md重点**：
- 输入：市场快照路径、分析配置
- 输出：结构化 `AnalysisResult` JSON + 自然语言解读
- 与现有 `trading-orchestrator` 技能协作

#### P3.2：主agent工作流更新
更新 `skills/trading-orchestrator/references/decision-flow.md`：

```markdown
## V2 决策流程

1. **数据准备**
   - 调用 `enhanced-analysis` 获取结构化分析
   - 读取账户快照
   - 读取当前armed策略

2. **策略匹配**
   - 检查当前市场状态是否符合策略触发条件
   - 使用分析结果中的量化指标进行匹配

3. **意图生成**
   - 基于分析结果生成 `TradeIntent`
   - 包含具体入场价、止损价、目标价、仓位大小

4. **风险审查**（V2仍为dry-run）
   - 检查是否符合风险限制
   - 输出 `RiskDecision`

5. **计划输出**
   - 生成交易计划文档
   - 记录到journal
```

#### P3.3：测试集成
创建 `tests/integration/test_analysis_integration.py`：
- 测试从快照到分析结果的完整流程
- 测试分析结果到交易意图的转换
- 验证与现有journal格式的兼容性

### 暂缓（P4）— 永续特有分析
**目标**：增强对永续合约特有指标的分析

#### P4.1：资金流分析库
```
src/auto_trade/analysis/flow/
├── __init__.py
├── oi_analysis.py       # 持仓量分析
├── funding_analysis.py  # 资金费率分析
├── liquidation.py       # 清算热图分析
└── sentiment.py         # 市场情绪综合
```

#### P4.2：核心指标
1. **OI-价格相关性**：背离检测
2. **资金费率分析**：套利机会、极端费率预警
3. **多空比分析**：大户 vs 散户行为
4. **成交量分析**：放量/缩量模式识别

#### P4.3：FlowAnalysis类型
```python
@dataclass
class FlowAnalysis:
    oi_trend: OITrend  # INCREASING, DECREASING, STABLE
    oi_price_correlation: float  # -1 到 1
    funding_signal: FundingSignal  # NEUTRAL, LONG_FUNDING, SHORT_FUNDING
    long_short_ratio: Optional[Decimal]
    volume_profile: VolumeProfile
```

### 暂缓（P5）— 策略信号化
**目标**：将策略注册表从描述性配置升级为可执行信号定义

#### P5.1：策略类型增强
```python
# src/auto_trade/strategy/
├── __init__.py
├── types.py              # StrategyDefinition, SignalCondition
├── parser.py             # 解析YAML为可执行条件
├── matcher.py            # 匹配市场状态与策略条件
└── registry.py           # 策略加载与管理
```

#### P5.2：信号条件语言
```yaml
# config/strategy-registry.v2.yaml
strategies:
  - id: eth_15m_ema_cross_v1
    signals:
      entry_long:
        conditions:
          - type: "INDICATOR"
            indicator: "EMA_CROSS"
            params: {fast: 9, slow: 21}
            operator: "FAST_ABOVE_SLOW"
          - type: "PRICE_LEVEL"
            level_type: "SUPPORT"
            distance_pct: 1.0
            operator: "WITHIN"
      exit_long:
        conditions:
          - type: "STOP_LOSS"
            based_on: "ATR"
            multiplier: 2.0
```

#### P5.3：策略匹配引擎
```python
def match_strategy(
    strategy: StrategyDefinition,
    analysis: AnalysisResult,
    account: AccountSnapshot
) -> Optional[TradeIntent]:
    """检查当前市场是否满足策略条件"""
```

### 后置（P6）— 回测框架
**目标**：在信号定义稳定后，增加历史验证能力

#### P6.1：轻量回测引擎
```
src/auto_trade/backtest/
├── __init__.py
├── engine.py            # 回放历史数据
├── performance.py       # 计算绩效指标
└── visualizer.py        # 生成图表
```

#### P6.2：回测数据源
- 使用 `state/snapshots/` 历史数据
- 支持多时间框架回放
- 模拟滑点、手续费

#### P6.3：绩效指标
- 总收益率、年化收益率
- 夏普比率、最大回撤
- 胜率、盈亏比、Profit Factor

## 实施路线图

### 阶段一：工程化准备（1-2周）
**目标**：建立可测试、可维护的代码库

1. ✅ **P0.1**：创建Python工程骨架（2天）
2. ✅ **P0.2**：定义核心数据类型（3天）
3. ✅ **P0.3**：创建数据适配层框架（2天）
4. ✅ **测试基建**：设置pytest、mypy、CI配置（1天）

### 阶段二：数据层迁移（2-3周）
**目标**：将现有脚本重构为可复用库

1. ✅ **P1.1**：重构行情采集（3天）
2. ✅ **P1.2**：重构账户采集（3天）
3. ✅ **P1.3**：状态管理库（3天）
4. ✅ **P1.4**：CLI包装层（2天）
5. ✅ **集成测试**：确保V1脚本功能不变（2天）

### 阶段三：分析引擎V1（3-4周）
**目标**：交付可用的技术分析能力

1. ✅ **P2.1**：技术指标库（5天）
2. ✅ **P2.2**：市场结构分析（4天）
3. ✅ **P2.3**：分析结果类型（2天）
4. ✅ **P2.4**：分析编排器（3天）
5. ✅ **端到端测试**：从快照到分析结果（2天）

### 阶段四：主agent集成（2-3周）
**目标**：让Claude能够使用结构化分析

1. ✅ **P3.1**：分析技能封装（3天）
2. ✅ **P3.2**：更新决策流程（2天）
3. ✅ **P3.3**：集成测试（3天）
4. ✅ **用户验收**：人工验证分析质量（2天）

### 阶段五：增强分析（3-4周）
**目标**：添加永续合约特有分析

1. ⏳ **P4.1**：资金流分析库（5天）
2. ⏳ **P4.2**：核心指标实现（4天）
3. ⏳ **P4.3**：FlowAnalysis集成（3天）

### 阶段六：策略系统（4-5周）
**目标**：实现可执行的策略信号

1. ⏳ **P5.1**：策略类型增强（4天）
2. ⏳ **P5.2**：信号条件语言（5天）
3. ⏳ **P5.3**：策略匹配引擎（4天）

### 阶段七：验证框架（3-4周）
**目标**：添加回测和历史验证

1. ⏳ **P6.1**：回测引擎（5天）
2. ⏳ **P6.2**：数据源适配（3天）
3. ⏳ **P6.3**：绩效分析（3天）

## 风险与缓解

### 技术风险
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 数据类型设计不当 | 后续重构成本高 | P0阶段充分review，使用dataclass+frozen |
| 性能问题 | 分析耗时过长 | 限制历史数据长度，添加缓存，性能测试 |
| 与V1不兼容 | 现有工作流中断 | 保持CLI接口不变，双版本并行运行 |

### 项目风险
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 范围蔓延 | 无法按时交付核心功能 | 严格执行优先级，P0-P3完成后才考虑P4+ |
| 技能集成复杂 | Claude无法正确使用新接口 | 早期人工测试，优化prompt设计 |
| 测试数据不足 | 算法验证不充分 | 使用现有state/数据，补充边缘案例 |

### 运营风险
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 过度依赖分析 | 忽视人工判断 | 明确分析结果为"参考"，非自动执行 |
| 误读指标 | 交易决策错误 | 提供指标解释文档，添加置信度评分 |
| 生产切换风险 | 影响现有交易 | V2单独环境测试，手动切换 |

## 成功标准

### 技术标准
- ✅ 所有核心类型有类型提示（mypy通过）
- ✅ 单元测试覆盖率 > 80%
- ✅ 从快照到分析结果端到端测试通过
- ✅ 分析性能：单品种完整分析 < 5秒
- ✅ 零破坏性变更：现有脚本功能完全保持

### 功能标准
- ✅ 支持15m/1H/4H时间框架分析
- ✅ 提供EMA、RSI、ATR、布林带核心指标
- ✅ 自动识别支撑阻力位
- ✅ 输出结构化分析结果（JSON）
- ✅ Claude能够理解并使用分析结果

### 运营标准
- ✅ 分析结果可解释（有自然语言摘要）
- ✅ 与现有journal格式兼容
- ✅ 配置与代码分离
- ✅ 有完整的操作文档

## 验收清单

### Phase 0-2 验收（工程化+数据层）
- [ ] `pyproject.toml` 存在且配置正确
- [ ] `src/auto_trade/types/` 包含所有核心类型
- [ ] `tests/fixtures/` 包含真实测试数据
- [ ] 现有CLI脚本功能不变（对比测试）
- [ ] 数据客户端有完整测试
- [ ] 状态管理库读写正常

### Phase 3 验收（分析引擎）
- [ ] 技术指标计算正确（对比已知工具验证）
- [ ] 支撑阻力识别算法合理
- [ ] `AnalysisResult` 类型完整
- [ ] 分析编排器可输出结构化结果
- [ ] 端到端测试：快照 → 分析 → 报告

### Phase 4 验收（集成）
- [ ] `enhanced-analysis` 技能可用
- [ ] Claude能够调用并理解分析结果
- [ ] 更新后的决策流程文档
- [ ] 集成测试通过

## 交付物

### 代码交付
1. `src/auto_trade/` Python包
2. 更新后的 `scripts/` CLI包装
3. 完整测试套件
4. 类型定义文件（.pyi）

### 文档交付
1. API参考文档（自动生成）
2. 架构更新说明
3. 用户操作指南
4. 开发人员指南

### 配置交付
1. 更新的策略注册表模板
2. 分析配置示例
3. 测试配置

## 下一步行动

### 立即开始（本周）
1. 创建 `pyproject.toml`
2. 建立 `src/auto_trade/types/` 基础类型
3. 复制测试夹具数据
4. 验证现有脚本在新结构下可运行

### 短期计划（1-2周）
1. 实现 `OkxPublicClient` 库版本
2. 创建 `MarketSnapshot` 转换逻辑
3. 保持CLI脚本兼容性
4. 添加基础测试

### 中期计划（3-4周）
1. 实现技术指标库
2. 创建分析编排器原型
3. 测试端到端流程

## 附录

### A. 技术栈决策
- **构建工具**：setuptools（更简单，兼容性好）
- **测试框架**：pytest + pytest-cov
- **类型检查**：mypy
- **代码格式化**：black + isort
- **文档生成**：pdoc3 或 Sphinx
- **CI/CD**：GitHub Actions（如使用）

### B. 目录结构最终目标
```
auto_trade_workspace_for_codex/
├── pyproject.toml
├── README.md
├── docs/
│   ├── v2-implementation-backlog.md
│   └── architecture.md
├── src/
│   └── auto_trade/
│       ├── types/          # 核心数据类型
│       ├── data/           # 数据采集与适配
│       ├── analysis/       # 分析引擎
│       ├── strategy/       # 策略系统
│       ├── backtest/       # 回测框架
│       ├── state/          # 状态管理
│       └── risk/           # 风控引擎（预留）
├── tests/
│   ├── fixtures/          # 测试数据
│   ├── unit/             # 单元测试
│   └── integration/      # 集成测试
├── scripts/              # CLI包装（调用src）
├── config/              # 配置文件模板
├── skills/              # Claude技能定义
└── state/               # 运行时数据（V1继续使用）
```

### C. 依赖管理
```toml
# pyproject.toml 依赖示例
[project]
dependencies = [
    "requests>=2.28.0",
    "pandas>=1.5.0",      # 数据分析
    "numpy>=1.24.0",      # 数值计算
    "pydantic>=2.0.0",    # 数据验证（可选）
    "python-dateutil>=2.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "mypy>=1.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
]
```

---

**文档版本**：1.0
**创建日期**：2026-04-06
**预计总工时**：25-35人日（Phase 0-4）
**优先级**：P0 > P1 > P2 > P3 > P4 > P5 > P6

**关键约束**：
1. 保持V1脚本100%兼容
2. 分析结果必须结构化+可解释
3. 所有代码必须有类型提示和测试
4. 先本地验证，再远程集成