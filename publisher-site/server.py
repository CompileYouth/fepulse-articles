from __future__ import annotations

import json
import os
import re
import shutil
import urllib.parse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "publisher-site"
ARTICLES_DIR = ROOT / "selected"
BRIEFS_DIR = ROOT / "briefs"
BRIEFS_ARCHIVED_DIR = BRIEFS_DIR / "archived"
DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(.+)\.md$")


def build_article_record(path: Path) -> dict[str, str | None]:
    match = DATE_PREFIX_RE.match(path.name)
    scheduled_date = None
    title = path.stem
    if match:
        scheduled_date = match.group(1)
        title = match.group(2)

    return {
        "filename": path.name,
        "title": title,
        "scheduled_date": scheduled_date,
    }


def build_scheduled_filename(title: str, scheduled_date: str) -> str:
    return f"{scheduled_date} {title}.md"


class PublisherHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/selected":
            self.handle_selected()
            return
        if parsed.path == "/api/briefs":
            self.handle_briefs()
            return
        if parsed.path == "/api/content":
            self.handle_content(parsed.query)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/promote-brief":
            self.handle_promote_brief()
            return
        if parsed.path == "/api/schedule-selected":
            self.handle_schedule_selected()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")

    def handle_selected(self) -> None:
        files = sorted(
            ARTICLES_DIR.glob("*.md"),
            key=lambda path: path.name,
        )
        payload = [build_article_record(path) for path in files]
        self.send_json(payload)

    def handle_briefs(self) -> None:
        unread = sorted(
            (path for path in BRIEFS_DIR.glob("*.md") if path.name != "README.md"),
            key=lambda path: path.name,
        )
        archived = sorted(
            (path for path in BRIEFS_ARCHIVED_DIR.glob("*.md") if path.name != "README.md"),
            key=lambda path: path.name,
        )
        payload = {
            "unread": [{"filename": path.name, "title": path.stem} for path in unread],
            "archived": [{"filename": path.name, "title": path.stem} for path in archived],
        }
        self.send_json(payload)

    def handle_content(self, query_string: str) -> None:
        params = urllib.parse.parse_qs(query_string)
        filename = params.get("filename", [None])[0]
        scope = params.get("scope", [None])[0]
        scope_dir = {
            "selected": ARTICLES_DIR,
            "briefs": BRIEFS_DIR,
            "archived": BRIEFS_ARCHIVED_DIR,
        }.get(scope)

        if not scope_dir:
            self.send_error(HTTPStatus.BAD_REQUEST, "scope is required")
            return
        if not filename:
            self.send_error(HTTPStatus.BAD_REQUEST, "filename is required")
            return

        file_path = (scope_dir / filename).resolve()
        if file_path.parent != scope_dir.resolve() or not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "content not found")
            return

        payload = {
            "filename": file_path.name,
            "content": file_path.read_text(encoding="utf-8"),
            "scope": scope,
        }
        self.send_json(payload)

    def handle_promote_brief(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8") or "{}")
        except (ValueError, json.JSONDecodeError):
            self.send_error(HTTPStatus.BAD_REQUEST, "invalid json")
            return

        filename = payload.get("filename")
        if not filename:
            self.send_error(HTTPStatus.BAD_REQUEST, "filename is required")
            return

        source_path = (BRIEFS_DIR / filename).resolve()
        target_path = (ARTICLES_DIR / filename).resolve()

        if source_path.parent != BRIEFS_DIR.resolve() or not source_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "brief not found")
            return
        if target_path.parent != ARTICLES_DIR.resolve():
            self.send_error(HTTPStatus.BAD_REQUEST, "invalid target")
            return
        if target_path.exists():
            self.send_error(HTTPStatus.CONFLICT, "selected file already exists")
            return

        shutil.move(str(source_path), str(target_path))
        self.send_json(
            {
                "ok": True,
                "moved_to": target_path.name,
            }
        )

    def handle_schedule_selected(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8") or "{}")
        except (ValueError, json.JSONDecodeError):
            self.send_error(HTTPStatus.BAD_REQUEST, "invalid json")
            return

        filename = payload.get("filename")
        scheduled_date = payload.get("scheduled_date")
        if not filename:
            self.send_error(HTTPStatus.BAD_REQUEST, "filename is required")
            return
        if not isinstance(scheduled_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", scheduled_date):
            self.send_error(HTTPStatus.BAD_REQUEST, "scheduled_date must be YYYY-MM-DD")
            return

        source_path = (ARTICLES_DIR / filename).resolve()
        if source_path.parent != ARTICLES_DIR.resolve() or not source_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "selected article not found")
            return

        record = build_article_record(source_path)
        target_path = (ARTICLES_DIR / build_scheduled_filename(record["title"], scheduled_date)).resolve()
        if target_path.parent != ARTICLES_DIR.resolve():
            self.send_error(HTTPStatus.BAD_REQUEST, "invalid target")
            return
        if target_path.exists() and target_path != source_path:
            self.send_error(HTTPStatus.CONFLICT, "scheduled file already exists")
            return

        source_path.rename(target_path)
        self.send_json(
            {
                "ok": True,
                "filename": target_path.name,
                "title": record["title"],
                "scheduled_date": scheduled_date,
            }
        )

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
