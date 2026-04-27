from __future__ import annotations

import argparse
import json

from content_store import (
    DEEP_READS_DIR,
    DEEP_READS_INDEX_PATH,
    RAW_DIR,
    build_brief_from_transcript,
    load_index,
    now_iso,
    read_source_document,
    write_json,
)


def build_fallback_deep_read(raw_text: str, source_url: str) -> str:
    brief = build_brief_from_transcript(raw_text, source_url)
    paragraphs = [part.strip() for part in brief.split("\n\n") if part.strip()]
    body = paragraphs[1:] if len(paragraphs) > 1 else paragraphs
    sections = [
        ("这份内容先把问题摆在哪里", body[0] if body else ""),
        ("它是怎么把这个问题展开的", body[1] if len(body) > 1 else body[0] if body else ""),
        ("里面最值得继续追的判断是什么", body[2] if len(body) > 2 else body[-1] if body else ""),
    ]
    parts = [f"> 原始来源：{source_url}", ""]
    for heading, paragraph in sections:
        if not paragraph:
            continue
        parts.append(f"## {heading}")
        parts.append(paragraph)
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="generate all queued deep reads")
    parser.add_argument("--id", dest="content_id", help="only generate one content id")
    args = parser.parse_args()

    deep_index = load_index(DEEP_READS_INDEX_PATH)
    deep_items = deep_index.setdefault("items", {})

    generated = []
    for content_id, item in deep_items.items():
        if args.content_id and content_id != args.content_id:
            continue
        if item.get("deep_read_file"):
            continue

        source_url = item["source_url"]
        raw_path = RAW_DIR / item["raw_file"]
        if not raw_path.exists():
            continue

        document = read_source_document(raw_path)
        if not document:
            continue
        deep_text = build_fallback_deep_read(raw_path.read_text(encoding="utf-8"), source_url)

        target_path = DEEP_READS_DIR / f"{content_id}.md"
        target_path.write_text(deep_text, encoding="utf-8")
        item["deep_read_file"] = target_path.name
        item["generated_at"] = now_iso()
        item["updated_at"] = now_iso()
        generated.append(content_id)

    write_json(DEEP_READS_INDEX_PATH, deep_index)
    print(json.dumps({"generated": generated}, ensure_ascii=False))


if __name__ == "__main__":
    main()
