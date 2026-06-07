import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.schema import ESG_SCHEMA
from backend.database import create_retrieval_eval_record
from utils.hybrid_retriever import retrieve_hybrid_chunks
from utils.retrieval_eval import evaluate_retrieval


def read_csv(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate ESG retrieval hit rate and MRR.")
    parser.add_argument("--eval-set", default=str(PROJECT_ROOT / "docs" / "eval" / "retrieval_eval_set.csv"))
    parser.add_argument("--chunks", required=True, help="Path to route_b_chunks.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--industry", default=None)
    parser.add_argument("--save", action="store_true", help="Persist the eval summary to SQLite.")
    parser.add_argument("--db-path", default=None, help="Optional SQLite path. Defaults to AGENT_DB_PATH.")
    parser.add_argument("--task-id", default=None, help="Optional task id to link this eval run.")
    parser.add_argument("--eval-set-name", default=None, help="Human-readable eval set name.")
    parser.add_argument(
        "--retrieval-profile",
        default="bm25_query_agg_evidence_rerank_v1",
        help="Retrieval profile label stored with saved eval records.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    eval_rows = read_csv(Path(args.eval_set))
    chunks = read_json(Path(args.chunks))

    def retriever(field_item: Dict[str, Any], chunk_rows: List[Dict[str, Any]]):
        return retrieve_hybrid_chunks(
            field_item,
            chunk_rows,
            top_k=args.top_k,
            industry=args.industry,
        )

    result = evaluate_retrieval(eval_rows, ESG_SCHEMA, chunks, retriever)
    if args.save:
        eval_record = create_retrieval_eval_record(
            task_id=args.task_id,
            eval_set_name=args.eval_set_name or Path(args.eval_set).name,
            retrieval_profile=args.retrieval_profile,
            hit_rate_at_5=result["hit_rate_at_k"],
            mrr_at_5=result["mrr_at_k"],
            avg_latency_ms=result["latency_ms"],
            metadata={
                "top_k": args.top_k,
                "industry": args.industry,
                "eval_set": str(Path(args.eval_set)),
                "chunks": str(Path(args.chunks)),
                "records": result["records"],
            },
            db_path=args.db_path,
        )
        result["eval_record_id"] = eval_record["id"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
