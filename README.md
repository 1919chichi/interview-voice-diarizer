# interview-voice-diarizer

本地面试录音复盘 CLI。输入录音文件，自动转码为火山语音识别支持的格式，调用火山 API 获取转写和说话人分离结果，再生成面试问题、候选人回答、回答缺陷、优化建议和后续学习点。

## 功能

- 支持本地 `.m4a`、`.qma`、`.wav`、`.mp3`、`.ogg` 输入。
- 对火山不直接支持的格式，使用 `ffmpeg` 转为 `.mp3` 后上传。
- 调用火山语音识别 API，开启说话人分离与 utterance 输出。
- 自动推断 `Speaker 0 / Speaker 1` 分别对应面试官和候选人。
- 输出本地 Markdown 和 JSON 文件。

## 环境要求

- Python 3.11+
- `ffmpeg` 和 `ffprobe`
- 火山语音识别 API Key
- 火山方舟 API Key 和模型 Endpoint ID

## 安装

```bash
git clone <repo-url>
cd interview-voice-diarizer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## 配置

```bash
cp .env.example .env
```

填写：

```bash
VOLC_ASR_API_KEY=你的火山语音识别 API Key
VOLC_ARK_API_KEY=你的火山方舟 API Key
VOLC_ARK_MODEL=你的方舟模型 Endpoint ID
```

也可以直接通过环境变量传入。

## 使用

```bash
ivd debrief "/path/to/recording.m4a" \
  --company "示例公司" \
  --role "后端开发" \
  --round "一面"
```

输出目录默认是：

```text
outputs/<录音文件名>/
├── converted.mp3
├── raw-asr.json
├── summary.json
├── transcript.md
└── qa-review.md
```

## `.qma` 说明

`.qma` 不是火山语音识别文档明确支持的音频格式。本 CLI 会先用 `ffprobe/ffmpeg` 尝试解码：

- 如果可解码，会转为 `.mp3` 后上传。
- 如果不可解码，会报错并提示先从录音来源导出为 `.m4a/.mp3/.wav`。

本项目不处理加密或受保护音频。
