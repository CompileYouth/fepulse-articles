from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from content_store import (
    AI_ARCHIVE_DIR,
    BRIEFS_DIR,
    BRIEFS_INDEX_PATH,
    DEEP_READS_DIR,
    DEEP_READS_INDEX_PATH,
    LEGACY_BRIEFS_ARCHIVED_DIR,
    LEGACY_BRIEFS_RAW_DIR,
    RAW_DIR,
    SUBTITLE_INDEX_PATH,
    build_brief_from_transcript,
    content_id_for_url,
    ensure_cover_image_markdown,
    ensure_parent,
    extract_source_url_from_text,
    load_index,
    load_json,
    normalize_source_url,
    now_iso,
    read_source_document,
    title_without_date_prefix,
    write_json,
)


def load_legacy_briefs() -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    current_index = load_index(BRIEFS_INDEX_PATH)
    for item in current_index.get("items", {}).values():
        brief_file = item.get("brief_file")
        source_url = item.get("source_url")
        title = item.get("title")
        if not isinstance(brief_file, str) or not isinstance(source_url, str) or not isinstance(title, str):
            continue
        if len(title) == 16 and all(char in "0123456789abcdef" for char in title.lower()):
            continue
        path = BRIEFS_DIR / brief_file
        if not path.exists():
            continue
        mapping[source_url] = {
            "title": title,
            "content": path.read_text(encoding="utf-8").strip() + "\n",
        }

    tracked = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", "briefs"],
        cwd=BRIEFS_DIR.parent,
        check=True,
        capture_output=True,
        text=True,
    )
    for raw_name in tracked.stdout.splitlines():
        if not raw_name.endswith(".md"):
            continue
        if raw_name.endswith("README.md") or raw_name.endswith("index.json"):
            continue
        shown = subprocess.run(
            ["git", "show", f"HEAD:{raw_name}"],
            cwd=BRIEFS_DIR.parent,
            check=True,
            capture_output=True,
            text=True,
        )
        source_url = extract_source_url_from_text(shown.stdout)
        if not source_url or source_url in mapping:
            continue
        mapping[source_url] = {
            "title": Path(raw_name).stem,
            "content": shown.stdout.strip() + "\n",
        }
    return mapping


def collect_raw_candidates() -> list[Path]:
    candidates: list[Path] = []
    for directory in [RAW_DIR, LEGACY_BRIEFS_RAW_DIR, AI_ARCHIVE_DIR]:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.txt")):
            candidates.append(path)
    return candidates


def migrate_raw_documents() -> dict[str, dict[str, str]]:
    documents: dict[str, dict[str, str]] = {}
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    subtitle_index = load_json(SUBTITLE_INDEX_PATH, {"items": []})
    subtitle_items = subtitle_index.get("items", []) if isinstance(subtitle_index, dict) else []
    published_by_url: dict[str, str] = {}
    title_by_url: dict[str, str] = {}
    if isinstance(subtitle_items, list):
        for item in subtitle_items:
            url = item.get("url")
            if not isinstance(url, str):
                continue
            normalized = normalize_source_url(url)
            if isinstance(item.get("title"), str) and item["title"].strip():
                title_by_url[normalized] = item["title"].strip()
            published = item.get("published_at")
            if isinstance(published, str) and published:
                published_by_url[normalized] = published[:10]
            elif isinstance(item.get("upload_date"), str) and len(item["upload_date"]) >= 8:
                date = item["upload_date"]
                published_by_url[normalized] = f"{date[:4]}-{date[4:6]}-{date[6:8]}"

    for path in collect_raw_candidates():
        document = read_source_document(path)
        if not document:
            continue

        content_id = content_id_for_url(document.source_url)
        target_path = RAW_DIR / f"{content_id}.txt"

        existing_text = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        candidate_text = path.read_text(encoding="utf-8")
        if not target_path.exists() or len(candidate_text) > len(existing_text):
            ensure_parent(target_path)
            target_path.write_text(candidate_text, encoding="utf-8")

        documents.setdefault(
            content_id,
            {
                "id": content_id,
                "source_url": document.source_url,
                "raw_file": target_path.name,
                "source_title": title_by_url.get(document.source_url, ""),
                "published_at": published_by_url.get(
                    document.source_url,
                    (
                        f"{path.name[:4]}-{path.name[4:6]}-{path.name[6:8]}"
                        if path.name[:8].isdigit()
                        else ""
                    ),
                ),
            },
        )

        if path.parent != RAW_DIR:
            path.unlink()

    return documents


