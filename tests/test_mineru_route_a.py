import unittest

from utils.mineru_route_a import build_mineru_route_a_pages, html_table_to_grid


class MinerURouteATests(unittest.TestCase):
    def test_rowspan_table_becomes_route_a_rows(self):
        block = {
            "block_id": "p53_table_0",
            "page_number": 53,
            "content_type": "table",
            "section_path": ["附录：关键绩效表", "环境绩效"],
            "bbox": [10, 20, 900, 800],
            "metadata": {"table_caption": []},
            "plain_text": "能源 指标 2024 单位 柴油总量 100 升",
            "raw_content": (
                "<table><tr><td rowspan='2'>能源</td><td>指标</td><td>2024</td><td>单位</td></tr>"
                "<tr><td>柴油总量</td><td>100</td><td>升</td></tr></table>"
            ),
        }

        result = build_mineru_route_a_pages([block])

        self.assertEqual(result["selected_tables"], 1)
        row = result["pages"][0]["tables"][0]["rows"][0]
        self.assertEqual(row["topic"], "能源")
        self.assertEqual(row["metric_name"], "柴油总量")
        self.assertEqual(row["values"], {"2024": "100"})
        self.assertEqual(row["unit"], "升")

    def test_index_table_is_not_selected(self):
        block = {
            "block_id": "p55_table_0",
            "page_number": 55,
            "content_type": "table",
            "section_path": ["附录：关键绩效表"],
            "metadata": {"table_caption": ["附录：可持续发展报告对标索引表"]},
            "plain_text": "章节 GRI Standards SDGs 2024",
            "raw_content": "<table><tr><td>章节</td><td>GRI Standards</td><td>SDGs</td></tr></table>",
        }

        result = build_mineru_route_a_pages([block])

        self.assertEqual(result["selected_tables"], 0)

    def test_grid_expands_rowspan(self):
        grid = html_table_to_grid(
            "<table><tr><td rowspan='2'>A</td><td>B</td></tr><tr><td>C</td></tr></table>"
        )
        self.assertEqual(grid, [["A", "B"], ["A", "C"]])


if __name__ == "__main__":
    unittest.main()
