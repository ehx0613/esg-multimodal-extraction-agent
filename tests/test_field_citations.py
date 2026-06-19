import unittest

from utils.field_citations import attach_field_citations, flatten_for_csv, parse_source_pages


class FieldCitationTests(unittest.TestCase):
    def test_parse_source_pages_handles_page_image_and_json_list(self) -> None:
        self.assertEqual(parse_source_pages("page_39.png"), [39])
        self.assertEqual(parse_source_pages("[13, 38]"), [13, 38])
        self.assertEqual(parse_source_pages(["page_2.png", 5]), [2, 5])

    def test_attach_field_citations_prefers_existing_source_page(self) -> None:
        rows = [
            {
                "field_key": "esg_strategy_targets",
                "field_name_cn": "ESG战略目标",
                "category": "E",
                "status": "extracted",
                "value": True,
                "evidence": "制定ESG目标，并负责推进落实。",
                "source_pages": "[13]",
            }
        ]
        chunks = [
            {
                "chunk_id": "p11_1",
                "page_number": 11,
                "text": "公司制定业务战略目标。",
            },
            {
                "chunk_id": "p13_1",
                "page_number": 13,
                "text": "ESG领导小组定期识别ESG议题风险和机遇，制定ESG目标，并负责推进落实。",
            },
        ]

        enriched = attach_field_citations(rows, chunks, industry="manufacturing", top_k=2)

        self.assertEqual(enriched[0]["citation_chunk_id"], "p13_1")
        self.assertEqual(enriched[0]["citation_page_number"], 13)
        self.assertEqual(enriched[0]["citation_review_status"], "auto_cited")

    def test_flatten_for_csv_serializes_review_reasons(self) -> None:
        row = {
            "field_key": "demo",
            "citation_review_reasons": ["missing_existing_evidence", "no_retrieved_citation"],
        }

        flattened = flatten_for_csv([row])

        self.assertEqual(
            flattened[0]["citation_review_reasons"],
            "missing_existing_evidence;no_retrieved_citation",
        )

    def test_table_route_uses_table_page_citation(self) -> None:
        rows = [
            {
                "field_key": "total_ghg_emissions",
                "field_name_cn": "温室气体排放总量",
                "category": "E",
                "status": "extracted",
                "value": "2000",
                "source_route": "route_a_appendix_table",
                "evidence": "温室气体排放总量 吨二氧化碳当量 2024年 2000",
                "source_pages": "page_39.png",
                "page_image": "page_39.png",
            }
        ]
        chunks = [
            {
                "chunk_id": "p40_1",
                "page_number": 40,
                "text": "范围二温室气体排放量。",
            }
        ]

        enriched = attach_field_citations(rows, chunks, industry="manufacturing", top_k=1)

        self.assertEqual(enriched[0]["citation_chunk_id"], "table_page_39")
        self.assertEqual(enriched[0]["citation_page_number"], 39)
        self.assertEqual(enriched[0]["citation_review_status"], "auto_cited")

    def test_missing_field_does_not_promote_candidate_to_evidence_text(self) -> None:
        rows = [
            {
                "field_key": "hazardous_waste",
                "field_name_cn": "危险废弃物产生量",
                "category": "E",
                "status": "missing",
                "value": "",
            }
        ]
        chunks = [
            {
                "chunk_id": "p23_1",
                "page_number": 23,
                "text": "废弃物排放总量83.45万吨，非危险废弃物排放总量81.50万吨。",
            }
        ]

        enriched = attach_field_citations(rows, chunks, industry="manufacturing", top_k=1)

        self.assertEqual(enriched[0]["citation_evidence_text"], "")
        self.assertEqual(enriched[0]["citation_text_excerpt"], chunks[0]["text"])
        self.assertEqual(enriched[0]["citation_review_status"], "needs_review")


if __name__ == "__main__":
    unittest.main()
