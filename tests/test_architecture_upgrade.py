import json
import tempfile
import unittest
from pathlib import Path

from utils.document_model import document_blocks_to_markdown
from utils.mineru_route_a import build_mineru_route_a_pages
from utils.raw_metric_store import write_raw_metric_store


class ArchitectureUpgradeTests(unittest.TestCase):
    def test_document_markdown_preserves_titles_text_and_html_tables(self):
        markdown = document_blocks_to_markdown(
            [
                {"content_type": "title", "plain_text": "环境绩效", "section_path": ["环境绩效"]},
                {"content_type": "text", "plain_text": "公司持续节能。"},
                {"content_type": "table", "plain_text": "用水量 10 吨", "raw_content": "<table><tr><td>用水量</td></tr></table>"},
            ]
        )
        self.assertIn("# 环境绩效", markdown)
        self.assertIn("公司持续节能", markdown)
        self.assertIn("<table>", markdown)

    def test_mineru_route_a_writes_flat_raw_metric_store(self):
        block = {
            "block_id": "p1_table_0",
            "page_number": 1,
            "content_type": "table",
            "section_path": ["关键绩效", "环境绩效"],
            "bbox": [1, 2, 3, 4],
            "metadata": {"table_caption": []},
            "plain_text": "指标 2024 单位 用水量 100 吨",
            "raw_content": "<table><tr><td>指标</td><td>2024</td><td>单位</td></tr><tr><td>用水量</td><td>100</td><td>吨</td></tr></table>",
        }
        result = build_mineru_route_a_pages([block])
        with tempfile.TemporaryDirectory() as tmp:
            summary = write_raw_metric_store(Path(tmp), result["pages"])
            rows = json.loads((Path(tmp) / "raw_table_metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["count"], 1)
        self.assertEqual(rows[0]["metric_name"], "用水量")
        self.assertEqual(rows[0]["bbox"], [1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
