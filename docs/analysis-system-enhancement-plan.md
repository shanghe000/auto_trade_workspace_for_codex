# 交易分析系统增强计划

## 概述

本文档旨在系统性地增强当前交易分析系统的量化分析能力，填补"架构完整但分析单薄"的缺口。目标是构建一套专业级的分析工具集，支持 `15m-4H` 级别的日内/波段交易决策。

## 核心目标

1. **从通用AI分析转向系统化量化分析**
2. **实现专用分析agent的Python模块化实现**
3. **集成技术指标与统计模型**
4. **建立轻量级回测与策略验证框架**
5. **增强风险计算的量化基础**

## 当前状态分析

### 已有优势
- ✅ 分层架构清晰（控制面/数据面/认知面）
- ✅ 数据采集链路完整（OKX行情+账户）
- ✅ 安全框架与风控闸门
- ✅ 可观测性基础设施（快照/日志/事件）

### 主要短板
- ❌ 分析agent仅有概念，无具体实现
- ❌ 无技术指标库（RSI、MACD、布林带等）
- ❌ 无统计分析模型（波动率、相关性）
- ❌ 无回测验证机制
- ❌ 策略信号缺乏量化定义

## 改进架构设计

### 总体架构更新
```
现有架构：
主agent → 通用AI分析 → 风险层 → 执行层

目标架构：
主agent → [专用分析工具集] → 结构化结论 → 风险层 → 执行层
                     │
                     ├── 市场结构分析 (technical_analysis/)
                     ├── 资金流分析 (flow_analysis/)
                     ├── 策略研究 (strategy_research/)
                     └── 回测验证 (backtest/)
```

### 分析工具集设计原则
1. **Python模块化**：每个分析领域为独立Python包
2. **接口标准化**：统一输入（快照数据）、输出（结构化结论）
3. **可组合性**：分析模块可单独使用或组合使用
4. **可测试性**：每个模块包含单元测试和样本数据测试

## 分阶段实施计划

### Phase 1：技术指标库与基础分析（预计2-3天）
**目标**：建立核心技术指标计算能力

#### 任务1.1：创建 `technical_analysis` 包
```
technical_analysis/
├── __init__.py
├── core/
│   ├── indicators.py      # 基础指标计算
│   ├── pattern_detection.py # 形态识别
│   └── trend.py           # 趋势分析
├── utils/
│   ├── data_processor.py  # 数据预处理
│   └── validation.py      # 数据验证
└── tests/
    └── test_indicators.py
```

**核心指标实现**：
```python
# technical_analysis/core/indicators.py
class TechnicalIndicators:
    """技术指标计算器"""

    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> List[Optional[float]]:
        """相对强弱指数"""
        # 实现逻辑...

    @staticmethod
    def macd(prices: List[float],
             fast_period: int = 12,
             slow_period: int = 26,
             signal_period: int = 9) -> Dict[str, List[float]]:
        """MACD指标"""
        # 实现逻辑...

    @staticmethod
    def bollinger_bands(prices: List[float],
                        period: int = 20,
                        std_dev: float = 2.0) -> Dict[str, List[float]]:
        """布林带"""
        # 实现逻辑...

    @staticmethod
    def atr(highs: List[float],
            lows: List[float],
            closes: List[float],
            period: int = 14) -> List[float]:
        """平均真实波幅"""
        # 实现逻辑...
```

#### 任务1.2：创建市场结构分析模块
```
technical_analysis/core/structure.py
```

**功能**：
- 支撑阻力自动识别（局部高/低点算法）
- 斐波那契回撤水平计算
- 供需区识别（基于成交量剖面）
- 多 timeframe 结构一致性分析

**接口示例**：
```python
def analyze_market_structure(
    candles: List[Dict],  # 标准化K线数据
    timeframe: str,       # 时间级别
    sensitivity: float = 0.5  # 敏感度参数
) -> Dict:
    """
    分析市场结构

    返回：
    {
        "trend": "uptrend" | "downtrend" | "range",
        "key_levels": [
            {"price": 2100.0, "type": "support", "strength": 0.8},
            {"price": 2150.0, "type": "resistance", "strength": 0.7}
        ],
        "fib_levels": {
            "0.236": 2080.0,
            "0.382": 2060.0,
            "0.5": 2040.0,
            "0.618": 2020.0,
            "0.786": 1990.0
        },
        "volatility_regime": "low" | "medium" | "high"
    }
    """
```

#### 任务1.3：创建分析结果标准化输出
```
technical_analysis/core/report.py
```

