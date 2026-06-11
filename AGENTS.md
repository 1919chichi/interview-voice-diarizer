# 项目协作约定

## 语言
- 默认使用中文沟通。

## 项目目标
- 本项目是本地运行的面试录音复盘 CLI。
- 输入 `.m4a` 或 `.qma` 等本地录音文件，必要时用 `ffmpeg` 转为标准音频，再调用火山引擎录音识别 API 获取转写和说话人分离结果。
- 根据对话内容判断面试官与候选人，并输出问题、回答、缺陷、优化建议和后续学习点。

## 目录结构

```
src/interview_voice_diarizer/
├── cli.py          # CLI 入口（Typer）
├── config.py       # 环境变量加载与配置
├── errors.py       # 自定义异常
├── models.py       # Pydantic 数据模型
├── providers/      # 外部服务适配器
│   └── volcengine.py   # 火山 ASR + 方舟 LLM 客户端
├── pipeline/       # 处理流水线各步骤
│   ├── audio.py        # 本地音频探测与转码
│   ├── transcript.py   # ASR 结果标准化
│   └── analysis.py     # 角色判断与复盘分析
└── output/         # 报告渲染与写入
    └── report.py
```

## 开发约定
- 优先保持 CLI 简单可运行，不引入 Web UI、数据库或用户系统。
- 不提交任何 API Key、录音文件或包含隐私内容的输出报告。
- 新增外部服务客户端放入 `providers/`；新增处理步骤放入 `pipeline/`；新增输出格式放入 `output/`。
- `models.py`、`errors.py`、`config.py` 是基础层，不得反向依赖 `pipeline/` 或 `providers/`。