def rebuild_briefs(raw_documents: dict[str, dict[str, str]]) -> dict[str, object]:
    legacy_briefs = load_legacy_briefs()
    existing_index = load_index(BRIEFS_INDEX_PATH).get("items", {})
    index = {"version": 1, "items": {}}

    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    for path in BRIEFS_DIR.glob("*.md"):
        path.unlink()

    for content_id, metadata in sorted(raw_documents.items()):
        source_url = metadata["source_url"]
        raw_path = RAW_DIR / metadata["raw_file"]
        document = read_source_document(raw_path)
        if not document:
            continue

        if source_url in legacy_briefs:
            title = legacy_briefs[source_url]["title"]
            brief_text = ensure_cover_image_markdown(legacy_briefs[source_url]["content"], source_url)
        else:
            title = metadata.get("source_title") or raw_path.stem
            brief_text = build_brief_from_transcript(raw_path.read_text(encoding="utf-8"), source_url)

        brief_path = BRIEFS_DIR / f"{content_id}.md"
        brief_path.write_text(brief_text, encoding="utf-8")
        existing_item = existing_index.get(content_id, {})
        item = {
            "id": content_id,
            "title": title,
            "source_url": source_url,
            "raw_file": metadata["raw_file"],
            "brief_file": brief_path.name,
            "published_at": metadata.get("published_at", ""),
            "read_at": existing_item.get("read_at"),
            "queued_for_deep_read": bool(existing_item.get("queued_for_deep_read")),
            "queued_at": existing_item.get("queued_at"),
            "updated_at": existing_item.get("updated_at") or now_iso(),
        }
        index["items"][content_id] = item

    return index


def rebuild_deep_reads() -> dict[str, object]:
    DEEP_READS_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_index(DEEP_READS_INDEX_PATH)
    items = existing.get("items", {})
    for path in DEEP_READS_DIR.glob("*.md"):
        if path.name == "index.json":
            continue
        if path.stem not in items:
            path.unlink()
    return {"version": 1, "items": items}


def cleanup_legacy_dirs() -> None:
    for directory in [LEGACY_BRIEFS_RAW_DIR, LEGACY_BRIEFS_ARCHIVED_DIR]:
        if directory.exists():
            shutil.rmtree(directory)


def sync_subtitle_index(raw_documents: dict[str, dict[str, str]]) -> None:
    payload = load_json(SUBTITLE_INDEX_PATH, {"items": []})
    if not isinstance(payload, dict):
        payload = {"items": []}
    items = payload.get("items", [])
    if not isinstance(items, list):
        items = []
    for item in items:
        url = item.get("url")
        if not isinstance(url, str):
            continue
        normalized = normalize_source_url(url)
        content_id = content_id_for_url(normalized)
        if content_id not in raw_documents:
            continue
        item["url"] = normalized
        item["content_id"] = content_id
        item["subtitle_path"] = str((RAW_DIR / f"{content_id}.txt").resolve())
    payload["items"] = items
    write_json(SUBTITLE_INDEX_PATH, payload)


def main() -> None:
    raw_documents = migrate_raw_documents()
    briefs_index = rebuild_briefs(raw_documents)
    deep_reads_index = rebuild_deep_reads()
    write_json(BRIEFS_INDEX_PATH, briefs_index)
    write_json(DEEP_READS_INDEX_PATH, deep_reads_index)
    sync_subtitle_index(raw_documents)
    cleanup_legacy_dirs()
    print(json.dumps({"raw": len(raw_documents), "briefs": len(briefs_index["items"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
