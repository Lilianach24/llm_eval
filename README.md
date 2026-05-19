# llm_eval

针对通用AI大模型开展全方面功能测试与质量验收，重点检测模型回答准确性、稳定性，排查幻觉与逻辑错误等问题。

## 写作助手测试项目（可直接运行）

### 1) 环境

```bash
python3 --version
```

本项目默认只依赖 Python 标准库，并在仓库内置了 `dotenv.load_dotenv()` 所需的最小实现。

### 2) 快速开始（离线可跑）

#### 启动交互式写作助手

```bash
python3 app.py chat --provider mock
```

#### 运行批量评测

```bash
python3 app.py eval --provider mock
```

评测结果会输出到：

- `reports/latest_report.json`

### 3) 接入真实模型（Silicon/OpenAI 兼容）

```bash
export ANTHROPIC_API_KEY="你的Key"
export ANTHROPIC_BASE_URL="https://api.openai-proxy.org/v1"
python3 app.py --provider openai --model Qwen/Qwen3-8B --max-history-turns 6 chat
python3 app.py --provider openai --model Qwen/Qwen3-8B eval
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
python3 run_regression.py --provider mock --model gpt-4.1-mini
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
