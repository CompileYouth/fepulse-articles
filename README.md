# fepulse-articles

用于按统一提示词，批量将 YouTube 字幕整理成文章。

## 目录结构

- `PROMPT_TEMPLATE.md`：基础提示词文件
- `transcripts/`：放置原始字幕文件
- `articles/`：放置生成后的文章
- `drafts/`：可选的中间草稿或人工修改版本

## 使用方式

1. 先在 `PROMPT_TEMPLATE.md` 中填写基础提示词。
2. 将字幕文件放入 `transcripts/`，或直接在对话里逐份发给我。
3. 我会根据提示词和字幕内容，生成对应文章。
4. 成稿可保存到 `articles/`。

## 命名建议

- 字幕文件：`topic-name.txt`
- 文章文件：`topic-name.md`
