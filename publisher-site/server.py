from __future__ import annotations

import json
import os
import sys
import urllib.parse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "publisher-site"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from content_store import (  # noqa: E402
    BRIEFS_DIR,
    BRIEFS_INDEX_PATH,
    DEEP_READS_DIR,
    DEEP_READS_INDEX_PATH,
    RAW_DIR,
    load_index,
    now_iso,
    sort_read,
    sort_unread,
    write_json,
)


def build_item_payload(item: dict[str, object]) -> dict[str, object]:
    return {
        "id": item["id"],
        "title": item["title"],
        "read_at": item.get("read_at"),
        "queued_for_deep_read": bool(item.get("queued_for_deep_read")),
        "queued_at": item.get("queued_at"),
        "source_url": item.get("source_url"),
        "published_at": item.get("published_at"),
        "preview_image": youtube_thumbnail_url(str(item.get("source_url") or "")),
    }


def youtube_thumbnail_url(source_url: str) -> str | None:
    if not source_url:
        return None

    parsed = urllib.parse.urlparse(source_url)
    host = parsed.netloc.lower()
    video_id = None

    if "youtube.com" in host:
        if parsed.path == "/watch":
            video_id = urllib.parse.parse_qs(parsed.query).get("v", [None])[0]
        elif parsed.path.startswith("/shorts/"):
            video_id = parsed.path.split("/", 2)[2]
    elif "youtu.be" in host:
        video_id = parsed.path.lstrip("/").split("/", 1)[0]

    if not video_id:
        return None
    return f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"


class PublisherHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/briefs":
            self.handle_briefs()
            return
        if parsed.path == "/api/deep-reads":
            self.handle_deep_reads()
            return
        if parsed.path == "/api/content":
            self.handle_content(parsed.query)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/queue-deep-read":
            self.handle_queue_deep_read()
            return
        if parsed.path == "/api/mark-read":
            self.handle_mark_read()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")

    def handle_briefs(self) -> None:
        index = load_index(BRIEFS_INDEX_PATH)
        items = list(index.get("items", {}).values())
        unread = sort_unread([build_item_payload(item) for item in items if not item.get("read_at")])
        read = sort_read([build_item_payload(item) for item in items if item.get("read_at")])
        self.send_json({"unread": unread, "read": read})

    def handle_deep_reads(self) -> None:
        index = load_index(DEEP_READS_INDEX_PATH)
        items = list(index.get("items", {}).values())
        unread = sort_unread([build_item_payload(item) for item in items if not item.get("read_at")])
        read = sort_read([build_item_payload(item) for item in items if item.get("read_at")])
        self.send_json({"unread": unread, "read": read})

    def handle_content(self, query_string: str) -> None:
        params = urllib.parse.parse_qs(query_string)
        content_id = params.get("id", [None])[0]
        scope = params.get("scope", [None])[0]
        if scope not in {"briefs", "deep-reads"}:
            self.send_error(HTTPStatus.BAD_REQUEST, "scope is required")
            return
        if not content_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "id is required")
            return

        index_path = BRIEFS_INDEX_PATH if scope == "briefs" else DEEP_READS_INDEX_PATH
        content_dir = BRIEFS_DIR if scope == "briefs" else DEEP_READS_DIR
        index = load_index(index_path)
        item = index.get("items", {}).get(content_id)
        if not item:
            self.send_error(HTTPStatus.NOT_FOUND, "content not found")
            return

        raw_path = (RAW_DIR / item["raw_file"]).resolve()
        file_name = item.get("brief_file") if scope == "briefs" else item.get("deep_read_file")
        content = ""
        if isinstance(file_name, str):
            file_path = (content_dir / file_name).resolve()
            if file_path.parent != content_dir.resolve() or not file_path.exists():
                self.send_error(HTTPStatus.NOT_FOUND, "content file missing")
                return
            content = file_path.read_text(encoding="utf-8")
        elif scope == "deep-reads":
            content = (
                f"> 原始来源：{item.get('source_url', '')}\n\n"
                "## 这条内容已加入详读\n"
                "当前还没有生成详读正文。执行生成详读命令后，这里会显示按原字幕整理出的中文全文稿。\n"
            )
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "content file missing")
            return

        payload = {
            "id": content_id,
            "title": item["title"],
            "content": content,
            "scope": scope,
            "read_at": item.get("read_at"),
            "queued_for_deep_read": bool(item.get("queued_for_deep_read")),
            "queued_at": item.get("queued_at"),
            "source_url": item.get("source_url"),
            "raw_path": str(raw_path),
            "preview_image": youtube_thumbnail_url(str(item.get("source_url") or "")),
            "generated": isinstance(file_name, str),
        }
        self.send_json(payload)

    def handle_queue_deep_read(self) -> None:
        payload = self.read_json_body()
        if payload is None:
            return
        content_id = payload.get("id")
        if not isinstance(content_id, str) or not content_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "id is required")
            return

        briefs_index = load_index(BRIEFS_INDEX_PATH)
        brief_items = briefs_index.get("items", {})
        item = brief_items.get(content_id)
        if not item:
            self.send_error(HTTPStatus.NOT_FOUND, "brief not found")
            return

        deep_index = load_index(DEEP_READS_INDEX_PATH)
        deep_items = deep_index.setdefault("items", {})
        existing_deep = deep_items.get(content_id, {})
        queued_at = existing_deep.get("queued_at") or item.get("queued_at") or now_iso()
        deep_items[content_id] = {
            "id": content_id,
            "title": item["title"],
            "source_url": item["source_url"],
            "raw_file": item["raw_file"],
            "deep_read_file": existing_deep.get("deep_read_file"),
            "published_at": item.get("published_at", ""),
            "read_at": existing_deep.get("read_at"),
            "queued_at": queued_at,
            "generated_at": existing_deep.get("generated_at"),
            "updated_at": now_iso(),
        }
        brief_items.pop(content_id, None)
        write_json(BRIEFS_INDEX_PATH, briefs_index)
        write_json(DEEP_READS_INDEX_PATH, deep_index)
        self.send_json({"ok": True, "id": content_id, "queued_at": queued_at})

    def handle_mark_read(self) -> None:
        payload = self.read_json_body()
        if payload is None:
            return
        content_id = payload.get("id")
        scope = payload.get("scope")
        if scope not in {"briefs", "deep-reads"}:
            self.send_error(HTTPStatus.BAD_REQUEST, "scope is required")
            return
        if not isinstance(content_id, str) or not content_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "id is required")
            return

        index_path = BRIEFS_INDEX_PATH if scope == "briefs" else DEEP_READS_INDEX_PATH
        index = load_index(index_path)
        item = index.get("items", {}).get(content_id)
        if not item:
            self.send_error(HTTPStatus.NOT_FOUND, "item not found")
            return

        item["read_at"] = now_iso()
        item["updated_at"] = item["read_at"]
        write_json(index_path, index)
        self.send_json({"ok": True, "id": content_id, "read_at": item["read_at"]})

    def read_json_body(self) -> dict[str, object] | None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)
            return json.loads(body.decode("utf-8") or "{}")
        except (ValueError, json.JSONDecodeError):
            self.send_error(HTTPStatus.BAD_REQUEST, "invalid json")
            return None

    def send_json(self, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = os.environ.get("PUBLISHER_SITE_HOST", "127.0.0.1")
    port = int(os.environ.get("PUBLISHER_SITE_PORT", "8008"))
    server = ThreadingHTTPServer((host, port), PublisherHandler)
    print(f"Publisher site running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
