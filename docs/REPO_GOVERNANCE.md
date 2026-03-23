# 仓库管理规则

## 1. 分支规则

- 主分支保留为 `main`
- 新功能分支统一使用 `codex/<scope>-<topic>`
- 单个 PR 只改一个模块边界内的事情，避免跨类别大杂烩

## 2. 目录规则

- 外部接口代码只能放在 `adapters/`
- 策略代码只能放在 `strategies/`
- 风控代码只能放在 `risk/`
- 订单执行代码只能放在 `execution/`
- 共享类型只能放在 `core/`

## 3. 配置规则

- 基础开关放 `configs/base.example.toml`
- 每个类别单独一个配置文件
- 不允许把 sports/crypto/weather 的参数塞进同一个巨型文件

## 4. 变更规则

- 新策略必须新增独立目录，不允许把多个策略堆进同一个文件
- 跨模块变更必须先更新文档
- 影响边界的调整要先改 `docs/ARCHITECTURE.md`
- 影响上线流程的调整要先改 `docs/V1_PLAN.md`

## 5. 测试规则

- unit tests 镜像源代码目录组织
- integration tests 只覆盖 adapter、execution、risk 的联动
- 策略变更必须补本类别 replay fixture
- 任何类别都必须可以在不启用其它类别的情况下独立测试

## 6. 运行模式

- `research`
- `paper`
- `shadow`
- `live`

默认模式必须是 `research` 或 `paper`，不得默认 `live`。
