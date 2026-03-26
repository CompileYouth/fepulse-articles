#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


SH_TZ = ZoneInfo("Asia/Shanghai")


@dataclass
class WebhookConfig:
    webhook: str
    secret: str


@dataclass
class AppConfig:
    app_id: str
    app_secret: str
    chat_id: str


@dataclass
class DeliveryConfig:
    webhook: WebhookConfig | None
    app: AppConfig | None


@dataclass
class ArticleSection:
    heading: str | None
    paragraphs: list[str]


@dataclass
class ArticleData:
    title: str
    preview_url: str
    participant_lines: list[str]
    source_url: str
    sections: list[ArticleSection]
    preview_text: str


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_delivery_config(workspace: Path) -> DeliveryConfig:
    merged: dict[str, str] = {}
    for path in (
        workspace / ".local" / "feishu-bot.env",
        workspace / ".local" / "feishu-app.env",
    ):
        merged.update(load_env_file(path))

    webhook = merged.get("FEISHU_BOT_WEBHOOK") or os.environ.get("FEISHU_BOT_WEBHOOK", "")
    secret = merged.get("FEISHU_BOT_SECRET") or os.environ.get("FEISHU_BOT_SECRET", "")
    app_id = merged.get("FEISHU_APP_ID") or os.environ.get("FEISHU_APP_ID", "")
    app_secret = merged.get("FEISHU_APP_SECRET") or os.environ.get("FEISHU_APP_SECRET", "")
    chat_id = merged.get("FEISHU_CHAT_ID") or os.environ.get("FEISHU_CHAT_ID", "")

    webhook_config = WebhookConfig(webhook=webhook, secret=secret) if webhook else None
    app_config = (
        AppConfig(app_id=app_id, app_secret=app_secret, chat_id=chat_id)
        if app_id and app_secret and chat_id
        else None
    )

    if not webhook_config and not app_config:
        raise SystemExit(
            "Missing Feishu config. Provide FEISHU_APP_ID/FEISHU_APP_SECRET/FEISHU_CHAT_ID "
            "for app delivery or FEISHU_BOT_WEBHOOK for webhook fallback."
        )
    return DeliveryConfig(webhook=webhook_config, app=app_config)


def sign(secret: str, timestamp: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(string_to_sign, b"", digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def get_today_prefix(date_override: str | None) -> str:
    if date_override:
        return date_override
    return datetime.now(SH_TZ).strftime("%Y-%m-%d")


def get_now_iso() -> str:
    return datetime.now(SH_TZ).isoformat(timespec="seconds")


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers or {},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"Feishu HTTP error: {exc.code} {exc.read().decode('utf-8', errors='ignore')}"
        ) from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Feishu request failed: {exc}") from exc

    result = json.loads(body)
    if result.get("code") not in (0, None) and result.get("StatusCode") not in (0, None):
        raise SystemExit(f"Feishu returned error: {body}")
    return result


def build_multipart_form_data(
    *,
    fields: dict[str, str],
    files: list[tuple[str, str, bytes, str]],
) -> tuple[bytes, str]:
    boundary = f"----CodexBoundary{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    for field_name, filename, content, content_type in files:
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="{field_name}"; '
                    f'filename="{filename}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                content,
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def fetch_app_token(config: AppConfig) -> str:
    payload = json.dumps(
        {"app_id": config.app_id, "app_secret": config.app_secret},
        ensure_ascii=False,
    ).encode("utf-8")
    result = request_json(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
        data=payload,
    )
    token = result.get("tenant_access_token")
    if not token:
        raise SystemExit("Feishu app auth succeeded but tenant_access_token is missing.")
    return token


def download_binary(url: str) -> tuple[bytes, str, str]:
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read()
            content_type = response.headers.get_content_type() or "application/octet-stream"
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"Failed to download image: {exc.code} {exc.read().decode('utf-8', errors='ignore')}"
        ) from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to download image: {exc}") from exc

    parsed = urllib.parse.urlparse(url)
    filename = Path(parsed.path).name or f"image-{uuid.uuid4().hex}.jpg"
    if "." not in filename:
        guessed_ext = mimetypes.guess_extension(content_type) or ".jpg"
        filename = f"{filename}{guessed_ext}"
    return content, filename, content_type


