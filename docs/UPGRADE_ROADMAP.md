# 后续升级优化方向

## 近端升级

- 体育从足球赛前扩到 NFL/NBA 赛中
- 加密从单一 strike 扩到完整 volatility surface
- 天气从温度阈值扩到降水、降雪和热带气旋
- 建立 replay 数据集和基线指标

## 中期升级

- 多策略组合分配器
- 策略级别的动态资金权重
- 更细粒度的库存风险控制
- 板块级熔断和自动降级
- 参数寻优和 walk-forward 验证

## 长期升级

- 新增 politics/entertainment 类别
- 跨市场相关性建模
- 统一特征仓和离线训练流水线
- 自动化实验追踪与版本回滚
- 真实部署环境的高可用编排

## 升级顺序建议

1. 先补 research 和 replay
2. 再补 paper execution
3. 再补 shadow
4. 最后才做 live 扩容

