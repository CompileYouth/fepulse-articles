# fepulse-articles

这个仓库现在不再围绕公众号发布流转，而是围绕“先读简报，再决定是否详读”的阅读流转。

## 目录结构

- `ai-interview-archive-data/`
  - 只负责扫描批次和去重索引
  - `link-batches/` 记录每次扫描结果
  - `subtitle-index.json` 记录哪些来源已经拉取过，避免重复下载

- `raw/`
  - 所有原始字幕统一放这里
  - 文件名是基于 `source_url` 生成的稳定 hash
  - 一旦写入就只读，不再移动或改名

- `briefs/`
  - 所有简报成品
  - 文件名统一为 `<hash>.md`
  - `index.json` 记录标题、来源、是否已读、已读时间、是否加入详读候选

- `deep-reads/`
  - 所有详读成品
  - 文件名统一为 `<hash>.md`
  - `index.json` 记录标题、来源、是否已读、已读时间
  - 内容形态不是观点长文，而是按原始字幕整理出的中文全文稿

- `selected/`
  - 历史遗留的旧长文目录
  - 已废弃，不再参与任何新流程，只保留已有内容

- `publisher-site/`
  - 本地阅读站点
  - 只展示 `briefs/` 和 `deep-reads/`

- `scripts/`
  - `sync_reading_pipeline.py`
    - 把扫描到的原始字幕同步进 `raw/`
    - 默认全部生成简报到 `briefs/`
    - 迁移历史 `briefs/raw`
  - `generate_deep_reads.py`
    - 读取 `briefs/index.json` 里已加入“详读候选”的内容
    - 生成 `deep-reads/<hash>.md`

## 当前工作流

### 1. 扫描

采集仍由 `$ai-interview-archive` 完成，扫描结果先进入：

- `ai-interview-archive-data/link-batches/`
- `ai-interview-archive-data/subtitle-index.json`

### 2. 同步到阅读结构

扫描完成后，默认继续执行：

```bash
python3 scripts/sync_reading_pipeline.py
```

这一步会做：

- 把原始字幕统一整理到 `raw/<hash>.txt`
- 默认为每条内容生成简报到 `briefs/<hash>.md`
- 更新 `briefs/index.json`
- 同步 `ai-interview-archive-data/subtitle-index.json` 里的 `subtitle_path`

默认规则：

- 每篇扫描出来的内容只先生成简报
- 不再自动生成长文
- 只有进入“详读候选”的内容，后面才会生成详读文章

### 3. 生成详读文章

网站里点击“详读”后，会把对应内容标记为详读候选。

执行：

```bash
python3 scripts/generate_deep_reads.py --all
```

脚本会读取 `briefs/index.json` 中 `queued_for_deep_read=true` 且尚未生成详读的内容，生成到：

- `deep-reads/<hash>.md`

说明：

- 详读一律从 `raw/` 生成
- `selected/` 不再作为详读输入
- 详读默认按“接近原文的中文整理稿”处理：
  - 翻译成简体中文
  - 把字幕断裂的句子自然衔接
  - 按内容重新分段
  - 尽量遵循原文，不改写成公众号文章

### 4. 已读状态

- `briefs/index.json` 维护简报的已读时间
- `deep-reads/index.json` 维护详读文章的已读时间
- 网站按“未读 / 已读”展示
- 已读列表按已读时间倒序排列

## 网站

启动方式：

```bash
python3 publisher-site/server.py
```

地址：

- `http://127.0.0.1:8008`

固定顺序：

- 先探活 `127.0.0.1:8008`
- 端口被死进程占用时先清理
- 再启动 `python3 publisher-site/server.py`
- 确认首页或 API 返回正常后再打开浏览器

网站行为：

- `简报` tab
  - `未读`
  - `已读`
  - 未读内容支持 `详读`
  - 简报支持 `标记已读`

- `详读` tab
  - `未读`
  - `已读`
  - 详读支持 `标记已读`

## 约定

- 内容的唯一标识统一使用基于 `source_url` 的稳定 hash
- 后续任何状态变化都只改 `index.json`，不改 `raw/` 中文件
- 本仓库的 git 提交信息默认使用中文
- 在这个仓库里，如果你只说“提交”，默认执行“提交 + 推送到远程”
