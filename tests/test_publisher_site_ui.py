import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublisherSiteUiTest(unittest.TestCase):
    def test_preview_actions_prioritize_mark_read_and_remove_copy(self):
        html = (ROOT / "publisher-site" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "publisher-site" / "app.js").read_text(encoding="utf-8")

        mark_read = re.search(r'<button id="markReadButton" class="([^"]+)"', html)

        self.assertIsNotNone(mark_read)
        self.assertIn("primary-button", mark_read.group(1).split())
        self.assertNotIn('id="copyButton"', html)
        self.assertNotIn("复制内容", html)
        self.assertNotIn("copyButton", app_js)
        self.assertNotIn("copyStyledContent", app_js)


if __name__ == "__main__":
    unittest.main()