def upload_image_via_app(token: str, image_url: str) -> str:
    image_bytes, filename, content_type = download_binary(image_url)
    body, boundary = build_multipart_form_data(
        fields={"image_type": "message"},
        files=[("image", filename, image_bytes, content_type)],
    )
    result = request_json(
        "https://open.feishu.cn/open-apis/im/v1/images",
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        data=body,
    )
    image_key = (result.get("data") or {}).get("image_key") or result.get("image_key")
    if not image_key:
        raise SystemExit("Feishu image upload succeeded but image_key is missing.")
    return image_key


def parse_article(path: Path) -> ArticleData:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = re.sub(r"^\d{4}-\d{2}-\d{2}\s+", "", path.stem)

    preview_url = ""
    meta_lines: list[str] = []
    sections: list[ArticleSection] = []
    current_heading: str | None = None
    paragraph_buffer: list[str] = []

    def normalize_inline(text_value: str) -> str:
        return re.sub(r"\s+", " ", text_value).strip()

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer
        if not paragraph_buffer:
            return
        paragraph = " ".join(normalize_inline(item) for item in paragraph_buffer if item.strip())
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        if paragraph:
            if not sections or sections[-1].heading != current_heading:
                sections.append(ArticleSection(heading=current_heading, paragraphs=[]))
            sections[-1].paragraphs.append(paragraph)
        paragraph_buffer = []

    image_match = re.match(r"!\[\]\((.+)\)", lines[0].strip()) if lines else None
    if image_match:
        preview_url = image_match.group(1)
        lines = lines[1:]

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            flush_paragraph()
            continue
        if re.match(r"^#{1,6}\s+", stripped):
            flush_paragraph()
            heading_text = re.sub(r"^#{1,6}\s+", "", stripped).strip()
            current_heading = heading_text if heading_text and heading_text != title else None
            continue
        if stripped.startswith(">"):
            flush_paragraph()
            info = normalize_inline(stripped.lstrip(">").strip())
            if info:
                meta_lines.append(info)
            continue
        if stripped.startswith("- "):
            flush_paragraph()
            bullet = normalize_inline(stripped[2:])
            if bullet:
                if not sections or sections[-1].heading != current_heading:
                    sections.append(ArticleSection(heading=current_heading, paragraphs=[]))
                sections[-1].paragraphs.append(f"- {bullet}")
            continue
        paragraph_buffer.append(stripped)

    flush_paragraph()

    participant_lines: list[str] = []
    source_url = ""
    for item in meta_lines:
        if item in {"访谈信息", "#### 访谈信息", "访谈参与者："}:
            continue
        if item.startswith("原始来源："):
            source_url = item.split("：", 1)[1].strip()
            continue
        participant_lines.append(item[2:].strip() if item.startswith("- ") else item)

    preview_text_parts: list[str] = []
    for section in sections:
        if section.heading:
            preview_text_parts.append(section.heading)
        preview_text_parts.extend(section.paragraphs)
    preview_text = "\n\n".join(part for part in preview_text_parts if part).strip()

    return ArticleData(
        title=title,
        preview_url=preview_url,
        participant_lines=participant_lines,
        source_url=source_url,
        sections=sections,
        preview_text=preview_text,
    )


def build_app_card(article: ArticleData, image_key: str | None) -> dict[str, Any]:
    elements: list[dict[str, Any]] = []

    def strip_markdown(text: str) -> str:
        return text.replace("**", "").strip()

    if image_key:
        elements.append(
            {
                "tag": "img",
                "img_key": image_key,
                "alt": {
                    "tag": "plain_text",
                    "content": "封面图",
                },
            }
        )

    source_lines = ["**信息来源**"]
    if article.participant_lines:
        source_lines.append(f"嘉宾：{'；'.join(article.participant_lines)}")
    if article.source_url:
        source_lines.append(f"原始来源：[{article.source_url}]({article.source_url})")
    elements.append(
        {
            "tag": "note",
            "elements": [
                {
                    "tag": "lark_md",
                    "content": "\n".join(source_lines),
                }
            ],
        }
    )
    elements.append({"tag": "hr"})

    for index, section in enumerate(article.sections):
        if not section.paragraphs:
            continue
        if section.heading:
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": f"✨ {strip_markdown(section.heading)}",
                        "text_size": "heading-3",
                    },
                }
            )
        for paragraph in section.paragraphs:
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": paragraph,
                    },
                }
            )
        if index != len(article.sections) - 1:
            elements.append({"tag": "hr"})

    return {
        "config": {
            "wide_screen_mode": True,
            "enable_forward": True,
        },
        "header": {
            "title": {
                "tag": "plain_text",
                "content": article.title,
            },
            "subtitle": {
                "tag": "plain_text",
                "content": "FEPulse 精选",
            },
            "template": "wathet",
        },
        "elements": elements,
    }