**功能**：将分析结果转换为结构化JSON，供主agent使用

#### 验收标准 Phase 1
- [ ] `technical_analysis` 包可通过 `pip install -e .` 安装
- [ ] RSI、MACD、布林带、ATR等指标计算正确
- [ ] 支撑阻力识别算法在历史数据上表现合理
- [ ] 单元测试覆盖率 > 80%
- [ ] 可与现有快照数据集成

### Phase 2：资金流分析与衍生品指标（预计2-3天）
**目标**：增强对永续合约特有指标的分析能力

#### 任务2.1：创建 `flow_analysis` 包
```
flow_analysis/
├── __init__.py
├── core/
│   ├── oi_analysis.py      # 持仓量分析
│   ├── funding_analysis.py # 资金费率分析
│   ├── liquidation.py      # 清算分析
│   └── sentiment.py        # 市场情绪指标
└── tests/
    └── test_flow.py
```

#### 任务2.2：实现核心资金流指标
```python
# flow_analysis/core/oi_analysis.py
class OpenInterestAnalyzer:
    """持仓量分析"""

    @staticmethod
    def oi_price_correlation(oi_data: List[float],
                            price_data: List[float],
                            lookback: int = 20) -> Dict:
        """
        分析OI与价格的相关性

        返回：
        {
            "correlation": 0.65,  # 相关系数
            "trend": "increasing",  # OI趋势
            "divergence": {
                "exists": True,
                "type": "bullish",  # 价格跌/OI涨 或 价格涨/OI跌
                "strength": 0.7
            }
        }
        """

    @staticmethod
    def analyze_oi_structure(oi_levels: List[Dict]) -> Dict:
        """
        分析OI层级结构（大户 vs 散户）
        基于OKX的top trader账户数据
        """

# flow_analysis/core/funding_analysis.py
class FundingAnalyzer:
    """资金费率分析"""

    @staticmethod
    def funding_arbitrage_signal(
        funding_rate: float,
        historical_rates: List[float],
        volatility: float
    ) -> Dict:
        """
        资金费率套利信号检测

        返回：
        {
            "signal": "neutral" | "long_funding" | "short_funding",
            "z_score": 2.1,  # 相对于历史的Z分数
            "expected_return": 0.015,  # 预期收益
            "risk": "low" | "medium" | "high"
        }
        """
```

#### 任务2.3：创建市场情绪综合指标
```python
# flow_analysis/core/sentiment.py
class MarketSentiment:
    """市场情绪综合评分"""

    @staticmethod
    def composite_sentiment(
        funding_rate: float,
        oi_trend: str,
        long_short_ratio: float,
        price_action: str,
        volume_profile: Dict
    ) -> Dict:
        """
        计算综合市场情绪得分（0-100）

        返回：
        {
            "score": 65.5,
            "bias": "bullish" | "bearish" | "neutral",
            "confidence": 0.8,
            "components": {
                "funding": {"score": 70, "weight": 0.2},
                "oi": {"score": 60, "weight": 0.3},
                "ls_ratio": {"score": 55, "weight": 0.25},
                "price": {"score": 75, "weight": 0.25}
            }
        }
        """
```

#### 验收标准 Phase 2
- [ ] `flow_analysis` 包完整实现
- [ ] OI-价格背离检测算法有效
- [ ] 资金费率套利信号逻辑合理
- [ ] 市场情绪评分系统可输出结构化结果
- [ ] 与现有OKX数据格式兼容

### Phase 3：策略研究与回测框架（预计3-4天）
**目标**：建立策略开发、验证与优化的完整工作流

#### 任务3.1：创建 `strategy_research` 包
```
strategy_research/
├── __init__.py
├── core/
│   ├── signal_generation.py  # 信号生成
│   ├── strategy_template.py  # 策略模板
│   └── optimization.py       # 参数优化
├── backtest/
│   ├── engine.py            # 回测引擎
│   ├── performance.py       # 绩效统计
│   └── visualizer.py        # 可视化
└── tests/
    └── test_backtest.py
```

#### 任务3.2：实现轻量回测引擎
```python
# strategy_research/backtest/engine.py
class BacktestEngine:
    """轻量回测引擎"""

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []

    def run_strategy(
        self,
        data: pd.DataFrame,           # OHLCV数据
        strategy_func: Callable,      # 策略函数
        strategy_params: Dict,        # 策略参数
        slippage: float = 0.001,      # 滑点
        commission: float = 0.0005    # 手续费
    ) -> Dict:
        """
        运行策略回测

        返回：
        {
            "total_return": 0.15,
            "sharpe_ratio": 1.2,
            "max_drawdown": -0.08,
            "win_rate": 0.55,
            "profit_factor": 1.8,
            "trades": [...],  # 详细交易记录
            "equity_curve": [...]  # 权益曲线
        }
        """
```

