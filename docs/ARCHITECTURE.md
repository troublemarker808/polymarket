# 架构说明

## 1. 分层

### Core

`core` 只放共享类型、协议、枚举和配置模型。这里不放任何交易所逻辑和策略逻辑。

### Adapters

`adapters` 负责接入 Polymarket 和外部数据源，并把原始数据翻译为统一格式。

### Strategies

`strategies` 只负责定价和信号生成。按 `category/strategy` 两级目录拆分，保证每个
策略是一个可替换的独立单元。

### Execution

`execution` 把信号变成订单意图，处理报价、库存、成交和撤单节奏。

### Risk

`risk` 独立判断仓位、限额、陈旧数据、板块暴露和熔断。

### Registry

`registry` 负责把配置里的 strategy id 映射成具体策略实例，避免 orchestrator
直接依赖具体类别实现。

### Research

`research` 负责 replay、backtest、metrics，不能直接依赖 live execution。

### Orchestrator

`orchestrator` 只做模块编排，不能包含任何类别特定策略公式。

### Storage

`storage` 负责事件记录与回放原始材料，不放策略判断。

## 2. 边界规则

- `strategies/sports/*` 不能 import `strategies/crypto/*`
- `strategies/crypto/*` 不能 import `strategies/weather/*`
- `strategies/weather/*` 不能 import `strategies/sports/*`
- `strategies/*` 不能直接 import `adapters/polymarket/*`
- `execution/*` 不能写死任何类别判断逻辑
- `risk/*` 不能内嵌类别策略参数，类别差异通过配置注入

## 3. 数据流

1. adapter 拉取市场与外部数据
2. discovery adapter 输出基础市场对象
3. CLOB enrichment 覆盖实时盘口字段
4. orchestrator 把快照送给启用中的策略
5. strategy 输出标准化 signal
6. risk 审核 signal 和 order intent
7. execution 生成订单并回传状态
8. research 记录所有输入输出用于 replay

## 4. 为什么这样拆

- 改体育模型时，不应影响加密和天气的导入图。
- 调整下单逻辑时，不应重写任何预测公式。
- 更换 Polymarket adapter 时，不应迫使策略代码大改。
- 新增第四个板块时，只需新增一个 category package 和配置，不需重构主干。
