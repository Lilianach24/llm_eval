# LLM测试项目面试材料（可直接讲解）

## 1) 一页架构图（输入→评测→回归→门禁→报告→整改）

```text
[测试集 tests/writing_cases.jsonl]
            |
            v
[app.py eval] -------------------------------> reports/latest_report.json
            |
            v
[run_regression.py]
  |- 分层统计(by_difficulty/by_tag) ---------> reports/regression_summary.json
  |- 失败样本导出 ---------------------------> reports/failed_cases.json
            |
            v
[gate_regression.py]
  |- 与 baseline 对比
  |- min_pass_rate / max_regression 门禁
  `- 通过/失败（CI可直接阻断）
            |
            v
[v2_eval.py]
  |- 并发评测 --workers
  |- 多模型交叉验证 --models
  |- 指标: accuracy/compliance_rate/ece/disagreement
  `-> reports/v2_eval_report.json
            |
            v
[fact_check.py] -----------------------------> reports/fact_check_report.json
            |
            v
[scripts/build_quality_dashboard.py] --------> reports/dashboard_snapshot.json
            |
            v
[周会复盘/缺陷分级/修复回归]
```

**你在面试里可用的一句话：**
> 我把“单次评测脚本”工程化成“可回归、可门禁、可定位、可汇报”的质量流水线。

---

## 2) 一页指标定义表（口径+解释+注意事项）

| 指标 | 计算方式（当前项目） | 代表含义 | 注意事项 |
|---|---|---|---|
| pass_rate | passed/total（样本级） | 总体通过水平 | 强依赖用例设计质量 |
| accuracy | V2中同 pass_rate 口径 | 模型在当前规则下的正确率 | 当前与 pass_rate 等价 |
| compliance_rate | includes_ok & length_ok 的比例 | 格式/约束合规程度 | 不是安全合规的完整定义 |
| avg_latency_ms | 每请求平均耗时 | 体验速度 | 受网络和平台负载影响 |
| p95_latency_ms | 延迟95分位 | 高延迟尾部风险 | 样本太少时波动大 |
| ece（近似） | 基于 confidence_proxy 分桶误差 | 置信-正确率校准差异 | 当前为代理实现（ECE-like） |
| cross_model_disagreement | 多模型在同case上 passed 是否不一致 | 模型间稳定性/分歧度 | 一致不代表都正确 |
| hallucination_risk_rate | 规则词信号命中率 | 幻觉风险预警 | 属于规则信号，不是事实裁决 |

**你在面试里可用的一句话：**
> 我把指标分成“结果质量、约束合规、时延稳定、跨模型一致性、风险信号”五类，避免只看单一通过率。

---

## 3) 一页真实问题案例（门禁拦截→定位→修复→回归）

### 案例标题
**“约束类样本通过率下滑被门禁拦截”**

### 背景
- 变更：提示词模板从“先结论后细节”改成“自由生成风格”。
- 期望：可读性提升。
- 风险：格式约束可能下降。

### 现象
- `gate_regression.py` 报门禁失败（`pass_rate` 低于阈值 / 相对基线退化超阈值）。
- `run_regression.py` 导出 `failed_cases.json`，集中在 `constraint-following` 和 `structure` 标签。

### 定位
1. 打开 `reports/failed_cases.json`，按 `tags` 聚合失败占比。
2. 发现大量失败为 `includes_ok=False`，而 `length_ok=True`。
3. 结论：主要是格式关键字/结构约束丢失，不是长度问题。

### 修复
- 在 system prompt 增加强约束模板：必须出现编号要点（1./2.）与关键词。
- 对高风险标签单独增加 few-shot 模板。

### 回归验证
- 重新跑：
  - `python run_regression.py --provider openai --model <model>`
  - `python gate_regression.py --provider openai --model <model>`
- 结果：门禁通过，`constraint-following` 分层恢复到基线以上。

### 复盘沉淀
- 新增2条“结构约束”对抗样本到测试集，防止同类问题复发。
- 将该问题标记为“P1：核心输出格式退化”。

**你在面试里可用的一句话：**
> 我不只给出分数，还给出可执行的定位路径和修复闭环，确保每次改动都能追溯质量影响。

---

## 附：30秒电梯陈述

> 我做了一个 LLM 写作助手测试框架：先构建分层测试集；再做自动化回归和门禁拦截；再做并发、多模型交叉验证与 ECE-like 校准分析；最后加真实性风险信号和看板快照。核心价值是把“可跑脚本”升级为“可持续质量保障流程”。