#### 任务3.3：创建策略模板系统
```python
# strategy_research/core/strategy_template.py
class StrategyTemplate:
    """策略模板基类"""

    def __init__(self, params: Dict):
        self.params = params
        self.signals = []

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        raise NotImplementedError

    def calculate_position_size(
        self,
        capital: float,
        risk_per_trade: float,
        stop_loss_distance: float
    ) -> float:
        """计算头寸大小（基于风险）"""
        return (capital * risk_per_trade) / stop_loss_distance

# 具体策略实现示例
class TrendFollowingStrategy(StrategyTemplate):
    """趋势跟随策略"""

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        # 使用均线交叉 + ATR止损
        data['ma_fast'] = data['close'].rolling(self.params['ma_fast']).mean()
        data['ma_slow'] = data['close'].rolling(self.params['ma_slow']).mean()
        data['atr'] = TechnicalIndicators.atr(
            data['high'], data['low'], data['close'], self.params['atr_period']
        )

        # 生成信号
        data['signal'] = 0
        data.loc[data['ma_fast'] > data['ma_slow'], 'signal'] = 1
        data.loc[data['ma_fast'] < data['ma_slow'], 'signal'] = -1

        return data
```

#### 任务3.4：增强策略注册表
更新 `config/strategy-registry.example.yaml`，添加量化信号定义：
```yaml
strategies:
  - id: eth_15m_trend_following_v1
    name: ETH 15分钟趋势跟随
    status: draft
    # ... 其他字段

    # 新增：量化信号定义
    signals:
      entry_long:
        conditions:
          - indicator: "MA_CROSS"
            params: {"fast": 9, "slow": 21}
            condition: "FAST_ABOVE_SLOW"
          - indicator: "RSI"
            params: {"period": 14}
            condition: "ABOVE_30"
          - indicator: "VOLUME"
            params: {"ma_period": 20}
            condition: "ABOVE_AVERAGE"
        confirmation:
          require_multiple_timeframes: true
          higher_tf_bias: "bullish"

      exit_long:
        conditions:
          - indicator: "MA_CROSS"
            params: {"fast": 9, "slow": 21}
            condition: "FAST_BELOW_SLOW"
          - indicator: "STOP_LOSS"
            params: {"atr_multiplier": 2}
            condition: "PRICE_BELOW"

    # 新增：回测参数
    backtest_params:
      lookback_days: 90
      initial_capital: 10000
      risk_per_trade: 0.02
      commission: 0.0005
```

#### 验收标准 Phase 3
- [ ] 回测引擎可正确计算绩效指标
- [ ] 策略模板系统可扩展
- [ ] 策略注册表支持量化信号定义
- [ ] 可视化模块可生成基本图表
- [ ] 参数优化功能可用

### Phase 4：系统集成与主agent升级（预计2-3天）
**目标**：将分析工具集集成到现有工作流中

#### 任务4.1：创建分析调度器
```
analysis_orchestrator/
├── __init__.py
├── orchestrator.py      # 分析调度
├── integration.py       # 与现有系统集成
└── skill/              # Claude技能封装
    └── enhanced_analysis.md
```

#### 任务4.2：更新主agent工作流
```python
# analysis_orchestrator/orchestrator.py
class AnalysisOrchestrator:
    """分析调度器"""

    def __init__(self, snapshot_path: str):
        self.snapshot = self.load_snapshot(snapshot_path)
        self.ta = TechnicalAnalysis()
        self.fa = FlowAnalysis()

    def run_full_analysis(self, instrument: str) -> Dict:
        """运行完整分析流程"""

        # 1. 技术分析
        ta_result = self.ta.analyze_all(self.snapshot, instrument)

        # 2. 资金流分析
        fa_result = self.fa.analyze_all(self.snapshot, instrument)

        # 3. 综合评分
        composite = self.composite_scoring(ta_result, fa_result)

        # 4. 生成交易建议
        suggestion = self.generate_trade_suggestion(composite)

        return {
            "technical": ta_result,
            "flow": fa_result,
            "composite": composite,
            "suggestion": suggestion,
            "metadata": {
                "instrument": instrument,
                "timestamp": datetime.now().isoformat(),
                "analysis_version": "1.0"
            }
        }
```

