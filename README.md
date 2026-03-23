# fepulse-articles

这个仓库用于两件事：

1. 用统一提示词整理前沿 AI 原始材料
2. 基于字幕或原文，产出 FEPulse 可发布的文章

原始内容采集由独立 skill `ai-interview-archive` 完成，但采集结果可以直接落到当前仓库下的 `ai-interview-archive-data/`。

## 目录结构

- `PROMPT_TEMPLATE.md`
  基础提示词模板。写作前先维护这里的稳定规则。

- `ai-interview-archive-data/`
  由 `ai-interview-archive` 生成的采集结果目录。
  其中包括：
  - `link-batches/`：每次扫描的批次结果
  - `transcripts/`：采集成功后的 cleaned 字幕或相关输出

- `transcripts/`
  手动放入的字幕文件。适合你单独提供某条 YouTube / 音频内容时直接使用。

- `articles/`
  最终文章输出目录。

- `drafts/`
  中间版本、改写稿、备选稿。

- `fepulse-reader-picks/`
  面向 FEPulse 公众号读者的二次筛选目录。
  用于保存每次扫描后按读者偏好挑出的候选内容。

- `skills/`
  当前仓库内维护的 skill 镜像。

## 当前工作流

### 1. 采集

使用 `ai-interview-archive`：

- 扫过去 1 天：
  `python3 /Users/bytedance/Documents/my-projects/ai-interview-archive/scripts/run_collection.py --mode daily --workspace-root /Users/bytedance/Documents/my-projects/fepulse-articles`

- 扫过去 2 天：
  `python3 /Users/bytedance/Documents/my-projects/ai-interview-archive/scripts/run_collection.py --mode manual --days 2 --workspace-root /Users/bytedance/Documents/my-projects/fepulse-articles`

- 扫过去 7 天：
  `python3 /Users/bytedance/Documents/my-projects/ai-interview-archive/scripts/run_collection.py --mode weekly --workspace-root /Users/bytedance/Documents/my-projects/fepulse-articles`

采集结果默认写到：

- `ai-interview-archive-data/link-batches/`
- `ai-interview-archive-data/`

### 2. 写作

写作时优先读取：

1. `PROMPT_TEMPLATE.md`
2. `ai-interview-archive-data/` 下最新批次结果
3. `transcripts/` 或 `ai-interview-archive-data/` 下已经落盘的字幕 / cleaned 文本

最终文章输出到：

- `articles/`

### 3. 筛选

每次 `ai-interview-archive` 扫描完成后，都需要再做一层 FEPulse 读者偏好筛选。

筛选结果写到：

- `fepulse-reader-picks/`

筛选标准以：

- `fepulse-reader-picks/FEPulse-reader-profile.md`

为准。

## 命名建议

- 手动字幕：`topic-name.txt`
- 文章文件：`topic-name.md`

## 备注

- 这个仓库本身不负责抓取 YouTube 频道列表，抓取逻辑由 `ai-interview-archive` 提供。
- 如果 YouTube 返回 `Sign in to confirm you’re not a bot`，通常需要给 `yt-dlp` 配置 cookies 后重试字幕下载。
