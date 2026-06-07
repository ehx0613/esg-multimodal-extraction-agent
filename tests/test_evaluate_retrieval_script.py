import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class EvaluateRetrievalScriptTests(unittest.TestCase):
    def _write_demo_inputs(self, tmp_path: Path) -> tuple[Path, Path]:
        chunks_path = tmp_path / "chunks.json"
        eval_path = tmp_path / "eval.csv"

        chunks_path.write_text(
            json.dumps(
                [
                    {
                        "chunk_id": "c1",
                        "page_number": 1,
                        "text": "温室气体排放总量为2000吨二氧化碳当量。",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        eval_path.write_text(
            "query_id,field_key,expected_chunk_id,expected_page,notes\n"
            "q1,total_ghg_emissions,c1,,demo\n",
            encoding="utf-8",
        )
        return chunks_path, eval_path

    def test_script_outputs_metrics_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            chunks_path, eval_path = self._write_demo_inputs(Path(tmp))

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.evaluate_retrieval",
                    "--eval-set",
                    str(eval_path),
                    "--chunks",
                    str(chunks_path),
                ],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(payload["hit_rate_at_k"], 1.0)
            self.assertEqual(payload["mrr_at_k"], 1.0)

    def test_script_can_save_metrics_to_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            chunks_path, eval_path = self._write_demo_inputs(tmp_path)
            db_path = tmp_path / "agent_state.db"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.evaluate_retrieval",
                    "--eval-set",
                    str(eval_path),
                    "--chunks",
                    str(chunks_path),
                    "--save",
                    "--db-path",
                    str(db_path),
                ],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(completed.stdout)
            self.assertIn("eval_record_id", payload)
            self.assertTrue(db_path.exists())


if __name__ == "__main__":
    unittest.main()