#### 任务4.3：创建增强版分析技能
```
skills/enhanced-analysis/
├── SKILL.md
└── references/
    └── analysis-protocol.md
```

**SKILL.md 内容**：
```markdown
---
name: enhanced-analysis
description: 使用量化分析工具集进行深度市场分析
---

# 增强分析技能

## 输入
- 市场快照路径
- 账户快照路径（可选）
- 分析范围（BTC/ETH）

## 输出
结构化分析报告，包含：
1. 技术分析摘要
2. 资金流分析摘要
3. 市场情绪评分
4. 交易建议（带置信度）
5. 关键风险提示

## 使用示例
```
/analyze eth --depth full
/analyze btc --include-backtest
```
```

#### 任务4.4：更新现有技能
更新 `skills/trading-orchestrator/SKILL.md`，引用新的分析工具：
```markdown
## 增强的分析流程

1. 使用 `enhanced-analysis` 技能进行量化分析
2. 读取已 `armed` 策略的量化信号定义
3. 检查当前市场是否满足策略触发条件
4. 生成带有量化依据的 `TradeIntent`
```

#### 验收标准 Phase 4
- [ ] 分析调度器可协调各分析模块
- [ ] 主agent可调用增强分析工具
- [ ] 输出格式与现有journal系统兼容
- [ ] 新技能可通过Claude技能系统调用
- [ ] 分析性能可接受（单次分析<10秒）

## 实施优先级建议

### 高优先级（立即开始）
1. Phase 1 技术指标库 - 基础中的基础
2. Phase 4 系统集成 - 确保与现有架构兼容

### 中优先级（2周内）
3. Phase 2 资金流分析 - 增强永续合约特有分析
4. Phase 3 回测框架 - 策略验证能力

### 低优先级（1月内）
5. 高级机器学习模型集成
6. 多品种相关性分析
7. 实时监控与预警系统

## 风险与缓解措施

### 技术风险
1. **性能问题**：分析计算耗时过长
   - 缓解：实现结果缓存，限制历史数据长度
   - 监控：添加分析耗时日志

2. **数据质量依赖**：分析结果高度依赖输入数据质量
   - 缓解：增强数据验证和异常处理
   - 监控：记录数据质量问题

3. **集成复杂性**：与现有系统集成可能复杂
   - 缓解：采用渐进式集成，保持向后兼容
   - 测试：充分集成测试

### 操作风险
1. **过度自动化**：可能降低人工判断参与度
   - 缓解：保持 `manual_confirm` 为默认模式
   - 设计：分析结果作为参考，非自动执行

2. **分析结果误读**：复杂指标可能被误解
   - 缓解：提供清晰的指标解释文档
   - 培训：使用者需要理解各指标含义

## 成功指标

### 技术指标
- 分析工具测试覆盖率 > 85%
- 单次完整分析耗时 < 15秒
- 与现有系统零破坏性变更
- 模块化设计，易于扩展

### 业务指标
- 分析深度提升：从定性描述到定量分析
- 策略验证能力：新增回测验证流程
- 决策支持：提供结构化、可解释的分析结果
- 用户接受度：交易员愿意参考分析结果做决策

## 后续演进路线

### 短期（3个月）
- 完善核心分析工具集
- 建立标准分析报告模板
- 集成到日常交易工作流

### 中期（6个月）
- 添加机器学习模型（LSTM预测、异常检测）
- 实现多时间框架协同分析
- 构建策略研究平台

### 长期（12个月）
- 实时智能监控与预警
- 自适应策略优化
- 跨市场套利分析

## 附录

### A. 技术选型建议
1. **数据处理**：pandas + numpy（已隐含在现有代码中）
2. **指标计算**：自实现核心指标，避免TA-Lib安装复杂性
3. **可视化**：matplotlib + seaborn（轻量，无需复杂前端）
4. **缓存**：joblib 或 diskcache
5. **配置管理**：沿用现有yaml/toml

### B. 代码质量标准
1. 类型提示全面（mypy通过）
2. 单元测试覆盖核心逻辑
3. 文档字符串完整
4. 错误处理健全
5. 日志记录详细

### C. 部署与维护
1. 分析工具作为Python包安装
2. 与主仓库版本同步
3. 配置与环境分离
4. 监控与告警集成

---

**文档版本**：1.0
**创建日期**：2026-04-06
**预计完成时间**：10-15人日
**负责人**：[待指定]
**批准人**：[待指定]