def build_webhook_card(article: ArticleData) -> list[dict[str, Any]]:
    blocks: list[str] = []
    meta_parts = ["> **信息来源**"]
    if article.participant_lines:
        meta_parts.append(f"> 嘉宾：{'；'.join(article.participant_lines)}")
    if article.source_url:
        meta_parts.append(f"> 原始来源：[{article.source_url}]({article.source_url})")
    if article.preview_url:
        meta_parts.append(f"> 封面图：[{article.preview_url}]({article.preview_url})")
    blocks.append("\n".join(meta_parts))

    for section in article.sections:
        if not section.paragraphs:
            continue
        heading = f"**{section.heading}**\n" if section.heading else ""
        blocks.append(heading + "\n\n".join(section.paragraphs))

    elements: list[dict[str, Any]] = []
    if blocks:
        elements.append({"tag": "markdown", "content": blocks[0]})
    if len(blocks) > 1:
        elements.append({"tag": "hr"})
        for index, block in enumerate(blocks[1:]):
            elements.append({"tag": "markdown", "content": block})
            if index != len(blocks[1:]) - 1:
                elements.append({"tag": "hr"})
    return elements


def post_via_webhook(config: WebhookConfig, article: ArticleData) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True,
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": article.title,
                }
            },
            "elements": build_webhook_card(article),
        },
    }
    if config.secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = sign(config.secret, timestamp)

    return request_json(
        config.webhook,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )


def post_via_app(config: AppConfig, article: ArticleData) -> dict[str, Any]:
    token = fetch_app_token(config)
    image_key = None
    if article.preview_url:
        try:
            image_key = upload_image_via_app(token, article.preview_url)
        except SystemExit as exc:
            error_text = str(exc)
            if "im:resource:upload" not in error_text and "im:resource" not in error_text:
                raise
    card = build_app_card(article, image_key)
    return request_json(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        data=json.dumps(
            {
                "receive_id": config.chat_id,
                "msg_type": "interactive",
                "content": json.dumps(card, ensure_ascii=False),
            },
            ensure_ascii=False,
        ).encode("utf-8"),
    )


def send_article(config: DeliveryConfig, article: ArticleData) -> str:
    if config.app:
        post_via_app(config.app, article)
        return "app"
    if not config.webhook:
        raise SystemExit("Webhook fallback is unavailable because FEISHU_BOT_WEBHOOK is missing.")
    post_via_webhook(config.webhook, article)
    return "webhook"


def load_sent_log(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"sent": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_sent_log(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def iter_today_articles(selected_dir: Path, date_prefix: str) -> list[Path]:
    prefix = f"{date_prefix} "
    return [path for path in sorted(selected_dir.glob("*.md")) if path.name.startswith(prefix)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--date", default=None, help="YYYY-MM-DD; defaults to Asia/Shanghai today")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="send even if already recorded in sent log")
    args = parser.parse_args()

    workspace = Path(args.workspace_root).resolve()
    selected_dir = workspace / "selected"
    log_path = workspace / ".local" / "feishu-sent-log.json"
    date_prefix = get_today_prefix(args.date)
    articles = iter_today_articles(selected_dir, date_prefix)
    if not articles:
        print(f"[skip] no scheduled selected articles for {date_prefix}")
        return

    delivery_config = load_delivery_config(workspace)
    sent_log = load_sent_log(log_path)
    sent_entries = sent_log.setdefault("sent", {})

    for article_path in articles:
        key = article_path.name
        if sent_entries.get(key) and not args.force:
            print(f"[skip] already sent {key}")
            continue

        article = parse_article(article_path)
        if args.dry_run:
            mode = "app" if delivery_config.app else "webhook"
            print(
                f"[dry-run] would send {key} as {article.title} "
                f"via={mode} sections={len(article.sections)}"
            )
            continue

        mode = send_article(delivery_config, article)
        sent_entries[key] = {
            "sent_at": get_now_iso(),
            "path": str(article_path),
            "delivery_mode": mode,
        }
        save_sent_log(log_path, sent_log)
        print(f"[sent] {key} via={mode}")


if __name__ == "__main__":
    main()
