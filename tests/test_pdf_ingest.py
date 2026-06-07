import unittest

from utils.pdf_ingest import build_page_features, select_route_a_candidate_pages
from utils.semantic_text_chunker import chunk_pages_semantic_esg
from utils.text_chunker import chunk_pages


class PDFIngestScoringTests(unittest.TestCase):
    def test_strong_performance_title_is_force_kept(self):
        pages = [
            {
                "page_number": 1,
                "text": "公司简介 董事长致辞",
                "char_count": 10,
            },
            {
                "page_number": 2,
                "text": "关键绩效表\n指标 单位 2024年 2023年\n用水量 吨 100 90\n用电量 千瓦时 200 180",
                "char_count": 50,
            },
        ]

        features = build_page_features(pages)
        selected = select_route_a_candidate_pages(
            features,
            top_k=1,
            min_score=999,
            expand_before=0,
            expand_after=0,
        )

        self.assertTrue(features[1]["force_keep"])
        self.assertEqual(selected["expanded_page_numbers"], [2])

    def test_index_page_with_few_numbers_is_penalized(self):
        pages = [
            {
                "page_number": 9,
                "text": "指标索引 GRI CASS 联交所指引\n环境 披露位置\n社会 披露位置",
                "char_count": 50,
            },
            {
                "page_number": 10,
                "text": "环境绩效数据\n指标 单位 2024 2023\n温室气体排放量 吨 100 90\n能源消耗 千瓦时 200 180",
                "char_count": 80,
            },
        ]

        features = build_page_features(pages)

        self.assertLess(features[0]["score"], features[1]["score"])
        self.assertIn("指标索引", features[0]["index_hits"])

    def test_high_unit_density_page_is_force_kept(self):
        pages = [
            {
                "page_number": 1,
                "text": "公司简介 战略介绍 愿景使命",
                "char_count": 20,
            },
            {
                "page_number": 2,
                "text": (
                    "绩效数据\n"
                    "温室气体 吨CO2e 10 20 30\n"
                    "能源 千瓦时 100 200 300\n"
                    "用水 立方米 100 200 300\n"
                    "环保投入 万元 5 6 7\n"
                    "员工 人 10 20 30\n"
                    "培训 小时 8 9 10\n"
                    "投诉 件 1 2 3\n"
                    "覆盖率 % 99 98 97\n"
                ),
                "char_count": 120,
            },
        ]

        features = build_page_features(pages)
        selected = select_route_a_candidate_pages(
            features,
            top_k=1,
            min_score=999,
            expand_before=0,
            expand_after=0,
        )

        self.assertTrue(features[1]["high_unit_density"])
        self.assertGreaterEqual(features[1]["unit_density_score"], 5)
        self.assertEqual(selected["expanded_page_numbers"], [2])

    def test_employee_composition_chart_page_is_b2_candidate_not_route_a_default(self):
        pages = [
            {"page_number": 1, "text": "公司简介", "char_count": 10},
            {
                "page_number": 2,
                "text": "员工组成情况\n按性别划分 男性 53.28% 女性 46.72%\n按学历划分 博士 0.11% 硕士 2.65% 本科 19.57%",
                "char_count": 80,
            },
            {"page_number": 3, "text": "公司治理", "char_count": 10},
            {"page_number": 4, "text": "员工培训", "char_count": 10},
            {"page_number": 5, "text": "供应链管理", "char_count": 10},
            {"page_number": 6, "text": "环境管理", "char_count": 10},
            {"page_number": 7, "text": "社会责任", "char_count": 10},
            {"page_number": 8, "text": "读者反馈", "char_count": 10},
            {"page_number": 9, "text": "附录", "char_count": 10},
            {
                "page_number": 10,
                "text": "关键绩效表\n指标 单位 2024年\n用电量 kWh 100",
                "char_count": 40,
            },
        ]

        features = build_page_features(pages)
        selected = select_route_a_candidate_pages(
            features,
            top_k=1,
            min_score=25,
            expand_before=0,
            expand_after=0,
        )

        self.assertTrue(features[1]["chart_force_keep"])
        self.assertIn("chart_candidate_for_b2", features[1]["reasons"])
        self.assertNotIn(2, selected["expanded_page_numbers"])

    def test_semantic_chunker_preserves_title_context_and_metric_type(self):
        pages = [
            {
                "page_number": 1,
                "text": (
                    "\u73af\u5883\u7ee9\u6548\n"
                    "\u516c\u53f8\u6301\u7eed\u63a8\u8fdb\u80fd\u6e90\u7ba1\u7406\u3002\n"
                    "\u6307\u6807 2024\u5e74 2023\u5e74\n"
                    "\u7528\u7535\u91cf 1000 kWh 900 kWh\n"
                    "\u7528\u6c34\u91cf 300 \u5428 280 \u5428\n"
                ),
                "char_count": 80,
            }
        ]

        chunks = chunk_pages_semantic_esg(pages, target_size=120, min_size=20, max_size=160)

        self.assertTrue(chunks)
        self.assertTrue(any(chunk["section_title"] == "\u73af\u5883\u7ee9\u6548" for chunk in chunks))
        self.assertTrue(any(chunk["chunk_type"] in {"table_like", "metric_dense"} for chunk in chunks))
        self.assertTrue(any("context_text" in chunk for chunk in chunks))
        self.assertTrue(any(chunk["number_count"] >= 2 for chunk in chunks))

    def test_semantic_chunker_keeps_kpi_label_value_panel_together(self):
        pages = [
            {
                "page_number": 52,
                "text": (
                    "\u5173\u952e\u7ee9\u6548\n"
                    "2024\u5e74\u5ea6\uff0c\u5458\u5de5\u57f9\u8bad\u60c5\u51b5\uff1a\n"
                    "\u5458\u5de5\u57f9\u8bad\u6295\u5165\uff1a\n"
                    "197\u4e07\u5143\n"
                    "\u5458\u5de5\u57f9\u8bad\u573a\u6b21\uff1a\n"
                    "227\u6b21\n"
                    "\u63a5\u53d7\u57f9\u8bad\u603b\u4eba\u6570\uff1a\n"
                    "3,547\u4eba\n"
                    "\u5458\u5de5\u57f9\u8bad\u8986\u76d6\u7387\uff1a\n"
                    "100%\n"
                    "\u57f9\u8bad\u603b\u65f6\u957f\uff1a\n"
                    "1,650,404\u5c0f\u65f6\n"
                    "\u5458\u5de5\u63a5\u53d7\u57f9\u8bad\u4eba\u5747\u65f6\u957f\uff1a\n"
                    "465.30\u5c0f\u65f6/\u4eba\n"
                    "\u63a5\u53d7\u57f9\u8bad\u603b\u4eba\u6b21\uff1a\n"
                    "23,913\u4eba\u6b21\n"
                ),
                "char_count": 180,
            }
        ]

        chunks = chunk_pages_semantic_esg(pages, target_size=900, min_size=250, max_size=1200)

        matching = [
            chunk
            for chunk in chunks
            if "1,650,404\u5c0f\u65f6" in chunk["text"]
        ]
        self.assertEqual(len(matching), 1)
        self.assertIn("\u57f9\u8bad\u603b\u65f6\u957f\uff1a", matching[0]["text"])
        self.assertIn("465.30\u5c0f\u65f6/\u4eba", matching[0]["text"])
        self.assertIn("23,913\u4eba\u6b21", matching[0]["text"])
        self.assertEqual(matching[0]["section_title"], "\u5173\u952e\u7ee9\u6548")

    def test_fixed_window_chunker_still_available(self):
        pages = [
            {
                "page_number": 1,
                "text": "abcdefghi",
            }
        ]

        chunks = chunk_pages(pages, chunk_size=4, overlap=1)

        self.assertEqual([chunk["text"] for chunk in chunks], ["abcd", "defg", "ghi"])


if __name__ == "__main__":
    unittest.main()
