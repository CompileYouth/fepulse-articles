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

- `publisher-site/`
  本地发布助手网站。
  作用：
  - 列出 `selected/` 里的文章
  - 按“待分配时间 / 已分配时间”分组显示
  - 点击后直接加载 markdown
  - 渲染预览
  - 一键复制带内联样式的内容到公众号编辑器

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

扫描完成后，默认继续执行，不停在“只下载字幕”这一步：

- 先按 `FEPulse-reader-profile.md` 自动筛选
- 适合长文的 raw 字幕移动到 `selected/raw/`
- 其余需要快速了解的 raw 字幕移动到 `briefs/raw/`
- `selected/raw/` 自动整理为正式文章，输出到 `selected/`
- `briefs/raw/` 自动整理为 500 字左右简报，输出到 `briefs/`

这是默认执行链路，不需要再额外提醒。
只要已经完成扫描并成功落下字幕，就必须继续完成：

- 分流到 `selected/raw/` 或 `briefs/raw/`
- 生成 `selected/` 下的正式文章
- 生成 `briefs/` 下的简报

除非用户明确要求“只采集，不做后续处理”，否则不能停在采集结果。

### 2. 初筛

新内容扫描完成后，不要长期留在 `ai-interview-archive-data/` 根目录。

需要立刻做一次分流，并继续完成后续生成：

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

处理 YouTube 来源时，参与者信息不能偷懒写成“分享者”“设计者”这类泛称。

默认规则：

- 先用视频公开元数据确认人物信息
- 优先读取 `channel`、`uploader`、`description`
- 能确认真实姓名时，使用“真实姓名（身份）”
- 如果不能确认，就保守描述身份，不使用含糊占位词

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

### 7. 公众号复制网站

启动方式：

- `python3 publisher-site/server.py`

默认地址：

- `http://127.0.0.1:8008`

工作方式：

- 左侧有 `精选` 和 `简报` 两个 Tab
- `精选` 会直接读取 `selected/` 里的 markdown 文件
- 文件名如果是 `YYYY-MM-DD 标题.md`，会归到“已分配时间”
- 文件名如果只有 `标题.md`，会归到“待分配时间”
- `简报` 会展示 `briefs/` 第一层未读内容，以及 `briefs/archived/` 中的已读内容
- `简报` 里的未读内容支持一键“精选”，会直接移动到 `selected/`
- 点击文章后直接渲染 markdown，并可一键复制带样式内容
- 复制时不会预先生成单独的 html 文件

### 8. 飞书群发送

如果你已经在 `selected/` 里把文章文件名改成：

- `YYYY-MM-DD 标题.md`

那么每天 `08:00` 的发送脚本会自动查找当天日期前缀的文章，并发送到飞书群机器人。

发送时区默认按：

- `Asia/Shanghai`

本地配置：

- `.local/feishu-bot.env`
- `.local/feishu-app.env`（可选，优先级更高）

需要包含：

- `FEISHU_BOT_WEBHOOK=...`
- `FEISHU_BOT_SECRET=...`
- `FEISHU_APP_ID=...`
- `FEISHU_APP_SECRET=...`
- `FEISHU_CHAT_ID=...`

发送脚本：

- `python3 scripts/send_scheduled_feishu_posts.py --workspace-root /Users/bytedance/Documents/my-projects/fepulse-articles`

默认规则：

- 优先使用飞书应用发送：`FEISHU_APP_ID + FEISHU_APP_SECRET + FEISHU_CHAT_ID`
- 如果没有配置飞书应用，则退回群 webhook 发送
- 只发送 `selected/` 第一层里文件名前缀等于当天日期的文章
- 如果同一天有多篇，会按文件名字典序依次发送
- 发送成功后记录到 `.local/feishu-sent-log.json`
- 已发送过的同名文件不会重复发送
- 优先使用飞书 `interactive card` 发送；webhook 兜底时也尽量保留标题、分段和小节结构

## 备注

- 这个仓库本身不负责抓取 YouTube 频道列表，抓取逻辑由 `ai-interview-archive` 提供。
- 如果 YouTube 返回 `Sign in to confirm you’re not a bot`，通常需要给 `yt-dlp` 配置 cookies 后重试字幕下载。
- 默认分流顺序是：`ai-interview-archive-data/` -> `selected/raw/` / `briefs/raw/`
- 默认长文顺序是：`selected/raw/` -> `PROMPT_TEMPLATE.md` -> `selected/`
- 默认简报顺序是：`briefs/raw/` -> `BRIEF_PROMPT_TEMPLATE.md` -> `briefs/`
- 本仓库的 git 提交信息默认使用中文。
- 在这个仓库里，如果你只说“提交”，默认执行“提交 + 推送到远程”。
