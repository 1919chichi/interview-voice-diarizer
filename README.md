# interview-voice-diarizer

本地面试录音复盘 CLI。输入录音文件，自动转码为火山语音识别支持的格式，调用火山 API 获取转写和说话人分离结果，再生成面试问题、候选人回答、回答缺陷、优化建议和后续学习点。

## 功能

- 支持本地 `.m4a`、`.qma`、`.wav`、`.mp3`、`.ogg` 输入。
- 对火山不直接支持的格式，使用 `ffmpeg` 转为 `.mp3` 后上传。
- 调用火山语音识别 API，开启说话人分离与 utterance 输出。
- 自动推断每个 Speaker 对应面试官、候选人或未知角色，并支持多个声纹簇归属于同一角色。
- 支持从历史 `raw-asr.json` 重新生成报告，无需再次调用 ASR。
- 输出本地 Markdown 和 JSON 文件。

## 环境要求

- Python 3.11+
- [`ffmpeg` 和 `ffprobe`](https://ffmpeg.org/documentation.html)
- [火山语音识别 API Key](https://www.volcengine.com/docs/6561/80816)（Volcano Engine ASR）
- [火山方舟 API Key](https://www.volcengine.com/docs/82379/1099455) 和模型 Endpoint ID（Volcano Ark LLM）

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

### 重新分析历史 ASR 结果

历史目录保留了 `raw-asr.json` 时，可以直接应用最新的 Speaker 和角色判断逻辑：

```bash
ivd reanalyze "outputs/<录音文件名>/raw-asr.json" \
  --company "示例公司" \
  --role "后端开发" \
  --round "一面"
```

该命令不会调用 ASR。默认仍会调用方舟重新生成完整复盘；使用下面的参数可执行完全本地的启发式修复：

```bash
ivd reanalyze "outputs/<录音文件名>/raw-asr.json" --skip-analysis
```

覆盖报告前，现有派生文件会备份到：

```text
outputs/<录音文件名>/backups/reanalysis-YYYYMMDD-HHMMSS/
├── summary.json
├── transcript.md
└── qa-review.md
```

原始 `raw-asr.json`、录音和转码文件不会被修改。

## `.qma` 说明

`.qma` 不是火山语音识别文档明确支持的音频格式。本 CLI 会先用 [`ffprobe`/`ffmpeg`](https://ffmpeg.org/ffprobe.html) 尝试解码：

- 如果可解码，会转为 `.mp3` 后上传。
- 如果不可解码，会报错并提示先从录音来源导出为 `.m4a/.mp3/.wav`。

本项目不处理加密或受保护音频。

## 相关文档

- [Volcano Engine ASR API](https://www.volcengine.com/docs/6561/80816) — 语音识别接口文档
- [Volcano Ark LLM API](https://www.volcengine.com/docs/82379/1099455) — 方舟大模型接口文档
- [ffmpeg Documentation](https://ffmpeg.org/documentation.html) — 音频转码工具文档
- [Python `python-dotenv`](https://github.com/theskumar/python-dotenv) — 环境变量管理
