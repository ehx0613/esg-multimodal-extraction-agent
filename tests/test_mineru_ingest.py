import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.pdf_ingest import ingest_pdf
from utils.structured_rag_chunks import build_structured_chunks_from_all_table_rows


class MinerUIngestTests(unittest.TestCase):
    def _write_mineru_sample(self, root: Path, pdf_path: Path) -> Path:
        content_dir = root / pdf_path.stem / "auto"
        content_dir.mkdir(parents=True)
        content_path = content_dir / f"{pdf_path.stem}_content_list.json"
        content_path.write_text(
            json.dumps(
                [
                    {
                        "type": "text",
                        "text": "环境篇",
                        "text_level": 1,
                        "bbox": [10, 10, 200, 40],
                        "page_idx": 0,
                    },
                    {
                        "type": "text",
                        "text": "能源管理",
                        "text_level": 2,
                        "bbox": [10, 50, 200, 80],
                        "page_idx": 0,
                    },
                    {
                        "type": "text",
                        "text": "公司持续提升能源使用效率。",
                        "bbox": [10, 90, 500, 140],
                        "page_idx": 0,
                    },
                    {
                        "type": "table",
                        "table_body": (
                            "<table><tr><td>指标</td><td>2024</td><td>单位</td></tr>"
                            "<tr><td>用水量</td><td>25,041</td><td>吨</td></tr></table>"
                        ),
                        "table_caption": ["环境绩效"],
                        "bbox": [10, 150, 900, 500],
                        "page_idx": 0,
                    },
                    {
                        "type": "header",
                        "text": "公司名称",
                        "bbox": [10, 0, 200, 10],
                        "page_idx": 0,
                    },
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return content_path

    def test_ingest_uses_mineru_document_model_and_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "report.pdf"
            pdf_path.write_bytes(b"not-needed-when-mineru-is-available")
            mineru_root = root / "mineru"
            self._write_mineru_sample(mineru_root, pdf_path)

            ingest = ingest_pdf(
                pdf_path,
                root / "report_output",
                parser_backend="mineru",
                mineru_output_root=str(mineru_root),
            )

            self.assertEqual(ingest["manifest"]["parser_name"], "mineru")
            self.assertEqual(ingest["manifest"]["document_model_version"], "1.1")
            self.assertEqual(
                ingest["manifest"]["parser_selection_reason"],
                "mineru_content_list_available",
            )
            self.assertTrue(Path(ingest["paths"]["markdown"]).exists())
            self.assertEqual(len(ingest["pages"]), 1)
            self.assertIn("用水量", ingest["pages"][0]["text"])
            self.assertNotIn("公司名称", ingest["pages"][0]["text"])

            table_chunks = [chunk for chunk in ingest["chunks"] if chunk["chunk_type"] == "table_like"]
            self.assertEqual(len(table_chunks), 1)
            self.assertEqual(table_chunks[0]["page_number"], 1)
            self.assertEqual(table_chunks[0]["section_path"], ["环境篇", "能源管理"])
            self.assertEqual(table_chunks[0]["bbox"], [10, 150, 900, 500])
            self.assertIn("25,041", table_chunks[0]["text"])
            self.assertIn("吨", table_chunks[0]["unit_hits"])

            self.assertTrue(Path(ingest["paths"]["document_model"]).exists())
            self.assertTrue(Path(ingest["paths"]["document_blocks"]).exists())

            structured_chunks = build_structured_chunks_from_all_table_rows(root / "report_output")
            self.assertEqual(len(structured_chunks), 1)
            self.assertEqual(structured_chunks[0]["chunk_type"], "mineru_structured_table")
            self.assertEqual(structured_chunks[0]["bbox"], [10, 150, 900, 500])
            self.assertIn("<table>", structured_chunks[0]["raw_content"])

    def test_ingest_reuses_mineru_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "report.pdf"
            pdf_path.write_bytes(b"pdf")
            mineru_root = root / "mineru"
            self._write_mineru_sample(mineru_root, pdf_path)
            output_dir = root / "report_output"

            first = ingest_pdf(
                pdf_path,
                output_dir,
                parser_backend="auto",
                mineru_output_root=str(mineru_root),
            )
            second = ingest_pdf(
                pdf_path,
                output_dir,
                parser_backend="auto",
                mineru_output_root=str(mineru_root),
            )

            self.assertFalse(first["cache_used"])
            self.assertTrue(second["cache_used"])
            self.assertEqual(second["manifest"]["parser_name"], "mineru")

    def test_auto_falls_back_to_pymupdf_contract(self):
        pages = [{"page_number": 1, "text": "环境管理与能源使用", "char_count": 9}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "report.pdf"
            pdf_path.write_bytes(b"pdf")
            with patch("utils.pdf_ingest.extract_pdf_text_by_page", return_value=pages):
                ingest = ingest_pdf(
                    pdf_path,
                    root / "report_output",
                    parser_backend="auto",
                    mineru_output_root=str(root / "missing"),
                )

            self.assertEqual(ingest["manifest"]["parser_name"], "pymupdf")
            self.assertEqual(ingest["pages"], pages)
            self.assertEqual(ingest["blocks"][0]["source_type"], "pymupdf_text")


if __name__ == "__main__":
    unittest.main()
