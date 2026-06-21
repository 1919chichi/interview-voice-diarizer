# 项目协作约定

## 语言
- 默认使用中文沟通。

## 项目目标
- 本项目是本地运行的面试录音复盘 CLI，不扩展 Web UI、数据库或用户系统。
- `ivd debrief` 接收本地录音，或在标准版模式下接收公网音频 URL，调用火山引擎 ASR 获取转写和说话人信息。
- 后处理流水线负责标准化 ASR 结果、校验说话人数量、判断面试官与候选人，并生成问题、回答、缺陷、优化建议和后续学习点。
- `ivd reanalyze` 复用历史 `raw-asr.json` 重新生成报告，不得再次调用 ASR。

## 目录结构

源码使用扁平化的 `src/` 布局，`pyproject.toml` 中的命令入口为 `cli:app`：

```text
src/
├── cli.py              # Typer CLI：debrief、reanalyze
├── config.py           # .env 加载与火山 ASR/方舟配置
├── errors.py           # 面向 CLI 的自定义异常
├── models.py           # Pydantic 数据模型
├── providers/
│   └── volcengine.py   # 火山 ASR 极速版/标准版与方舟 LLM 客户端
├── pipeline/
│   ├── audio.py        # 音频探测、格式校验与 ffmpeg 转码
│   ├── transcript.py   # ASR 标准化、说话人诊断与角色重标记
│   ├── analysis.py     # 启发式/方舟角色判断与问答复盘
│   └── debrief.py      # 新识别与历史重分析共用的后处理流水线
└── output/
    └── report.py       # Markdown/JSON 渲染、写入与旧报告备份

tests/                  # pytest 单元测试与 CLI 行为测试
```

## 处理流程
- `flash` 模式处理本地文件：探测音频，必要时转为 MP3，再以内嵌数据调用 ASR 极速版。
- `standard` 模式要求 `--audio-url`，提交公网 URL 并轮询标准版 ASR 任务。
- 两种模式都先写入 `raw-asr.json`，再进入 `pipeline/debrief.py` 的共享后处理。
- 后处理必须校验多说话人的原始结果没有在标准化阶段错误折叠。
- 未指定 `--skip-analysis` 时使用方舟生成完整复盘；指定后只运行本地启发式分析。
- 历史重分析只覆盖 `summary.json`、`transcript.md`、`qa-review.md`，覆盖前将已有派生报告备份到 `backups/reanalysis-<时间戳>/`；不得修改 `raw-asr.json`、录音或转码文件。

## 代码注释约定
- **每个函数（含方法、属性、静态方法）都必须有 docstring**，放在函数体第一行。
- docstring 使用中文，一行说明即可；说清楚该函数**做什么、边界条件或副作用**。
- 新增或修改函数时，必须同步添加或更新 docstring，不得留空。

## 开发约定
- 新增外部服务客户端放入 `providers/`；新增处理步骤放入 `pipeline/`；新增输出格式放入 `output/`。
- `models.py`、`errors.py`、`config.py` 是基础层，不得反向依赖 `pipeline/`、`providers/` 或 `output/`。
- 新识别与历史重分析的 ASR 后处理逻辑应集中在 `pipeline/debrief.py`，避免两条命令产生不同结果。
- 保留 `raw-asr.json` 作为可续跑的中间产物；方舟失败时不得要求重新上传和识别音频。
- 写入新报告前先完成输入解析、说话人校验和模型分析，失败时保留现有报告。
- 不提交 API Key、录音文件、`raw-asr.json` 或包含面试隐私的输出报告。

## 验证

```bash
.venv/bin/ruff check .
.venv/bin/python -m pytest -q
```

- 修改 CLI 时同时检查 `ivd --help`、`ivd debrief --help` 和 `ivd reanalyze --help`。
- 修改用户可见行为时同步更新 `README.md` 与 `README.en.md`。
