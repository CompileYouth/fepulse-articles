from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from scripts.content_store import build_brief_from_transcript
from scripts.sync_reading_pipeline import filter_brief_documents


class BuildBriefFromTranscriptTest(unittest.TestCase):
    def test_english_transcript_does_not_flow_through_as_english_brief(self) -> None:
        transcript = """原文： https://www.youtube.com/watch?v=test

Codex is great for knowledge work.
It can work with email, documents, and data sources.
People use it as an agent management interface.
"""

        brief = build_brief_from_transcript(transcript, "https://www.youtube.com/watch?v=test")

        self.assertIn("> 原始来源：https://www.youtube.com/watch?v=test", brief)
        self.assertNotIn("Codex is great for knowledge work", brief)
        self.assertIn("中文简报待整理", brief)

    def test_chinese_transcript_intro_does_not_flow_through_as_brief(self) -> None:
        transcript = """原文： https://www.youtube.com/watch?v=test

大家好，欢迎回到节目，今天我们继续聊一个很重要的问题。
首先我们来回答一个问题，什么是机器人数据，它和大语言模型的数据有什么不同。
这段开场很长，但它仍然只是视频引子，不应该被直接截断成简报正文。
"""

        brief = build_brief_from_transcript(transcript, "https://www.youtube.com/watch?v=test")

        self.assertIn("> 原始来源：https://www.youtube.com/watch?v=test", brief)
        self.assertNotIn("大家好，欢迎回到节目", brief)
        self.assertIn("中文简报待整理", brief)


class FilterBriefDocumentsTest(unittest.TestCase):
    def test_excludes_documents_that_already_exist_in_deep_reads(self) -> None:
        raw_documents = {
            "brief-only": {"id": "brief-only", "source_url": "https://example.com/brief"},
            "deep-item": {"id": "deep-item", "source_url": "https://example.com/deep"},
        }
        deep_items = {"deep-item": {"id": "deep-item", "deep_read_file": "deep-item.md"}}

        filtered = filter_brief_documents(raw_documents, deep_items)

        self.assertEqual({"brief-only"}, set(filtered))

    def test_excludes_explicitly_off_topic_documents(self) -> None:
        raw_documents = {
            "off-topic": {"id": "off-topic", "source_url": "https://www.youtube.com/watch?v=jn_H3vuUC6E"},
            "source-archive-only": {"id": "source-archive-only", "source_url": "https://www.youtube.com/watch?v=sRKBGVFVYAw"},
            "war-debate": {"id": "war-debate", "source_url": "https://www.youtube.com/watch?v=QIa63fYcqvI"},
            "brief-only": {"id": "brief-only", "source_url": "https://example.com/brief"},
        }

        filtered = filter_brief_documents(raw_documents, {})

        self.assertEqual({"brief-only"}, set(filtered))


if __name__ == "__main__":
    unittest.main()
