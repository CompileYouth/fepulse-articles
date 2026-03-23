---
name: fepulse-wechat-publisher
description: Use when the user wants to turn archived FEPulse raw sources or transcripts into publishable WeChat articles for 公众号 FEPulse, including restructuring, rewriting, batching, and draft scheduling based on the locally stored source archive.
---

# FEPulse WeChat Publisher

Use this skill when the user wants finished article output rather than raw source collection.

## Load First

- Read `references/path-map.md`
- Read `/Users/bytedance/Documents/my-projects/fepulse-articles/PROMPT_TEMPLATE.md`
- Read the exact source bundle or transcript files the user wants processed

## What This Skill Does

- turn archived raw materials into publish-ready FEPulse articles
- preserve the source meaning while improving structure, readability, and public-account fit
- keep the raw archive separate from the rewritten output
- support single-article generation and batched article production from a backlog

## Core Rules

- Treat the source archive as the ground truth.
- Do not add outside claims unless the user explicitly asks for extra analysis.
- Keep one clear center of gravity per article.
- Prefer direct delivery into `articles/` when the user explicitly asks for the article.
- Use `drafts/` only for intermediate versions, comparison copies, or multi-round revisions.
- Never overwrite the raw source bundle or transcript.

## Default Workflow

1. Identify the exact input set.
   - one transcript
   - one source bundle
   - several related source bundles for synthesis
2. Read `PROMPT_TEMPLATE.md` before drafting.
3. Extract the article's single driving question or judgment.
4. Write the article directly into `articles/`.
   - default filename: `topic-name.md`
   - if a better slug is obvious from the source, use it
5. If the user is still exploring, stay in outline mode first.
6. If the user asks for the final article, produce the article instead of discussing the process.
7. After writing, do a short review for:
   - source fidelity
   - structure
   - public-account readability
   - whether the title and opening are strong enough to publish

## Working With Backlogs

When the user has a backlog of collected materials:

- prioritize the most information-dense or most timely primary sources first
- avoid turning every source into the same article template
- keep article filenames stable after creation
- if several sources repeat the same theme, propose a synthesis article instead of forcing separate pieces

## Optional Scheduling

If the user wants article drafting to run on a schedule, create or update an automation.

- Daily drafting RRULE:
  - `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR,SA,SU;BYHOUR=<hour>;BYMINUTE=<minute>`
- Weekly drafting RRULE:
  - `FREQ=WEEKLY;BYDAY=<day>;BYHOUR=<hour>;BYMINUTE=<minute>`
- Use this path in the automation prompt:
  - `[$fepulse-wechat-publisher](/Users/bytedance/.codex/skills/fepulse-wechat-publisher/SKILL.md)`
- Set `cwds` to `/Users/bytedance/Documents/my-projects/fepulse-articles`

## Output Standard

At the end of each run, leave the user with:

- the finished article path
- the source paths it came from
- any open issue that still blocks publishing
