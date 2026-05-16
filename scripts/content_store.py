from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


ROOT = Path(__file__).resolve().parents[1]
AI_ARCHIVE_DIR = ROOT / "ai-interview-archive-data"
RAW_DIR = ROOT / "raw"
BRIEFS_DIR = ROOT / "briefs"
DEEP_READS_DIR = ROOT / "deep-reads"
LEGACY_SELECTED_DIR = ROOT / "selected"
LEGACY_SELECTED_RAW_DIR = LEGACY_SELECTED_DIR / "raw"
LEGACY_BRIEFS_RAW_DIR = BRIEFS_DIR / "raw"
LEGACY_BRIEFS_ARCHIVED_DIR = BRIEFS_DIR / "archived"

BRIEFS_INDEX_PATH = BRIEFS_DIR / "index.json"
DEEP_READS_INDEX_PATH = DEEP_READS_DIR / "index.json"
SUBTITLE_INDEX_PATH = AI_ARCHIVE_DIR / "subtitle-index.json"

DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\s+")


@dataclass
class SourceDocument:
    source_url: str
    body: str


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_index(path: Path) -> dict[str, object]:
    payload = load_json(path, {"version": 1, "items": {}})
    if not isinstance(payload, dict):
        return {"version": 1, "items": {}}
    payload.setdefault("version", 1)
    payload.setdefault("items", {})
    return payload


def normalize_source_url(url: str) -> str:
    parsed = urlparse(url.strip())
    query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if parsed.netloc.endswith("youtube.com") or parsed.netloc == "youtu.be":
            if key in {"t", "si", "feature"}:
                continue
        query.append((key, value))
    normalized = parsed._replace(query=urlencode(query), fragment="")
    return urlunparse(normalized)


def content_id_for_url(url: str) -> str:
    normalized = normalize_source_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def title_without_date_prefix(filename_stem: str) -> str:
    return DATE_PREFIX_RE.sub("", filename_stem)


def read_source_document(path: Path) -> SourceDocument | None:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    lines = text.split("\n")
    if not lines:
        return None

    first_line = lines[0].strip()
    match = re.match(r"^(?:原文|原始来源)[:：]\s*(https?://\S+)\s*$", first_line)
    if not match:
        return None

    body = "\n".join(lines[1:]).strip()
    return SourceDocument(source_url=normalize_source_url(match.group(1)), body=body)


def extract_source_url_from_markdown(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    patterns = [
        r"^> 原始来源：(.+)$",
        r"^原始来源[:：]\s*(https?://\S+)$",
        r"^>.*原始来源[:：]\s*(https?://\S+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.M)
        if match:
            return normalize_source_url(match.group(1).strip())
    return None


def markdown_to_plain_paragraphs(text: str) -> list[str]:
    lines = text.replace("\r\n", "\n").split("\n")
    paragraphs: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if not buffer:
            return
        paragraph = "".join(buffer).strip()
        paragraph = re.sub(r"\*\*(.+?)\*\*", r"\1", paragraph)
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        if paragraph:
            paragraphs.append(paragraph)
        buffer = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush()
            continue
        if line.startswith("![](") or line.startswith(">") or line.startswith("#"):
            flush()
            continue
        buffer.append(line)

    flush()
    return paragraphs


def plain_text_from_transcript(text: str) -> str:
    cleaned = unescape(text)
    cleaned = re.sub(r"\[(?:MUSIC PLAYING|音乐)\]", "", cleaned, flags=re.I)
    cleaned = re.sub(r">>\s*", "", cleaned)
    cleaned = re.sub(r"\n+", "\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


def strip_source_header(text: str) -> str:
    return re.sub(r"^(?:原文|原始来源)[:：]\s*https?://\S+\s*", "", text, count=1).strip()


def is_mostly_english_text(text: str) -> bool:
    letters = re.findall(r"[A-Za-z]", text)
    if not letters:
        return False
    han = re.findall(r"[\u4e00-\u9fff]", text)
    if not han:
        return len(letters) >= 30
    return len(letters) >= len(han) * 2


def youtube_thumbnail_url(source_url: str) -> str | None:
    normalized = normalize_source_url(source_url)
    parsed = urlparse(normalized)
    host = parsed.netloc.lower()
    video_id = None

    if "youtube.com" in host:
        if parsed.path == "/watch":
            video_id = dict(parse_qsl(parsed.query)).get("v")
        elif parsed.path.startswith("/shorts/"):
            video_id = parsed.path.split("/", 2)[2]
    elif "youtu.be" in host:
        video_id = parsed.path.lstrip("/").split("/", 1)[0]

    if not video_id:
        return None
    return f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"


def ensure_cover_image_markdown(markdown_text: str, source_url: str) -> str:
    text = markdown_text.strip()
    thumbnail = youtube_thumbnail_url(source_url)
    if not thumbnail:
        return text + "\n"
    image_line = f"![]({thumbnail})"
    if image_line in text:
        return text + ("\n" if not text.endswith("\n") else "")

    lines = text.split("\n")
    insert_at = None
    for idx, line in enumerate(lines):
        if line.startswith("> 原始来源："):
            insert_at = idx + 1
            break
    if insert_at is None:
        lines = [image_line, "", *lines]
    else:
        lines = [*lines[:insert_at], "", image_line, *lines[insert_at:]]
    return "\n".join(lines).strip() + "\n"


def build_brief_from_article(article_text: str, source_url: str) -> str:
    paragraphs = markdown_to_plain_paragraphs(article_text)
    picked: list[str] = []
    total = 0
    for paragraph in paragraphs:
        if len(paragraph) < 40:
            continue
        remaining = 620 - total
        if remaining <= 0:
            break
        snippet = paragraph[:remaining].rstrip("，、；：,;: ")
        picked.append(snippet)
        total += len(snippet)
        if total >= 480 and len(picked) >= 2:
            break
    if not picked:
        picked = ["这份内容主要围绕一个核心问题展开，但旧文章没有留下足够可复用的正文。"]
    text = f"> 原始来源：{source_url}\n\n" + "\n\n".join(picked[:3]).strip() + "\n"
    return ensure_cover_image_markdown(text, source_url)


def build_brief_from_transcript(transcript_text: str, source_url: str) -> str:
    text = (
        f"> 原始来源：{source_url}\n\n"
        "这条内容的原始字幕已经入库，但当前自动同步步骤还不能把字幕稳定整理成可读的中文简报。"
        "为避免把原文开头片段直接当成简报展示，这里先只保留来源，并标记为中文简报待整理。\n"
    )
    return ensure_cover_image_markdown(text, source_url)


def build_deep_read_from_legacy(article_text: str, source_url: str) -> str:
    if extract_source_url_from_text(article_text):
        return article_text
    return f"> 原始来源：{source_url}\n\n{article_text.strip()}\n"


def extract_source_url_from_text(text: str) -> str | None:
    match = re.search(r"原始来源[:：]\s*(https?://\S+)", text)
    if match:
        return normalize_source_url(match.group(1))
    return None


def sort_unread(items: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        items,
        key=lambda item: (
            str(item.get("published_at") or ""),
            str(item.get("title") or ""),
        ),
        reverse=True,
    )


def sort_read(items: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        items,
        key=lambda item: str(item.get("read_at") or ""),
        reverse=True,
    )
