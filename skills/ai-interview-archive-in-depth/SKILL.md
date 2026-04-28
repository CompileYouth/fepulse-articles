---
name: ai-interview-archive-in-depth
description: Use when the user wants to inspect queued deep-read items in this repository and generate any missing full Chinese deep reads from raw transcripts.
---

# AI Interview Archive In Depth

Use this skill in `/Users/bytedance/Documents/my-projects/fepulse-articles` when the user wants to complete pending `deep-reads`.

This skill does not scan sources and does not touch `selected/`. It only checks `deep-reads/` and fills in missing detailed content from `raw/`.

## Load First

- Read `/Users/bytedance/Documents/my-projects/fepulse-articles/deep-reads/index.json`
- Read `/Users/bytedance/Documents/my-projects/fepulse-articles/scripts/content_store.py`
- If you need one concrete format reference, read `/Users/bytedance/Documents/my-projects/fepulse-articles/deep-reads/e75438cdff99ec22.md`

## What Counts As "Not Yet A Detailed Article"

Treat an item as pending when any of these is true:

- `deep_read_file` is `null`
- `deep_read_file` points to a file that does not exist
- the file exists but is only a placeholder, for example it mainly says the item was queued for deep read and does not contain real transcript-style content

Do not use `selected/` to fill gaps. `selected/` is deprecated history only.

## Source Of Truth

For each pending item:

1. Read its `raw_file` from `/Users/bytedance/Documents/my-projects/fepulse-articles/raw/`
2. Use the raw transcript as the only ground truth
3. Generate `/Users/bytedance/Documents/my-projects/fepulse-articles/deep-reads/<id>.md`

## Output Standard

The output is not a summary article and not a viewpoint essay.

It must be:

- a simplified-Chinese full-text整理稿 based on the transcript
- faithful to the original meaning and order
- cleaned up so subtitle-broken sentences are naturally reconnected
- re-paragraphed by topic and speech flow
- readable as continuous prose

## Writing Rules

- Keep the original chronology.
- Do not compress the content into a few takeaway sections.
- Do not rewrite it into a公众号文章.
- Do not add outside facts, opinions, or synthesis.
- Remove subtitle noise such as `[MUSIC PLAYING]`, repeated arrows, and obvious OCR debris.
- Repair broken sentences caused by subtitle line wrapping.
- Preserve names, product names, and technical terms when that is clearer than forced translation.
- Prefer plain paragraphs.
- Only add `##` section headings when the speaker clearly shifts to a new topic and the heading helps navigation.

## File Format

Each generated file should start with:

```md
> 原始来源：https://...

![](https://i.ytimg.com/vi/<video_id>/maxresdefault.jpg)
```

Then the正文整理稿 begins.

If the source is not a YouTube link or no thumbnail can be derived, omit the image line.

## Index Updates

After generating a deep read:

- set `deep_read_file` to `<id>.md`
- set `generated_at` if it was empty
- always refresh `updated_at`

Write the changes back to `/Users/bytedance/Documents/my-projects/fepulse-articles/deep-reads/index.json`.

## Completion Standard

Before you say the run is done:

- every pending item you chose to process now has a real `deep-reads/<id>.md`
- the corresponding `deep-reads/index.json` entries point to those files
- the generated content is Chinese and no longer a placeholder

At the end, report:

- which ids were generated
- the output file paths
- any item you skipped and the concrete reason
