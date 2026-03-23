# fepulse-articles

这个仓库现在有一条更明确的四层流程：

1. 新扫描内容先进入 `ai-interview-archive-data/`
2. 初筛后分流到 `selected/raw/` 或 `briefs/raw/`
3. `selected/raw/` 生成正式文章到 `selected/`
4. `briefs/raw/` 生成约 500 字简报到 `briefs/`

原始内容采集由独立 skill `ai-interview-archive` 完成，但采集结果可以直接落到当前仓库下。

## 目录结构

- `PROMPT_TEMPLATE.md`
  正式写作提示词。
  对 `selected/raw/` 中选中的字幕文件，默认使用这个提示词生成文章。

- `FEPulse-reader-profile.md`
  读者画像。
  用于判断哪些 raw 字幕应该进入长文主线。

- `BRIEF_PROMPT_TEMPLATE.md`
  500 字左右的快速概览提示词。
  用于把非精选内容整理成可快速阅读的简报。

- `ai-interview-archive-data/`
  由 `ai-interview-archive` 生成的新扫描结果目录。
  这是扫描入口，不是长期堆积区。
  其中包括：
  - `link-batches/`：每次扫描的批次结果

- `selected/`
  最终可发布长文目录。
  第一层存放正式长文。
  `selected/raw/` 存放这些长文对应的 raw 字幕。

- `briefs/`
  非精选内容的简报目录。
  第一层只保留你还没读完的简报。
  `briefs/raw/` 存放这些简报对应的原始字幕。
  `briefs/archived/` 存放你已经看过的简报。

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

### 2. 初筛

新内容扫描完成后，不要长期留在 `ai-interview-archive-data/` 根目录。

需要立刻做一次分流：

- 如果适合 FEPulse 主线读者：
  移到 `selected/raw/`

- 如果不适合长文，但仍值得快速了解：
  移到 `briefs/raw/`

- 如果没有字幕或价值很低：
  可以直接忽略

### 3. 处理精选内容

写作正式文章时优先读取：

1. `PROMPT_TEMPLATE.md`
2. `selected/raw/` 中已筛选出的字幕文件

最终文章输出到：

- `selected/`

### 4. 处理非精选内容

对 `briefs/raw/` 中的字幕：

1. 使用 `BRIEF_PROMPT_TEMPLATE.md`
2. 生成约 500 字简报
3. 输出到 `briefs/` 第一层
4. 你看完之后手动移到 `briefs/archived/`

### 5. 公众号排期

当你告诉我某篇正式文章的发布日期时：

- 我会把 `selected/` 里的文件名从：
  `标题.md`
- 改成：
  `YYYY-MM-DD 标题.md`

例如：

- `2026-03-03 AI时代最值钱的程序员，已经不再只盯着代码.md`

### 6. 筛选标准

每次 `ai-interview-archive` 扫描完成后，都需要再做一层 FEPulse 读者偏好筛选。

筛选标准以：

- `FEPulse-reader-profile.md`

为准。

## 备注

- 这个仓库本身不负责抓取 YouTube 频道列表，抓取逻辑由 `ai-interview-archive` 提供。
- 如果 YouTube 返回 `Sign in to confirm you’re not a bot`，通常需要给 `yt-dlp` 配置 cookies 后重试字幕下载。
- 默认分流顺序是：`ai-interview-archive-data/` -> `selected/raw/` / `briefs/raw/`
- 默认长文顺序是：`selected/raw/` -> `PROMPT_TEMPLATE.md` -> `selected/`
- 默认简报顺序是：`briefs/raw/` -> `BRIEF_PROMPT_TEMPLATE.md` -> `briefs/`
