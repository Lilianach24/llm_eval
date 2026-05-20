# llm_eval

针对通用AI大模型开展全方面功能测试与质量验收，重点检测模型回答准确性、稳定性，排查幻觉与逻辑错误等问题。

## 写作助手测试项目（可直接运行）

### 1) 环境

```bash
python --version
```

本项目默认只依赖 Python 标准库，并在仓库内置了 `dotenv.load_dotenv()` 所需的最小实现。

### 2) 快速开始（离线可跑）

#### 启动交互式写作助手

```bash
python app.py chat --provider mock
```

#### 运行批量评测

```bash
python app.py eval --provider mock
```

评测结果会输出到：

- `reports/latest_report.json`

### 3) 接入真实模型（Silicon/OpenAI 兼容）

```bash
export ANTHROPIC_API_KEY="你的Key"
export ANTHROPIC_BASE_URL="https://api.openai-proxy.org/v1"
python app.py --provider openai --model Qwen/Qwen3-8B --max-history-turns 6 chat
python app.py --provider openai --model Qwen/Qwen3-8B eval
```

> Windows PowerShell 不支持 `export`，请使用：
>
> ```powershell
> $env:ANTHROPIC_API_KEY="你的Key"
> $env:ANTHROPIC_BASE_URL="https://api.openai-proxy.org/v1"
> ```

### 4) 测试集格式（JSONL）

默认文件：`tests/writing_cases.jsonl`（当前内置 36 条样本）

每一行示例：

```json
{"case_id":"w001","prompt":"...","must_include":["标题","1.","2.","3."],"max_chars":800}
```

字段说明：

- `case_id`: 用例 ID
- `prompt`: 输入提示词
- `must_include`: 必须包含的关键词
- `max_chars`: 答案最大字符数
- `tags`: 场景标签（如 `rewrite`, `safety`）
- `difficulty`: 难度分层（L1-L4）

### 5) 输出指标

- `pass_rate`: 用例通过率
- `avg_latency_ms`: 平均延迟
- `p95_latency_ms`: P95 延迟


### 6) 上下文记忆（chat 模式）

- chat 模式默认保留最近 `--max-history-turns` 轮对话（默认 6 轮）。
- 输入 `/clear` 可手动清空上下文。


### 7) .env 配置

程序启动时会自动读取项目根目录下的 `.env` 文件。


### 8) 第二阶段：自动化回归

自动化回归 = 把“固定测试集评测”变成可重复执行的流水线（本地/CI都可跑），用于发现版本变更是否导致质量退化。

#### 你可以直接运行

```bash
python run_regression.py --provider mock --model gpt-4.1-mini
```

执行后会产出：
- `reports/latest_report.json`：基础评测结果
- `reports/regression_summary.json`：按 `difficulty` 与 `tags` 的分层通过率

#### 为什么这是第二阶段

第一阶段你有了更完整测试集（36条分层样本）；
第二阶段是让它“自动跑、可对比、可预警”，核心价值是：
- 每次改 prompt / 模型 / 代码后，快速知道是否退化；
- 定位退化发生在哪一层难度、哪一类场景；
- 为后续接入 CI 和阈值门禁打基础。


### 9) 第三阶段：回归门禁与失败闭环

第三阶段目标：把“能跑回归”升级为“可拦截退化”。

```bash
python gate_regression.py --provider mock --model gpt-4.1-mini
```

该命令会：
- 先执行回归（生成分层统计）；
- 检查最小通过率阈值（默认 `0.80`）；
- 与基线对比退化幅度（默认最多下降 `0.03`）；
- 导出失败用例到 `reports/failed_cases.json`，用于修复闭环。


### 10) V2增强（覆盖你提出的4项要求）

```bash
python v2_eval.py --provider mock --models gpt-4.1-mini,Qwen/Qwen3-8B --workers 8
```

V2 新增能力：
- 并发批量调用（`--workers`）；
- 多模型交叉验证（`--models` 逗号分隔）；
- 不一致性计算（`cross_model_disagreement`）；
- 指标增强：`accuracy`、`compliance_rate`、`ece`、`avg_latency_ms`；
- 输出 `reports/v2_eval_report.json` 作为多维测试报告。


### 11) V2.1 真实性核查模块

```bash
python fact_check.py --report reports/latest_report.json
```

输出：`reports/fact_check_report.json`，包含幻觉风险与合规信号统计。

### 12) 压测资产化（Postman / JMeter）

- Postman collection: `postman/llm_eval_collection.json`
- JMeter test plan: `perf/jmeter_test_plan.jmx`

### 13) 质量看板数据快照

```bash
python scripts/build_quality_dashboard.py
```

输出：`reports/dashboard_snapshot.json`，聚合基础评测、回归、V2、多模型不一致性、真实性核查指标。


### 14) 面试材料

已提供可直接复用的面试材料文档：
- `docs/interview_materials.md`

包含：
- 一页架构图（评测→回归→门禁→报告→整改）
- 一页指标定义表（accuracy/compliance/ECE/disagreement等）
- 一页真实问题案例模板（拦截→定位→修复→回归）
