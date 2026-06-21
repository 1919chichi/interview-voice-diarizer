# interview-voice-diarizer

[English](README.en.md)

本地面试录音复盘 CLI。它将录音交给火山引擎语音识别，标准化转写和说话人信息，判断面试官与候选人，再生成完整对话、问答复盘和结构化摘要。

## 功能

- 支持本地 `.wav`、`.mp3`、`.ogg` 直接上传。
- 支持 `.m4a`、`.qma`、`.mp4`、`.aac`、`.flac`，通过 `ffmpeg` 转为 16 kHz MP3 后上传。
- 支持火山 ASR 极速版的本地文件识别，以及标准版的公网音频 URL 提交与轮询。
- 请求 ASR 输出 utterance 和说话人信息，并校验多说话人结果未在标准化阶段错误折叠。
- 按每个 Speaker 的提问和回答证据判断面试官、候选人或未知角色，支持多个声纹簇归属于同一角色。
- 默认使用火山方舟生成深度复盘；也可使用 `--skip-analysis` 完全在本地生成启发式复盘。
- 支持从历史 `raw-asr.json` 重新生成报告，无需重新上传音频或调用 ASR。
- 输出 Markdown 转录稿、Markdown 问答复盘和 JSON 结构化摘要。

## 处理流程

```text
本地录音 / 公网音频 URL
        |
        v
音频探测与可选转码
        |
        v
火山 ASR -> raw-asr.json
        |
        v
转写标准化 -> 说话人校验 -> 角色判断 -> 复盘分析
        |
        v
transcript.md + qa-review.md + summary.json
```

`raw-asr.json` 会在方舟分析前落盘。分析阶段失败时，可使用 `ivd reanalyze` 从该文件继续，无需再次转写长录音。

## 环境要求

- Python 3.11+
- [`ffmpeg` 和 `ffprobe`](https://ffmpeg.org/documentation.html)
- [火山语音识别 API Key](https://www.volcengine.com/docs/6561/80816)
- 使用完整模型分析时，还需要[火山方舟 API Key 和模型 Endpoint ID](https://www.volcengine.com/docs/82379/1099455)

## 安装

```bash
git clone <repo-url>
cd interview-voice-diarizer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

安装后可用以下命令确认 CLI：

```bash
ivd --help
```

## 配置

```bash
cp .env.example .env
```

最小配置：

```dotenv
VOLC_ASR_API_KEY=你的火山语音识别_API_Key
VOLC_ARK_API_KEY=你的火山方舟_API_Key
VOLC_ARK_MODEL=你的方舟模型_Endpoint_ID
```

使用 `--skip-analysis` 时不需要 `VOLC_ARK_API_KEY` 和 `VOLC_ARK_MODEL`。代码还支持以下可选变量：

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `VOLC_ASR_RESOURCE_ID` | `volc.seedasr.auc` | ASR 标准版资源 ID |
| `VOLC_ASR_FLASH_RESOURCE_ID` | `volc.bigasr.auc_turbo` | ASR 极速版资源 ID |
| `VOLC_ARK_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3` | 方舟 OpenAI 兼容接口地址 |

也可以直接通过进程环境变量传入。可选变量如需使用代码默认值，应省略该变量，而不是将其设置为空字符串。

## 使用

### 分析本地录音

默认的 `flash` 模式读取本地文件：

```bash
ivd debrief "/path/to/recording.m4a" \
  --company "示例公司" \
  --role "后端开发" \
  --round "一面"
```

常用选项：

```bash
# 指定输出目录
ivd debrief "/path/to/recording.mp3" --output-dir "/path/to/output"

# 跳过方舟，只生成启发式复盘
ivd debrief "/path/to/recording.mp3" --skip-analysis
```

### 分析公网音频 URL

`standard` 模式使用 `--audio-url` 提交标准版 ASR 任务。位置参数仍用于生成默认输出目录名；建议显式指定 `--output-dir`：

```bash
ivd debrief "remote-interview.mp3" \
  --mode standard \
  --audio-url "https://example.com/interview.mp3" \
  --output-dir "outputs/remote-interview"
```

### 重新分析历史 ASR 结果

只要保留了 `raw-asr.json`，就能应用当前的转写标准化、Speaker 角色判断和复盘逻辑：

```bash
ivd reanalyze "outputs/<录音文件名>/raw-asr.json" \
  --company "示例公司" \
  --role "后端开发" \
  --round "一面"
```

该命令不会调用 ASR。默认会调用方舟重新生成完整复盘；完全本地运行时使用：

```bash
ivd reanalyze "outputs/<录音文件名>/raw-asr.json" --skip-analysis
```

默认写回 `raw-asr.json` 所在目录，也可用 `--output-dir` 指定其他目录。覆盖报告前，已有派生文件会备份到：

```text
outputs/<录音文件名>/backups/reanalysis-YYYYMMDD-HHMMSS/
├── summary.json
├── transcript.md
└── qa-review.md
```

原始 `raw-asr.json`、录音和转码文件不会被修改。输入 JSON 无效、说话人校验失败或方舟调用失败时，现有派生报告也不会被覆盖。

## 输出

默认输出目录为 `outputs/<录音文件名>/`：

```text
outputs/<录音文件名>/
├── converted.mp3      # 仅在本地输入需要转码时生成
├── raw-asr.json       # 火山 ASR 原始响应
├── summary.json       # 角色映射和结构化复盘
├── transcript.md      # 带时间戳和角色标签的完整对话
└── qa-review.md       # 问题、回答、缺陷、建议和学习点
```

## 音频格式与限制

- `.wav`、`.mp3`、`.ogg` 会直接上传，但仍会先由 `ffprobe` 探测。
- `.m4a`、`.qma`、`.mp4`、`.aac`、`.flac` 会保留最多两个声道并转为 16 kHz、64 kbps MP3。
- `.qma` 不是火山 ASR 明确支持的格式；只有能被 `ffprobe`/`ffmpeg` 解码时才能处理。
- 本项目不解密或绕过受保护音频。无法解码时，请从录音来源导出为 `.m4a`、`.mp3` 或 `.wav`。
- ASR 请求语言当前固定为 `zh-CN`。

## 开发与验证

```bash
.venv/bin/ruff check .
.venv/bin/python -m pytest -q
```

项目使用扁平化 `src/` 布局，CLI 入口为 `cli:app`。核心模块如下：

```text
src/
├── cli.py
├── config.py
├── errors.py
├── models.py
├── providers/volcengine.py
├── pipeline/{audio,transcript,analysis,debrief}.py
└── output/report.py
```

## 隐私

`.gitignore` 已排除 `.env`、常见录音格式、`outputs/` 和生成报告。不要提交 API Key、面试录音、`raw-asr.json` 或任何包含候选人隐私的输出。

## 相关文档

- [Volcano Engine ASR API](https://www.volcengine.com/docs/6561/80816)
- [Volcano Ark LLM API](https://www.volcengine.com/docs/82379/1099455)
- [ffmpeg Documentation](https://ffmpeg.org/documentation.html)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
